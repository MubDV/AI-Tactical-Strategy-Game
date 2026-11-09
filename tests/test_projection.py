import itertools

from tactical_game.ui.constants import BOARD_N, TH, TW
from tactical_game.ui.projection import depth_key, grid_to_screen, screen_to_grid, tile_polygon


def test_round_trip_all_cells():
    for r, c in itertools.product(range(BOARD_N), repeat=2):
        x, y = grid_to_screen(r, c)
        assert screen_to_grid(x, y) == (r, c)


def test_points_just_inside_each_edge_pick_the_same_tile():
    eps = 0.6
    for r, c in itertools.product(range(BOARD_N), repeat=2):
        x, y = grid_to_screen(r, c)
        for dx, dy in [(0, -TH / 2 + eps), (TW / 2 - eps * 2, 0), (0, TH / 2 - eps), (-TW / 2 + eps * 2, 0),
                       (TW / 4 - eps, TH / 4 - eps / 2), (-TW / 4 + eps, -TH / 4 + eps / 2)]:
            assert screen_to_grid(x + dx, y + dy) == (r, c), (r, c, dx, dy)


def test_points_outside_the_board_return_none():
    assert screen_to_grid(0, 0) is None
    x, y = grid_to_screen(0, 0)
    assert screen_to_grid(x, y - TH) is None          # above the top corner
    x, y = grid_to_screen(7, 7)
    assert screen_to_grid(x, y + TH) is None          # below the bottom corner
    assert screen_to_grid(1000, 1000) is None


def test_polygon_has_four_corners_around_the_centre():
    pts = tile_polygon(3, 4)
    cx, cy = grid_to_screen(3, 4)
    assert pts == [(cx, cy - TH / 2), (cx + TW / 2, cy), (cx, cy + TH / 2), (cx - TW / 2, cy)]


def test_painter_order_draws_far_tiles_first():
    assert depth_key(0, 0) < depth_key(1, 0) < depth_key(1, 1)
    assert depth_key(2, 1) < depth_key(1, 2) or depth_key(2, 1) > depth_key(1, 2)  # same diagonal: tie broken by row
    assert depth_key(0, 3)[0] == depth_key(3, 0)[0]


def test_directions_on_screen():
    cx, cy = grid_to_screen(4, 4)
    nx, ny = grid_to_screen(3, 4)    # North
    ex, ey = grid_to_screen(4, 5)    # East
    sx, sy = grid_to_screen(5, 4)    # South
    wx, wy = grid_to_screen(4, 3)    # West
    assert nx > cx and ny < cy       # up-right
    assert ex > cx and ey > cy       # down-right
    assert sx < cx and sy > cy       # down-left
    assert wx < cx and wy < cy       # up-left
