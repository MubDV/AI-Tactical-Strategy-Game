"""What the UI currently shows on top of the game state: hover, selection, animations, floating text."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .demo_rules import Options
from .stub import Pos, Unit


@dataclass
class Slide:
    """A unit gliding along a path of cells (about 0.25 s in total)."""
    path: List[Pos]                       # starts at the origin cell
    t0: float
    duration: float = 0.25

    def position(self, now: float) -> Tuple[float, float]:
        k = min(1.0, max(0.0, (now - self.t0) / self.duration))
        segs = len(self.path) - 1
        if segs <= 0:
            return float(self.path[0][0]), float(self.path[0][1])
        f = k * segs
        i = min(int(f), segs - 1)
        u = f - i
        a, b = self.path[i], self.path[i + 1]
        u = u * u * (3 - 2 * u) if segs == 1 else u          # ease a single step
        return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u

    def done(self, now: float) -> bool:
        return now - self.t0 >= self.duration


@dataclass
class FloatText:
    text: str
    color: tuple
    pos: Tuple[float, float]              # logical screen position
    t0: float
    life: float = 1.0


@dataclass
class Ghost:
    """A unit that was just killed: fades out in place."""
    unit: Unit
    t0: float
    life: float = 0.45


@dataclass
class Flash:
    unit_id: str
    t0: float
    life: float = 0.12


@dataclass
class View:
    hover: Optional[Pos] = None
    selected: Optional[str] = None
    options: Optional[Options] = None
    slides: Dict[str, Slide] = field(default_factory=dict)
    texts: List[FloatText] = field(default_factory=list)
    ghosts: List[Ghost] = field(default_factory=list)
    flashes: List[Flash] = field(default_factory=list)
    message: str = ""
    message_kind: str = "info"           # info | warn | error
    message_t0: float = 0.0
    shake_until: float = 0.0
    shake_mag: int = 0

    def say(self, text: str, now: float, kind: str = "info"):
        self.message, self.message_kind, self.message_t0 = text, kind, now

    def prune(self, now: float):
        self.slides = {k: v for k, v in self.slides.items() if not v.done(now)}
        self.texts = [t for t in self.texts if now - t.t0 < t.life]
        self.ghosts = [g for g in self.ghosts if now - g.t0 < g.life]
        self.flashes = [f for f in self.flashes if now - f.t0 < f.life]
