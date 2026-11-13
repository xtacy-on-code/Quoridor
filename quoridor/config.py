"""Game constants shared by every module."""

SIZE = 9                 # the board is SIZE x SIZE cells
WALLS_PER_PLAYER = 10    # each player starts with this many walls
MAX_PLIES = 200          # a game with this many moves is called a draw

# Player 0 starts at the bottom and races to the top row.
# Player 1 starts at the top and races to the bottom row.
START = [(SIZE - 1, SIZE // 2), (0, SIZE // 2)]
GOAL_ROW = [0, SIZE - 1]

# Up, down, left, right as (row change, col change)
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
