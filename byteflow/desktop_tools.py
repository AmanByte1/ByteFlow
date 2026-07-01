"""
Small set of safe, scoped desktop helper tools for Windows (also works on
macOS/Linux where noted) - launching named apps/files/URLs, listing and
searching files in folders you specify, and clipboard read/write.

This is deliberately NOT a general computer-use agent: there's no screen
vision, no mouse/keyboard control, no acting on arbitrary parts of the
screen. Every function here does exactly one named, auditable thing, on
a folder or app you explicitly specify - the same trust model as the
add/multiply tools in builtin_tools.py, just pointed at the filesystem
and OS instead of numbers.

Destructive operations (move/copy/rename) are preview-only in organize_files()
- there is no argument that performs the action directly. A separate call
to confirm_organize(token) is required, using a one-time token that only
exists after a preview. Nothing here deletes files.
"""

import os
import platform
import shutil
import subprocess
import fnmatch

from .tools import Tool


# ---------------------------------------------------------------------------
# LAUNCHING APPS / FILES / URLS
# ---------------------------------------------------------------------------

# Curated friendly-name shortcuts. Lookup is case-insensitive. Anything not
# in this table just gets passed straight to the OS as-is (a raw URL, file
# path, or an app name the OS already knows like "notepad" or "calc") -
# this table is a convenience layer on top of launch(), not a restriction.
# Add more here as needed; the structure is just name -> URL/app string.
SHORTCUTS = {
    # media / social
    "youtube": "https://www.youtube.com",
    "spotify": "https://open.spotify.com",
    "gmail": "https://mail.google.com",
    "linkedin": "https://www.linkedin.com/feed/",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
    "facebook": "https://www.facebook.com",
    "whatsapp": "https://web.whatsapp.com",
    "netflix": "https://www.netflix.com",
    "instagram": "https://www.instagram.com",
    "reddit": "https://www.reddit.com",
    # dev tools
    "github": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "vscode": "code",
    "code": "code",
    "visualstudiocode": "code",
    # office / utilities (Windows app names - os.startfile resolves these)
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "calculator": "calc",
    "calc": "calc",
    "notepad": "notepad",
    "paint": "mspaint",
    "explorer": "explorer",
    "files": "explorer",
}


def list_shortcuts():
    """Return the sorted list of known shortcut names, for discoverability."""
    return sorted(SHORTCUTS.keys())


def resolve_shortcut(target):
    """
    If `target` matches a known shortcut name (case-insensitive, and
    tolerant of spaces/hyphens - "vs code" and "vs-code" both match
    "vscode"), return the URL/app it maps to. Otherwise return `target`
    unchanged, so any raw URL, file path, or OS-known app name still
    works exactly as before.
    """
    key = target.strip().lower()
    if key in SHORTCUTS:
        return SHORTCUTS[key]

    # tolerate spaces/hyphens: "vs code" / "vs-code" -> "vscode"
    normalized = key.replace(" ", "").replace("-", "")
    if normalized in SHORTCUTS:
        return SHORTCUTS[normalized]

    return target


def launch(target):
    """
    Open an app, file, or URL using the OS's default handler.

    `target` can be:
      - a known shortcut name, case-insensitive (see SHORTCUTS / list_shortcuts())
        e.g. "youtube", "vscode", "calculator"
      - a raw URL ("https://...")
      - a file path
      - an app name the OS already knows ("notepad", "calc") even if it's
        not in the shortcut table

    On Windows: os.startfile (the same thing double-clicking does).
    On macOS: `open`. On Linux: `xdg-open`.

    This does not search for or guess at paths beyond what SHORTCUTS or
    the OS itself resolves - if Windows wouldn't know what "target" is
    from Start -> Run, this won't either.
    """
    resolved = resolve_shortcut(target)
    system = platform.system()

    try:
        if system == "Windows":
            os.startfile(resolved)  # noqa: this only exists on Windows
        elif system == "Darwin":
            subprocess.run(["open", resolved], check=True, capture_output=True, text=True)
        else:
            subprocess.run(["xdg-open", resolved], check=True, capture_output=True, text=True)
        return f"Launched: {resolved}" if resolved == target else f"Launched: {target} ({resolved})"
    except FileNotFoundError:
        return f"Error: could not find or launch '{target}'"
    except subprocess.CalledProcessError as e:
        detail = e.stderr.strip() if e.stderr else f"exit code {e.returncode}"
        return f"Error launching '{target}': {detail}"
    except OSError as e:
        return f"Error launching '{target}': {e}"


