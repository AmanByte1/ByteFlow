"""
ByteFlow Settings Manager
==========================
Persistent settings stored in byteflow_settings.json.
Covers: model, theme, language, memory limit, notifications,
wake word, shortcuts/macros, and any future config.

All settings survive restarts. Changing the model here
automatically switches the agent on next request.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

SETTINGS_FILE = Path(__file__).parent.parent / "byteflow_settings.json"

DEFAULTS: dict[str, Any] = {
    # AI
    "model": "llama3",
    "temperature": 0.7,
    "max_tokens": 1024,
    "response_timeout": 120,

    # UI
    "theme": "dark",           # dark | light | system
    "language": "en",
    "font_size": "medium",     # small | medium | large
    "show_timestamps": True,
    "show_copy_btn": True,

    # Memory
    "memory_enabled": True,
    "memory_max_history": 2000,
    "memory_file": "byteflow_memory.json",
    "memory_search_enabled": True,

    # Voice
    "voice_enabled": True,
    "voice_language": "en-US",
    "voice_rate": 1.0,
    "wake_word_enabled": False,
    "wake_word": "hey byteflow",

    # Notifications
    "notifications_enabled": True,
    "notify_on_task_done": True,
    "notify_on_error": True,
    "watch_disk_threshold": 90,    # % full before alerting
    "watch_git_enabled": False,

    # Shortcuts (macros)
    "shortcuts": [
        {
            "id": "morning",
            "name": "Morning Routine",
            "icon": "☀️",
            "steps": [
                "git status",
                "show system info",
                "list running processes"
            ]
        },
        {
            "id": "build",
            "name": "Build Project",
            "icon": "🔨",
            "steps": [
                "run npm run build",
                "run npm test"
            ]
        }
    ],

    # Network
    "frontend_port": 7860,
    "core_port": 7861,
    "allow_remote": True,

    # Privacy
    "analytics_enabled": False,
    "crash_reports": False,
}


class Settings:
    """
    Read/write persistent ByteFlow settings.
    Merges saved values with defaults so new settings
    always have a fallback value.
    """

    def __init__(self, path: Path = SETTINGS_FILE):
        self._path = path
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                saved = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    self._data.update(saved)
            except Exception as e:
                print(f"[Settings] Could not load settings: {e}. Using defaults.")

    def _save(self):
        try:
            tmp = Path(str(self._path) + ".tmp")
            tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._path)
        except Exception as e:
            print(f"[Settings] Could not save settings: {e}")

    # ── Read ───────────────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULTS.get(key, default))

    def all(self) -> dict:
        return dict(self._data)

    def defaults(self) -> dict:
        return dict(DEFAULTS)

    # ── Write ──────────────────────────────────────────────────────────────────

    def set(self, key: str, value: Any) -> dict:
        """Set a single setting and persist."""
        if key not in DEFAULTS:
            return {"ok": False, "error": f"Unknown setting: '{key}'"}
        self._data[key] = value
        self._save()
        return {"ok": True, "key": key, "value": value}

    def update(self, changes: dict) -> dict:
        """Update multiple settings at once."""
        unknown = [k for k in changes if k not in DEFAULTS]
        if unknown:
            return {"ok": False, "error": f"Unknown settings: {unknown}"}
        self._data.update(changes)
        self._save()
        return {"ok": True, "updated": list(changes.keys())}

    def reset(self, key: str = None) -> dict:
        """Reset one setting (or all) to defaults."""
        if key:
            if key not in DEFAULTS:
                return {"ok": False, "error": f"Unknown setting: '{key}'"}
            self._data[key] = DEFAULTS[key]
        else:
            self._data = dict(DEFAULTS)
        self._save()
        return {"ok": True, "reset": key or "all"}

    # ── Shortcuts ──────────────────────────────────────────────────────────────

    def get_shortcuts(self) -> list:
        return self._data.get("shortcuts", [])

    def add_shortcut(self, name: str, icon: str, steps: list[str]) -> dict:
        import uuid
        shortcuts = self.get_shortcuts()
        shortcut = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "icon": icon,
            "steps": steps,
        }
        shortcuts.append(shortcut)
        self._data["shortcuts"] = shortcuts
        self._save()
        return {"ok": True, "shortcut": shortcut}

    def delete_shortcut(self, shortcut_id: str) -> dict:
        shortcuts = [s for s in self.get_shortcuts() if s["id"] != shortcut_id]
        if len(shortcuts) == len(self.get_shortcuts()):
            return {"ok": False, "error": f"Shortcut '{shortcut_id}' not found"}
        self._data["shortcuts"] = shortcuts
        self._save()
        return {"ok": True}

    def __repr__(self):
        return f"<Settings path={self._path} keys={list(self._data.keys())}>"


# ── Global instance ────────────────────────────────────────────────────────────
_settings: Settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
