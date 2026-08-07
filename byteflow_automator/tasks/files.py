"""
File Automation Tasks
=====================
Open, read, write, search, create, delete, move, copy files and folders.
All destructive ops require explicit confirmation (safe=False).
"""

import os
import shutil
import fnmatch
import platform
import subprocess
import secrets
from pathlib import Path
from typing import Union

from ..registry import AutomationTask, register_task

# ── Pending confirmation tokens for destructive ops ───────────────────────────
_pending: dict[str, tuple] = {}


def _token() -> str:
    return secrets.token_hex(4)


# ── Read / inspect ─────────────────────────────────────────────────────────────

def open_file(path: str) -> str:
    """Open a file with the OS default application."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"Error: '{path}' not found."
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.run(["open", path], check=True)
        else:
            subprocess.run(["xdg-open", path], check=True)
        return f"Opened: {path}"
    except Exception as e:
        return f"Error opening '{path}': {e}"


def read_file(path: str, max_lines: int = 200) -> str:
    """Read and return the contents of a text file (up to max_lines)."""
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return f"Error: '{path}' is not a file or does not exist."
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            return "".join(lines[:max_lines]) + f"\n... [{len(lines) - max_lines} more lines]"
        return "".join(lines)
    except Exception as e:
        return f"Error reading '{path}': {e}"


def list_folder(folder: str = "~", pattern: str = "*", recursive: bool = False) -> list:
    """List files in a folder matching a glob pattern."""
    folder = os.path.expanduser(folder)
    if not os.path.isdir(folder):
        return [f"Error: '{folder}' is not a folder."]
    matches = []
    if recursive:
        for root, _, files in os.walk(folder):
            for f in fnmatch.filter(files, pattern):
                matches.append(os.path.join(root, f))
    else:
        for name in os.listdir(folder):
            full = os.path.join(folder, name)
            if fnmatch.fnmatch(name, pattern):
                matches.append(full)
    return sorted(matches)


def search_files(folder: str, keyword: str, recursive: bool = True) -> list:
    """Find files whose NAME contains keyword (case-insensitive)."""
    folder = os.path.expanduser(folder)
    kw = keyword.lower()
    results = []
    if recursive:
        for root, dirs, files in os.walk(folder):
            for f in files:
                if kw in f.lower():
                    results.append(os.path.join(root, f))
    else:
        for name in os.listdir(folder):
            if kw in name.lower():
                results.append(os.path.join(folder, name))
    return sorted(results)


def file_info(path: str) -> dict:
    """Return metadata about a file: size, modified time, type."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return {"error": f"'{path}' not found."}
    stat = os.stat(path)
    import datetime
    return {
        "path": path,
        "size_bytes": stat.st_size,
        "size_human": _human_size(stat.st_size),
        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "is_file": os.path.isfile(path),
        "is_dir": os.path.isdir(path),
        "extension": Path(path).suffix,
    }


