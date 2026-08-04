from __future__ import annotations

import os
import platform
import subprocess
import webbrowser


SHORTCUTS = {
    "calculator": "calc",
    "calc": "calc",
    "notepad": "notepad",
    "paint": "mspaint",
    "explorer": "explorer",
    "files": "explorer",
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "vscode": "code",
    "code": "code",
}


class ActionRunner:
    def run(self, command: str) -> str:
        command = command.strip()
        if not command:
            return "No command to run."

        lowered = command.lower()
        if lowered.startswith("open "):
            return self.open_target(command[5:].strip())
        if lowered.startswith("launch "):
            return self.open_target(command[7:].strip())
        if lowered.startswith("click "):
            return self.click_at(command[6:].strip())
        if lowered.startswith("say "):
            return command[4:].strip() or "..."

        return (
            "Unknown action. Use commands like 'open calculator', "
            "'click 500 300', or 'say hello'."
        )

    def open_target(self, target: str) -> str:
        if not target:
            return "Tell me what to open."
        resolved = SHORTCUTS.get(target.lower().replace(" ", ""), target)
        if resolved.startswith(("http://", "https://")):
            webbrowser.open(resolved)
            return f"Opened {target}."

        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(resolved)  # type: ignore[attr-defined]
            elif system == "Darwin":
                subprocess.Popen(["open", resolved])
            else:
                subprocess.Popen(["xdg-open", resolved])
            return f"Opened {target}."
        except Exception as exc:
            return f"Could not open {target}: {exc}"

    def click_at(self, args: str) -> str:
        pieces = args.replace(",", " ").split()
        if len(pieces) != 2:
            return "Use click like: click 500 300"
        try:
            x, y = int(pieces[0]), int(pieces[1])
        except ValueError:
            return "Click coordinates must be numbers."

        try:
            import pyautogui
        except ImportError:
            return "Install pyautogui to enable clicking: pip install pyautogui"

        pyautogui.click(x, y)
        return f"Clicked at {x}, {y}."
