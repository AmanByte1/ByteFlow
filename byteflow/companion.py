"""
ByteFlow Desktop Companion
===========================
A floating holographic orb that lives on your desktop.

Design:
  - Animated glowing orb (idle → pulse, thinking → spin, speaking → wave)
  - Glassmorphism chat panel slides in from the side
  - Tabs: Chat · Alerts · Shortcuts · Status
  - Drag anywhere to reposition
  - Right-click → quit

Run:
    python -m byteflow.companion
    python -m byteflow.companion_core --model llama3  (full power mode)
"""

import queue
import threading
import math
import time


# ══════════════════════════════════════════════════════════════
# CompanionController — the non-visual brain (unchanged)
# ══════════════════════════════════════════════════════════════

class CompanionController:
    """
    Non-visual brain: owns the Agent, queues replies thread-safely.
    Kept separate from Tkinter so it can be tested without a display.
    """

    def __init__(self, agent, speak_replies=False):
        self.agent = agent
        self.replies = queue.Queue()
        self._busy = False
        self._pending_messages = []
        self._lock = threading.Lock()
        self.speaker = None
        if speak_replies:
            from .voice import Speaker, tts_available
            if tts_available():
                self.speaker = Speaker()

    @property
    def busy(self):
        return self._busy

    def speak(self, text):
        if not self.speaker or not text:
            return
        def worker():
            try:
                self.speaker.speak(text)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def send(self, message):
        if not message or not message.strip():
            return
        with self._lock:
            if self._busy:
                self._pending_messages.append(message)
                self.replies.put("[Still thinking — queued your message]")
                return
            self._busy = True
        self._run_worker(message)

    def _run_worker(self, message):
        def worker():
            try:
                result = self.agent.run(message)
                reply = self._format_result(result)
            except Exception as e:
                reply = f"[Error: {e}]"
            self.replies.put(reply)
            next_message = None
            with self._lock:
                if self._pending_messages:
                    next_message = self._pending_messages.pop(0)
                else:
                    self._busy = False
            if next_message is not None:
                self._run_worker(next_message)
        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _format_result(result):
        if isinstance(result, dict) and "code" in result:
            lines = ["Here's the code:", "", result["code"]]
            exec_result = result.get("result")
            if result.get("executed") and exec_result is not None:
                lines += ["", "Output:", exec_result.format()]
            return "\n".join(lines)
        return str(result)

    @staticmethod
    def speech_friendly(reply):
        if reply.startswith("Here's the code:"):
            if "Output:" in reply:
                out = reply.split("Output:", 1)[1].strip()
                out = out.replace("--- stdout ---", "").replace("--- stderr ---", "").strip()
                if out:
                    return f"I wrote the code and ran it. The result was: {out}"
                return "I wrote the code and ran it, but there was no output."
            return "I wrote the code for you — take a look."
        return reply

    def poll_reply(self):
        try:
            return self.replies.get_nowait()
        except queue.Empty:
            return None


# ══════════════════════════════════════════════════════════════
# HOLOGRAPHIC ORB — drawing helpers
# ══════════════════════════════════════════════════════════════

# Color palette
C = {
    "bg":        "#080c14",
    "orb1":      "#4f8cff",
    "orb2":      "#7c4fff",
    "orb3":      "#00e5a0",
    "orb_idle":  "#4f8cff",
    "orb_think": "#ffd94f",
    "orb_speak": "#00e5a0",
    "orb_alert": "#ff4f6a",
    "panel_bg":  "#0d1220",
    "panel_bdr": "#1e2d4a",
    "text":      "#e8e8f0",
    "text2":     "#8899bb",
    "accent":    "#4f8cff",
    "green":     "#00e5a0",
    "red":       "#ff4f6a",
    "yellow":    "#ffd94f",
    "user_msg":  "#1a2a4a",
    "bot_msg":   "#111a2e",
    "tab_act":   "#4f8cff",
    "ring":      "#1a2540",
}

ORB_SIZE = 90       # orb canvas width/height
PANEL_W  = 340
PANEL_H  = 480


