"""The board's ground and the earth slab under it, for any camera between the diamond view and the front view.

The diamond view uses the original pre-drawn board. Every other camera is rendered here: each screen pixel is
mapped back to the board with the camera's exact inverse and coloured from two textures (the diamond tiles and a
flat top-down version of the same tiles) that are cross-faded while the camera moves.
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import pygame

from . import art_terrain as T
from . import constants as K
from .camera import Camera, smoothstep
from .gfx import hash01, new_surface, shade
from .stub import BOARD_N

try:
    import numpy as np
except ImportError:                            # pragma: no cover
    np = None

HAVE_NUMPY = np is not None
F = T.FLAT


class GroundRenderer:
    def __init__(self, tiles_iso: pygame.Surface, flat_tex: pygame.Surface, bg_plain: pygame.Surface, board_layer_iso: pygame.Surface):
        self.iso_layer = board_layer_iso
        self.bg = bg_plain                                         # backdrop without any grid
        self.grid_iso = T.make_iso_grid()
        self.grid_sq = T.make_square_grid()
        self._cache: Dict[float, pygame.Surface] = {}
        if HAVE_NUMPY:
            self.iso_rgb = np.transpose(pygame.surfarray.array3d(tiles_iso), (1, 0, 2)).copy()       # (H, W, 3)
            self.iso_a = np.transpose(pygame.surfarray.array_alpha(tiles_iso), (1, 0)).copy()
            self.flat_rgb = np.transpose(pygame.surfarray.array3d(flat_tex), (1, 0, 2)).copy()

    # ---------------------------------------------------------------- the ground
    def _ground(self, cam: Camera):
        e = cam.e
        corners = [cam.ground(-0.5, -0.5), cam.ground(-0.5, BOARD_N - 0.5), cam.ground(BOARD_N - 0.5, BOARD_N - 0.5), cam.ground(BOARD_N - 0.5, -0.5)]
        x0 = max(0, int(min(p[0] for p in corners)) - 2)
        x1 = min(K.LOGICAL_W, int(max(p[0] for p in corners)) + 3)
        y0 = max(0, int(min(p[1] for p in corners)) - 2)
        y1 = min(K.LOGICAL_H, int(max(p[1] for p in corners)) + 3)
        w, h = x1 - x0, y1 - y0
        sx = ((np.arange(x0, x1, dtype=np.float32) + 0.5 - cam.cx) / cam.scale)[None, :]          # (1, w)
        sy = ((np.arange(y0, y1, dtype=np.float32) + 0.5 - cam.cy) / cam.scale)[:, None]          # (h, 1)
        a = cam.p * cam._cp
        den = np.maximum(cam._sp + a * sy, 1e-6)
        v = sy / den                                                                              # depth of each screen row
        m = 1.0 - a * v                                                                           # 1 / perspective factor
        half = (BOARD_N - 1) / 2.0
        # grid column and row as  (per-row constant) + (per-row slope) * sx: only a multiply-add per pixel
        col = (m * cam._c) * sx + (v * cam._s + half)
        row = (-m * cam._s) * sx + (v * cam._c + half)
        inside = (row >= -0.5) & (row < BOARD_N - 0.5) & (col >= -0.5) & (col < BOARD_N - 0.5)
        wt = smoothstep((e - 0.12) / 0.7)                                                         # share of the flat texture
        out = None
        if wt < 1.0:
            ix = np.clip(((col - row) * (K.TW / 2) + K.OX).astype(np.int32), 0, K.LOGICAL_W - 1)
            iy = np.clip(((col + row) * (K.TH / 2) + K.OY).astype(np.int32), 0, K.LOGICAL_H - 1)
            out = self.iso_rgb[iy, ix]
        if wt > 0.0:
            fx = np.clip(((col + 0.5) * F).astype(np.int32), 0, F * BOARD_N - 1)
            fy = np.clip(((row + 0.5) * F).astype(np.int32), 0, F * BOARD_N - 1)
            flat = self.flat_rgb[fy, fx]
            if out is None:
                out = flat
            else:
                out = (out * (1.0 - wt) + flat * wt).astype(np.uint8)
        rgba = np.empty((h, w, 4), dtype=np.uint8)
        rgba[..., :3] = out
        rgba[..., 3] = inside * np.uint8(255)
        return pygame.image.frombuffer(rgba.tobytes(), (w, h), "RGBA"), (x0, y0)

    # ---------------------------------------------------------------- soil under the board
    def _slab(self, dst: pygame.Surface, cam: Camera):
        """The visible vertical sides of the soil slab, drawn as one-pixel-wide columns (grass lip, strata, dark bottom)."""
        for face in cam.visible_faces():
            if face == "S":
                a, b, base, lip_f, seed = (BOARD_N - 0.5, -0.5), (BOARD_N - 0.5, BOARD_N - 0.5), K.SOIL_LEFT, 0.78, 3
            else:
                a, b, base, lip_f, seed = (-0.5, BOARD_N - 0.5), (BOARD_N - 0.5, BOARD_N - 0.5), K.SOIL_RIGHT, 0.62, 5
            (xa, ya), (xb, yb) = cam.ground(*a), cam.ground(*b)
            (xa2, ya2), (xb2, yb2) = cam.ground(*a, -cam.slab), cam.ground(*b, -cam.slab)
            if xa > xb:                                          # left edge first
                (xa, ya, xa2, ya2), (xb, yb, xb2, yb2) = (xb, yb, xb2, yb2), (xa, ya, xa2, ya2)
            span = max(1e-6, xb - xa)
            lip = shade(K.GRASS_B, lip_f)
            for x in range(int(math.floor(xa)), int(math.ceil(xb)) + 1):
                t = max(0.0, min(1.0, (x + 0.5 - xa) / span))
                yt = int(round(ya + (yb - ya) * t))
                n = max(2, int(round(ya2 + (yb2 - ya2) * t)) - yt)
                nz = hash01(x, 7, seed)
                body = shade(base, 1.0 + (nz - 0.5) * 0.16)
                band = shade(body, 0.88)
                lip_n = 2 + (1 if hash01(x, 99, seed) > 0.62 else 0)
                pygame.draw.line(dst, shade(lip, 1.0 + (nz - 0.5) * 0.2), (x, yt), (x, yt + lip_n - 1))
                j = lip_n
                while j < n:
                    seg = min(n - j, 2 if (j + seed) % 4 < 2 else 2)
                    pygame.draw.line(dst, band if (j + seed) % 4 < 1 else body, (x, yt + j), (x, yt + j + seg - 1))
                    j += seg
                pygame.draw.line(dst, shade(body, 0.7), (x, yt + n - 1), (x, yt + n))

    def _shadow(self, dst: pygame.Surface, cam: Camera):
        sh = new_surface(*dst.get_size())
        pts = [cam.ground(-0.5, -0.5, -cam.slab), cam.ground(-0.5, BOARD_N - 0.5, -cam.slab),
               cam.ground(BOARD_N - 0.5, BOARD_N - 0.5, -cam.slab), cam.ground(BOARD_N - 0.5, -0.5, -cam.slab)]
        cx = sum(p[0] for p in pts) / 4
        cy = sum(p[1] for p in pts) / 4
        for i in range(7, 0, -1):
            g = 1.0 + i * 0.012
            poly = [(cx + (x - cx) * g, cy + (y - cy) * g + 3) for x, y in pts]
            pygame.draw.polygon(sh, (0, 0, 8, 22), poly)
        dst.blit(sh, (0, 0))

    # ---------------------------------------------------------------- public
    def layer(self, cam: Camera) -> pygame.Surface:
        """The full 640x360 backdrop + board for this camera."""
        if cam.is_iso:
            return self.iso_layer
        key = cam.e
        if key in self._cache:
            return self._cache[key]
        e = cam.e
        out = self.bg.copy()
        ga = self.grid_iso
        gs = self.grid_sq
        a_iso, a_sq = int(255 * (1 - smoothstep(e * 1.6))), int(255 * smoothstep((e - 0.35) / 0.65))
        if a_iso > 2:
            ga.set_alpha(a_iso)
            out.blit(ga, (0, 0))
        if a_sq > 2:
            gs.set_alpha(a_sq)
            out.blit(gs, (0, 0))
        self._shadow(out, cam)
        self._slab(out, cam)
        surf, pos = self._ground(cam)
        out.blit(surf, pos)
        if e >= 1.0:                                              # the settled front view is the same every frame
            self._cache[key] = out
        return out
