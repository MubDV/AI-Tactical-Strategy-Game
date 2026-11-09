"""Procedurally drawn terrain art: grass, forest floor, rock floor, board slab, mountains, pines, HQ.

Everything is generated at start-up from code, so the game runs with no image files. When real
art arrives (milestone M9) only this module is replaced; the renderer uses the same (surface, anchor)
pairs either way.
"""
from __future__ import annotations

import math
import random

import pygame

from . import constants as K
from .gfx import (circle_pts, hash01, iso, iso_box, lerp_pt, mix, new_surface, outline, shade,
                  speckle, tile_distance)

TW, TH = K.TW, K.TH

GROUND_COLORS = {
    "grass": (K.GRASS_A, K.GRASS_B),
    "forest": ((72, 132, 72), (66, 124, 66)),
    "rock": ((118, 114, 110), (108, 104, 102)),
}


# ---------------------------------------------------------------- ground tiles
def make_ground_tile(kind: str, parity: int, variant: int, tint=None, tint_amount: float = 0.0):
    """One 48x24 diamond tile. Pixel-exact so neighbours tile with no gaps."""
    base = GROUND_COLORS[kind][parity]
    if tint is not None:
        base = mix(base, tint, tint_amount)
    s = new_surface(TW, TH)
    seed = variant * 7 + parity + (0 if kind == "grass" else 31)
    rng = random.Random(seed * 13 + 5)
    for y in range(TH):
        for x in range(TW):
            d, a, b = tile_distance(x, y)
            if d > 1:
                continue
            n = hash01(x, y, seed)
            f = 1.0 + (n - 0.5) * 0.10 - (b / 12.0) * 0.035
            c = shade(base, f)
            if d > 0.925:                       # bevelled rim: light on the back edges, dark on the front
                if b < 0:
                    c = shade(base, 1.20 if a < 0 else 1.10)
                else:
                    c = shade(base, 0.74 if a < 0 else 0.64)
            s.set_at((x, y), c)

    def inside(px, py):
        return 0 <= px < TW and 0 <= py < TH and tile_distance(px, py)[0] < 0.78

    if kind == "grass":
        for _ in range(4 + variant % 3):        # grass tufts
            x, y = rng.randrange(8, 40), rng.randrange(6, 19)
            if inside(x, y) and inside(x, y - 2):
                s.set_at((x, y - 2), shade(base, 1.28))
                s.set_at((x, y - 1), shade(base, 1.14))
                s.set_at((x, y), shade(base, 0.78))
                if inside(x + 2, y - 1):
                    s.set_at((x + 2, y - 1), shade(base, 1.18))
                    s.set_at((x + 2, y), shade(base, 0.80))
        if variant in (2, 3):                   # flowers
            for _ in range(2):
                x, y = rng.randrange(10, 38), rng.randrange(7, 18)
                if inside(x, y):
                    col = rng.choice([(250, 246, 220), (255, 224, 120), (255, 170, 190)])
                    s.set_at((x, y), col)
                    s.set_at((x, y + 1), shade(base, 0.75))
    elif kind == "forest":
        for _ in range(7):                      # fallen needles and moss
            x, y = rng.randrange(8, 40), rng.randrange(5, 19)
            if inside(x, y) and inside(x + 1, y):
                col = rng.choice([shade(base, 0.72), (122, 96, 60), shade(base, 1.2)])
                s.set_at((x, y), col)
                s.set_at((x + 1, y), col)
    else:                                       # rock floor: cracks and chips
        for _ in range(6):
            x, y = rng.randrange(8, 40), rng.randrange(5, 19)
            if inside(x, y) and inside(x + 2, y + 1):
                s.set_at((x, y), shade(base, 0.62))
                s.set_at((x + 1, y), shade(base, 0.62))
                s.set_at((x + 2, y + 1), shade(base, 0.62))
    return s


# ---------------------------------------------------------------- flat ground tiles (front view)
FLAT = 32                                              # pixels per tile in the flat ground texture


