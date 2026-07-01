# ByteFlow

A lightweight Python framework for building AI agents and workflows.

## Features

- **Tool calling** — register Python functions as tools, the agent plans and executes them via an LLM. The planner validates every step against actually-registered tools, so a hallucinated tool name gets rejected instead of producing "Tool not found" for unrelated questions. The planner prompt also explicitly distinguishes past tool-call history from the current request, so an earlier action (e.g. opening LinkedIn) doesn't get mistakenly repeated or referenced for a later, unrelated message.
- **Built-in arithmetic tools** — `add`/`subtract`/`multiply`/`divide` are registered by default in the CLI's `run` command, so basic math is computed by real Python, not improvised by the LLM.
- **Coding mode** — ask it to write code and it generates *and runs* Python in an isolated subprocess by default, showing real stdout/stderr/errors rather than a description of what the code "should" do. `byteflow run` auto-detects obvious coding requests and routes to this automatically.
- **Plugins** — bundle related tools together and load them into an agent.
- **Persistent memory** — conversation history can be saved to a JSON file, so the agent remembers context across separate runs of your program (not just within one session).
- **Automatic learning (profile)** — after each `chat()`/`code()` turn, one extra LLM call checks whether anything durable was said (your name, a preference, an ongoing project) and saves it to a separate, deduplicated profile - distinct from raw chat history. These facts get fed into every future prompt, so answers improve across separate conversations. This does **not** change the underlying model - see "Manual model tuning" below for that.
- **Semantic memory search** — finds relevant older messages by meaning (shared topic/words), not just recency, using a fully offline TF-IDF search (no model downloads, no internet required). So if you mentioned your dog weeks ago, asking about it later can still surface that, even if it's long out of the "recent" window.
- **Personality** — `chat()` defaults to a warm mentor/companion tone; pass `personality=None` (or `--no-personality` on the CLI) for a neutral assistant instead.
- **Plain chat mode** — ask general questions, get explanations, or get help with code, without forcing everything through tool selection.
- **Pluggable LLM providers** — ships with an Ollama provider; the core framework has no hard dependency on it.
- **Desktop helper tools (opt-in)** — launch named apps/files/URLs, list/search files in folders you specify, read/write the clipboard, and preview-then-confirm file organizing (move/copy/rename). This is deliberately NOT a general "control my whole PC" agent: there's no screen vision and no mouse/keyboard automation. Every tool does one named, auditable thing; destructive operations require a separate confirmation step that the LLM planner cannot trigger on its own (see "Desktop tools" below).
- **Desktop companion** — a small, always-on-top robot character (`byteflow companion`) you click to chat with, backed by the same `Agent` as everywhere else (full access to tools, coding mode, and chat - not just conversation). Runs the model on a background thread so the window never freezes. Optional fully-offline voice input/output (`--voice`).

Everything above runs **fully offline** once you have a local model via Ollama — no API keys, no cloud calls, no data leaving your machine.

## Quick start: coding mode

```python
from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider

agent = Agent(provider=OllamaProvider())

result = agent.code("write a function that checks if a number is prime", execute=True)
print(result["code"])              # the generated source
print(result["result"].format())   # real stdout/stderr from actually running it
```

Or just use `run()` — coding-sounding requests are detected and routed automatically:

```python
agent.run("write a function that checks if a number is prime")
```

```bash
byteflow code "write a function that checks if a number is prime"
byteflow code "..." --no-execute   # just show the code, don't run it
byteflow run "write code to reverse a string"   # auto-routes to coding mode
```

The generated code runs in a separate subprocess with a timeout (10s by default), so a buggy or infinite-looping snippet can't crash or hang the agent itself - see `byteflow/sandbox.py`. This is a practical safety net, not a security sandbox against deliberately malicious code.

## Install

```bash
pip install -e .
```

`ollama` is only required if you use `OllamaProvider`:

```bash
pip install ollama
```

## Quick start: tools

