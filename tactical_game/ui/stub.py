"""Temporary game model for the UI (milestones M1-M3).

The names mirror the real domain layer in the Team Supporting Document (Side, UnitType, Terrain,
Direction, Unit, GameState). At milestone M4 replace the import in the UI modules by
`from tactical_game.domain import ...`; nothing in the renderer needs to change.
The state is immutable: every change builds a new GameState with `dataclasses.replace`.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, IntEnum
from typing import Optional, Tuple

Pos = Tuple[int, int]            # (row, col), each 0-7, row 0 at the top


class Side(Enum):
    HUMAN = "human"
    AI = "ai"


class UnitType(Enum):
    TANK = "T"
    SNIPER = "S"
    SCOUT = "C"
    BOMBER = "B"
    MINER = "M"


class Terrain(Enum):
    OPEN = "open"
    WALL = "wall"
    COVER = "cover"


class Direction(IntEnum):        # N, E, S, W in the order used everywhere
    N = 0
    E = 1
    S = 2
    W = 3


DELTA = {Direction.N: (-1, 0), Direction.E: (0, 1), Direction.S: (1, 0), Direction.W: (0, -1)}

BOARD_N = 8
WALLS = frozenset({(2, 2), (2, 5), (5, 2), (5, 5)})
COVER = frozenset({(1, 3), (1, 4), (6, 3), (6, 4), (3, 3), (4, 4)})
BASES = {Side.HUMAN: (4, 1), Side.AI: (3, 6)}
SPAWNS = {Side.HUMAN: [(3, 1), (5, 0), (4, 0)], Side.AI: [(4, 6), (2, 7), (3, 7)]}
MAX_HP = {UnitType.TANK: 12, UnitType.SNIPER: 5, UnitType.SCOUT: 8, UnitType.BOMBER: 6, UnitType.MINER: 7}
MOVE = {UnitType.TANK: 2, UnitType.SNIPER: 2, UnitType.SCOUT: 3, UnitType.BOMBER: 2, UnitType.MINER: 1}
NAMES = {UnitType.TANK: "Tank", UnitType.SNIPER: "Sniper", UnitType.SCOUT: "Scout",
         UnitType.BOMBER: "Bomber", UnitType.MINER: "Miner"}
ATTACK_TEXT = {
    UnitType.TANK: "Hits the 1st or 2nd cell straight ahead. Turns only by moving.",
    UnitType.SNIPER: "Hits any enemy within 5 cells. Weaker up close.",
    UnitType.SCOUT: "Hits an adjacent enemy.",
    UnitType.BOMBER: "Missile 1-2 cells in a line. One airstrike per match.",
    UnitType.MINER: "Hits an adjacent enemy. Burrows 1-2 cells.",
}
WIN_POINTS = 10
PLY_LIMIT = 200
HOLD_ACTIONS = 3


def terrain_at(pos: Pos) -> Terrain:
    if pos in WALLS:
        return Terrain.WALL
    if pos in COVER or pos in BASES.values():
        return Terrain.COVER                      # both bases sit on cover
    return Terrain.OPEN


def is_base(pos: Pos) -> Optional[Side]:
    for side, b in BASES.items():
        if b == pos:
            return side
    return None


@dataclass(frozen=True)
class Unit:
    id: str
    side: Side
    type: UnitType
    pos: Pos
    hp: int
    facing: Direction = Direction.E


@dataclass(frozen=True)
class GameState:
    units: Tuple[Unit, ...]
    side_to_move: Side = Side.HUMAN
    points: Tuple[int, int] = (0, 0)              # (human, ai)
    hold: Tuple[int, int] = (0, 0)                # capture pips: human holding AI base, AI holding human base
    captured: Tuple[bool, bool] = (False, False)
    airstrike_used: Tuple[bool, bool] = (False, False)
    action_no: int = 0

    def unit_at(self, pos: Pos) -> Optional[Unit]:
        for u in self.units:
            if u.pos == pos:
                return u
        return None

    def unit_by_id(self, uid: str) -> Optional[Unit]:
        for u in self.units:
            if u.id == uid:
                return u
        return None

    def units_of(self, side: Side):
        return [u for u in self.units if u.side == side]

    def replace_unit(self, new_unit: Unit) -> "GameState":
        return replace(self, units=tuple(new_unit if u.id == new_unit.id else u for u in self.units))

    def remove_unit(self, uid: str) -> "GameState":
        return replace(self, units=tuple(u for u in self.units if u.id != uid))


def side_index(side: Side) -> int:
    return 0 if side == Side.HUMAN else 1


def make_stub_state(human: str = "TSB", ai: str = "TCM", mid_game: bool = False) -> GameState:
    """A hard-coded starting position. `human` and `ai` are three distinct letters from T S C B M."""
    for name, lineup in (("human", human), ("ai", ai)):
        if len(lineup) != 3 or len(set(lineup)) != 3 or any(ch not in "TSCBM" for ch in lineup):
            raise ValueError(f"{name} lineup must be three distinct letters from TSCBM, got {lineup!r}")
    units = []
    for side, lineup, tag in ((Side.HUMAN, human, "H"), (Side.AI, ai, "A")):
        for i, ch in enumerate(lineup):
            t = UnitType(ch)
            units.append(Unit(f"{tag}{i + 1}", side, t, SPAWNS[side][i], MAX_HP[t],
                              Direction.E if side == Side.HUMAN else Direction.W))
    state = GameState(tuple(units))
    if mid_game:                                   # damage, score and capture pips, to test the HUD
        hurt = {"H1": 7, "H2": 2, "A2": 3, "A3": 5}
        state = replace(state, units=tuple(replace(u, hp=min(u.hp, hurt.get(u.id, u.hp))) for u in state.units),
                        points=(4, 2), hold=(2, 0), action_no=17)
    return state
