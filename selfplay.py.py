"""Balance check, soak test and weight tuning (Q32).

AI plays AI: the search simply runs for whichever side is to move, so the two
armies are labelled HUMAN and AI only because those are the game's side names.
Purpose: catch a dominant first-move rush or a dominant unit. It is a sanity
check, not a proof of balance, and says nothing about how a person plays.

    records = run_selfplay(games=200, depth=2, seed=0)
    save_selfplay(records, "results")

Every ply is checked with validate_invariants() (the soak test), and a game
that raises or never ends fails loudly.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable, Iterable, Optional

import pandas as pd

from tactical_game import config, rules
from tactical_game.domain import GameState, Side, UnitType
from tactical_game.ai.evaluation import (
    DEFAULT_WEIGHTS,
    TERM_NAMES,
    EvaluationWeights,
    Evaluator,
    opponent,
    side_value,
)
from tactical_game.ai.search import SearchConfig, choose_action_alphabeta

DEFAULT_OPENING_PLIES = 2  # seeded random actions to diversify the start
LINEUPS: tuple[tuple[UnitType, ...], ...] = tuple(
    itertools.combinations(UnitType, 3))  # the 10 possible lineups
WIN_SHARE_NEUTRAL = 0.5
TUNING_FACTORS = (0.5, 1.5)
TUNING_LOG_COLUMNS = ["trial", "weight", "factor", "old_value", "new_value",
                      "games", "depth", "wins", "draws", "losses",
                      "win_share", "kept", "weights_after"]


class GameDidNotEnd(AssertionError):
    """A self-play game went past the ply limit without a result."""


@dataclass(frozen=True)
class GameRecord:
    """One finished self-play game (one CSV row)."""

    game: int
    human_lineup: str
    ai_lineup: str
    first_side: str
    winner: str  # HUMAN, AI or DRAW
    reason: str  # POINTS, ELIMINATION or PLY_LIMIT
    winner_captured: bool  # the winner captured the enemy base
    plies: int
    human_points: int
    ai_points: int


def _lineup_text(lineup: Iterable[UnitType]) -> str:
    return "+".join(t.name for t in lineup)


def _lineup_pairs(seed: int) -> list[tuple[tuple[UnitType, ...], tuple[UnitType, ...]]]:
    """All 100 ordered (human, ai) lineup pairs in a seeded random order."""
    pairs = [(h, a) for h in LINEUPS for a in LINEUPS]
    random.Random(seed).shuffle(pairs)
    return pairs




def play_game(game: int, human_lineup, ai_lineup, first_side: Side, seed: int,
              depth: int, evaluators: dict[Side, Evaluator],
              opening_plies: int = DEFAULT_OPENING_PLIES,
              validate: bool = True) -> GameRecord:
    """Play one AI-versus-AI match and return its record.

    ``seed`` fixes the airstrike dice and the random opening, so the game can
    be replayed. ``evaluators`` gives each side its own heuristic (the same one
    for a plain balance check, different ones when tuning). With ``validate``
    every ply is followed by validate_invariants().
    """
    rng = random.Random(seed)
    state = rules.initial_state(human_lineup, ai_lineup, seed, first_side)
    for _ in range(opening_plies):
        if state.result is not None:
            break
        state = rules.apply_action(state, rng.choice(rules.legal_actions(state)))
        if validate:
            state.validate_invariants()

    ply_cap = config.DEFAULT_CONFIG.PLY_LIMIT + 1
    search_config = SearchConfig(depth=depth)
    while state.result is None:
        if state.ply > ply_cap:
            raise GameDidNotEnd(f"game {game} passed ply {ply_cap} without a result")
        mover = state.side_to_move
        choice = choose_action_alphabeta(state, search_config, evaluators[mover])
        state = rules.apply_action(state, choice.action)
        if validate:
            state.validate_invariants()
    return _record(game, human_lineup, ai_lineup, first_side, state)


def _record(game: int, human_lineup, ai_lineup, first_side: Side,
            state: GameState) -> GameRecord:
    result = state.result
    winner = "DRAW" if result.winner is None else result.winner.name
    captured = (result.winner is not None
                and bool(side_value(state.base_captured, result.winner)))
    return GameRecord(
        game=game, human_lineup=_lineup_text(human_lineup),
        ai_lineup=_lineup_text(ai_lineup), first_side=first_side.name,
        winner=winner, reason=result.reason.name, winner_captured=captured,
        plies=state.ply,
        human_points=side_value(state.points, Side.HUMAN),
        ai_points=side_value(state.points, Side.AI),
    )


# ------------------------------------------------------------ balance check

def run_selfplay(games: int, depth: int = 2, seed: int = 0,
                 weights: Optional[dict[Side, EvaluationWeights]] = None,
                 opening_plies: int = DEFAULT_OPENING_PLIES,
                 validate: bool = True,
                 on_game: Optional[Callable[[GameRecord], None]] = None
                 ) -> list[GameRecord]:
    """AI-versus-AI matches with varied lineups, alternating first mover.

    Game g uses the (g // 2)-th lineup pair of a seeded shuffle of all 100
    ordered pairs, and the first mover alternates HUMAN, AI, HUMAN... so each
    pair is played once with each side starting (200 games cover everything).
    ``weights`` optionally gives each side its own EvaluationWeights.
    Raises if any game errors, breaks an invariant or never ends.
    """
    weights = weights or {}
    evaluators = {
        side: Evaluator(weights.get(side, DEFAULT_WEIGHTS)) for side in Side
    }
    pairs = _lineup_pairs(seed)
    records: list[GameRecord] = []
    for game in range(games):
        human_lineup, ai_lineup = pairs[(game // 2) % len(pairs)]
        first_side = Side.HUMAN if game % 2 == 0 else Side.AI
        record = play_game(game, human_lineup, ai_lineup, first_side,
                           seed * 100_003 + game, depth, evaluators,
                           opening_plies, validate)
        records.append(record)
        if on_game is not None:
            on_game(record)
    return records


def summarize_selfplay(records: Iterable[GameRecord]) -> dict[str, float]:
    
    """Wins, draws, game length and how games ended, as flat name -> value.
    first_mover_share is the first mover's share of decided games (0.5 is
    fair). unit_win_rate_X is the share of games a team fielding unit X won,
    over all games where X was fielded (a draw counts as not won).
    """
    table = pd.DataFrame([asdict(r) for r in records])
    if table.empty:
        raise ValueError("no games to summarize")
    decided = table[table["winner"] != "DRAW"]
    first_wins = int((decided["winner"] == decided["first_side"]).sum())
    out: dict[str, float] = {
        "games": len(table),
        "human_wins": int((table["winner"] == "HUMAN").sum()),
        "ai_wins": int((table["winner"] == "AI").sum()),
        "draws": int((table["winner"] == "DRAW").sum()),
        "first_mover_wins": first_wins,
        "first_mover_share": first_wins / len(decided) if len(decided) else float("nan"),
        "average_plies": float(table["plies"].mean()),
        "ended_elimination": int((table["reason"] == "ELIMINATION").sum()),
        "ended_ply_limit": int((table["reason"] == "PLY_LIMIT").sum()),
        "ended_capture_and_points": int(
            ((table["reason"] == "POINTS") & table["winner_captured"]).sum()),
        "ended_points_only": int(
            ((table["reason"] == "POINTS") & ~table["winner_captured"]).sum()),
    }
    for unit_type in UnitType:
        fielded = won = 0
        for _, row in table.iterrows():
            for side, lineup in (("HUMAN", row["human_lineup"]),
                                 ("AI", row["ai_lineup"])):
                if unit_type.name in lineup.split("+"):
                    fielded += 1
                    won += row["winner"] == side
        out[f"unit_win_rate_{unit_type.name}"] = won / fielded if fielded else float("nan")
        out[f"unit_games_{unit_type.name}"] = fielded
    return out


def save_selfplay(records: list[GameRecord], out_dir: str | Path,
                  stem: str = "selfplay") -> dict[str, Path]:
    """Write ``<stem>_games.csv`` and ``<stem>_summary.csv``; return paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {"games": out / f"{stem}_games.csv",
             "summary": out / f"{stem}_summary.csv"}
    pd.DataFrame([asdict(r) for r in records]).to_csv(paths["games"], index=False)
    summary = summarize_selfplay(records)
    pd.DataFrame({"metric": list(summary), "value": list(summary.values())}
                 ).to_csv(paths["summary"], index=False)
    return paths