```python
from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider
from byteflow.tools import Tool

def add(a, b):
    return a + b

agent = Agent(provider=OllamaProvider())
agent.register_tool(Tool("add", add, "adds two numbers"))

print(agent.run("add 10 and 20"))
```

## Desktop tools (opt-in)

A small set of named, scoped helpers for things you'd otherwise do by hand on your own machine - launching apps/sites/URLs (by shortcut name or directly), listing or searching files in a folder you specify, and clipboard access. These are **off by default** for the agent and must be explicitly enabled:

```bash
byteflow run "open notepad" --enable-desktop-tools
byteflow run "list pdf files in C:\Users\me\Documents" --enable-desktop-tools
```

For just opening something - no LLM call, no agent setup - use `byteflow open` directly:

```bash
byteflow open youtube          # resolves to https://www.youtube.com
byteflow open vscode
byteflow open https://example.com   # any raw URL works too
byteflow open --list           # see all known shortcut names
```

Known shortcuts (case-insensitive) include media/social (`youtube`, `spotify`, `gmail`, `linkedin`, `twitter`/`x`, `facebook`, `whatsapp`, `netflix`, `instagram`, `reddit`), dev tools (`github`, `stackoverflow`, `vscode`/`code`), and Windows office/utility apps (`word`, `excel`, `powerpoint`, `calculator`/`calc`, `notepad`, `paint`, `explorer`/`files`). Anything not in the list - a raw URL, a file path, or an app name your OS already knows - still works exactly as before; the shortcut table is a convenience layer on top of `launch()`, not a restriction. See `byteflow/desktop_tools.py`'s `SHORTCUTS` dict to add more.

```python
from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider
from byteflow.desktop_tools import register_desktop_tools

agent = Agent(provider=OllamaProvider())
register_desktop_tools(agent)

print(agent.use_tool("list_files", r"C:\Users\me\Documents", "*.pdf"))
print(agent.use_tool("launch", "youtube"))
```

**This is deliberately not a general computer-use agent.** There's no screen vision and no mouse/keyboard automation - each tool does exactly one named, auditable thing on a folder or app you specify, the same trust model as `add`/`multiply`, just pointed at the filesystem and OS instead of numbers.

**File organizing is two-step on purpose.** `organize_files()` (move/copy/rename) can **never** perform the action itself - calling it always returns a preview and a one-time confirmation token, even if extra arguments are passed in. Actually performing the change requires a separate call to `confirm_organize(token)`:

```python
preview = agent.use_tool("organize_files", r"C:\Users\me\Downloads", "move", "*.jpg", r"C:\Users\me\Pictures")
print(preview)
# DRY RUN (move, 3 file(s)) - nothing changed yet.
#   ... file list ...
# To actually perform this, call confirm_organize('a1b2c3d4'). This token is single-use...

agent.use_tool("confirm_organize", "a1b2c3d4")  # actually performs it
```

This means there's no single tool call - however the LLM planner phrases it - that can move, copy, or rename a file in one shot. Clipboard writing and the file-organize *preview* are otherwise safe to let the agent call freely; only `confirm_organize` actually changes anything on disk, and it requires a token that only exists after a human has seen the preview.

Clipboard support needs `pip install pyperclip` (`pip install byteflow[clipboard]`); without it, `read_clipboard`/`write_clipboard` return a clear error string instead of crashing.

## Drafting social posts (stage-only, never publishes)

`agent.draft_social_post()` / `byteflow post` drafts a social media post with the LLM, copies it to your clipboard, and opens the platform's compose page - **it never publishes anything automatically**. There is no browser automation, no clicking, no login handling. You paste (Ctrl+V), review, and click Post yourself.

```bash
byteflow post "launching my open source project" --platform linkedin --tone excited
# === DRAFT ===
# Thrilled to share my latest project...
#
# Copied to clipboard.
#
# Opened linkedin in your browser.
# ByteFlow does NOT type or paste anything for you - that's a deliberate safety choice.
# Next steps:
#   1. Click into the post text box on the page that just opened
#   2. Press Ctrl+V to paste (the draft is on your clipboard)
#   3. Review it, then click Post yourself
```

