"""The shared camera: exact in the diamond view, exactly invertible everywhere, and sensible in the front view."""
import itertools
import math

import pytest

from tactical_game.ui import constants as K
from tactical_game.ui import projection as P
from tactical_game.ui.camera import Camera

BLENDS = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)


def legacy(row, col):
    return K.OX + (col - row) * K.TW / 2, K.OY + (col + row) * K.TH / 2


def test_blend_zero_is_the_original_diamond_formula():
    cam = Camera(0.0)
    for r, c in itertools.product(range(K.BOARD_N), repeat=2):
        assert cam.ground(r, c) == legacy(r, c)
    # the general formula (used by every other blend) agrees with it too, apart from float noise
    cam2 = Camera(0.0)
    cam2.is_iso = False
    for r, c in itertools.product(range(K.BOARD_N), repeat=2):
        x, y = cam2.ground(r + 0.3, c - 0.2)
        lx, ly = legacy(r + 0.3, c - 0.2)
        assert abs(x - lx) < 1e-6 and abs(y - ly) < 1e-6


@pytest.mark.parametrize("e", BLENDS)
def test_inverse_round_trips_at_every_blend(e):
    cam = Camera(e)
    for r, c in [(0, 0), (3.5, 2.25), (7, 7), (-0.5, 7.5), (6.1, 0.3)]:
        x, y = cam.ground(r, c)
        r2, c2 = cam.inverse(x, y)
        assert abs(r2 - r) < 1e-6 and abs(c2 - c) < 1e-6


@pytest.mark.parametrize("e", BLENDS)
def test_every_tile_is_picked_from_its_centre_and_near_its_corners(e):
    P.set_blend(e)
    for r, c in itertools.product(range(K.BOARD_N), repeat=2):
        x, y = P.grid_to_screen(r, c)
        assert P.screen_to_grid(x, y) == (r, c)
        poly = P.tile_polygon(r, c)
        for px, py in poly:                                      # a point 85% of the way from the centre to each corner
            assert P.screen_to_grid(x + (px - x) * 0.85, y + (py - y) * 0.85) == (r, c)


@pytest.mark.parametrize("e", BLENDS)
def test_tiles_cover_the_board_without_overlap(e):
    P.set_blend(e)

    def area(poly):
        return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2

    cam = P.CAM
    outline = [cam.ground(-0.5, -0.5), cam.ground(-0.5, 7.5), cam.ground(7.5, 7.5), cam.ground(7.5, -0.5)]
    total = sum(area(P.tile_polygon(r, c)) for r, c in itertools.product(range(K.BOARD_N), repeat=2))
    assert math.isclose(total, area(outline), rel_tol=1e-6)


def test_points_outside_the_board_return_none_in_the_front_view():
    P.set_blend(1.0)
    assert P.screen_to_grid(0, 0) is None
    assert P.screen_to_grid(1000, 1000) is None
    x, y = P.grid_to_screen(0, 3)
    assert P.screen_to_grid(x, y - K.TOP_TILE) is None


def test_front_view_directions_and_painter_order():
    P.set_blend(1.0)
    cx, cy = P.grid_to_screen(4, 4)
    nx, ny = P.grid_to_screen(3, 4)
    ex, ey = P.grid_to_screen(4, 5)
    sx, sy = P.grid_to_screen(5, 4)
    wx, wy = P.grid_to_screen(4, 3)
    assert ny < cy and abs(nx - cx) < 1          # North is straight up
    assert ex > cx and abs(ey - cy) < 1          # East is straight right
    assert sy > cy and abs(sx - cx) < 1
    assert wx < cx and abs(wy - cy) < 1
    assert P.depth_key(3, 3) < P.depth_key(4, 3) < P.depth_key(5, 0)     # nearer rows draw later


def test_front_view_is_a_trapezoid_that_fits_the_board_area():
    cam = Camera(1.0)
    left_far, right_far = cam.ground(-0.5, -0.5), cam.ground(-0.5, 7.5)
    left_near, right_near = cam.ground(7.5, -0.5), cam.ground(7.5, 7.5)
    assert (right_far[0] - left_far[0]) < (right_near[0] - left_near[0])          # far edge is narrower
    bottom = cam.ground(7.5, 3.5, -cam.slab)[1]                                    # including the soil slab
    assert left_far[1] >= 34 and bottom <= K.RECT_MESSAGE[1]
    assert left_far[0] >= K.RECT_LEFT[0] + K.RECT_LEFT[2] and right_near[0] <= K.RECT_RIGHT[0]


def test_tile_size_is_48_in_the_diamond_view_and_shrinks_in_the_front_view():
    assert Camera(0.0).tile_px(3, 3) == pytest.approx(K.TW)
    assert 25 < Camera(1.0).tile_px(3.5, 3.5) < 35


def test_the_camera_moves_smoothly():
    prev = None
    for i in range(41):
        cam = Camera(i / 40)
        pts = [cam.ground(r, c) for r, c in ((0, 0), (0, 7), (7, 7), (7, 0))]
        if prev:
            assert max(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pts, prev)) < 14
        prev = pts
