from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class PetState:
    name: str = "Byte"
    age_ticks: int = 0
    mood: int = 55
    trust: int = 35
    energy: int = 75
    level: int = 1
    xp: int = 0
    notes: List[str] = field(default_factory=list)
    learned_actions: Dict[str, str] = field(default_factory=dict)

    @property
    def mood_label(self) -> str:
        if self.mood >= 75:
            return "happy"
        if self.mood >= 45:
            return "curious"
        if self.mood >= 25:
            return "quiet"
        return "sad"

    def clamp(self) -> None:
        self.mood = max(0, min(100, self.mood))
        self.trust = max(0, min(100, self.trust))
        self.energy = max(0, min(100, self.energy))
        self.level = max(1, self.level)

    def add_xp(self, amount: int) -> None:
        self.xp += max(0, amount)
        while self.xp >= self.level * 40:
            self.xp -= self.level * 40
            self.level += 1
            self.mood += 8
            self.energy += 5
        self.clamp()


class PetMemory:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self.load()

    def load(self) -> PetState:
        if not self.path.exists():
            return PetState()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            state = PetState(**raw)
            state.clamp()
            return state
        except Exception:
            return PetState()

    def save(self) -> None:
        self.state.clamp()
        self.path.write_text(
            json.dumps(asdict(self.state), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def tick(self) -> None:
        self.state.age_ticks += 1
        if self.state.age_ticks % 12 == 0:
            self.state.energy -= 1
        if self.state.age_ticks % 30 == 0:
            self.state.mood -= 1
        self.state.clamp()
        self.save()

    def praise(self) -> str:
        self.state.mood += 9
        self.state.trust += 7
        self.state.energy += 3
        self.state.add_xp(8)
        self.save()
        return f"{self.state.name} feels trusted."

    def scold(self) -> str:
        self.state.mood -= 12
        self.state.trust -= 8
        self.state.energy -= 4
        self.save()
        return f"{self.state.name} becomes careful."

    def feed(self) -> str:
        self.state.energy += 18
        self.state.mood += 5
        self.state.add_xp(5)
        self.save()
        return f"{self.state.name} has more energy."

    def remember_note(self, note: str) -> None:
        note = note.strip()
        if not note:
            return
        self.state.notes.append(note)
        self.state.notes = self.state.notes[-30:]
        self.state.add_xp(3)
        self.save()

    def teach_action(self, name: str, command: str) -> str:
        key = name.strip().lower()
        value = command.strip()
        if not key or not value:
            return "Give the action a name and a command."
        self.state.learned_actions[key] = value
        self.state.trust += 4
        self.state.add_xp(10)
        self.save()
        return f"Learned action '{key}'."
