"""Does keeping walls in hand matter? Tuning the evaluation function.

Two identical depth-2 Alpha-Beta agents play each other. The only difference
is how much one unused wall is worth in their evaluation:

    eval = 10 * (opponent distance - my distance) + WALL_WEIGHT * (my walls - opponent walls)

Each pairing plays GAMES games, swapping who moves first every game.

Run:  python -m experiments.eval_weights
"""

import csv
import os

from quoridor.ai import AlphaBetaAgent
from quoridor.board import GameState
from quoridor.config import MAX_PLIES

RESULTS = os.path.join(os.path.dirname(__file__), "results")
GAMES = 20
BASELINE = 3                 # the weight the game uses
CHALLENGERS = [0, 10]        # walls worth nothing / walls worth as much as a step


def play(agent_a, agent_b):
    """Play one game. Returns 0 if agent_a wins, 1 if agent_b wins, None for a draw."""
    s = GameState()
    agents = [agent_a, agent_b]
    while s.winner() is None and s.plies() < MAX_PLIES:
        s.apply(agents[s.turn].choose_move(s))
    return s.winner(), s.plies(), [10 - s.walls_left[0], 10 - s.walls_left[1]]


def main():
    rows = []
    for w in CHALLENGERS:
        wins = 0
        for g in range(GAMES):
            base = AlphaBetaAgent(2, max_walls=8, wall_weight=BASELINE, seed=g)
            test = AlphaBetaAgent(2, max_walls=8, wall_weight=w, seed=100 + g)
            if g % 2 == 0:
                winner, plies, used = play(base, test)
                test_won = winner == 1
                base_walls, test_walls = used[0], used[1]
            else:
                winner, plies, used = play(test, base)
                test_won = winner == 0
                base_walls, test_walls = used[1], used[0]
            wins += test_won
            rows.append({"challenger_weight": w, "game": g, "challenger_won": int(test_won),
                         "draw": int(winner is None), "plies": plies,
                         "walls_used_baseline": base_walls, "walls_used_challenger": test_walls})
        print("wall_weight %d vs %d: challenger won %d/%d" % (w, BASELINE, wins, GAMES))

    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "eval_weights.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("wrote", path)


if __name__ == "__main__":
    main()
