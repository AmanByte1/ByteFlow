"""
App & URL Automation Tasks
===========================
Launch apps, open URLs, manage windows, clipboard, notifications.
Cross-platform (Windows/macOS/Linux).
"""

import os
import platform
import subprocess
from ..registry import AutomationTask, register_task

# ── App/URL shortcut map ───────────────────────────────────────────────────────
SHORTCUTS: dict[str, str] = {
    # Browsers
    "chrome": "google-chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "safari": "safari",
    # Dev tools
    "vscode": "code",
    "code": "code",
    "cursor": "cursor",
    "pycharm": "pycharm",
    "intellij": "idea",
    "sublime": "subl",
    "vim": "vim",
    "nvim": "nvim",
    "terminal": "terminal",  # filled in after _terminal() is defined below
    "cmd": "cmd",
    "powershell": "powershell",
    "bash": "bash",
    "zsh": "zsh",
    "gitbash": "git-bash",
    "docker": "docker",
    "postman": "postman",
    "insomnia": "insomnia",
    "dbeaver": "dbeaver",
    "tableplus": "tableplus",
    # Productivity
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "excel": "excel",
    "word": "winword",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "teams": "teams",
    "slack": "slack",
    "discord": "discord",
    "zoom": "zoom",
    "notion": "notion",
    "obsidian": "obsidian",
    # Websites
    "github": "https://github.com",
    "gitlab": "https://gitlab.com",
    "stackoverflow": "https://stackoverflow.com",
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "drive": "https://drive.google.com",
    "docs": "https://docs.google.com",
    "sheets": "https://sheets.google.com",
    "figma": "https://figma.com",
    "linkedin": "https://linkedin.com",
    "twitter": "https://twitter.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "npm": "https://npmjs.com",
    "pypi": "https://pypi.org",
}


def _terminal() -> str:
    system = platform.system()
    if system == "Windows":
        return "wt"  # Windows Terminal
    elif system == "Darwin":
        return "Terminal"
    else:
        for t in ("gnome-terminal", "xterm", "konsole", "alacritty", "kitty"):
            if subprocess.run(["which", t], capture_output=True).returncode == 0:
                return t
    return "xterm"


# Patch terminal shortcut now that _terminal() is defined
SHORTCUTS["terminal"] = _terminal()


def _resolve(target: str) -> str:
    key = target.strip().lower().replace(" ", "").replace("-", "")
    return SHORTCUTS.get(key, target)


def open_app(target: str) -> str:
    """
    Open an app, file, or URL.
    Supports shortcut names: vscode, chrome, github, slack, etc.
    """
    resolved = _resolve(target)
    system = platform.system()
    try:
        if resolved.startswith("http"):
            import webbrowser
            webbrowser.open(resolved)
            return f"Opened in browser: {resolved}"
        if system == "Windows":
            os.startfile(resolved)
        elif system == "Darwin":
            subprocess.run(["open", "-a", resolved] if not os.path.exists(resolved) else ["open", resolved], check=True)
        else:
            subprocess.Popen([resolved], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        label = f"{target} ({resolved})" if resolved != target else target
        return f"Launched: {label}"
    except Exception as e:
        return f"Error launching '{target}': {e}"


def open_url(url: str) -> str:
    """Open a URL in the default browser."""
    if not url.startswith("http"):
        url = "https://" + url
    import webbrowser
    webbrowser.open(url)
    return f"Opened URL: {url}"


def open_in_editor(path: str, editor: str = "vscode") -> str:
    """
    Open a file or folder in a code editor.
    Supports: vscode, cursor, sublime, vim, nvim, pycharm, etc.
    """
    path = os.path.expanduser(path)
    editor_cmd = _resolve(editor)
    try:
        subprocess.Popen([editor_cmd, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Opened '{path}' in {editor}"
    except FileNotFoundError:
        return f"Error: '{editor_cmd}' not found. Is {editor} installed?"
    except Exception as e:
        return f"Error: {e}"


def list_app_shortcuts() -> list:
    """Return all known app/URL shortcut names."""
    return sorted(SHORTCUTS.keys())


# ── Clipboard ──────────────────────────────────────────────────────────────────

def read_clipboard() -> str:
    """Return the current clipboard text content."""
    try:
        import pyperclip
        return pyperclip.paste()
    except ImportError:
        return "Error: install pyperclip → pip install pyperclip"
    except Exception as e:
        return f"Clipboard error: {e}"


def write_clipboard(text: str) -> str:
    """Copy text to the clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return f"Copied to clipboard ({len(text)} chars)"
    except ImportError:
        return "Error: install pyperclip → pip install pyperclip"
    except Exception as e:
        return f"Clipboard error: {e}"


# ── Notifications ──────────────────────────────────────────────────────────────

def notify(title: str, message: str) -> str:
    """Send a desktop notification."""
    system = platform.system()
    try:
        if system == "Windows":
            # Use plyer if available, fallback to msg
            try:
                from plyer import notification
                notification.notify(title=title, message=message, timeout=5)
            except ImportError:
                subprocess.run(["msg", "*", f"{title}: {message}"], capture_output=True)
        elif system == "Darwin":
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], check=True)
        else:
            subprocess.run(["notify-send", title, message], check=True)
        return f"Notification sent: {title}"
    except Exception as e:
        return f"Notification error: {e}"


# ── Register ───────────────────────────────────────────────────────────────────

def register():
    tasks = [
        AutomationTask("open_app", open_app, "launch an app or website by name or shortcut (vscode, chrome, slack, github...)", "apps", "open_app('vscode')"),
        AutomationTask("open_url", open_url, "open a URL in the default browser", "apps", "open_url('https://github.com')"),
        AutomationTask("open_in_editor", open_in_editor, "open a file or folder in a code editor (vscode, cursor, vim...)", "apps", "open_in_editor('~/project', 'vscode')"),
        AutomationTask("list_app_shortcuts", list_app_shortcuts, "list all known app and website shortcut names", "apps"),
        AutomationTask("read_clipboard", read_clipboard, "return the current clipboard text", "apps"),
        AutomationTask("write_clipboard", write_clipboard, "copy text to the clipboard", "apps", "write_clipboard('hello world')"),
        AutomationTask("notify", notify, "send a desktop notification with a title and message", "apps", "notify('Done', 'Your task is complete')"),
    ]
    for t in tasks:
        register_task(t)
