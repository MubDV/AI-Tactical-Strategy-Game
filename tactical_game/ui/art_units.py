"""Procedurally drawn unit sprites (5 types x 2 teams; the Tank has 4 facings).

Every function returns (surface, anchor) where `anchor` is the point on the sprite that sits at the
centre of the tile (the unit's feet). Replace with image loading at milestone M9 and keep this contract.
"""
from __future__ import annotations

import math

import pygame

from . import constants as K
from .gfx import iso, iso_box, new_surface, outline, shade, speckle

SKIN = (238, 192, 152)
SKIN_D = (204, 150, 112)
TROUSER = (46, 50, 68)
BOOT = (28, 30, 42)
METAL = (66, 72, 90)
METAL_HI = (160, 168, 188)
TAN = (196, 164, 112)
ORANGE = (250, 146, 34)
YELLOW = (255, 216, 70)
GLASS = (150, 222, 246)

SOLDIER_W, SOLDIER_H, FOOT_X, FOOT_Y = 40, 50, 20, 44
TANK_W, TANK_H, TANK_CX, TANK_CY = 76, 64, 38, 46
HELI_W, HELI_H, HELI_CX, HELI_CY = 68, 56, 34, 48
HELI_LIFT = 15


def _rect(s, col, x, y, w, h):
    pygame.draw.rect(s, col, (int(x), int(y), int(w), int(h)))


def _soldier_base(s, P, tw=10, skin=SKIN):
    fx, fy = FOOT_X, FOOT_Y
    _rect(s, TROUSER, fx - 4, fy - 9, 3, 8)
    _rect(s, TROUSER, fx + 1, fy - 9, 3, 8)
    _rect(s, shade(TROUSER, 1.35), fx - 4, fy - 9, 1, 7)
    _rect(s, BOOT, fx - 5, fy - 2, 4, 3)
    _rect(s, BOOT, fx + 1, fy - 2, 4, 3)
    x0 = fx - tw // 2
    _rect(s, P["main"], x0, fy - 18, tw, 10)                  # torso
    _rect(s, P["light"], x0, fy - 18, tw, 2)                  # shoulder light
    _rect(s, P["dark"], x0 + tw - 3, fy - 16, 3, 8)           # shaded side
    _rect(s, (60, 52, 44), x0, fy - 10, tw, 2)                # belt
    _rect(s, (230, 200, 90), fx - 1, fy - 10, 2, 2)           # buckle
    _rect(s, P["dark"], x0 - 2, fy - 17, 2, 8)                # arms
    _rect(s, P["dark"], x0 + tw, fy - 17, 2, 8)
    _rect(s, skin, x0 - 2, fy - 9, 2, 2)                      # hands
    _rect(s, skin, x0 + tw, fy - 9, 2, 2)
    _rect(s, skin, fx - 3, fy - 24, 6, 6)                     # head
    _rect(s, SKIN_D, fx - 3, fy - 20, 6, 1)
    s.set_at((fx - 2, fy - 22), (30, 30, 40))
    s.set_at((fx + 1, fy - 22), (30, 30, 40))


def _finish(s, P, flip_for_ai: bool, ai: bool):
    speckle(s, 0.035, 11)
    s = outline(s, P["deep"])
    if flip_for_ai and ai:
        s = pygame.transform.flip(s, True, False)
    return s


def make_sniper(P, ai: bool):
    s = new_surface(SOLDIER_W, SOLDIER_H)
    fx, fy = FOOT_X, FOOT_Y
    _soldier_base(s, P, tw=9)
    _rect(s, P["light"], fx - 3, fy - 19, 6, 2)               # scarf
    _rect(s, P["dark"], fx - 7, fy - 27, 14, 2)               # wide-brim hat
    _rect(s, P["main"], fx - 4, fy - 30, 8, 4)
    _rect(s, P["light"], fx - 4, fy - 30, 8, 1)
    pygame.draw.line(s, (30, 32, 44), (fx - 8, fy - 6), (fx + 15, fy - 20), 3)      # long rifle
    pygame.draw.line(s, METAL, (fx - 8, fy - 6), (fx + 15, fy - 20), 1)
    pygame.draw.line(s, METAL_HI, (fx - 4, fy - 9), (fx + 12, fy - 18), 1)
    _rect(s, (30, 32, 44), fx + 3, fy - 17, 5, 3)             # scope
    s.set_at((fx + 4, fy - 16), GLASS)
    _rect(s, SKIN, fx + 3, fy - 12, 2, 2)
    return _finish(s, P, True, ai), (FOOT_X, FOOT_Y)


