"""Sprites for the front view (the steep camera). Same units and props as the diamond view, drawn from higher up.

Soldiers, pines and bushes are standing figures, so they are the diamond-view art scaled to the smaller tiles
(`shrink` keeps the pixels crisp). The Tank, Bomber, HQ and mountains are solid shapes, so they are drawn again
here from above. Every function returns (surface, anchor) like art_units.py and art_terrain.py.
"""
from __future__ import annotations

import math

import pygame

from . import constants as K
from . import art_terrain as T
from .art_units import GLASS, METAL, METAL_HI
from .gfx import new_surface, outline, shade, speckle

try:                                           # numpy is only needed for the nicer scaling and for the view change
    import numpy as np
except ImportError:                            # pragma: no cover
    np = None

PITCH = math.radians(K.TOP_PITCH_DEG)
SY = math.sin(PITCH)                           # how much a tile's depth is squashed on screen
CY = math.cos(PITCH)
TILE = K.TOP_TILE
HELI_LIFT_TOP = 8


# ---------------------------------------------------------------- scaling that keeps pixel art crisp
def shrink(surf: pygame.Surface, k: float) -> pygame.Surface:
    """Scale a sprite by k with smoothing, then snap every colour to the sprite's own small palette and make alpha binary."""
    w, h = surf.get_size()
    nw, nh = max(1, int(round(w * k))), max(1, int(round(h * k)))
    out = pygame.transform.smoothscale(surf, (nw, nh))
    if np is None:
        return out
    pal_src = pygame.surfarray.array3d(surf).reshape(-1, 3)
    alpha_src = pygame.surfarray.array_alpha(surf).reshape(-1)
    px = (pal_src[alpha_src > 200] // 8) * 8 + 4
    if len(px) == 0:
        return out
    keys, counts = np.unique(px, axis=0, return_counts=True)
    palette = keys[np.argsort(-counts)[:40]].astype(np.int32)
    rgb = pygame.surfarray.array3d(out).astype(np.int32)
    al = pygame.surfarray.array_alpha(out)
    flat = rgb.reshape(-1, 3)
    d = ((flat[:, None, :] - palette[None, :, :]) ** 2).sum(axis=2)
    snapped = palette[d.argmin(axis=1)].reshape(rgb.shape).astype(np.uint8)
    res = new_surface(nw, nh)
    pygame.surfarray.blit_array(res, snapped)
    a = pygame.surfarray.pixels_alpha(res)
    a[:] = np.where(al > 120, 255, 0)
    del a
    return res


# ---------------------------------------------------------------- tiny box helper for a high camera
def _box(s, cx, cy, ex, ey, h, top, front, z0=0.0, oe=0.0, os_=0.0, edge=None):
    """A cuboid seen from the front-top. ex, ey = half sizes in tiles (East, South); h and z0 in pixels."""
    x = cx + oe * TILE
    y = cy + os_ * TILE * SY - z0
    w, d = 2 * ex * TILE, 2 * ey * TILE * SY
    top_r = pygame.Rect(int(round(x - w / 2)), int(round(y - h - d / 2)), int(round(w)), max(2, int(round(d))))
    front_r = pygame.Rect(top_r.x, top_r.bottom, top_r.w, max(1, int(round(h))))
    pygame.draw.rect(s, front, front_r)
    pygame.draw.rect(s, top, top_r)
    pygame.draw.line(s, shade(top, 1.22), top_r.topleft, (top_r.right - 1, top_r.y))
    if edge is not None:
        pygame.draw.rect(s, edge, top_r, 1)
        pygame.draw.line(s, edge, front_r.bottomleft, front_r.bottomright)
    return top_r


# ---------------------------------------------------------------- tank
_DIR = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}