# ------------------------------------------------------------------ tuning

def _play_match(candidate: EvaluationWeights, baseline: EvaluationWeights,
                games: int, depth: int, seed: int,
                opening_plies: int) -> tuple[int, int, int]:
    """Candidate weights against baseline weights: (wins, draws, losses).

    Each lineup pair is played four times so the candidate takes each side
    and each side moves first equally often, cancelling both biases.
    """
    pairs = _lineup_pairs(seed)
    wins = draws = losses = 0
    for game in range(games):
        human_lineup, ai_lineup = pairs[(game // 4) % len(pairs)]
        candidate_side = Side.HUMAN if game % 2 == 0 else Side.AI
        first_side = Side.HUMAN if (game // 2) % 2 == 0 else Side.AI
        evaluators = {candidate_side: Evaluator(candidate),
                      opponent(candidate_side): Evaluator(baseline)}
        record = play_game(game, human_lineup, ai_lineup, first_side,
                           seed * 100_003 + game, depth, evaluators,
                           opening_plies, validate=False)
        if record.winner == "DRAW":
            draws += 1
        elif record.winner == candidate_side.name:
            wins += 1
        else:
            losses += 1
    return wins, draws, losses


def _weights_text(weights: EvaluationWeights) -> str:
    return " ".join(f"{name}={getattr(weights, name):g}" for name in TERM_NAMES)


def tune_weights(weights: EvaluationWeights = DEFAULT_WEIGHTS, games: int = 100,
                 depth: int = 2, seed: int = 0,
                 factors: Iterable[float] = TUNING_FACTORS,
                 log_path: Optional[str | Path] = None,
                 opening_plies: int = DEFAULT_OPENING_PLIES,
                 margin: float = 0.0
                 ) -> tuple[EvaluationWeights, pd.DataFrame]:
    """Tune one evaluation weight at a time by self-play.

    For each weight (in TERM_NAMES order) and each factor, the changed weights
    play ``games`` games against the current weights. The change is kept only
    if the candidate's win share (a draw counts half) beats 0.5 by more than
    ``margin``; after a kept change the next weight is tried from the new
    base. Every trial is appended to ``log_path`` (a CSV) when given: this
    table goes into the report.

    Returns the final weights and the log of trials as a DataFrame.
    """
    current = weights
    log: list[dict] = []
    trial = 0
    for name in TERM_NAMES:
        for factor in factors:
            old_value = getattr(current, name)
            new_value = round(old_value * factor, 2)
            if new_value == old_value:
                continue
            trial += 1
            candidate = replace(current, **{name: new_value})
            wins, draws, losses = _play_match(
                candidate, current, games, depth, seed + trial, opening_plies)
            share = (wins + 0.5 * draws) / games
            kept = share > WIN_SHARE_NEUTRAL + margin
            if kept:
                current = candidate
            row = {"trial": trial, "weight": name, "factor": factor,
                   "old_value": old_value, "new_value": new_value,
                   "games": games, "depth": depth, "wins": wins,
                   "draws": draws, "losses": losses, "win_share": share,
                   "kept": kept, "weights_after": _weights_text(current)}
            log.append(row)
            if log_path is not None:
                _append_log(row, Path(log_path))
            if kept:
                break
    return current, pd.DataFrame(log, columns=TUNING_LOG_COLUMNS)


def _append_log(row: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row], columns=TUNING_LOG_COLUMNS).to_csv(
        path, mode="a", header=not path.exists(), index=False)