"""Round-robin tournament between all agents.

Each pair plays GAMES_PER_PAIR games, swapping who moves first every game
(moving first is an advantage in Quoridor). Results go to
experiments/results/tournament.csv (one row per game).

Run:  python -m experiments.tournament
"""

import csv
import itertools
import os
import sys
import time
from multiprocessing import Pool

from quoridor.ai import RandomAgent, GreedyAgent, AlphaBetaAgent
from quoridor.board import GameState
from quoridor.config import MAX_PLIES

RESULTS = os.path.join(os.path.dirname(__file__), "results")
GAMES_PER_PAIR = 10

# Hard gets 1 second per move here (2 s in the game) to keep the run short.
AGENTS = {
    "Random": lambda seed: RandomAgent(seed),
    "Greedy": lambda seed: GreedyAgent(seed),
    "Easy": lambda seed: AlphaBetaAgent(1, max_walls=4, mistake_rate=0.4, seed=seed),
    "Medium": lambda seed: AlphaBetaAgent(2, max_walls=8, seed=seed),
    "Hard": lambda seed: AlphaBetaAgent(6, max_walls=12, time_limit=1.0, seed=seed),
}


def play_game(args):
    first, second, seed = args
    agents = [AGENTS[first](seed), AGENTS[second](seed + 1000)]
    s = GameState()
    think = [0.0, 0.0]
    while s.winner() is None and s.plies() < MAX_PLIES:
        t = time.time()
        move = agents[s.turn].choose_move(s)
        think[s.turn] += time.time() - t
        s.apply(move)
    w = s.winner()
    winner = "draw" if w is None else (first if w == 0 else second)
    return {"first": first, "second": second, "seed": seed, "winner": winner,
            "plies": s.plies(), "walls_used_first": 10 - s.walls_left[0],
            "walls_used_second": 10 - s.walls_left[1],
            "think_s_first": round(think[0], 2), "think_s_second": round(think[1], 2)}


def main(games=GAMES_PER_PAIR):
    jobs = []
    for a, b in itertools.combinations(AGENTS, 2):
        for g in range(games):
            first, second = (a, b) if g % 2 == 0 else (b, a)
            jobs.append((first, second, g))
    rows = []
    with Pool() as pool:
        for i, row in enumerate(pool.imap_unordered(play_game, jobs), 1):
            rows.append(row)
            print("[%d/%d] %s vs %s -> %s (%d plies)" % (
                i, len(jobs), row["first"], row["second"], row["winner"], row["plies"]))
            sys.stdout.flush()
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "tournament.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["first"], r["second"], r["seed"])))
    print("wrote", path)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else GAMES_PER_PAIR)
