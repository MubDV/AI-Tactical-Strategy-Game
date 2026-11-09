"""Builds and caches every picture the renderer needs. Swap this module for image loading in M9."""
from __future__ import annotations

import math
from typing import Dict, Tuple

import pygame

from . import art_terrain as T
from . import art_top as TOP
from . import art_units as U
from . import constants as K
from .gfx import hash01, iso, new_surface, shade, silhouette, tile_distance
from .ground import GroundRenderer
from .projection import grid_to_screen
from .stub import BASES, BOARD_N, Direction, Side, Terrain, UnitType, WALLS, terrain_at

Sprite = Tuple[pygame.Surface, Tuple[int, int]]


def team_palette(side: Side) -> dict:
    return K.HUMAN if side == Side.HUMAN else K.AI


def make_highlight(color, fill_alpha=64, border_alpha=235, rim=0.90) -> pygame.Surface:
    """Pixel-exact translucent diamond: solid outer rim, lighter inner rim, soft fill."""
    s = new_surface(K.TW, K.TH)
    light = shade(color, 1.35)
    for y in range(K.TH):
        for x in range(K.TW):
            d, a, b = tile_distance(x, y)
            if d > 1:
                continue
            if d > rim:
                s.set_at((x, y), (*color, border_alpha))
            elif d > rim - 0.07:
                s.set_at((x, y), (*light, min(255, fill_alpha + 70)))
            else:
                s.set_at((x, y), (*color, fill_alpha))
    return s


def make_corner_brackets(color) -> pygame.Surface:
    """Four short L-shaped ticks on the tile corners; used for the selected unit's tile."""
    s = new_surface(K.TW, K.TH)
    cx, cy = K.TW // 2, K.TH // 2
    for x in range(K.TW):
        for y in range(K.TH):
            d, a, b = tile_distance(x, y)
            if 0.80 < d <= 1.0:
                if abs(a) > 14 or abs(b) > 7:
                    s.set_at((x, y), (*color, 255))
    return s