def _human_size(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


# ── Write / create ─────────────────────────────────────────────────────────────

def write_file(path: str, content: str, overwrite: bool = False) -> str:
    """Write text content to a file. Will not overwrite unless told to."""
    path = os.path.expanduser(path)
    if os.path.exists(path) and not overwrite:
        return f"Error: '{path}' already exists. Pass overwrite=True to replace it."
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written: {path} ({len(content)} chars)"
    except Exception as e:
        return f"Error writing '{path}': {e}"


def append_file(path: str, content: str) -> str:
    """Append text to an existing file (or create it)."""
    path = os.path.expanduser(path)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended to: {path}"
    except Exception as e:
        return f"Error appending to '{path}': {e}"


def create_folder(path: str) -> str:
    """Create a folder (and any missing parents)."""
    path = os.path.expanduser(path)
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder created: {path}"
    except Exception as e:
        return f"Error creating folder '{path}': {e}"


# ── Destructive ops (safe=False, require confirmation) ─────────────────────────

def preview_delete(path: str) -> str:
    """Preview what would be deleted. Returns a confirmation token."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"Error: '{path}' does not exist."
    tok = _token()
    _pending[tok] = ("delete", path)
    size = _human_size(os.stat(path).st_size) if os.path.isfile(path) else "folder"
    return (
        f"DRY RUN: Would delete '{path}' ({size}).\n"
        f"To confirm, call confirm_file_op('{tok}'). Token is single-use."
    )


def preview_move(src: str, dst: str) -> str:
    """Preview moving src to dst. Returns a confirmation token."""
    src, dst = os.path.expanduser(src), os.path.expanduser(dst)
    if not os.path.exists(src):
        return f"Error: '{src}' does not exist."
    tok = _token()
    _pending[tok] = ("move", src, dst)
    return (
        f"DRY RUN: Would move '{src}' -> '{dst}'.\n"
        f"To confirm, call confirm_file_op('{tok}'). Token is single-use."
    )


def preview_copy(src: str, dst: str) -> str:
    """Preview copying src to dst. Returns a confirmation token."""
    src, dst = os.path.expanduser(src), os.path.expanduser(dst)
    if not os.path.exists(src):
        return f"Error: '{src}' does not exist."
    tok = _token()
    _pending[tok] = ("copy", src, dst)
    return (
        f"DRY RUN: Would copy '{src}' -> '{dst}'.\n"
        f"To confirm, call confirm_file_op('{tok}'). Token is single-use."
    )


def confirm_file_op(token: str) -> str:
    """Execute a previously previewed destructive file operation."""
    if token not in _pending:
        return "Error: unknown or expired token. Run a preview_ function again."
    op = _pending.pop(token)
    action = op[0]
    try:
        if action == "delete":
            path = op[1]
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return f"Deleted: {path}"
        elif action == "move":
            shutil.move(op[1], op[2])
            return f"Moved: {op[1]} -> {op[2]}"
        elif action == "copy":
            if os.path.isdir(op[1]):
                shutil.copytree(op[1], op[2])
            else:
                shutil.copy2(op[1], op[2])
            return f"Copied: {op[1]} -> {op[2]}"
    except Exception as e:
        return f"Error performing {action}: {e}"


# ── Register all tasks ─────────────────────────────────────────────────────────

def register():
    tasks = [
        AutomationTask("open_file", open_file, "open a file with its default OS application", "files", "open_file('~/doc.pdf')"),
        AutomationTask("read_file", read_file, "read and return contents of a text file", "files", "read_file('~/notes.txt')"),
        AutomationTask("list_folder", list_folder, "list files in a folder, optionally with a glob pattern", "files", "list_folder('~/Downloads', '*.pdf')"),
        AutomationTask("search_files", search_files, "search for files by name keyword in a folder", "files", "search_files('~/projects', 'main')"),
        AutomationTask("file_info", file_info, "get metadata about a file (size, modified date, type)", "files", "file_info('~/report.pdf')"),
        AutomationTask("write_file", write_file, "write text content to a file (won't overwrite by default)", "files", "write_file('~/notes.txt', 'hello')"),
        AutomationTask("append_file", append_file, "append text to an existing file or create it", "files", "append_file('~/log.txt', 'new entry')"),
        AutomationTask("create_folder", create_folder, "create a new folder (and any missing parents)", "files", "create_folder('~/projects/new_app')"),
        AutomationTask("preview_delete", preview_delete, "preview deleting a file/folder - returns confirmation token", "files", "preview_delete('~/old.txt')", safe=False),
        AutomationTask("preview_move", preview_move, "preview moving a file/folder - returns confirmation token", "files", "preview_move('~/a.txt', '~/archive/a.txt')", safe=False),
        AutomationTask("preview_copy", preview_copy, "preview copying a file/folder - returns confirmation token", "files", "preview_copy('~/src', '~/backup')", safe=False),
        AutomationTask("confirm_file_op", confirm_file_op, "execute a previously previewed destructive file operation using its token", "files", "confirm_file_op('a1b2')"),
    ]
    for t in tasks:
        register_task(t)
