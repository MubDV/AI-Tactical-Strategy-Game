"""Shared builders for tests."""

import random

from tactical_game import config, rules
from tactical_game.domain import Direction, Position, Side, Unit, UnitType

H, A = Side.HUMAN, Side.AI
TANK, SNIPER, SCOUT, BOMBER, MINER = (
    UnitType.TANK, UnitType.SNIPER, UnitType.SCOUT, UnitType.BOMBER, UnitType.MINER)


def unit(uid, unit_type, row, col, hp=None, facing=None):
    """A unit for a hand-made position; the side comes from the id prefix."""
    side = H if uid.startswith("H") else A
    if facing is None:
        facing = Direction.E if side is H else Direction.W
    return Unit(uid, side, unit_type, Position(row, col),
                hp if hp is not None else config.PROFILES[unit_type].max_hp, facing)


def playout_states(count, seed, max_plies=70):
    """``count`` unfinished states from seeded random playouts (varied lineups)."""
    rng = random.Random(seed)
    types = list(UnitType)
    states, game = [], 0
    while len(states) < count:
        state = rules.initial_state(tuple(rng.sample(types, 3)),
                                    tuple(rng.sample(types, 3)),
                                    seed * 1000 + game, rng.choice(list(Side)))
        for _ in range(rng.randrange(0, max_plies)):
            if state.result is not None:
                break
            state = rules.apply_action(state, rng.choice(rules.legal_actions(state)))
        if state.result is None:
            states.append(state)
        game += 1
    return states