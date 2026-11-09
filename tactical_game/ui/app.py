"""Window, main loop and the temporary demo interaction (milestones M1-M4 preview)."""
from __future__ import annotations

if __package__ in (None, ""):                 # started as a plain file (e.g. a Run button): make the package importable
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
    from tactical_game.ui.app import main as _main
    raise SystemExit(_main())

import argparse
import os
import sys
import time
from dataclasses import replace
from typing import List, Optional

import pygame

from . import constants as K
from . import projection as P
from .art import Art
from .camera import smoothstep
from .ground import HAVE_NUMPY
from .demo_rules import Options, apply_attack, apply_move, options_for
from .hud import Hud
from .projection import screen_to_grid
from .renderer import BoardRenderer
from .scaling import Viewport, compute_viewport, window_to_logical
from .stub import NAMES, GameState, Side, UnitType, make_stub_state, terrain_at
from .view import FloatText, Flash, Ghost, Slide, View
from .projection import grid_to_screen

TITLE = "Tactical Strategy: AI Battle"


def _count(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


class App:
    def __init__(self, human: str = "TSB", ai: str = "TCM", scale: int = 2, mid_game: bool = False, front_view: bool = False):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.size = (K.LOGICAL_W * scale, K.LOGICAL_H * scale)
        self.window = pygame.display.set_mode(self.size, pygame.RESIZABLE)
        self.logical = pygame.Surface((K.LOGICAL_W, K.LOGICAL_H)).convert()
        self.clock = pygame.time.Clock()
        self.integer_scale = True
        self.fullscreen = False
        self.debug = False
        self.lineups = (human, ai)
        self.mid_game = mid_game
        self.art = Art()
        if HAVE_NUMPY:
            self.art.warm_up()
        self.renderer = BoardRenderer(self.art)
        self.hud = Hud(self.art)
        self.view = View()
        self.state: GameState = make_stub_state(human, ai, mid_game)
        self.viewport: Viewport = compute_viewport(*self.window.get_size(), self.integer_scale)
        self.mouse_logical: Optional[tuple] = None
        self.mouse_down = False
        self.running = True
        self.t0 = time.perf_counter()
        # camera: 0 = diamond view, 1 = front view. `cam_t` moves towards `cam_target` over VIEW_SECONDS and is eased.
        self.cam_target = 0.0
        self.cam_t = 0.0
        self._cam_last = None
        if front_view and HAVE_NUMPY:
            self.cam_target = self.cam_t = 1.0
        P.set_blend(smoothstep(self.cam_t))
        self.view.say("Click one of your units. Demo mode: no turns yet, the AI joins in M5.", 0.0)

    # ---------------------------------------------------------------- time and mapping
    def now(self) -> float:
        return time.perf_counter() - self.t0

    def update_viewport(self):
        self.viewport = compute_viewport(*self.window.get_size(), self.integer_scale)

    # ---------------------------------------------------------------- the camera (diamond view <-> front view)
    def toggle_view(self):
        if not HAVE_NUMPY:
            self.view.say("Changing the view needs numpy: pip install numpy", self.now(), "warn")
            return
        self.cam_target = 1.0 - self.cam_target
        self.view.say("Front view. Press V to go back to the diamond view." if self.cam_target else "Diamond view.", self.now())

    def update_camera(self, now: float):
        """Moves the shared camera a little towards the wanted view (called once per frame)."""
        dt = 0.0 if self._cam_last is None else max(0.0, min(0.1, now - self._cam_last))
        self._cam_last = now
        step = dt / K.VIEW_SECONDS
        if self.cam_t < self.cam_target:
            self.cam_t = min(self.cam_target, self.cam_t + step)
        elif self.cam_t > self.cam_target:
            self.cam_t = max(self.cam_target, self.cam_t - step)
        P.set_blend(smoothstep(self.cam_t))

    @property
    def front_view(self) -> bool:
        return self.cam_target >= 0.5

    def hover_cell(self):
        if self.mouse_logical is None:
            return None
        return screen_to_grid(*self.mouse_logical)

    # ---------------------------------------------------------------- demo interaction
    def reset(self, mid_game: Optional[bool] = None):
        if mid_game is not None:
            self.mid_game = mid_game
        self.state = make_stub_state(*self.lineups, mid_game=self.mid_game)
        self.view = View()
        self.view.say("Position reset." if not self.mid_game else "Mid-game demo state: damage, score and capture pips.", self.now())

    def select(self, uid: Optional[str]):
        self.view.selected = uid
        self.view.options = None
        if uid:
            u = self.state.unit_by_id(uid)
            self.view.options = options_for(self.state, u)
            o = self.view.options
            msg = f"{NAMES[u.type]} selected: {_count(len(o.moves), 'move')}, {_count(len(o.attacks), 'target')}"
            if u.type == UnitType.MINER:
                msg += f", {_count(len(o.burrows), 'burrow landing')}"
            self.view.say(msg + ".", self.now())

    def click_cell(self, cell):
        now = self.now()
        unit_here = self.state.unit_at(cell)
        sel = self.state.unit_by_id(self.view.selected) if self.view.selected else None
        opts = self.view.options
        if sel and opts:
            if cell in opts.moves:
                path = [sel.pos] + opts.moves[cell]
                self.view.slides[sel.id] = Slide(path, now, 0.12 * (len(path) - 1) + 0.06)
                self.state = apply_move(self.state, sel, cell)
                moved = self.state.unit_by_id(sel.id)
                extra = f" Now facing {moved.facing.name}." if sel.type == UnitType.TANK else ""
                self.view.say(f"{NAMES[sel.type]} moved to {cell[0]},{cell[1]}.{extra}", now)
                self.select(None)
                return
            if cell in opts.burrows:
                self.state = apply_move(self.state, sel, cell)
                self.view.say(f"Miner burrowed to {cell[0]},{cell[1]}.", now)
                cx, cy = grid_to_screen(*cell)
                self.view.texts.append(FloatText("DIG", (190, 150, 255), (cx, cy - 8), now, 0.7))
                self.select(None)
                return
            if cell in opts.attacks and unit_here:
                self.state, dmg, killed = apply_attack(self.state, sel, unit_here)
                cx, cy = grid_to_screen(*cell)
                cover = terrain_at(cell).value == "cover"
                self.view.texts.append(FloatText(f"-{dmg}", (255, 120, 110), (cx - 2, cy - 22), now, 1.0))
                if cover:
                    self.view.texts.append(FloatText("COVER", (150, 220, 150), (cx, cy - 6), now + 0.05, 0.9))
                self.view.flashes.append(Flash(unit_here.id, now))
                if killed:
                    self.view.ghosts.append(Ghost(unit_here, now))
                    self.view.texts.append(FloatText("+2", (255, 214, 84), (cx + 6, cy - 50), now + 0.1, 1.1))
                self.view.say(f"{NAMES[sel.type]} hits {NAMES[unit_here.type]} for {dmg}" + (" and destroys it." if killed else "."), now)
                self.select(None)
                return
        if unit_here and unit_here.side == Side.HUMAN:
            self.select(unit_here.id)
        elif sel:
            self.select(None)
            self.view.say("Selection cleared.", now)

    def handle_click(self, lx: float, ly: float):
        now = self.now()
        pt = (int(lx), int(ly))
        for b in self.hud.buttons(self.state, self.view):
            if b.rect.collidepoint(pt) and b.enabled:
                if b.key == "restart":
                    self.reset()
                elif b.key == "view":
                    self.toggle_view()
                elif b.key == "airstrike":
                    self.view.say("Airstrike aiming arrives with the rules in M4.", now, "warn")
                return
        for i, rect in enumerate(self.hud.unit_button_rects()):
            if rect.collidepoint(pt):
                self._select_by_index(i)
                return
        cell = screen_to_grid(lx, ly)
        if cell is not None:
            self.click_cell(cell)

    def _select_by_index(self, i: int):
        humans = sorted(self.state.units_of(Side.HUMAN), key=lambda u: u.id)
        if i < len(humans):
            self.select(humans[i].id)

    # ---------------------------------------------------------------- events
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self._windowed_size = self.window.get_size()
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode(getattr(self, "_windowed_size", self.size), pygame.RESIZABLE)
        self.update_viewport()

    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.VIDEORESIZE:
            self.window = pygame.display.get_surface()
            self.update_viewport()
        elif e.type == pygame.MOUSEMOTION:
            self.mouse_logical = window_to_logical(*e.pos, self.viewport)
        elif e.type == pygame.MOUSEBUTTONDOWN:
            self.mouse_logical = window_to_logical(*e.pos, self.viewport)
            if e.button == 1:
                self.mouse_down = True
                if self.mouse_logical is not None:
                    self.handle_click(*self.mouse_logical)
            elif e.button == 3 and self.view.selected:
                self.select(None)
                self.view.say("Selection cleared.", self.now())
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.mouse_down = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.view.selected:
                    self.select(None)
                    self.view.say("Selection cleared.", self.now())
                elif self.fullscreen:
                    self.toggle_fullscreen()
            elif e.key == pygame.K_r:
                self.reset()
            elif e.key == pygame.K_v:
                self.toggle_view()
            elif e.key == pygame.K_d:
                self.reset(mid_game=not self.mid_game)
            elif e.key == pygame.K_i:
                self.integer_scale = not self.integer_scale
                self.update_viewport()
                self.view.say("Integer scaling " + ("on: sharp pixels." if self.integer_scale else "off: fills the window."), self.now())
            elif e.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif e.key == pygame.K_F1:
                self.debug = not self.debug
            elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self._select_by_index(e.key - pygame.K_1)

    # ---------------------------------------------------------------- frame
    def draw_frame(self, now: float):
        self.update_camera(now)
        self.hud.front_view = self.front_view
        self.hud.can_change_view = HAVE_NUMPY
        self.view.hover = self.hover_cell()
        self.view.prune(now)
        shake = (0, 0)
        self.renderer.draw(self.logical, self.state, self.view, now)
        mouse = (int(self.mouse_logical[0]), int(self.mouse_logical[1])) if self.mouse_logical else None
        self.hud.draw(self.logical, self.state, self.view, mouse, now, self.mouse_down)
        if self.debug:
            fps = self.clock.get_fps()
            lines = [f"FPS {fps:5.1f}", f"WINDOW {self.window.get_width()}x{self.window.get_height()}  SCALE {self.viewport.scale:.2f}",
                     f"MOUSE {None if mouse is None else mouse}  CELL {self.view.hover}"]
            self.hud.debug_overlay(self.logical, lines)

    def present(self):
        vp = self.viewport
        self.window.fill((4, 6, 12))
        if vp.w == K.LOGICAL_W and vp.h == K.LOGICAL_H:
            self.window.blit(self.logical, (vp.x, vp.y))
        else:
            scaled = pygame.transform.scale(self.logical, (vp.w, vp.h))   # nearest neighbour: keeps pixels sharp
            self.window.blit(scaled, (vp.x, vp.y))
        pygame.display.flip()

    def run(self):
        while self.running:
            self.update_viewport()                       # window may have been resized or maximised
            if not pygame.mouse.get_focused():
                self.mouse_logical = None
            for e in pygame.event.get():
                self.handle_event(e)
            self.draw_frame(self.now())
            self.present()
            self.clock.tick(K.FPS)
        pygame.quit()

    # ---------------------------------------------------------------- headless screenshot (for README and tests)
    def screenshot(self, path: str, frames: int = 8, scale: int = 2, mouse=None, click=None, now=1.0):
        """Render without opening a window loop; writes the 640x360 picture scaled by `scale`."""
        if mouse is not None:
            self.mouse_logical = mouse
        if click is not None:
            self.mouse_logical = click
            self.handle_click(*click)
        for i in range(frames):
            self.draw_frame(now + i / 60.0)
        pygame.image.save(pygame.transform.scale(self.logical, (K.LOGICAL_W * scale, K.LOGICAL_H * scale)), path)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tactical_game", description="Tactical game UI (milestones M1-M3 starter)")
    ap.add_argument("--human", default="TSB", help="your lineup: three distinct letters from T S C B M (default TSB)")
    ap.add_argument("--ai", default="TCM", help="AI lineup (default TCM)")
    ap.add_argument("--scale", type=int, default=2, help="initial window scale (default 2 = 1280x720)")
    ap.add_argument("--demo", action="store_true", help="start in the mid-game demo state (damage, score, capture pips)")
    ap.add_argument("--view", choices=("diamond", "front"), default="diamond", help="start in the diamond view (default) or the front view")
    ap.add_argument("--screenshot", metavar="PNG", help="render one frame to a PNG and exit (no window needed)")
    args = ap.parse_args(argv)
    try:
        app = App(args.human.upper(), args.ai.upper(), args.scale, args.demo, args.view == "front")
    except ValueError as err:
        print("error:", err, file=sys.stderr)
        return 2
    if args.screenshot:
        app.screenshot(args.screenshot)
        return 0
    app.run()
    return 0