class Art:
    def __init__(self):
        self.bg_plain = T.make_background()
        self.tiles_iso = self._tiles_layer()
        self.board_layer = self._make_board_layer()
        self.rocks = [T.make_rock(s) for s in (3, 8, 13, 21)]
        self.rocks_top = [TOP.make_rock_top(s) for s in (3, 8, 13, 21)]
        self.hq_top = {Side.HUMAN: TOP.make_hq_top(K.HUMAN), Side.AI: TOP.make_hq_top(K.AI)}
        self.ground = None                                       # the front-view ground (needs numpy); built by warm_up()
        self._scaled: Dict[tuple, tuple] = {}
        self._top_units: Dict[tuple, Sprite] = {}
        self.pines = [T.make_pine(v) for v in range(3)]
        self.bush = T.make_bush()
        self.hq = {Side.HUMAN: T.make_hq(K.HUMAN), Side.AI: T.make_hq(K.AI)}
        self.hl = {
            "move": make_highlight(K.HL_MOVE, 88),
            "attack": make_highlight(K.HL_ATTACK, 104),
            "burrow": make_highlight(K.HL_BURROW, 96),
            "hover": make_highlight(K.HL_HOVER, 34, 200),
            "select": make_highlight(K.HL_SELECT, 46, 255, 0.84),
            "blocked": make_highlight((255, 90, 90), 40, 200),
        }
        self.brackets = make_corner_brackets((255, 255, 255))
        self._units: Dict[tuple, Sprite] = {}
        self._outlines: Dict[tuple, pygame.Surface] = {}
        self._markers: Dict[tuple, pygame.Surface] = {}
        self._arrows: Dict[tuple, pygame.Surface] = {}
        self._icons: Dict[tuple, pygame.Surface] = {}

    # ---------------------------------------------------------------- ground
    def _variant(self, r: int, c: int):
        t = terrain_at((r, c))
        kind = "rock" if t == Terrain.WALL else "forest" if t == Terrain.COVER else "grass"
        tint, amt = (None, 0.0)
        if c <= 1:
            tint, amt = K.HUMAN["main"], 0.11
        elif c >= BOARD_N - 2:
            tint, amt = K.AI["main"], 0.11
        return kind, (r + c) % 2, int(hash01(r, c, 5) * 4), tint, amt

    def _tiles_layer(self) -> pygame.Surface:
        """Just the diamond ground tiles on a transparent 640x360 surface."""
        layer = new_surface(K.LOGICAL_W, K.LOGICAL_H)
        cache = {}
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                key = self._variant(r, c)
                if key not in cache:
                    cache[key] = T.make_ground_tile(*key)
                cx, cy = grid_to_screen(r, c)
                layer.blit(cache[key], (int(cx - K.TW / 2), int(cy - K.TH / 2)))
        return layer

    def _flat_layer(self) -> pygame.Surface:
        """The same ground seen from straight above: 8x8 square tiles, FLAT pixels each."""
        n = T.FLAT
        layer = pygame.Surface((n * BOARD_N, n * BOARD_N))
        cache = {}
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                key = self._variant(r, c)
                if key not in cache:
                    cache[key] = T.make_flat_tile(*key)
                layer.blit(cache[key], (c * n, r * n))
        return layer

    def _make_board_layer(self) -> pygame.Surface:
        bg = self.bg_plain.copy()
        T.draw_board_shadow(bg)
        for r in range(BOARD_N):                                   # earth sides under the board edge
            for c in range(BOARD_N):
                cx, cy = grid_to_screen(r, c)
                if r == BOARD_N - 1:
                    bg.blit(T.make_slab_face("left", c % 3), (int(cx - K.TW / 2), int(cy - K.TH / 2)))
                if c == BOARD_N - 1:
                    bg.blit(T.make_slab_face("right", r % 3), (int(cx), int(cy - K.TH / 2)))
        bg.blit(self.tiles_iso, (0, 0))
        return bg

    def warm_up(self):
        """Builds everything the view change needs now, so the first press of V does not stall."""
        from .camera import Camera
        if self.ground is None:
            self.ground = GroundRenderer(self.tiles_iso, self._flat_layer(), T.make_background(grid=False), self.board_layer)
            self.ground.layer(Camera(0.5))
            self.ground.layer(Camera(1.0))

    def board(self, cam) -> pygame.Surface:
        """Backdrop and board for a camera (the original pre-drawn board in the diamond view)."""
        if cam.is_iso:
            return self.board_layer
        self.warm_up()
        return self.ground.layer(cam)

    # ---------------------------------------------------------------- units
    def unit(self, utype: UnitType, side: Side, facing: Direction = Direction.E) -> Sprite:
        f = int(facing) if utype == UnitType.TANK else 0
        key = (utype, side, f)
        if key not in self._units:
            P, ai = team_palette(side), side == Side.AI
            if utype == UnitType.TANK:
                self._units[key] = U.make_tank(P, f, ai)
            elif utype == UnitType.SNIPER:
                self._units[key] = U.make_sniper(P, ai)
            elif utype == UnitType.SCOUT:
                self._units[key] = U.make_scout(P, ai)
            elif utype == UnitType.MINER:
                self._units[key] = U.make_miner(P, ai)
            else:
                self._units[key] = U.make_bomber_body(P, ai)
        return self._units[key]

    def unit_outline(self, utype, side, facing, color=(255, 255, 255), thickness=1) -> pygame.Surface:
        """Ring-only silhouette (white for selected, red for friendly fire warnings)."""
        key = (utype, side, int(facing) if utype == UnitType.TANK else 0, color, thickness)
        if key not in self._outlines:
            from .gfx import silhouette
            surf, _ = self.unit(utype, side, facing)
            pad = new_surface(surf.get_width() + 4, surf.get_height() + 4)
            pad.blit(surf, (2, 2))
            self._outlines[key] = silhouette(pad, color, thickness)
        return self._outlines[key]

    def icon(self, utype: UnitType, side: Side, size: int = 30) -> pygame.Surface:
        key = (utype, side, size)
        if key not in self._icons:
            surf, _ = self.unit(utype, side, Direction.E if side == Side.HUMAN else Direction.W)
            self._icons[key] = U.unit_icon(surf, size)
        return self._icons[key]

    def unit_top(self, utype: UnitType, side: Side, facing: Direction = Direction.E):
        """The front-view version of a unit's sprite, or None when the diamond-view sprite is simply scaled (standing figures)."""
        if utype not in (UnitType.TANK, UnitType.BOMBER):
            return None
        f = int(facing) if utype == UnitType.TANK else 0
        key = (utype, side, f)
        if key not in self._top_units:
            P = team_palette(side)
            self._top_units[key] = TOP.make_tank_top(P, f) if utype == UnitType.TANK else TOP.make_bomber_top(P, side == Side.AI)
        return self._top_units[key]

    def scaled(self, sprite: Sprite, ratio: float, settled: bool) -> Sprite:
        """A sprite scaled by `ratio`. Settled views use a few cached, palette-snapped sizes; a moving camera smooths."""
        surf, (ax, ay) = sprite
        if abs(ratio - 1.0) < 0.02:
            return sprite
        w, h = surf.get_size()
        if settled:
            q = max(0.3, round(ratio * 20) / 20)
            key = (id(surf), q)
            if key not in self._scaled:
                out = TOP.shrink(surf, q)
                self._scaled[key] = (surf, (out, (ax * out.get_width() / w, ay * out.get_height() / h)))
            out, (bx, by) = self._scaled[key][1]
            return out, (int(round(bx)), int(round(by)))
        nw, nh = max(1, int(round(w * ratio))), max(1, int(round(h * ratio)))
        out = pygame.transform.smoothscale(surf, (nw, nh))
        return out, (int(round(ax * nw / w)), int(round(ay * nh / h)))

    def outline_of(self, surf: pygame.Surface, color=(255, 255, 255), thickness: int = 1) -> pygame.Surface:
        """Ring-only silhouette of any sprite surface, padded by 2 px on every side."""
        pad = new_surface(surf.get_width() + 4, surf.get_height() + 4)
        pad.blit(surf, (2, 2))
        return silhouette(pad, color, thickness)

    # ---------------------------------------------------------------- markers
    def marker(self, side: Side, selected: bool = False) -> pygame.Surface:
        """Colour-blind-safe ground marker: humans get a ring (circle), the AI gets a diamond."""
        key = (side, selected)
        if key not in self._markers:
            P = team_palette(side)
            s = new_surface(40, 22)
            cx, cy = 20, 11
            col = P["main"] if not selected else (255, 255, 255)
            if side == Side.HUMAN:
                pygame.draw.ellipse(s, (*P["main"], 70), (cx - 14, cy - 7, 28, 14))
                pygame.draw.ellipse(s, (*P["deep"], 255), (cx - 15, cy - 8, 30, 16), 3)
                pygame.draw.ellipse(s, (*col, 255), (cx - 14, cy - 7, 28, 14), 2)
                pygame.draw.ellipse(s, (*P["light"], 255), (cx - 14, cy - 7, 28, 14), 1)
            else:
                pts = [(cx, cy - 8), (cx + 16, cy), (cx, cy + 8), (cx - 16, cy)]
                inner = [(cx, cy - 6), (cx + 12, cy), (cx, cy + 6), (cx - 12, cy)]
                pygame.draw.polygon(s, (*P["main"], 70), pts)
                pygame.draw.polygon(s, (*P["deep"], 255), pts, 3)
                pygame.draw.polygon(s, (*col, 255), inner, 2)
            self._markers[key] = s
        return self._markers[key]

    def facing_arrow(self, facing: Direction, side: Side) -> pygame.Surface:
        key = (int(facing), side)
        if key not in self._arrows:
            P = team_palette(side)
            fe, fs = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}[int(facing)]
            pe, ps = -fs, fe
            s = new_surface(K.TW, K.TH)
            cx, cy = K.TW / 2, K.TH / 2

            def pt(u, v):
                return iso(cx, cy, u * fe + v * pe, u * fs + v * ps)

            head = [pt(0.52, 0), pt(0.33, 0.19), pt(0.33, -0.19)]
            shaft = [pt(0.33, 0.045), pt(0.22, 0.045), pt(0.22, -0.045), pt(0.33, -0.045)]
            pygame.draw.polygon(s, (*P["deep"], 255), head)
            pygame.draw.polygon(s, (255, 255, 255, 255), [pt(0.46, 0), pt(0.36, 0.11), pt(0.36, -0.11)])
            pygame.draw.polygon(s, (*P["light"], 255), shaft)
            self._arrows[key] = s
        return self._arrows[key]