# ---------------------------------------------------------------------------
# LISTING / SEARCHING FILES (read-only)
# ---------------------------------------------------------------------------

def list_files(folder=None, pattern="*", recursive=False):
    """
    List files in `folder` matching a glob `pattern` (e.g. "*.pdf").
    Read-only - never modifies anything. Returns a list of file paths,
    or a string starting with "Error:" if the folder doesn't exist.

    If `folder` is omitted, defaults to the user's home directory -
    this means an underspecified call (e.g. a planner forgetting to
    pass a folder) lists something sensible instead of crashing.
    """
    if not folder:
        folder = os.path.expanduser("~")
    folder = os.path.expanduser(folder)

    if not os.path.isdir(folder):
        return f"Error: '{folder}' is not a folder or does not exist"

    matches = []
    if recursive:
        for root, _dirs, files in os.walk(folder):
            for name in fnmatch.filter(files, pattern):
                matches.append(os.path.join(root, name))
    else:
        for name in os.listdir(folder):
            full = os.path.join(folder, name)
            if os.path.isfile(full) and fnmatch.fnmatch(name, pattern):
                matches.append(full)

    return sorted(matches)


def search_files(folder, keyword, recursive=True):
    """
    Find files in `folder` whose NAME contains `keyword` (case-insensitive).
    Read-only - does not search file contents, only filenames. For content
    search inside text files, that's a different, heavier operation outside
    this tool's scope.
    """
    return list_files(folder, pattern=f"*{keyword}*", recursive=recursive)


# ---------------------------------------------------------------------------
# CLIPBOARD
# ---------------------------------------------------------------------------

def read_clipboard():
    """Return the current text clipboard contents, or an error string."""
    try:
        import pyperclip
    except ImportError:
        return "Error: clipboard support requires 'pip install pyperclip'"

    try:
        return pyperclip.paste()
    except Exception as e:
        return f"Error reading clipboard: {e}"


def write_clipboard(text):
    """Set the text clipboard contents. Returns a confirmation string."""
    try:
        import pyperclip
    except ImportError:
        return "Error: clipboard support requires 'pip install pyperclip'"

    try:
        pyperclip.copy(text)
        return "Clipboard updated."
    except Exception as e:
        return f"Error writing clipboard: {e}"


# ---------------------------------------------------------------------------
# FILE ORGANIZE (move/copy/rename) - dry-run by default, confirm to act
# ---------------------------------------------------------------------------
#
# SAFETY DESIGN: organize_files() (the function the LLM planner can call as
# a Tool) NEVER accepts a confirm flag from its caller - it always returns a
# preview and a token. Actually performing the action requires a SEPARATE
# call to confirm_organize(token) - a human-driven follow-up step, not
# something the planner can pass in the same tool call. This means a
# hallucinated or malicious-looking planner response can never skip the
# dry-run: there is no argument position that performs a destructive action
# in one shot.

_VALID_ACTIONS = {"move", "copy", "rename"}
_pending_plans = {}  # token -> (action, plan list, folder/destination info)


def _make_token():
    import secrets
    return secrets.token_hex(4)


