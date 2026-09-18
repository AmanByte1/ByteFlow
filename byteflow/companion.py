"""
ByteFlow Companion v3
=====================
Floating holographic orb with full power:
  - All 56 automation tasks
  - Voice model switching (say "switch to q1")
  - Settings panel with model picker
  - Self-understanding (knows its own capabilities)
  - Voice input + TTS output
  - Quick actions, alerts, shortcuts
  - Real-time status

Run:
    python byteflow/companion.py
    python byteflow/companion.py --model q1
"""

import queue, threading, math, time, os, sys, json
from pathlib import Path


# ══════════════════════════════════════════════════════════
# CONTROLLER
# ══════════════════════════════════════════════════════════
class CompanionController:
    def __init__(self, agent, speak_replies=False):
        self.agent = agent
        self.replies = queue.Queue()
        self._busy = False
        self._pending = []
        self._lock = threading.Lock()
        self.speaker = None
        self._last_reply = ""
        if speak_replies:
            try:
                from .voice import Speaker, tts_available
                if tts_available():
                    self.speaker = Speaker()
            except Exception:
                pass

    @property
    def busy(self):
        return self._busy

    def speak(self, text):
        if not self.speaker or not text:
            return
        threading.Thread(target=lambda: self.speaker.speak(text), daemon=True).start()

    def send(self, message):
        if not message.strip():
            return
        with self._lock:
            if self._busy:
                self._pending.append(message)
                self.replies.put("[Queued — still thinking...]")
                return
            self._busy = True
        self._run(message)

    def _run(self, message):
        def worker():
            try:
                result = self.agent.run(message)
                reply = self._fmt(result)
            except Exception as e:
                reply = f"[Error: {e}]"
            self._last_reply = reply
            self.replies.put(reply)
            nxt = None
            with self._lock:
                if self._pending:
                    nxt = self._pending.pop(0)
                else:
                    self._busy = False
            if nxt:
                self._run(nxt)
        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _fmt(result):
        if isinstance(result, dict) and "code" in result:
            lines = ["Here's the code:", "", result["code"]]
            r = result.get("result")
            if result.get("executed") and r is not None:
                lines += ["", "Output:", r.format()]
            return "\n".join(lines)
        return str(result)

    @staticmethod
    def speech_friendly(reply):
        if reply.startswith("Here's the code:"):
            if "Output:" in reply:
                out = reply.split("Output:", 1)[1].strip()
                out = out.replace("--- stdout ---","").replace("--- stderr ---","").strip()
                if out:
                    return f"Done. The output was: {out}"
                return "Code written and executed — no output."
            return "I wrote the code for you."
        return reply[:300]

    def poll_reply(self):
        try:
            return self.replies.get_nowait()
        except queue.Empty:
            return None


# ══════════════════════════════════════════════════════════
# COLORS & CONSTANTS
# ══════════════════════════════════════════════════════════
C = {
    "void":    "#03040a",
    "deep":    "#070b14",
    "ink":     "#0c1220",
    "surface": "#111b2e",
    "lift":    "#172338",
    "rim":     "#1f3048",
    "border":  "#243650",
    "cyan":    "#00d4c8",
    "cyan2":   "#007d76",
    "amber":   "#f0a030",
    "rose":    "#e05870",
    "violet":  "#9060f0",
    "green":   "#40d080",
    "t1":      "#ddeeff",
    "t2":      "#7aa0c0",
    "t3":      "#3a5878",
    "t4":      "#1e3050",
    # orb states
    "idle":    "#00d4c8",
    "think":   "#f0a030",
    "speak":   "#40d080",
    "alert":   "#e05870",
    "listen":  "#9060f0",
}

PANEL_W, PANEL_H = 400, 560
ORB_S = 100   # canvas size


