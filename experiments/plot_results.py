"""Turn the CSV results into charts in experiments/results/plots/.

Run:  python -m experiments.plot_results
"""

import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RESULTS = os.path.join(os.path.dirname(__file__), "results")
PLOTS = os.path.join(RESULTS, "plots")

COLORS = ["#8A91A0", "#F2A541", "#4CC9F0"]


def read(name):
    with open(os.path.join(RESULTS, name)) as f:
        return list(csv.DictReader(f))


def style(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=12, loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)


def plot_nodes():
    rows = read("search_nodes.csv")
    algos = []
    for r in rows:
        if r["algorithm"] not in algos:
            algos.append(r["algorithm"])
    depths = sorted({int(r["depth"]) for r in rows})
    fig, ax = plt.subplots(figsize=(8, 4.5))
    width = 0.26
    for i, a in enumerate(algos):
        vals = [float(r["avg_nodes"]) for r in rows if r["algorithm"] == a]
        xs = [d + (i - 1) * width for d in depths]
        bars = ax.bar(xs, vals, width, label=a, color=COLORS[i])
        for x, v in zip(xs, vals):
            ax.text(x, v * 1.08, "%d" % round(v), ha="center", fontsize=8)
        _ = bars
    ax.set_yscale("log")
    ax.set_xticks(depths)
    style(ax, "Positions searched per move (log scale, avg of 12 positions)",
          "Search depth (plies)", "Nodes visited")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "search_nodes.png"), dpi=150)
    plt.close(fig)


def plot_time():
    rows = read("search_nodes.csv")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    algos = []
    for r in rows:
        if r["algorithm"] not in algos:
            algos.append(r["algorithm"])
    for i, a in enumerate(algos):
        sub = [r for r in rows if r["algorithm"] == a]
        ax.plot([int(r["depth"]) for r in sub], [float(r["avg_time_s"]) for r in sub],
                marker="o", label=a, color=COLORS[i], linewidth=2)
    ax.set_xticks(sorted({int(r["depth"]) for r in rows}))
    style(ax, "Time to choose one move", "Search depth (plies)", "Seconds")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "search_time.png"), dpi=150)
    plt.close(fig)


def plot_branching():
    rows = read("branching.csv")
    keys = [("all_legal_moves", "All legal moves"),
            ("path_cutting_moves", "Pawn moves +\npath-cutting walls"),
            ("searched_moves_cap8", "+ keep best 8 walls")]
    vals = [sum(float(r[k]) for r in rows) / len(rows) for k, _ in keys]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.bar([label for _, label in keys], vals, color=COLORS)
    for i, v in enumerate(vals):
        ax.text(i, v + 2, "%.1f" % v, ha="center")
    style(ax, "Branching factor: moves searched per position", "", "Moves (avg)")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "branching.png"), dpi=150)
    plt.close(fig)


def plot_bfs_astar():
    rows = read("bfs_vs_astar.csv")
    bfs = sum(int(r["bfs_expanded"]) for r in rows) / len(rows)
    ast = sum(int(r["astar_expanded"]) for r in rows) / len(rows)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["BFS", "A* (h = rows to goal)"], [bfs, ast], color=[COLORS[1], COLORS[2]])
    for i, v in enumerate([bfs, ast]):
        ax.text(i, v + 0.6, "%.1f" % v, ha="center")
    style(ax, "Cells expanded to find the shortest route\n(same path length every time)",
          "", "Cells expanded (avg)")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "bfs_vs_astar.png"), dpi=150)
    plt.close(fig)


def tournament_table():
    rows = read("tournament.csv")
    names = ["Random", "Greedy", "Easy", "Medium", "Hard"]
    wins = defaultdict(int)
    games = defaultdict(int)
    for r in rows:
        a, b = r["first"], r["second"]
        games[(a, b)] += 1
        games[(b, a)] += 1
        if r["winner"] != "draw":
            loser = b if r["winner"] == a else a
            wins[(r["winner"], loser)] += 1
    return names, wins, games


def plot_tournament():
    names, wins, games = tournament_table()
    n = len(names)
    grid = [[float("nan")] * n for _ in range(n)]
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i != j and games[(a, b)]:
                grid[i][j] = 100 * wins[(a, b)] / games[(a, b)]
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    im = ax.imshow(grid, cmap="RdYlGn", vmin=0, vmax=100)
    ax.set_xticks(range(n), names)
    ax.set_yticks(range(n), names)
    for i in range(n):
        for j in range(n):
            if i != j:
                ax.text(j, i, "%d%%" % round(grid[i][j]), ha="center", va="center", fontsize=10)
    ax.set_title("Win rate of row agent vs column agent", loc="left")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "tournament.png"), dpi=150)
    plt.close(fig)

    totals = []
    for a in names:
        w = sum(wins[(a, b)] for b in names if b != a)
        g = sum(games[(a, b)] for b in names if b != a)
        totals.append(100 * w / g)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(names, totals, color=["#8A91A0", "#8A91A0", "#F2A541", "#F2A541", "#4CC9F0"])
    for i, v in enumerate(totals):
        ax.text(i, v + 1.5, "%d%%" % round(v), ha="center")
    ax.set_ylim(0, 105)
    style(ax, "Overall win rate in the round-robin", "", "Win rate (%)")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "win_rates.png"), dpi=150)
    plt.close(fig)


def plot_game_lengths():
    """Box plot of how long games last (in plies) for each pairing."""
    rows = read("tournament.csv")
    order = ["Random", "Greedy", "Easy", "Medium", "Hard"]
    by_pair = defaultdict(list)
    for r in rows:
        a, b = sorted([r["first"], r["second"]], key=order.index)
        by_pair["%s vs\n%s" % (a, b)].append(int(r["plies"]))
    labels = sorted(by_pair, key=lambda k: sum(by_pair[k]) / len(by_pair[k]))
    data = [by_pair[k] for k in labels]

    fig, ax = plt.subplots(figsize=(10, 4.5))
    box = ax.boxplot(data, patch_artist=True, widths=0.6)
    for patch in box["boxes"]:
        patch.set_facecolor("#4CC9F0")
        patch.set_alpha(0.6)
    for median in box["medians"]:
        median.set_color("#0F1115")
    ax.set_xticks(range(1, len(labels) + 1), labels, fontsize=8)
    style(ax, "Game length per pairing (10 games each, sorted by average)",
          "", "Moves in the game (plies)")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "game_lengths.png"), dpi=150)
    plt.close(fig)


def main():
    os.makedirs(PLOTS, exist_ok=True)
    plot_nodes()
    plot_time()
    plot_branching()
    plot_bfs_astar()
    if os.path.exists(os.path.join(RESULTS, "tournament.csv")):
        plot_tournament()
        plot_game_lengths()
    print("plots saved to", PLOTS)


if __name__ == "__main__":
    main()