def make_scout(P, ai: bool):
    s = new_surface(SOLDIER_W, SOLDIER_H)
    fx, fy = FOOT_X, FOOT_Y
    _rect(s, TAN, fx - 9, fy - 18, 5, 11)                     # backpack
    _rect(s, shade(TAN, 0.7), fx - 9, fy - 11, 5, 4)
    pygame.draw.line(s, METAL, (fx - 8, fy - 19), (fx - 8, fy - 29), 1)             # antenna
    s.set_at((fx - 8, fy - 30), (255, 96, 90))
    _soldier_base(s, P, tw=8)
    _rect(s, P["main"], fx - 4, fy - 27, 8, 4)                # cap
    _rect(s, P["light"], fx - 4, fy - 27, 8, 1)
    _rect(s, P["dark"], fx - 5, fy - 24, 10, 1)
    _rect(s, GLASS, fx - 3, fy - 23, 6, 2)                    # goggles
    s.set_at((fx - 1, fy - 23), (255, 255, 255))
    _rect(s, P["light"], fx - 4, fy - 19, 8, 2)               # scarf
    pygame.draw.polygon(s, P["light"], [(fx + 3, fy - 19), (fx + 10, fy - 17), (fx + 3, fy - 16)])   # scarf tail
    _rect(s, METAL, fx + 4, fy - 11, 6, 2)                    # sidearm
    _rect(s, (30, 32, 44), fx + 8, fy - 12, 2, 3)
    return _finish(s, P, True, ai), (FOOT_X, FOOT_Y)


def make_miner(P, ai: bool):
    s = new_surface(SOLDIER_W, SOLDIER_H)
    fx, fy = FOOT_X, FOOT_Y
    _soldier_base(s, P, tw=12)
    x0 = fx - 6
    _rect(s, ORANGE, x0 + 1, fy - 17, 10, 8)                  # hi-vis vest
    _rect(s, shade(ORANGE, 0.78), x0 + 8, fy - 16, 3, 7)
    _rect(s, (250, 250, 230), x0 + 1, fy - 14, 10, 1)         # reflective stripes
    _rect(s, (250, 250, 230), x0 + 1, fy - 11, 10, 1)
    _rect(s, YELLOW, fx - 4, fy - 28, 8, 5)                   # hard hat
    _rect(s, shade(YELLOW, 1.25), fx - 4, fy - 28, 8, 1)
    _rect(s, shade(YELLOW, 0.72), fx - 5, fy - 24, 10, 1)
    _rect(s, (255, 252, 214), fx - 1, fy - 27, 2, 2)          # lamp
    pygame.draw.line(s, (90, 58, 34), (fx + 5, fy - 6), (fx + 11, fy - 29), 2)       # pickaxe handle
    pygame.draw.polygon(s, METAL, [(fx + 5, fy - 31), (fx + 17, fy - 28), (fx + 17, fy - 26), (fx + 11, fy - 29),
                                   (fx + 5, fy - 27), (fx + 3, fy - 28)])
    pygame.draw.line(s, METAL_HI, (fx + 6, fy - 30), (fx + 16, fy - 28), 1)
    return _finish(s, P, True, ai), (FOOT_X, FOOT_Y)


# ---------------------------------------------------------------- tank
_DIR_AXES = {
    # facing -> (forward vector in (east, south) tile units)
    0: (0, -1),   # N
    1: (1, 0),    # E
    2: (0, 1),    # S
    3: (-1, 0),   # W
}


def make_tank(P, facing: int, ai: bool):
    s = new_surface(TANK_W, TANK_H)
    cx, cy = TANK_CX, TANK_CY
    fe, fs = _DIR_AXES[facing]
    along_e = fe != 0                                          # long axis runs East-West?
    ea, es = (0.30, 0.17) if along_e else (0.17, 0.30)
    body = (P["light"], P["main"], P["dark"])
    track_t, track_l, track_r = (62, 66, 80), (44, 48, 60), (30, 32, 42)

    def tread(sign):
        if along_e:
            iso_box(s, cx, cy, 0.34, 0.06, 4, track_t, track_l, track_r, oe=0, os_=sign * 0.22, edge=(18, 20, 28))
        else:
            iso_box(s, cx, cy, 0.06, 0.34, 4, track_t, track_l, track_r, oe=sign * 0.22, os_=0, edge=(18, 20, 28))

    tread(-1)                                                  # far tread first
    iso_box(s, cx, cy, ea, es, 6, *body, z0=2, edge=P["deep"])
    # hull detail: a lighter engine deck stripe behind the turret
    d = (-fe * 0.18, -fs * 0.18)
    iso_box(s, cx, cy, 0.07 if not along_e else 0.05, 0.05 if not along_e else 0.07, 1, shade(P["main"], 0.8), P["dark"], P["deep"],
            z0=8, oe=d[0], os_=d[1])
    tread(+1)                                                  # near tread
    # barrel: behind the turret for N/W facings, in front for E/S
    tz = 8
    start = iso(cx, cy, fe * 0.04, fs * 0.04, tz + 3)
    end = iso(cx, cy, fe * 0.58, fs * 0.58, tz + 3)

    def barrel():
        pygame.draw.line(s, (24, 26, 36), start, end, 4)
        pygame.draw.line(s, METAL, start, end, 2)
        pygame.draw.line(s, METAL_HI, (start[0], start[1] - 1), (end[0], end[1] - 1), 1)
        pygame.draw.circle(s, (24, 26, 36), (int(end[0]), int(end[1])), 3)
        pygame.draw.circle(s, METAL, (int(end[0]), int(end[1])), 2)

    behind = facing in (0, 3)
    if behind:
        barrel()
    iso_box(s, cx, cy, 0.15, 0.15, 5, P["light"], P["main"], P["dark"], z0=tz, edge=P["deep"])
    hatch = iso(cx, cy, -fe * 0.03, -fs * 0.03, tz + 5)
    pygame.draw.circle(s, shade(P["dark"], 0.8), (int(hatch[0]), int(hatch[1])), 2)
    pygame.draw.circle(s, P["light"], (int(hatch[0]), int(hatch[1] - 1)), 1)
    if not behind:
        barrel()
    speckle(s, 0.03, 21 + facing)
    return outline(s, P["deep"]), (cx, cy)


