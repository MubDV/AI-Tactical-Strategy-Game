"""Draws the board: ground, highlights, terrain props and units in painter order (Q3).

Everything goes through the shared camera (camera.py / projection.py), so the same code draws the diamond view, the
front view and every step of the animation between them. In the diamond view the original pre-drawn art is blitted
unscaled, exactly as before. In other views the art is scaled to the local tile size, and the pieces that are drawn
differently from above (Tank, Bomber, mountains, HQ) cross-fade from one picture to the other mid-animation.
"""
from __future__ import annotations

import math
from typing import List, Tuple

import pygame

from . import art_terrain as T
from . import art_top as TOP
from . import art_units as AU
from . import constants as K
from . import font
from . import projection as P
from .art import Art, team_palette
from .camera import smoothstep
from .gfx import new_surface, shade
from .projection import depth_key, grid_to_screen, tile_polygon
from .stub import BASES, BOARD_N, COVER, MAX_HP, WALLS, GameState, Side, Terrain, Unit, UnitType, terrain_at
from .view import View

HP_BAR_TOP = {UnitType.TANK: 36, UnitType.SNIPER: 40, UnitType.SCOUT: 40, UnitType.MINER: 40, UnitType.BOMBER: 46}
HP_BAR_TOP_FRONT = {UnitType.TANK: 22, UnitType.SNIPER: 26, UnitType.SCOUT: 26, UnitType.MINER: 26, UnitType.BOMBER: 33}
SHADOW = {UnitType.TANK: (30, 12), UnitType.SNIPER: (18, 8), UnitType.SCOUT: (18, 8),
          UnitType.MINER: (20, 8), UnitType.BOMBER: (22, 8)}
PINE_SPOTS = [(-10, -1), (9, -2), (0, -7)]
HL_STYLE = {"move": (K.HL_MOVE, 88, 235, 185, 70), "attack": (K.HL_ATTACK, 104, 235, 200, 55), "burrow": (K.HL_BURROW, 96, 235, 185, 70)}


def hp_color(frac: float):
    if frac > 0.6:
        return (96, 214, 110)
    if frac > 0.3:
        return (244, 200, 70)
    return (240, 86, 78)


def _lerp(a, b, t):
    return a + (b - a) * t


def _toward(poly, k):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in poly]


