"""Shortest paths on the Quoridor board: BFS and A*.

The pawn's goal is not one cell but a whole row, so the search stops at the
first cell it reaches on the goal row. Every step costs 1, which is why plain
BFS already gives the shortest path. A* uses h(cell) = rows left to the goal:
it never overestimates (each step changes the row by at most 1), so it is
admissible and consistent and also returns the shortest path, but it
expands fewer cells.

The opponent's pawn is ignored here: it moves every turn and can be jumped,
so it is not a lasting obstacle.
"""

import heapq
from collections import deque

from quoridor.config import GOAL_ROW, DIRECTIONS


def bfs(state, player, return_path=False):
    """Breadth-first search from the player's pawn to its goal row.

    Returns (distance, path, cells_expanded). distance is None if the goal
    row cannot be reached. path is a list of cells (only if return_path).
    """
    start = state.pawns[player]
    goal = GOAL_ROW[player]
    if start[0] == goal:
        return 0, [start], 0

    parent = {start: None}
    dist = {start: 0}
    queue = deque([start])
    expanded = 0
    while queue:
        cell = queue.popleft()
        expanded += 1
        r, c = cell
        for dr, dc in DIRECTIONS:
            if not state.can_step(r, c, dr, dc):
                continue
            nxt = (r + dr, c + dc)
            if nxt in parent:
                continue
            parent[nxt] = cell
            dist[nxt] = dist[cell] + 1
            if nxt[0] == goal:
                path = _rebuild(parent, nxt) if return_path else None
                return dist[nxt], path, expanded
            queue.append(nxt)
    return None, None, expanded


def astar(state, player, return_path=False):
    """A* search with h = number of rows left to the goal row.

    Returns (distance, path, cells_expanded) just like bfs().
    """
    start = state.pawns[player]
    goal = GOAL_ROW[player]

    def h(cell):
        return abs(cell[0] - goal)

    g = {start: 0}
    parent = {start: None}
    frontier = [(h(start), 0, start)]   # (f, g, cell)
    closed = set()
    expanded = 0
    while frontier:
        f, cost, cell = heapq.heappop(frontier)
        if cell in closed:
            continue
        if cell[0] == goal:
            path = _rebuild(parent, cell) if return_path else None
            return cost, path, expanded
        closed.add(cell)
        expanded += 1
        r, c = cell
        for dr, dc in DIRECTIONS:
            if not state.can_step(r, c, dr, dc):
                continue
            nxt = (r + dr, c + dc)
            new_cost = cost + 1
            if nxt not in g or new_cost < g[nxt]:
                g[nxt] = new_cost
                parent[nxt] = cell
                heapq.heappush(frontier, (new_cost + h(nxt), new_cost, nxt))
    return None, None, expanded


def _rebuild(parent, cell):
    path = []
    while cell is not None:
        path.append(cell)
        cell = parent[cell]
    path.reverse()
    return path


# Small helpers used by the rules and the AI ---------------------------------

def distance(state, player):
    """Length of the shortest route to the goal row, or None if walled in."""
    return bfs(state, player)[0]


def shortest_path(state, player):
    """List of cells from the pawn to its goal row (pawn cell included)."""
    return bfs(state, player, return_path=True)[1]


def has_path(state, player):
    return distance(state, player) is not None