def make_tank_top(P, facing: int):
    W, H = 46, 46
    cx, cy = W // 2, 32
    s = new_surface(W, H)
    fe, fs = _DIR[facing]
    along_e = fe != 0
    track_t, track_f = (62, 66, 80), (34, 36, 48)
    body = (P["light"], P["main"])
    L, Wd = 0.34, 0.20                                          # half length / half width of the hull
    ea, es = (L, Wd) if along_e else (Wd, L)
    for sign in (-1, 1):                                        # treads along both sides
        if along_e:
            _box(s, cx, cy, L + 0.02, 0.075, 3, track_t, track_f, oe=0, os_=sign * 0.215, edge=(18, 20, 28))
        else:
            _box(s, cx, cy, 0.075, L + 0.02, 3, track_t, track_f, oe=sign * 0.215, os_=0, edge=(18, 20, 28))
    _box(s, cx, cy, ea - 0.01 if not along_e else ea, es if not along_e else es - 0.02, 4, *body, z0=1, edge=P["deep"])
    back = (-fe * 0.2, -fs * 0.2)                               # engine deck behind the turret
    _box(s, cx, cy, 0.06 if along_e else 0.1, 0.1 if along_e else 0.06, 1, shade(P["main"], 0.82), P["dark"], z0=5, oe=back[0], os_=back[1])
    tz = 5

    def barrel():
        x0, y0 = cx + fe * 0.03 * TILE, cy + fs * 0.03 * TILE * SY - tz - 4
        x1, y1 = cx + fe * 0.60 * TILE, cy + fs * 0.60 * TILE * SY - tz - 4
        pygame.draw.line(s, (24, 26, 36), (x0, y0), (x1, y1), 4 if along_e else 3)
        pygame.draw.line(s, METAL, (x0, y0), (x1, y1), 2 if along_e else 1)
        pygame.draw.circle(s, (24, 26, 36), (int(x1), int(y1)), 2)

    if facing == 0:
        barrel()
    _box(s, cx, cy, 0.14, 0.14, 4, P["light"], P["main"], z0=tz, edge=P["deep"])
    pygame.draw.circle(s, shade(P["dark"], 0.8), (cx, int(cy - tz - 4 - 2)), 2)
    pygame.draw.circle(s, P["light"], (cx, int(cy - tz - 4 - 3)), 1)
    if facing != 0:
        barrel()
    speckle(s, 0.03, 21 + facing)
    return outline(s, P["deep"]), (cx, cy)


# ---------------------------------------------------------------- bomber (helicopter), facing East; the AI one is mirrored
BW, BH = 54, 44
BOMBER_ANCHOR = (27, 34)
ROTOR_HUB = (0, -(HELI_LIFT_TOP + 5))                  # offsets from the anchor
TAIL_HUB = (-17, -(HELI_LIFT_TOP + 2))


def make_bomber_top(P, ai: bool):
    s = new_surface(BW, BH)
    ax, ay = BOMBER_ANCHOR
    cx, cy = ax, ay - HELI_LIFT_TOP
    pygame.draw.polygon(s, P["dark"], [(cx - 6, cy - 2), (cx - 19, cy - 1), (cx - 19, cy + 1), (cx - 6, cy + 3)])        # tail boom
    pygame.draw.polygon(s, P["main"], [(cx - 18, cy - 5), (cx - 20, cy - 5), (cx - 17, cy + 2), (cx - 15, cy + 2)])      # fin
    pygame.draw.line(s, (30, 32, 44), (cx - 9, cy + 8), (cx + 10, cy + 8), 2)                                          # skids
    pygame.draw.line(s, (30, 32, 44), (cx - 4, cy + 4), (cx - 5, cy + 8), 1)
    pygame.draw.line(s, (30, 32, 44), (cx + 5, cy + 4), (cx + 6, cy + 8), 1)
    pygame.draw.rect(s, (40, 44, 58), (cx - 3, cy + 4, 10, 2))                                                        # missile pod
    pygame.draw.rect(s, (255, 110, 90), (cx + 7, cy + 4, 2, 2))
    pygame.draw.ellipse(s, P["main"], (cx - 9, cy - 6, 21, 13))                                                       # fuselage
    pygame.draw.ellipse(s, P["dark"], (cx - 9, cy, 21, 7))
    pygame.draw.ellipse(s, P["main"], (cx - 9, cy - 6, 21, 9))
    pygame.draw.ellipse(s, P["light"], (cx - 5, cy - 5, 10, 3))
    pygame.draw.ellipse(s, GLASS, (cx + 3, cy - 5, 9, 8))                                                             # canopy
    pygame.draw.ellipse(s, (236, 252, 255), (cx + 5, cy - 4, 4, 2))
    pygame.draw.rect(s, (40, 44, 58), (cx - 1, cy - 8, 3, 3))                                                         # mast
    speckle(s, 0.03, 31)
    s = outline(s, P["deep"])
    if ai:
        s = pygame.transform.flip(s, True, False)
        return s, (BW - 1 - ax, ay)
    return s, (ax, ay)


