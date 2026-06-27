"""
ByteFlow Desktop Companion - a small, always-on-top robot character that
sits on your screen and opens a chat panel when clicked.

Run it with:
    python -m byteflow.companion
or:
    from byteflow.companion import run_companion
    run_companion()

Requires tkinter, which ships with the standard Python installer on
Windows and macOS. On some Linux distros it's a separate package:
    sudo apt install python3-tk

This is a genuinely different kind of artifact than the rest of
ByteFlow: a long-running GUI app, not a one-shot CLI command. The
agent-calling logic below is deliberately kept separate from the
Tkinter drawing code (see CompanionController) so it can be tested
without a display.
"""

import queue
import threading


class CompanionController:
    """
    The non-visual brain of the companion: owns the Agent, and runs
    each chat message on a background thread so the GUI never freezes
    while waiting for the LLM. Results land in a thread-safe queue that
    the Tkinter main loop polls periodically.

    Kept separate from any Tkinter code so this logic can be tested
    without a display (see tests/test_byteflow.py).
    """

    def __init__(self, agent, speak_replies=False):
        self.agent = agent
        self.replies = queue.Queue()
        self._busy = False

        self.speaker = None
        if speak_replies:
            from .voice import Speaker, tts_available
            if tts_available():
                self.speaker = Speaker()
            # if not available, silently stay text-only - run_companion()
            # is responsible for warning the user about this up front

    @property
    def busy(self):
        return self._busy

    def speak(self, text):
        """Speak `text` aloud on a background thread, if a Speaker is configured.
        No-op (returns immediately) if voice output isn't set up."""
        if not self.speaker or not text:
            return

        def worker():
            try:
                self.speaker.speak(text)
            except Exception:
                pass  # voice output failing should never crash the companion

        threading.Thread(target=worker, daemon=True).start()

    def send(self, message):
        """
        Send a message to the agent on a background thread. Non-blocking -
        returns immediately. The reply (or an error string) will show up
        in self.replies once ready; poll it from the GUI loop.

        Uses agent.run(), the same smart entrypoint as `byteflow run` -
        so the companion has access to everything: registered tools
        (math, desktop helpers if you registered them), auto-routed
        coding mode (generates AND runs code), and falls back to plain
        chat for everything else. This is what gives the companion
        "all the modules" rather than only ever chatting.
        """
        if self._busy:
            self.replies.put("[Still thinking about your last message - one moment.]")
            return

        if not message or not message.strip():
            return

        self._busy = True

        def worker():
            try:
                result = self.agent.run(message)
                reply = self._format_result(result)
            except Exception as e:
                reply = f"[Error: {e}]"
            finally:
                self._busy = False
            self.replies.put(reply)

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _format_result(result):
        """
        agent.run() can return a plain string (chat/tool results) or a
        dict (code mode's {"code": ..., "result": ...}). Normalize both
        into a single readable string for the chat panel.
        """
        if isinstance(result, dict) and "code" in result:
            lines = ["Here's the code:", "", result["code"]]
            exec_result = result.get("result")
            if result.get("executed") and exec_result is not None:
                lines.append("")
                lines.append("Output:")
                lines.append(exec_result.format())
            return "\n".join(lines)

        return str(result)

    @staticmethod
    def speech_friendly(reply):
        """
        Shorten a reply for speaking aloud. Reading raw Python source
        character-by-character via TTS is a bad experience, so code
        blocks get summarized instead of read verbatim.
        """
        if reply.startswith("Here's the code:"):
            if "Output:" in reply:
                output_part = reply.split("Output:", 1)[1].strip()
                # strip the "--- stdout ---" / "--- stderr ---" section
                # markers from sandbox.ExecutionResult.format() - they
                # read awkwardly aloud and add no spoken value
                output_part = output_part.replace("--- stdout ---", "").replace("--- stderr ---", "").strip()
                if output_part:
                    return f"I wrote the code and ran it. The result was: {output_part}"
                return "I wrote the code and ran it, but there was no output."
            return "I wrote the code for you - take a look at the panel."
        return reply

    def poll_reply(self):
        """Return the next available reply, or None if nothing's ready yet."""
        try:
            return self.replies.get_nowait()
        except queue.Empty:
            return None


