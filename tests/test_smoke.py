"""Headless smoke tests: the UI builds, draws a frame, and the demo interaction behaves."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from dataclasses import replace

import pygame
import pytest

from tactical_game.ui.app import App
from tactical_game.ui import constants as K
from tactical_game.ui.projection import grid_to_screen
from tactical_game.ui.stub import Direction, Side, UnitType, make_stub_state, terrain_at, Terrain


@pytest.fixture()
def app():
    a = App()
    yield a
    pygame.quit()


def click_cell(app, cell):
    app.handle_click(*grid_to_screen(*cell))


def test_frame_draws_and_the_logical_surface_has_the_right_size(app):
    app.draw_frame(1.0)
    assert app.logical.get_size() == (K.LOGICAL_W, K.LOGICAL_H)
    # the board region is not blank: tiles are painted where the projection says they are
    x, y = grid_to_screen(4, 4)
    assert app.logical.get_at((int(x), int(y)))[:3] != app.art.bg_plain.get_at((int(x), int(y)))[:3]


def test_stub_state_has_six_units_in_the_final_spawn_slots():
    s = make_stub_state("TSB", "TCM")
    assert len(s.units) == 6
    pos = {u.id: u.pos for u in s.units}
    assert pos == {"H1": (3, 1), "H2": (5, 0), "H3": (4, 0), "A1": (4, 6), "A2": (2, 7), "A3": (3, 7)}
    assert {u.hp for u in s.units if u.type == UnitType.TANK} == {12}
    assert terrain_at((4, 1)) == Terrain.COVER and terrain_at((2, 2)) == Terrain.WALL


@pytest.mark.parametrize("bad", ["TT", "TSX", "TST1", ""])
def test_bad_lineups_are_rejected(bad):
    with pytest.raises(ValueError):
        make_stub_state(bad, "TCM")


def test_select_then_move_a_tank_updates_position_and_facing(app):
    click_cell(app, (3, 1))
    assert app.view.selected == "H1" and app.view.options is not None
    assert (3, 2) in app.view.options.moves
    click_cell(app, (3, 2))
    u = app.state.unit_by_id("H1")
    assert u.pos == (3, 2) and u.facing == Direction.E
    assert app.view.selected is None


def test_diagonal_tank_move_faces_east_or_west_by_column_change(app):
    click_cell(app, (3, 1))
    assert (2, 2) not in app.view.options.moves            # wall
    assert (4, 2) in app.view.options.moves                # diagonal, column +1
    click_cell(app, (4, 2))
    assert app.state.unit_by_id("H1").facing == Direction.E


def test_walls_and_units_are_not_reachable(app):
    click_cell(app, (5, 0))                                # Sniper, move 2
    moves = set(app.view.options.moves)
    assert (4, 0) not in moves and (3, 1) not in moves     # occupied by friends
    assert (5, 2) not in moves                             # wall
    assert (5, 1) in moves


def test_right_click_and_escape_cancel_selection(app):
    click_cell(app, (3, 1))
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.view.selected is None
    click_cell(app, (3, 1))
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(5, 5)))
    assert app.view.selected is None


def test_attack_applies_damage_cover_reduction_and_scores_a_kill(app):
    us = [replace(u, pos=(3, 2)) if u.id == "H1" else replace(u, pos=(3, 4), hp=3) if u.id == "A2" else u for u in app.state.units]
    app.state = replace(app.state, units=tuple(us))
    click_cell(app, (3, 2))
    assert (3, 4) in app.view.options.attacks               # Tank faces east: 2nd cell ahead
    click_cell(app, (3, 4))
    assert app.state.unit_by_id("A2") is None               # 10 damage kills a 3 HP scout
    assert app.state.points == (2, 0)
    assert app.view.ghosts and app.view.texts


def test_number_keys_select_units_and_restart_resets(app):
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
    assert app.view.selected == "H2"
    click_cell(app, (5, 1))
    assert app.state.unit_by_id("H2").pos == (5, 1)
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
    assert app.state.unit_by_id("H2").pos == (5, 0)


def test_window_resize_keeps_clicks_on_the_right_cell(app):
    app.window = pygame.display.set_mode((1920, 1000), pygame.RESIZABLE)
    app.update_viewport()
    vp = app.viewport
    lx, ly = grid_to_screen(3, 1)
    wx, wy = lx * vp.scale + vp.x, ly * vp.scale + vp.y
    app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(wx, wy), rel=(0, 0), buttons=(0, 0, 0)))
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(wx, wy)))
    assert app.view.selected == "H1"


def test_screenshot_writes_a_png(app, tmp_path):
    out = tmp_path / "shot.png"
    app.screenshot(str(out), frames=3)
    assert out.exists() and out.stat().st_size > 5000


# ---------------------------------------------------------------- the view change (diamond <-> front)
def run_frames(app, seconds, start=1.0):
    n = int(seconds * 60) + 2
    for i in range(n):
        app.draw_frame(start + i / 60)
    return start + n / 60


def test_view_button_exists_and_the_v_key_toggles_the_target(app):
    assert any(b.key == "view" for b in app.hud.buttons(app.state, app.view))
    assert app.cam_target == 0.0
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, mod=0, unicode="v"))
    assert app.cam_target == 1.0
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, mod=0, unicode="v"))
    assert app.cam_target == 0.0


def test_the_camera_glides_to_the_front_view_and_back(app):
    app.draw_frame(1.0)
    diamond = app.logical.copy()
    app.toggle_view()
    seen = set()
    t = 1.0
    for i in range(int(K.VIEW_SECONDS * 60) + 6):
        t += 1 / 60
        app.draw_frame(t)
        seen.add(round(app.cam_t, 2))
    assert app.cam_t == 1.0 and len(seen) > 10                      # it passed through many in-between angles
    from tactical_game.ui import projection
    assert projection.CAM.e == 1.0
    app.toggle_view()
    for i in range(int(K.VIEW_SECONDS * 60) + 6):
        t += 1 / 60
        app.draw_frame(t)
    assert app.cam_t == 0.0 and projection.CAM.is_iso
    assert app.art.board(projection.CAM) is app.art.board_layer       # back to the original pre-drawn diamond board


def test_clicks_pick_the_right_cell_in_the_front_view(app):
    app.toggle_view()
    run_frames(app, K.VIEW_SECONDS + 0.2)
    assert app.cam_t == 1.0
    tank = app.state.unit_by_id("H1")
    cx, cy = grid_to_screen(*tank.pos)
    app.handle_click(cx, cy)
    assert app.view.selected == "H1"
    target = sorted(app.view.options.moves)[0]
    app.handle_click(*grid_to_screen(*target))
    assert app.state.unit_by_id("H1").pos == target


def test_front_view_draws_every_kind_of_thing_without_errors(app):
    app.mid_game = True
    app.reset(mid_game=True)
    app.toggle_view()
    t = run_frames(app, K.VIEW_SECONDS + 0.2)
    app.select("H1")
    for i in range(10):
        app.draw_frame(t + i / 60)
    app.view.slides["H2"] = __import__("tactical_game.ui.view", fromlist=["Slide"]).Slide([(5, 0), (5, 1)], t, 0.3)
    for i in range(30):
        app.draw_frame(t + 1 + i / 60)
    assert app.logical.get_size() == (K.LOGICAL_W, K.LOGICAL_H)


def test_front_view_screenshot_flag_writes_a_png(tmp_path):
    from tactical_game.ui.app import main
    out = tmp_path / "front.png"
    assert main(["--view", "front", "--screenshot", str(out)]) == 0
    assert out.exists() and out.stat().st_size > 1000
    pygame.quit()
