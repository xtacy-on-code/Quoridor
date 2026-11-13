"""How good is a position? The heuristic evaluation used at the search leaves.

Quoridor is a race, so the key number is how many steps each player still
needs, which we get from BFS. A position is good for me if my opponent's
route is long and mine is short. Walls left in hand are a resource too:
they are future chances to slow the opponent down.

    score = 10 * (opponent_distance - my_distance)
          +  3 * (my_walls_left - opponent_walls_left)
"""

from quoridor import pathfinding

WIN_SCORE = 100000
PATH_WEIGHT = 10
WALL_WEIGHT = 3


def evaluate(state, player):
    """Score of `state` from `player`'s point of view (higher is better)."""
    w = state.winner()
    if w is not None:
        return WIN_SCORE if w == player else -WIN_SCORE
    my_dist = pathfinding.distance(state, player)
    opp_dist = pathfinding.distance(state, 1 - player)
    score = PATH_WEIGHT * (opp_dist - my_dist)
    score += WALL_WEIGHT * (state.walls_left[player] - state.walls_left[1 - player])
    return score