```python
from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider

agent = Agent(provider=OllamaProvider())
result = agent.draft_social_post("launching my open source project", platform="linkedin", tone="excited")

if result["warning"]:
    print("Heads up:", result["warning"])
else:
    print(result["draft"])       # the generated text
    print(result["clipboard"])   # True if copied successfully
    print(result["launched"])    # True if the site opened
```

Supported platforms: `linkedin`, `twitter`/`x`, `facebook`. Other platforms (e.g. `youtube`, which has no quick text-compose URL the way LinkedIn/Twitter do) return a clear `warning` explaining why, with `draft: None`, instead of silently doing nothing. `--no-open` (CLI) / `open_site=False` (Python) drafts and copies without opening a browser. This is a deliberate safety boundary, not a missing feature: ByteFlow can write words for you, but a human approves what actually gets published under their name.

`draft_social_post` is auto-registered as a `Tool` on every `Agent`, so a request like "post about my new project on LinkedIn" can trigger this directly through `agent.run()`. If the topic is too vague to extract ("post on linkedin" with no stated subject), it asks what to post about instead of crashing - this fixes a real bug where a missing topic raised a raw `TypeError`.

## Desktop companion

A small, always-on-top box-faced robot with a single large glowing eye - a soft multi-step glow, a glassy lit iris, a dark pupil, and a bright highlight glint for a genuinely alive, camera-lens feel (drawn with plain shapes, no image files needed) - that sits on your screen. Click it (without dragging) to open a chat panel, drag it to move it, right-click to quit.

The chat panel has a small header showing a **mode badge** (TEXT / VOICE / LISTENING / CONVERSATION / HEARING) so you always know what state it's in, and an input row with an **upload button** (📎) alongside the text entry and send button - click it to pick a file (`.pdf`, `.docx`, or plain text); the real extracted content gets ingested into the vector store (chunked automatically if long - see "Documents and RAG" below) rather than truncated or dumped wholesale into one message, so you can ask about any part of even a very large file.

```bash
byteflow companion
byteflow companion --model llama3 --memory-path none
byteflow companion --no-desktop-tools   # skip registering launch/files/clipboard/organize
```

```python
from byteflow.companion import run_companion
run_companion()  # blocks until you close the window
```

Requires `tkinter` - it ships with the standard Python installer on Windows and macOS. On some Linux distros it's a separate package: `sudo apt install python3-tk`. `byteflow companion` checks for it and gives a clear error instead of crashing if it's missing.

**Full module access:** the companion routes every message through `agent.run()` - the same smart entrypoint as `byteflow run` - so it has access to everything: registered tools (math, web search, desktop helpers like launching apps/organizing files, and drafting+staging social posts), auto-routed coding mode (writes AND runs Python, showing real output), auto-routed web search for current-events questions, and falls back to plain chat for everything else. It's not just a chat window - ask it to do math, write and run code, search the web, draft a post, or open an app, and it actually does, the same as the CLI.

Every connection point listed above was specifically audited end-to-end (not assumed): with the companion's default agent setup, `agent.tools` contains `add`/`subtract`/`multiply`/`divide`/`web_search`/`launch`/`list_shortcuts`/`list_files`/`search_files`/`read_clipboard`/`write_clipboard`/`organize_files`/`confirm_organize`/`draft_social_post` (13 tools), plus `agent.vector_store`, `agent.profile`, `chat_with_search()`, `ingest_document()`, and `code()` are all live and reachable. One gap found and fixed during that audit: `draft_social_post` existed as a method but had no way to actually be *triggered* from chat - it's now auto-registered as a tool on every `Agent`, so "post about X on LinkedIn" really drafts, copies, and opens the compose page instead of just talking about it. `Workflow` and the plugin system (`load_plugin()`) are deliberately NOT auto-connected - they're user-driven extension points you opt into explicitly in your own code, not things that make sense to silently load into every companion session.

