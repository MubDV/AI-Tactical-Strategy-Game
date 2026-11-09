"""The interface panels around the board (layout from Team Supporting Document 7.3)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame

from . import art_terrain as T
from . import constants as K
from . import font
from .art import Art, team_palette
from .gfx import mix, new_surface, shade
from .stub import (ATTACK_TEXT, BASES, HOLD_ACTIONS, MAX_HP, MOVE, NAMES, PLY_LIMIT, WIN_POINTS, Direction,
                   GameState, Side, Terrain, Unit, UnitType, is_base, terrain_at)
from .view import View

DIM = K.TEXT_DIM
TXT = K.TEXT
SHADOW = (4, 6, 14)


@dataclass
class Button:
    key: str
    label: str
    rect: pygame.Rect
    enabled: bool = True
    hotkey: str = ""


def hp_color(frac: float):
    return (96, 214, 110) if frac > 0.6 else (244, 200, 70) if frac > 0.3 else (240, 86, 78)


class Hud:
    def __init__(self, art: Art):
        self.art = art
        self.front_view = False                                  # set by the app: which view the VIEW button will switch to
        self.can_change_view = True
        self._panels = {}
        self.mini = {
            Terrain.OPEN: pygame.transform.scale(T.make_ground_tile("grass", 0, 2), (30, 15)),
            Terrain.COVER: pygame.transform.scale(T.make_ground_tile("forest", 0, 1), (30, 15)),
            Terrain.WALL: pygame.transform.scale(T.make_ground_tile("rock", 0, 1), (30, 15)),
        }
        self.pine_icon = pygame.transform.scale(art.pines[0][0], (13, 20))
        self.rock_icon = pygame.transform.scale(art.rocks[0][0], (28, 31))

    # ---------------------------------------------------------------- building blocks
    def panel(self, dst, rect, title: Optional[str] = None, accent=None, alpha=236):
        x, y, w, h = rect
        key = (w, h, title, accent, alpha)
        if key not in self._panels:
            s = new_surface(w + 1, h + 1)
            pygame.draw.rect(s, (0, 0, 6, 110), (1, 1, w, h), border_radius=4)
            pygame.draw.rect(s, (*K.PANEL, alpha), (0, 0, w, h), border_radius=4)
            for i in range(9):                                                       # soft light at the top
                pygame.draw.line(s, (120, 150, 230, 16 - i * 2), (3, 1 + i), (w - 4, 1 + i))
            pygame.draw.rect(s, (*K.PANEL_EDGE, 255), (0, 0, w, h), 1, border_radius=4)
            pygame.draw.line(s, (*K.PANEL_EDGE_DIM, 255), (3, 2), (w - 4, 2))
            if title:
                pygame.draw.line(s, (*K.PANEL_EDGE_DIM, 255), (4, 13), (w - 5, 13))
                if accent:
                    pygame.draw.rect(s, (*accent, 255), (4, 4, 2, 7))
                s.blit(font.render(title, DIM, 1), (9 if accent else 6, 4))
            self._panels[key] = s
        dst.blit(self._panels[key], (x, y))

    def text(self, dst, s, x, y, color=TXT, scale=1, anchor="topleft", shadow=True):
        return font.draw(dst, s, (x, y), color, scale, SHADOW if shadow else None, anchor)

    def bar(self, dst, x, y, w, h, frac, color=None):
        frac = max(0.0, min(1.0, frac))
        pygame.draw.rect(dst, (8, 10, 20), (x - 1, y - 1, w + 2, h + 2))
        pygame.draw.rect(dst, (38, 44, 66), (x, y, w, h))
        fill = int(round(w * frac))
        if fill:
            col = color or hp_color(frac)
            pygame.draw.rect(dst, col, (x, y, fill, h))
            pygame.draw.rect(dst, (255, 255, 255), (x, y, fill, 1))
            pygame.draw.rect(dst, shade(col, 0.6), (x, y + h - 1, fill, 1))

    def side_icon(self, dst, side: Side, cx: int, cy: int, r: int = 5):
        P = team_palette(side)
        if side == Side.HUMAN:
            pygame.draw.circle(dst, P["deep"], (cx, cy), r + 1)
            pygame.draw.circle(dst, P["main"], (cx, cy), r)
            pygame.draw.circle(dst, P["light"], (cx, cy), r, 1)
            pygame.draw.circle(dst, P["deep"], (cx, cy), max(1, r - 3))
        else:
            for rr, col in ((r + 2, P["deep"]), (r + 1, P["main"]), (r - 1, P["deep"])):
                pygame.draw.polygon(dst, col, [(cx, cy - rr), (cx + rr, cy), (cx, cy + rr), (cx - rr, cy)])

    # ---------------------------------------------------------------- top bar
    def top_bar(self, dst, state: GameState, view: View, now: float):
        x, y, w, h = K.RECT_TOPBAR
        pygame.draw.rect(dst, (*K.PANEL,), (0, 0, w, h))
        pygame.draw.line(dst, K.PANEL_EDGE, (0, h - 1), (w, h - 1))
        pygame.draw.line(dst, (8, 10, 22), (0, h), (w, h))
        # turn banner
        side = state.side_to_move
        P = team_palette(side)
        chip = pygame.Rect(6, 4, 112, 20)
        pygame.draw.rect(dst, P["deep"], chip, border_radius=4)
        pygame.draw.rect(dst, P["main"], chip.inflate(-2, -2), border_radius=3)
        pygame.draw.line(dst, P["light"], (chip.x + 4, chip.y + 2), (chip.right - 5, chip.y + 2))
        pygame.draw.rect(dst, P["light"], chip, 1, border_radius=4)
        self.side_icon(dst, side, chip.x + 13, chip.centery, 4)
        label = "YOUR TURN" if side == Side.HUMAN else "AI TURN"
        self.text(dst, label, chip.x + 24, chip.y + 6, (255, 255, 255))
        # scores and capture pips
        self._score_block(dst, 196, Side.HUMAN, state)
        self.text(dst, "VS", 322, 10, DIM, anchor="midtop")
        self._score_block(dst, 346, Side.AI, state)
        # action counter and gear
        self.text(dst, "ACTION", 600, 4, DIM, anchor="topright")
        self.text(dst, f"{state.action_no} / {PLY_LIMIT}", 600, 14, TXT, anchor="topright")
        self._gear(dst, 620, 14, now)

    def _score_block(self, dst, x, side: Side, state: GameState):
        P = team_palette(side)
        i = 0 if side == Side.HUMAN else 1
        pts = state.points[i]
        self.side_icon(dst, side, x + 5, 10, 4)
        self.text(dst, "YOU" if side == Side.HUMAN else "AI", x + 14, 4, P["light"])
        self.text(dst, f"{pts}/{WIN_POINTS}", x + 14 + (24 if side == Side.HUMAN else 18), 4, TXT)
        for k in range(WIN_POINTS):                                         # ten point cells
            col = P["main"] if k < pts else (34, 40, 62)
            pygame.draw.rect(dst, col, (x + 14 + k * 6, 16, 5, 5))
            if k < pts:
                pygame.draw.rect(dst, P["light"], (x + 14 + k * 6, 16, 5, 1))
        # capture pips: this side is trying to capture the other base
        hold, done = state.hold[i], state.captured[i]
        px = x + 80
        self.text(dst, "CAP", px, 4, DIM)
        for k in range(HOLD_ACTIONS):
            filled = done or k < hold
            col = (255, 214, 84) if done else P["main"]
            pygame.draw.rect(dst, col if filled else (34, 40, 62), (px + k * 7, 16, 6, 5))
            if filled:
                pygame.draw.rect(dst, (255, 255, 255, 80), (px + k * 7, 16, 6, 1))

    def _gear(self, dst, cx, cy, now):
        col = DIM
        for k in range(8):
            a = k * math.pi / 4
            pygame.draw.line(dst, col, (cx + math.cos(a) * 4, cy + math.sin(a) * 4), (cx + math.cos(a) * 7, cy + math.sin(a) * 7), 2)
        pygame.draw.circle(dst, col, (cx, cy), 5)
        pygame.draw.circle(dst, K.PANEL, (cx, cy), 2)

    # ---------------------------------------------------------------- left column
    def unit_button_rects(self) -> List[pygame.Rect]:
        x, y, w, h = K.RECT_LEFT
        bh = 54
        return [pygame.Rect(x, y + i * (bh + 4), w, bh) for i in range(3)]

    def left_column(self, dst, state: GameState, view: View, mouse, now: float):
        humans = sorted(state.units_of(Side.HUMAN), key=lambda u: u.id)
        for i, rect in enumerate(self.unit_button_rects()):
            u = humans[i] if i < len(humans) else None
            self._unit_button(dst, rect, u, i, view, mouse, now)
        # legend
        self.panel(dst, (6, 212, 118, 92), "LEGEND")
        rows = [("move", "Reachable"), ("attack", "Attack target"), ("burrow", "Burrow landing")]
        y = 218 + 12
        for kind, label in rows:
            self._swatch(dst, 12, y, kind)
            self.text(dst, label, 30, y + 1, TXT)
            y += 12
        self.side_icon(dst, Side.HUMAN, 17, y + 4, 4)
        self.text(dst, "You (ring)", 30, y + 1, TXT)
        y += 12
        self.side_icon(dst, Side.AI, 17, y + 4, 4)
        self.text(dst, "AI (diamond)", 30, y + 1, TXT)
        y += 12
        pygame.draw.polygon(dst, K.HUMAN["light"], [(18, y), (21, y + 4), (15, y + 4)])
        pygame.draw.rect(dst, K.HUMAN["light"], (17, y + 4, 2, 3))
        self.text(dst, "Tank facing", 30, y + 1, TXT)

    def _swatch(self, dst, x, y, kind):
        s = self.art.hl[kind]
        mini = pygame.transform.scale(s, (14, 7))
        dst.blit(mini, (x, y + 1))

    def _unit_button(self, dst, rect, u: Optional[Unit], index, view: View, mouse, now):
        hover = u is not None and rect.collidepoint(mouse) if mouse else False
        sel = u is not None and view.selected == u.id
        P = K.HUMAN
        bg = (26, 38, 70) if sel else (22, 32, 58) if hover else K.PANEL
        pygame.draw.rect(dst, (0, 0, 6), rect.move(1, 1), border_radius=4)
        pygame.draw.rect(dst, bg, rect, border_radius=4)
        edge = K.HL_SELECT if sel else (110, 140, 210) if hover else K.PANEL_EDGE
        pygame.draw.rect(dst, edge, rect, 2 if sel else 1, border_radius=4)
        if u is None:
            self.text(dst, "DEFEATED", rect.centerx, rect.centery - 3, (110, 70, 80), anchor="midtop")
            return
        # icon plate
        plate = pygame.Rect(rect.x + 5, rect.y + 6, 34, 34)
        pygame.draw.rect(dst, (12, 18, 36), plate, border_radius=3)
        pygame.draw.rect(dst, P["deep"], plate, 1, border_radius=3)
        icon = self.art.icon(u.type, u.side, 30)
        dst.blit(icon, (plate.x + 2, plate.y + 2 + (1 if sel and int(now * 3) % 2 else 0)))
        # text
        self.text(dst, NAMES[u.type].upper(), rect.x + 44, rect.y + 6, (255, 255, 255) if sel else TXT)
        mx = MAX_HP[u.type]
        self.text(dst, f"HP {u.hp}/{mx}", rect.x + 44, rect.y + 17, DIM)
        self.bar(dst, rect.x + 44, rect.y + 29, 68, 5, u.hp / mx)
        self.text(dst, f"MOVE {MOVE[u.type]}", rect.x + 44, rect.y + 39, DIM)
        # key hint
        self.text(dst, str(index + 1), rect.right - 7, rect.y + 5, (92, 108, 150), anchor="topright")

    # ---------------------------------------------------------------- right column
    def right_column(self, dst, state: GameState, view: View, now: float):
        focus = self._focus_unit(state, view)
        self._unit_card(dst, (516, 36, 118, 120), focus, state)
        self._terrain_card(dst, (516, 160, 118, 56), view)
        self._ai_panel(dst, (516, 220, 118, 80), state, now)

    def _focus_unit(self, state: GameState, view: View) -> Optional[Unit]:
        if view.hover is not None:
            u = state.unit_at(view.hover)
            if u:
                return u
        return state.unit_by_id(view.selected) if view.selected else None

    def _unit_card(self, dst, rect, u: Optional[Unit], state: GameState):
        x, y, w, h = rect
        if u is None:
            self.panel(dst, rect, "UNIT")
            for i, line in enumerate(font.wrap("Hover a unit to see its stats, or click one of yours.", w - 14)):
                self.text(dst, line, x + 7, y + 22 + i * 10, DIM)
            return
        P = team_palette(u.side)
        self.panel(dst, rect, "UNIT", P["main"])
        tag = "YOURS" if u.side == Side.HUMAN else "ENEMY"
        self.text(dst, tag, x + w - 6, y + 4, P["light"], anchor="topright")
        plate = pygame.Rect(x + 6, y + 18, 34, 34)
        pygame.draw.rect(dst, (12, 18, 36), plate, border_radius=3)
        pygame.draw.rect(dst, P["deep"], plate, 1, border_radius=3)
        dst.blit(self.art.icon(u.type, u.side, 30), (plate.x + 2, plate.y + 2))
        self.text(dst, NAMES[u.type].upper(), x + 46, y + 20, (255, 255, 255))
        mx = MAX_HP[u.type]
        self.text(dst, f"HP {u.hp}/{mx}", x + 46, y + 31, TXT)
        self.bar(dst, x + 46, y + 42, 66, 5, u.hp / mx)
        self.text(dst, f"MOVE {MOVE[u.type]}", x + 6, y + 56, TXT)
        extra = ""
        if u.type == UnitType.TANK:
            arrow = {Direction.N: "N", Direction.E: "E", Direction.S: "S", Direction.W: "W"}[u.facing]
            self.text(dst, f"FACING {arrow}", x + w - 6, y + 56, K.ACCENT, anchor="topright")
        elif u.type == UnitType.BOMBER:
            used = state.airstrike_used[0 if u.side == Side.HUMAN else 1]
            self.text(dst, "STRIKE USED" if used else "STRIKE READY", x + w - 6, y + 56,
                      (150, 150, 160) if used else K.ACCENT, anchor="topright")
        pygame.draw.line(dst, K.PANEL_EDGE_DIM, (x + 6, y + 67), (x + w - 7, y + 67))
        for i, line in enumerate(font.wrap(ATTACK_TEXT[u.type], w - 14)[:5]):
            self.text(dst, line, x + 7, y + 71 + i * 9, DIM)

    def _terrain_card(self, dst, rect, view: View):
        x, y, w, h = rect
        self.panel(dst, rect, "TERRAIN")
        cell = view.hover
        if cell is None:
            self.text(dst, "Hover a cell.", x + 7, y + 22, DIM)
            return
        t = terrain_at(cell)
        base = is_base(cell)
        name = {Terrain.OPEN: "OPEN GROUND", Terrain.COVER: "FOREST COVER", Terrain.WALL: "ROCKS"}[t]
        effect = {Terrain.OPEN: "No effect.", Terrain.COVER: "Hits on this cell do 1 less damage.",
                  Terrain.WALL: "Blocks movement. Attacks pass over it."}[t]
        if base is not None:
            name = "YOUR BASE" if base == Side.HUMAN else "ENEMY BASE"
            effect = "HQ on cover. Hold it 3 actions to capture."
        dst.blit(self.mini[t], (x + 6, y + 18))
        self.text(dst, name, x + 40, y + 19, (255, 255, 255))
        self.text(dst, f"CELL {cell[0]},{cell[1]}", x + 40, y + 29, DIM)
        for i, line in enumerate(font.wrap(effect, w - 14)[:2]):
            self.text(dst, line, x + 7, y + 38 + i * 9, DIM)

    def _ai_panel(self, dst, rect, state: GameState, now: float):
        x, y, w, h = rect
        self.panel(dst, rect, "AI", K.AI["main"])
        yy = y + 20
        for line in font.wrap("Waiting for your move.", w - 14):
            self.text(dst, line, x + 7, yy, TXT)
            yy += 10
        yy += 4
        for line in font.wrap("From M5 this panel shows the AI's last move and why.", w - 14)[:4]:
            self.text(dst, line, x + 7, yy, DIM)
            yy += 9

    # ---------------------------------------------------------------- message line and buttons
    def message_line(self, dst, view: View, now: float):
        rect = K.RECT_MESSAGE
        self.panel(dst, rect)
        col = {"info": TXT, "warn": K.ACCENT, "error": (255, 130, 120)}[view.message_kind]
        msg = view.message or "Click one of your units."
        age = now - view.message_t0
        if age < 0.25:                                    # fade-in so new messages are noticed
            col = mix(K.PANEL_EDGE, col, age / 0.25)
        lines = font.wrap(msg, rect[2] - 16)[:2]
        top = rect[1] + (7 if len(lines) == 1 else 3)
        for i, line in enumerate(lines):
            self.text(dst, line, rect[0] + 8, top + i * 9, col)

    def buttons(self, state: GameState, view: View) -> List[Button]:
        x, y, w, h = K.RECT_BUTTONS
        sel = state.unit_by_id(view.selected) if view.selected else None
        defs = []
        if sel is not None and sel.type == UnitType.BOMBER and not state.airstrike_used[0]:
            defs.append(("airstrike", "AIRSTRIKE", "A", True))
        defs.append(("view", "DIAMOND VIEW" if self.front_view else "FRONT VIEW", "V", self.can_change_view))
        defs.append(("restart", "RESTART", "R", True))
        bw, gap = 100, 10
        total = len(defs) * bw + (len(defs) - 1) * gap
        x0 = x + (w - total) // 2
        return [Button(k, label, pygame.Rect(x0 + i * (bw + gap), y + 3, bw, h - 6), en, hk)
                for i, (k, label, hk, en) in enumerate(defs)]

    def draw_buttons(self, dst, buttons: List[Button], mouse, pressed: bool):
        for b in buttons:
            hover = mouse is not None and b.rect.collidepoint(mouse) and b.enabled
            down = hover and pressed
            r = b.rect.move(0, 1 if down else 0)
            pygame.draw.rect(dst, (0, 0, 6), r.move(1, 1), border_radius=4)
            base = (36, 52, 96) if hover else (26, 38, 72)
            if not b.enabled:
                base = (22, 28, 44)
            pygame.draw.rect(dst, base, r, border_radius=4)
            pygame.draw.line(dst, (120, 150, 220) if hover else (80, 104, 160), (r.x + 4, r.y + 1), (r.right - 5, r.y + 1))
            pygame.draw.rect(dst, K.ACCENT if hover else K.PANEL_EDGE, r, 1, border_radius=4)
            col = (255, 255, 255) if hover else TXT if b.enabled else (90, 100, 130)
            self.text(dst, b.label, r.centerx - 5, r.centery - 4, col, anchor="midtop")
            if b.hotkey:
                self.text(dst, b.hotkey, r.right - 7, r.centery - 3, (110, 128, 176), anchor="midtop")

    def hint_line(self, dst):
        dim = (88, 104, 146)
        self.text(dst, "CLICK select / move    RIGHT-CLICK or ESC cancel    1-3 pick unit", 320, 336, dim, anchor="midtop", shadow=False)
        self.text(dst, "R reset    D demo state    V change view    I pixel scaling    F11 fullscreen    F1 debug", 320, 347, dim, anchor="midtop", shadow=False)

    def debug_overlay(self, dst, lines):
        w = max(font.text_width(l) for l in lines) + 8
        s = new_surface(w, len(lines) * 10 + 4)
        s.fill((0, 0, 0, 170))
        dst.blit(s, (2, 32))
        for i, l in enumerate(lines):
            font.draw(dst, l, (6, 34 + i * 10), (120, 255, 160))

    # ---------------------------------------------------------------- all together
    def draw(self, dst, state: GameState, view: View, mouse, now: float, pressed: bool = False):
        self.top_bar(dst, state, view, now)
        self.left_column(dst, state, view, mouse, now)
        self.right_column(dst, state, view, now)
        self.message_line(dst, view, now)
        self.draw_buttons(dst, self.buttons(state, view), mouse, pressed)
        self.hint_line(dst)