def make_flat_tile(kind: str, parity: int, variant: int, tint=None, tint_amount: float = 0.0, n: int = FLAT):
    """The same tile as make_ground_tile, seen from straight above: a square with a bevelled rim, grain, tufts and so on."""
    base = GROUND_COLORS[kind][parity]
    if tint is not None:
        base = mix(base, tint, tint_amount)
    s = new_surface(n, n)
    seed = variant * 7 + parity + (0 if kind == "grass" else 31)
    rng = random.Random(seed * 13 + 5)
    for y in range(n):
        for x in range(n):
            nz = hash01(x, y, seed)
            f = 1.0 + (nz - 0.5) * 0.10 - ((y - n / 2) / n) * 0.07
            c = shade(base, f)
            if x == 0 or y == 0:                       # bevelled rim: light on the back edges, dark on the front
                c = shade(base, 1.16)
            elif x == n - 1 or y == n - 1:
                c = shade(base, 0.70)
            s.set_at((x, y), c)

    def inside(px, py):
        return 3 <= px < n - 3 and 3 <= py < n - 3

    if kind == "grass":
        for _ in range(6 + variant % 3):
            x, y = rng.randrange(4, n - 4), rng.randrange(5, n - 3)
            if inside(x, y) and inside(x, y - 2):
                s.set_at((x, y - 2), shade(base, 1.28))
                s.set_at((x, y - 1), shade(base, 1.14))
                s.set_at((x, y), shade(base, 0.78))
                if inside(x + 2, y - 1):
                    s.set_at((x + 2, y - 1), shade(base, 1.18))
                    s.set_at((x + 2, y), shade(base, 0.80))
        if variant in (2, 3):
            for _ in range(2):
                x, y = rng.randrange(5, n - 5), rng.randrange(5, n - 5)
                col = rng.choice([(250, 246, 220), (255, 224, 120), (255, 170, 190)])
                s.set_at((x, y), col)
                s.set_at((x, y + 1), shade(base, 0.75))
    elif kind == "forest":
        for _ in range(10):
            x, y = rng.randrange(4, n - 5), rng.randrange(4, n - 4)
            col = rng.choice([shade(base, 0.72), (122, 96, 60), shade(base, 1.2)])
            s.set_at((x, y), col)
            s.set_at((x + 1, y), col)
    else:
        for _ in range(8):
            x, y = rng.randrange(5, n - 7), rng.randrange(5, n - 6)
            s.set_at((x, y), shade(base, 0.62))
            s.set_at((x + 1, y), shade(base, 0.62))
            s.set_at((x + 2, y + 1), shade(base, 0.62))
    return s


# ---------------------------------------------------------------- slab (earth under the board)
def make_slab_face(side: str, variant: int):
    """Side face under a board-edge tile. side 'left' = lower-left edge, 'right' = lower-right edge.

    Returns a (24, TH + SLAB_DEPTH) surface whose top-left is at the tile's top-left (left face)
    or at tile x offset 24 (right face).
    """
    D = K.SLAB_DEPTH
    w, h = TW // 2, TH + D
    s = new_surface(w, h)
    base = K.SOIL_LEFT if side == "left" else K.SOIL_RIGHT
    lip = shade(K.GRASS_B, 0.78 if side == "left" else 0.62)
    x0 = 0 if side == "left" else TW // 2
    lasts = []
    for x in range(w):
        last = -1
        for y in range(TH):
            if tile_distance(x + x0, y)[0] <= 1:
                last = y
        lasts.append(last)
    for x in range(w):                          # the extreme corner column has no tile pixels: reuse its neighbour
        if lasts[x] < 0:
            lasts[x] = lasts[x + 1] if x + 1 < w and lasts[x + 1] >= 0 else lasts[x - 1]
    for x in range(w):
        gx = x + x0
        last = lasts[x]
        for k in range(1, D + 1):
            y = last + k
            if y >= h:
                break
            n = hash01(gx, y, variant + 3)
            c = shade(base, 1.0 + (n - 0.5) * 0.14)
            if (k + variant) % 4 == 0:           # strata bands
                c = shade(c, 0.88)
            if k <= 2 + (1 if hash01(gx, 99, variant) > 0.62 else 0):   # grass overhang, ragged edge
                c = shade(lip, 1.0 + (n - 0.5) * 0.16)
            if k == D:
                c = shade(c, 0.78)
            s.set_at((x, y), c)
        if hash01(gx, 7, variant) > 0.93:        # pebbles
            yy = last + 5 + int(hash01(gx, 8, variant) * 4)
            if yy < h:
                s.set_at((x, yy), shade(base, 1.35))
    return s


