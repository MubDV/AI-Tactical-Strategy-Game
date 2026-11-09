# Tactical Strategy Game: UI starter (milestones M1 to M3, plus an M4 preview)

Person 1's starting point: a working window, the isometric projection and picking, and the board drawn
from a hard-coded stub state, with a polished HUD shell. All art is drawn by code, so there are no asset
files to install. Everything follows Section 7 of the Team Supporting Document.

## Run it

```
pip install -r requirements.txt      # pygame, numpy and pytest
python -m tactical_game              # opens a 1280x720 window
python -m tactical_game --human TSC --ai BMT --demo
python -m tactical_game --view front                 # start in the front view
python launcher.py                   # easiest: works from any folder, offers to install pygame/numpy, keeps errors on screen
play.bat                             # Windows: double-click (or run it) to start the game
python -m tactical_game --screenshot board.png      # one frame to a PNG, no window needed
python -m pytest -q                   # 63 tests (run from this folder)
```

Lineups are three distinct letters from T S C B M (Tank, Sniper, Scout, Bomber, Miner).
Python 3.11 or newer, pygame 2.5 or newer.

## Controls

| Input | Action |
| --- | --- |
| Click your unit, or keys 1 to 3 | Select it; its moves (green), targets (red) and burrow landings (purple) light up |
| Click a highlighted cell | Move, attack or burrow (demo rules, see below) |
| Right-click, Esc, or click empty ground | Clear the selection |
| R | Reset the position |
| D | Toggle the mid-game demo state (damage, score, capture pips) |
| I | Toggle integer scaling (sharp pixels) or fill-the-window scaling |
| V or the VIEW button | Change view: the camera glides from the diamond view up to a steep front view (and back) |
| F11 / F1 | Fullscreen / debug overlay (fps, mouse, cell) |

## What is done

| Milestone | Where | Check |
| --- | --- | --- |
| M1 window, logical surface, letterbox, clock | `ui/app.py`, `ui/scaling.py` | `tests/test_scaling.py`: round trip for 7 window sizes, clicks on the black bars are rejected |
| M2 projection and picking | `ui/camera.py`, `ui/projection.py` | `tests/test_projection.py` and `tests/test_camera.py`: all 64 cells round trip at every camera angle, points just inside each diamond edge, outside points give None, painter order, N/E/S/W directions on screen |
| M3 board from a stub state | `ui/stub.py`, `ui/renderer.py`, `ui/art*.py` | `tests/test_smoke.py`: six units in the final spawn slots, a frame draws, screenshots work |
| M4 preview (selection and highlights) | `ui/demo_rules.py` | Highlights follow the final rules table; this file is temporary |
| M6 preview (HUD shell) | `ui/hud.py` | Layout rectangles from Section 7.3 live in `ui/constants.py` |

## Files

```
tactical_game/
  __main__.py          python -m tactical_game
  ui/
    constants.py       every number: sizes, layout rectangles, palette (change values here only)
    camera.py          the one camera behind both views: diamond (yaw 45) and front (steep pitch + a little perspective), exact inverse
    projection.py      grid <-> screen, picking and painter order through the current camera
    ground.py          the board ground for any camera angle (warps the tile textures), soil slab, shadow
    scaling.py         letterbox viewport and window <-> logical mouse mapping
    stub.py            TEMPORARY model: Side, UnitType, Terrain, Direction, Unit, GameState
    demo_rules.py      TEMPORARY highlights and damage so you can click around (delete at M4)
    art.py             caches sprites, highlights, markers
    art_terrain.py     grass, forest floor, rock floor, board slab, mountains, pines, HQ and flag
    art_units.py       five unit types x two teams (Tank has four facings), helicopter rotor
    art_top.py         front-view sprites: Tank, Bomber, HQ and mountains redrawn from above; crisp scaling for the rest
    font.py            built-in 5x7 pixel font (no font file, no licence)
    gfx.py             colour maths, isometric box, outline helpers
    renderer.py        painter-order drawing, highlights, HP bars, floating text, props that fade when they hide something
    hud.py             top bar, unit buttons, legend, unit and terrain cards, AI panel, message line, buttons
    view.py            hover, selection, slide animation, floating text
    app.py             window, main loop, demo interaction, screenshot mode
tests/
```

## Look and feel decisions

* Humans stand on a circle ring and the AI on a diamond ring, so the teams differ by shape and not only by colour.
* Tall props (mountains, trees) fade to see-through when a unit or a highlighted cell is hidden behind them.
* Every wall and tree is drawn from the same painter order as the units, so a unit walks behind a mountain and in front of a tree correctly.
* HP bars show one divider per hit point. Hover a unit to see its HP number.
* The Tank draws its barrel in its facing direction and an arrow at its feet. Facing follows the final rule: a diagonal destination faces east or west by the column change.
* The 640x360 surface is scaled with nearest neighbour; integer scale is the default so every pixel is the same size.

## Next step (milestone M4): plug in the real rules

1. Replace the imports from `ui/stub.py` by `from tactical_game.domain import ...` in `renderer.py`, `hud.py`, `art*.py`, `view.py` and `app.py`. The class and enum names already match the Supporting Document (Side, UnitType, Terrain, Direction, Unit, GameState).
2. Delete `ui/demo_rules.py`. In `App.select`, build `Options` from `rules.legal_actions(state)` filtered to the selected unit: MOVE destinations become `moves`, ATTACK targets become `attacks`, BURROW landings become `burrows`.
3. In `App.click_cell`, send the matching `Action` to the controller instead of editing the state, and animate the unit with the `Slide` that is already there.
4. Keep the UI read-only: it never decides legality itself.

Art can be swapped later (M9) by replacing `art_terrain.py` and `art_units.py`; the renderer only needs a `(surface, anchor)` pair per sprite.

## The two views

The default is the diamond view, drawn exactly as before. Press **V** (or the VIEW button) and the camera glides up and round
into the front view: North is up, East is right, and the far edge of the board is a little narrower than the near edge. Standing
figures, pines and bushes are the same art scaled to the smaller tiles; the Tank, Bomber, HQ and mountains are redrawn from
above and cross-fade in during the move. Clicking works at every moment of the animation because picking uses the camera's
exact inverse.

Knobs (all in `ui/constants.py`): `TOP_PITCH_DEG` (camera elevation of the front view, 30 is the diamond view, 90 is straight down),
`TOP_PERSPECTIVE`, `TOP_TILE` (tile size), `TOP_CY` (vertical position), `TOP_SLAB` (soil thickness) and `VIEW_SECONDS`.
The change-view animation needs numpy; without it the game still runs in the diamond view and the button says so.