def draw_rotor_top(dst, mx: float, my: float, t: float, k: float = 1.0):
    """Main rotor from above: a pale disc (nearly round) and two spinning blades."""
    rw, rh = 19 * k, 19 * k * SY
    disc = new_surface(int(2 * rw) + 4, int(2 * rh) + 4)
    pygame.draw.ellipse(disc, (220, 230, 255, 30), (1, 1, int(2 * rw) + 1, int(2 * rh) + 1))
    dst.blit(disc, (mx - rw - 1, my - rh - 1))
    ph = t * 22.0
    for i in range(2):
        a = ph + i * math.pi / 2
        dx, dy = rw * math.cos(a), rh * math.sin(a)
        pygame.draw.line(dst, (34, 38, 52), (mx - dx, my - dy), (mx + dx, my + dy), 2)
        pygame.draw.line(dst, (172, 180, 200), (mx - dx, my - dy - 1), (mx + dx, my + dy - 1), 1)
    pygame.draw.circle(dst, (60, 66, 84), (int(mx), int(my)), 2)


# ---------------------------------------------------------------- headquarters
HW, HH = 42, 46
HQ_ANCHOR = (21, 33)
HQ_POLE = (-0.40, -0.40)                                 # tile offset of the flag pole (East, South)
POLE_H = 22


def make_hq_top(team: dict):
    s = new_surface(HW, HH)
    ax, ay = HQ_ANCHOR
    _box(s, ax, ay, 0.47, 0.47, 3, (156, 158, 170), (96, 98, 112), edge=(40, 42, 58))
    top_y = ay - 3
    pad = pygame.Rect(0, 0, int(0.76 * TILE), int(0.76 * TILE * SY))
    pad.center = (ax, int(top_y))
    pygame.draw.rect(s, team["dark"], pad)
    inner = pad.inflate(-4, -4)
    pygame.draw.rect(s, team["main"], inner)
    pygame.draw.rect(s, team["light"], pad, 1)
    cxp, cyp = pad.center
    pygame.draw.polygon(s, team["light"], [(cxp, cyp - 3), (cxp + 5, cyp), (cxp, cyp + 3), (cxp - 5, cyp)], 1)
    bag_t, bag_f = (206, 182, 126), (150, 126, 86)
    for i in range(4):                                    # sandbags along the back (north) and left (west) edges
        t = -0.28 + i * 0.185
        _box(s, ax, ay, 0.085, 0.045, 3, bag_t, bag_f, z0=3, oe=t, os_=-0.40, edge=(70, 56, 36))
        _box(s, ax, ay, 0.045, 0.085, 3, bag_t, bag_f, z0=3, oe=-0.40, os_=t, edge=(70, 56, 36))
    speckle(s, 0.04, 5)
    return s, (ax, ay)


def flag_attach_top(cx: float, cy: float, k: float = 1.0):
    return cx + HQ_POLE[0] * TILE * k, cy + HQ_POLE[1] * TILE * SY * k - 3 * k - POLE_H * k


def draw_hq_flag_top(dst: pygame.Surface, cx: float, cy: float, team: dict, t: float, k: float = 1.0):
    bx, by = cx + HQ_POLE[0] * TILE * k, cy + HQ_POLE[1] * TILE * SY * k - 3 * k
    tx, ty = flag_attach_top(cx, cy, k)
    pygame.draw.line(dst, (40, 42, 58), (bx - 1, by), (tx - 1, ty), 1)
    pygame.draw.line(dst, (206, 210, 224), (bx, by), (tx, ty), 1)
    pygame.draw.rect(dst, (255, 214, 90), (tx - 1, ty - 2, 3, 3))
    fw, fh = max(6, round(12 * k)), max(4, round(7 * k))
    for i in range(fw):
        wave = math.sin(t * 5.0 + i * 0.55) * (0.5 + i * 0.09)
        x = int(tx + 1 + i)
        y0 = int(ty + 1 + wave)
        col = shade(team["main"], 1.0 - 0.1 * (math.sin(t * 5.0 + i * 0.55) + 1) / 2)
        pygame.draw.line(dst, team["deep"], (x, y0 - 1), (x, y0 - 1), 1)
        pygame.draw.line(dst, col, (x, y0), (x, y0 + fh - 1), 1)
        pygame.draw.line(dst, team["light"], (x, y0), (x, y0), 1)
        pygame.draw.line(dst, team["deep"], (x, y0 + fh), (x, y0 + fh), 1)
        if fw // 2 - 1 <= i <= fw // 2 + 1:
            pygame.draw.line(dst, (245, 248, 255), (x, y0 + fh // 2 - 1), (x, y0 + fh // 2 + 1), 1)
    pygame.draw.line(dst, team["deep"], (int(tx + 1), int(ty + 1)), (int(tx + 1), int(ty + fh)), 1)


# ---------------------------------------------------------------- mountains
def make_rock_top(seed: int):
    """The same faceted, snow-capped mountain, with a rounder footprint and lower peaks for the higher camera."""
    return T.make_rock(seed, sx=0.62, sy=1.12, sh=0.72, size=(42, 48), centre=(21, 36))