def _hex_lerp(c1, c2, t):
    """Interpolate between two hex colors."""
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    r = int(r1 + (r2-r1)*t)
    g = int(g1 + (g2-g1)*t)
    b = int(b1 + (b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _draw_orb(canvas, cx, cy, r, color, glow_color, phase=0.0, state="idle"):
    """
    Draw the holographic orb on a canvas.
    state: idle | thinking | speaking | alert
    phase: 0..1 animation phase
    Returns list of canvas item ids to delete on redraw.
    """
    items = []
    # Outer glow rings (3 layers)
    for i, (alpha, size) in enumerate([(0.08, 2.8), (0.15, 2.2), (0.25, 1.7)]):
        col = _hex_lerp(C["bg"], glow_color, alpha)
        s = r * size
        items.append(canvas.create_oval(
            cx-s, cy-s, cx+s, cy+s,
            fill=col, outline=""
        ))

    # Rotating ring (thinking state spins faster)
    ring_r = r * 1.3
    speed = 4.0 if state == "thinking" else 1.0
    ring_angle = phase * 2 * math.pi * speed
    for i in range(8):
        a = ring_angle + i * math.pi / 4
        x = cx + ring_r * math.cos(a)
        y = cy + ring_r * math.sin(a) * 0.35  # flatten to ellipse
        dot_r = 2.5 if i % 2 == 0 else 1.5
        dot_c = glow_color if i % 2 == 0 else _hex_lerp(C["bg"], glow_color, 0.5)
        items.append(canvas.create_oval(
            x-dot_r, y-dot_r, x+dot_r, y+dot_r,
            fill=dot_c, outline=""
        ))

    # Second counter-rotating ring
    ring2_r = r * 1.15
    for i in range(6):
        a = -ring_angle * 0.7 + i * math.pi / 3
        x = cx + ring2_r * math.cos(a)
        y = cy + ring2_r * math.sin(a) * 0.3
        dot_r = 1.5
        items.append(canvas.create_oval(
            x-dot_r, y-dot_r, x+dot_r, y+dot_r,
            fill=_hex_lerp(C["bg"], glow_color, 0.4), outline=""
        ))

    # Main orb body gradient (4 concentric ovals)
    for t, factor in [(0.0, 1.0), (0.35, 0.82), (0.65, 0.62), (0.85, 0.38)]:
        col = _hex_lerp(C["bg"], glow_color, 0.9 - t * 0.5)
        s = r * factor
        items.append(canvas.create_oval(
            cx-s, cy-s, cx+s, cy+s,
            fill=col, outline=""
        ))

    # Pulse wave (idle breathe / speaking ripple)
    if state in ("idle", "speaking"):
        pulse_r = r * (1.05 + 0.12 * math.sin(phase * 2 * math.pi))
        items.append(canvas.create_oval(
            cx-pulse_r, cy-pulse_r, cx+pulse_r, cy+pulse_r,
            fill="", outline=_hex_lerp(C["bg"], glow_color, 0.3),
            width=1.5
        ))

    # Inner bright core
    core_r = r * 0.32
    items.append(canvas.create_oval(
        cx-core_r, cy-core_r, cx+core_r, cy+core_r,
        fill=_hex_lerp(glow_color, "#ffffff", 0.4), outline=""
    ))

    # Glint / highlight
    gx, gy = cx - r * 0.28, cy - r * 0.30
    gr = r * 0.14
    items.append(canvas.create_oval(
        gx-gr, gy-gr, gx+gr, gy+gr,
        fill="#ffffff", outline=""
    ))
    gx2, gy2 = cx + r * 0.18, cy - r * 0.18
    gr2 = r * 0.07
    items.append(canvas.create_oval(
        gx2-gr2, gy2-gr2, gx2+gr2, gy2+gr2,
        fill=_hex_lerp(glow_color, "#ffffff", 0.6), outline=""
    ))

    # Thinking: spinning arc indicator
    if state == "thinking":
        arc_start = (phase * 360 * 3) % 360
        items.append(canvas.create_arc(
            cx-r*1.08, cy-r*1.08, cx+r*1.08, cy+r*1.08,
            start=arc_start, extent=90,
            outline=glow_color, width=2, style="arc"
        ))

    # Alert: pulsing red ring
    if state == "alert":
        alert_r = r * (1.2 + 0.15 * abs(math.sin(phase * 2 * math.pi * 3)))
        items.append(canvas.create_oval(
            cx-alert_r, cy-alert_r, cx+alert_r, cy+alert_r,
            fill="", outline=C["red"],
            width=2
        ))

    return items


# ══════════════════════════════════════════════════════════════
# MAIN COMPANION WINDOW
# ══════════════════════════════════════════════════════════════

def run_companion(agent=None, model="llama3", enable_desktop_tools=True,
                  voice_input=False, voice_output=False, conversation_mode=False):
    """
    Launch the ByteFlow companion. Blocks until closed.
    Right-click the orb to quit.
    """
    import tkinter as tk
    from tkinter import font as tkfont
    import os

    # ── Build agent if not provided ───────────────────────────────────────────
    if agent is None:
        from .agent import Agent
        from .providers.ollama_provider import OllamaProvider
        from .builtin_tools import register_builtin_tools
        mem = os.path.join(os.path.expanduser("~"), ".byteflow", "memory.json")
        os.makedirs(os.path.dirname(mem), exist_ok=True)
        agent = Agent(provider=OllamaProvider(model=model), memory_path=mem)
        register_builtin_tools(agent)
        if enable_desktop_tools:
            try:
                from .desktop_tools import register_desktop_tools
                register_desktop_tools(agent)
            except Exception:
                pass

    controller = CompanionController(agent, speak_replies=voice_output)

    # ── Animation state ───────────────────────────────────────────────────────
    anim = {
        "phase": 0.0,
        "state": "idle",        # idle | thinking | speaking | alert
        "color": C["orb_idle"],
        "items": [],
        "unread": 0,
        "active_tab": "chat",
    }

    # ── Root window (orb) ─────────────────────────────────────────────────────
    root = tk.Tk()
    root.title("ByteFlow")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", C["bg"])
    root.configure(bg=C["bg"])

    S = ORB_SIZE + 20   # canvas size with padding for glow
    root.geometry(f"{S}x{S}+80+80")

    canvas = tk.Canvas(root, width=S, height=S, bg=C["bg"],
                       highlightthickness=0, bd=0)
    canvas.pack()
    cx, cy = S // 2, S // 2
    orb_r = ORB_SIZE // 2 - 4

    # ── Chat panel (Toplevel) ─────────────────────────────────────────────────
    panel = tk.Toplevel(root)
    panel.withdraw()
    panel.overrideredirect(True)
    panel.attributes("-topmost", True)
    panel.configure(bg=C["panel_bg"])
    panel.geometry(f"{PANEL_W}x{PANEL_H}")

    # Fonts
    F_BODY  = tkfont.Font(family="Segoe UI", size=10)
    F_BOLD  = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    F_SMALL = tkfont.Font(family="Segoe UI", size=9)
    F_MONO  = tkfont.Font(family="Consolas",  size=9)
    F_TITLE = tkfont.Font(family="Segoe UI",  size=12, weight="bold")
    F_TAB   = tkfont.Font(family="Segoe UI",  size=9,  weight="bold")

    # ── Panel header ──────────────────────────────────────────────────────────
    header = tk.Frame(panel, bg="#0a0f1e", height=46)
    header.pack(fill="x")
    header.pack_propagate(False)

    # Orb mini icon in header
    h_canvas = tk.Canvas(header, width=28, height=28, bg="#0a0f1e",
                          highlightthickness=0)
    h_canvas.place(x=12, y=9)
    h_canvas.create_oval(4, 4, 24, 24, fill=C["orb_idle"], outline="")
    h_canvas.create_oval(8, 8, 18, 18, fill="#7cb9ff", outline="")
    h_canvas.create_oval(10, 9, 15, 14, fill="#ffffff", outline="")

    tk.Label(header, text="ByteFlow", font=F_TITLE,
             bg="#0a0f1e", fg=C["text"]).place(x=46, y=12)

    status_lbl = tk.Label(header, text="● ready", font=F_SMALL,
                           bg="#0a0f1e", fg=C["green"])
    status_lbl.place(x=200, y=15)

    close_btn = tk.Label(header, text="✕", font=F_BOLD,
                          bg="#0a0f1e", fg=C["text2"], cursor="hand2")
    close_btn.place(x=PANEL_W - 28, y=13)
    close_btn.bind("<Button-1>", lambda e: toggle_panel())

    # Separator
    tk.Frame(panel, bg=C["panel_bdr"], height=1).pack(fill="x")

    # ── Tab bar ───────────────────────────────────────────────────────────────
    tab_bar = tk.Frame(panel, bg="#0a0f1e", height=36)
    tab_bar.pack(fill="x")
    tab_bar.pack_propagate(False)

    tab_labels = {}
    TABS = [("💬 Chat", "chat"), ("🔔 Alerts", "alerts"),
            ("⚡ Quick", "quick"), ("📊 Status", "status")]

    def switch_tab(name):
        anim["active_tab"] = name
        for tname, lbl in tab_labels.items():
            if tname == name:
                lbl.configure(bg=C["panel_bg"], fg=C["accent"])
            else:
                lbl.configure(bg="#0a0f1e", fg=C["text2"])
        # Show/hide frames
        chat_frame.pack_forget()
        alerts_frame.pack_forget()
        quick_frame.pack_forget()
        status_frame.pack_forget()
        frames = {"chat": chat_frame, "alerts": alerts_frame,
                  "quick": quick_frame, "status": status_frame}
        frames[name].pack(fill="both", expand=True)
        if name == "alerts":
            refresh_alerts()
        if name == "status":
            refresh_status()

    for i, (label, name) in enumerate(TABS):
        lbl = tk.Label(tab_bar, text=label, font=F_TAB,
                        bg="#0a0f1e", fg=C["text2"],
                        cursor="hand2", padx=8)
        lbl.place(x=i * (PANEL_W // 4), y=0,
                  width=PANEL_W // 4, height=36)
        lbl.bind("<Button-1>", lambda e, n=name: switch_tab(n))
        tab_labels[name] = lbl

    tk.Frame(panel, bg=C["panel_bdr"], height=1).pack(fill="x")

    # ── CHAT frame ────────────────────────────────────────────────────────────
    chat_frame = tk.Frame(panel, bg=C["panel_bg"])

    # Message display
    msg_frame = tk.Frame(chat_frame, bg=C["panel_bg"])
    msg_frame.pack(fill="both", expand=True, padx=0, pady=0)

    msg_scroll = tk.Scrollbar(msg_frame, bg=C["panel_bg"],
                               troughcolor=C["panel_bg"],
                               activebackground=C["panel_bdr"])
    msg_scroll.pack(side="right", fill="y")

    msg_text = tk.Text(
        msg_frame, bg=C["panel_bg"], fg=C["text"],
        font=F_BODY, wrap="word", state="disabled",
        padx=12, pady=10, borderwidth=0, highlightthickness=0,
        yscrollcommand=msg_scroll.set, selectbackground=C["ring"],
        insertbackground=C["accent"],
    )
    msg_text.pack(side="left", fill="both", expand=True)
    msg_scroll.config(command=msg_text.yview)

    # Message tags
    msg_text.tag_configure("you_name",  foreground=C["accent"],  font=F_BOLD)
    msg_text.tag_configure("bot_name",  foreground=C["green"],   font=F_BOLD)
    msg_text.tag_configure("sys_name",  foreground=C["yellow"],  font=F_BOLD)
    msg_text.tag_configure("err_name",  foreground=C["red"],     font=F_BOLD)
    msg_text.tag_configure("you_text",  foreground=C["text"])
    msg_text.tag_configure("bot_text",  foreground=C["text"])
    msg_text.tag_configure("sys_text",  foreground=C["text2"],   font=F_SMALL)
    msg_text.tag_configure("err_text",  foreground=C["red"])
    msg_text.tag_configure("code_text", foreground="#a9d3df",    font=F_MONO,
                            background="#0a1020")
    msg_text.tag_configure("divider",   foreground=C["ring"])

    def append_msg(sender, text, kind="bot"):
        msg_text.configure(state="normal")
        name_tag = {"you":"you_name","bot":"bot_name",
                    "sys":"sys_name","err":"err_name"}.get(kind,"bot_name")
        text_tag = {"you":"you_text","bot":"bot_text",
                    "sys":"sys_text","err":"err_text"}.get(kind,"bot_text")

        # Format code blocks
        if "```" in text:
            parts = text.split("```")
            msg_text.insert("end", f"{sender}\n", name_tag)
            for i, part in enumerate(parts):
                if i % 2 == 1:  # inside code block
                    msg_text.insert("end", part.lstrip("python\n").lstrip("bash\n"), "code_text")
                else:
                    if part.strip():
                        msg_text.insert("end", part, text_tag)
        else:
            msg_text.insert("end", f"{sender}\n", name_tag)
            msg_text.insert("end", f"{text}\n", text_tag)

        msg_text.insert("end", "\n")
        msg_text.configure(state="disabled")
        msg_text.see("end")

    # Input area
    input_sep = tk.Frame(chat_frame, bg=C["panel_bdr"], height=1)
    input_sep.pack(fill="x")

    input_area = tk.Frame(chat_frame, bg="#080c18", pady=8, padx=10)
    input_area.pack(fill="x", side="bottom")

    entry_var = tk.StringVar()
    entry = tk.Entry(
        input_area, textvariable=entry_var,
        bg="#111827", fg=C["text"], insertbackground=C["accent"],
        font=F_BODY, relief="flat", bd=0,
        highlightthickness=1, highlightcolor=C["accent"],
        highlightbackground=C["panel_bdr"],
    )
    entry.pack(fill="x", ipady=7, padx=(0,0), pady=(0,6))

    btn_row = tk.Frame(input_area, bg="#080c18")
    btn_row.pack(fill="x")

    def _mk_btn(parent, text, cmd, accent=False):
        bg = C["accent"] if accent else C["ring"]
        fg = "#fff" if accent else C["text2"]
        b = tk.Label(parent, text=text, font=F_SMALL, bg=bg, fg=fg,
                      cursor="hand2", padx=10, pady=5, relief="flat")
        b.bind("<Button-1>", lambda e: cmd())
        return b

    def on_send(event=None):
        msg = entry_var.get().strip()
        if not msg:
            return
        entry_var.set("")
        append_msg("You", msg, "you")
        set_state("thinking")
        controller.send(msg)

    def on_upload():
        from tkinter import filedialog
        from .file_reading import read_file_text, FileReadError
        path = filedialog.askopenfilename(parent=panel)
        if not path:
            return
        fname = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        try:
            content = read_file_text(path)
        except Exception as e:
            append_msg("System", f"Could not read {fname}: {e}", "sys")
            return
        n_chunks = agent.ingest_document(content, source=fname)
        append_msg("System", f"Indexed {fname} ({n_chunks} chunks)", "sys")
        set_state("thinking")
        controller.send(
            f"I uploaded `{fname}` — {len(content)} chars, {n_chunks} chunks indexed. "
            f"Preview:\n```\n{content[:300]}\n```"
        )

    send_btn   = _mk_btn(btn_row, "  Send ➤  ", on_send, accent=True)
    upload_btn = _mk_btn(btn_row, "📎 File",    on_upload)
    clear_btn  = _mk_btn(btn_row, "🗑 Clear",
                          lambda: [msg_text.configure(state="normal"),
                                   msg_text.delete("1.0","end"),
                                   msg_text.configure(state="disabled")])

    send_btn.pack(side="right", padx=(4,0))
    upload_btn.pack(side="right", padx=(4,0))
    clear_btn.pack(side="right", padx=(4,0))
    entry.bind("<Return>", on_send)

    # ── ALERTS frame ──────────────────────────────────────────────────────────
    alerts_frame = tk.Frame(panel, bg=C["panel_bg"])

    alerts_header = tk.Frame(alerts_frame, bg=C["panel_bg"])
    alerts_header.pack(fill="x", padx=12, pady=(10,6))
    tk.Label(alerts_header, text="System Alerts", font=F_BOLD,
             bg=C["panel_bg"], fg=C["text"]).pack(side="left")
    refresh_btn = tk.Label(alerts_header, text="↻ Refresh", font=F_SMALL,
                            bg=C["panel_bg"], fg=C["accent"], cursor="hand2")
    refresh_btn.pack(side="right")

    alerts_text = tk.Text(
        alerts_frame, bg=C["panel_bg"], fg=C["text"],
        font=F_SMALL, wrap="word", state="disabled",
        padx=12, pady=6, borderwidth=0, highlightthickness=0,
    )
    alerts_text.pack(fill="both", expand=True)
    alerts_text.tag_configure("warn",  foreground=C["yellow"], font=F_BOLD)
    alerts_text.tag_configure("err",   foreground=C["red"],    font=F_BOLD)
    alerts_text.tag_configure("info",  foreground=C["accent"], font=F_BOLD)
    alerts_text.tag_configure("body",  foreground=C["text2"])
    alerts_text.tag_configure("time",  foreground=C["ring"])

    def refresh_alerts():
        try:
            from byteflow.watcher import get_watcher
            w = get_watcher()
            alerts = w.get_alerts(limit=20)
            alerts_text.configure(state="normal")
            alerts_text.delete("1.0","end")
            if not alerts:
                alerts_text.insert("end", "✅  All systems good — no alerts\n", "info")
            else:
                for a in alerts:
                    tag = {"warning":"warn","error":"err"}.get(a["level"],"info")
                    alerts_text.insert("end", f"[{a['level'].upper()}] {a['title']}\n", tag)
                    alerts_text.insert("end", f"{a['body']}\n", "body")
                    alerts_text.insert("end", f"{a['ts'][:19]}\n\n", "time")
            alerts_text.configure(state="disabled")
        except Exception as e:
            alerts_text.configure(state="normal")
            alerts_text.delete("1.0","end")
            alerts_text.insert("end", f"Could not load alerts: {e}", "body")
            alerts_text.configure(state="disabled")

    refresh_btn.bind("<Button-1>", lambda e: refresh_alerts())

    # ── QUICK ACTIONS frame ───────────────────────────────────────────────────
    quick_frame = tk.Frame(panel, bg=C["panel_bg"])

    tk.Label(quick_frame, text="Quick Actions", font=F_BOLD,
             bg=C["panel_bg"], fg=C["text"]).pack(anchor="w", padx=14, pady=(12,8))

    QUICK_ACTIONS = [
        ("💻 System Info",    "show system info"),
        ("🌿 Git Status",     "show git status of current directory"),
        ("⚙️ Processes",      "list running processes"),
        ("💾 Disk Usage",     "check disk space"),
        ("📋 Clipboard",      "read clipboard"),
        ("⏰ Current Time",   "what time is it"),
        ("📚 KB Status",      "kb_status"),
        ("🔔 Check Alerts",   "check_alerts"),
        ("📊 List Workflows", "list_workflows"),
        ("⚡ List Shortcuts", "list_shortcuts"),
        ("🔗 Integrations",   "integration_status"),
        ("🕐 History Stats",  "history_stats"),
    ]

    def run_quick(cmd):
        switch_tab("chat")
        append_msg("You", cmd, "you")
        set_state("thinking")
        controller.send(cmd)

    qa_scroll = tk.Frame(quick_frame, bg=C["panel_bg"])
    qa_scroll.pack(fill="both", expand=True, padx=10, pady=(0,10))

    for i, (label, cmd) in enumerate(QUICK_ACTIONS):
        row = i // 2
        col = i % 2
        btn = tk.Label(
            qa_scroll, text=label, font=F_SMALL,
            bg=C["ring"], fg=C["text"],
            cursor="hand2", padx=8, pady=8,
            anchor="w", relief="flat",
        )
        btn.grid(row=row, column=col, padx=4, pady=3,
                 sticky="ew", ipadx=4)
        btn.bind("<Enter>",  lambda e, b=btn: b.configure(bg=C["panel_bdr"], fg=C["accent"]))
        btn.bind("<Leave>",  lambda e, b=btn: b.configure(bg=C["ring"], fg=C["text"]))
        btn.bind("<Button-1>", lambda e, c=cmd: run_quick(c))
        qa_scroll.columnconfigure(col, weight=1)

    # Shortcut runner
    tk.Frame(quick_frame, bg=C["panel_bdr"], height=1).pack(fill="x", padx=10, pady=6)
    sc_row = tk.Frame(quick_frame, bg=C["panel_bg"])
    sc_row.pack(fill="x", padx=10, pady=(0,10))
    sc_entry = tk.Entry(sc_row, bg="#111827", fg=C["text"],
                         insertbackground=C["accent"], font=F_BODY,
                         relief="flat", highlightthickness=1,
                         highlightbackground=C["panel_bdr"],
                         highlightcolor=C["accent"])
    sc_entry.pack(side="left", fill="x", expand=True, ipady=5)
    sc_entry.insert(0, "ask anything...")
    sc_entry.bind("<FocusIn>", lambda e: sc_entry.delete(0,"end") if sc_entry.get()=="ask anything..." else None)
    sc_send = tk.Label(sc_row, text=" Ask ➤ ", font=F_SMALL,
                        bg=C["accent"], fg="#fff", cursor="hand2", padx=8, pady=5)
    sc_send.pack(side="right", padx=(6,0))
    def sc_run(e=None):
        q = sc_entry.get().strip()
        if q and q != "ask anything...":
            sc_entry.delete(0,"end")
            run_quick(q)
    sc_send.bind("<Button-1>", sc_run)
    sc_entry.bind("<Return>", sc_run)

    # ── STATUS frame ──────────────────────────────────────────────────────────
    status_frame = tk.Frame(panel, bg=C["panel_bg"])

    status_text = tk.Text(
        status_frame, bg=C["panel_bg"], fg=C["text"],
        font=F_SMALL, wrap="word", state="disabled",
        padx=14, pady=12, borderwidth=0, highlightthickness=0,
    )
    status_text.pack(fill="both", expand=True)
    status_text.tag_configure("head",  foreground=C["accent"], font=F_BOLD)
    status_text.tag_configure("key",   foreground=C["green"])
    status_text.tag_configure("val",   foreground=C["text"])
    status_text.tag_configure("sep",   foreground=C["ring"])

    def refresh_status():
        status_text.configure(state="normal")
        status_text.delete("1.0","end")

        def sec(title):
            status_text.insert("end", f"\n{title}\n", "head")
            status_text.insert("end", "─" * 36 + "\n", "sep")

        def kv(k, v):
            status_text.insert("end", f"  {k:<18}", "key")
            status_text.insert("end", f"{v}\n", "val")

        import platform, sys, os, shutil
        sec("⚙️  System")
        kv("OS",      f"{platform.system()} {platform.release()}")
        kv("Python",  sys.version.split()[0])
        kv("Host",    platform.node())

        try:
            du = shutil.disk_usage("/")
            kv("Disk",  f"{du.used/1e9:.1f} / {du.total/1e9:.1f} GB ({du.used/du.total*100:.0f}%)")
        except Exception:
            pass

        try:
            import psutil
            mem = psutil.virtual_memory()
            kv("Memory", f"{mem.used/1e9:.1f} / {mem.total/1e9:.1f} GB ({mem.percent:.0f}%)")
            kv("CPU",    f"{psutil.cpu_percent(interval=0.5):.0f}%")
        except ImportError:
            kv("Memory", "install psutil for details")

        sec("🤖  ByteFlow")
        try:
            from byteflow.knowledge_base import get_kb
            kb = get_kb()
            s = kb.stats()
            kv("KB sources",   s["total_sources"])
            kv("KB chunks",    s["total_chunks"])
        except Exception:
            pass

        try:
            from byteflow.chat_history import get_history
            h = get_history()
            s = h.stats()
            kv("Sessions",     s["total_sessions"])
            kv("Messages",     s["total_messages"])
        except Exception:
            pass

        try:
            from byteflow.workflows import get_workflow_engine
            eng = get_workflow_engine()
            s = eng.stats()
            kv("Workflows",    f"{s['enabled']} active / {s['total']} total")
        except Exception:
            pass

        try:
            from byteflow.watcher import get_watcher
            w = get_watcher()
            kv("Alerts",       f"{w.unread_count()} unread")
        except Exception:
            pass

        try:
            from byteflow.integrations import get_integrations
            ig = get_integrations()
            st = ig.status()
            active = [k for k,v in st.items() if v.get("configured")]
            kv("Integrations", ", ".join(active) if active else "none configured")
        except Exception:
            pass

        try:
            from byteflow_automator import Automator
            auto = Automator()
            kv("Auto tasks",   len(auto.registry))
        except Exception:
            pass

        status_text.configure(state="disabled")

    # Show chat by default
    chat_frame.pack(fill="both", expand=True)
    switch_tab("chat")

    # ── Orb animation ─────────────────────────────────────────────────────────
    def set_state(state):
        anim["state"] = state
        anim["color"] = {
            "idle":     C["orb_idle"],
            "thinking": C["orb_think"],
            "speaking": C["orb_speak"],
            "alert":    C["orb_alert"],
        }.get(state, C["orb_idle"])
        status_lbl.configure(
            text={"idle":"● ready","thinking":"● thinking…",
                  "speaking":"● speaking","alert":"● alert!"}.get(state,"● ready"),
            fg=anim["color"]
        )

    def redraw_orb():
        # Remove old items
        for item in anim["items"]:
            try:
                canvas.delete(item)
            except Exception:
                pass
        anim["items"] = _draw_orb(
            canvas, cx, cy, orb_r,
            anim["color"], anim["color"],
            anim["phase"], anim["state"]
        )

    def animate():
        speed = {"idle": 0.008, "thinking": 0.025,
                 "speaking": 0.018, "alert": 0.030}.get(anim["state"], 0.008)
        anim["phase"] = (anim["phase"] + speed) % 1.0
        redraw_orb()
        root.after(40, animate)  # ~25 fps

    animate()

    # ── Panel visibility ──────────────────────────────────────────────────────
    panel_visible = {"v": False}

    def position_panel():
        rx = root.winfo_x()
        ry = root.winfo_y()
        sw = root.winfo_screenwidth()
        # Open to the right, or left if near screen edge
        if rx + S + PANEL_W + 10 < sw:
            px = rx + S + 6
        else:
            px = rx - PANEL_W - 6
        py = max(0, ry - (PANEL_H - S) // 2)
        panel.geometry(f"{PANEL_W}x{PANEL_H}+{px}+{py}")

    def toggle_panel(event=None):
        if panel_visible["v"]:
            panel.withdraw()
            panel_visible["v"] = False
        else:
            position_panel()
            panel.deiconify()
            panel_visible["v"] = True
            anim["unread"] = 0
            entry.focus_set()

    # ── Drag ─────────────────────────────────────────────────────────────────
    drag = {"x": 0, "y": 0, "moved": False}

    def on_press(e):
        drag["x"] = e.x
        drag["y"] = e.y
        drag["moved"] = False

    def on_drag(e):
        dx = abs(e.x - drag["x"])
        dy = abs(e.y - drag["y"])
        if dx > 3 or dy > 3:
            drag["moved"] = True
        nx = root.winfo_x() + (e.x - drag["x"])
        ny = root.winfo_y() + (e.y - drag["y"])
        root.geometry(f"+{nx}+{ny}")
        if panel_visible["v"]:
            position_panel()

    def on_release(e):
        if not drag["moved"]:
            toggle_panel()

    canvas.bind("<Button-1>",       on_press)
    canvas.bind("<B1-Motion>",      on_drag)
    canvas.bind("<ButtonRelease-1>",on_release)
    canvas.bind("<Button-3>",       lambda e: root.destroy())

    # Tooltip on hover
    tip_lbl = tk.Label(root, text="ByteFlow — click to open",
                        font=F_SMALL, bg="#0d1220", fg=C["text2"],
                        padx=6, pady=3, relief="flat")

    def show_tip(e):
        tip_lbl.place(x=S + 4, y=cy - 10)
        root.after(2000, lambda: tip_lbl.place_forget())

    canvas.bind("<Enter>", show_tip)

    # ── Poll agent replies ─────────────────────────────────────────────────────
    def poll():
        reply = controller.poll_reply()
        if reply is not None:
            append_msg("ByteFlow", reply, "bot")
            controller.speak(controller.speech_friendly(reply))
            if panel_visible["v"]:
                set_state("idle")
            else:
                anim["unread"] += 1
                set_state("alert")
        root.after(200, poll)

    poll()

    # Welcome message
    append_msg("ByteFlow",
               "Hello! I'm your ByteFlow companion.\n"
               "I can help with files, code, automation, alerts, and more.\n"
               "Use the Quick tab for one-tap actions, or just ask me anything.",
               "bot")

    root.mainloop()


if __name__ == "__main__":
    run_companion()