def lerp_color(c1, c2, t):
    r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
    r=int(r1+(r2-r1)*t); g=int(g1+(g2-g1)*t); b=int(b1+(b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"


def draw_orb(canvas, cx, cy, r, color, phase, state):
    items = []
    # Outer glow
    for a,s in [(0.06,3.0),(0.12,2.3),(0.22,1.8)]:
        col = lerp_color(C["void"], color, a)
        items.append(canvas.create_oval(cx-r*s,cy-r*s,cx+r*s,cy+r*s,fill=col,outline=""))
    # Orbit ring 1
    speed = 4 if state=="think" else 1.5 if state=="listen" else 1.0
    ang = phase * 2 * math.pi * speed
    for i in range(8):
        a = ang + i*math.pi/4
        ox = cx + r*1.35*math.cos(a)
        oy = cy + r*1.35*math.sin(a)*0.35
        dr = 3 if i%2==0 else 1.5
        col = color if i%2==0 else lerp_color(C["void"],color,0.4)
        items.append(canvas.create_oval(ox-dr,oy-dr,ox+dr,oy+dr,fill=col,outline=""))
    # Orbit ring 2 (counter)
    for i in range(6):
        a = -ang*0.6 + i*math.pi/3
        ox = cx + r*1.15*math.cos(a)
        oy = cy + r*1.15*math.sin(a)*0.28
        items.append(canvas.create_oval(ox-1.5,oy-1.5,ox+1.5,oy+1.5,
                                        fill=lerp_color(C["void"],color,0.35),outline=""))
    # Body gradient
    for t,f in [(0.0,1.0),(0.35,0.82),(0.65,0.62),(0.85,0.4)]:
        col = lerp_color(C["void"], color, 0.9-t*0.5)
        items.append(canvas.create_oval(cx-r*f,cy-r*f,cx+r*f,cy+r*f,fill=col,outline=""))
    # Pulse
    if state in ("idle","speak"):
        pr = r*(1.05+0.1*math.sin(phase*2*math.pi))
        items.append(canvas.create_oval(cx-pr,cy-pr,cx+pr,cy+pr,
                     fill="",outline=lerp_color(C["void"],color,0.25),width=1.5))
    # Thinking arc
    if state=="think":
        s = (phase*360*3)%360
        items.append(canvas.create_arc(cx-r*1.1,cy-r*1.1,cx+r*1.1,cy+r*1.1,
                     start=s,extent=100,outline=color,width=2,style="arc"))
    # Listening bars
    if state=="listen":
        for i,h in enumerate([0.5,0.9,0.7,1.0,0.6]):
            bh = r*0.5*h*(0.8+0.4*math.sin(phase*2*math.pi+i*0.8))
            bx = cx-r*0.4+i*r*0.2
            items.append(canvas.create_rectangle(bx-2,cy-bh,bx+2,cy+bh,fill=color,outline=""))
    # Alert ring
    if state=="alert":
        ar = r*(1.2+0.15*abs(math.sin(phase*2*math.pi*3)))
        items.append(canvas.create_oval(cx-ar,cy-ar,cx+ar,cy+ar,
                     fill="",outline=C["rose"],width=2))
    # Core
    items.append(canvas.create_oval(cx-r*0.3,cy-r*0.3,cx+r*0.3,cy+r*0.3,
                 fill=lerp_color(color,"#ffffff",0.45),outline=""))
    # Glint
    gx,gy,gr = cx-r*0.26,cy-r*0.28,r*0.13
    items.append(canvas.create_oval(gx-gr,gy-gr,gx+gr,gy+gr,fill="#ffffff",outline=""))
    gx2,gy2,gr2 = cx+r*0.16,cy-r*0.16,r*0.07
    items.append(canvas.create_oval(gx2-gr2,gy2-gr2,gx2+gr2,gy2+gr2,
                 fill=lerp_color(color,"#ffffff",0.6),outline=""))
    return items


# ══════════════════════════════════════════════════════════
# MAIN COMPANION
# ══════════════════════════════════════════════════════════
def run_companion(agent=None, model="llama3", voice_output=False,
                  voice_input=False, enable_desktop_tools=True):

    import tkinter as tk
    from tkinter import font as tkfont

    # ── Build agent ──────────────────────────────────────────
    if agent is None:
        from byteflow.agent import Agent
        from byteflow.providers.ollama_provider import OllamaProvider
        from byteflow.builtin_tools import register_builtin_tools
        from byteflow.model_registry import resolve_model
        mem = Path.home() / ".byteflow" / "memory.json"
        mem.parent.mkdir(exist_ok=True)
        real_model = resolve_model(model)
        provider = OllamaProvider(model=real_model)
        agent = Agent(provider=provider, memory_path=str(mem))
        register_builtin_tools(agent)
        if enable_desktop_tools:
            try:
                from byteflow.desktop_tools import register_desktop_tools
                register_desktop_tools(agent)
            except Exception:
                pass

    # Wire automator
    try:
        from byteflow_automator import Automator
        from byteflow.tools import Tool
        _auto = Automator()
        for task in _auto.registry.all():
            if task.safe:
                agent.register_tool(Tool(task.name, task.func, task.description))
        _auto_ref = _auto
    except ImportError:
        _auto_ref = None

    controller = CompanionController(agent, speak_replies=voice_output)

    # ── State ────────────────────────────────────────────────
    st = {
        "phase": 0.0, "state": "idle", "color": C["idle"],
        "items": [], "panel_open": False, "unread": 0,
        "active_tab": "chat", "model": getattr(agent.provider,"model",model),
    }

    # ── Root (orb) ───────────────────────────────────────────
    root = tk.Tk()
    root.title("ByteFlow")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", C["void"])
    root.configure(bg=C["void"])
    root.geometry(f"{ORB_S+20}x{ORB_S+20}+80+80")

    canv = tk.Canvas(root, width=ORB_S+20, height=ORB_S+20,
                     bg=C["void"], highlightthickness=0)
    canv.pack()
    cx, cy = (ORB_S+20)//2, (ORB_S+20)//2
    orb_r  = ORB_S//2 - 4

    # ── Fonts ────────────────────────────────────────────────
    F_UI   = tkfont.Font(family="Segoe UI",   size=10)
    F_BOLD = tkfont.Font(family="Segoe UI",   size=10, weight="bold")
    F_SML  = tkfont.Font(family="Segoe UI",   size=9)
    F_CODE = tkfont.Font(family="Consolas",   size=9)
    F_TTL  = tkfont.Font(family="Segoe UI",   size=12, weight="bold")
    F_TAB  = tkfont.Font(family="Segoe UI",   size=9,  weight="bold")
    F_MONO = tkfont.Font(family="JetBrains Mono", size=9)

    # ── Panel ────────────────────────────────────────────────
    panel = tk.Toplevel(root)
    panel.withdraw()
    panel.overrideredirect(True)
    panel.attributes("-topmost", True)
    panel.configure(bg=C["deep"])
    panel.geometry(f"{PANEL_W}x{PANEL_H}")

    # ── Panel header ─────────────────────────────────────────
    hdr = tk.Frame(panel, bg="#04080f", height=50)
    hdr.pack(fill="x"); hdr.pack_propagate(False)

    hc = tk.Canvas(hdr, width=30, height=30, bg="#04080f", highlightthickness=0)
    hc.place(x=12, y=10)
    hc.create_oval(3,3,27,27,fill=C["cyan"],outline="")
    hc.create_oval(8,8,20,20,fill="#60d8d0",outline="")
    hc.create_oval(11,10,17,15,fill="#ffffff",outline="")

    tk.Label(hdr, text="ByteFlow", font=F_TTL,
             bg="#04080f", fg=C["t1"]).place(x=48, y=14)

    status_lbl = tk.Label(hdr, text="● ready", font=F_SML,
                          bg="#04080f", fg=C["green"])
    status_lbl.place(x=160, y=17)

    model_badge = tk.Label(hdr, text=f"⚡ {st['model']}", font=F_SML,
                           bg=C["ink"], fg=C["amber"],
                           cursor="hand2", padx=6, pady=2)
    model_badge.place(x=PANEL_W-120, y=14)

    close_lbl = tk.Label(hdr, text="✕", font=F_BOLD,
                         bg="#04080f", fg=C["t3"], cursor="hand2")
    close_lbl.place(x=PANEL_W-22, y=16)
    close_lbl.bind("<Button-1>", lambda e: toggle_panel())

    tk.Frame(panel, bg=C["border"], height=1).pack(fill="x")

    # ── Tab bar ──────────────────────────────────────────────
    tab_bar = tk.Frame(panel, bg=C["ink"], height=36)
    tab_bar.pack(fill="x"); tab_bar.pack_propagate(False)
    TABS = [("💬","chat"),("⚡","quick"),("🔔","alerts"),
            ("⚙️","settings"),("📊","status")]
    tab_lbls = {}

    def switch_tab(name):
        st["active_tab"] = name
        for n, l in tab_lbls.items():
            l.configure(bg=C["surface"] if n==name else C["ink"],
                        fg=C["cyan"]    if n==name else C["t3"])
        for f in [chat_f, quick_f, alerts_f, settings_f, status_f]:
            f.pack_forget()
        {"chat":chat_f,"quick":quick_f,"alerts":alerts_f,
         "settings":settings_f,"status":status_f}[name].pack(fill="both",expand=True,side="top")
        if name=="alerts": refresh_alerts()
        if name=="status": refresh_status()
        if name=="settings": refresh_settings()

    for i,(icon,name) in enumerate(TABS):
        l = tk.Label(tab_bar, text=icon, font=F_TAB,
                     bg=C["ink"], fg=C["t3"], cursor="hand2",
                     width=PANEL_W//(len(TABS)*8))
        l.place(x=i*(PANEL_W//len(TABS)), y=0,
                width=PANEL_W//len(TABS), height=36)
        l.bind("<Button-1>", lambda e,n=name: switch_tab(n))
        tab_lbls[name] = l
    tk.Frame(panel, bg=C["border"], height=1).pack(fill="x")

    def set_state(s):
        st["state"] = s
        st["color"] = {"idle":C["idle"],"think":C["think"],
                       "speak":C["speak"],"alert":C["alert"],
                       "listen":C["listen"]}.get(s, C["idle"])
        status_lbl.configure(
            text={"idle":"● ready","think":"● thinking…","speak":"● speaking",
                  "alert":"● alert!","listen":"● listening"}.get(s,"● ready"),
            fg=st["color"])

    # ════════════════════════════════════════════════════════
    # CHAT FRAME
    # ════════════════════════════════════════════════════════
    chat_f = tk.Frame(panel, bg=C["deep"])

    # INPUT — pack bottom first
    in_sep = tk.Frame(chat_f, bg=C["border"], height=1)
    in_sep.pack(side="bottom", fill="x")
    in_area = tk.Frame(chat_f, bg=C["ink"], pady=8, padx=10)
    in_area.pack(side="bottom", fill="x")

    # MSG area fills rest
    msg_wrap = tk.Frame(chat_f, bg=C["deep"])
    msg_wrap.pack(side="top", fill="both", expand=True)

    msg_sb = tk.Scrollbar(msg_wrap, bg=C["deep"], troughcolor=C["deep"])
    msg_sb.pack(side="right", fill="y")

    msg_txt = tk.Text(msg_wrap, bg=C["deep"], fg=C["t1"], font=F_UI,
                      wrap="word", state="disabled", padx=12, pady=10,
                      borderwidth=0, highlightthickness=0,
                      yscrollcommand=msg_sb.set,
                      selectbackground=C["rim"],
                      insertbackground=C["cyan"])
    msg_txt.pack(side="left", fill="both", expand=True)
    msg_sb.config(command=msg_txt.yview)

    msg_txt.tag_configure("you",   foreground=C["cyan"],  font=F_BOLD)
    msg_txt.tag_configure("bf",    foreground=C["green"], font=F_BOLD)
    msg_txt.tag_configure("sys",   foreground=C["amber"], font=F_BOLD)
    msg_txt.tag_configure("err",   foreground=C["rose"],  font=F_BOLD)
    msg_txt.tag_configure("ytxt",  foreground=C["t1"])
    msg_txt.tag_configure("btxt",  foreground=C["t1"])
    msg_txt.tag_configure("stxt",  foreground=C["t2"], font=F_SML)
    msg_txt.tag_configure("etxt",  foreground=C["rose"])
    msg_txt.tag_configure("code",  foreground="#a9d3df", font=F_CODE,
                           background="#08101e")

    def append_msg(sender, text, kind="bf"):
        msg_txt.configure(state="normal")
        name_tag = {"you":"you","bf":"bf","sys":"sys","err":"err"}.get(kind,"bf")
        text_tag = {"you":"ytxt","bf":"btxt","sys":"stxt","err":"etxt"}.get(kind,"btxt")
        if "```" in text:
            parts = text.split("```")
            msg_txt.insert("end", f"{sender}\n", name_tag)
            for i,p in enumerate(parts):
                if i%2==1:
                    msg_txt.insert("end", p.lstrip("python\nbash\n"), "code")
                elif p.strip():
                    msg_txt.insert("end", p, text_tag)
        else:
            msg_txt.insert("end", f"{sender}\n", name_tag)
            msg_txt.insert("end", f"{text}\n", text_tag)
        msg_txt.insert("end", "\n")
        msg_txt.configure(state="disabled")
        msg_txt.see("end")

    # Input widgets
    ev = tk.StringVar()
    entry = tk.Entry(in_area, textvariable=ev,
                     bg=C["surface"], fg=C["t1"],
                     insertbackground=C["cyan"], font=F_UI,
                     relief="flat", highlightthickness=1,
                     highlightcolor=C["cyan"],
                     highlightbackground=C["border"])
    entry.pack(fill="x", ipady=7, pady=(0,6))

    btn_row = tk.Frame(in_area, bg=C["ink"])
    btn_row.pack(fill="x")

    def btn(parent, text, cmd, accent=False):
        b = tk.Label(parent, text=text, font=F_SML, cursor="hand2",
                     bg=C["cyan"] if accent else C["rim"],
                     fg=C["void"] if accent else C["t2"],
                     padx=10, pady=5)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e,b=b: b.configure(bg=C["cyan"] if accent else C["border"]))
        b.bind("<Leave>", lambda e,b=b: b.configure(bg=C["cyan"] if accent else C["rim"]))
        return b

    def on_send(e=None):
        msg = ev.get().strip()
        if not msg: return
        ev.set("")
        # Check voice model switch command first
        if handle_model_switch(msg):
            return
        append_msg("You", msg, "you")
        set_state("think")
        controller.send(msg)

    def on_upload():
        from tkinter import filedialog
        path = filedialog.askopenfilename(parent=panel)
        if not path: return
        fname = Path(path).name
        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            append_msg("System", f"Could not read {fname}: {e}", "sys"); return
        try:
            n = agent.ingest_document(content, source=fname)
            append_msg("System", f"Indexed {fname} ({n} chunks)", "sys")
        except Exception:
            append_msg("System", f"Loaded {fname}", "sys")
        set_state("think")
        controller.send(f"I uploaded `{fname}`. Preview:\n```\n{content[:300]}\n```")

    sb  = btn(btn_row, "  Send ➤  ", on_send, accent=True)
    ub  = btn(btn_row, "📎 File",    on_upload)
    clr = btn(btn_row, "🗑 Clear",
              lambda: [msg_txt.configure(state="normal"),
                       msg_txt.delete("1.0","end"),
                       msg_txt.configure(state="disabled")])
    mic_btn = btn(btn_row, "🎙 Voice",  lambda: toggle_mic())

    sb.pack(side="right", padx=(4,0))
    ub.pack(side="right", padx=(4,0))
    clr.pack(side="right", padx=(4,0))
    mic_btn.pack(side="right", padx=(4,0))
    entry.bind("<Return>", on_send)

    # ════════════════════════════════════════════════════════
    # QUICK ACTIONS FRAME
    # ════════════════════════════════════════════════════════
    quick_f = tk.Frame(panel, bg=C["deep"])
    tk.Label(quick_f, text="Quick Actions", font=F_BOLD,
             bg=C["deep"], fg=C["t1"]).pack(anchor="w", padx=14, pady=(12,6))

    QUICK = [
        ("💻 System Info",    "show system info"),
        ("🌿 Git Status",     "git status of current directory"),
        ("⚙️  Processes",     "list running processes"),
        ("💾 Disk Usage",     "check disk space"),
        ("📋 Clipboard",      "read clipboard"),
        ("🕐 Time",           "what time is it"),
        ("📚 KB Status",      "kb_status"),
        ("🔔 Alerts",         "check_alerts"),
        ("⚡ Shortcuts",      "list_shortcuts"),
        ("🔗 Integrations",   "integration_status"),
        ("📊 Workflows",      "list_workflows"),
        ("🧠 My Memories",    "history_stats"),
        ("🤖 My Skills",      "What tools and skills do you have?"),
        ("🔄 Switch q1",      "switch to q1"),
        ("🔄 Switch llama3",  "switch to llama3"),
        ("🔄 Switch my-buddy","switch to my-buddy"),
    ]

    def run_quick(cmd):
        switch_tab("chat")
        if handle_model_switch(cmd):
            return
        append_msg("You", cmd, "you")
        set_state("think")
        controller.send(cmd)

    qa_grid = tk.Frame(quick_f, bg=C["deep"])
    qa_grid.pack(fill="both", expand=True, padx=10, pady=(0,10))
    for i,(label,cmd) in enumerate(QUICK):
        row, col = i//2, i%2
        b = tk.Label(qa_grid, text=label, font=F_SML, bg=C["ink"],
                     fg=C["t2"], cursor="hand2", anchor="w",
                     padx=10, pady=7, relief="flat")
        b.grid(row=row, column=col, padx=4, pady=3, sticky="ew")
        b.bind("<Enter>",  lambda e,x=b: x.configure(bg=C["surface"], fg=C["cyan"]))
        b.bind("<Leave>",  lambda e,x=b: x.configure(bg=C["ink"], fg=C["t2"]))
        b.bind("<Button-1>", lambda e,c=cmd: run_quick(c))
        qa_grid.columnconfigure(col, weight=1)

    # Free-ask bar
    tk.Frame(quick_f, bg=C["border"], height=1).pack(fill="x", padx=10, pady=6)
    ask_row = tk.Frame(quick_f, bg=C["deep"])
    ask_row.pack(fill="x", padx=10, pady=(0,10))
    ask_ev = tk.StringVar()
    ask_e  = tk.Entry(ask_row, textvariable=ask_ev, bg=C["surface"], fg=C["t1"],
                      insertbackground=C["cyan"], font=F_UI, relief="flat",
                      highlightthickness=1, highlightbackground=C["border"],
                      highlightcolor=C["cyan"])
    ask_e.pack(side="left", fill="x", expand=True, ipady=5)
    ask_e.insert(0, "ask anything or type a model alias...")
    ask_e.bind("<FocusIn>", lambda e: ask_e.delete(0,"end")
               if ask_e.get().startswith("ask") else None)
    ask_sb = tk.Label(ask_row, text=" Ask ➤ ", font=F_SML, bg=C["cyan"],
                      fg=C["void"], cursor="hand2", padx=8, pady=5)
    ask_sb.pack(side="right", padx=(6,0))
    def ask_run(e=None):
        q = ask_ev.get().strip()
        if q and not q.startswith("ask"): ask_ev.set(""); run_quick(q)
    ask_sb.bind("<Button-1>", ask_run)
    ask_e.bind("<Return>", ask_run)

    # ════════════════════════════════════════════════════════
    # ALERTS FRAME
    # ════════════════════════════════════════════════════════
    alerts_f = tk.Frame(panel, bg=C["deep"])
    ah = tk.Frame(alerts_f, bg=C["deep"])
    ah.pack(fill="x", padx=12, pady=(10,6))
    tk.Label(ah, text="System Alerts", font=F_BOLD,
             bg=C["deep"], fg=C["t1"]).pack(side="left")
    rb = tk.Label(ah, text="↻ Refresh", font=F_SML,
                  bg=C["deep"], fg=C["cyan"], cursor="hand2")
    rb.pack(side="right")

    at = tk.Text(alerts_f, bg=C["deep"], fg=C["t1"], font=F_SML,
                 wrap="word", state="disabled", padx=12, pady=6,
                 borderwidth=0, highlightthickness=0)
    at.pack(fill="both", expand=True)
    at.tag_configure("warn", foreground=C["amber"], font=F_BOLD)
    at.tag_configure("err",  foreground=C["rose"],  font=F_BOLD)
    at.tag_configure("info", foreground=C["cyan"],  font=F_BOLD)
    at.tag_configure("body", foreground=C["t2"])
    at.tag_configure("time", foreground=C["t4"])

    def refresh_alerts():
        try:
            from byteflow.watcher import get_watcher
            alerts = get_watcher().get_alerts(limit=20)
            at.configure(state="normal"); at.delete("1.0","end")
            if not alerts:
                at.insert("end","✅  All systems look good\n","info")
            else:
                for a in alerts:
                    tag = {"warning":"warn","error":"err"}.get(a["level"],"info")
                    at.insert("end",f"[{a['level'].upper()}] {a['title']}\n",tag)
                    at.insert("end",f"{a['body']}\n","body")
                    at.insert("end",f"{a['ts'][:19]}\n\n","time")
            at.configure(state="disabled")
        except Exception as e:
            at.configure(state="normal"); at.delete("1.0","end")
            at.insert("end",f"Watcher unavailable: {e}","body")
            at.configure(state="disabled")

    rb.bind("<Button-1>", lambda e: refresh_alerts())

    # ════════════════════════════════════════════════════════
    # SETTINGS FRAME
    # ════════════════════════════════════════════════════════
    settings_f = tk.Frame(panel, bg=C["deep"])

    sf_scroll = tk.Frame(settings_f, bg=C["deep"])
    sf_scroll.pack(fill="both", expand=True, padx=14, pady=10)

    def srow(parent, label, widget_fn):
        row = tk.Frame(parent, bg=C["ink"], pady=1)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, font=F_SML, bg=C["ink"],
                 fg=C["t2"], width=18, anchor="w").pack(side="left", padx=10, pady=8)
        w = widget_fn(row)
        if w: w.pack(side="right", padx=10, pady=6)
        return row

    # Section: Model
    tk.Label(sf_scroll, text="🤖  AI MODEL", font=F_TAB,
             bg=C["deep"], fg=C["cyan"]).pack(anchor="w", pady=(6,4))
    model_sect = tk.Frame(sf_scroll, bg=C["ink"], bd=0,
                          highlightthickness=1, highlightbackground=C["border"])
    model_sect.pack(fill="x", pady=(0,10))

    # Current model display
    cur_model_lbl = tk.Label(model_sect, text=f"Current: {st['model']}",
                             font=F_BOLD, bg=C["ink"], fg=C["amber"])
    cur_model_lbl.pack(anchor="w", padx=12, pady=(10,4))

    # Available models from Ollama
    models_var = tk.StringVar(value=st["model"])
    models_list_lbl = tk.Label(model_sect, text="Switch to:", font=F_SML,
                                bg=C["ink"], fg=C["t3"])
    models_list_lbl.pack(anchor="w", padx=12)

    models_frame = tk.Frame(model_sect, bg=C["ink"])
    models_frame.pack(fill="x", padx=12, pady=(4,10))

    known_aliases = [
        ("⚡ q1",       "q1",       "qwen2.5-coder:1.5b — fast code model"),
        ("🦙 l3",       "llama3",   "Llama 3 — general purpose"),
        ("🤝 mb",       "my-buddy", "My Buddy — your custom model"),
        ("💨 m",        "mistral",  "Mistral — fast & efficient"),
        ("💻 cl",       "codellama","CodeLlama — code specialist"),
    ]

    def do_switch_model(alias, name):
        switch_model_to(alias)
        append_msg("System", f"Switched to {name} (alias: {alias})", "sys")
        switch_tab("chat")

    for i,(label,alias,desc) in enumerate(known_aliases):
        row = tk.Frame(models_frame, bg=C["surface"])
        row.pack(fill="x", pady=2)
        is_cur = alias == st["model"] or st["model"].startswith(alias.split(":")[0])
        color = C["cyan"] if is_cur else C["t2"]
        tk.Label(row, text=label, font=F_BOLD, bg=C["surface"],
                 fg=color, width=8).pack(side="left", padx=8, pady=4)
        tk.Label(row, text=desc, font=F_SML, bg=C["surface"],
                 fg=C["t3"]).pack(side="left", padx=4)
        sw = tk.Label(row, text="→ Use", font=F_SML, bg=C["rim"],
                      fg=C["t2"], cursor="hand2", padx=8, pady=3)
        sw.pack(side="right", padx=8)
        sw.bind("<Button-1>", lambda e,a=alias,n=desc: do_switch_model(a,n))
        sw.bind("<Enter>", lambda e,w=sw: w.configure(bg=C["cyan"],fg=C["void"]))
        sw.bind("<Leave>", lambda e,w=sw: w.configure(bg=C["rim"],fg=C["t2"]))

    # Custom model entry
    tk.Label(model_sect, text="Custom model name / alias:",
             font=F_SML, bg=C["ink"], fg=C["t3"]).pack(anchor="w", padx=12)
    custom_row = tk.Frame(model_sect, bg=C["ink"])
    custom_row.pack(fill="x", padx=12, pady=(4,10))
    custom_ev = tk.StringVar()
    custom_e = tk.Entry(custom_row, textvariable=custom_ev,
                        bg=C["surface"], fg=C["t1"],
                        insertbackground=C["cyan"], font=F_CODE,
                        relief="flat", highlightthickness=1,
                        highlightbackground=C["border"],
                        highlightcolor=C["cyan"])
    custom_e.pack(side="left", fill="x", expand=True, ipady=5)
    custom_e.insert(0, "e.g. q1  or  qwen2.5-coder:1.5b")
    custom_e.bind("<FocusIn>", lambda e: custom_e.delete(0,"end")
                  if custom_e.get().startswith("e.g") else None)
    def apply_custom(e=None):
        v = custom_ev.get().strip()
        if v and not v.startswith("e.g"): switch_model_to(v)
    cok = tk.Label(custom_row, text=" Apply ", font=F_SML,
                   bg=C["amber"], fg=C["void"], cursor="hand2", padx=8, pady=5)
    cok.pack(side="right", padx=(6,0))
    cok.bind("<Button-1>", apply_custom)
    custom_e.bind("<Return>", apply_custom)

    # Voice note
    tk.Label(model_sect,
             text="💡 Voice command: say  \"switch to q1\"  or  \"use buddy\"",
             font=F_SML, bg=C["ink"], fg=C["t4"],
             wraplength=350, justify="left").pack(anchor="w", padx=12, pady=(0,10))

    # Section: Voice
    tk.Label(sf_scroll, text="🎙️  VOICE", font=F_TAB,
             bg=C["deep"], fg=C["cyan"]).pack(anchor="w", pady=(6,4))
    voice_sect = tk.Frame(sf_scroll, bg=C["ink"], bd=0,
                           highlightthickness=1, highlightbackground=C["border"])
    voice_sect.pack(fill="x", pady=(0,10))

    voice_enabled_var = tk.BooleanVar(value=True)
    def make_toggle(parent, var):
        f = tk.Frame(parent, bg=C["ink"])
        def toggle():
            var.set(not var.get())
            on.configure(bg=C["cyan"] if var.get() else C["rim"],
                         fg=C["void"] if var.get() else C["t3"])
        on = tk.Label(f, text=" ON ", font=F_SML, cursor="hand2",
                      bg=C["cyan"] if var.get() else C["rim"],
                      fg=C["void"] if var.get() else C["t3"],
                      padx=6, pady=3)
        on.pack()
        on.bind("<Button-1>", lambda e: toggle())
        return f

    srow(voice_sect, "Voice output (TTS)", lambda p: make_toggle(p, voice_enabled_var))
    srow(voice_sect, "Wake word", lambda p: tk.Label(p,text="\"hey byteflow\"",
         font=F_CODE, bg=C["ink"], fg=C["t2"]))

    def refresh_settings():
        cur_model_lbl.configure(text=f"Current: {st['model']}")

    # ════════════════════════════════════════════════════════
    # STATUS FRAME
    # ════════════════════════════════════════════════════════
    status_f = tk.Frame(panel, bg=C["deep"])
    st_txt = tk.Text(status_f, bg=C["deep"], fg=C["t1"], font=F_SML,
                     wrap="word", state="disabled", padx=14, pady=12,
                     borderwidth=0, highlightthickness=0)
    st_txt.pack(fill="both", expand=True)
    st_txt.tag_configure("head", foreground=C["cyan"],  font=F_BOLD)
    st_txt.tag_configure("key",  foreground=C["green"])
    st_txt.tag_configure("val",  foreground=C["t1"])
    st_txt.tag_configure("sep",  foreground=C["t4"])

    def refresh_status():
        st_txt.configure(state="normal"); st_txt.delete("1.0","end")
        def sec(t):
            st_txt.insert("end", f"\n{t}\n", "head")
            st_txt.insert("end", "─"*38+"\n", "sep")
        def kv(k,v):
            st_txt.insert("end", f"  {k:<20}", "key")
            st_txt.insert("end", f"{v}\n", "val")

        import platform, sys, shutil
        sec("⚙️  System")
        kv("OS", f"{platform.system()} {platform.release()}")
        kv("Python", sys.version.split()[0])
        try:
            du = shutil.disk_usage("/")
            kv("Disk", f"{du.used/1e9:.1f}/{du.total/1e9:.1f}GB ({du.used/du.total*100:.0f}%)")
        except Exception: pass
        try:
            import psutil
            mem = psutil.virtual_memory()
            kv("Memory", f"{mem.used/1e9:.1f}/{mem.total/1e9:.1f}GB ({mem.percent:.0f}%)")
            kv("CPU", f"{psutil.cpu_percent(interval=0.3):.0f}%")
        except ImportError:
            kv("Memory", "pip install psutil for details")

        sec("🤖  ByteFlow")
        kv("Model", st["model"])
        try:
            from byteflow.model_registry import get_model_info
            info = get_model_info(st["model"])
            kv("Model label", info.get("label","?"))
            kv("Best for", ", ".join(info.get("best_for",[])))
        except Exception: pass
        try:
            from byteflow_automator import Automator
            auto = Automator()
            kv("Auto tasks", len(auto.registry))
            cats = list(set(t.category for t in auto.registry.all()))
            kv("Categories", ", ".join(cats))
        except Exception: pass
        try:
            from byteflow.knowledge_base import get_kb
            kb = get_kb(); s = kb.stats()
            kv("KB sources", s["total_sources"])
            kv("KB chunks", s["total_chunks"])
        except Exception: pass
        try:
            from byteflow.chat_history import get_history
            h = get_history(); s = h.stats()
            kv("Sessions", s["total_sessions"])
            kv("Messages", s["total_messages"])
        except Exception: pass
        try:
            from byteflow.watcher import get_watcher
            kv("Alerts", f"{get_watcher().unread_count()} unread")
        except Exception: pass

        sec("🔑  Model Aliases")
        from byteflow.model_registry import ALIASES
        for alias, full in list(ALIASES.items())[:12]:
            kv(f"  {alias}", full)

        st_txt.configure(state="disabled")

    # ── Init first tab ───────────────────────────────────────
    chat_f.pack(fill="both", expand=True, side="top")
    switch_tab("chat")

    # ════════════════════════════════════════════════════════
    # MODEL SWITCHING — core function
    # ════════════════════════════════════════════════════════
    def switch_model_to(alias_or_name: str) -> bool:
        from byteflow.model_registry import resolve_model, get_model_info
        full = resolve_model(alias_or_name)
        try:
            agent.provider.switch_model(full)
            st["model"] = full
            info = get_model_info(full)
            label = info.get("label", full)
            model_badge.configure(text=f"⚡ {full}")
            cur_model_lbl.configure(text=f"Current: {full}")
            append_msg("System",
                f"✅ Model switched to {label} ({full})\n"
                f"Alias: {info.get('alias','?')} | Best for: {', '.join(info.get('best_for',[]))}",
                "sys")
            controller.speak(f"Switched to {label}")
            return True
        except Exception as e:
            append_msg("System", f"⚠️ Could not switch model: {e}", "err")
            return False

    def handle_model_switch(text: str) -> bool:
        """
        Detect voice/text model switch commands.
        Returns True if a switch was handled.
        Examples:
          "switch to q1"  "use buddy"  "switch model llama3"
          "q1"  "l3"  "mb"  (just the alias alone)
        """
        from byteflow.model_registry import ALIASES, resolve_model
        low = text.strip().lower().replace("-","").replace(" ","")

        # Pattern: "switchtoX", "useX", "switchmodelX", "changetoX"
        for prefix in ["switchto","useto","use","switchmodel","changeto","change","model"]:
            if low.startswith(prefix):
                candidate = low[len(prefix):].strip()
                full = resolve_model(candidate)
                if full != candidate or candidate in ALIASES.values():
                    switch_model_to(candidate)
                    return True

        # Pattern: bare alias (e.g. "q1", "mb", "l3")
        bare = low.strip()
        if bare in ALIASES:
            switch_model_to(bare)
            return True

        return False

    # ════════════════════════════════════════════════════════
    # VOICE MIC
    # ════════════════════════════════════════════════════════
    _mic_active = [False]
    _mic_rec    = [None]

    def toggle_mic():
        try:
            import speech_recognition as sr
        except ImportError:
            append_msg("System",
                "Install SpeechRecognition: pip install SpeechRecognition pyaudio", "err")
            return

        if _mic_active[0]:
            _mic_active[0] = False
            mic_btn.configure(bg=C["rim"], fg=C["t2"], text="🎙 Voice")
            set_state("idle")
            return

        _mic_active[0] = True
        mic_btn.configure(bg=C["rose"], fg=C["void"], text="🔴 Stop")
        set_state("listen")

        def listen_thread():
            recog = sr.Recognizer()
            try:
                with sr.Microphone() as src:
                    recog.adjust_for_ambient_noise(src, duration=0.5)
                    audio = recog.listen(src, timeout=8, phrase_time_limit=12)
                text = recog.recognize_google(audio)
                root.after(0, lambda: _on_voice_result(text))
            except sr.WaitTimeoutError:
                root.after(0, lambda: _on_voice_done("No speech detected"))
            except sr.UnknownValueError:
                root.after(0, lambda: _on_voice_done("Could not understand"))
            except Exception as e:
                root.after(0, lambda: _on_voice_done(f"Mic error: {e}"))

        threading.Thread(target=listen_thread, daemon=True).start()

    def _on_voice_result(text):
        _mic_active[0] = False
        mic_btn.configure(bg=C["rim"], fg=C["t2"], text="🎙 Voice")
        set_state("idle")
        # Show what was heard
        append_msg("🎙 You", text, "you")
        # Check for model switch first
        if handle_model_switch(text):
            return
        set_state("think")
        controller.send(text)

    def _on_voice_done(msg):
        _mic_active[0] = False
        mic_btn.configure(bg=C["rim"], fg=C["t2"], text="🎙 Voice")
        set_state("idle")
        append_msg("System", msg, "sys")

    # ════════════════════════════════════════════════════════
    # ORB ANIMATION
    # ════════════════════════════════════════════════════════
    def redraw():
        for it in st["items"]:
            try: canv.delete(it)
            except Exception: pass
        st["items"] = draw_orb(canv, cx, cy, orb_r,
                               st["color"], st["phase"], st["state"])

    def animate():
        spd = {"idle":0.008,"think":0.028,"speak":0.018,
               "alert":0.035,"listen":0.022}.get(st["state"],0.008)
        st["phase"] = (st["phase"] + spd) % 1.0
        redraw()
        root.after(40, animate)

    animate()

    # ════════════════════════════════════════════════════════
    # PANEL SHOW / HIDE
    # ════════════════════════════════════════════════════════
    def pos_panel():
        rx, ry = root.winfo_x(), root.winfo_y()
        sw = root.winfo_screenwidth()
        px = rx + ORB_S+26 if rx+ORB_S+PANEL_W+30 < sw else rx-PANEL_W-6
        py = max(0, ry-(PANEL_H-ORB_S)//2)
        panel.geometry(f"{PANEL_W}x{PANEL_H}+{px}+{py}")

    def toggle_panel(e=None):
        if st["panel_open"]:
            panel.withdraw(); st["panel_open"] = False
        else:
            pos_panel(); panel.deiconify()
            st["panel_open"] = True; st["unread"] = 0
            entry.focus_set()

    # ════════════════════════════════════════════════════════
    # DRAG
    # ════════════════════════════════════════════════════════
    drag = {"x":0,"y":0,"moved":False}
    def on_press(e): drag["x"]=e.x; drag["y"]=e.y; drag["moved"]=False
    def on_drag(e):
        if abs(e.x-drag["x"])>3 or abs(e.y-drag["y"])>3: drag["moved"]=True
        root.geometry(f"+{root.winfo_x()+(e.x-drag['x'])}+{root.winfo_y()+(e.y-drag['y'])}")
        if st["panel_open"]: pos_panel()
    def on_release(e):
        if not drag["moved"]: toggle_panel()

    canv.bind("<Button-1>",        on_press)
    canv.bind("<B1-Motion>",       on_drag)
    canv.bind("<ButtonRelease-1>", on_release)
    canv.bind("<Button-3>",        lambda e: root.destroy())

    # Tooltip
    tip = tk.Label(root, text="ByteFlow — click to open",
                   font=F_SML, bg=C["ink"], fg=C["t3"], padx=6, pady=3)
    def show_tip(e):
        tip.place(x=ORB_S+26, y=cy-10)
        root.after(2000, tip.place_forget)
    canv.bind("<Enter>", show_tip)

    # ════════════════════════════════════════════════════════
    # POLL REPLIES
    # ════════════════════════════════════════════════════════
    def poll():
        reply = controller.poll_reply()
        if reply:
            append_msg("ByteFlow", reply, "bf")
            controller.speak(controller.speech_friendly(reply))
            if st["panel_open"]: set_state("idle")
            else:
                st["unread"] += 1
                set_state("alert")
        root.after(200, poll)

    poll()

    # Welcome
    append_msg("ByteFlow",
        f"Hello! Running on {st['model']}.\n"
        f"I have access to all automation tools, memory, KB, and more.\n"
        f"Say or type a model alias to switch: q1=qwen-coder, l3=llama3, mb=my-buddy\n"
        f"Voice: click 🎙 Voice or say 'hey byteflow' to activate.",
        "bf")

    root.mainloop()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="ByteFlow Companion v3")
    p.add_argument("--model", default="llama3",
                   help="Model name or alias (q1, l3, mb, mistral...)")
    p.add_argument("--voice-output", action="store_true")
    p.add_argument("--voice-input",  action="store_true")
    p.add_argument("--no-tools",     action="store_true")
    a = p.parse_args()
    run_companion(model=a.model,
                  voice_output=a.voice_output,
                  voice_input=a.voice_input,
                  enable_desktop_tools=not a.no_tools)
