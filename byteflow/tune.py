"""
Deliberate, manual "fine-tuning" of a local Ollama model using everything
ByteFlow has learned about you (see profile.py) and your chosen personality.

IMPORTANT - what this actually does and doesn't do:

This does NOT change the underlying model's weights. Real weight-level
fine-tuning (LoRA/QLoRA) needs a GPU, heavy ML libraries (transformers,
peft, bitsandbytes), and a labeled training run - that's a fundamentally
different, much heavier thing than what a lightweight offline framework
should bundle by default.

What this DOES do, using only Ollama itself (already installed, no new
dependencies, fully offline): builds an Ollama "Modelfile" - a small text
file that bundles a base model with a permanent system prompt - and runs
`ollama create` to bake your learned facts and personality into a real,
new, named local model. After that, talking to that model via plain
`ollama run <name>` (or ByteFlow pointed at it) carries your context by
default, without ByteFlow needing to inject it into every prompt at
runtime.

This is a deliberate, occasional action you run yourself (`byteflow tune`),
not something that happens automatically after every conversation - unlike
profile fact-learning (see agent.py's learn_from_exchange), which is safe
to run on every turn, this creates a new persistent system artifact and
should be a conscious choice.
"""

import shutil
import subprocess


class TuneError(Exception):
    pass


def ollama_available():
    """Check whether the `ollama` CLI binary is on PATH."""
    return shutil.which("ollama") is not None


def build_modelfile(base_model, profile_facts, personality=None, extra_instructions=None):
    """
    Build the text content of an Ollama Modelfile that bakes in the given
    facts and personality as a permanent system prompt.

    base_model: name of the existing Ollama model to build on (e.g. "llama3")
    profile_facts: list of fact strings (from Profile.all_facts())
    personality: optional personality/tone text (e.g. Agent.DEFAULT_PERSONALITY)
    extra_instructions: optional additional free-text instructions to append
    """
    sections = []

    if personality:
        sections.append(personality.strip())

    if profile_facts:
        sections.append(
            "Known facts about the user, from past conversations:\n"
            + "\n".join(f"- {fact}" for fact in profile_facts)
        )

    if extra_instructions:
        sections.append(extra_instructions.strip())

    system_prompt = "\n\n".join(sections) if sections else (
        "You are a helpful assistant."
    )

    # Triple-quote the system prompt Ollama-Modelfile-style. Escape any
    # literal triple-quotes in the content so we can't break out of the block.
    safe_prompt = system_prompt.replace('"""', '\\"\\"\\"')

    return f'FROM {base_model}\nSYSTEM """\n{safe_prompt}\n"""\n'


def create_tuned_model(model_name, base_model, profile_facts, personality=None,
                        extra_instructions=None, modelfile_path=None):
    """
    Write a Modelfile and run `ollama create <model_name> -f <path>` to bake
    it into a real local model. Returns the path to the Modelfile written.

    Raises TuneError if the ollama CLI isn't available or the create
    command fails - never silently does nothing.
    """
    if not ollama_available():
        raise TuneError(
            "The 'ollama' command was not found on your PATH. "
            "Install Ollama (https://ollama.com) to use byteflow tune."
        )

    content = build_modelfile(base_model, profile_facts, personality, extra_instructions)

    if modelfile_path is None:
        import tempfile
        import os
        fd, modelfile_path = tempfile.mkstemp(prefix="byteflow_modelfile_")
        os.close(fd)

    with open(modelfile_path, "w", encoding="utf-8") as f:
        f.write(content)

    try:
        proc = subprocess.run(
            ["ollama", "create", model_name, "-f", modelfile_path],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as e:
        raise TuneError(f"'ollama create' timed out after 300s: {e}") from e

    if proc.returncode != 0:
        raise TuneError(
            f"'ollama create' failed (exit code {proc.returncode}):\n{proc.stderr}"
        )

    return modelfile_path