def make_iso_grid() -> pygame.Surface:
    """The faint diamond floor grid behind the board (diamond view)."""
    W, H = K.LOGICAL_W, K.LOGICAL_H
    grid = new_surface(W, H)
    step = TW // 2
    col = (110, 140, 220, 16)
    for i in range(-H * 2, W + H * 2, step):
        pygame.draw.line(grid, col, (i, 0), (i + H * 2, H), 1)       # slope +1/2
        pygame.draw.line(grid, col, (i, H), (i + H * 2, 0), 1)       # slope -1/2
    return grid


def make_square_grid() -> pygame.Surface:
    """The faint square floor grid behind the board (front view)."""
    W, H = K.LOGICAL_W, K.LOGICAL_H
    grid = new_surface(W, H)
    step = int(round(K.TOP_TILE))
    col = (110, 140, 220, 16)
    for x in range(int(K.LOGICAL_W / 2) % step, W, step):
        pygame.draw.line(grid, col, (x, 0), (x, H), 1)
    for y in range(0, H, step):
        pygame.draw.line(grid, col, (0, y), (W, y), 1)
    return grid


def make_background(grid: bool = True) -> pygame.Surface:
    """Night-blue backdrop: vertical gradient, faint isometric floor grid (optional), glow behind the board."""
    W, H = K.LOGICAL_W, K.LOGICAL_H
    bg = pygame.Surface((W, H))
    for y in range(H):
        t = y / (H - 1)
        bg.fill(mix(K.BG_TOP, K.BG_BOTTOM, t ** 0.9), (0, y, W, 1))
    if grid:
        bg.blit(make_iso_grid(), (0, 0))
    glow = new_surface(W, H)
    for i in range(14, 0, -1):
        rx, ry = 150 + i * 13, 70 + i * 7
        pygame.draw.ellipse(glow, (70, 110, 200, 3), (K.OX - rx, 150 - ry, rx * 2, ry * 2))
    bg.blit(glow, (0, 0))
    for i in range(70):                                              # stars
        x, y = int(hash01(i, 1, 9) * W), int(hash01(i, 2, 9) * 36)
        b = 120 + int(hash01(i, 3, 9) * 110)
        bg.set_at((x, y), (b, b, min(255, b + 30)))
    return bg


def board_polygon(margin=0):
    """Corner points of the whole 8x8 board diamond."""
    n = K.BOARD_N
    top = iso(K.OX, K.OY, -0.5, -0.5)
    right = iso(K.OX, K.OY, n - 0.5, -0.5)
    bottom = iso(K.OX, K.OY, n - 0.5, n - 0.5)
    left = iso(K.OX, K.OY, -0.5, n - 0.5)
    return [top, right, bottom, left]


