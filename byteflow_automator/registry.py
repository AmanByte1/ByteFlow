"""
TaskRegistry
============
Central registry for all automation tasks in byteflow_automator.
Tasks register themselves here; the Automator queries this to build
the tool list it sends to the ByteFlow brain for planning.

Design principle: the ByteFlow Agent's brain does the thinking.
The registry just knows *what* tasks exist and how to call them.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any, Optional


@dataclass
class AutomationTask:
    """A single automation capability."""
    name: str
    func: Callable
    description: str
    category: str            # "files" | "apps" | "devtools" | "system" | "shell" | "browser"
    example: str = ""        # e.g. "open vscode -> open_app('vscode')"
    safe: bool = True        # False = needs user confirmation before running
    args_schema: dict = field(default_factory=dict)  # {arg_name: description}

    def run(self, *args, **kwargs) -> Any:
        try:
            return self.func(*args, **kwargs)
        except Exception as e:
            return f"[AutomationTask Error - {self.name}]: {e}"

    def describe(self) -> str:
        """Short description for the planner prompt."""
        desc = f"{self.name}: {self.description}"
        if self.example:
            desc += f" (e.g. {self.example})"
        if not self.safe:
            desc += " [requires confirmation]"
        return desc


class TaskRegistry:
    """
    Holds all registered AutomationTask instances.
    Supports filtering by category, safety, and name lookup.
    """

    def __init__(self):
        self._tasks: dict[str, AutomationTask] = {}

    def register(self, task: AutomationTask):
        self._tasks[task.name] = task

    def get(self, name: str) -> Optional[AutomationTask]:
        return self._tasks.get(name)

    def all(self) -> list[AutomationTask]:
        return list(self._tasks.values())

    def by_category(self, category: str) -> list[AutomationTask]:
        return [t for t in self._tasks.values() if t.category == category]

    def safe_only(self) -> list[AutomationTask]:
        return [t for t in self._tasks.values() if t.safe]

    def names(self) -> list[str]:
        return list(self._tasks.keys())

    def summary(self) -> str:
        """Human-readable list of all tasks, grouped by category."""
        by_cat: dict[str, list[AutomationTask]] = {}
        for task in self._tasks.values():
            by_cat.setdefault(task.category, []).append(task)

        lines = []
        for cat in sorted(by_cat):
            lines.append(f"\n[{cat.upper()}]")
            for t in by_cat[cat]:
                lines.append(f"  {t.describe()}")
        return "\n".join(lines)

    def __len__(self):
        return len(self._tasks)

    def __contains__(self, name: str):
        return name in self._tasks


# Global registry instance - all task modules import and use this
_global_registry = TaskRegistry()


def get_registry() -> TaskRegistry:
    return _global_registry


def register_task(task: AutomationTask):
    """Convenience function to register into the global registry."""
    _global_registry.register(task)
