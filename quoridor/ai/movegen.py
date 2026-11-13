"""Which moves should the AI bother searching?

On an empty board there are 128 wall spots, so a 2-ply search would look at
~130 x 130 = 17,000 positions, and most of those walls are pointless.

Pruning idea: a wall only matters right now if it lengthens the opponent's
route. Any wall that does so must cut the opponent's current shortest path
(otherwise that path still exists). So we only try walls that block one of
the steps on that path, and keep the ones that actually make it longer.
That cuts ~128 wall spots down to roughly 5-15.

Move ordering idea: alpha-beta prunes most when the best move is searched
first. We give every move a quick score (how much it shortens my route or
lengthens the opponent's) and search high scores first.
"""

from quoridor import pathfinding


def walls_on_path(path):
    """Wall spots that would block one of the steps along `path`."""
    spots = []
    for (r1, c1), (r2, c2) in zip(path, path[1:]):
        if r1 != r2:
            # A vertical step crosses the groove between two rows,
            # which a horizontal wall covers (it can start at c or c-1).
            gr = min(r1, r2)
            spots.append(("h", gr, c1))
            spots.append(("h", gr, c1 - 1))
        else:
            # A sideways step crosses the groove between two columns.
            gc = min(c1, c2)
            spots.append(("v", r1, gc))
            spots.append(("v", r1 - 1, gc))
    return spots


def scored_moves(state, max_walls=None):
    """List of (quick_score, move) for the player to move.

    quick_score for a pawn move  = how much it shortens my route (x10)
    quick_score for a wall       = (opponent route gain - my route loss) (x10)
    """
    me = state.turn
    opp = 1 - me
    my_dist = pathfinding.distance(state, me)
    opp_path = pathfinding.shortest_path(state, opp)
    opp_dist = len(opp_path) - 1

    result = []
    for (r, c) in state.pawn_moves():
        old = state.pawns[me]
        state.pawns[me] = (r, c)
        new_dist = pathfinding.distance(state, me)
        state.pawns[me] = old
        result.append((10 * (my_dist - new_dist), ("move", r, c)))

    if state.walls_left[me] > 0:
        seen = set()
        walls = []
        for ori, r, c in walls_on_path(opp_path):
            if (ori, r, c) in seen or not state.wall_fits(ori, r, c):
                continue
            seen.add((ori, r, c))
            state.place_wall_temp(ori, r, c)
            new_opp = pathfinding.distance(state, opp)
            new_me = pathfinding.distance(state, me)
            state.remove_wall_temp(ori, r, c)
            if new_opp is None or new_me is None:
                continue                      # illegal: it walls someone in
            gain = new_opp - opp_dist
            if gain <= 0:
                continue                      # a detour of equal length exists
            loss = new_me - my_dist
            walls.append((10 * (gain - loss), ("wall", ori, r, c)))
        walls.sort(key=lambda x: -x[0])
        if max_walls is not None:
            walls = walls[:max_walls]
        result.extend(walls)
    return result


def candidate_moves(state, ordering=True, max_walls=None, rng=None):
    """Moves to search, best-looking first when ordering is on."""
    scored = scored_moves(state, max_walls)
    if rng is not None:
        rng.shuffle(scored)                   # random tie-breaks between equal scores
    if ordering:
        scored.sort(key=lambda x: -x[0])      # stable sort keeps the shuffle for ties
    else:
        scored.sort(key=lambda x: x[1])       # fixed, "dumb" order: by coordinates
    return [m for _, m in scored]
