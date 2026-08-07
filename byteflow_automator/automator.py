"""
Automator
=========
The main entry point for ByteFlow Automator.

Bridges the ByteFlow Agent (brain) to all registered automation tasks.
The Agent does the planning and reasoning - this does the executing.

Design:
  - ByteFlow stays lightweight: no automation logic lives in the core
  - Automator wraps a ByteFlow Agent internally for planning
  - All tasks live in sub-modules and register into TaskRegistry
  - Automator.run(goal) → Agent plans → Automator executes → returns result

Usage:
    from byteflow_automator import Automator

    # Standalone (no LLM, direct task calls only)
    auto = Automator()
    auto.run_task("git_status", "~/myproject")

    # With ByteFlow brain (natural language goals)
    from byteflow.providers.ollama_provider import OllamaProvider
    provider = OllamaProvider(model="llama2")
    auto = Automator(provider=provider)
    result = auto.run("open vscode and show git status of ~/myproject")
"""

from __future__ import annotations
import sys
import os
from typing import Any, Optional

from .registry import TaskRegistry, get_registry, AutomationTask


class Automator:
    """
    General-purpose desktop automation, directed by the ByteFlow brain.

    Keeps ByteFlow's Agent lightweight by handling all automation
    execution in this separate layer. The Agent plans; the Automator acts.
    """

    def __init__(self, provider=None, auto_register: bool = True):
        """
        provider: a ByteFlow-compatible LLM provider for natural language planning.
                  If None, only direct task calls (run_task) work.
        auto_register: if True (default), automatically import and register
                       all built-in task modules on startup.
        """
        self.provider = provider
        self.registry: TaskRegistry = get_registry()
        self._agent = None          # lazy-loaded ByteFlow Agent
        self._history: list[dict] = []  # execution history

        if auto_register:
            self._register_all()

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _register_all(self):
        """Import all task modules and register their tasks."""
        modules_to_register = [
            "byteflow_automator.tasks.files",
            "byteflow_automator.tasks.apps",
            "byteflow_automator.devtools.dev",
            "byteflow_automator.system.system",
        ]
        for mod_path in modules_to_register:
            try:
                import importlib
                mod = importlib.import_module(mod_path)
                if hasattr(mod, "register"):
                    mod.register()
            except ImportError as e:
                print(f"[Automator] Warning: could not load {mod_path}: {e}", file=sys.stderr)

    def _get_agent(self):
        """Lazily create a ByteFlow Agent for planning (only if provider is set)."""
        if self._agent is not None:
            return self._agent
        if not self.provider:
            return None
        try:
            # Import ByteFlow's Agent - it lives in the parent project
            # This import works because byteflow_automator lives inside the ByteFlow project
            from byteflow.agent import Agent
            from byteflow.tools import Tool

            self._agent = Agent(provider=self.provider, memory_path=False, learn=False)

            # Register all automation tasks as ByteFlow Tools on the agent
            for task in self.registry.all():
                self._agent.register_tool(Tool(task.name, task.func, task.description))

            return self._agent
        except ImportError:
            print("[Automator] Warning: byteflow.agent not found. Natural language planning disabled.", file=sys.stderr)
            return None

    # ── Direct task execution ──────────────────────────────────────────────────

    def run_task(self, name: str, *args, **kwargs) -> Any:
        """
        Execute an automation task directly by name.

        Example:
            auto.run_task("git_status", "~/myproject")
            auto.run_task("pip_install", "requests")
        """
        task = self.registry.get(name)
        if not task:
            available = ", ".join(self.registry.names()[:10]) + " ..."
            return f"Error: task '{name}' not found. Available: {available}"

        result = task.run(*args, **kwargs)
        self._log(name, args, kwargs, result)
        return result

    # ── Natural language execution ─────────────────────────────────────────────

    def run(self, goal: str) -> str:
        """
        Execute an automation goal described in natural language.
        The ByteFlow Agent plans which tasks to call and in what order.

        Requires a provider to be set.

        Example:
            auto.run("open vscode in ~/myproject and show git status")
            auto.run("install requests and flask, then run main.py")
        """
        agent = self._get_agent()
        if not agent:
            return (
                "Error: no provider set. Pass a ByteFlow provider to Automator(provider=...) "
                "for natural language automation, or use run_task() for direct calls."
            )

        # Build an enriched goal with task context
        task_summary = self.registry.summary()
        enriched_goal = (
            f"You are an automation assistant. Use the available tools to accomplish this goal:\n"
            f"GOAL: {goal}\n\n"
            f"AVAILABLE AUTOMATION TASKS:\n{task_summary}\n\n"
            f"Plan and execute the minimum steps needed. Be concise."
        )

        try:
            plan = agent.plan(enriched_goal)
            if plan:
                return self._execute_plan(plan, goal)
            # Fallback to chat if no plan was generated
            return agent.chat(goal)
        except Exception as e:
            return f"Automation error: {e}"

    def _execute_plan(self, plan: str, original_goal: str) -> str:
        """Parse and execute a plan returned by the ByteFlow brain."""
        import re
        results = []

        # Try to find tool calls in the plan: tool_name(args...)
        calls = re.findall(r'(\w+)\(([^)]*)\)', plan)

        if not calls:
            # No parseable calls - just return the plan text
            return f"Plan:\n{plan}"

        for func_name, args_str in calls:
            task = self.registry.get(func_name)
            if not task:
                continue

            # Parse args - simple CSV, handles quoted strings
            try:
                import ast
                args = [ast.literal_eval(a.strip()) for a in args_str.split(",") if a.strip()]
            except Exception:
                args = [a.strip().strip("'\"") for a in args_str.split(",") if a.strip()]

            # Safety check - confirm before destructive ops
            if not task.safe:
                results.append(f"[{func_name}] Skipped: requires human confirmation (safe=False). Call run_task('{func_name}', ...) directly.")
                continue

            result = task.run(*args)
            self._log(func_name, args, {}, result)
            results.append(f"[{func_name}] {result}")

        if not results:
            return f"No executable tasks found in plan. Plan was:\n{plan}"

        return "\n\n".join(results)

    # ── Convenience shortcuts ──────────────────────────────────────────────────

    def open(self, target: str) -> str:
        """Shortcut: open an app, file, or URL."""
        return self.run_task("open_app", target)

    def edit(self, path: str, editor: str = "vscode") -> str:
        """Shortcut: open a file or folder in a code editor."""
        return self.run_task("open_in_editor", path, editor)

    def git(self, command: str, repo: str = ".") -> str:
        """Shortcut: run a named git operation (status, log, pull, diff, branch)."""
        task_map = {
            "status": "git_status",
            "log": "git_log",
            "pull": "git_pull",
            "diff": "git_diff",
            "branch": "git_branch",
        }
        task_name = task_map.get(command.lower(), f"git_{command.lower()}")
        return self.run_task(task_name, repo)

    def shell(self, command: str, cwd: str = None) -> str:
        """Shortcut: run a shell command."""
        return self.run_task("run_command", command, cwd)

    def install(self, package: str, manager: str = "pip") -> str:
        """Shortcut: install a package with pip or npm."""
        if manager == "pip":
            return self.run_task("pip_install", package)
        elif manager == "npm":
            return self.run_task("npm_install", package)
        return f"Unknown package manager: {manager}"

    def new_project(self, name: str, kind: str = "python", path: str = "~") -> str:
        """Shortcut: scaffold a new Python or Node project."""
        task = "scaffold_python_project" if kind == "python" else "scaffold_node_project"
        return self.run_task(task, name, path)

    # ── Info / introspection ───────────────────────────────────────────────────

    def list_tasks(self, category: str = None) -> list[str]:
        """List all available automation task names."""
        if category:
            return [t.name for t in self.registry.by_category(category)]
        return self.registry.names()

    def describe_task(self, name: str) -> str:
        """Get the description and example usage of a task."""
        task = self.registry.get(name)
        if not task:
            return f"No task named '{name}'"
        lines = [
            f"Task: {task.name}",
            f"Category: {task.category}",
            f"Description: {task.description}",
            f"Safe: {task.safe}",
        ]
        if task.example:
            lines.append(f"Example: {task.example}")
        return "\n".join(lines)

    def capabilities(self) -> str:
        """Return a formatted summary of all automation capabilities."""
        return (
            f"ByteFlow Automator — {len(self.registry)} tasks loaded\n"
            + self.registry.summary()
        )

    # ── History ────────────────────────────────────────────────────────────────

    def _log(self, name: str, args, kwargs, result):
        from datetime import datetime
        self._history.append({
            "time": datetime.now().isoformat(),
            "task": name,
            "args": args,
            "kwargs": kwargs,
            "result": str(result)[:500],
        })

    def history(self, n: int = 20) -> list[dict]:
        """Return the last N automation executions."""
        return self._history[-n:]

    def clear_history(self):
        """Clear the execution history."""
        self._history.clear()
