"""Small drawing helpers shared by the art modules (colour maths, isometric boxes, outlines)."""
from __future__ import annotations

import math

import pygame

from .constants import TH, TW


def clamp8(v) -> int:
    return 0 if v < 0 else 255 if v > 255 else int(v)


def shade(c, f):
    """Multiply a colour by f (f > 1 lightens, f < 1 darkens)."""
    return (clamp8(c[0] * f), clamp8(c[1] * f), clamp8(c[2] * f))


def mix(a, b, t):
    return (clamp8(a[0] + (b[0] - a[0]) * t), clamp8(a[1] + (b[1] - a[1]) * t), clamp8(a[2] + (b[2] - a[2]) * t))


def hash01(x: int, y: int, seed: int = 0) -> float:
    """Deterministic pseudo-random number in [0, 1) from integer inputs (no global RNG state)."""
    n = (x * 374761393 + y * 668265263 + seed * 2147483647 + 1442695040888963407) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65536.0


def new_surface(w: int, h: int) -> pygame.Surface:
    return pygame.Surface((w, h), pygame.SRCALPHA)


def iso(cx: float, cy: float, oe: float = 0.0, os_: float = 0.0, z: float = 0.0):
    """Screen point for an offset of (oe tiles East, os_ tiles South, z pixels up) from (cx, cy)."""
    return (cx + (oe - os_) * TW / 2, cy + (oe + os_) * TH / 2 - z)


def iso_box(surf, cx, cy, ea, es, h, top, left, right, z0=0.0, oe=0.0, os_=0.0, edge=None):
    """Draw an isometric cuboid centred `oe`,`os_` tiles from (cx, cy), half-sizes ea (East) and es (South)."""
    def P(de, ds, z):
        return iso(cx, cy, oe + de, os_ + ds, z)

    t = [P(-ea, -es, z0 + h), P(ea, -es, z0 + h), P(ea, es, z0 + h), P(-ea, es, z0 + h)]
    lf = [t[3], t[2], P(ea, es, z0), P(-ea, es, z0)]
    rt = [t[2], t[1], P(ea, -es, z0), P(ea, es, z0)]
    pygame.draw.polygon(surf, left, lf)
    pygame.draw.polygon(surf, right, rt)
    pygame.draw.polygon(surf, top, t)
    if edge is not None:
        pygame.draw.lines(surf, edge, True, t, 1)
        pygame.draw.line(surf, edge, t[2], P(ea, es, z0), 1)
    return t


def speckle(surf: pygame.Surface, amount: float, seed: int = 0):
    """Add per-pixel brightness noise to every opaque pixel (gives surfaces a hand-painted grain)."""
    w, h = surf.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = surf.get_at((x, y))
            if a > 200:
                f = 1.0 + (hash01(x, y, seed) - 0.5) * 2 * amount
                surf.set_at((x, y), (clamp8(r * f), clamp8(g * f), clamp8(b * f), a))


def outline(surf: pygame.Surface, color, thickness: int = 1) -> pygame.Surface:
    """Return a copy of `surf` with a solid outline around its opaque pixels.

    The surface needs `thickness` transparent pixels of margin on every side.
    """
    w, h = surf.get_size()
    mask = pygame.mask.from_surface(surf, 100)
    flat = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
    out = new_surface(w, h)
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if abs(dx) + abs(dy) <= thickness and (dx or dy):
                out.blit(flat, (dx, dy))
    out.blit(surf, (0, 0))
    return out


def silhouette(surf: pygame.Surface, color, thickness: int = 1) -> pygame.Surface:
    """Outline only (no fill): used for the white selection outline."""
    w, h = surf.get_size()
    mask = pygame.mask.from_surface(surf, 100)
    flat = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
    out = new_surface(w, h)
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if abs(dx) + abs(dy) <= thickness and (dx or dy):
                out.blit(flat, (dx, dy))
    # punch out the sprite itself so only the ring remains
    hole = mask.to_surface(setcolor=(0, 0, 0, 0), unsetcolor=(0, 0, 0, 0))
    inner = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    out.blit(inner, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    del hole
    return out


def tile_distance(x: int, y: int):
    """For pixel (x, y) of a TWxTH tile: (d, a, b), where d <= 1 means inside the diamond."""
    a = x + 0.5 - TW / 2
    b = y + 0.5 - TH / 2
    return abs(a) / (TW / 2) + abs(b) / (TH / 2), a, b


def lerp_pt(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def circle_pts(cx, cy, rx, ry, n=10, jitter=None):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + (jitter[i][0] if jitter else 0)
        r = 1 + (jitter[i][1] if jitter else 0)
        pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
    return pts