def organize_files(folder, action, pattern="*", destination=None):
    """
    Preview a move/copy/rename of files in `folder` matching `pattern`.

    ALWAYS a dry run - this function can NEVER perform the action itself,
    by design, so it's safe to expose to an LLM planner. It returns a
    preview and a confirmation token. To actually perform the previewed
    action, a human must separately call confirm_organize(token) - this
    is not something the planner can trigger in the same step.

    action: "move" or "copy" (requires `destination` folder) or
            "rename" (requires destination to be a naming pattern like "photo_{n}.jpg")
    pattern: glob pattern to select which files in `folder` are affected
    destination: target folder (move/copy) or naming pattern (rename)
    """
    if action not in _VALID_ACTIONS:
        return f"Error: action must be one of {sorted(_VALID_ACTIONS)}"

    folder = os.path.expanduser(folder)
    if not os.path.isdir(folder):
        return f"Error: '{folder}' is not a folder or does not exist"

    if action in ("move", "copy") and not destination:
        return "Error: 'destination' folder is required for move/copy"
    if action == "rename" and (not destination or "{n}" not in destination):
        return "Error: for rename, 'destination' must be a pattern containing {n}, e.g. 'photo_{n}.jpg'"

    matches = list_files(folder, pattern=pattern, recursive=False)
    if isinstance(matches, str):  # error from list_files
        return matches

    if not matches:
        return f"No files in '{folder}' match pattern '{pattern}'."

    if action in ("move", "copy"):
        destination_resolved = os.path.expanduser(destination)
        plan = [
            (src, os.path.join(destination_resolved, os.path.basename(src)))
            for src in matches
        ]
        preview_lines = [f"  {src} -> {dst}" for src, dst in plan]
    else:
        plan = [
            (src, os.path.join(folder, destination.replace("{n}", str(i))))
            for i, src in enumerate(matches, start=1)
        ]
        preview_lines = [f"  {os.path.basename(s)} -> {os.path.basename(d)}" for s, d in plan]

    token = _make_token()
    _pending_plans[token] = (action, plan)

    preview = "\n".join(preview_lines)
    return (
        f"DRY RUN ({action}, {len(plan)} file(s)) - nothing changed yet.\n"
        f"{preview}\n"
        f"To actually perform this, call confirm_organize('{token}'). "
        f"This token is single-use and only valid for this preview."
    )


def confirm_organize(token):
    """
    Actually perform a previously previewed organize_files() action.

    This is a deliberate, separate call - never something the LLM planner
    can trigger directly from organize_files()'s own arguments. A human
    (or code acting on a human's explicit instruction) must call this
    with the exact token returned by the preview.

    Tokens are single-use: calling confirm_organize twice with the same
    token returns an error the second time, since the plan is removed
    after it runs (success or failure) to prevent accidental replay.
    """
    if token not in _pending_plans:
        return "Error: unknown or already-used confirmation token. Run organize_files() again to get a new preview."

    action, plan = _pending_plans.pop(token)

    if action in ("move", "copy"):
        destination = os.path.dirname(plan[0][1]) if plan else None
        if destination:
            os.makedirs(destination, exist_ok=True)
        done = []
        for src, dst in plan:
            if action == "move":
                shutil.move(src, dst)
            else:
                shutil.copy2(src, dst)
            done.append(dst)
        verb = {"move": "Moved", "copy": "Copied"}[action]
        return f"{verb} {len(done)} file(s)."

    # rename
    done = []
    for src, dst in plan:
        os.rename(src, dst)
        done.append(dst)
    return f"Renamed {len(done)} file(s)."


# ---------------------------------------------------------------------------
# TOOL REGISTRATION
# ---------------------------------------------------------------------------

def get_desktop_tools():
    """Return the list of desktop-helper Tool instances."""
    return [
        Tool("launch", launch, "opens an app, file, or URL with the default handler (supports shortcut names like youtube, vscode, calculator)"),
        Tool("list_shortcuts", list_shortcuts, "lists known shortcut names that launch() understands"),
        Tool("list_files", list_files, "lists files in a folder matching a pattern"),
        Tool("search_files", search_files, "finds files in a folder by name keyword"),
        Tool("read_clipboard", read_clipboard, "returns current clipboard text"),
        Tool("write_clipboard", write_clipboard, "sets the clipboard text"),
        Tool("organize_files", organize_files, "previews a move/copy/rename of files; never performs it directly"),
        Tool("confirm_organize", confirm_organize, "performs a previously previewed organize_files action, given its token"),
    ]


def register_desktop_tools(agent):
    """Register all desktop-helper tools onto the given agent."""
    for tool in get_desktop_tools():
        agent.register_tool(tool)
