"""One camera for both views of the board (Q2).

The diamond view and the front view are two settings of the same camera, so the board can glide between them.
A camera has a yaw (45 degrees = diamond, 0 = front), a pitch, a small perspective strength and a scale.
World coordinates are in tiles, centred on the board: X to the East (column), Y to the South (row), Z up.

    u =  X cos(yaw) - Y sin(yaw)          (screen right)
    v =  X sin(yaw) + Y cos(yaw)          (towards the viewer)
    k = 1 / (1 - p (v cos(pitch) + Z sin(pitch)))
    screen = centre + scale * k * (u, v sin(pitch) - Z cos(pitch))

Because the ground is a flat plane this is a projective map, so it has an exact closed-form inverse
(used for picking). At blend 0 every function returns exactly the original diamond formulas.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

from . import constants as K

HALF = (K.BOARD_N - 1) / 2.0
_YAW_ISO = math.radians(45.0)
_PITCH_ISO = math.asin(K.TH / K.TW)                           # a 2:1 diamond
_SCALE_ISO = (K.TW / 2.0) / math.cos(_YAW_ISO)
_CY_ISO = K.OY + (K.BOARD_N - 1) * K.TH / 2.0
_SLAB_ISO = K.SLAB_DEPTH / (math.cos(_PITCH_ISO) * _SCALE_ISO)  # soil thickness in tiles that gives the original 11 px


def smoothstep(x: float) -> float:
    x = 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
    return x * x * (3.0 - 2.0 * x)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class Camera:
    def __init__(self, blend: float = 0.0):
        e = max(0.0, min(1.0, float(blend)))
        self.e = e
        self.yaw = _lerp(_YAW_ISO, 0.0, e)
        self.pitch = _lerp(_PITCH_ISO, math.radians(K.TOP_PITCH_DEG), e)
        self.p = _lerp(0.0, K.TOP_PERSPECTIVE, e)
        self.scale = _lerp(_SCALE_ISO, K.TOP_TILE, e)
        self.cx = K.LOGICAL_W / 2.0
        self.cy = _lerp(_CY_ISO, K.TOP_CY, e)
        self.slab = _lerp(_SLAB_ISO, K.TOP_SLAB, e)
        self._c, self._s = math.cos(self.yaw), math.sin(self.yaw)
        self._sp, self._cp = math.sin(self.pitch), math.cos(self.pitch)
        self.is_iso = e == 0.0

    # ---------------------------------------------------------------- forward
    def ground(self, row: float, col: float, z: float = 0.0) -> Tuple[float, float]:
        """Screen position of the point `z` tiles above the grid point (row, col). Tile centres sit on whole numbers."""
        if self.is_iso and z == 0.0:
            return K.OX + (col - row) * K.TW / 2, K.OY + (col + row) * K.TH / 2
        x, y = col - HALF, row - HALF
        u = x * self._c - y * self._s
        v = x * self._s + y * self._c
        k = 1.0 / (1.0 - self.p * (v * self._cp + z * self._sp))
        return self.cx + self.scale * k * u, self.cy + self.scale * k * (v * self._sp - z * self._cp)

    def k_at(self, row: float, col: float) -> float:
        """Perspective factor at a grid point (1 in the middle of the board, larger nearer the viewer)."""
        x, y = col - HALF, row - HALF
        v = x * self._s + y * self._c
        return 1.0 / (1.0 - self.p * v * self._cp)

    def tile_px(self, row: float, col: float) -> float:
        """Width in pixels of the tile at (row, col) (its bounding box on screen). 48 in the diamond view."""
        return self.scale * self.k_at(row, col) * (abs(self._c) + abs(self._s))

    # ---------------------------------------------------------------- inverse
    def inverse(self, x: float, y: float) -> Optional[Tuple[float, float]]:
        """Grid position (row, col, as floats) under screen point (x, y); None if the point is above the horizon."""
        xs, ys = (x - self.cx) / self.scale, (y - self.cy) / self.scale
        a = self.p * self._cp
        den = self._sp + a * ys
        if den <= 1e-9:
            return None
        v = ys / den
        k = 1.0 / (1.0 - a * v)
        u = xs / k
        X = u * self._c + v * self._s
        Y = -u * self._s + v * self._c
        return Y + HALF, X + HALF

    # ---------------------------------------------------------------- helpers for drawing on the ground
    def basis(self, row: float, col: float):
        """(centre, east half-vector, south half-vector) of a tile on screen, from finite differences."""
        c = self.ground(row, col)
        e0, e1 = self.ground(row, col - 0.5), self.ground(row, col + 0.5)
        s0, s1 = self.ground(row - 0.5, col), self.ground(row + 0.5, col)
        return c, ((e1[0] - e0[0]) / 2, (e1[1] - e0[1]) / 2), ((s1[0] - s0[0]) / 2, (s1[1] - s0[1]) / 2)

    def depth(self, row: float, col: float) -> Tuple[float, float]:
        """Painter order key: smaller draws first (farther from the viewer)."""
        if self.is_iso:
            return (row + col, row)
        x, y = col - HALF, row - HALF
        return (round(x * self._s + y * self._c, 4), -round(x * self._c - y * self._s, 4))

    def visible_faces(self):
        """Which vertical sides of the soil slab face the viewer: 'S' (row 7 edge) and 'E' (col 7 edge)."""
        faces = []
        if self._c > 1e-6:
            faces.append("S")
        if self._s > 1e-6:
            faces.append("E")
        return faces
