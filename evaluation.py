"""Heuristic evaluation and terminal scoring (Q23, Q24).

Imports follow the one-way rule of Section 5.1: this module may import
``rules`` and ``domain`` and nothing from the UI.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Optional

from tactical_game import config, domain, rules
from tactical_game.domain import GameState, Position, Side, Terrain

# A won position scores TERMINAL_WIN_SCORE minus the plies from the root.
TERMINAL_WIN_SCORE = 10_000

# Stand-in for "no path" and for a side with no units; larger than any real
# shortest path on the 8x8 board.
UNREACHABLE_DISTANCE = 64

TERM_NAMES = ("points", "health", "progress", "distance", "safety")

_SIDE_INDEX = {Side.HUMAN: 0, Side.AI: 1}


def opponent(side: Side) -> Side:
    """The other side."""
    return Side.AI if side is Side.HUMAN else Side.HUMAN


def side_value(per_side, side: Side):
    """Read a per-side field of GameState (points, capture_progress, ...).

    The shared contract only says these fields exist "per side", so both a
    mapping keyed by Side and a (human, ai) pair are accepted. This is the
    single place that knows the container type.
    """
    if isinstance(per_side, Mapping):
        return per_side[side]
    if isinstance(per_side, Sequence):
        return per_side[_SIDE_INDEX[side]]
    raise TypeError(f"cannot read a per-side value from {type(per_side)!r}")


@dataclass(frozen=True)
class EvaluationWeights:
    """How much each heuristic term counts (starting guesses, tuned in Q32)."""

    points: float = 20
    health: float = 4
    progress: float = 10
    distance: float = 2
    safety: float = 4


DEFAULT_WEIGHTS = EvaluationWeights()


class Evaluator:
    """Scores a GameState from a root side's point of view (Q23).

    Each term is root minus opponent, so ``evaluate(state, HUMAN)`` equals
    ``-evaluate(state, AI)`` for any state (the symmetry test). One Evaluator
    keeps a small distance cache; create one per search (or per thread).
    """

    def __init__(self, weights: EvaluationWeights = DEFAULT_WEIGHTS) -> None:
        self.weights = weights
        self._board: Optional[domain.Board] = None
        self._distances: dict[tuple[Position, Position], int] = {}

    # ------------------------------------------------------------ the terms

    def points(self, state: GameState, root: Side) -> float:
        """Root points minus opponent points."""
        return (side_value(state.points, root)
                - side_value(state.points, opponent(root)))

    def health(self, state: GameState, root: Side) -> float:
        """Root total HP minus opponent total HP."""
        diff = 0
        for unit in state.units:
            diff += unit.hp if unit.side is root else -unit.hp
        return diff

    def progress(self, state: GameState, root: Side) -> float:
        """Root hold count minus opponent hold count on the enemy base."""
        return (side_value(state.capture_progress, root)
                - side_value(state.capture_progress, opponent(root)))

    def distance(self, state: GameState, root: Side) -> float:
        """Opponent's distance to the root's base minus the root's distance
        to the opponent's base (nearest unit each, BFS over terrain only).

        A side that already captured the enemy base counts as distance 0.
        """
        foe = opponent(root)
        return (self._distance_to_goal(state, foe)
                - self._distance_to_goal(state, root))

    def safety(self, state: GameState, root: Side) -> float:
        """(units on cover - units an enemy can hit now) for the root, minus
        the same for the opponent."""
        return (self._side_safety(state, root)
                - self._side_safety(state, opponent(root)))

    # ------------------------------------------------------------- combined

    def weighted_terms(self, state: GameState, root: Side) -> dict[str, float]:
        """Each term already multiplied by its weight, in TERM_NAMES order."""
        w = self.weights
        return {
            "points": w.points * self.points(state, root),
            "health": w.health * self.health(state, root),
            "progress": w.progress * self.progress(state, root),
            "distance": w.distance * self.distance(state, root),
            "safety": w.safety * self.safety(state, root),
        }

    def evaluate(self, state: GameState, root: Side) -> float:
        """The weighted sum of the five terms (never called on a finished
        match; use terminal_score there)."""
        return sum(self.weighted_terms(state, root).values())

    # -------------------------------------------------------------- helpers

    def _side_safety(self, state: GameState, side: Side) -> int:
        board = state.terrain
        on_cover = sum(
            1 for u in state.units
            if u.side is side and board.terrain_at(u.pos) is Terrain.COVER
        )
        return on_cover - len(rules.threatened_units(state, side))

    def _distance_to_goal(self, state: GameState, side: Side) -> int:
        """Nearest unit of ``side`` to the enemy base; 0 once captured."""
        if side_value(state.base_captured, side):
            return 0
        goal = state.terrain.base_of(opponent(side))
        best = UNREACHABLE_DISTANCE
        for unit in state.units:
            if unit.side is side:
                best = min(best, self._cached_distance(state.terrain, unit.pos, goal))
        return best

    def _cached_distance(self, board: domain.Board, start: Position,
                         goal: Position) -> int:
        if board is not self._board:
            if self._board is None or board != self._board:
                self._distances = {}
            self._board = board
        key = (start, goal)
        found = self._distances.get(key)
        if found is None:
            found = rules.shortest_distance(board, start, goal)
            if found is None:
                found = UNREACHABLE_DISTANCE
            self._distances[key] = found
        return found


# ----------------------------------------------------------- terminal (Q24)

def terminal_score(state: GameState, ply_from_root: int, root: Side) -> float:
    """Score of a finished match for the root side.

    +10,000 minus the plies from the root for a win, -10,000 plus the plies for
    a loss, 0 for a draw: faster wins and slower losses are preferred.
    """
    result = state.result
    if result is None:
        raise ValueError("terminal_score needs a finished match")
    if result.winner is None:
        return 0
    if result.winner is root:
        return TERMINAL_WIN_SCORE - ply_from_root
    return -TERMINAL_WIN_SCORE + ply_from_root


def _farthest_cell_from_bases(board: domain.Board) -> int:
    """Longest shortest-path from any open cell to either base."""
    farthest = 0
    for side in (Side.HUMAN, Side.AI):
        base = board.base_of(side)
        for row in range(config.DEFAULT_CONFIG.board_size):
            for col in range(config.DEFAULT_CONFIG.board_size):
                cell = Position(row, col)
                if board.is_passable(cell):
                    d = rules.shortest_distance(board, cell, base)
                    farthest = max(farthest, UNREACHABLE_DISTANCE if d is None else d)
    return farthest


def max_heuristic_bound(weights: EvaluationWeights = DEFAULT_WEIGHTS) -> float:
    """Largest |evaluate| any non-terminal state can produce.

    Built from the weights and the rules, term by term:
      points    both sides stay below WIN_POINTS (else the match is over)
      health    the three highest-HP unit types make the largest lineup
      progress  hold counts run 0..HOLD_ACTIONS
      distance  the longest path from any cell to a base on the real map
      safety    each side contributes at most +/- its unit count
    The result must stay well below TERMINAL_WIN_SCORE minus the deepest
    search, so a heuristic score can never outrank a real win or loss.
    Recompute (call again) whenever weights or unit stats change.
    """
    cfg = config.DEFAULT_CONFIG
    units_per_side = len(cfg.human_spawns)
    hp_values = sorted((p.max_hp for p in config.PROFILES.values()), reverse=True)
    largest_lineup_hp = sum(hp_values[:units_per_side])
    farthest = _farthest_cell_from_bases(domain.Board.default())
    return (
        abs(weights.points) * (cfg.WIN_POINTS - 1)
        + abs(weights.health) * largest_lineup_hp
        + abs(weights.progress) * cfg.HOLD_ACTIONS
        + abs(weights.distance) * farthest
        + abs(weights.safety) * 2 * units_per_side
    )