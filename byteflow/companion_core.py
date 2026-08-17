"""
ByteFlow CompanionCore
=======================
Wires ALL ByteFlow systems into the companion's agent so it can:

  - Run automation tasks (files, apps, git, docker, npm...)
  - Search and answer from the knowledge base
  - Send Telegram / Email / Slack messages
  - Watch alerts and report them proactively
  - Run and manage workflows
  - Execute terminal commands
  - Schedule tasks
  - Use persistent memory and chat history
  - Control the desktop (open apps, clipboard, notify)

Usage:
    from byteflow.companion_core import build_companion_agent
    agent = build_companion_agent(model="llama3")
    # Pass to run_companion(agent=agent)
"""

from __future__ import annotations
import os
import sys
from pathlib import Path


def build_companion_agent(model: str = "llama3", memory_path: str = None) -> "Agent":
    """
    Build a fully-wired ByteFlow Agent for the companion.
    Registers all tools from every module we built.
    """
    from byteflow.agent import Agent
    from byteflow.providers.ollama_provider import OllamaProvider
    from byteflow.builtin_tools import register_builtin_tools
    from byteflow.tools import Tool

    # Memory path
    if memory_path is None:
        memory_dir = Path.home() / ".byteflow"
        memory_dir.mkdir(exist_ok=True)
        memory_path = str(memory_dir / "memory.json")

    # Core agent
    provider = OllamaProvider(model=model)
    agent = Agent(provider=provider, memory_path=memory_path)
    register_builtin_tools(agent)

    # ── Register all automator tasks ──────────────────────────────────────────
    try:
        from byteflow_automator import Automator
        auto = Automator()

        for task in auto.registry.all():
            if task.safe:
                agent.register_tool(Tool(
                    task.name,
                    task.func,
                    task.description
                ))

        # Convenience wrappers the companion will use naturally
        def run_shortcut_by_name(name: str) -> str:
            """Run a saved shortcut macro by name."""
            from byteflow.settings import get_settings
            shortcuts = get_settings().get_shortcuts()
            sc = next((s for s in shortcuts if name.lower() in s["name"].lower()), None)
            if not sc:
                return f"No shortcut named '{name}'. Available: {[s['name'] for s in shortcuts]}"
            results = []
            for step in sc.get("steps", []):
                results.append(auto.run_task("run_command", step))
            return "\n".join(results)

        agent.register_tool(Tool(
            "run_shortcut",
            run_shortcut_by_name,
            "run a saved shortcut macro by name (e.g. 'morning routine', 'build project')"
        ))

    except ImportError:
        print("[CompanionCore] byteflow_automator not found — automation tasks unavailable")

    # ── Register desktop tools ─────────────────────────────────────────────────
    try:
        from byteflow.desktop_tools import register_desktop_tools
        register_desktop_tools(agent)
    except Exception:
        pass

    # ── Knowledge base tools ──────────────────────────────────────────────────
    try:
        from byteflow.knowledge_base import get_kb

        def kb_ask(question: str) -> str:
            """Search the knowledge base and answer a question using indexed files."""
            kb = get_kb()
            context = kb.get_context(question, top_k=3)
            if not context:
                return "No relevant content found in the knowledge base. Try indexing some files first with kb_index."
            return context + f"\n\n(Use this context to answer: {question})"

        def kb_index(path: str) -> str:
            """Index a file or folder into the knowledge base so ByteFlow can answer questions about it."""
            kb = get_kb()
            expanded = os.path.expanduser(path)
            if os.path.isdir(expanded):
                r = kb.add_folder(expanded)
                return f"Indexed {r.get('indexed',0)} files, {r.get('total_chunks',0)} chunks from {path}"
            else:
                r = kb.add_file(expanded)
                if r.get("ok"):
                    return f"Indexed {r.get('chunks',0)} chunks from {r.get('source', path)}"
                return f"Error: {r.get('error')}"

        def kb_search(query: str) -> str:
            """Search the knowledge base for content matching a query."""
            kb = get_kb()
            results = kb.search(query, top_k=3)
            if not results:
                return "Nothing found in knowledge base for that query."
            return "\n\n".join(f"[{r['source']}] {r['preview']}" for r in results)

        def kb_status() -> str:
            """Show knowledge base stats — how many files and chunks are indexed."""
            kb = get_kb()
            stats = kb.stats()
            sources = kb.sources()
            names = [s["title"] for s in sources[:10]]
            return (
                f"Knowledge base: {stats['total_sources']} sources, "
                f"{stats['total_chunks']} chunks indexed.\n"
                f"Sources: {', '.join(names) if names else 'none'}"
            )

        agent.register_tool(Tool("kb_ask", kb_ask, "answer a question using the knowledge base of indexed files"))
        agent.register_tool(Tool("kb_index", kb_index, "index a file or folder so you can answer questions about it"))
        agent.register_tool(Tool("kb_search", kb_search, "search the knowledge base for content matching a query"))
        agent.register_tool(Tool("kb_status", kb_status, "show knowledge base stats — indexed files and chunk count"))

    except Exception as e:
        print(f"[CompanionCore] KB tools unavailable: {e}")

    # ── Integration tools ──────────────────────────────────────────────────────
    try:
        from byteflow.integrations import get_integrations

        def send_telegram(message: str) -> str:
            """Send a Telegram message via the configured bot."""
            ig = get_integrations()
            r = ig.telegram.send(message)
            return "Telegram sent ✓" if r.get("ok") else f"Telegram error: {r.get('error')}"

        def send_email(to: str, subject: str, body: str) -> str:
            """Send an email. Requires EMAIL_USERNAME and EMAIL_PASSWORD env vars."""
            ig = get_integrations()
            r = ig.email.send(to, subject, body)
            return "Email sent ✓" if r.get("ok") else f"Email error: {r.get('error')}"

        def send_slack(message: str) -> str:
            """Send a Slack message via the configured webhook."""
            ig = get_integrations()
            r = ig.slack.send(message)
            return "Slack sent ✓" if r.get("ok") else f"Slack error: {r.get('error')}"

        def read_inbox(n: int = 5) -> str:
            """Read the last N emails from your inbox."""
            ig = get_integrations()
            r = ig.email.read_inbox(n)
            if not r.get("ok"):
                return f"Email error: {r.get('error')}"
            msgs = r.get("messages", [])
            if not msgs:
                return "Inbox is empty."
            return "\n\n".join(
                f"From: {m['from']}\nSubject: {m['subject']}\n{m['body'][:200]}"
                for m in msgs
            )

        def integration_status() -> str:
            """Check which integrations (Telegram, Email, Slack, WhatsApp) are configured."""
            ig = get_integrations()
            st = ig.status()
            lines = []
            for name, info in st.items():
                status = "✅ configured" if info.get("configured") else "⚠️ not configured"
                lines.append(f"{name}: {status}")
            return "\n".join(lines)

        agent.register_tool(Tool("send_telegram", send_telegram, "send a Telegram message via the configured bot"))
        agent.register_tool(Tool("send_email", send_email, "send an email — requires EMAIL_USERNAME and EMAIL_PASSWORD env vars"))
        agent.register_tool(Tool("send_slack", send_slack, "send a message to Slack via webhook"))
        agent.register_tool(Tool("read_inbox", read_inbox, "read the last N emails from your email inbox"))
        agent.register_tool(Tool("integration_status", integration_status, "check which integrations are configured and active"))

    except Exception as e:
        print(f"[CompanionCore] Integration tools unavailable: {e}")

    # ── Watcher / alerts tools ─────────────────────────────────────────────────
    try:
        from byteflow.watcher import get_watcher

        def check_alerts(n: int = 5) -> str:
            """Check for recent system alerts (disk, CPU, git, custom watches)."""
            w = get_watcher()
            alerts = w.get_alerts(unread_only=False, limit=n)
            if not alerts:
                return "No alerts — all systems look good."
            w.mark_read()
            return "\n".join(
                f"[{a['level'].upper()}] {a['title']}: {a['body']}"
                for a in alerts
            )

        def check_disk(path: str = "/") -> str:
            """Check disk usage for a given path."""
            import shutil
            try:
                usage = shutil.disk_usage(os.path.expanduser(path))
                pct = (usage.used / usage.total) * 100
                free_gb = usage.free / 1e9
                return f"Disk {path}: {pct:.1f}% used, {free_gb:.1f} GB free"
            except Exception as e:
                return f"Error: {e}"

        def watch_file(path: str) -> str:
            """Start watching a file for changes and alert when it's modified."""
            w = get_watcher()
            rule_id = f"file_{path.replace('/', '_')}"
            w.add_rule(rule_id, f"Watch {path}", "file", {"path": path}, interval=10)
            return f"Now watching '{path}' for changes. I'll alert you when it's modified."

        agent.register_tool(Tool("check_alerts", check_alerts, "check for recent system alerts — disk, CPU, git, custom watches"))
        agent.register_tool(Tool("check_disk", check_disk, "check disk usage for a given path"))
        agent.register_tool(Tool("watch_file", watch_file, "start watching a file and alert when it changes"))

    except Exception as e:
        print(f"[CompanionCore] Watcher tools unavailable: {e}")

    # ── Workflow tools ─────────────────────────────────────────────────────────
    try:
        from byteflow.workflows import get_workflow_engine

        def list_workflows() -> str:
            """List all automation workflows and their status."""
            eng = get_workflow_engine()
            wfs = eng.all()
            if not wfs:
                return "No workflows configured yet."
            lines = []
            for wf in wfs:
                status = "✅ enabled" if wf["enabled"] else "⏸ disabled"
                lines.append(f"• {wf['name']} ({status}) — runs: {wf['run_count']}")
            return "\n".join(lines)

        def run_workflow(name: str) -> str:
            """Run a workflow by name immediately."""
            eng = get_workflow_engine()
            wfs = eng.all()
            match = next((wf for wf in wfs if name.lower() in wf["name"].lower()), None)
            if not match:
                return f"No workflow named '{name}'. Use list_workflows to see all."
            r = eng.trigger_now(match["workflow_id"])
            return f"Workflow '{match['name']}' ran: {'; '.join(r.get('results', []))}"

        agent.register_tool(Tool("list_workflows", list_workflows, "list all automation workflows and their status"))
        agent.register_tool(Tool("run_workflow", run_workflow, "run a workflow by name immediately"))

    except Exception as e:
        print(f"[CompanionCore] Workflow tools unavailable: {e}")

    # ── Settings tools ─────────────────────────────────────────────────────────
    try:
        from byteflow.settings import get_settings

        def get_setting(key: str) -> str:
            """Get a ByteFlow setting value."""
            s = get_settings()
            val = s.get(key)
            return f"{key} = {val}" if val is not None else f"Unknown setting: {key}"

        def set_setting(key: str, value: str) -> str:
            """Change a ByteFlow setting (model, theme, voice_enabled, etc)."""
            s = get_settings()
            # Auto-cast common types
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            r = s.set(key, value)
            return f"Setting updated: {key} = {value}" if r.get("ok") else r.get("error")

        def list_shortcuts() -> str:
            """List all saved shortcut macros."""
            s = get_settings()
            shortcuts = s.get_shortcuts()
            if not shortcuts:
                return "No shortcuts saved yet."
            return "\n".join(f"• {sc['icon']} {sc['name']}: {len(sc['steps'])} steps" for sc in shortcuts)

        agent.register_tool(Tool("get_setting", get_setting, "get a ByteFlow setting value by key"))
        agent.register_tool(Tool("set_setting", set_setting, "change a ByteFlow setting (model, theme, voice_enabled, etc)"))
        agent.register_tool(Tool("list_shortcuts", list_shortcuts, "list all saved shortcut macros"))
        agent.register_tool(Tool("run_shortcut", run_shortcut_by_name if 'run_shortcut_by_name' in dir() else lambda n: "automator not available", "run a shortcut macro by name"))

    except Exception as e:
        print(f"[CompanionCore] Settings tools unavailable: {e}")

    # ── Chat history tools ─────────────────────────────────────────────────────
    try:
        from byteflow.chat_history import get_history

        def search_history(query: str) -> str:
            """Search past conversations for a topic or keyword."""
            h = get_history()
            results = h.search(query, limit=5)
            if not results:
                return f"Nothing found in history for '{query}'."
            return "\n\n".join(
                f"[{r['session_title']}] {r['message']['role']}: {r['message']['content'][:200]}"
                for r in results
            )

        def history_stats() -> str:
            """Show chat history statistics."""
            h = get_history()
            stats = h.stats()
            return (
                f"Chat history: {stats['total_sessions']} sessions, "
                f"{stats['total_messages']} total messages, "
                f"{stats['active_messages']} in current session."
            )

        agent.register_tool(Tool("search_history", search_history, "search past conversations for a topic or keyword"))
        agent.register_tool(Tool("history_stats", history_stats, "show chat history statistics"))

    except Exception as e:
        print(f"[CompanionCore] History tools unavailable: {e}")

    # ── System personality prompt ─────────────────────────────────────────────
    try:
        system_prompt = """You are ByteFlow, an intelligent desktop AI companion.

You have access to powerful tools to help the user:
- Run shell commands and scripts
- Open apps, files, and websites  
- Manage files (read, write, search, organize)
- Use Git, pip, npm, Docker
- Search and answer from the user's knowledge base (indexed docs)
- Send messages via Telegram, Email, Slack
- Check system alerts and disk usage
- Run automation workflows
- Remember past conversations
- Use shortcuts/macros for repeated tasks

Be proactive: if asked to do something, use the appropriate tool.
Be concise: short answers for simple tasks, detailed for complex ones.
Be helpful: suggest relevant tools the user might not know about.

When you run a tool, tell the user what you did and show the result."""

        if hasattr(agent, 'set_system_prompt'):
            agent.set_system_prompt(system_prompt)
        elif hasattr(agent, 'system_prompt'):
            agent.system_prompt = system_prompt

    except Exception:
        pass

    return agent


def run_full_companion(model: str = "llama3", **kwargs):
    """
    Launch the companion with all ByteFlow systems connected.
    Drop-in replacement for run_companion().
    """
    from byteflow.companion import run_companion

    print(f"[ByteFlow] Building companion with all systems (model: {model})...")
    agent = build_companion_agent(model=model)
    print(f"[ByteFlow] Agent ready with {len(agent._tools) if hasattr(agent,'_tools') else '?'} tools")
    print(f"[ByteFlow] Starting companion window...")
    run_companion(agent=agent, **kwargs)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="ByteFlow Full Companion")
    p.add_argument("--model", default="llama3")
    p.add_argument("--voice-output", action="store_true")
    p.add_argument("--voice-input", action="store_true")
    args = p.parse_args()
    run_full_companion(
        model=args.model,
        voice_output=args.voice_output,
        voice_input=args.voice_input,
    )
