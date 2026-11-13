"""domain.py  (Q12)

The basic "words" of the game: enums, small frozen data classes and errors.
Nothing in here knows about rules, AI or UI. Everyone else imports from this file.

Big idea: every class below is FROZEN. Once an object is created it can never
be changed. To "change" something we build a new copy (see with_pos, with_hp).
"""

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Optional

# The board is 8 x 8. (config.py will also store this, but domain.py cannot
# import config.py because config.py imports domain.py. So we keep one copy here.)
BOARD_SIZE = 8


# ---------------------------------------------------------------------------
# 1. ENUMS: fixed lists of names. They stop typos like "humen" or "tnak".
# ---------------------------------------------------------------------------

class Side(Enum):
    HUMAN = auto()
    AI = auto()


class UnitType(Enum):
    TANK = auto()
    SNIPER = auto()
    SCOUT = auto()
    BOMBER = auto()
    MINER = auto()


class Terrain(Enum):
    OPEN = auto()
    WALL = auto()
    COVER = auto()


class Direction(Enum):
    """Each direction stores (row change, column change).
    Row 0 is the TOP of the board, so going North means row - 1."""
    N = (-1, 0)
    E = (0, 1)
    S = (1, 0)
    W = (0, -1)


class ActionKind(Enum):
    MOVE = auto()
    ATTACK = auto()
    AIRSTRIKE = auto()
    BURROW = auto()
    PASS = auto()


class Reason(Enum):
    """How a match ended."""
    POINTS = auto()
    ELIMINATION = auto()
    PLY_LIMIT = auto()


# ---------------------------------------------------------------------------
# 2. EXCEPTIONS: our own error types, shared by all three people.
# ---------------------------------------------------------------------------

class RuleViolation(Exception):
    """Raised when someone tries an illegal action. The UI shows its message."""


class SearchCancelled(Exception):
    """Raised when the AI search is stopped from outside (restart or close)."""


# ---------------------------------------------------------------------------
# 3. POSITION: one cell on the board, written (row, col).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def in_bounds(self) -> bool:
        """True if this cell is inside the 8x8 board."""
        return 0 <= self.row < BOARD_SIZE and 0 <= self.col < BOARD_SIZE    #row and col is in between 0 and 8

    def step(self, direction: Direction) -> "Position":
        """The cell one step away in the given direction.
        It can land off the board. Use in_bounds() to check."""
        row_change, col_change = direction.value    # value of the tuple direction is split in row and column
        return Position(self.row + row_change, self.col + col_change)

    def neighbors(self) -> list["Position"]:
        """The cells next to this one (N, E, S, W order), only those on the board."""
        result = []
        for direction in (Direction.N, Direction.E, Direction.S, Direction.W):
            cell = self.step(direction)
            if cell.in_bounds():        #It builds an empty list, tries the four directions in a fixed order, keeps only cells on the board, and returns the list.
                result.append(cell)
        return result

    def manhattan(self, other: "Position") -> int:
        """Distance in steps if you can only walk up, down, left, right."""
        return abs(self.row - other.row) + abs(self.col - other.col)


# ---------------------------------------------------------------------------
# 4. UNIT: one soldier on the board.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Unit:
    id: str                 # "H1".."H3" for the human, "A1".."A3" for the AI
    side: Side
    unit_type: UnitType
    pos: Position
    hp: int
    facing: Direction = Direction.E   # only Tanks really use this

    def __post_init__(self) -> None:
        # Runs right after the object is created. Bad data stops here.
        if not self.pos.in_bounds():
            raise ValueError(f"Unit {self.id} is off the board: {self.pos}")
        if self.hp < 0:
            raise ValueError(f"Unit {self.id} has negative hp: {self.hp}")

    # The three with_ methods return a NEW Unit. The old one stays the same.
    # replace() makes a copy with one field changed (and re-runs the checks).
    def with_pos(self, new_pos: Position) -> "Unit":
        return replace(self, pos=new_pos)

    def with_hp(self, new_hp: int) -> "Unit":
        return replace(self, hp=new_hp)

    def with_facing(self, new_facing: Direction) -> "Unit":
        return replace(self, facing=new_facing)

    def is_alive(self) -> bool:
        return self.hp > 0


# ---------------------------------------------------------------------------
# 5. ACTION: one thing a player does on their turn.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Action:
    kind: ActionKind
    unit_id: Optional[str]          # which unit acts (None for PASS)
    target: Optional[Position]      # where to (None for PASS)

    def __post_init__(self) -> None:
        if self.kind == ActionKind.PASS:
            if self.target is not None:
                raise ValueError("PASS must not have a target")
        else:
            if self.target is None:
                raise ValueError(f"{self.kind.name} needs a target")
            if not self.target.in_bounds():
                raise ValueError(f"Target is off the board: {self.target}")

    # Factory methods: short, readable ways to build each kind of action.
    # Example: Action.move("H1", Position(3, 2))
    @staticmethod
    def move(unit_id: str, target: Position) -> "Action":
        return Action(ActionKind.MOVE, unit_id, target)

    @staticmethod
    def attack(unit_id: str, target: Position) -> "Action":
        return Action(ActionKind.ATTACK, unit_id, target)

    @staticmethod
    def airstrike(unit_id: str, centre: Position) -> "Action":
        return Action(ActionKind.AIRSTRIKE, unit_id, centre)

    @staticmethod
    def burrow(unit_id: str, landing: Position) -> "Action":
        return Action(ActionKind.BURROW, unit_id, landing)

    @staticmethod
    def pass_turn() -> "Action":
        return Action(ActionKind.PASS, None, None)


# ---------------------------------------------------------------------------
# 6. GAMERESULT: how a finished match ended.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GameResult:
    winner: Optional[Side]   # None means a draw
    reason: Reason


# ---------------------------------------------------------------------------
# Quick self-check. Run this file directly:  python domain.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    p = Position(3, 1)
    print("neighbors of (3,1):", p.neighbors())
    print("step North from (0,0) is on board?", Position(0, 0).step(Direction.N).in_bounds())
    print("distance (0,0) to (3,4):", Position(0, 0).manhattan(Position(3, 4)))

    tank = Unit("H1", Side.HUMAN, UnitType.TANK, Position(3, 1), 12)
    hurt = tank.with_hp(7)
    print("old hp:", tank.hp, "| new hp:", hurt.hp)      # 12 and 7

    try:
        tank.hp = 1                                       # frozen: this must fail
    except Exception as error:
        print("cannot edit a frozen unit:", type(error).__name__)

    try:
        Unit("H2", Side.HUMAN, UnitType.SNIPER, Position(9, 9), 5)
    except ValueError as error:
        print("bad unit rejected:", error)

    print(Action.move("H1", Position(3, 2)))
    print(Action.pass_turn())
    print(GameResult(Side.HUMAN, Reason.POINTS))