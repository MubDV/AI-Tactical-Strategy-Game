"""Every UI number lives here (Team Supporting Document, Section 7.3-7.4).

Change a value here, never inside a drawing function.
"""
# Logical drawing surface. Everything is drawn at this size, then scaled up.
LOGICAL_W, LOGICAL_H = 640, 360
FPS = 60

# Isometric tiles and board placement (Section 7.4).
BOARD_N = 8
TW, TH = 48, 24          # tile diamond width and height
OX, OY = 320, 66         # screen position of the centre of tile (0, 0)
SLAB_DEPTH = 11          # thickness of the board "slab" under the tiles

# The second ("front") view: the same board seen from a steep angle with a little perspective.
# The camera glides between the diamond view and this one (see camera.py).
VIEW_SECONDS = 0.95      # length of the change-view animation
TOP_PITCH_DEG = 70.0     # camera elevation of the front view (30 = the diamond view, 90 = straight down)
TOP_PERSPECTIVE = 0.05  # 0 = no perspective; larger = the far edge of the board is narrower
TOP_TILE = 29.5          # width in pixels of a tile at the middle of the board in the front view
TOP_CY = 144.0           # screen y of the centre of the board in the front view
TOP_SLAB = 0.6           # thickness of the soil slab in the front view, in tiles

# Layout rectangles (x, y, w, h) from Section 7.3.
RECT_TOPBAR = (0, 0, 640, 28)
RECT_LEFT = (6, 36, 118, 170)
RECT_RIGHT = (516, 36, 118, 264)
RECT_MESSAGE = (128, 270, 384, 22)
RECT_BUTTONS = (128, 298, 384, 28)

# Directions in the order N, E, S, W as (d_row, d_col).
DIRS = ((-1, 0), (0, 1), (1, 0), (0, -1))
DIR_NAMES = ("N", "E", "S", "W")

# Palette --------------------------------------------------------------
BG_TOP = (11, 15, 30)
BG_BOTTOM = (24, 33, 62)
PANEL = (17, 25, 46)
PANEL_EDGE = (62, 84, 132)
PANEL_EDGE_DIM = (38, 52, 86)
TEXT = (226, 233, 247)
TEXT_DIM = (140, 155, 186)
ACCENT = (255, 205, 90)

HUMAN = {"main": (70, 136, 226), "dark": (38, 86, 168), "light": (140, 190, 255), "deep": (24, 52, 108)}
AI = {"main": (222, 80, 72), "dark": (160, 48, 46), "light": (255, 150, 136), "deep": (98, 28, 30)}

GRASS_A = (96, 160, 78)
GRASS_B = (88, 150, 72)
SOIL_LEFT = (126, 90, 60)
SOIL_RIGHT = (90, 62, 44)

HL_MOVE = (90, 225, 130)
HL_ATTACK = (255, 90, 84)
HL_BURROW = (178, 120, 255)
HL_HOVER = (255, 255, 255)
HL_SELECT = (255, 214, 84)

# Unit display data (name, HP, MOVE, attack text) -- placeholders until rules exist.
UNIT_INFO = {
    "T": ("Tank", 12, 2, "1st or 2nd cell ahead"),
    "S": ("Sniper", 5, 2, "Any enemy within 5"),
    "C": ("Scout", 8, 3, "Adjacent cell"),
    "B": ("Bomber", 6, 2, "Missile 1-2 cells, airstrike"),
    "M": ("Miner", 7, 1, "Adjacent, burrow 1-2"),
}
