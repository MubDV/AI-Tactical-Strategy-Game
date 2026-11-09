"""TEMPORARY move and attack highlights so the UI can be tried before the rules exist.

This is NOT the rules engine. At milestone M4 delete this file and build the highlights from
`rules.legal_actions(state)` (Person 2). It follows the final rules table so the demo matches.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Dict, List, Set

from .stub import (BOARD_N, DELTA, MOVE, WALLS, COVER, BASES, Direction, GameState, Pos, Side, Terrain,
                   Unit, UnitType, terrain_at)


@dataclass
class Options:
    moves: Dict[Pos, List[Pos]]          # destination -> path of cells (excluding the start)
    attacks: Set[Pos]
    burrows: Set[Pos]


def in_board(p: Pos) -> bool:
    return 0 <= p[0] < BOARD_N and 0 <= p[1] < BOARD_N


def manhattan(a: Pos, b: Pos) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def facing_after_move(origin: Pos, dest: Pos, old: Direction) -> Direction:
    """Final rule: straight move faces that way; a diagonal destination faces East or West by the column change."""
    dr, dc = dest[0] - origin[0], dest[1] - origin[1]
    if dr == 0 and dc == 0:
        return old
    if dc == 0:
        return Direction.S if dr > 0 else Direction.N
    if dr == 0:
        return Direction.E if dc > 0 else Direction.W
    return Direction.E if dc > 0 else Direction.W


def options_for(state: GameState, u: Unit) -> Options:
    occupied = {x.pos for x in state.units}
    paths: Dict[Pos, List[Pos]] = {}
    q = deque([(u.pos, [])])
    seen = {u.pos}
    while q:
        cell, path = q.popleft()
        if len(path) >= MOVE[u.type]:
            continue
        for d in DELTA.values():
            n = (cell[0] + d[0], cell[1] + d[1])
            if in_board(n) and n not in WALLS and n not in occupied and n not in seen:
                seen.add(n)
                paths[n] = path + [n]
                q.append((n, path + [n]))
    enemies = [x for x in state.units if x.side != u.side]
    att: Set[Pos] = set()
    for e in enemies:
        dr, dc = e.pos[0] - u.pos[0], e.pos[1] - u.pos[1]
        md = abs(dr) + abs(dc)
        if u.type == UnitType.SNIPER and md <= 5:
            att.add(e.pos)
        elif u.type in (UnitType.SCOUT, UnitType.MINER) and md == 1:
            att.add(e.pos)
        elif u.type == UnitType.BOMBER and ((dr == 0 and abs(dc) in (1, 2)) or (dc == 0 and abs(dr) in (1, 2))):
            att.add(e.pos)
        elif u.type == UnitType.TANK:
            fd = DELTA[u.facing]
            if any((u.pos[0] + fd[0] * k, u.pos[1] + fd[1] * k) == e.pos for k in (1, 2)):
                att.add(e.pos)
    burrows: Set[Pos] = set()
    if u.type == UnitType.MINER:
        for d in DELTA.values():
            for k in (1, 2):
                n = (u.pos[0] + d[0] * k, u.pos[1] + d[1] * k)
                if in_board(n) and n not in WALLS and n not in occupied:
                    burrows.add(n)
    return Options(paths, att, burrows)


def attack_damage(attacker: Unit, target: Unit) -> int:
    """Damage table from the final rules, cover -1 (min 1)."""
    if attacker.type == UnitType.TANK:
        base = 10
    elif attacker.type == UnitType.SNIPER:
        d = manhattan(attacker.pos, target.pos)
        base = 3 if d >= 5 else 2 if d >= 3 else 1
    elif attacker.type == UnitType.SCOUT:
        base = 3
    elif attacker.type == UnitType.BOMBER:
        base = 5
    else:
        base = 3
    if terrain_at(target.pos) == Terrain.COVER:
        base = max(1, base - 1)
    return base


def apply_move(state: GameState, u: Unit, dest: Pos) -> GameState:
    f = facing_after_move(u.pos, dest, u.facing) if u.type == UnitType.TANK else u.facing
    s = state.replace_unit(replace(u, pos=dest, facing=f))
    return replace(s, action_no=s.action_no + 1)


def apply_attack(state: GameState, attacker: Unit, target: Unit):
    """Returns (new_state, damage, killed)."""
    dmg = attack_damage(attacker, target)
    hp = target.hp - dmg
    s = state
    pts = list(state.points)
    killed = hp <= 0
    if killed:
        s = s.remove_unit(target.id)
        pts[0 if attacker.side == Side.HUMAN else 1] += 2
    else:
        s = s.replace_unit(replace(target, hp=hp))
    return replace(s, points=tuple(pts), action_no=s.action_no + 1), dmg, killed
