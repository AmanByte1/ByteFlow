"""
ByteFlow Chat History
======================
Persists full chat history across restarts, organized into sessions.
Each session is a conversation with a start time, title, and messages.

Sessions are stored in byteflow_history.json.
The UI can paginate through sessions and search past conversations.
"""

from __future__ import annotations
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

HISTORY_FILE = Path(__file__).parent.parent / "byteflow_history.json"
MAX_SESSIONS = 200       # keep last 200 sessions
MAX_MSG_PER_SESSION = 500


class ChatMessage:
    def __init__(self, role: str, content: str, mode: str = "run", ts: str = None):
        self.role = role           # "user" | "assistant" | "system" | "error"
        self.content = content
        self.mode = mode
        self.ts = ts or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content, "mode": self.mode, "ts": self.ts}

    @classmethod
    def from_dict(cls, d: dict) -> "ChatMessage":
        return cls(d["role"], d["content"], d.get("mode", "run"), d.get("ts"))


class ChatSession:
    def __init__(self, session_id: str = None, title: str = None, created: str = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.title = title or "New conversation"
        self.created = created or datetime.now().isoformat()
        self.updated = self.created
        self.messages: list[ChatMessage] = []
        self.pinned: bool = False

    def add(self, role: str, content: str, mode: str = "run") -> ChatMessage:
        msg = ChatMessage(role, content, mode)
        self.messages.append(msg)
        self.updated = msg.ts
        # Auto-title from first user message
        if role == "user" and self.title == "New conversation" and len(content) > 3:
            self.title = content[:48] + ("..." if len(content) > 48 else "")
        # Trim if too long
        if len(self.messages) > MAX_MSG_PER_SESSION:
            self.messages = self.messages[-MAX_MSG_PER_SESSION:]
        return msg

    def to_dict(self, include_messages: bool = True) -> dict:
        d = {
            "session_id": self.session_id,
            "title": self.title,
            "created": self.created,
            "updated": self.updated,
            "pinned": self.pinned,
            "message_count": len(self.messages),
        }
        if include_messages:
            d["messages"] = [m.to_dict() for m in self.messages]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ChatSession":
        s = cls(d["session_id"], d.get("title"), d.get("created"))
        s.updated = d.get("updated", s.created)
        s.pinned = d.get("pinned", False)
        for m in d.get("messages", []):
            s.messages.append(ChatMessage.from_dict(m))
        return s


class ChatHistory:
    """
    Manages all chat sessions with persistence.
    Always has an active session. Creates a new one on startup
    or when explicitly requested.
    """

    def __init__(self, path: Path = HISTORY_FILE):
        self._path = path
        self._sessions: dict[str, ChatSession] = {}
        self._active_id: Optional[str] = None
        self._load()
        if not self._active_id or self._active_id not in self._sessions:
            self._new_session()

    # ── Active session ─────────────────────────────────────────────────────────

    @property
    def active(self) -> ChatSession:
        return self._sessions[self._active_id]

    def add_message(self, role: str, content: str, mode: str = "run") -> ChatMessage:
        msg = self.active.add(role, content, mode)
        self._save()
        return msg

    def new_session(self) -> ChatSession:
        s = self._new_session()
        self._save()
        return s

    def _new_session(self) -> ChatSession:
        s = ChatSession()
        self._sessions[s.session_id] = s
        self._active_id = s.session_id
        return s

    def switch_session(self, session_id: str) -> dict:
        if session_id not in self._sessions:
            return {"ok": False, "error": f"Session '{session_id}' not found"}
        self._active_id = session_id
        return {"ok": True, "session": self.active.to_dict()}

    # ── Query ──────────────────────────────────────────────────────────────────

    def all_sessions(self, limit: int = 50) -> list[dict]:
        """Return session summaries (no messages), newest first."""
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.updated,
            reverse=True
        )
        pinned = [s for s in sessions if s.pinned]
        unpinned = [s for s in sessions if not s.pinned]
        ordered = pinned + unpinned
        return [s.to_dict(include_messages=False) for s in ordered[:limit]]

    def get_session(self, session_id: str) -> Optional[dict]:
        s = self._sessions.get(session_id)
        return s.to_dict(include_messages=True) if s else None

    def get_messages(self, session_id: str = None, n: int = 100) -> list[dict]:
        sid = session_id or self._active_id
        s = self._sessions.get(sid)
        if not s:
            return []
        return [m.to_dict() for m in s.messages[-n:]]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Search all messages across all sessions."""
        q = query.lower()
        results = []
        for session in self._sessions.values():
            for msg in session.messages:
                if q in msg.content.lower():
                    results.append({
                        "session_id": session.session_id,
                        "session_title": session.title,
                        "message": msg.to_dict(),
                    })
        # Sort by timestamp desc
        results.sort(key=lambda x: x["message"]["ts"], reverse=True)
        return results[:limit]

    def stats(self) -> dict:
        total_msg = sum(len(s.messages) for s in self._sessions.values())
        return {
            "total_sessions": len(self._sessions),
            "total_messages": total_msg,
            "active_session": self._active_id,
            "active_messages": len(self.active.messages),
        }

    # ── Manage ────────────────────────────────────────────────────────────────

    def pin_session(self, session_id: str, pinned: bool = True) -> dict:
        s = self._sessions.get(session_id)
        if not s:
            return {"ok": False, "error": "Not found"}
        s.pinned = pinned
        self._save()
        return {"ok": True, "pinned": pinned}

    def rename_session(self, session_id: str, title: str) -> dict:
        s = self._sessions.get(session_id)
        if not s:
            return {"ok": False, "error": "Not found"}
        s.title = title[:80]
        self._save()
        return {"ok": True, "title": s.title}

    def delete_session(self, session_id: str) -> dict:
        if session_id not in self._sessions:
            return {"ok": False, "error": "Not found"}
        if session_id == self._active_id:
            del self._sessions[session_id]
            if self._sessions:
                self._active_id = sorted(
                    self._sessions.values(), key=lambda s: s.updated, reverse=True
                )[0].session_id
            else:
                self._new_session()
        else:
            del self._sessions[session_id]
        self._save()
        return {"ok": True}

    def clear_all(self) -> dict:
        self._sessions = {}
        self._new_session()
        self._save()
        return {"ok": True, "message": "All history cleared"}

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save(self):
        # Trim old sessions
        if len(self._sessions) > MAX_SESSIONS:
            sorted_s = sorted(self._sessions.values(), key=lambda s: s.updated, reverse=True)
            keep = {s.session_id for s in sorted_s[:MAX_SESSIONS] if not s.pinned}
            keep.update(s.session_id for s in sorted_s if s.pinned)
            self._sessions = {sid: s for sid, s in self._sessions.items() if sid in keep}

        data = {
            "active_id": self._active_id,
            "sessions": {sid: s.to_dict() for sid, s in self._sessions.items()},
        }
        try:
            tmp = Path(str(self._path) + ".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._path)
        except Exception as e:
            print(f"[ChatHistory] Save failed: {e}")

    def _load(self):
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for sid, sd in data.get("sessions", {}).items():
                self._sessions[sid] = ChatSession.from_dict(sd)
            self._active_id = data.get("active_id")
        except Exception as e:
            print(f"[ChatHistory] Load failed: {e}. Starting fresh.")


# ── Global instance ────────────────────────────────────────────────────────────
_history: ChatHistory = None

def get_history() -> ChatHistory:
    global _history
    if _history is None:
        _history = ChatHistory()
    return _history