class BoardRenderer:
    def __init__(self, art: Art):
        self.art = art
        self._shadow_cache = {}
        self._white = {}
        self._fade = {}
        self._fade_t = 0.0
        self._outlines = {}
        self.cam = P.CAM
        self.w_sprite = 0.0                     # 0 = diamond-view art, 1 = front-view art

    # ---------------------------------------------------------------- camera helpers
    def _ratios(self, row, col):
        """Scale of diamond-view art and of front-view art at this spot of the board."""
        tp = self.cam.tile_px(row, col)
        return tp / K.TW, tp / K.TOP_TILE

    def _settled(self) -> bool:
        return self.cam.e in (0.0, 1.0)

    def _parts(self, iso, top, ri, rt):
        """(sprite, ratio, alpha) layers to draw, bottom first. `top` None means the diamond art is just scaled."""
        w = self.w_sprite
        if top is None or w <= 0.0:
            return [(iso, ri, 255)]
        if w >= 1.0:
            return [(top, rt, 255)]
        return [(iso, ri, 255), (top, rt, int(255 * w))]

    # ---------------------------------------------------------------- ground-plane drawing
    def _tile_fx(self, dst, cell, color, fill_a, border_a, alpha=255, rim=2):
        """A translucent tile highlight: soft fill, solid rim and a lighter inner rim."""
        poly = tile_polygon(*cell)
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
        w, h = int(max(xs)) - x0 + 4, int(max(ys)) - y0 + 4
        s = new_surface(w, h)
        pts = [(x - x0, y - y0) for x, y in poly]
        pygame.draw.polygon(s, (*color, fill_a), pts)
        pygame.draw.polygon(s, (*color, border_a), pts, rim)
        pygame.draw.polygon(s, (*shade(color, 1.35), min(255, fill_a + 70)), _toward(pts, 0.84), 1)
        if alpha != 255:
            s.set_alpha(alpha)
        dst.blit(s, (x0, y0))

    def _marker(self, dst, side: Side, pos, selected: bool):
        """Colour-blind-safe ground marker: humans get a ring (circle), the AI gets a diamond."""
        Pal = team_palette(side)
        cam = self.cam
        r0, c0 = pos
        col = Pal["main"] if not selected else (255, 255, 255)
        if side == Side.HUMAN:
            def ring(R):
                return [cam.ground(r0 + R * math.sin(a), c0 + R * math.cos(a)) for a in [i * math.pi / 14 for i in range(28)]]
            outer, mid = ring(0.45), ring(0.41)
            pts = outer
        else:
            ang = math.pi / 4 * cam.e                                   # a tile-aligned square in the diamond view, a diamond from above

            def quad(h):
                return [cam.ground(r0 + h * 1.4142 * math.sin(math.radians(45 + 90 * i) + ang),
                                   c0 + h * 1.4142 * math.cos(math.radians(45 + 90 * i) + ang)) for i in range(4)]
            h0 = 0.36 * (1 - 0.1 * cam.e)
            outer, mid = quad(h0), quad(h0 * 0.80)
            pts = outer
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, y0 = int(min(xs)) - 3, int(min(ys)) - 3
        s = new_surface(int(max(xs)) - x0 + 6, int(max(ys)) - y0 + 6)
        o = [(x - x0, y - y0 + 1) for x, y in outer]
        m = [(x - x0, y - y0 + 1) for x, y in mid]
        pygame.draw.polygon(s, (*Pal["main"], 70), o)
        pygame.draw.polygon(s, (*Pal["deep"], 255), o, 3)
        pygame.draw.polygon(s, (*col, 255), m, 2)
        if side == Side.HUMAN:
            pygame.draw.polygon(s, (*Pal["light"], 255), m, 1)
        dst.blit(s, (x0, y0))

    def facing_arrow(self, dst, pos, facing, side: Side):
        """An arrow on the tile edge in the Tank's facing direction (drawn flat on the ground)."""
        Pal = team_palette(side)
        cam = self.cam
        fe, fs = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}[int(facing)]
        pe, ps = -fs, fe
        r0, c0 = pos

        def pt(u, v):
            return cam.ground(r0 + (u * fs + v * ps), c0 + (u * fe + v * pe))

        head = [pt(0.52, 0), pt(0.33, 0.19), pt(0.33, -0.19)]
        shaft = [pt(0.33, 0.045), pt(0.22, 0.045), pt(0.22, -0.045), pt(0.33, -0.045)]
        pygame.draw.polygon(dst, Pal["deep"], head)
        pygame.draw.polygon(dst, (255, 255, 255), [pt(0.46, 0), pt(0.36, 0.11), pt(0.36, -0.11)])
        pygame.draw.polygon(dst, Pal["light"], shaft)

    # ---------------------------------------------------------------- pieces
    def _shadow(self, utype: UnitType, alpha: int, ratio: float):
        w, h = SHADOW[utype]
        e = self.cam.e
        w = max(6, int(round(w * ratio * _lerp(1.0, 1.05, e))))
        h = max(4, int(round(h * ratio * _lerp(1.0, 1.9, e))))
        key = (utype, alpha, w, h)
        if key not in self._shadow_cache:
            s = new_surface(w + 2, h + 2)
            pygame.draw.ellipse(s, (0, 0, 10, alpha), (1, 1, w, h))
            self._shadow_cache[key] = s
        return self._shadow_cache[key]

    def _outline_for(self, spr: pygame.Surface, color=(255, 255, 255), thickness=1):
        if not self._settled():
            return self.art.outline_of(spr, color, thickness)
        key = (id(spr), color, thickness)
        if key not in self._outlines:
            self._outlines[key] = (spr, self.art.outline_of(spr, color, thickness))
        return self._outlines[key][1]

    def draw_unit(self, dst, u: Unit, pos: Tuple[float, float], now: float, view: View,
                  selected=False, hovered=False, alpha=255, rise=0.0):
        """Draws one unit with its shadow and ground marker. Returns (cx, cy, ratio) for the overlays."""
        art = self.art
        cam = self.cam
        cxf, cyf = grid_to_screen(*pos)
        cx, cy = int(round(cxf)), int(round(cyf))
        ri, rt = self._ratios(*pos)
        iso = art.unit(u.type, u.side, u.facing)
        top = art.unit_top(u.type, u.side, u.facing)
        phase = (sum(map(ord, u.id)) % 7) * 0.9
        bob = 0
        if u.type == UnitType.BOMBER:
            bob = int(round(math.sin(now * 3.0 + phase) * 1.4 * ri))
        elif u.type != UnitType.TANK and math.sin(now * 2.4 + phase) > 0.55:
            bob = -1
        # ground: shadow, marker, tank facing arrow
        sh = self._shadow(u.type, 70 if u.type != UnitType.BOMBER else 50, ri)
        dst.blit(sh, (cx - sh.get_width() // 2, cy - sh.get_height() // 2 + int(round(3 * ri))))
        self._marker(dst, u.side, pos, selected)
        if u.type == UnitType.TANK:
            self.facing_arrow(dst, pos, u.facing, u.side)
        layer, ox, oy = dst, 0, 0
        if alpha < 255:
            layer = new_surface(120, 130)
            ox, oy = cx - 60, cy - 90
        flashing = any(f.unit_id == u.id for f in view.flashes)
        settled = self._settled()
        main = None
        for spr_t, ratio, a in self._parts(iso, top, ri, rt):
            spr, (ax, ay) = art.scaled(spr_t, ratio, settled)
            px_, py_ = cx - ax - ox, cy - ay + bob - oy - int(rise)
            if selected and main is None:
                layer.blit(self._outline_for(spr), (px_ - 2, py_ - 2))
            if a < 255:
                spr = spr.copy()
                spr.set_alpha(a)
            layer.blit(spr, (px_, py_))
            if flashing:
                mask = pygame.mask.from_surface(spr, 100).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
                layer.blit(mask, (px_, py_))
            main = spr
        if u.type == UnitType.BOMBER:
            flip = -1 if u.side == Side.AI else 1
            lift = (AU.HELI_LIFT + 12) * ri
            if self.w_sprite < 0.5:
                AU.draw_rotor(layer, cx - ox + (0 if u.side == Side.HUMAN else -1) * ri, cy - oy + bob - lift - int(rise), now + phase, ri)
                AU.draw_tail_rotor(layer, cx - ox - 29 * flip * ri, cy - oy + bob - (AU.HELI_LIFT + 7) * ri - int(rise), now + phase, ri)
            else:
                hx, hy = TOP.ROTOR_HUB
                tx, ty = TOP.TAIL_HUB
                TOP.draw_rotor_top(layer, cx - ox + hx * rt, cy - oy + bob + hy * rt - int(rise), now + phase, rt)
                AU.draw_tail_rotor(layer, cx - ox + tx * flip * rt, cy - oy + bob + ty * rt - int(rise), now + phase, rt)
        if layer is not dst:
            layer.set_alpha(alpha)
            dst.blit(layer, (ox, oy))
        return cx, cy, ri

    def _bar_offset(self, u: Unit, ri: float) -> float:
        return _lerp(HP_BAR_TOP[u.type] * ri, HP_BAR_TOP_FRONT[u.type], self.w_sprite)

    def draw_hp_bar(self, dst, u: Unit, cx: int, cy: int, ri: float, hovered: bool, now: float, rise=0.0):
        top = int(cy - self._bar_offset(u, ri) - int(rise))
        w, h = int(round(22 - 4 * self.w_sprite)), int(round(5 - self.w_sprite))
        x = cx - w // 2
        frac = max(0.0, min(1.0, u.hp / MAX_HP[u.type]))
        Pal = team_palette(u.side)
        pygame.draw.rect(dst, (8, 10, 20), (x - 1, top - 1, w + 2, h + 2))
        pygame.draw.rect(dst, (38, 44, 66), (x, top, w, h))
        fill = max(1, int(round(w * frac))) if u.hp > 0 else 0
        col = hp_color(frac)
        if fill:
            pygame.draw.rect(dst, col, (x, top, fill, h))
            pygame.draw.rect(dst, (255, 255, 255), (x, top, fill, 1))
            pygame.draw.rect(dst, tuple(int(v * 0.6) for v in col), (x, top + h - 1, fill, 1))
        pygame.draw.rect(dst, Pal["main"], (x - 3, top - 1, 2, h + 2))        # team tick
        for i in range(1, MAX_HP[u.type]):                                      # one divider per HP point
            dx = int(round(w * i / MAX_HP[u.type]))
            if 0 < dx < w and MAX_HP[u.type] <= 12:
                pygame.draw.line(dst, (8, 10, 20), (x + dx, top), (x + dx, top + h - 1), 1)
        if hovered:
            font.draw(dst, f"{u.hp}/{MAX_HP[u.type]}", (cx, top - 9), (255, 255, 255), shadow=(0, 0, 0), anchor="midtop")

    # ---------------------------------------------------------------- props
    def _blit_prop(self, dst, iso, top, cx, cy, ri, rt, alpha=255):
        settled = self._settled()
        for spr_t, ratio, a in self._parts(iso, top, ri, rt):
            spr, (ax, ay) = self.art.scaled(spr_t, ratio, settled)
            aa = min(a, alpha)
            if aa < 255:
                spr = spr.copy()
                spr.set_alpha(aa)
            dst.blit(spr, (int(cx - ax), int(cy - ay)))

    def _draw_hq(self, dst, side: Side, cell, X, Y, now, alpha):
        art = self.art
        ri, rt = self._ratios(*cell)
        Pal = team_palette(side)
        w = self.w_sprite
        if self.cam.is_iso:                                            # the original drawing, untouched
            spr, (ax, ay) = art.hq[side]
            if alpha < 255:
                spr.set_alpha(alpha)
            dst.blit(spr, (int(X - ax), int(Y - ay)))
            if alpha < 255:
                spr.set_alpha(255)
            T.draw_hq_flag(dst, X, Y, Pal, now)
            return
        for variant, ratio, a in ((0, ri, 255 if w < 1.0 else 0), (1, rt, int(255 * w))):
            if a <= 0:
                continue
            canvas = new_surface(90, 90)
            cxc, cyc = 45, 62
            if variant == 0:
                spr, (ax, ay) = art.hq[side]
                canvas.blit(spr, (cxc - ax, cyc - ay))
                T.draw_hq_flag(canvas, cxc, cyc, Pal, now)
            else:
                spr, (ax, ay) = art.hq_top[side]
                canvas.blit(spr, (cxc - ax, cyc - ay))
                TOP.draw_hq_flag_top(canvas, cxc, cyc, Pal, now)
            if abs(ratio - 1.0) >= 0.02:
                nw = max(1, int(round(90 * ratio)))
                canvas = pygame.transform.smoothscale(canvas, (nw, nw))
                cxc, cyc = int(round(cxc * nw / 90)), int(round(cyc * nw / 90))
            aa = min(a, alpha)
            if aa < 255:
                canvas.set_alpha(aa)
            dst.blit(canvas, (int(X - cxc), int(Y - cyc)))

    # ---------------------------------------------------------------- frame
    def draw(self, dst: pygame.Surface, state: GameState, view: View, now: float):
        art = self.art
        cam = self.cam = P.CAM
        self.w_sprite = smoothstep((cam.e - 0.3) / 0.4)
        dst.blit(art.board(cam), (0, 0))
        hover = view.hover
        opts = view.options
        pulse = 0.5 + 0.5 * math.sin(now * 5.0)

        # 1. ground highlights (below everything standing on the board)
        if opts:
            for cell in opts.moves:
                self._tile_fx(dst, cell, K.HL_MOVE, 88, 235, int(185 + 70 * pulse))
            for cell in opts.burrows:
                self._tile_fx(dst, cell, K.HL_BURROW, 96, 235, int(185 + 70 * pulse))
            for cell in opts.attacks:
                self._tile_fx(dst, cell, K.HL_ATTACK, 104, 235, int(200 + 55 * pulse))
        sel_unit = state.unit_by_id(view.selected) if view.selected else None
        if sel_unit:
            self._tile_fx(dst, sel_unit.pos, K.HL_SELECT, 46, 255, int(210 + 45 * pulse), rim=3)
        if hover is not None:
            self._tile_fx(dst, hover, K.HL_HOVER, 34, 200, 230)

        # 2. everything that stands up, in painter order.
        # Tall props (rocks, trees) fade when something they would hide stands, or is highlighted, behind them.
        fade = self._occlusion_fade(state, view, now)
        items: List[Tuple[tuple, callable]] = []

        for r in range(BOARD_N):
            for c in range(BOARD_N):
                cell = (r, c)
                cx, cy = grid_to_screen(r, c)
                ri, rt = self._ratios(r, c)
                key = depth_key(r, c)
                if cell in WALLS:
                    i = (r * 3 + c) % len(art.rocks)
                    items.append((key + (0,), lambda i=i, X=cx, Y=cy, ri=ri, rt=rt, a=fade.get(cell, 255):
                                  self._blit_prop(dst, art.rocks[i], art.rocks_top[i], X, Y, ri, rt, a)))
                    continue
                if cell in BASES.values():
                    side = Side.HUMAN if BASES[Side.HUMAN] == cell else Side.AI
                    items.append((key + (0,), lambda sd=side, cl=cell, X=cx, Y=cy: self._draw_hq(dst, sd, cl, X, Y, now, 255)))
                elif cell in COVER:
                    for i, (dx, dy) in enumerate(PINE_SPOTS):
                        pine = art.pines[(r + c + i) % 3]
                        items.append((key + (0 if i == 2 else -0.5,),
                                      lambda p=pine, X=cx + dx * ri, Y=cy + dy * ri, ri=ri, a=fade.get(cell, 255):
                                      self._blit_prop(dst, p, None, X, Y, ri, ri, a)))
                    items.append((key + (2,), lambda X=cx - 13 * ri, Y=cy + 7 * ri, ri=ri:
                                  self._blit_prop(dst, art.bush, None, X, Y, ri, ri)))

        for u in state.units:
            pos = view.slides[u.id].position(now) if u.id in view.slides else (float(u.pos[0]), float(u.pos[1]))
            items.append((depth_key(*pos) + (1,), lambda u=u, p=pos: self._draw_unit_full(dst, u, p, now, view, state)))
        for g in view.ghosts:
            k = (now - g.t0) / g.life
            p = (float(g.unit.pos[0]), float(g.unit.pos[1]))
            items.append((depth_key(*p) + (1,),
                          lambda g=g, k=k, p=p: self.draw_unit(dst, g.unit, p, now, view, alpha=int(255 * (1 - k)), rise=6 * k)))
        items.sort(key=lambda it: it[0])
        for _, fn in items:
            fn()

        # 3. overlays: attack reticles, capture pips, floating text
        if opts:
            for cell in opts.attacks:
                self._reticle(dst, cell, now)
        self._capture_pips(dst, state)
        for t in view.texts:
            k = (now - t.t0) / t.life
            x, y = t.pos
            y -= 16 * (1 - (1 - k) ** 2)
            s = font.render(t.text, t.color, 2, (0, 0, 0))
            if k > 0.6:
                s = s.copy()
                s.set_alpha(int(255 * (1 - (k - 0.6) / 0.4)))
            dst.blit(s, s.get_rect(midbottom=(int(x), int(y))))

    # ---------------------------------------------------------------- occlusion fading
    def _occlusion_fade(self, state: GameState, view: View, now: float):
        """Target alpha per tall prop cell, eased over time so props fade smoothly instead of popping."""
        interest = []                                          # (depth, screen rect) of things the player must see
        for u in state.units:
            pos = view.slides[u.id].position(now) if u.id in view.slides else (float(u.pos[0]), float(u.pos[1]))
            cx, cy = grid_to_screen(*pos)
            r, _ = self._ratios(*pos)
            if u.type == UnitType.BOMBER:
                rect = pygame.Rect(int(cx - 22 * r), int(cy - 56 * r), int(44 * r), int(66 * r))
            else:
                rect = pygame.Rect(int(cx - 14 * r), int(cy - 46 * r), int(28 * r), int(56 * r))
            interest.append((depth_key(*pos)[0], rect))
        cells = set()
        if view.options:
            cells |= set(view.options.moves) | set(view.options.attacks) | set(view.options.burrows)
        if view.hover is not None:
            cells.add(view.hover)
        for cell in cells:
            cx, cy = grid_to_screen(*cell)
            r, _ = self._ratios(*cell)
            interest.append((depth_key(*cell)[0], pygame.Rect(int(cx - 22 * r), int(cy - 12 * r), int(44 * r), int(24 * r))))
        dt = max(0.0, min(0.1, now - self._fade_t)) if self._fade_t else 0.0
        self._fade_t = now
        k = min(1.0, dt * 14.0)
        out = {}
        for cell in list(WALLS) + list(COVER):
            cx, cy = grid_to_screen(*cell)
            r, _ = self._ratios(*cell)
            if cell in WALLS:
                zone, low = pygame.Rect(int(cx - 22 * r), int(cy - 34 * r), int(44 * r), int(46 * r)), 140
            else:
                zone, low = pygame.Rect(int(cx - 20 * r), int(cy - 30 * r), int(40 * r), int(34 * r)), 165
            depth = depth_key(*cell)[0]
            hides = any(d < depth - 1e-6 and zone.colliderect(rect) for d, rect in interest)
            target = low if hides else 255
            cur = self._fade.get(cell, 255.0)
            cur += (target - cur) * k
            self._fade[cell] = cur
            out[cell] = int(round(cur))
        return out

    # ---------------------------------------------------------------- unit overlays
    def _draw_unit_full(self, dst, u, pos, now, view, state):
        sel = (view.selected == u.id)
        hov = (view.hover is not None and view.hover == u.pos and u.id not in view.slides)
        cx, cy, ri = self.draw_unit(dst, u, pos, now, view, selected=sel, hovered=hov)
        self.draw_hp_bar(dst, u, cx, cy, ri, hov or sel, now)
        if sel:
            by = int(cy - self._bar_offset(u, ri) - 12 + int(round(math.sin(now * 6.0) * 2)))
            pygame.draw.polygon(dst, (10, 12, 24), [(cx - 5, by - 1), (cx + 5, by - 1), (cx, by + 6)])
            pygame.draw.polygon(dst, K.HL_SELECT, [(cx - 4, by), (cx + 4, by), (cx, by + 4)])

    def _reticle(self, dst, cell, now):
        cx, cy = grid_to_screen(*cell)
        r, _ = self._ratios(*cell)
        cx, cy = int(cx), int(cy) + 1
        g = int(round((5 + math.sin(now * 8.0)) * r))
        col = (255, 236, 230)
        for dx in (-1, 1):
            pygame.draw.line(dst, col, (cx + dx * (g + int(4 * r)), cy), (cx + dx * (g + int(9 * r)), cy), 1)
        for dy in (-1, 1):
            pygame.draw.line(dst, col, (cx, cy + dy * (g // 2 + int(2 * r))), (cx, cy + dy * (g // 2 + int(5 * r))), 1)
        pygame.draw.circle(dst, col, (cx, cy), 1)

    def _capture_pips(self, dst, state: GameState):
        """Three pips beside each base that fill as the hold count rises (spec 7.6)."""
        for i, side in enumerate((Side.HUMAN, Side.AI)):
            base = BASES[side]
            holder = Side.AI if side == Side.HUMAN else Side.HUMAN          # who is trying to capture this base
            hold = state.hold[0 if holder == Side.HUMAN else 1]
            done = state.captured[0 if holder == Side.HUMAN else 1]
            cx, cy = grid_to_screen(*base)
            r, _ = self._ratios(*base)
            Pal = team_palette(holder)
            x0, y0 = int(cx) - 14, int(cy + 13 * r)
            pill = pygame.Rect(x0 - 3, y0 - 3, 34, 10)
            pygame.draw.rect(dst, (12, 18, 38), pill, border_radius=3)
            pygame.draw.rect(dst, Pal["deep"] if not done else (150, 120, 40), pill, 1, border_radius=3)
            for k in range(3):
                filled = done or k < hold
                col = (255, 214, 84) if done else Pal["main"]
                pygame.draw.rect(dst, col if filled else (36, 44, 70), (x0 + k * 10, y0, 9, 4))
                if filled:
                    pygame.draw.rect(dst, Pal["light"] if not done else (255, 244, 180), (x0 + k * 10, y0, 9, 1))
