"""config.py  (Q13)

Every number of the game lives in THIS file and nowhere else.
Why: the balance check may change a number (for example a damage value).
If numbers were spread around the code, we would miss some. Here there is
one place to look and one place to change (only after the team agrees).

This file has three things:
  1. UnitProfile : the stats of ONE unit type (hp, move, damage, ranges)
  2. GameConfig  : the board layout and the match rules (points, limits)
  3. PROFILES    : a dictionary that gives the UnitProfile of any UnitType
"""

from dataclasses import dataclass
from typing import Optional

import domain
from domain import Position, UnitType


# ---------------------------------------------------------------------------
# 1. UNITPROFILE: the stats of one unit type. Frozen, so nobody can edit it.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UnitProfile:
    max_hp: int
    move_range: int
    damage: int                                  # damage of the normal attack
    attack_range: int                            # how far the normal attack reaches
    airstrike_range: Optional[int] = None        # Bomber only, others stay None
    airstrike_damage: Optional[int] = None       # Bomber only, others stay None
    damage_bands: tuple = ()                     # Sniper only: ((up to distance, damage), ...)


# ---------------------------------------------------------------------------
# 2. GAMECONFIG: board layout and match rules.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GameConfig:
    # --- Board layout ---
    # The number 8 is written only in domain.py. We read it from there.
    BOARD_SIZE: int = domain.BOARD_SIZE
    WALLS: tuple = (Position(2, 2), Position(2, 5), Position(5, 2), Position(5, 5))

    HUMAN_BASE: Position = Position(4, 1)
    AI_BASE: Position = Position(3, 6)

    # Both bases are cover too, so we reuse the base names written above.
    COVER: tuple = (Position(1, 3), Position(1, 4), Position(6, 3), Position(6, 4),
                    Position(3, 3), Position(4, 4), HUMAN_BASE, AI_BASE)

    # Spawn slots in lineup order: the first unit goes to the first slot, and so on.
    HUMAN_SPAWNS: tuple = (Position(3, 1), Position(5, 0), Position(4, 0))
    AI_SPAWNS: tuple = (Position(4, 6), Position(2, 7), Position(3, 7))

    # --- Match rules ---
    HOLD_ACTIONS: int = 3         # own actions needed to capture a base
    CAPTURE_POINTS: int = 8       # points for a capture (once per base)
    KILL_POINTS: int = 2          # points for killing an enemy unit
    WIN_POINTS: int = 10          # reach this to win
    PLY_LIMIT: int = 200          # one ply = one action by one side

    # --- Special ranges and damage ---
    SNIPER_RANGE: int = 5
    AIRSTRIKE_RANGE: int = 4
    AIRSTRIKE_DAMAGE: int = 6

    # --- Small helpers (the underscore means "for use inside this class") ---
    def _is_inside(self, pos: Position) -> bool:
        """True if the cell is inside this config's board."""
        return 0 <= pos.row < self.BOARD_SIZE and 0 <= pos.col < self.BOARD_SIZE

    def _rotate(self, pos: Position) -> Position:
        """Turn the board 180 degrees: cell (r, c) lands on (7-r, 7-c)."""
        last = self.BOARD_SIZE - 1
        return Position(last - pos.row, last - pos.col)

    def validate(self) -> None:
        """Check the layout is legal and fair. Raises ValueError if not."""
        bases = (self.HUMAN_BASE, self.AI_BASE)
        spawns = self.HUMAN_SPAWNS + self.AI_SPAWNS

        # Check 1: every coordinate is on the board.
        for cell in self.WALLS + self.COVER + bases + spawns:
            if not self._is_inside(cell):
                raise ValueError(f"Cell is off the board: {cell}")

        # Check 2: nobody starts on a wall.
        for cell in bases + spawns:
            if cell in self.WALLS:
                raise ValueError(f"Base or spawn is on a wall: {cell}")

        # Check 3: the map looks the same after a 180 degree turn (fair for both sides).
        if {self._rotate(c) for c in self.WALLS} != set(self.WALLS):
            raise ValueError("Walls are not symmetric")
        if {self._rotate(c) for c in self.COVER} != set(self.COVER):
            raise ValueError("Cover cells are not symmetric")
        if self._rotate(self.HUMAN_BASE) != self.AI_BASE:
            raise ValueError("Bases are not symmetric")
        if tuple(self._rotate(c) for c in self.HUMAN_SPAWNS) != self.AI_SPAWNS:
            raise ValueError("Spawn slots are not symmetric")


# ---------------------------------------------------------------------------
# 3. PROFILES: a dictionary (hash map). PROFILES[UnitType.TANK] gives the Tank's stats.
#    It sits AFTER GameConfig because it reads numbers from GameConfig.
#    That way SNIPER_RANGE, AIRSTRIKE_RANGE and AIRSTRIKE_DAMAGE are written only once.
# ---------------------------------------------------------------------------

PROFILES: dict[UnitType, UnitProfile] = {
    UnitType.TANK: UnitProfile(
        max_hp=12, move_range=2, damage=10, attack_range=2),

    UnitType.SNIPER: UnitProfile(
        max_hp=5, move_range=2, damage=3, attack_range=GameConfig.SNIPER_RANGE,
        # up to distance 2 deals 1, up to 4 deals 2, up to 5 deals 3
        damage_bands=((2, 1), (4, 2), (GameConfig.SNIPER_RANGE, 3))),

    UnitType.SCOUT: UnitProfile(
        max_hp=8, move_range=3, damage=3, attack_range=1),

    UnitType.BOMBER: UnitProfile(
        max_hp=6, move_range=2, damage=5, attack_range=2,      # missile
        airstrike_range=GameConfig.AIRSTRIKE_RANGE,
        airstrike_damage=GameConfig.AIRSTRIKE_DAMAGE),

    UnitType.MINER: UnitProfile(
        max_hp=7, move_range=1, damage=3, attack_range=1),
}


# ---------------------------------------------------------------------------
# Quick self-check. Run this file directly:  python config.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    config = GameConfig()
    config.validate()
    print("default layout is valid")

    print("Tank profile:", PROFILES[UnitType.TANK])
    print("Sniper bands:", PROFILES[UnitType.SNIPER].damage_bands)
    print("Bomber airstrike:", PROFILES[UnitType.BOMBER].airstrike_range,
          "range,", PROFILES[UnitType.BOMBER].airstrike_damage, "damage")

    short = GameConfig(PLY_LIMIT=10)              # override for a short test match
    print("override works:", short.PLY_LIMIT, "(default is", config.PLY_LIMIT, ")")

    try:
        config.PLY_LIMIT = 5                      # frozen: this must fail
    except Exception as error:
        print("cannot edit the config:", type(error).__name__)

    broken = GameConfig(WALLS=(Position(2, 2), Position(2, 5), Position(5, 2)))
    try:
        broken.validate()                         # one wall missing: not symmetric
    except ValueError as error:
        print("bad layout rejected:", error)