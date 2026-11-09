"""Projection and picking (Q2). The functions here use the current camera (see camera.py).

In the diamond view (the default) a tile centre sits at
    x = OX + (col - row) * TW / 2
    y = OY + (col + row) * TH / 2
North (row - 1) points up-right on screen, East down-right, South down-left, West up-left.
In the front view North is up, East is right. `set_blend` moves the camera between the two.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

from .camera import Camera
from .constants import BOARD_N, OX, OY, TH, TW

CAM = Camera(0.0)


def set_blend(e: float) -> Camera:
    """Move the shared camera to blend e (0 = diamond view, 1 = front view) and return it."""
    global CAM
    e = max(0.0, min(1.0, float(e)))
    if e != CAM.e:
        CAM = Camera(e)
    return CAM


def grid_to_screen(row: float, col: float) -> Tuple[float, float]:
    """Pixel position of the centre of tile (row, col). Floats are fine (used for slides)."""
    return CAM.ground(row, col)


def tile_polygon(row: int, col: int):
    """The four corners of a tile: back corner, then clockwise (top, right, bottom, left in the diamond view)."""
    if CAM.is_iso:
        x, y = OX + (col - row) * TW / 2, OY + (col + row) * TH / 2
        return [(x, y - TH / 2), (x + TW / 2, y), (x, y + TH / 2), (x - TW / 2, y)]
    g = CAM.ground
    return [g(row - 0.5, col - 0.5), g(row - 0.5, col + 0.5), g(row + 0.5, col + 0.5), g(row + 0.5, col - 0.5)]


def screen_to_grid(x: float, y: float) -> Optional[Tuple[int, int]]:
    """Exact inverse of the tile-centre formula: the tile under a screen point, or None off the board.

    Diamond view: rounding each grid coordinate selects exactly the diamond around a tile centre,
    because |dc - dr| + |dc + dr| = 2 * max(|dc|, |dr|). Other views use the camera's closed-form inverse.
    """
    if CAM.is_iso:
        dx, dy = x - OX, y - OY
        col = math.floor((dy / (TH / 2) + dx / (TW / 2)) / 2 + 0.5)
        row = math.floor((dy / (TH / 2) - dx / (TW / 2)) / 2 + 0.5)
    else:
        rc = CAM.inverse(x, y)
        if rc is None:
            return None
        row, col = math.floor(rc[0] + 0.5), math.floor(rc[1] + 0.5)
    if 0 <= row < BOARD_N and 0 <= col < BOARD_N:
        return row, col
    return None


def depth_key(row: float, col: float) -> Tuple[float, float]:
    """Painter order: smaller draws first (farther from the camera)."""
    return CAM.depth(row, col)
