"""Letterbox scaling and window-to-logical mouse mapping (Q1, milestone M1).

The game draws on a fixed 640x360 surface. Each frame that surface is scaled (nearest neighbour, so
pixels stay sharp) into the window and centred; black bars fill the rest. Mouse positions must go the
other way: undo the offset and the scale, and reject points that land on the bars.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .constants import LOGICAL_H, LOGICAL_W


@dataclass(frozen=True)
class Viewport:
    scale: float        # window pixels per logical pixel
    x: int              # left edge of the scaled picture inside the window
    y: int              # top edge
    w: int              # scaled picture size
    h: int


def compute_viewport(win_w: int, win_h: int, integer: bool = True) -> Viewport:
    """Largest scaled picture that fits the window. With integer=True the scale is a whole number
    (when the window is at least 640x360), which keeps every pixel the same size."""
    win_w, win_h = max(1, win_w), max(1, win_h)
    fit = min(win_w / LOGICAL_W, win_h / LOGICAL_H)
    scale = float(max(1, int(fit))) if integer and fit >= 1 else fit
    w, h = max(1, int(LOGICAL_W * scale)), max(1, int(LOGICAL_H * scale))
    return Viewport(scale, (win_w - w) // 2, (win_h - h) // 2, w, h)


def window_to_logical(mx: float, my: float, vp: Viewport) -> Optional[Tuple[float, float]]:
    """Window pixel -> logical coordinates, or None when the point is on a letterbox bar."""
    if not (vp.x <= mx < vp.x + vp.w and vp.y <= my < vp.y + vp.h):
        return None
    return (mx - vp.x) / vp.scale, (my - vp.y) / vp.scale


def logical_to_window(lx: float, ly: float, vp: Viewport) -> Tuple[float, float]:
    return lx * vp.scale + vp.x, ly * vp.scale + vp.y
