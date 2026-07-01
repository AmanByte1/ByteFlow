import json
import os
import re
from .memory import Memory
from .profile import Profile
from .vector_store import VectorStore

from .tools import Tool


DEFAULT_PERSONALITY = """You are a warm, knowledgeable companion and mentor.
You remember what the person has told you and use that to give thoughtful,
personal answers - not generic ones. You explain things clearly when
teaching or helping with code, and you're easy to talk to otherwise.
You're honest: if you don't know something or aren't sure, you say so
instead of guessing confidently."""


_UNSET = object()  # sentinel: distinguishes "argument not passed" from "passed as None"


def _default_memory_path():
    return os.path.join(os.path.expanduser("~"), ".byteflow", "memory.json")


class Agent:
    def __init__(self, provider=None, memory_path=_UNSET, profile_path=None,
                 personality=DEFAULT_PERSONALITY, learn=True,
                 vector_store_path=None, embedder=None):
        """
        provider: an LLM provider (e.g. OllamaProvider) implementing .generate(prompt)
        memory_path: path to a JSON file for raw conversation history.
                     - Not passed at all: defaults to ~/.byteflow/memory.json,
                       so the agent remembers across separate runs/processes/
                       notebooks by default - this is almost always what you
                       want, since it's the same behavior as the CLI.
                     - Pass memory_path=False to explicitly opt OUT of
                       persistence (in-memory only, cleared when the process
                       exits) - useful for tests, quick experiments, or
                       anywhere you deliberately don't want state carried over.
                     - Pass a custom path string to use a specific file.
        profile_path: optional path to a JSON file for durable extracted facts
                     (name, preferences, ongoing projects). Defaults to
                     memory_path with a "_profile" suffix if memory_path is
                     given, so `byteflow chat` keeps a profile automatically.
                     If both are omitted, profile is in-memory only.
        personality: system-prompt-style text describing how the agent should
                     behave in chat(). Pass None or "" for a neutral assistant.
        learn: if True (default), chat()/run() automatically try to extract
                     a durable fact from each exchange and add it to the
                     profile - this is what makes ByteFlow "get smarter"
                     about you over separate conversations. Set False to
                     disable this extra LLM call per turn.
        vector_store_path: optional path to a JSON file for the chunk-level
                     vector store (see vector_store.py) used by
                     ingest_document() and recalled_context()'s document
                     search. Defaults to memory_path with a "_vectors"
                     suffix if memory_path is given, matching profile_path's
                     pattern, so uploaded documents persist by default too.
        embedder: optional Embedder instance (see embeddings.py) backing
                     the vector store - defaults to TfidfEmbedder (fully
                     offline, no extra dependencies). Pass a
                     SentenceTransformerEmbedder for real semantic search.
        """
        if memory_path is _UNSET:
            memory_path = _default_memory_path()
            memory_dir = os.path.dirname(memory_path)
            if memory_dir:
                os.makedirs(memory_dir, exist_ok=True)
        elif memory_path is False:
            memory_path = None  # explicit opt-out -> Memory's own ephemeral mode

        self.provider = provider
        self.tools = {}        # name -> Tool object
        self.plugins = []
        self.memory = Memory(path=memory_path)

        if profile_path is None and memory_path:
            base, ext = memory_path.rsplit(".", 1) if "." in memory_path else (memory_path, "json")
            profile_path = f"{base}_profile.{ext}"
        self.profile = Profile(path=profile_path)

        if vector_store_path is None and memory_path:
            base, ext = memory_path.rsplit(".", 1) if "." in memory_path else (memory_path, "json")
            vector_store_path = f"{base}_vectors.{ext}"
        self.vector_store = VectorStore(embedder=embedder, path=vector_store_path)

        self.personality = personality
        self.learn = learn

        # Register this agent's own bound methods as tools where it makes
        # sense - draft_social_post_tool needs `self` (the provider, the
        # agent's own clipboard/launch calls), so it can't be a free
        # function like add/subtract/etc. Without this, the method
        # existed but the planner/companion chat had no way to actually
        # trigger it - "post about X on linkedin" would just talk about
        # posting instead of really drafting+staging it.
        self.register_tool(Tool(
            "draft_social_post",
            self.draft_social_post_tool,
            "drafts a social media post, copies it to the clipboard, and opens the platform's compose page - never posts automatically",
        ))

    def ingest_document(self, text, source):
        """
        Add a document (or any long text) to the agent's vector store,
        chunking it automatically if it's long (see chunking.py). Once
        ingested, recalled_context() can surface the most relevant
        chunks for a given message, regardless of which part of a big
        document they came from. Returns the number of chunks added.
        """
        return self.vector_store.add_document(text, source=source)

    # -----------------------------
    # TOOL SYSTEM
    # -----------------------------
    def register_tool(self, tool):
        self.tools[tool.name] = tool

    def use_tool(self, name, *args):
        return self.tools[name].run(*args)

    # -----------------------------
    # PLUGINS
    # -----------------------------
    def load_plugin(self, plugin):
        if any(p.name == plugin.name for p in self.plugins):
            return f"Plugin '{plugin.name}' already loaded"

        plugin.setup(self)
        self.plugins.append(plugin)

        return f"Plugin '{plugin.name}' loaded"

    # -----------------------------
    # MEMORY HELPERS
    # -----------------------------
    def add_memory(self, role, content):
        self.memory.add(role, content)

    def recent_context(self, n=5):
        """Format recent memory entries as readable text for prompts."""
        entries = self.memory.get_recent(n)
        if not entries:
            return "(no prior context)"

        return "\n".join(
            f"- [{e['role']}] {e['content']}" for e in entries
        )

    def recalled_context(self, query, n_recent=6, n_relevant=4, n_doc_chunks=3):
        """
        Build a richer context block than recent_context() alone: the most
        recent messages (what was just said) PLUS older messages that are
        semantically relevant to `query` (offline TF-IDF search), even if
        they happened long ago, PLUS relevant chunks from any ingested
        documents (see ingest_document()). Deduplicates overlap between
        the memory sets.
        """
        recent = self.memory.get_recent(n_recent)
        recent_texts = {e["content"] for e in recent}

        relevant = self.memory.search(query, top_k=n_relevant)
        older_relevant = [
            entry for entry, score in relevant
            if entry["content"] not in recent_texts
        ]

        doc_chunks = self.vector_store.search(query, top_k=n_doc_chunks)

        lines = []

        known_facts = self.profile.all_facts()
        if known_facts:
            lines.append("Known facts about the user (from past conversations):")
            lines.extend(f"- {fact}" for fact in known_facts)
            lines.append("")

        if doc_chunks:
            lines.append("Relevant excerpts from documents you've shared:")
            for chunk in doc_chunks:
                lines.append(f"- [{chunk['source']}] {chunk['text']}")
            lines.append("")

        if older_relevant:
            lines.append("Relevant things from earlier conversations:")
            lines.extend(f"- [{e['role']}] {e['content']}" for e in older_relevant)
            lines.append("")

        lines.append("Recent conversation:")
        if recent:
            lines.extend(f"- [{e['role']}] {e['content']}" for e in recent)
        else:
            lines.append("(no prior messages)")

        return "\n".join(lines)

    # -----------------------------
    # LEARNING (FACT EXTRACTION)
    # -----------------------------
    def learn_from_exchange(self, user_message, assistant_response):
        """
        Use one extra LLM call to decide whether this exchange contains a
        durable fact worth remembering long-term (name, preference, ongoing
        project, correction) - as opposed to throwaway chatter. If so,
        extract it as a short standalone statement and add it to the
        profile. This is what makes ByteFlow's answers improve across
        separate conversations: the model itself doesn't change, but what
        it's told about you accumulates and gets fed back in every time.

        Silently does nothing if there's no provider, learn=False, or the
        model decides there's nothing worth remembering.
        """
        if not self.provider or not self.learn:
            return None

        extraction_prompt = f"""Look at this exchange and decide if it contains
a durable fact about the user worth remembering for future conversations -
things like their name, preferences, ongoing projects, corrections they've
made, or important context about their situation.

Ignore throwaway chatter, small talk, one-off questions, and anything that
won't matter in a future conversation.

User said: {user_message}
Assistant replied: {assistant_response}

If there IS a durable fact, respond with ONLY a short standalone sentence
stating it (e.g. "User's name is Aman" or "User prefers Python over Java").
If there is NOT a durable fact worth remembering, respond with ONLY: none
"""

        response = self.provider.generate(extraction_prompt)
        fact = response.strip().strip('"')

        if not fact or fact.lower() in ("none", "none.", "n/a"):
            return None

        added = self.profile.add_fact(fact)
        return fact if added else None

    # -----------------------------
    # CODE MODE
    # -----------------------------
    @staticmethod
    def extract_code_block(text):
        """
        Pull the first fenced code block out of a markdown-ish LLM response.
        Falls back to the raw text if no fence is found (some models just
        return bare code without fences).
        """
        match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def code(self, request, execute=False, timeout=10):
        """
        Coding mode: ask the LLM to write Python code for `request`,
        using the standard library as needed, and optionally execute it.

        Returns a dict:
            {
                "code": "<the generated source>",
                "explanation": "<the model's full response, for context>",
                "executed": bool,
                "result": ExecutionResult | None,
            }

        Set execute=True to actually run the generated code in an isolated
        subprocess (see byteflow/sandbox.py) and capture real stdout/stderr,
        instead of just showing what the code *should* do.
        """
        if not self.provider:
            return {
                "code": "",
                "explanation": "[No provider configured. Pass a provider (e.g. OllamaProvider) to Agent().]",
                "executed": False,
                "result": None,
            }

        self.add_memory("user", request)

        prompt = f"""You are an expert Python programmer. Write correct,
working Python code for the following request.

Use the Python standard library (and well-known third-party libraries if
genuinely helpful) where appropriate, rather than reinventing things by
hand. Prefer simple, readable code over clever one-liners.

IMPORTANT: this code may be executed non-interactively in a sandbox with
no stdin attached. NEVER use input() - it will block forever and the run
will simply time out with no useful output. If the task is naturally
about taking two numbers, a name, etc., write a function that takes
parameters and call it with a couple of concrete, hardcoded example
values (e.g. a small `if __name__ == "__main__":` block calling the
function with sample inputs and printing the result), so the script
still runs to completion and shows real output on its own.

If the request asks a question rather than to "write" something, still
answer with runnable code that demonstrates/computes the answer where
that makes sense (e.g. a math question -> a short script that prints
the result), unless the request is purely conceptual.

Context from earlier conversation:
{self.recalled_context(request)}

Request:
{request}

Respond with a short explanation if useful, followed by the code in a
single fenced Python code block:
```python
# code here
```
"""

        response = self.provider.generate(prompt)
        code_str = self.extract_code_block(response)

        self.add_memory("assistant", response)
        self.learn_from_exchange(request, response)

        result = {
            "code": code_str,
            "explanation": response,
            "executed": False,
            "result": None,
        }

        if execute and code_str:
            from .sandbox import run_python_code
            exec_result = run_python_code(code_str, timeout=timeout)
            result["executed"] = True
            result["result"] = exec_result
            self.add_memory(
                "tool",
                f"executed generated code -> success={exec_result.success}",
            )

        return result

    # -----------------------------
    # SAFE ARG HANDLING
    # -----------------------------
    def safe_args(self, args):
        if not isinstance(args, list):
            return []

        return [
            a if isinstance(a, (int, float, str)) else str(a)
            for a in args
        ]

    # -----------------------------
    # JSON PARSER (ROBUST)
    # -----------------------------
    def extract_json(self, text):
        if text is None:
            return None

        text = text.strip()

        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # try to find a JSON object OR a JSON list embedded in extra text
        for pattern in (r"\[.*\]", r"\{.*\}"):
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue

        return None

    # -----------------------------
    # PLANNER (MULTI STEP)
    # -----------------------------
    def plan(self, goal):
        if not self.provider:
            return None

        if not self.tools:
            # no tools registered at all - nothing for a plan to call
            return None

        prompt = f"""
You are a STRICT planner for an AI agent. Your ONLY job is to decide
which of the agent's registered tools (if any) should be called for
the CURRENT goal below.

Available tools (ONLY these - do not invent others):
{list(self.tools.keys())}

Recent context (this is HISTORY - things that already happened earlier
in the conversation, NOT instructions for what to do now):
{self.recent_context()}

Current goal (decide based on THIS, not the history above):
{goal}

Rules:
- Default to null. Only return a tool call if the CURRENT goal CLEARLY
  and DIRECTLY matches what a tool does - exact numbers for math, a
  clear file/folder path for file tools, a clear app/site name for
  launch, a clear topic for posting.
- The "Recent context" is what ALREADY happened - a previous launch,
  search, or post draft. Do NOT treat it as a new instruction to repeat.
  If the user already asked to open LinkedIn and the goal now is
  something else entirely ("what's the weather", "hii", "can you write
  code"), that goal has nothing to do with LinkedIn - don't call
  draft_social_post or launch again just because they're mentioned in
  the history.
- If the goal is small talk, a greeting, a question about the
  conversation itself, or anything vague or general, return null.
  Do NOT force-fit a tool just because one exists or was used recently.
- Use ONLY tool names from the list above. Never invent a tool name.

Examples:
  Goal: "add 10 and 20"          -> [{{"step": "add", "args": [10, 20]}}]
  Goal: "open youtube"           -> [{{"step": "launch", "args": ["youtube"]}}]
  Goal: "hii"                    -> null
  Goal: "select one video"       -> null
  Goal: "what is my name"        -> null
  History shows "launch -> Launched: linkedin", Goal: "can you write a function for me" -> null (unrelated to the LinkedIn history)
  History shows "launch -> Launched: linkedin", Goal: "give me content ideas" -> null (too vague to draft a post about - ask for a topic instead, don't guess)

Return ONLY the JSON list or the literal null. No other text.
"""

        response = self.provider.generate(prompt)
        data = self.extract_json(response)

        if not isinstance(data, list):
            return None

        # Validate every step references a real, registered tool.
        # A plan that hallucinates an unknown tool is worse than no plan -
        # reject it entirely rather than partially executing garbage.
        for step in data:
            if not isinstance(step, dict) or step.get("step") not in self.tools:
                return None

        return data
    # -----------------------------
    # PLAIN CHAT (NO TOOLS)
    # -----------------------------
    def chat(self, message):
        """
        Talk to the underlying LLM directly, with conversation memory,
        but without forcing tool selection. Use this for general Q&A,
        explanations, brainstorming, code help, etc.

        Pulls in both recent messages and older messages that are
        semantically relevant to `message`, so the agent can recall
        things mentioned a long time ago, not just the last few turns.
        """
        if not self.provider:
            return "[No provider configured. Pass a provider (e.g. OllamaProvider) to Agent().]"

        self.add_memory("user", message)

        personality_block = f"{self.personality}\n\n" if self.personality else ""

        prompt = f"""{personality_block}{self.recalled_context(message)}

User:
{message}
"""

        response = self.provider.generate(prompt)
        self.add_memory("assistant", response)
        self.learn_from_exchange(message, response)
        return response

    # Phrases people type as part of a *request to search* rather than
    # part of the actual topic - e.g. "web search and give me top places
    # in india" should search for "top places in india", not the literal
    # sentence including "web search and give me". Sent verbatim, that
    # extra command text pollutes the query and DuckDuckGo often returns
    # nothing relevant. Stripped from the front only (order matters -
    # longer/more specific patterns first so they win over a shorter
    # partial match).
    _SEARCH_COMMAND_PREFIXES = (
        r"^(please\s+)?(can|could)\s+you\s+",
        r"^(please\s+)?(do\s+a\s+|perform\s+a\s+)?web\s*search\s*(the\s*web\s*)?(for|on|about)?\s*(and\s+(give|tell|find)\s+me\s*)?",
        r"^(please\s+)?search\s+(the\s+)?web\s*(for|on|about)?\s*(and\s+(give|tell|find)\s+me\s*)?",
        r"^(please\s+)?google\s+(search\s+)?(for)?\s*",
        r"^(please\s+)?look\s*up\s*",
        r"^(please\s+)?find\s+me\s*",
        r"^(please\s+)?give\s+me\s*",
        r"^(please\s+)?tell\s+me\s*",
    )

    @classmethod
    def _clean_search_query(cls, text):
        """
        Strip leading command phrasing ("web search and give me...",
        "can you search for...") off `text`, leaving just the topic to
        actually search for. Applies prefixes repeatedly since more than
        one can stack ("can you web search and give me..."). Falls back
        to the original text if stripping would leave nothing.
        """
        cleaned = text.strip()
        changed = True
        while changed:
            changed = False
            for pattern in cls._SEARCH_COMMAND_PREFIXES:
                new = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
                if new != cleaned:
                    cleaned = new
                    changed = True
        return cleaned if cleaned else text.strip()

    def chat_with_search(self, message, max_results=4):
        """
        Like chat(), but first performs a real web search (DuckDuckGo,
        no API key - see web_search.py) and folds the results into the
        prompt, so the model answers using current information instead
        of only its fixed training data.

        If the search genuinely fails or finds nothing, this returns an
        honest message directly WITHOUT calling the LLM at all - this
        is a hard guarantee, not just a prompt instruction, because a
        prompt instruction alone ("say so if search didn't help") isn't
        reliably followed by every local model: in testing, a model
        given empty/failed search results still fabricated plausible-
        looking but fake URLs and headlines rather than admitting the
        search didn't work. Only when there ARE real results does this
        hand off to the LLM to summarize them.

        This is what powers both byteflow.agent's auto-detection (see
        _looks_like_search_request) and the explicit `web_search` tool.
        """
        if not self.provider:
            return "[No provider configured. Pass a provider (e.g. OllamaProvider) to Agent().]"

        from .web_search import search, WebSearchError

        self.add_memory("user", message)

        query = self._clean_search_query(message)

        try:
            results = search(query, max_results=max_results)
        except WebSearchError as e:
            answer = (
                f"I tried to search the web for \"{query}\", but it didn't work ({e}). "
                f"I don't want to guess or make up current information, so I can't "
                f"give you a reliable answer to that right now."
            )
            self.add_memory("assistant", answer)
            return answer

        if not results:
            answer = (
                f"I searched the web for \"{query}\" but didn't find any results. "
                f"I don't want to guess or make up an answer, so I can't help "
                f"with that specific question right now."
            )
            self.add_memory("assistant", answer)
            return answer

        search_block = "\n".join(
            f"[{i}] {r['title']}\n    {r['snippet']}\n    Source: {r['url']}"
            for i, r in enumerate(results, start=1)
        )

        personality_block = f"{self.personality}\n\n" if self.personality else ""

        prompt = f"""{personality_block}You have access to REAL, live web search results below
for the question "{message}". Answer using ONLY the information in
these results - never invent sources, URLs, statistics, or facts
beyond what's written here.

How to use these results well:
- Synthesize an actual answer in your own words; don't just list the
  results back at the person.
- If multiple results agree, give one confident, combined answer.
- If results disagree or are unclear, say so explicitly rather than
  picking one arbitrarily - mention the discrepancy.
- If the results are only partially relevant, answer what you can and
  clearly say what's still unknown - don't pad the gap with a guess.
- Reference which result(s) support a claim using [1], [2], etc. when
  it's useful for the person to know where something came from.
- Keep the answer focused and proportional to the question - a quick
  fact deserves a short answer, not a wall of text.

Search results:
{search_block}

{self.recalled_context(message)}

User:
{message}
"""

        response = self.provider.generate(prompt)
        self.add_memory("assistant", response)
        self.learn_from_exchange(message, response)
        return response

    # -----------------------------
    # SOCIAL POST DRAFTING (stage-only, never publishes)
    # -----------------------------
    # Known site URLs for the "open the right page" step. Add more as needed.
    _SOCIAL_SITE_URLS = {
        "linkedin": "https://www.linkedin.com/feed/?shareActive=true",
        "twitter": "https://twitter.com/compose/tweet",
        "x": "https://twitter.com/compose/tweet",
        "facebook": "https://www.facebook.com/",
    }

    def draft_social_post(self, topic, platform="linkedin", tone=None, open_site=True):
        """
        Draft a social media post with the LLM, copy it to the clipboard,
        and (by default) open the platform's compose page in your browser.

        This NEVER posts anything automatically - it stages the text for
        YOU to paste, review, and publish yourself. There is no browser
        automation, no clicking, no login handling. The actual "Post"
        button only gets clicked by a human, on purpose - that's not a
        missing feature, it's the safety boundary: ByteFlow can write
        words, but a human approves what goes out under their name.

        Returns a dict:
            {
                "draft": "<the generated post text>",
                "clipboard": bool,   # True if successfully copied
                "launched": bool,    # True if the site was opened
                "platform_url": str | None,
                "warning": str | None,  # set if something didn't work as expected
            }
        """
        if not self.provider:
            return {
                "draft": "[No provider configured. Pass a provider (e.g. OllamaProvider) to Agent().]",
                "clipboard": False,
                "launched": False,
                "platform_url": None,
                "warning": None,
            }

        platform_key = platform.lower()
        supported = sorted(set(self._SOCIAL_SITE_URLS.keys()))

        if platform_key not in self._SOCIAL_SITE_URLS:
            return {
                "draft": None,
                "clipboard": False,
                "launched": False,
                "platform_url": None,
                "warning": (
                    f"'{platform}' isn't a supported platform for draft_social_post - "
                    f"it has no text-compose page to open. Supported: {', '.join(supported)}. "
                    f"(YouTube, for example, doesn't have a quick text-post compose URL like "
                    f"LinkedIn/Twitter/Facebook do - posting there means uploading a video or "
                    f"writing a Community post from inside Studio, which this method doesn't target.)"
                ),
            }

        tone_instruction = f" Tone: {tone}." if tone else ""

        prompt = f"""Write a short, engaging {platform} post about the
following topic.{tone_instruction} Keep it natural and appropriately
sized for {platform} (concise - a few short paragraphs at most, not an
essay). Do not include hashtags unless they'd genuinely help. Return
ONLY the post text itself, with no preamble, no quotation marks around
it, and no explanation of what you wrote.

Topic: {topic}
"""

        draft = self.provider.generate(prompt).strip().strip('"')

        from .desktop_tools import write_clipboard, launch

        clipboard_result = write_clipboard(draft)
        clipboard_ok = not clipboard_result.startswith("Error")
        warning = None if clipboard_ok else clipboard_result

        launched = False
        platform_url = self._SOCIAL_SITE_URLS.get(platform_key)
        if open_site and platform_url:
            launch_result = launch(platform_url)
            launched = launch_result.startswith("Launched")
            if not launched:
                launch_warning = f"Could not open {platform}: {launch_result}"
                warning = f"{warning}; {launch_warning}" if warning else launch_warning

        return {
            "draft": draft,
            "clipboard": clipboard_ok,
            "launched": launched,
            "platform_url": platform_url,
            "warning": warning,
        }

    def draft_social_post_tool(self, topic=None, platform="linkedin", tone=None):
        """
        Tool-friendly wrapper around draft_social_post(): same behavior,
        but returns a single readable string instead of a dict, so it
        can be registered as a Tool and called by the planner/companion
        chat - e.g. "post about my new project on linkedin" can now
        actually trigger drafting + clipboard + opening the compose
        page, instead of the model only ever talking about doing it.

        If `topic` is omitted (a planner forgetting to extract one from
        a vague request like "post on linkedin" with no stated subject
        previously crashed with a raw TypeError), this falls back to
        asking what to post about instead of drafting something blind.
        """
        if not topic or not topic.strip():
            return (
                "I'd be happy to draft a post, but I need to know what it should be "
                "about - what topic, project, or update would you like the post to cover?"
            )

        result = self.draft_social_post(topic, platform=platform, tone=tone)

        if result["warning"] and result["draft"] is None:
            return result["warning"]

        lines = [f"Draft: {result['draft']}"]
        if result["clipboard"]:
            lines.append("Copied to clipboard.")
        else:
            lines.append("Could not copy to clipboard (pyperclip may not be installed).")
        if result["launched"]:
            lines.append(f"Opened {platform} - paste (Ctrl+V), review, and post yourself.")
        elif result["platform_url"]:
            lines.append(f"Could not open the browser. Go to: {result['platform_url']}")
        if result["warning"]:
            lines.append(f"Note: {result['warning']}")
        return "\n".join(lines)

    # -----------------------------
    # SINGLE STEP FALLBACK
    # -----------------------------
    def _single_step(self, prompt):
        tool_prompt = f"""
You are a tool-selection engine for an AI agent.

Available tools:
{list(self.tools.keys())}

Recent context (this is HISTORY - things that already happened, NOT
instructions for what to do now):
{self.recent_context()}

Current user request (decide based on THIS, not the history above):
{prompt}

Default to no tool. Only pick a tool if the CURRENT request CLEARLY and
DIRECTLY needs it - exact numbers for math, a clear file/folder path
for file tools, a clear app/site name for launch, a clear topic for
posting. For greetings, small talk, questions about the conversation
itself, or anything vague, no tool fits.

The "Recent context" is what ALREADY happened, not a new instruction.
If a previous message launched an app or drafted a post, and the
current request is unrelated, ignore that history - don't repeat an
old action just because it's mentioned recently.

If one of the available tools clearly fits, return ONLY:
{{"tool": "tool_name", "args": [arg1, arg2]}}

Otherwise return ONLY:
{{"tool": null, "answer": "<your direct answer to the user request>"}}

Examples:
  "add 10 and 20" -> {{"tool": "add", "args": [10, 20]}}
  "hii" -> {{"tool": null, "answer": "Hi! How can I help?"}}
  "what is my name" -> {{"tool": null, "answer": "<answer from context, or say you don't know yet>"}}
"""

        response = self.provider.generate(tool_prompt)
        data = self.extract_json(response)

        if not isinstance(data, dict):
            # model didn't return parseable JSON at all; fall back to chat
            return self.chat(prompt)

        tool_name = data.get("tool")

        if tool_name and tool_name in self.tools:
            args = self.safe_args(data.get("args", []))
            result = self.tools[tool_name].run(*args)
            self.add_memory("tool", f"{tool_name} -> {result}")
            return result

        # tool_name was set but isn't a real tool (hallucinated) - don't
        # trust it, fall back to chat instead of reporting "not found"
        if tool_name and tool_name not in self.tools:
            return self.chat(prompt)

        # no matching tool - use the model's direct answer, or fall back to chat
        answer = data.get("answer")
        if answer:
            self.add_memory("assistant", answer)
            return answer

        return self.chat(prompt)

    # -----------------------------
    # MAIN RUN LOOP (AUTONOMOUS)
    # -----------------------------
    # Phrases that strongly suggest the user wants code written/run/debugged,
    # checked before planning so coding requests don't get routed through
    # the tool-planner (which has nothing to do with writing code).
    _CODE_INTENT_PATTERNS = (
        "write code", "write a function", "write a script", "write a program",
        "code for", "python code", "debug this", "fix this code", "fix this bug",
        "write python", "implement a", "implement the", "code to ",
    )

    def _looks_like_code_request(self, prompt):
        p = prompt.lower()
        return any(pattern in p for pattern in self._CODE_INTENT_PATTERNS)

    # Phrases/patterns that strongly suggest plain conversation rather
    # than a tool-using task - checked before the planner, so small local
    # models aren't asked to pick a tool out of a long list for messages
    # that obviously need none. This is what stops "hii" or "what is my
    # name" from getting misrouted to list_files/write_clipboard.
    _CHAT_INTENT_PATTERNS = (
        "hi", "hii", "hey", "hello", "yo", "sup",
        "thanks", "thank you", "ok", "okay", "cool", "nice", "great",
        "what is my name", "what's my name", "do you remember",
        "who are you", "how are you", "bye", "goodbye",
    )

    def _looks_like_chat_only(self, prompt):
        p = prompt.strip().lower().rstrip("!.?")
        if not p:
            return True
        # very short messages and pure punctuation/filler ("...", "ok", "..")
        # are essentially never a tool-using request
        if len(p) <= 3 and not any(ch.isdigit() for ch in p):
            return True
        return any(p == pat or p.startswith(pat + " ") for pat in self._CHAT_INTENT_PATTERNS)

    # Patterns for plain date/time questions - these get answered
    # directly from the system clock (100% accurate, instant, no LLM
    # or network needed) rather than asked of the model or searched.
    # A model has no reliable way to know "today's date" on its own,
    # and searching the web for it is needless latency for something
    # the computer already knows with certainty. This fixes a real
    # observed bug: without this, "what's today's date" went through
    # chat_with_search() and the model returned the literal placeholder
    # text "[current date]" instead of a real date when the search
    # didn't clearly answer it.
    # Word-combination check rather than enumerated exact phrases - a
    # real reported bug: "today date" (terse, no question grammar at
    # all) wasn't caught by an earlier version of this that only
    # matched fixed phrases like "what is today's date". Real people
    # type short, keyword-style queries, not full questions - this
    # checks for a date/time WORD plus a present/now WORD anywhere in
    # a short message, which is robust to phrasing and word order.
    _DATE_WORDS = ("date", "day", "year")
    _TIME_WORDS = ("time", "clock")
    _PRESENT_WORDS = ("today", "todays", "current", "currently", "now")

    @staticmethod
    def _contains_word(text, word):
        """Whole-word match, not substring - so "day" doesn't match
        inside "today" (a real bug: that substring overlap meant any
        message containing the word "today" alone triggered a false
        positive, since "today" contains "day")."""
        return re.search(rf"\b{re.escape(word)}\b", text) is not None

    def _looks_like_datetime_request(self, prompt):
        p = prompt.strip().lower().rstrip("!.?")
        if not p or len(p) > 60:
            # long messages are very unlikely to be a pure date/time
            # ask - avoids false-positiving on a sentence that happens
            # to mention "today" deep inside a longer, unrelated message
            return False

        words = re.findall(r"\w+", p)

        date_time_positions = [
            i for i, w in enumerate(words) if w in self._DATE_WORDS + self._TIME_WORDS
        ]
        present_positions = [i for i, w in enumerate(words) if w in self._PRESENT_WORDS]

        if date_time_positions and present_positions:
            # require the closest pair to be near each other (within 2
            # words) - a real question has them adjacent ("today date",
            # "current time", "what's today's date"); an unrelated
            # sentence that merely mentions both words far apart
            # ("today was a good day at work") should not match
            closest_gap = min(
                abs(d - pr) for d in date_time_positions for pr in present_positions
            )
            if closest_gap <= 2:
                return True

        # "what day is it" / "what year is it" don't contain a present
        # word at all, so also accept "is it" as a stand-in for that
        # specific question shape
        if date_time_positions and "is it" in p:
            return True

        return False

    def _answer_datetime_request(self, prompt):
        from datetime import datetime
        now = datetime.now()
        p = prompt.strip().lower()
        wants_time = any(self._contains_word(p, w) for w in self._TIME_WORDS)
        wants_date = any(self._contains_word(p, w) for w in self._DATE_WORDS)
        if wants_time and not wants_date:
            return f"It's currently {now.strftime('%I:%M %p')} (system local time)."
        return f"Today's date is {now.strftime('%A, %B %d, %Y')}."

    # Phrases/patterns that strongly suggest the question needs current,
    # real-world information the model's training data can't have (the
    # model has a fixed knowledge cutoff and no built-in way to know
    # today's date, recent events, current prices, etc.) - checked
    # before chat()/the planner so these get a web search folded into
    # the prompt automatically, rather than the model guessing or
    # giving an outdated answer with false confidence.
    #
    # Deliberately specific multi-word patterns rather than bare words
    # like "current" or "today" alone - those false-positive on personal
    # questions like "what is my current project status" or "today I
    # learned X", which have nothing to do with needing a web search.
    _SEARCH_INTENT_PATTERNS = (
        "latest news", "latest update", "latest version", "what's the latest",
        "current price", "current weather", "current president",
        "current prime minister", "current ceo", "current events",
        "today's weather", "today's news", "news today",
        "this week's", "this month's", "this year's",
        "right now in", "as of now",
        "what's new with", "what is new with", "what's happening with",
        "who is the current", "who is the president", "who is the prime minister",
        "who is the ceo of", "who is the current ceo",
        "stock price", "exchange rate",
        "weather in", "weather today", "weather forecast",
        "news about", "news on", "breaking news",
        "recent developments", "recent news",
        "who won", "final score", "live score",
    )

    # Topic words that are almost always asked about because someone wants
    # up-to-the-minute info (weather, sports fixtures/scores, etc), paired
    # with a "right now" word - same word-order-agnostic proximity idea as
    # _looks_like_datetime_request, since real queries are terse and don't
    # respect fixed phrase order ("today weather" as often as "weather
    # today"). This is what fixes queries like "today weather" and "fifa
    # match today" that a fixed phrase list alone would miss.
    _SEARCH_TOPIC_WORDS = (
        "weather", "match", "score", "scores", "fixture", "fixtures",
        "game", "tournament", "standings", "schedule",
    )
    _SEARCH_PRESENT_WORDS = (
        "today", "todays", "tonight", "now", "current", "currently",
        "latest", "live", "tomorrow",
    )

    # A few topics that are inherently about "right now" even with no
    # explicit present-tense word attached ("fifa match" almost always
    # means "what's on / what happened", not a request to explain what
    # FIFA is) - kept short and specific to avoid false positives.
    # NOTE: "weather" is deliberately NOT here - it's handled by the
    # topic+present-word pairing above instead, so general/hypothetical
    # weather questions ("what's the weather usually like in winter")
    # don't get force-routed to a live search.
    _ALWAYS_SEARCH_TOPICS = ("fifa", "world cup")

    def _looks_like_search_request(self, prompt):
        p = prompt.lower()
        if any(pattern in p for pattern in self._SEARCH_INTENT_PATTERNS):
            return True

        # "top N ... today/this week" - e.g. "top 10 ai news today",
        # "top 5 movies this week" - a shape that's hard to enumerate
        # as fixed phrases since the topic word varies every time
        if re.search(r"\btop\s+\d+\b", p) and any(
            w in p for w in ("today", "this week", "this month", "this year", "now")
        ):
            return True

        words = re.findall(r"\w+", p)

        # word-order-agnostic pairing: a "right now" topic (weather,
        # match, score...) near a "right now" word (today, live,
        # current...) anywhere in the message - catches "today weather"
        # as readily as "weather today"
        topic_positions = [i for i, w in enumerate(words) if w in self._SEARCH_TOPIC_WORDS]
        present_positions = [i for i, w in enumerate(words) if w in self._SEARCH_PRESENT_WORDS]
        if topic_positions and present_positions:
            closest_gap = min(
                abs(t - pr) for t in topic_positions for pr in present_positions
            )
            if closest_gap <= 3:
                return True

        # a small set of topics that are inherently about "right now"
        # even with no present-tense word attached at all
        if len(p) <= 60 and any(
            self._contains_word(p, w) for w in self._ALWAYS_SEARCH_TOPICS
        ):
            return True

        return False

    # Cues that show up in the agent's OWN previous reply when it asked
    # the person to clarify a location for a weather question (see the
    # personality/chat() prompt - the model naturally asks this when a
    # weather question has no place in it). Used to recognize the next
    # turn as an answer to THAT question rather than a new, unrelated
    # topic - a real observed bug: asking "today weather" -> agent asks
    # "which city?" -> answering "ahmedabad" got treated as a brand new
    # standalone message ("Ahmedabad is a city in India") instead of
    # being reattached to the pending weather question.
    _LOCATION_CLARIFICATION_CUES = (
        "specify a location", "specify a city", "which city",
        "which location", "what city", "what location",
    )

    def _pending_weather_location_followup(self, prompt):
        """
        If the agent's last reply asked for a location to answer a
        weather question, and `prompt` looks like a bare place-name
        answer (short, no question mark, not itself a new command),
        return a proper standalone search query combining the two
        ("weather in ahmedabad today"). Otherwise return None.
        """
        p = prompt.strip()
        if not p or "?" in p:
            return None
        word_count = len(p.split())
        if word_count > 4:
            return None
        # a bare answer shouldn't itself look like a new request
        if (
            self._looks_like_datetime_request(prompt)
            or self._looks_like_code_request(prompt)
            or self._looks_like_chat_only(prompt)
        ):
            return None

        recent = self.memory.get_recent(2)
        if len(recent) < 1:
            return None
        last = recent[-1]
        if last.get("role") != "assistant":
            return None
        last_content = last.get("content", "").lower()
        if any(cue in last_content for cue in self._LOCATION_CLARIFICATION_CUES):
            return f"weather in {p} today"
        return None

    def run(self, prompt, execute_code=True):
        """
        Main autonomous entrypoint: try to plan + execute tool calls.
        Falls back to plain chat if no plan or tools apply.

        Requests that clearly look like coding tasks (e.g. "write a
        function that...", "debug this code...") are routed to code()
        instead, so you get real generated/executed code rather than the
        tool-planner trying (and failing) to handle it.

        Requests that clearly look like plain conversation (greetings,
        short filler, "what's my name") skip the tool planner entirely -
        with several tools registered, asking a small local model to pick
        one for every message (even "hii") leads to it guessing wrong
        rather than recognizing no tool is needed.

        Requests that clearly need current, real-world information
        (e.g. "latest news on X", "who is the current Y") are routed to
        chat_with_search(), which performs a real web search and folds
        the results into the prompt before answering - see
        _looks_like_search_request and web_search.py.

        Plain date/time questions ("what's today's date") are answered
        directly from the system clock - no LLM call, no web search,
        100% accurate and instant. This fixes a real observed bug where
        the model returned the literal placeholder text "[current date]"
        when asked this through a search-based path.
        """
        if not self.provider:
            return prompt

        followup_query = self._pending_weather_location_followup(prompt)
        if followup_query is not None:
            return self.chat_with_search(followup_query)

        if self._looks_like_datetime_request(prompt):
            return self._answer_datetime_request(prompt)

        if self._looks_like_code_request(prompt):
            return self.code(prompt, execute=execute_code)

        if self._looks_like_chat_only(prompt):
            return self.chat(prompt)

        if self._looks_like_search_request(prompt):
            return self.chat_with_search(prompt)

        # STEP 1: PLAN
        plan = self.plan(prompt)

        # fallback if planning fails - let _single_step decide tool vs chat
        if not plan:
            return self._single_step(prompt)

        self.add_memory("user", prompt)
        results = []

        # STEP 2: EXECUTE PLAN
        for step in plan:
            tool_name = step.get("step")
            args = self.safe_args(step.get("args", []))

            if tool_name in self.tools:
                try:
                    result = self.tools[tool_name].run(*args)
                    results.append(result)

                    # store memory
                    self.add_memory("tool", f"{tool_name} -> {result}")

                except Exception as e:
                    results.append(f"[Tool Error]: {str(e)}")

            else:
                # Should not happen since plan() validates tool names upfront,
                # but kept as a defensive fallback in case that ever changes.
                results.append(f"Tool not found: {tool_name}")

        # STEP 3: RETURN RESULT
        return results