"""
Quick Notes Plugin
==================
Persistent note-taking with tags and search.
Notes are stored in byteflow_notes.json next to this file.
"""

import json
import os
from pathlib import Path
from datetime import datetime

PLUGIN_META = {
    "id": "notes",
    "name": "Quick Notes",
    "description": "Persistent note-taking with tags and search.",
    "author": "ByteFlow Team",
    "version": "1.0.3",
    "icon": "📝",
    "tags": ["productivity"],
}

NOTES_FILE = Path(__file__).parent.parent.parent / "byteflow_notes.json"


def _load() -> list:
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text())
        except Exception:
            pass
    return []


def _save(notes: list):
    NOTES_FILE.write_text(json.dumps(notes, indent=2))


def note_add(content: str, tags: str = "") -> str:
    """Add a new note. Tags are comma-separated."""
    notes = _load()
    note = {
        "id": len(notes) + 1,
        "content": content,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "created": datetime.now().isoformat(),
    }
    notes.append(note)
    _save(notes)
    return f"Note #{note['id']} saved: {content[:60]}{'...' if len(content)>60 else ''}"


def note_list(tag: str = "") -> str:
    """List all notes, optionally filtered by tag."""
    notes = _load()
    if tag:
        notes = [n for n in notes if tag.lower() in [t.lower() for t in n.get("tags", [])]]
    if not notes:
        return "No notes found."
    lines = []
    for n in notes[-20:]:
        tags_str = f" [{', '.join(n['tags'])}]" if n.get("tags") else ""
        lines.append(f"#{n['id']}{tags_str}: {n['content'][:80]}")
    return "\n".join(lines)


def note_search(query: str) -> str:
    """Search notes by content."""
    notes = _load()
    q = query.lower()
    matches = [n for n in notes if q in n["content"].lower()]
    if not matches:
        return f"No notes matching '{query}'."
    return "\n".join(f"#{n['id']}: {n['content'][:80]}" for n in matches)


def note_delete(note_id: int) -> str:
    """Delete a note by ID."""
    notes = _load()
    before = len(notes)
    notes = [n for n in notes if n["id"] != note_id]
    if len(notes) == before:
        return f"Note #{note_id} not found."
    _save(notes)
    return f"Note #{note_id} deleted."


def register():
    from byteflow_automator.registry import AutomationTask, register_task
    tasks = [
        AutomationTask("note_add", note_add, "add a new note with optional tags", "productivity", "note_add('buy milk', 'personal,shopping')"),
        AutomationTask("note_list", note_list, "list all notes, optionally filtered by tag", "productivity", "note_list('work')"),
        AutomationTask("note_search", note_search, "search notes by content", "productivity", "note_search('meeting')"),
        AutomationTask("note_delete", note_delete, "delete a note by ID", "productivity", "note_delete(3)"),
    ]
    for t in tasks:
        register_task(t)
