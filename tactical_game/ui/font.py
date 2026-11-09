"""Tiny built-in 5x7 pixel font, so the game needs no font file (original code, no licence issues).

Each glyph is 5 bytes, one per column, bit 0 = top row.  Rows 0-6 are the letter, row 7 is
the descender row used by g j p q y.  Text is drawn on the 640x360 logical surface, so every
pixel here becomes a crisp square after scaling.
"""
from __future__ import annotations

import pygame

_RAW = """
20: 00 00 00 00 00 | 21: 00 00 5F 00 00 | 22: 00 07 00 07 00 | 23: 14 7F 14 7F 14
24: 24 2A 7F 2A 12 | 25: 23 13 08 64 62 | 26: 36 49 56 20 50 | 27: 00 05 03 00 00
28: 00 1C 22 41 00 | 29: 00 41 22 1C 00 | 2A: 2A 1C 7F 1C 2A | 2B: 08 08 3E 08 08
2C: 00 A0 60 00 00 | 2D: 08 08 08 08 08 | 2E: 00 60 60 00 00 | 2F: 20 10 08 04 02
30: 3E 51 49 45 3E | 31: 00 42 7F 40 00 | 32: 42 61 51 49 46 | 33: 21 41 45 4B 31
34: 18 14 12 7F 10 | 35: 27 45 45 45 39 | 36: 3C 4A 49 49 30 | 37: 01 71 09 05 03
38: 36 49 49 49 36 | 39: 06 49 49 29 1E | 3A: 00 36 36 00 00 | 3B: 00 56 36 00 00
3C: 08 14 22 41 00 | 3D: 14 14 14 14 14 | 3E: 00 41 22 14 08 | 3F: 02 01 51 09 06
40: 32 49 79 41 3E | 41: 7E 11 11 11 7E | 42: 7F 49 49 49 36 | 43: 3E 41 41 41 22
44: 7F 41 41 22 1C | 45: 7F 49 49 49 41 | 46: 7F 09 09 09 01 | 47: 3E 41 49 49 7A
48: 7F 08 08 08 7F | 49: 00 41 7F 41 00 | 4A: 20 40 41 3F 01 | 4B: 7F 08 14 22 41
4C: 7F 40 40 40 40 | 4D: 7F 02 0C 02 7F | 4E: 7F 04 08 10 7F | 4F: 3E 41 41 41 3E
50: 7F 09 09 09 06 | 51: 3E 41 51 21 5E | 52: 7F 09 19 29 46 | 53: 46 49 49 49 31
54: 01 01 7F 01 01 | 55: 3F 40 40 40 3F | 56: 1F 20 40 20 1F | 57: 3F 40 38 40 3F
58: 63 14 08 14 63 | 59: 07 08 70 08 07 | 5A: 61 51 49 45 43 | 5B: 00 7F 41 41 00
5C: 02 04 08 10 20 | 5D: 00 41 41 7F 00 | 5E: 04 02 01 02 04 | 5F: 40 40 40 40 40
60: 00 01 02 04 00 | 61: 20 54 54 54 78 | 62: 7F 48 44 44 38 | 63: 38 44 44 44 20
64: 38 44 44 48 7F | 65: 38 54 54 54 18 | 66: 08 7E 09 01 02 | 67: 18 A4 A4 9C 78
68: 7F 08 04 04 78 | 69: 00 44 7D 40 00 | 6A: 20 40 44 3D 00 | 6B: 7F 10 28 44 00
6C: 00 41 7F 40 00 | 6D: 7C 04 18 04 78 | 6E: 7C 08 04 04 78 | 6F: 38 44 44 44 38
70: FC 18 24 24 18 | 71: 18 24 24 18 FC | 72: 7C 08 04 04 08 | 73: 48 54 54 54 20
74: 04 3F 44 40 20 | 75: 3C 40 40 20 7C | 76: 1C 20 40 20 1C | 77: 3C 40 30 40 3C
78: 44 28 10 28 44 | 79: 4C 90 90 90 7C | 7A: 44 64 54 4C 44 | 7B: 00 08 36 41 00
7C: 00 00 7F 00 00 | 7D: 00 41 36 08 00 | 7E: 02 01 02 04 02
"""

GLYPHS: dict[str, tuple[int, ...]] = {}
for _chunk in _RAW.replace("\n", "|").split("|"):
    _chunk = _chunk.strip()
    if not _chunk:
        continue
    _code, _bytes = _chunk.split(":")
    GLYPHS[chr(int(_code, 16))] = tuple(int(b, 16) for b in _bytes.split())

# Characters the interface needs beyond ASCII, drawn as 5-column bitmaps.
GLYPHS["−"] = (0x08, 0x08, 0x08, 0x08, 0x08)        # minus sign -> same as hyphen
GLYPHS["•"] = (0x00, 0x1C, 0x1C, 0x1C, 0x00)        # bullet
GLYPHS["→"] = (0x08, 0x08, 0x2A, 0x1C, 0x08)        # arrow right
GLYPHS["×"] = (0x22, 0x14, 0x08, 0x14, 0x22)        # multiplication sign

_cache: dict[tuple, pygame.Surface] = {}


def text_width(text: str, scale: int = 1) -> int:
    return max(0, len(text) * 6 - 1) * scale if text else 0


def render(text: str, color, scale: int = 1, shadow=None) -> pygame.Surface:
    """Return a surface with `text` drawn in `color` (optional 1-pixel drop shadow)."""
    key = (text, tuple(color), scale, tuple(shadow) if shadow else None)
    hit = _cache.get(key)
    if hit is not None:
        return hit
    w = max(1, text_width(text, scale)) + (scale if shadow else 0)
    h = 8 * scale + (scale if shadow else 0)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for layer_color, off in ((shadow, scale), (color, 0)) if shadow else ((color, 0),):
        x = 0
        for ch in text:
            cols = GLYPHS.get(ch, GLYPHS["?"])
            for cx, bits in enumerate(cols):
                for cy in range(8):
                    if bits >> cy & 1:
                        surf.fill(layer_color, (x + cx * scale + off, cy * scale + off, scale, scale))
            x += 6 * scale
    if len(_cache) > 800:
        _cache.clear()
    _cache[key] = surf
    return surf


def draw(dst: pygame.Surface, text: str, pos, color, scale: int = 1, shadow=None, anchor: str = "topleft"):
    """Draw text; `anchor` is any pygame Rect attribute name such as 'topleft', 'midtop', 'topright'."""
    s = render(text, color, scale, shadow)
    r = s.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    dst.blit(s, r)
    return r


def wrap(text: str, max_width: int, scale: int = 1) -> list[str]:
    """Greedy word wrap into lines no wider than max_width pixels."""
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines
