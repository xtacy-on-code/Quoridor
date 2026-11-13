"""Sizes and colours for the Pygame window."""

CELL = 62            # cell size in pixels
GAP = 14             # groove width (where walls go)
STEP = CELL + GAP
MARGIN = 45
BOARD_PX = 9 * CELL + 8 * GAP          # 670
BOARD_X = MARGIN
BOARD_Y = MARGIN

PANEL_X = BOARD_X + BOARD_PX + 40
PANEL_W = 300
WIDTH = PANEL_X + PANEL_W + 30
HEIGHT = BOARD_Y + BOARD_PX + MARGIN

FPS = 60

BG = (15, 17, 21)
BOARD_BG = (24, 27, 34)
CELL_COLOR = (36, 40, 51)
CELL_HOVER = (50, 56, 70)
TEXT = (230, 232, 236)
MUTED = (138, 145, 160)
LINE = (52, 57, 70)
WALL = (232, 220, 194)
ILLEGAL = (229, 72, 77)

# Player 0 (bottom, moves first) and player 1 (top)
PLAYER_COLORS = [(242, 165, 65), (76, 201, 240)]
PLAYER_NAMES = ["Amber", "Cyan"]

AI_MOVE_DELAY = 0.45   # seconds; keeps AI-vs-AI games watchable