def draw_board_shadow(bg: pygame.Surface):
    sh = new_surface(*bg.get_size())
    top, right, bottom, left = board_polygon()
    for i in range(7, 0, -1):
        g = i * 3
        pts = [(top[0], top[1] + K.SLAB_DEPTH + 3 - g // 2), (right[0] + g, right[1] + K.SLAB_DEPTH + 3),
               (bottom[0], bottom[1] + K.SLAB_DEPTH + 3 + g), (left[0] - g, left[1] + K.SLAB_DEPTH + 3)]
        pygame.draw.polygon(sh, (0, 0, 8, 22), pts)
    bg.blit(sh, (0, 0))


# ---------------------------------------------------------------- props
def make_rock(seed: int, sx: float = 1.0, sy: float = 1.0, sh: float = 1.0, size=(56, 62), centre=(28, 48)):
    """A three-tier faceted mountain for a wall cell. Returns (surface, anchor) with the anchor on the tile centre."""
    rng = random.Random(seed)
    W, H = size
    cx, cy = centre
    s = new_surface(W, H)
    shadow = new_surface(W, H)
    pygame.draw.ellipse(shadow, (0, 0, 10, 70), (cx - 22 * sx, cy - 9 * sy, 44 * sx, 18 * sy))
    s.blit(shadow, (0, 0))
    base = (122, 122, 136)
    snow = (232, 240, 252)
    light = (-0.8, 0.6)
    tiers = [(0.92, 11 * sh), (0.66, 9 * sh), (0.40, 7 * sh)]
    z = 0.0
    for ti, (rf, h) in enumerate(tiers):
        n = 9
        ang = [2 * math.pi * i / n + rng.uniform(-0.16, 0.16) for i in range(n)]
        rad = [rf * rng.uniform(0.88, 1.08) for _ in range(n)]
        bp = [(cx + r * 22 * sx * math.cos(a), cy - z + r * 11 * sy * math.sin(a)) for a, r in zip(ang, rad)]
        lift = [h + rng.uniform(-2.0, 2.0) * sh for _ in range(n)]
        tp = [(x, y - l) for (x, y), l in zip(bp, lift)]
        last = ti == len(tiers) - 1
        for i in range(n):
            j = (i + 1) % n
            mid = (ang[i] + ang[j]) / 2
            if math.sin(mid) < -0.2:
                continue
            nl = -light[0] * -math.cos(mid) * 0 + (math.cos(mid) * light[0] + math.sin(mid) * light[1])
            f = max(0.5, min(1.22, 0.80 + 0.38 * nl))
            col = shade(base, f * (1.0 + 0.05 * ti))
            quad = [tp[i], tp[j], bp[j], bp[i]]
            pygame.draw.polygon(s, col, quad)
            if hash01(i, ti, seed) > 0.4:                # vertical crack
                a = lerp_pt(tp[i], tp[j], 0.5)
                b = lerp_pt(bp[i], bp[j], 0.35)
                pygame.draw.line(s, shade(col, 0.72), a, b, 1)
            if last:                                      # snow cap dripping down the faces
                drip = [tp[i], tp[j], lerp_pt(tp[j], bp[j], 0.42), lerp_pt(tp[j], bp[j], 0.22),
                        lerp_pt(lerp_pt(tp[i], tp[j], 0.5), lerp_pt(bp[i], bp[j], 0.5), 0.5),
                        lerp_pt(tp[i], bp[i], 0.3), lerp_pt(tp[i], bp[i], 0.18)]
                pygame.draw.polygon(s, shade(snow, 0.74 + 0.26 * min(1.0, f)), drip)
        centre = (sum(p[0] for p in tp) / n, sum(p[1] for p in tp) / n)
        for i in range(n):                                # faceted top: a fan of shaded triangles
            j = (i + 1) % n
            mid = (ang[i] + ang[j]) / 2
            nl = math.cos(mid) * light[0] + math.sin(mid) * light[1]
            f = 1.14 + 0.10 * nl
            col = shade(snow if last else base, f if last else f * 1.05)
            pygame.draw.polygon(s, col, [centre, tp[i], tp[j]])
        z += h - 1
    speckle(s, 0.05, seed)
    return outline(s, (34, 36, 52)), (cx, cy)


def make_pine(variant: int):
    """A pine tree, 18x30, anchor on the trunk foot."""
    W, H = 20, 32
    s = new_surface(W, H)
    cx = W // 2
    foot = 28
    leaf_l = [(62, 148, 80), (66, 152, 72), (56, 140, 84)][variant % 3]
    leaf_r = shade(leaf_l, 0.66)
    pygame.draw.rect(s, (96, 66, 40), (cx - 1, foot - 5, 3, 6))
    pygame.draw.rect(s, (66, 44, 28), (cx + 1, foot - 5, 1, 6))
    tiers = [(foot - 5, foot - 17, 8), (foot - 12, foot - 23, 6.5), (foot - 18, foot - 28, 5)]
    for base_y, apex_y, hw in tiers:
        pygame.draw.polygon(s, leaf_l, [(cx, apex_y), (cx - hw, base_y), (cx, base_y)])
        pygame.draw.polygon(s, leaf_r, [(cx, apex_y), (cx, base_y), (cx + hw, base_y)])
        pygame.draw.line(s, shade(leaf_r, 0.7), (cx - hw + 1, base_y), (cx + hw - 1, base_y), 1)
        pygame.draw.line(s, shade(leaf_l, 1.25), (cx, apex_y + 1), (cx - hw * 0.55, base_y - 2), 1)
    speckle(s, 0.06, variant + 40)
    return outline(s, (14, 44, 34)), (cx, foot)


def make_bush():
    """Small round bush used in front of units standing on cover. 18x12, anchor on the bottom centre."""
    s = new_surface(20, 14)
    for (x, y, r, c) in [(6, 8, 5, (54, 128, 66)), (13, 8, 5, (50, 120, 62)), (10, 5, 5, (66, 148, 76))]:
        pygame.draw.circle(s, c, (x, y), r)
    pygame.draw.circle(s, (100, 180, 100), (8, 3), 1)
    pygame.draw.circle(s, (100, 180, 100), (12, 4), 1)
    for (x, y) in [(5, 9), (14, 7), (10, 9)]:
        s.set_at((x, y), (230, 90, 100))                 # berries
    speckle(s, 0.06, 77)
    return outline(s, (14, 44, 34)), (10, 12)


def make_hq(team: dict):
    """Static part of a headquarters: stone plinth, team-coloured pad, sandbags. Anchor on the tile centre."""
    W, H = 56, 40
    cx, cy = 28, 24
    s = new_surface(W, H)
    stone_t, stone_l, stone_r = (156, 158, 170), (112, 114, 128), (80, 82, 96)
    iso_box(s, cx, cy, 0.47, 0.47, 3, stone_t, stone_l, stone_r, edge=(40, 42, 58))
    pad = [iso(cx, cy, -0.38, -0.38, 3), iso(cx, cy, 0.38, -0.38, 3), iso(cx, cy, 0.38, 0.38, 3), iso(cx, cy, -0.38, 0.38, 3)]
    pygame.draw.polygon(s, team["dark"], pad)
    inner = [iso(cx, cy, -0.30, -0.30, 3), iso(cx, cy, 0.30, -0.30, 3), iso(cx, cy, 0.30, 0.30, 3), iso(cx, cy, -0.30, 0.30, 3)]
    pygame.draw.polygon(s, team["main"], inner)
    pygame.draw.polygon(s, team["light"], pad, 1)
    centre = iso(cx, cy, 0, 0, 3)
    pygame.draw.polygon(s, shade(team["light"], 1.0), [(centre[0], centre[1] - 3), (centre[0] + 6, centre[1]),
                                                       (centre[0], centre[1] + 3), (centre[0] - 6, centre[1])], 1)
    bag_t, bag_l, bag_r = (206, 182, 126), (160, 136, 92), (120, 98, 66)
    for i in range(4):                                    # sandbags along the two back edges
        t = -0.30 + i * 0.2
        iso_box(s, cx, cy, 0.05, 0.095, 4, bag_t, bag_l, bag_r, z0=3, oe=-0.43, os_=t, edge=(70, 56, 36))
        iso_box(s, cx, cy, 0.095, 0.05, 4, bag_t, bag_l, bag_r, z0=3, oe=t, os_=-0.43, edge=(70, 56, 36))
    speckle(s, 0.04, 5)
    return s, (cx, cy)


def flag_pole_top(tile_cx: float, tile_cy: float):
    """Screen point where the HQ flag is attached (top of the pole)."""
    return iso(tile_cx, tile_cy, -0.40, -0.40, 34)


def draw_hq_flag(dst: pygame.Surface, tile_cx: float, tile_cy: float, team: dict, t: float):
    """Pole and an animated, waving flag. Drawn every frame."""
    bx, by = iso(tile_cx, tile_cy, -0.40, -0.40, 3)
    tx, ty = flag_pole_top(tile_cx, tile_cy)
    pygame.draw.line(dst, (40, 42, 58), (bx - 1, by), (tx - 1, ty), 1)
    pygame.draw.line(dst, (206, 210, 224), (bx, by), (tx, ty), 1)
    pygame.draw.rect(dst, (255, 214, 90), (tx - 1, ty - 2, 3, 3))
    fw, fh = 15, 9
    for i in range(fw):
        wave = math.sin(t * 5.0 + i * 0.55) * (0.6 + i * 0.10)
        x = int(tx + 1 + i)
        y0 = int(ty + 1 + wave)
        col = shade(team["main"], 1.0 - 0.1 * (math.sin(t * 5.0 + i * 0.55) + 1) / 2)
        pygame.draw.line(dst, team["deep"], (x, y0 - 1), (x, y0 - 1), 1)
        pygame.draw.line(dst, col, (x, y0), (x, y0 + fh - 1), 1)
        pygame.draw.line(dst, team["light"], (x, y0), (x, y0), 1)
        pygame.draw.line(dst, team["deep"], (x, y0 + fh), (x, y0 + fh), 1)
        if i in (6, 7, 8):                                 # little white emblem
            pygame.draw.line(dst, (245, 248, 255), (x, y0 + 3), (x, y0 + 5), 1)
    pygame.draw.line(dst, team["deep"], (int(tx + 1), int(ty + 1)), (int(tx + 1), int(ty + fh)), 1)
