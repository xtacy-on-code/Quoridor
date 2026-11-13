"""The AI players.

RandomAgent     - plays any legal move (baseline)
GreedyAgent     - always steps along its BFS shortest path, never places walls
MinimaxAgent    - full minimax to a fixed depth (no pruning)
AlphaBetaAgent  - minimax with alpha-beta pruning, move ordering, wall pruning
                  and (optionally) iterative deepening under a time limit

Every agent has choose_move(state) -> move and records search stats
(nodes visited, depth reached, time taken) for the experiments and the UI.
"""

import math
import random
import time

from quoridor import pathfinding
from quoridor.ai.evaluation import evaluate, WIN_SCORE
from quoridor.ai.movegen import candidate_moves


class Agent:
    name = "Agent"

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.nodes = 0
        self.depth_reached = 0
        self.last_time = 0.0
        self.last_score = 0

    def choose_move(self, state):
        raise NotImplementedError


class RandomAgent(Agent):
    """Picks a pawn move or a wall at random (50/50)."""
    name = "Random"

    def choose_move(self, state):
        pawn = [("move", r, c) for (r, c) in state.pawn_moves()]
        if state.walls_left[state.turn] > 0 and self.rng.random() < 0.5:
            spots = list(state.all_wall_spots())
            self.rng.shuffle(spots)
            for ori, r, c in spots:
                if state.is_legal_wall(ori, r, c):
                    return ("wall", ori, r, c)
        return self.rng.choice(pawn)


class GreedyAgent(Agent):
    """Moves to whichever neighbouring cell has the shortest route to goal."""
    name = "Greedy"

    def choose_move(self, state):
        me = state.turn
        best, best_moves = None, []
        for (r, c) in state.pawn_moves():
            old = state.pawns[me]
            state.pawns[me] = (r, c)
            d = pathfinding.distance(state, me)
            state.pawns[me] = old
            if best is None or d < best:
                best, best_moves = d, [("move", r, c)]
            elif d == best:
                best_moves.append(("move", r, c))
        return self.rng.choice(best_moves)


class TimeUp(Exception):
    pass


class AlphaBetaAgent(Agent):
    """Negamax search with alpha-beta pruning.

    Negamax is minimax written once: the score of a position for the player
    to move is minus the best score their opponent can get after any move.

    depth         - how many plies (single moves) to look ahead
    ordering      - search promising moves first (makes pruning work better)
    max_walls     - only consider this many of the best wall placements
    time_limit    - if set, use iterative deepening: search depth 1, 2, 3...
                    and return the deepest finished answer when time runs out
    mistake_rate  - chance of ignoring the search and playing greedily
                    (used to make the Easy level beatable)
    """

    def __init__(self, depth=2, ordering=True, max_walls=None, time_limit=None,
                 mistake_rate=0.0, name=None, seed=None, pruning=True):
        super().__init__(seed)
        self.depth = depth
        self.ordering = ordering
        self.max_walls = max_walls
        self.time_limit = time_limit
        self.mistake_rate = mistake_rate
        self.pruning = pruning
        self.name = name or ("AlphaBeta-d%d" % depth if pruning else "Minimax-d%d" % depth)
        self._deadline = None

    # -- public -----------------------------------------------------------
    def choose_move(self, state):
        start = time.time()
        self.nodes = 0
        self.depth_reached = 0

        if self.mistake_rate and self.rng.random() < self.mistake_rate:
            move = GreedyAgent(seed=self.rng.random()).choose_move(state)
            self.last_time = time.time() - start
            return move

        root = state.copy()             # search on a copy so a timeout can't corrupt the game
        self._deadline = start + self.time_limit if self.time_limit else None
        depths = range(1, self.depth + 1) if self.time_limit else [self.depth]

        best_move = None
        for d in depths:
            try:
                move, score = self._search_root(root, d, best_move)
            except TimeUp:
                break
            best_move, self.last_score, self.depth_reached = move, score, d
            if abs(score) >= WIN_SCORE:
                break                   # found a forced win or loss, no need to go deeper

        if best_move is None:           # timed out even at depth 1 or no candidates
            best_move = GreedyAgent(seed=1).choose_move(state)
        self.last_time = time.time() - start
        return best_move

    # -- search -----------------------------------------------------------
    def _moves(self, state):
        moves = candidate_moves(state, self.ordering, self.max_walls, self.rng)
        if not moves:
            moves = [("move", r, c) for (r, c) in state.pawn_moves()]
        return moves

    def _search_root(self, state, depth, previous_best):
        moves = self._moves(state)
        if previous_best in moves:      # iterative deepening: try last best first
            moves.remove(previous_best)
            moves.insert(0, previous_best)
        alpha, beta = -math.inf, math.inf
        best_move, best_score = moves[0], -math.inf
        for move in moves:
            state.apply(move)
            score = -self._negamax(state, depth - 1, -beta, -alpha)
            state.undo()
            if score > best_score:
                best_score, best_move = score, move
            if self.pruning and score > alpha:
                alpha = score
        return best_move, best_score

    def _negamax(self, state, depth, alpha, beta):
        self.nodes += 1
        if self._deadline and self.nodes % 64 == 0 and time.time() > self._deadline:
            raise TimeUp()

        if state.winner() is not None:
            # The player who just moved has won. A bigger `depth` here means
            # the win came sooner, so the winner prefers it.
            return -(WIN_SCORE + depth)
        if depth == 0:
            return evaluate(state, state.turn)

        best = -math.inf
        for move in self._moves(state):
            state.apply(move)
            score = -self._negamax(state, depth - 1, -beta, -alpha)
            state.undo()
            if score > best:
                best = score
            if self.pruning:
                if best > alpha:
                    alpha = best
                if alpha >= beta:
                    break               # opponent will never allow this line: prune
        return best


def MinimaxAgent(depth=2, **kwargs):
    """Plain minimax: the same search with pruning switched off."""
    kwargs.setdefault("ordering", False)
    return AlphaBetaAgent(depth=depth, pruning=False, **kwargs)


# Difficulty levels used by the game UI -------------------------------------

LEVELS = ["Easy", "Medium", "Hard"]


def make_agent(level, seed=None):
    if level == "Easy":
        return AlphaBetaAgent(depth=1, max_walls=4, mistake_rate=0.4, name="Easy AI", seed=seed)
    if level == "Medium":
        return AlphaBetaAgent(depth=2, max_walls=8, name="Medium AI", seed=seed)
    return AlphaBetaAgent(depth=6, max_walls=12, time_limit=2.0, name="Hard AI", seed=seed)