# ---------------------------------------------------------------------------
# GUI (Tkinter) - only imported/used when actually running the companion
# ---------------------------------------------------------------------------

def _build_face(canvas, size=120):
    """
    Draw a box-faced robot with TWO glowing eyes - each one a soft
    multi-step glow falloff behind a glassy iris, a dark pupil, and a
    bright highlight glint for a genuinely alive, camera-lens feel.
    No image files required, so this works out of the box on a fresh
    install.

    Tkinter's Canvas has no gradient fill support, so the "glassy"
    look is approximated with several flat-color concentric ovals
    stepping from dim (outer glow) to bright (inner iris) - verified
    by rendering the exact same shapes/colors as SVG and inspecting
    the result, since this environment has no display to test
    against directly.

    Returns (head, eye_layers, eye_layers, halo_items) - eye_layers is
    ONE combined dict covering both eyes (keys prefixed "l_"/"r_"), put
    in both the second and third return slots so existing callers that
    unpack (head, left_eye, right_eye, antenna) keep working unchanged:
    _set_eyes_color()/_set_eyes_visible() read from the first of the
    two and apply to every layer (both eyes) either way.
    """
    pad = 8
    head = canvas.create_rectangle(
        pad, pad, size - pad, size - pad,
        fill="#3b4252", outline="#88c0d0", width=2.5, tags="head",
    )

    # antenna: stem + glowing tip
    cx = size / 2
    canvas.create_line(cx, pad, cx, pad - 14, fill="#88c0d0", width=2.5)
    antenna_halo = canvas.create_oval(
        cx - 9, pad - 25, cx + 9, pad - 7,
        fill="#3b4252", outline="#a3be8c", width=1,
    )
    antenna_tip = canvas.create_oval(
        cx - 5, pad - 21, cx + 5, pad - 11,
        fill="#a3be8c", outline="",
    )

    def _draw_eye(eye_x, eye_y, r):
        """Draw one glowing eye centered at (eye_x, eye_y) with radius r.
        Returns a dict of this eye's canvas item ids."""
        glow_outer = canvas.create_oval(
            eye_x - r * 1.55, eye_y - r * 1.55, eye_x + r * 1.55, eye_y + r * 1.55,
            fill="#3e5063", outline="",
        )
        glow_inner = canvas.create_oval(
            eye_x - r * 1.25, eye_y - r * 1.25, eye_x + r * 1.25, eye_y + r * 1.25,
            fill="#45596c", outline="",
        )
        ring = canvas.create_oval(
            eye_x - r, eye_y - r, eye_x + r, eye_y + r,
            fill="#5e9aae", outline="#eceff4", width=1.5,
        )
        iris_outer = canvas.create_oval(
            eye_x - r * 0.86, eye_y - r * 0.86, eye_x + r * 0.7, eye_y + r * 0.7,
            fill="#88c0d0", outline="",
        )
        iris_inner = canvas.create_oval(
            eye_x - r * 0.64, eye_y - r * 0.64, eye_x + r * 0.36, eye_y + r * 0.36,
            fill="#a9d3df", outline="",
        )
        core = canvas.create_oval(
            eye_x - r * 0.36, eye_y - r * 0.36, eye_x + r * 0.36, eye_y + r * 0.36,
            fill="#212730", outline="",
        )
        spark = canvas.create_oval(
            eye_x - r * 0.29, eye_y - r * 0.31, eye_x - r * 0.03, eye_y - r * 0.05,
            fill="#eceff4", outline="",
        )
        spark_small = canvas.create_oval(
            eye_x + r * 0.15, eye_y + r * 0.17, eye_x + r * 0.25, eye_y + r * 0.27,
            fill="#eceff4", outline="",
        )
        return {
            "glow_outer": glow_outer, "glow_inner": glow_inner, "ring": ring,
            "iris_outer": iris_outer, "iris_inner": iris_inner,
            "core": core, "spark": spark, "spark_small": spark_small,
            "iris": iris_outer,  # backward-compat alias
        }

    # --- two eyes, side by side ---
    eye_y = size * 0.42
    r = size * 0.155  # smaller than the old single-eye radius so two fit cleanly
    gap = size * 0.20  # half-distance between the two eye centers

    left_layers = _draw_eye(size * 0.5 - gap, eye_y, r)
    right_layers = _draw_eye(size * 0.5 + gap, eye_y, r)

    # combine into ONE dict covering both eyes, so a single call to
    # _set_eyes_color()/_set_eyes_visible() updates both at once - every
    # existing call site already passes the same value as both the
    # "left_eye" and "right_eye" argument, so this just needs the dict
    # itself to contain both eyes' items under prefixed keys.
    eye_layers = {}
    for key, item_id in left_layers.items():
        eye_layers[f"l_{key}"] = item_id
    for key, item_id in right_layers.items():
        eye_layers[f"r_{key}"] = item_id

    # mouth indicator (a thin glowing bar rather than a hard line)
    canvas.create_rectangle(
        size * 0.32, size * 0.78, size * 0.68, size * 0.815,
        fill="#4c566a", outline="",
    )

    return head, eye_layers, eye_layers, (antenna_halo, antenna_tip)