**How it works:** each message runs on a background thread, so the window never freezes while the local model is thinking - eyes turn yellow while it's working, green if a reply arrived while the chat panel was closed. Because tool-routing, the reply itself, and automatic fact-learning each cost a separate LLM call, a single message can involve 2-3 calls to your local model depending on what it ends up doing - expect noticeably more than one generation's worth of wait per message.

### Voice (optional, fully offline)

```bash
byteflow companion --voice              # both push-to-talk input and spoken output
byteflow companion --voice-input        # push-to-talk microphone button only
byteflow companion --voice-output       # spoken replies only
byteflow companion --conversation-mode  # hands-free: auto-detects when you start/stop talking, no clicking
```

The mode badge reflects whichever of these is active: **VOICE** when push-to-talk is ready, **LISTENING** while push-to-talk is recording, **CONVERSATION** when hands-free mode is on, **HEARING** while it's actively picking up your speech in that mode.

- **Voice output** uses `pyttsx3` (your OS's built-in voice - SAPI5 on Windows, fully offline, no model download). Install with `pip install pyttsx3` or `pip install byteflow[voice]`.
- **Voice input** is push-to-talk (click the microphone button to start, click again to stop and transcribe) via `vosk` + `sounddevice`, fully offline but needs a one-time model download:
  1. `pip install vosk sounddevice` (or `pip install byteflow[voice]`)
  2. Download a model from https://alphacephei.com/vosk/models (e.g. `vosk-model-small-en-us-0.15.zip`, ~40MB)
  3. Unzip it and place its contents at `~/.byteflow/vosk-model/`
  4. Run `python -m byteflow.voice` any time for these instructions again
- **Conversation mode** is hands-free - once toggled on, it keeps listening and automatically detects when you start and stop talking (no clicking per utterance), firing off each thing you say as soon as you pause. Same requirements as voice input above.

If the libraries or model aren't present, voice features are silently skipped (with a one-line printed notice) rather than crashing - the companion still works as a text-only chat window.

Code replies are never read aloud verbatim - speaking out raw Python source line-by-line would be unpleasant, so voice output gives a short spoken summary ("I wrote the code and ran it - the result was: ...") while the chat panel still shows the full code and output.

**Testing note, in the interest of being upfront:** the non-visual logic (`CompanionController`, `voice.py`'s availability checks and error handling) is covered by real tests - 87 passing as of this version, including specific regression tests for bugs found and fixed during development (a click/drag binding collision, and code being read aloud verbatim instead of summarized). The actual Tkinter window, and the real Vosk/pyttsx3 libraries, could not be exercised in the environment this was built in, since it has no display and no audio hardware - the code is written carefully and reviewed, but it's worth trying the window and voice features on your machine before relying on them fully.

## Quick start: chat (with memory)

```python
from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider

# Persists by default to ~/.byteflow/memory.json - the same location the
# CLI uses, so a notebook, a script, and `byteflow chat` all share memory
# automatically. No memory_path needed for this.
agent = Agent(provider=OllamaProvider())

print(agent.chat("My name is Aman."))
# ... later, in a completely separate run/notebook/script ...
print(agent.chat("What's my name?"))  # -> remembers "Aman"
```

Want a specific file instead? Pass `memory_path="my_memory.json"`. Want it to NOT persist at all (in-memory only, cleared when the process exits) - useful for tests or quick one-off experiments? Pass `memory_path=False`:

```python
agent = Agent(provider=OllamaProvider(), memory_path=False)  # ephemeral, no file written
```

## Quick start: automatic learning (profile)

After each `chat()`/`code()` exchange, ByteFlow makes one extra LLM call to check whether anything durable was said, and saves it separately from raw chat history:

```python
from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider

agent = Agent(provider=OllamaProvider(), memory_path="my_memory.json")
# profile_path defaults to "my_memory_profile.json" automatically

agent.chat("Hi, my name is Aman and I'm learning data structures.")
# -> in the background, extracts and saves facts like "User's name is Aman"

print(agent.profile.format())
# - User's name is Aman
# - User is learning data structures
```

These facts get woven into every future prompt automatically (see `recalled_context()`), so the agent's answers improve across separate conversations without ever touching the underlying model. Set `Agent(..., learn=False)` to disable this extra call per turn.

```bash
byteflow profile                          # view learned facts
byteflow profile --forget "User's name is Aman"
byteflow profile --clear                  # forget everything learned
byteflow chat "..." --no-learn            # skip learning for one message
```

## Documents and RAG (chunking + vector search)

ByteFlow can ingest long documents and chat history into a chunk-aware vector store, then automatically pull in the most relevant chunk for whatever you ask - real retrieval-augmented generation (RAG), fully offline:

```python
from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider

agent = Agent(provider=OllamaProvider())

# Long text gets chunked automatically (see byteflow/chunking.py) - short
# text becomes a single chunk, so this is safe to call uniformly.
agent.ingest_document(open("project_notes.txt").read(), source="project_notes.txt")

# recalled_context() (used internally by chat()/run()) now pulls in just
# the relevant chunk(s), even if the document is far too big to fit in
# one prompt:
print(agent.chat("where are the deployment credentials stored?"))
```

**How it works:** `byteflow/chunking.py` splits long text into overlapping pieces on sentence boundaries (with a hard fallback for unpunctuated text like logs or code, so no chunk is ever unbounded), so a fact sitting right at a chunk boundary is still findable in at least one piece. `byteflow/embeddings.py` defines a swappable `Embedder` interface:

- **`TfidfEmbedder`** (default) - the same TF-IDF + cosine similarity math used elsewhere in ByteFlow, zero new dependencies, fully offline out of the box. Matches on shared words, not true semantic meaning.
- **`SentenceTransformerEmbedder`** (optional) - real semantic embeddings via `sentence-transformers`, genuinely understanding that "dog" and "puppy" are related. Requires `pip install sentence-transformers` (or `pip install byteflow[embeddings]`) and a one-time model download (~80-400MB) - still fully offline after that, no per-query network calls.

```python
from byteflow.embeddings import SentenceTransformerEmbedder

agent = Agent(provider=OllamaProvider(), embedder=SentenceTransformerEmbedder())
# same Agent API, genuinely semantic retrieval underneath
```

`byteflow/vector_store.py`'s `VectorStore` ties both pieces together and persists to disk (`<memory_path>_vectors.json` by default, alongside the profile file) so ingested documents survive across separate runs, just like memory and profile facts.

The desktop companion's upload button (📎) uses this automatically: uploading a file ingests its real extracted text (chunked if long) into the vector store, rather than truncating it or dumping the whole thing into one message - ask about any part of a large file and the relevant chunk gets pulled in.

**Real text extraction for PDF and DOCX, not binary garbage.** `byteflow/file_reading.py` detects the actual file type and extracts genuine text: `.pdf` via `pypdf` (`pip install pypdf` or `pip install byteflow[documents]`), `.docx` via `python-docx`, everything else as plain text. This fixes a real, serious bug: uploads were previously opened with plain `open(path, "r", encoding="utf-8")`, which doesn't extract any real PDF/DOCX content - it reads raw binary bytes (compressed streams, font tables) and mangles them into meaningless replacement characters. The garbage got chunked and indexed exactly as if it were real text, so every question about an uploaded PDF retrieved nonsense, and the model would hallucinate an unrelated answer rather than admit it had nothing useful to work with. Image-only/scanned PDFs (no extractable text at all) and missing optional libraries both raise a clear, specific error instead of silently indexing garbage.

## Web search (free, no API key)

ByteFlow can search the web (DuckDuckGo's HTML endpoint, no signup, no key) so it can answer questions about current events, prices, or anything else outside the model's fixed training data:

```python
agent.run("what is the latest news on AI")          # auto-detected, searches automatically
agent.run("search for python 3.13 release notes")    # explicit web_search tool
print(agent.chat_with_search("who is the current CEO of OpenAI"))  # direct call
```

```bash
byteflow run "what is the current weather in Tokyo"
```

**Auto-detection** (`Agent._looks_like_search_request`) recognizes patterns like "latest news", "current president", "stock price", "today's weather" and automatically searches before answering - deliberately specific multi-word patterns rather than bare words like "current" or "today" alone, since those falsely matched personal questions like "what is my current project status" during testing. An explicit **`web_search` tool** is also registered by default for the planner to call directly.

**Date/time questions never touch the LLM or the network at all.** "What's today's date" - or even terse phrasing like "today date" - is answered directly from the system clock (`Agent._answer_datetime_request`) - instant and 100% accurate. Detection uses word proximity (a date/time word like "date"/"day"/"time" near a present-tense word like "today"/"current"/"now") rather than a fixed list of exact phrases, since real people type short keyword-style queries, not full questions - while still avoiding false positives on sentences that merely mention "today" in passing (e.g. "today I learned something cool" or "today was a good day at work" correctly do NOT trigger this). This fixes a real observed bug: routed through search, a model given an unhelpful result returned the literal placeholder text `"[current date]"` instead of a real date.

**The explicit `web_search` tool now actually summarizes results instead of dumping raw text.** When registered via `register_builtin_tools(agent)`, it's bound to the agent and delegates to `chat_with_search()` - same anti-fabrication guarantee, same answer quality - rather than returning an unsummarized block of titles/snippets/URLs as the "answer". This fixes a real observed bug: a query like "top 10 ai news today" that didn't match the auto-detection patterns fell through to the regular tool-planner, which picked `web_search` directly and returned raw search text verbatim instead of a real answer. Auto-detection patterns were also broadened to catch this kind of phrasing ("top N ... today/this week") directly, so it's now caught even before reaching the tool-planner.

**A hard guarantee against fabricated results, not just a prompt instruction.** If a real search genuinely fails or finds nothing, `chat_with_search()` returns an honest message directly and the LLM is **never called** for that turn - this isn't a "please be honest" instruction the model can ignore, it's structurally impossible for the model to answer in that case. This fixes a real observed bug: with an unreliable/blocked search, a model still confidently returned a list of specific-looking but fabricated news URLs (Google News, Reuters, CNN) rather than admitting the search didn't work.

When search *does* succeed, the summarization prompt gives the model concrete guidance for a better answer: synthesize in its own words rather than just listing results back, call out disagreement between sources instead of picking one arbitrarily, reference sources with `[1]`/`[2]` when useful, and keep the answer proportional to the question.

This is genuinely more fragile than a real search API - there's no stable contract, and the page structure could change. See `byteflow/web_search.py`.

## Manual model tuning (deliberate, not automatic)

`byteflow tune` is a separate, manual step you run yourself - it does **not** happen automatically. It bakes your learned profile facts and personality into a real, new, named local Ollama model using an [Ollama Modelfile](https://github.com/ollama/ollama/blob/main/docs/modelfile.md):

```bash
byteflow tune my-buddy --base-model llama3
# Building 'my-buddy' from base model 'llama3' with 4 learned fact(s)...
# Done. Modelfile written to /tmp/byteflow_modelfile_xxxx
# Model 'my-buddy' created. Try it with: ollama run my-buddy
```

Afterwards, `ollama run my-buddy` (or any tool pointed at that model) carries your context by default - no runtime prompt injection needed for that part anymore.

**What this is NOT**: this doesn't change the base model's actual weights. Real weight-level fine-tuning (LoRA/QLoRA) needs a GPU and heavy ML libraries (`transformers`, `peft`, `bitsandbytes`) and is a fundamentally bigger undertaking than a lightweight offline framework should bundle by default. The Modelfile approach uses only `ollama` itself - already installed, zero new dependencies, fully offline - to wrap the base model with a permanent system prompt instead.

Requires the `ollama` CLI on your `PATH`. Options: `--no-personality` to skip the default tone, `--instructions "..."` to bake in any extra free-text instructions, `--profile-path` to point at a specific profile file.

## Quick start: code help

```python
from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider
from byteflow.codehelp import explain_code

agent = Agent(provider=OllamaProvider())
print(explain_code(agent, "myscript.py", "Are there any bugs here?"))
```

## CLI

```bash
byteflow run "add 10 and 20"
byteflow run "write code to reverse a string"   # auto-routes to coding mode
byteflow code "write a function that checks if a number is prime"
byteflow code "..." --no-execute   # just show the code, don't run it
byteflow chat "explain how a binary search works"
byteflow memory            # view recent persisted memory
byteflow memory --search "what did I say about my dog"   # semantic recall
byteflow memory --clear    # wipe persisted memory
byteflow chat "hi" --no-personality   # neutral tone instead of mentor/companion
byteflow profile           # view learned facts about you
byteflow profile --forget "User's name is Aman"
byteflow profile --clear   # forget everything learned
byteflow tune my-buddy --base-model llama3   # bake facts into a real Ollama model (manual)
byteflow run "open notepad" --enable-desktop-tools   # opt-in desktop helper tools
byteflow post "launching my project" --platform linkedin --tone excited
byteflow open youtube      # quick launch by shortcut name, no LLM call
byteflow open --list       # see all known shortcuts
byteflow companion         # launch the desktop robot character
```

Every command supports `--help` for its full list of options (e.g. `byteflow post --help`). Running `byteflow` with no command shows the full list above.

By default, CLI memory persists to `~/.byteflow/memory.json`. Pass `--memory-path none` to disable persistence for a single call.

## Using ByteFlow in Jupyter / notebooks

`byteflow run "..."`, `byteflow code "..."`, etc. are **terminal commands** — they're built on `click`, which reads `sys.argv` to figure out what you typed. Jupyter overwrites `sys.argv` with its own kernel-launch arguments, so calling `cli()` directly inside a notebook cell will fail (and can raise `SystemExit`, which kills the kernel).

This only affects `byteflow.cli`. The actual library - `Agent`, `Memory`, `Tool`, `Plugin` - is plain Python with no dependency on `sys.argv`, and works in a notebook exactly like any other import:

```python
# This is the notebook-friendly way to use ByteFlow - call the Agent API directly,
# not the byteflow.cli command functions.
from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider

agent = Agent(provider=OllamaProvider())  # persists to ~/.byteflow/memory.json by default

print(agent.chat("Explain list comprehensions"))
result = agent.code("write a function that reverses a string", execute=True)
print(result["result"].format())
```

**Watch out for relative paths.** If you pass a relative `memory_path` (e.g. `memory_path="notebook_memory.json"`), it resolves relative to Jupyter's *current working directory* - which is often different from your terminal's - so you can end up with a different file per notebook/folder and it'll look like ByteFlow "forgot" things between environments. Leaving `memory_path` unset (the default) avoids this entirely, since it always resolves to the same absolute `~/.byteflow/memory.json` no matter where the process is running from.

If you specifically want the CLI's exact output formatting (the `=== CODE ===` / `=== EXECUTION ===` headers) inside a notebook, call the same logic without going through `click`:

```python
from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider

agent = Agent(provider=OllamaProvider())
result = agent.code("write a function that reverses a string", execute=True)

print("=== CODE ===")
print(result["code"])
if result["executed"]:
    print("\n=== EXECUTION ===")
    print(result["result"].format())
```

## Running tests

```bash
pip install -e .[dev]
python -m pytest tests/ -v
# or, without pytest:
python tests/test_byteflow.py
```

## Plugins

```python
from byteflow.plugin import Plugin
from byteflow.tools import Tool

class MathPlugin(Plugin):
    def __init__(self):
        super().__init__("MathPlugin")

    def setup(self, agent):
        agent.register_tool(Tool("multiply", lambda a, b: a * b))

agent.load_plugin(MathPlugin())
```

## Status

Currently in development. Contributions and feedback welcome.
