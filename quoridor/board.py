"""Quoridor rules: the board state, pawn moves, walls and legality.

Coordinates
-----------
Cells are (row, col) with (0, 0) at the top-left.

A wall is 2 cells long and sits in the groove between cells. We store it by
its *anchor*: the groove intersection at the bottom-right corner of cell
(row, col). So anchors go from (0, 0) to (SIZE-2, SIZE-2).

- Horizontal wall at (r, c): blocks moving between rows r and r+1,
  in columns c and c+1.
- Vertical wall at (r, c): blocks moving between columns c and c+1,
  in rows r and r+1.

Moves
-----
A move is a plain tuple:
    ("move", row, col)          move your pawn to (row, col)
    ("wall", "h" or "v", r, c)  place a wall at anchor (r, c)
"""

from quoridor.config import SIZE, WALLS_PER_PLAYER, START, GOAL_ROW, DIRECTIONS
from quoridor import pathfinding


class GameState:
    def __init__(self):
        self.pawns = list(START)
        self.walls_left = [WALLS_PER_PLAYER, WALLS_PER_PLAYER]
        self.h_walls = set()
        self.v_walls = set()
        self.turn = 0          # whose turn it is: 0 or 1
        self.history = []      # list of (move, previous pawn position) for undo

    def copy(self):
        s = GameState()
        s.pawns = list(self.pawns)
        s.walls_left = list(self.walls_left)
        s.h_walls = set(self.h_walls)
        s.v_walls = set(self.v_walls)
        s.turn = self.turn
        s.history = list(self.history)
        return s

    # ------------------------------------------------------------------
    # Walls blocking a single step
    # ------------------------------------------------------------------
    def is_blocked(self, r, c, dr, dc):
        """True if a wall sits between (r, c) and (r+dr, c+dc)."""
        if dr == 1:      # stepping down crosses the groove under row r
            return (r, c) in self.h_walls or (r, c - 1) in self.h_walls
        if dr == -1:     # stepping up crosses the groove above row r
            return (r - 1, c) in self.h_walls or (r - 1, c - 1) in self.h_walls
        if dc == 1:      # stepping right crosses the groove right of col c
            return (r, c) in self.v_walls or (r - 1, c) in self.v_walls
        # stepping left crosses the groove left of col c
        return (r, c - 1) in self.v_walls or (r - 1, c - 1) in self.v_walls

    def can_step(self, r, c, dr, dc):
        """True if a pawn on (r, c) could step one cell in direction (dr, dc)."""
        nr, nc = r + dr, c + dc
        if nr < 0 or nr >= SIZE or nc < 0 or nc >= SIZE:
            return False
        return not self.is_blocked(r, c, dr, dc)

    # ------------------------------------------------------------------
    # Pawn moves (including jumps)
    # ------------------------------------------------------------------
    def pawn_moves(self, player=None):
        """All cells the pawn can move to this turn.

        Normal move: one step up/down/left/right, not through a wall.
        If the opponent is on that cell, you jump straight over them.
        If a wall or the board edge is behind them, you may go diagonally
        to either side of them instead.
        """
        if player is None:
            player = self.turn
        r, c = self.pawns[player]
        opp = self.pawns[1 - player]
        result = []
        for dr, dc in DIRECTIONS:
            if not self.can_step(r, c, dr, dc):
                continue
            nr, nc = r + dr, c + dc
            if (nr, nc) != opp:
                result.append((nr, nc))
                continue
            # The opponent is right there: try to jump straight over.
            if self.can_step(nr, nc, dr, dc):
                result.append((nr + dr, nc + dc))
            else:
                # Blocked behind them: side-step diagonally.
                for sr, sc in ((dc, dr), (-dc, -dr)):
                    if self.can_step(nr, nc, sr, sc):
                        result.append((nr + sr, nc + sc))
        return result

    # ------------------------------------------------------------------
    # Walls
    # ------------------------------------------------------------------
    def wall_fits(self, ori, r, c):
        """Geometry only: inside the board, no overlap, no crossing."""
        if r < 0 or r > SIZE - 2 or c < 0 or c > SIZE - 2:
            return False
        if ori == "h":
            if (r, c) in self.h_walls or (r, c - 1) in self.h_walls or (r, c + 1) in self.h_walls:
                return False
            return (r, c) not in self.v_walls          # would cross a vertical wall
        if (r, c) in self.v_walls or (r - 1, c) in self.v_walls or (r + 1, c) in self.v_walls:
            return False
        return (r, c) not in self.h_walls              # would cross a horizontal wall

    def place_wall_temp(self, ori, r, c):
        (self.h_walls if ori == "h" else self.v_walls).add((r, c))

    def remove_wall_temp(self, ori, r, c):
        (self.h_walls if ori == "h" else self.v_walls).discard((r, c))

    def is_legal_wall(self, ori, r, c, player=None):
        """A wall is legal if the player has walls left, it fits, and both
        players can still reach their goal row afterwards (checked with BFS)."""
        if player is None:
            player = self.turn
        if self.walls_left[player] <= 0:
            return False
        if not self.wall_fits(ori, r, c):
            return False
        self.place_wall_temp(ori, r, c)
        ok = pathfinding.has_path(self, 0) and pathfinding.has_path(self, 1)
        self.remove_wall_temp(ori, r, c)
        return ok

    def all_wall_spots(self):
        for ori in ("h", "v"):
            for r in range(SIZE - 1):
                for c in range(SIZE - 1):
                    yield ori, r, c

    # ------------------------------------------------------------------
    # Full move list, applying and undoing moves
    # ------------------------------------------------------------------
    def legal_moves(self):
        moves = [("move", r, c) for (r, c) in self.pawn_moves()]
        if self.walls_left[self.turn] > 0:
            for ori, r, c in self.all_wall_spots():
                if self.is_legal_wall(ori, r, c):
                    moves.append(("wall", ori, r, c))
        return moves

    def is_legal(self, move):
        if self.winner() is not None:
            return False
        if move[0] == "move":
            return (move[1], move[2]) in self.pawn_moves()
        return self.is_legal_wall(move[1], move[2], move[3])

    def apply(self, move):
        """Play a move for the player whose turn it is (no legality check)."""
        p = self.turn
        if move[0] == "move":
            self.history.append((move, self.pawns[p]))
            self.pawns[p] = (move[1], move[2])
        else:
            self.place_wall_temp(move[1], move[2], move[3])
            self.walls_left[p] -= 1
            self.history.append((move, None))
        self.turn = 1 - p

    def undo(self):
        move, old_pos = self.history.pop()
        self.turn = 1 - self.turn
        p = self.turn
        if move[0] == "move":
            self.pawns[p] = old_pos
        else:
            self.remove_wall_temp(move[1], move[2], move[3])
            self.walls_left[p] += 1

    def winner(self):
        """0 or 1 if someone reached their goal row, else None."""
        for p in (0, 1):
            if self.pawns[p][0] == GOAL_ROW[p]:
                return p
        return None

    def plies(self):
        return len(self.history)
