import pytest

from tactical_game.ui.constants import LOGICAL_H, LOGICAL_W
from tactical_game.ui.scaling import compute_viewport, logical_to_window, window_to_logical


@pytest.mark.parametrize("w,h", [(1280, 720), (1920, 1080), (1000, 800), (640, 360), (1366, 768), (2560, 1440), (900, 300)])
def test_round_trip_for_many_window_sizes(w, h):
    for integer in (True, False):
        vp = compute_viewport(w, h, integer)
        assert vp.w <= w and vp.h <= h
        for lx, ly in [(0, 0), (320, 180), (639.5, 359.5), (100.25, 200.75)]:
            wx, wy = logical_to_window(lx, ly, vp)
            back = window_to_logical(wx, wy, vp)
            assert back is not None
            assert back[0] == pytest.approx(lx, abs=1e-6) and back[1] == pytest.approx(ly, abs=1e-6)


def test_integer_scale_is_a_whole_number_and_centred():
    vp = compute_viewport(1366, 768, True)
    assert vp.scale == 2.0 and (vp.w, vp.h) == (1280, 720)
    assert vp.x == (1366 - 1280) // 2 and vp.y == (768 - 720) // 2


def test_non_integer_mode_fills_the_window_on_the_limiting_side():
    vp = compute_viewport(1366, 768, False)
    assert vp.h == 768 or vp.w == 1366
    assert vp.scale == pytest.approx(min(1366 / LOGICAL_W, 768 / LOGICAL_H))


def test_clicks_on_the_letterbox_bars_are_rejected():
    vp = compute_viewport(1920, 1000, True)           # scale 2 -> 1280x720, bars on every side
    assert window_to_logical(5, 5, vp) is None
    assert window_to_logical(vp.x - 1, vp.y + 10, vp) is None
    assert window_to_logical(vp.x + vp.w, vp.y + 10, vp) is None
    assert window_to_logical(vp.x + 1, vp.y + 1, vp) is not None


def test_tiny_window_falls_back_to_fractional_scale():
    vp = compute_viewport(320, 180, True)
    assert vp.scale == pytest.approx(0.5)
    assert vp.w == 320 and vp.h == 180
