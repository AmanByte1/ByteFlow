from __future__ import annotations

import random
import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont

from .actions import ActionRunner
from .brain import ByteFlowBrain
from .memory import PetMemory


APP_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = APP_DIR / "data"


class DesktopPetApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.memory = PetMemory(DATA_DIR / "pet_state.json")
        self.brain = ByteFlowBrain(DATA_DIR)
        self.actions = ActionRunner()

        self.pet_size = 116
        self.vx = random.choice([-2, -1, 1, 2])
        self.vy = random.choice([-1, 1])
        self.drag = {"x": 0, "y": 0, "moved": False}
        self.panel_visible = False

        self._build_pet_window()
        self._build_panel()
        self._draw_pet()
        self._schedule()

    def _build_pet_window(self) -> None:
        self.root.title("ByteFlowPet")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#12151a")
        try:
            self.root.attributes("-transparentcolor", "#12151a")
        except tk.TclError:
            pass
        self.root.geometry(f"{self.pet_size}x{self.pet_size}+120+120")

        self.canvas = tk.Canvas(
            self.root,
            width=self.pet_size,
            height=self.pet_size,
            bg="#12151a",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", lambda _event: self.root.destroy())

    def _build_panel(self) -> None:
        self.panel = tk.Toplevel(self.root)
        self.panel.withdraw()
        self.panel.overrideredirect(True)
        self.panel.attributes("-topmost", True)
        self.panel.configure(bg="#20242b")

        ui_font = tkfont.Font(family="Segoe UI", size=10)
        bold_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        small_font = tkfont.Font(family="Segoe UI", size=8)

        header = tk.Frame(self.panel, bg="#2c323a")
        header.pack(fill="x")
        self.title_label = tk.Label(
            header,
            text=self._title_text(),
            bg="#2c323a",
            fg="#f2f5f7",
            font=bold_font,
        )
        self.title_label.pack(side="left", padx=10, pady=7)
        tk.Label(
            header,
            text="x",
            bg="#2c323a",
            fg="#b8c0cc",
            cursor="hand2",
            font=bold_font,
        ).pack(side="right", padx=10, pady=7)
        header.winfo_children()[-1].bind("<Button-1>", lambda _event: self.toggle_panel())

        self.stats_label = tk.Label(
            self.panel,
            text="",
            bg="#20242b",
            fg="#b8c0cc",
            anchor="w",
            justify="left",
            font=small_font,
        )
        self.stats_label.pack(fill="x", padx=10, pady=(8, 0))

        self.log = tk.Text(
            self.panel,
            width=48,
            height=13,
            bg="#15191f",
            fg="#f2f5f7",
            insertbackground="#f2f5f7",
            wrap="word",
            state="disabled",
            borderwidth=0,
            font=ui_font,
            padx=9,
            pady=8,
        )
        self.log.pack(fill="both", expand=True, padx=10, pady=8)

        input_row = tk.Frame(self.panel, bg="#20242b")
        input_row.pack(fill="x", padx=10, pady=(0, 8))
        self.entry = tk.Entry(
            input_row,
            bg="#303842",
            fg="#f2f5f7",
            insertbackground="#f2f5f7",
            relief="flat",
            font=ui_font,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        self.entry.bind("<Return>", lambda _event: self.send_message())
        tk.Button(
            input_row,
            text="Send",
            command=self.send_message,
            bg="#2f7d6d",
            fg="white",
            relief="flat",
            font=ui_font,
            padx=12,
        ).pack(side="right")

        teach = tk.Frame(self.panel, bg="#20242b")
        teach.pack(fill="x", padx=10, pady=(0, 10))
        self.action_name = tk.Entry(
            teach,
            bg="#303842",
            fg="#f2f5f7",
            insertbackground="#f2f5f7",
            relief="flat",
            font=small_font,
            width=13,
        )
        self.action_name.insert(0, "action name")
        self.action_name.pack(side="left", ipady=4, padx=(0, 6))
        self.action_command = tk.Entry(
            teach,
            bg="#303842",
            fg="#f2f5f7",
            insertbackground="#f2f5f7",
            relief="flat",
            font=small_font,
        )
        self.action_command.insert(0, "open calculator")
        self.action_command.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 6))
        tk.Button(
            teach,
            text="Teach",
            command=self.teach_action,
            bg="#586b9f",
            fg="white",
            relief="flat",
            font=small_font,
            padx=10,
        ).pack(side="right")

        buttons = tk.Frame(self.panel, bg="#20242b")
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        for label, command in (
            ("Feed", self.feed),
            ("Praise", self.praise),
            ("Correct", self.correct),
            ("Actions", self.show_actions),
        ):
            tk.Button(
                buttons,
                text=label,
                command=command,
                bg="#3b4654",
                fg="#f2f5f7",
                relief="flat",
                font=small_font,
                padx=8,
            ).pack(side="left", padx=(0, 6))

        self.append("System", self.brain.status)
        self.refresh_stats()

    def _draw_pet(self) -> None:
        s = self.pet_size
        st = self.memory.state
        self.canvas.delete("all")

        mood = st.mood_label
        body_color = {
            "happy": "#62b477",
            "curious": "#4aa3a8",
            "quiet": "#7b8ca8",
            "sad": "#8878a8",
        }[mood]
        eye_color = "#f5f7fb" if st.energy > 20 else "#c5ccd8"
        scale = min(1.22, 0.82 + st.level * 0.045)
        pad = (s - s * 0.78 * scale) / 2

        self.canvas.create_oval(
            pad,
            pad + 14,
            s - pad,
            s - pad,
            fill=body_color,
            outline="#17202a",
            width=2,
        )
        self.canvas.create_polygon(
            s * 0.28, s * 0.27, s * 0.38, s * 0.08, s * 0.48, s * 0.29,
            fill=body_color,
            outline="#17202a",
            width=2,
        )
        self.canvas.create_polygon(
            s * 0.52, s * 0.29, s * 0.62, s * 0.08, s * 0.72, s * 0.27,
            fill=body_color,
            outline="#17202a",
            width=2,
        )

        blink = st.age_ticks % 28 == 0
        if blink:
            self.canvas.create_line(s * 0.34, s * 0.48, s * 0.45, s * 0.48, fill="#17202a", width=3)
            self.canvas.create_line(s * 0.55, s * 0.48, s * 0.66, s * 0.48, fill="#17202a", width=3)
        else:
            for x in (0.39, 0.61):
                self.canvas.create_oval(
                    s * x - 9,
                    s * 0.47 - 9,
                    s * x + 9,
                    s * 0.47 + 9,
                    fill=eye_color,
                    outline="#17202a",
                    width=1,
                )
                self.canvas.create_oval(
                    s * x - 3,
                    s * 0.47 - 3,
                    s * x + 3,
                    s * 0.47 + 3,
                    fill="#17202a",
                    outline="",
                )

        mouth_y = s * 0.67
        if mood == "happy":
            self.canvas.create_arc(s * 0.39, mouth_y - 10, s * 0.61, mouth_y + 14, start=200, extent=140, style="arc", width=3)
        elif mood == "sad":
            self.canvas.create_arc(s * 0.39, mouth_y, s * 0.61, mouth_y + 22, start=20, extent=140, style="arc", width=3)
        else:
            self.canvas.create_line(s * 0.42, mouth_y, s * 0.58, mouth_y, fill="#17202a", width=3)

        self.canvas.create_text(
            s / 2,
            s - 11,
            text=f"L{st.level}",
            fill="#f2f5f7",
            font=("Segoe UI", 8, "bold"),
        )

    def _schedule(self) -> None:
        self.root.after(120, self.move_tick)
        self.root.after(1000, self.life_tick)

    def move_tick(self) -> None:
        if not self.drag["moved"]:
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()

            if random.random() < 0.025:
                self.vx = random.choice([-2, -1, 0, 1, 2])
                self.vy = random.choice([-2, -1, 0, 1, 2])

            nx = x + self.vx
            ny = y + self.vy
            if nx < 0 or nx > sw - self.pet_size:
                self.vx *= -1
                nx = max(0, min(sw - self.pet_size, nx))
            if ny < 0 or ny > sh - self.pet_size:
                self.vy *= -1
                ny = max(0, min(sh - self.pet_size, ny))
            self.root.geometry(f"+{nx}+{ny}")
            if self.panel_visible:
                self.position_panel()
        self.root.after(120, self.move_tick)

    def life_tick(self) -> None:
        self.memory.tick()
        self._draw_pet()
        self.refresh_stats()
        self.root.after(1000, self.life_tick)

    def _on_press(self, event) -> None:
        self.drag.update({"x": event.x, "y": event.y, "moved": False})

    def _on_motion(self, event) -> None:
        self.drag["moved"] = True
        x = self.root.winfo_x() + event.x - self.drag["x"]
        y = self.root.winfo_y() + event.y - self.drag["y"]
        self.root.geometry(f"+{x}+{y}")
        if self.panel_visible:
            self.position_panel()

    def _on_release(self, _event) -> None:
        if not self.drag["moved"]:
            self.toggle_panel()
        self.drag["moved"] = False

    def toggle_panel(self) -> None:
        self.panel_visible = not self.panel_visible
        if self.panel_visible:
            self.position_panel()
            self.panel.deiconify()
            self.entry.focus_set()
        else:
            self.panel.withdraw()

    def position_panel(self) -> None:
        x = min(
            self.root.winfo_x() + self.pet_size + 10,
            self.root.winfo_screenwidth() - 390,
        )
        y = min(self.root.winfo_y(), self.root.winfo_screenheight() - 430)
        self.panel.geometry(f"370x420+{max(0, x)}+{max(0, y)}")

    def append(self, sender: str, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"{sender}: {text}\n\n")
        self.log.configure(state="disabled")
        self.log.see("end")

    def _title_text(self) -> str:
        st = self.memory.state
        return f"{st.name} - {st.mood_label}"

    def refresh_stats(self) -> None:
        st = self.memory.state
        self.title_label.configure(text=self._title_text())
        self.stats_label.configure(
            text=(
                f"Level {st.level} | mood {st.mood} | trust {st.trust} | "
                f"energy {st.energy} | actions {len(st.learned_actions)}"
            )
        )

    def pet_context(self) -> str:
        st = self.memory.state
        notes = "; ".join(st.notes[-5:]) if st.notes else "none"
        actions = ", ".join(sorted(st.learned_actions)) or "none"
        return (
            f"name={st.name}, level={st.level}, mood={st.mood_label}({st.mood}), "
            f"trust={st.trust}, energy={st.energy}, learned_actions={actions}, "
            f"recent_notes={notes}"
        )

    def send_message(self) -> None:
        message = self.entry.get().strip()
        if not message:
            return
        self.entry.delete(0, "end")
        self.append("You", message)

        lowered = message.lower()
        if lowered.startswith("remember "):
            self.memory.remember_note(message[9:])
            self.append(self.memory.state.name, "I saved that.")
            return
        if lowered.startswith("do "):
            self.do_action(message[3:].strip())
            return

        self.memory.remember_note(f"User said: {message}")
        self.root.after(10, lambda: self.ask_brain(message))

    def ask_brain(self, message: str) -> None:
        self.append(self.memory.state.name, "Thinking...")
        reply = self.brain.ask(message, self.pet_context())
        self.append("ByteFlow", reply)
        self.memory.state.mood += 2
        self.memory.state.add_xp(4)
        self.memory.save()
        self.refresh_stats()
        self._draw_pet()

    def teach_action(self) -> None:
        result = self.memory.teach_action(
            self.action_name.get(),
            self.action_command.get(),
        )
        self.append("Trainer", result)
        self.refresh_stats()
        self._draw_pet()

    def do_action(self, name: str) -> None:
        key = name.lower().strip()
        command = self.memory.state.learned_actions.get(key)
        if not command:
            self.append(self.memory.state.name, f"I do not know '{key}' yet.")
            return
        result = self.actions.run(command)
        self.append(self.memory.state.name, result)
        self.memory.state.add_xp(6)
        self.memory.save()
        self.refresh_stats()

    def feed(self) -> None:
        self.append("Trainer", self.memory.feed())
        self.refresh_stats()
        self._draw_pet()

    def praise(self) -> None:
        self.append("Trainer", self.memory.praise())
        self.refresh_stats()
        self._draw_pet()

    def correct(self) -> None:
        self.append("Trainer", self.memory.scold())
        self.refresh_stats()
        self._draw_pet()

    def show_actions(self) -> None:
        actions = self.memory.state.learned_actions
        if not actions:
            self.append("Trainer", "No learned actions yet.")
            return
        lines = [f"{name}: {command}" for name, command in sorted(actions.items())]
        self.append("Trainer", "\n".join(lines))


def main() -> int:
    root = tk.Tk()
    DesktopPetApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