def _set_eyes_color(canvas, left_dots, right_dots, color):
    """
    Recolor both eyes to `color`. left_dots/right_dots are both the
    same combined eye_layers dict (see _build_face) - kept as two
    parameters so every existing call site (set_status, poll_loop,
    etc.) works unchanged. Recolors each eye's iris body and ring rim
    together so both eyes visibly shift color (thinking/idle/unread);
    the glow rings, dark pupils, and glints stay put for visual structure.
    """
    layers = left_dots
    for prefix in ("l_", "r_"):
        canvas.itemconfig(layers[f"{prefix}iris_outer"], fill=color)
        canvas.itemconfig(layers[f"{prefix}ring"], fill=color)


def _set_eyes_visible(canvas, left_dots, right_dots, visible):
    """Show/hide both eyes for blinking - hides the iris/pupil/glint
    layers so a blink reads as the eyes 'closing' rather than the whole
    face vanishing (the outer glow stays, like eyelids over still-present eyes)."""
    layers = left_dots
    state = "normal" if visible else "hidden"
    for prefix in ("l_", "r_"):
        for key in ("iris_outer", "iris_inner", "core", "spark", "spark_small"):
            canvas.itemconfig(layers[f"{prefix}{key}"], state=state)


def run_companion(agent=None, model="llama3", enable_desktop_tools=True,
                   voice_input=False, voice_output=False, conversation_mode=False):
    """
    Launch the desktop companion window. Blocks until the window is closed.

    agent: an existing byteflow.Agent to use. If omitted, a new one is
           created with OllamaProvider(model=model), persistent memory
           at ~/.byteflow/memory.json (same default as the CLI), and
           builtin (math) + desktop tools registered so it has access
           to the same capabilities as `byteflow run` - coding mode,
           tool calling, desktop helpers - not just plain chat.
    enable_desktop_tools: if True (default) and `agent` is omitted,
           registers desktop helper tools (launch/list/search/clipboard/
           organize) on the auto-created agent. Has no effect if you
           pass your own `agent` - register tools on it yourself first.
    voice_input: if True, adds a push-to-talk microphone button to the
           chat panel (requires 'vosk' + 'sounddevice' and a downloaded
           Vosk model - see byteflow/voice.py). If unavailable, the
           button is simply omitted with a one-time printed notice -
           never a crash.
    voice_output: if True, replies are spoken aloud via your OS's
           built-in voice (requires 'pyttsx3'). Same graceful
           degradation if unavailable.
    conversation_mode: if True, adds a second toggle for hands-free,
           continuous listening - no clicking per utterance, it
           automatically detects when you start/stop talking (see
           voice.ConversationListener). Off by default; you explicitly
           opt in to always-on listening, and can turn it off again at
           any time by clicking the toggle.
    """
    import tkinter as tk
    from tkinter import font as tkfont
    import os

    if agent is None:
        from .agent import Agent
        from .providers.ollama_provider import OllamaProvider
        from .builtin_tools import register_builtin_tools
        memory_path = os.path.join(os.path.expanduser("~"), ".byteflow", "memory.json")
        os.makedirs(os.path.dirname(memory_path), exist_ok=True)
        agent = Agent(provider=OllamaProvider(model=model), memory_path=memory_path)
        register_builtin_tools(agent)
        if enable_desktop_tools:
            from .desktop_tools import register_desktop_tools
            register_desktop_tools(agent)

    controller = CompanionController(agent, speak_replies=voice_output)
    if voice_output and controller.speaker is None:
        print("[Companion] voice_output requested but 'pyttsx3' isn't installed - "
              "staying text-only. Install with: pip install pyttsx3")

    listener = None
    if voice_input:
        from .voice import Listener, stt_available, vosk_model_present, DEFAULT_VOSK_MODEL_DIR
        if not stt_available():
            print("[Companion] voice_input requested but 'vosk'/'sounddevice' aren't installed - "
                  "staying text-only. Install with: pip install vosk sounddevice")
        elif not vosk_model_present():
            print(f"[Companion] voice_input requested but no Vosk model found at "
                  f"{DEFAULT_VOSK_MODEL_DIR} - staying text-only. Run "
                  f"'python -m byteflow.voice' for download instructions.")
        else:
            try:
                listener = Listener()
            except Exception as e:
                print(f"[Companion] could not start voice input ({e}) - staying text-only.")

    conversation_listener = None
    if conversation_mode:
        from .voice import ConversationListener, stt_available, vosk_model_present, DEFAULT_VOSK_MODEL_DIR
        if not stt_available():
            print("[Companion] conversation_mode requested but 'vosk'/'sounddevice' aren't installed - "
                  "skipping. Install with: pip install vosk sounddevice")
        elif not vosk_model_present():
            print(f"[Companion] conversation_mode requested but no Vosk model found at "
                  f"{DEFAULT_VOSK_MODEL_DIR} - skipping. Run "
                  f"'python -m byteflow.voice' for download instructions.")
        # ConversationListener itself is constructed later, once the GUI
        # callbacks it needs (to show transcripts / send messages) exist.

    root = tk.Tk()
    root.title("ByteFlow")
    root.overrideredirect(True)       # no title bar - just the character
    root.attributes("-topmost", True)  # always-on-top
    root.geometry("140x140+80+80")
    root.configure(bg="#2e3440")

    # allow dragging the window by clicking+holding the character; a
    # short click (no real movement) instead toggles the chat panel -
    # see on_press/on_motion/on_release below
    drag_state = {"x": 0, "y": 0, "moved": False}

    face_canvas = tk.Canvas(root, width=140, height=140, bg="#2e3440", highlightthickness=0)
    face_canvas.pack()
    head, left_eye, right_eye, antenna_items = _build_face(face_canvas, size=140)

    # --- chat panel (hidden until the character is clicked) ---
    chat_win = tk.Toplevel(root)
    chat_win.withdraw()
    chat_win.overrideredirect(True)
    chat_win.attributes("-topmost", True)
    chat_win.configure(bg="#2e3440", highlightthickness=1, highlightbackground="#4c566a")

    chat_font = tkfont.Font(family="Segoe UI", size=10)
    chat_font_bold = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    badge_font = tkfont.Font(family="Segoe UI", size=8, weight="bold")

    header = tk.Frame(chat_win, bg="#3b4252")
    header.pack(fill="x")
    tk.Label(
        header, text="ByteFlow", font=chat_font_bold, bg="#3b4252", fg="#eceff4",
    ).pack(side="left", padx=(10, 6), pady=7)

    mode_badge = tk.Label(
        header, text="TEXT", font=badge_font, bg="#88c0d0", fg="#2e3440",
        padx=6, pady=1,
    )
    mode_badge.pack(side="left", pady=7)

    def set_mode_badge(label, color):
        mode_badge.configure(text=label, bg=color)

    close_btn = tk.Label(
        header, text="\u2715", font=chat_font, bg="#3b4252", fg="#9aa5b1", cursor="hand2",
    )
    close_btn.pack(side="right", padx=(0, 10), pady=7)
    close_btn.bind("<Button-1>", lambda e: toggle_chat())

    text_area = tk.Text(
        chat_win, width=42, height=12, bg="#2e3440", fg="#eceff4",
        font=chat_font, wrap="word", state="disabled", padx=10, pady=8,
        borderwidth=0, highlightthickness=0,
    )
    text_area.pack(fill="both", expand=True, padx=8, pady=(8, 6))
    text_area.tag_configure("sender_you", foreground="#88c0d0", font=chat_font_bold)
    text_area.tag_configure("sender_bf", foreground="#a3be8c", font=chat_font_bold)
    text_area.tag_configure("sender_sys", foreground="#ebcb8b", font=chat_font_bold)
    text_area.tag_configure("sender_hearing", foreground="#9aa5b1", font=chat_font)

    input_row = tk.Frame(chat_win, bg="#2e3440")
    input_row.pack(fill="x", padx=8, pady=(0, 10))

    entry = tk.Entry(
        input_row, font=chat_font, bg="#434c5e", fg="#eceff4",
        insertbackground="#eceff4", relief="flat",
    )
    # NOTE: entry.pack() is deliberately called further down, AFTER the
    # upload button is created - Tkinter's pack() lays out left-to-right
    # in call order, and entry uses expand=True which would otherwise
    # claim all space before the upload button gets a chance to sit to
    # its left.

    def _icon_button(parent, symbol, tooltip_text, command, bg="#4c566a"):
        btn = tk.Label(
            parent, text=symbol, font=("Segoe UI", 12), bg=bg, fg="#eceff4",
            width=2, cursor="hand2", padx=2, pady=4,
        )
        btn.bind("<Button-1>", lambda e: command())
        return btn

    def _sender_tag(sender):
        if sender == "You":
            return "sender_you"
        if sender == "ByteFlow":
            return "sender_bf"
        if sender == "(hearing)":
            return "sender_hearing"
        return "sender_sys"

    def append_message(sender, text):
        text_area.configure(state="normal")
        text_area.insert("end", f"{sender}: ", _sender_tag(sender))
        text_area.insert("end", f"{text}\n\n")
        text_area.configure(state="disabled")
        text_area.see("end")

    def set_status(thinking):
        # visual cue: eyes + antenna swap color while thinking vs idle
        _set_eyes_color(face_canvas, left_eye, right_eye, "#ebcb8b" if thinking else "#88c0d0")
        face_canvas.itemconfig(antenna_items[1], fill="#ebcb8b" if thinking else "#a3be8c")

    def on_send(event=None):
        message = entry.get().strip()
        if not message:
            return
        entry.delete(0, "end")
        append_message("You", message)
        set_status(True)
        controller.send(message)

    def on_upload():
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Upload a file to ask ByteFlow about",
            parent=chat_win,
        )
        if not path:
            return  # user cancelled

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as e:
            append_message("System", f"[Error] Could not read {path}: {e}")
            return

        filename = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]

        # Ingest the FULL file into the vector store - chunked automatically
        # if it's long (see chunking.py) - rather than truncating it or
        # dumping the whole thing into this one message. recalled_context()
        # will pull in just the relevant chunk(s) for whatever you ask
        # about it next, even for files far too big to fit in one prompt.
        n_chunks = agent.ingest_document(content, source=filename)

        append_message("You", f"(uploaded {filename} - {n_chunks} chunk(s) indexed)")
        set_status(True)

        preview = content[:400] + ("..." if len(content) > 400 else "")
        message = (
            f"I uploaded a file called `{filename}` ({len(content)} characters, "
            f"indexed in {n_chunks} chunk(s)). Here's a preview:\n\n```\n{preview}\n```\n\n"
            f"Take a look and let me know what you think, or help with whatever I ask about it next."
        )
        controller.send(message)

    upload_button = _icon_button(input_row, "\U0001F4CE", "Upload a file", on_upload)
    upload_button.pack(side="left", padx=(0, 6))

    entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))

    send_button = tk.Button(
        input_row, text="Send", command=on_send, bg="#5e81ac", fg="white",
        activebackground="#81a1c1", relief="flat", padx=12, pady=4,
        font=chat_font,
    )
    send_button.pack(side="right")
    entry.bind("<Return>", on_send)

    if listener is not None:
        set_mode_badge("VOICE", "#88c0d0")
        recording_state = {"active": False}

        def toggle_recording():
            if not recording_state["active"]:
                recording_state["active"] = True
                mic_button.configure(text="\u23f9", bg="#bf616a")
                set_mode_badge("LISTENING", "#bf616a")
                append_message("System", "Listening... click the mic again when you're done.")
                listener.start_recording()
            else:
                recording_state["active"] = False
                mic_button.configure(text="\U0001F3A4", bg="#5e81ac")
                set_mode_badge("VOICE", "#88c0d0")

                def transcribe_worker():
                    try:
                        text = listener.stop_recording()
                    except Exception as e:
                        root.after(0, lambda: append_message("System", f"[Voice error: {e}]"))
                        return

                    if text:
                        root.after(0, lambda: (entry.delete(0, "end"), entry.insert(0, text), on_send()))
                    else:
                        root.after(0, lambda: append_message("System", "(didn't catch that - try again)"))

                threading.Thread(target=transcribe_worker, daemon=True).start()

        mic_button = tk.Button(
            input_row, text="\U0001F3A4", command=toggle_recording,
            bg="#5e81ac", fg="white", activebackground="#81a1c1", relief="flat",
            padx=8, pady=4, font=chat_font,
        )
        mic_button.pack(side="right", padx=(6, 0))

    if conversation_mode:
        from .voice import ConversationListener, stt_available, vosk_model_present

        conv_state = {"active": False, "listener": None}

        def on_utterance(text):
            # called from the audio callback thread - marshal to main thread
            def handle():
                entry.delete(0, "end")
                entry.insert(0, text)
                on_send()
            root.after(0, handle)

        hearing_mark = {"start": None}

        def on_partial(text):
            def handle():
                text_area.configure(state="normal")
                if hearing_mark["start"] is not None:
                    # overwrite the previous partial line in place, instead
                    # of appending a new one each time - keeps the chat log
                    # from filling up with every intermediate guess
                    text_area.delete(hearing_mark["start"], "end")
                else:
                    hearing_mark["start"] = text_area.index("end-1c")
                text_area.insert("end", f"(hearing): {text}\n\n")
                text_area.configure(state="disabled")
                text_area.see("end")
            root.after(0, handle)

        def on_listening_change(is_active):
            def handle():
                set_status(is_active)
                if is_active:
                    set_mode_badge("HEARING", "#bf616a")
                elif conv_state["active"]:
                    set_mode_badge("CONVERSATION", "#a3be8c")
            root.after(0, handle)

        def toggle_conversation_mode():
            if not conv_state["active"]:
                if not stt_available() or not vosk_model_present():
                    append_message(
                        "System",
                        "Conversation mode needs 'vosk'+'sounddevice' installed and a "
                        "downloaded model - run 'python -m byteflow.voice' for instructions.",
                    )
                    return
                try:
                    conv_state["listener"] = ConversationListener(
                        on_utterance=on_utterance,
                        on_partial=on_partial,
                        on_listening_change=on_listening_change,
                    )
                    conv_state["listener"].start()
                except Exception as e:
                    append_message("System", f"[Voice error: {e}]")
                    return
                conv_state["active"] = True
                conv_button.configure(text="\U0001F50A On", bg="#a3be8c")
                set_mode_badge("CONVERSATION", "#a3be8c")
                append_message("System", "Conversation mode on - just talk, no clicking needed.")
            else:
                if conv_state["listener"] is not None:
                    conv_state["listener"].stop()
                    conv_state["listener"] = None
                conv_state["active"] = False
                conv_button.configure(text="\U0001F507 Off", bg="#5e81ac")
                set_mode_badge("TEXT", "#88c0d0")
                append_message("System", "Conversation mode off.")

        conv_button = tk.Button(
            input_row, text="\U0001F507 Off", command=toggle_conversation_mode,
            bg="#5e81ac", fg="white", activebackground="#81a1c1", relief="flat",
            padx=8, pady=4, font=chat_font,
        )
        conv_button.pack(side="right", padx=(6, 0))

    chat_visible = {"value": False}

    def position_chat_window():
        x = root.winfo_x() + 150
        y = root.winfo_y()
        # Fix the WIDTH and POSITION, but let Tkinter compute the actual
        # required HEIGHT from its contents. update_idletasks() forces a
        # geometry pass so winfo_reqheight() reflects everything that's
        # actually packed in (header + text area + input row), instead
        # of a hardcoded guess that silently clips/collapses widgets
        # (e.g. the input row disappearing) whenever something gets
        # added later and the old fixed height no longer fits.
        chat_win.update_idletasks()
        needed_height = max(chat_win.winfo_reqheight(), 320)  # sane floor, just in case
        chat_win.geometry(f"320x{needed_height}+{x}+{y}")

    def toggle_chat(event=None):
        if chat_visible["value"]:
            chat_win.withdraw()
        else:
            position_chat_window()
            chat_win.deiconify()
            entry.focus_set()
            if has_unread["value"]:
                has_unread["value"] = False
                set_status(False)
        chat_visible["value"] = not chat_visible["value"]

    def on_press(event):
        drag_state["x"] = event.x
        drag_state["y"] = event.y
        drag_state["moved"] = False

    def on_motion(event):
        # if the mouse has moved more than a couple pixels, treat this as
        # a drag, not a click - this is what distinguishes "pick up and
        # move the character" from "click to open the chat panel"
        dx = abs(event.x - drag_state["x"])
        dy = abs(event.y - drag_state["y"])
        if dx > 3 or dy > 3:
            drag_state["moved"] = True
        x = root.winfo_x() + (event.x - drag_state["x"])
        y = root.winfo_y() + (event.y - drag_state["y"])
        root.geometry(f"+{x}+{y}")

    def on_release(event):
        if not drag_state["moved"]:
            toggle_chat()

    face_canvas.bind("<Button-1>", on_press)
    face_canvas.bind("<B1-Motion>", on_motion)
    face_canvas.bind("<ButtonRelease-1>", on_release)

    # --- idle blink animation ---
    blink_state = {"phase": 0}

    def blink_tick():
        blink_state["phase"] = (blink_state["phase"] + 1) % 40
        if blink_state["phase"] == 0:
            _set_eyes_visible(face_canvas, left_eye, right_eye, False)
            root.after(120, lambda: _set_eyes_visible(face_canvas, left_eye, right_eye, True))
        root.after(150, blink_tick)

    # --- poll for agent replies without blocking the GUI ---
    has_unread = {"value": False}

    def poll_loop():
        reply = controller.poll_reply()
        if reply is not None:
            append_message("ByteFlow", reply)
            controller.speak(controller.speech_friendly(reply))
            if chat_visible["value"]:
                set_status(False)
            else:
                # chat panel is closed - leave a visible cue (green eyes)
                # so you know a reply is waiting next time you look
                has_unread["value"] = True
                _set_eyes_color(face_canvas, left_eye, right_eye, "#a3be8c")
        root.after(200, poll_loop)

    blink_tick()
    poll_loop()

    # small close affordance: right-click to quit
    def quit_app(event=None):
        root.destroy()

    face_canvas.bind("<Button-3>", quit_app)

    root.mainloop()


if __name__ == "__main__":
    run_companion()