# ---------------------------------------------------------------- bomber (helicopter)
def make_bomber_body(P, ai: bool):
    s = new_surface(HELI_W, HELI_H)
    cx, cy = HELI_CX, HELI_CY - HELI_LIFT
    # tail boom and fin
    pygame.draw.polygon(s, P["dark"], [(cx - 8, cy - 4), (cx - 26, cy - 2), (cx - 26, cy + 1), (cx - 8, cy + 3)])
    pygame.draw.polygon(s, P["main"], [(cx - 24, cy - 2), (cx - 29, cy - 11), (cx - 26, cy - 11), (cx - 20, cy - 2)])
    pygame.draw.line(s, P["light"], (cx - 24, cy - 3), (cx - 9, cy - 5), 1)
    # skids
    pygame.draw.line(s, (30, 32, 44), (cx - 10, cy + 10), (cx + 12, cy + 10), 2)
    pygame.draw.line(s, (30, 32, 44), (cx - 5, cy + 5), (cx - 6, cy + 10), 1)
    pygame.draw.line(s, (30, 32, 44), (cx + 6, cy + 5), (cx + 7, cy + 10), 1)
    # missile pod under the body
    pygame.draw.rect(s, (40, 44, 58), (cx - 4, cy + 4, 12, 3))
    pygame.draw.rect(s, (255, 110, 90), (cx + 8, cy + 4, 2, 3))
    # fuselage
    pygame.draw.ellipse(s, P["main"], (cx - 11, cy - 8, 26, 16))
    pygame.draw.ellipse(s, P["dark"], (cx - 11, cy - 1, 26, 8))
    pygame.draw.ellipse(s, P["main"], (cx - 11, cy - 8, 26, 11))
    pygame.draw.ellipse(s, P["light"], (cx - 6, cy - 7, 12, 3))
    # cockpit canopy
    pygame.draw.ellipse(s, GLASS, (cx + 3, cy - 6, 12, 9))
    pygame.draw.ellipse(s, (236, 252, 255), (cx + 6, cy - 5, 5, 3))
    pygame.draw.arc(s, (60, 110, 140), (cx + 3, cy - 6, 12, 9), -1.5, 1.5, 1)
    # mast
    pygame.draw.rect(s, (40, 44, 58), (cx - 1, cy - 11, 3, 4))
    speckle(s, 0.03, 31)
    s = outline(s, P["deep"])
    if ai:
        s = pygame.transform.flip(s, True, False)
    return s, (HELI_CX, HELI_CY)


def draw_rotor(dst, mast_x: float, mast_y: float, t: float, k: float = 1.0):
    """Spinning main rotor drawn above the helicopter: translucent disc plus two blade lines (k scales it)."""
    dw, dh = max(4, int(46 * k)), max(2, int(12 * k))
    disc = new_surface(dw, dh)
    pygame.draw.ellipse(disc, (220, 230, 255, 38), (0, 0, dw, dh))
    dst.blit(disc, (mast_x - dw / 2, mast_y - dh / 2))
    ph = t * 22.0
    for i in range(2):
        a = ph + i * math.pi / 2
        ln = 21 * k * math.cos(a)
        dy = 3.2 * k * math.sin(a)
        pygame.draw.line(dst, (34, 38, 52), (mast_x - ln, mast_y - dy), (mast_x + ln, mast_y + dy), 2)
        pygame.draw.line(dst, (172, 180, 200), (mast_x - ln, mast_y - dy - 1), (mast_x + ln, mast_y + dy - 1), 1)
    pygame.draw.circle(dst, (60, 66, 84), (int(mast_x), int(mast_y)), 2)


def draw_tail_rotor(dst, x: float, y: float, t: float, k: float = 1.0):
    r = (4 * abs(math.sin(t * 40.0)) + 1) * k
    pygame.draw.line(dst, (34, 38, 52), (x, y - r), (x, y + r), 1)


# ---------------------------------------------------------------- icons for the HUD
def unit_icon(sprite: pygame.Surface, size: int = 30) -> pygame.Surface:
    """Crop a sprite to its visible pixels and fit it into a size x size square (no scaling when it fits)."""
    r = sprite.get_bounding_rect()
    crop = sprite.subsurface(r).copy()
    w, h = crop.get_size()
    if w > size or h > size:
        f = size / max(w, h)
        crop = pygame.transform.scale(crop, (max(1, int(w * f)), max(1, int(h * f))))
    out = new_surface(size, size)
    out.blit(crop, crop.get_rect(center=(size // 2, size // 2)))
    return out
