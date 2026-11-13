"""Reproducible test positions for the benchmarks.

We let two Medium-level agents play from the start and save the position
every few moves, so the benchmarks run on realistic mid-game boards
(pawns spread out, some walls down) rather than only the empty board.
"""

from quoridor.ai import AlphaBetaAgent
from quoridor.board import GameState


def sample_positions(n=12, seed=0):
    positions = []
    game = 0
    while len(positions) < n:
        s = GameState()
        agents = [AlphaBetaAgent(2, max_walls=8, seed=seed + game * 2),
                  AlphaBetaAgent(2, max_walls=8, seed=seed + game * 2 + 1)]
        ply = 0
        while s.winner() is None and ply < 60 and len(positions) < n:
            s.apply(agents[s.turn].choose_move(s))
            ply += 1
            if ply in (6, 12, 18) and s.winner() is None:
                positions.append(s.copy())
        game += 1
    return positions
