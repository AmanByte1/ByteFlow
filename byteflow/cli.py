import os
import click
from .agent import Agent, DEFAULT_PERSONALITY
from .providers.ollama_provider import OllamaProvider
from .builtin_tools import register_builtin_tools
from .desktop_tools import register_desktop_tools, launch, list_shortcuts

DEFAULT_MEMORY_PATH = os.path.join(
    os.path.expanduser("~"), ".byteflow", "memory.json"
)


def _ensure_memory_dir(path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


@click.group()
def cli():
    """
    ByteFlow - a lightweight, fully offline AI agent framework powered by Ollama.

    \b
    Common commands:
      byteflow run "add 10 and 20"              tools + chat fallback
      byteflow code "write a prime checker"     generate & run Python
      byteflow chat "explain recursion"         plain conversation
      byteflow memory --search "my dog"         search past conversations
      byteflow profile                          see what it's learned about you
      byteflow tune my-buddy                    bake facts into a real Ollama model
      byteflow post "launching my project"      draft + stage a social post
      byteflow open youtube                     open an app/site by shortcut name
      byteflow companion                        launch the desktop robot character
      byteflow companion --voice                ...with voice input/output (offline)

    \b
    Run any command with --help for its full options, e.g.:
      byteflow run --help
    """
    pass


@cli.command()
@click.argument("request")
@click.option("--model", default="llama3", help="Ollama model name to use.")
@click.option(
    "--memory-path",
    default=DEFAULT_MEMORY_PATH,
    help="Path to persistent memory JSON file. Use 'none' to disable persistence.",
)
@click.option(
    "--execute/--no-execute",
    default=True,
    help="Run the generated code in a sandboxed subprocess and show its output (default: on).",
)
@click.option("--timeout", default=10, help="Execution timeout in seconds.")
@click.option(
    "--no-learn",
    is_flag=True,
    help="Don't extract durable facts from this exchange into the profile.",
)
def code(request, model, memory_path, execute, timeout, no_learn):
    """Coding mode: generate (and by default run) Python code for a request."""
    memory_path = None if memory_path.lower() == "none" else memory_path
    if memory_path:
        _ensure_memory_dir(memory_path)

    agent = Agent(provider=OllamaProvider(model=model), memory_path=memory_path, learn=not no_learn)

    result = agent.code(request, execute=execute, timeout=timeout)

    click.echo("=== CODE ===")
    click.echo(result["code"])

    if result["executed"]:
        click.echo("")
        click.echo("=== EXECUTION ===")
        click.echo(result["result"].format())
        if not result["result"].success:
            click.echo("")
            click.echo("(The code ran but did not finish successfully - see errors above.)")


@cli.command()
@click.argument("prompt")
@click.option("--model", default="llama3", help="Ollama model name to use.")
@click.option(
    "--memory-path",
    default=DEFAULT_MEMORY_PATH,
    help="Path to persistent memory JSON file. Use 'none' to disable persistence.",
)
@click.option(
    "--no-builtin-tools",
    is_flag=True,
    help="Don't register the built-in arithmetic tools (add/subtract/multiply/divide).",
)
@click.option(
    "--enable-desktop-tools",
    is_flag=True,
    help="Register desktop helper tools (launch apps/files, list/search folders, "
         "clipboard, organize files). Off by default - these can touch your filesystem.",
)
def run(prompt, model, memory_path, no_builtin_tools, enable_desktop_tools):
    """Run the ByteFlow agent (planner + tools, falls back to chat)."""
    memory_path = None if memory_path.lower() == "none" else memory_path
    if memory_path:
        _ensure_memory_dir(memory_path)

    agent = Agent(provider=OllamaProvider(model=model), memory_path=memory_path)
    if not no_builtin_tools:
        register_builtin_tools(agent)
    if enable_desktop_tools:
        register_desktop_tools(agent)

    result = agent.run(prompt)

    if isinstance(result, dict) and "code" in result:
        # run() routed this to code mode
        click.echo("=== CODE ===")
        click.echo(result["code"])
        if result["executed"]:
            click.echo("")
            click.echo("=== EXECUTION ===")
            click.echo(result["result"].format())
            if not result["result"].success:
                click.echo("")
                click.echo("(The code ran but did not finish successfully - see errors above.)")
    else:
        click.echo("=== OUTPUT ===")
        click.echo(str(result))


@cli.command()
@click.argument("message")
@click.option("--model", default="llama3", help="Ollama model name to use.")
@click.option(
    "--memory-path",
    default=DEFAULT_MEMORY_PATH,
    help="Path to persistent memory JSON file. Use 'none' to disable persistence.",
)
@click.option(
    "--no-personality",
    is_flag=True,
    help="Disable the default mentor/companion personality (neutral assistant instead).",
)
@click.option(
    "--no-learn",
    is_flag=True,
    help="Don't extract durable facts from this conversation into the profile.",
)
def chat(message, model, memory_path, no_personality, no_learn):
    """Chat directly with the agent (general Q&A, code help, explanations)."""
    memory_path = None if memory_path.lower() == "none" else memory_path
    if memory_path:
        _ensure_memory_dir(memory_path)

    agent = Agent(provider=OllamaProvider(model=model), memory_path=memory_path, learn=not no_learn)
    if no_personality:
        agent.personality = None

    response = agent.chat(message)

    click.echo(response)


@cli.command()
@click.option(
    "--memory-path",
    default=DEFAULT_MEMORY_PATH,
    help="Path to persistent memory JSON file (used to derive the default profile path).",
)
@click.option(
    "--profile-path",
    default=None,
    help="Path to profile JSON file directly. Overrides --memory-path derivation.",
)
@click.option("--clear", is_flag=True, help="Clear the stored profile (forget everything learned).")
@click.option("--forget", default=None, help="Remove a specific fact (exact or close text match).")
def profile(memory_path, profile_path, clear, forget):
    """Inspect, clear, or edit ByteFlow's learned profile (durable facts about you)."""
    from .profile import Profile

    if profile_path is None:
        base, ext = memory_path.rsplit(".", 1) if "." in memory_path else (memory_path, "json")
        profile_path = f"{base}_profile.{ext}"

    prof = Profile(path=profile_path)

    if clear:
        prof.clear()
        click.echo(f"Cleared profile at {profile_path}")
        return

    if forget:
        removed = prof.remove_fact(forget)
        click.echo("Removed." if removed else "No matching fact found.")
        return

    click.echo(prof.format())


@cli.command()
@click.option(
    "--memory-path",
    default=DEFAULT_MEMORY_PATH,
    help="Path to persistent memory JSON file.",
)
@click.option("--clear", is_flag=True, help="Clear stored memory.")
@click.option("--n", default=10, help="Number of recent entries to show.")
@click.option(
    "--search",
    default=None,
    help="Semantically search memory for entries relevant to this text, "
         "instead of showing the most recent ones.",
)
def memory(memory_path, clear, n, search):
    """Inspect, search, or clear ByteFlow's persistent memory."""
    from .memory import Memory

    mem = Memory(path=memory_path)

    if clear:
        mem.clear()
        click.echo(f"Cleared memory at {memory_path}")
        return

    if search:
        results = mem.search(search, top_k=n)
        if not results:
            click.echo("(no relevant memory found)")
            return
        for entry, score in results:
            click.echo(f"[{score:.3f}] [{entry.get('timestamp', '?')}] {entry['role']}: {entry['content']}")
        return

    entries = mem.get_recent(n)
    if not entries:
        click.echo("(no memory stored yet)")
        return

    for e in entries:
        click.echo(f"[{e.get('timestamp', '?')}] {e['role']}: {e['content']}")


@cli.command()
@click.argument("model_name")
@click.option("--base-model", default="llama3", help="Existing Ollama model to build on.")
@click.option(
    "--memory-path",
    default=DEFAULT_MEMORY_PATH,
    help="Path to memory JSON file (used to derive the default profile path).",
)
@click.option(
    "--profile-path",
    default=None,
    help="Path to profile JSON file directly. Overrides --memory-path derivation.",
)
@click.option(
    "--no-personality",
    is_flag=True,
    help="Don't bake in the default mentor/companion personality.",
)
@click.option(
    "--instructions",
    default=None,
    help="Extra free-text instructions to bake into the model's system prompt.",
)
def tune(model_name, base_model, memory_path, profile_path, no_personality, instructions):
    """
    Bake your learned profile facts and personality into a real, new,
    named local Ollama model (deliberate, manual - run this yourself
    when you want to, not automatically).

    This does NOT change the base model's weights - it creates a new
    Ollama model (via `ollama create`) that wraps the base model with a
    permanent system prompt containing what ByteFlow has learned about
    you. Afterwards you can run it directly with `ollama run <model_name>`,
    or point ByteFlow's --model option at it.

    Requires the `ollama` CLI to be installed and on your PATH.
    """
    from .tune import create_tuned_model, TuneError, ollama_available
    from .profile import Profile

    if not ollama_available():
        click.echo(
            "Error: the 'ollama' command was not found on your PATH.\n"
            "Install Ollama (https://ollama.com) to use this command."
        )
        raise SystemExit(1)

    if profile_path is None:
        base, ext = memory_path.rsplit(".", 1) if "." in memory_path else (memory_path, "json")
        profile_path = f"{base}_profile.{ext}"

    prof = Profile(path=profile_path)
    facts = prof.all_facts()

    if not facts:
        click.echo(
            f"No learned facts found at {profile_path}.\n"
            "Chat with ByteFlow a bit first (facts are extracted automatically), "
            "or pass --profile-path to point at a different profile."
        )
        raise SystemExit(1)

    personality = None if no_personality else DEFAULT_PERSONALITY

    click.echo(f"Building '{model_name}' from base model '{base_model}' with {len(facts)} learned fact(s)...")

    try:
        modelfile_path = create_tuned_model(
            model_name=model_name,
            base_model=base_model,
            profile_facts=facts,
            personality=personality,
            extra_instructions=instructions,
        )
    except TuneError as e:
        click.echo(f"Error: {e}")
        raise SystemExit(1)

    click.echo(f"Done. Modelfile written to {modelfile_path}")
    click.echo(f"Model '{model_name}' created. Try it with: ollama run {model_name}")


@cli.command()
@click.argument("topic")
@click.option(
    "--platform",
    default="linkedin",
    help="Target platform (linkedin, twitter, x, facebook). Determines the URL opened.",
)
@click.option("--tone", default=None, help="Optional tone guidance, e.g. 'excited', 'professional', 'casual'.")
@click.option("--model", default="llama3", help="Ollama model name to use.")
@click.option(
    "--no-open",
    is_flag=True,
    help="Just draft and copy to clipboard - don't open the platform site.",
)
def post(topic, platform, tone, model, no_open):
    """
    Draft a social media post and stage it for you to publish yourself.

    This NEVER posts automatically. It drafts text with the LLM, copies
    it to your clipboard, and opens the platform's compose page - you
    paste, review, and click Post yourself. There is no browser
    automation and no auto-publishing, by design.
    """
    agent = Agent(provider=OllamaProvider(model=model), memory_path=None)

    result = agent.draft_social_post(topic, platform=platform, tone=tone, open_site=not no_open)

    if result["draft"] is None:
        click.echo(f"Error: {result['warning']}")
        raise SystemExit(1)

    click.echo("=== DRAFT ===")
    click.echo(result["draft"])
    click.echo("")

    if result["clipboard"]:
        click.echo("Copied to clipboard.")
    else:
        click.echo("Could NOT copy to clipboard - is 'pyperclip' installed? Run: pip install pyperclip")
        click.echo("(Or: pip install byteflow[clipboard])")
        click.echo("Copy the draft text above manually instead.")

    click.echo("")

    if not no_open:
        if result["launched"]:
            click.echo(f"Opened {platform} in your browser.")
            click.echo("ByteFlow does NOT type or paste anything for you - that's a deliberate safety choice.")
            click.echo("Next steps:")
            click.echo("  1. Click into the post text box on the page that just opened")
            click.echo("  2. Press Ctrl+V to paste (the draft is on your clipboard)")
            click.echo("  3. Review it, then click Post yourself")
        elif result["platform_url"]:
            click.echo(f"Could not open the browser automatically. Go to: {result['platform_url']}")
            click.echo("Then click into the post box, paste (Ctrl+V), review, and post.")
        else:
            click.echo(f"Unknown platform '{platform}' - no URL to open. Supported: linkedin, twitter, x, facebook.")


@cli.command(name="open")
@click.argument("target", required=False)
@click.option("--list", "show_list", is_flag=True, help="List all known shortcut names instead of opening anything.")
def open_(target, show_list):
    """
    Open an app, file, URL, or shortcut directly - no LLM call needed.

    \b
    TARGET can be:
      - a shortcut name, e.g. youtube, spotify, gmail, vscode, calculator
      - a raw URL, e.g. https://example.com
      - a file path
      - an app name your OS already knows, e.g. notepad

    \b
    Examples:
      byteflow open youtube
      byteflow open https://example.com
      byteflow open C:\\Users\\me\\Documents\\notes.txt
      byteflow open --list
    """
    if show_list:
        click.echo("Known shortcuts:")
        for name in list_shortcuts():
            click.echo(f"  {name}")
        return

    if not target:
        click.echo("Usage: byteflow open <target>")
        click.echo("Run 'byteflow open --list' to see known shortcut names.")
        return

    click.echo(launch(target))


@cli.command()
@click.option("--model", default="llama3", help="Ollama model name to use.")
@click.option(
    "--memory-path",
    default=DEFAULT_MEMORY_PATH,
    help="Path to persistent memory JSON file. Use 'none' to disable persistence.",
)
@click.option(
    "--no-desktop-tools",
    is_flag=True,
    help="Don't register desktop helper tools (launch/files/clipboard/organize) on the companion's agent.",
)
@click.option(
    "--voice-input",
    is_flag=True,
    help="Add a push-to-talk microphone button (requires 'vosk'+'sounddevice' and a downloaded model).",
)
@click.option(
    "--voice-output",
    is_flag=True,
    help="Speak replies aloud using your OS's built-in voice (requires 'pyttsx3').",
)
@click.option(
    "--voice",
    is_flag=True,
    help="Shortcut for --voice-input --voice-output.",
)
@click.option(
    "--conversation-mode",
    is_flag=True,
    help="Hands-free continuous listening - auto-detects when you start/stop talking, "
         "no clicking per utterance (requires 'vosk'+'sounddevice' and a downloaded model).",
)
def companion(model, memory_path, no_desktop_tools, voice_input, voice_output, voice, conversation_mode):
    """
    Launch the ByteFlow desktop companion - a small always-on-top robot
    character. Click it to open a chat panel, drag it to move it, or
    right-click to quit. Blocks until you close it.

    The companion has the same capabilities as `byteflow run`: it can
    do math via real tools, generate AND run code, and falls back to
    plain chat for everything else - not just conversation.

    Requires tkinter (ships with Python on Windows/macOS; on Linux you
    may need: sudo apt install python3-tk). Voice features are optional
    and degrade gracefully (with a printed notice, never a crash) if
    their libraries/model aren't installed - see --voice-input/--voice-output.
    """
    try:
        import tkinter  # noqa: F401 - just checking availability
    except ImportError:
        click.echo(
            "Error: tkinter is not available in this Python installation.\n"
            "On Windows/macOS it ships with the standard installer - try reinstalling Python.\n"
            "On Linux: sudo apt install python3-tk"
        )
        raise SystemExit(1)

    memory_path = None if memory_path.lower() == "none" else memory_path
    if memory_path:
        _ensure_memory_dir(memory_path)

    agent = Agent(provider=OllamaProvider(model=model), memory_path=memory_path)
    register_builtin_tools(agent)
    if not no_desktop_tools:
        register_desktop_tools(agent)

    from .companion import run_companion
    run_companion(
        agent=agent,
        voice_input=voice_input or voice,
        voice_output=voice_output or voice,
        conversation_mode=conversation_mode,
    )


if __name__ == "__main__":
    cli()
