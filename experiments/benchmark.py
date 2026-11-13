"""Search benchmarks (no games played).

1. Minimax vs Alpha-Beta (with and without move ordering): nodes and time
   per move at depths 1-4, averaged over the same set of positions.
2. Wall pruning: how many moves the AI really searches vs all legal moves.
3. BFS vs A*: cells expanded to find the shortest route to the goal row.

Writes CSV files to experiments/results/.
"""

import csv
import os
import time

from quoridor import pathfinding
from quoridor.ai import AlphaBetaAgent, MinimaxAgent
from quoridor.ai.movegen import candidate_moves
from experiments.positions import sample_positions

RESULTS = os.path.join(os.path.dirname(__file__), "results")
MAX_WALLS = 8


def search_benchmark(positions, depths=(1, 2, 3, 4)):
    rows = []
    variants = [
        ("Minimax", lambda d: MinimaxAgent(d, max_walls=MAX_WALLS, seed=0)),
        ("Alpha-Beta (no ordering)", lambda d: AlphaBetaAgent(d, ordering=False, max_walls=MAX_WALLS, seed=0)),
        ("Alpha-Beta (ordered)", lambda d: AlphaBetaAgent(d, ordering=True, max_walls=MAX_WALLS, seed=0)),
    ]
    for d in depths:
        for name, make in variants:
            nodes, secs, scores = [], [], []
            for s in positions:
                agent = make(d)
                t = time.time()
                agent.choose_move(s)
                secs.append(time.time() - t)
                nodes.append(agent.nodes)
                scores.append(agent.last_score)
            rows.append({
                "depth": d, "algorithm": name,
                "avg_nodes": round(sum(nodes) / len(nodes), 1),
                "avg_time_s": round(sum(secs) / len(secs), 4),
                "scores": " ".join(str(x) for x in scores),
            })
            print("depth %d  %-26s nodes %10.1f  time %.3fs" % (
                d, name, rows[-1]["avg_nodes"], rows[-1]["avg_time_s"]))
    return rows


def branching_benchmark(positions):
    rows = []
    for i, s in enumerate(positions):
        full = len(s.legal_moves())
        pruned = len(candidate_moves(s, max_walls=None))
        capped = len(candidate_moves(s, max_walls=MAX_WALLS))
        rows.append({"position": i, "all_legal_moves": full,
                     "path_cutting_moves": pruned, "searched_moves_cap8": capped})
    return rows


def pathfinding_benchmark(positions):
    rows = []
    for i, s in enumerate(positions):
        for p in (0, 1):
            d1, _, e1 = pathfinding.bfs(s, p)
            d2, _, e2 = pathfinding.astar(s, p)
            assert d1 == d2
            rows.append({"position": i, "player": p, "distance": d1,
                         "bfs_expanded": e1, "astar_expanded": e2})
    return rows


def write_csv(name, rows):
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, name)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", path)


def main():
    positions = sample_positions(12)
    write_csv("search_nodes.csv", search_benchmark(positions))
    write_csv("branching.csv", branching_benchmark(positions))
    write_csv("bfs_vs_astar.csv", pathfinding_benchmark(positions))


if __name__ == "__main__":
    main()
