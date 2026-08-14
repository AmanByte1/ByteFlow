"""
ByteFlow Plugin Marketplace
============================
Backend for discovering, installing, managing, and creating plugins.

Plugins are Python modules that register AutomationTasks into the global
TaskRegistry. They can be:
  - Built-in (shipped with ByteFlow)
  - Community (loaded from a folder)
  - Custom (created by the user via the UI)

Each plugin is a single .py file with:
  - PLUGIN_META dict at the top (name, author, desc, tags, version, icon)
  - register() function that adds tasks to the registry
"""

from __future__ import annotations
import os
import sys
import json
import importlib.util
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


# ── Plugin metadata ────────────────────────────────────────────────────────────
@dataclass
class PluginMeta:
    id: str
    name: str
    description: str
    author: str = "Unknown"
    version: str = "1.0.0"
    icon: str = "🧩"
    tags: list[str] = field(default_factory=list)
    downloads: int = 0
    rating: float = 5.0
    installed: bool = False
    enabled: bool = True
    path: Optional[str] = None
    created: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ── Plugin registry ────────────────────────────────────────────────────────────
class PluginMarketplace:
    """
    Manages ByteFlow plugins:
    - Discover plugins in the plugins/ folder
    - Install/uninstall/enable/disable plugins
    - Load plugins into the task registry
    - Create new plugins from user-provided code
    - Persist installed state to plugins.json
    """

    PLUGINS_DIR = Path(__file__).parent / "plugins"
    STATE_FILE = Path(__file__).parent / "plugins.json"

    # Built-in plugin catalog (simulates a marketplace)
    CATALOG: list[dict] = [
        {
            "id": "weather", "name": "Weather", "icon": "🌤️",
            "author": "ByteFlow Team", "version": "1.2.0",
            "description": "Get real-time weather for any city. Ask 'weather in Tokyo' or 'is it raining?'",
            "tags": ["utility", "api"], "downloads": 1247, "rating": 4.8,
        },
        {
            "id": "github_tools", "name": "GitHub Tools", "icon": "🐙",
            "author": "ByteFlow Team", "version": "2.0.1",
            "description": "Manage repos, issues, PRs, and gists. Requires GITHUB_TOKEN env var.",
            "tags": ["devtools", "git"], "downloads": 3412, "rating": 4.9,
        },
        {
            "id": "notes", "name": "Quick Notes", "icon": "📝",
            "author": "ByteFlow Team", "version": "1.0.3",
            "description": "Persistent note-taking with tags, search, and markdown. Notes survive restarts.",
            "tags": ["productivity"], "downloads": 2134, "rating": 4.7,
        },
        {
            "id": "pomodoro", "name": "Pomodoro Timer", "icon": "🍅",
            "author": "Community", "version": "1.1.0",
            "description": "Built-in Pomodoro timer with desktop notifications and session tracking.",
            "tags": ["productivity", "timer"], "downloads": 892, "rating": 4.6,
        },
        {
            "id": "sysmon", "name": "System Monitor", "icon": "📊",
            "author": "ByteFlow Team", "version": "1.3.0",
            "description": "Real-time CPU, memory, disk, and network monitoring with history.",
            "tags": ["system", "monitoring"], "downloads": 2201, "rating": 4.9,
        },
        {
            "id": "snippets", "name": "Code Snippets", "icon": "✂️",
            "author": "ByteFlow Team", "version": "1.0.0",
            "description": "Save, search, and insert code snippets. Supports 30+ languages.",
            "tags": ["devtools", "productivity"], "downloads": 1521, "rating": 4.8,
        },
        {
            "id": "translate", "name": "Translator", "icon": "🌐",
            "author": "Community", "version": "1.0.2",
            "description": "Translate text between 100+ languages using free LibreTranslate API.",
            "tags": ["utility", "language"], "downloads": 763, "rating": 4.4,
        },
        {
            "id": "clipboard_sync", "name": "Clipboard Sync", "icon": "📋",
            "author": "Community", "version": "1.0.0",
            "description": "Sync clipboard between phone and laptop over your local network.",
            "tags": ["utility"], "downloads": 2891, "rating": 4.5,
        },
        {
            "id": "terminal_access", "name": "Terminal Access", "icon": "⌨️",
            "author": "ByteFlow Team", "version": "2.1.0",
            "description": "Full terminal emulator in your browser. Run commands, manage processes.",
            "tags": ["devtools", "system"], "downloads": 4102, "rating": 4.9,
        },
        {
            "id": "docker_mgr", "name": "Docker Manager", "icon": "🐳",
            "author": "ByteFlow Team", "version": "1.4.0",
            "description": "Manage containers, view logs, start/stop services from your phone.",
            "tags": ["devtools", "docker"], "downloads": 1834, "rating": 4.7,
        },
    ]

    def __init__(self):
        self.PLUGINS_DIR.mkdir(exist_ok=True)
        self._state: dict[str, dict] = self._load_state()
        self._loaded: dict[str, any] = {}  # id → module

    def _load_state(self) -> dict:
        if self.STATE_FILE.exists():
            try:
                return json.loads(self.STATE_FILE.read_text())
            except Exception:
                pass
        return {}

    def _save_state(self):
        self.STATE_FILE.write_text(json.dumps(self._state, indent=2))

    # ── Catalog ────────────────────────────────────────────────────────────────

    def catalog(self, query: str = "", tag: str = "") -> list[dict]:
        """Return marketplace catalog, optionally filtered."""
        results = self.CATALOG
        if query:
            q = query.lower()
            results = [p for p in results if q in p["name"].lower() or q in p["description"].lower()]
        if tag:
            results = [p for p in results if tag in p.get("tags", [])]
        return [
            {**p, "installed": p["id"] in self._state and self._state[p["id"]].get("installed", False)}
            for p in results
        ]

    def installed(self) -> list[dict]:
        """Return all installed plugins."""
        installed = []
        for pid, state in self._state.items():
            if state.get("installed"):
                catalog_entry = next((p for p in self.CATALOG if p["id"] == pid), None)
                if catalog_entry:
                    installed.append({**catalog_entry, "installed": True, "enabled": state.get("enabled", True)})
                else:
                    # Custom plugin
                    installed.append({**state, "installed": True})
        return installed

    # ── Install / uninstall ────────────────────────────────────────────────────

    def install(self, plugin_id: str) -> dict:
        """Mark a plugin as installed and load it."""
        catalog_entry = next((p for p in self.CATALOG if p["id"] == plugin_id), None)
        if not catalog_entry:
            return {"ok": False, "error": f"Plugin '{plugin_id}' not found in catalog."}

        self._state[plugin_id] = {
            **catalog_entry,
            "installed": True,
            "enabled": True,
            "installed_at": datetime.now().isoformat(),
        }
        self._save_state()
        self._load_plugin(plugin_id)
        return {"ok": True, "message": f"Installed: {catalog_entry['name']}", "plugin": catalog_entry}

    def uninstall(self, plugin_id: str) -> dict:
        """Remove a plugin."""
        if plugin_id not in self._state:
            return {"ok": False, "error": f"Plugin '{plugin_id}' is not installed."}
        name = self._state[plugin_id].get("name", plugin_id)
        del self._state[plugin_id]
        self._loaded.pop(plugin_id, None)
        self._save_state()
        return {"ok": True, "message": f"Uninstalled: {name}"}

    def toggle(self, plugin_id: str) -> dict:
        """Enable or disable a plugin."""
        if plugin_id not in self._state:
            return {"ok": False, "error": "Not installed."}
        current = self._state[plugin_id].get("enabled", True)
        self._state[plugin_id]["enabled"] = not current
        self._save_state()
        state = "enabled" if not current else "disabled"
        return {"ok": True, "enabled": not current, "message": f"Plugin {state}."}

    # ── Custom plugin creation ─────────────────────────────────────────────────

    def create(self, name: str, description: str, code: str, author: str = "User") -> dict:
        """
        Create a new custom plugin from user-provided Python code.
        The code must define a register() function.
        """
        plugin_id = name.lower().replace(" ", "_").replace("-", "_")
        plugin_file = self.PLUGINS_DIR / f"{plugin_id}.py"

        meta = {
            "PLUGIN_META": {
                "id": plugin_id,
                "name": name,
                "description": description,
                "author": author,
                "version": "1.0.0",
                "icon": "🔧",
                "tags": ["custom"],
            }
        }

        full_code = (
            f'"""\n{name}\n{description}\nAuthor: {author}\n"""\n\n'
            f"PLUGIN_META = {json.dumps(meta['PLUGIN_META'], indent=4)}\n\n"
            f"{code}\n"
        )

        # Validate syntax
        try:
            compile(full_code, plugin_file.name, "exec")
        except SyntaxError as e:
            return {"ok": False, "error": f"Syntax error: {e}"}

        # Check register() exists
        if "def register(" not in code and "def register\n" not in code:
            return {"ok": False, "error": "Code must define a register() function that adds tasks to the registry."}

        # Save to disk
        plugin_file.write_text(full_code, encoding="utf-8")

        # Register state
        self._state[plugin_id] = {
            "id": plugin_id, "name": name, "description": description,
            "author": author, "icon": "🔧", "tags": ["custom"],
            "installed": True, "enabled": True, "path": str(plugin_file),
            "installed_at": datetime.now().isoformat(),
        }
        self._save_state()

        # Load it
        result = self._load_plugin_from_file(plugin_id, plugin_file)
        if not result["ok"]:
            return result

        return {"ok": True, "message": f"Plugin '{name}' created and loaded.", "id": plugin_id}

    # ── Loading ────────────────────────────────────────────────────────────────

    def _load_plugin(self, plugin_id: str):
        """Load a built-in or community plugin by ID."""
        plugin_file = self.PLUGINS_DIR / f"{plugin_id}.py"
        if plugin_file.exists():
            return self._load_plugin_from_file(plugin_id, plugin_file)
        # Try built-in plugins package
        try:
            builtin_path = Path(__file__).parent / "builtin_plugins" / f"{plugin_id}.py"
            if builtin_path.exists():
                return self._load_plugin_from_file(plugin_id, builtin_path)
        except Exception:
            pass
        return {"ok": True, "message": "Plugin registered (no code to load for built-in)."}

    def _load_plugin_from_file(self, plugin_id: str, path: Path) -> dict:
        """Dynamically load a plugin .py file."""
        try:
            spec = importlib.util.spec_from_file_location(f"byteflow_plugin_{plugin_id}", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "register"):
                mod.register()
            self._loaded[plugin_id] = mod
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": f"Error loading plugin: {e}"}

    def load_all_enabled(self):
        """Load all enabled installed plugins on startup."""
        for pid, state in self._state.items():
            if state.get("installed") and state.get("enabled", True):
                self._load_plugin(pid)

    def status(self) -> dict:
        return {
            "total_catalog": len(self.CATALOG),
            "installed": len([s for s in self._state.values() if s.get("installed")]),
            "enabled": len([s for s in self._state.values() if s.get("installed") and s.get("enabled", True)]),
            "loaded": len(self._loaded),
        }


# ── Global instance ────────────────────────────────────────────────────────────
_marketplace = None

def get_marketplace() -> PluginMarketplace:
    global _marketplace
    if _marketplace is None:
        _marketplace = PluginMarketplace()
    return _marketplace
