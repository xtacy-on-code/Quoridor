"""Tests for pathfinding and the AI agents."""

import random

from quoridor import pathfinding
from quoridor.ai import AlphaBetaAgent, MinimaxAgent, GreedyAgent, RandomAgent, make_agent
from quoridor.ai.movegen import candidate_moves
from quoridor.board import GameState


def test_bfs_and_astar_agree_on_empty_board():
    s = GameState()
    assert pathfinding.bfs(s, 0)[0] == 8
    assert pathfinding.astar(s, 0)[0] == 8


def test_bfs_and_astar_agree_with_walls():
    rng = random.Random(0)
    for _ in range(30):
        s = GameState()
        for _ in range(8):
            ori, r, c = rng.choice(["h", "v"]), rng.randrange(8), rng.randrange(8)
            if s.is_legal_wall(ori, r, c):
                s.apply(("wall", ori, r, c))
        for p in (0, 1):
            assert pathfinding.bfs(s, p)[0] == pathfinding.astar(s, p)[0]
            # A* never expands more cells than BFS with this heuristic
            assert pathfinding.astar(s, p)[2] <= pathfinding.bfs(s, p)[2] + 1


def test_wall_detour():
    s = GameState()
    s.pawns = [(8, 4), (0, 0)]
    s.place_wall_temp("h", 7, 3)           # wall right above player 0
    assert pathfinding.distance(s, 0) == 9  # one step sideways first


def test_candidate_walls_all_lengthen_opponent_path():
    s = GameState()
    s.pawns = [(6, 4), (2, 4)]
    before = pathfinding.distance(s, 1)
    for m in candidate_moves(s):
        if m[0] == "wall":
            s.apply(m)
            assert pathfinding.distance(s, 1) > before
            s.undo()


def test_ai_takes_the_winning_step():
    s = GameState()
    s.pawns = [(1, 4), (6, 0)]
    for agent in (AlphaBetaAgent(depth=1), AlphaBetaAgent(depth=3), make_agent("Hard", seed=1)):
        assert agent.choose_move(s) == ("move", 0, 4)


def test_ai_blocks_opponent_about_to_win():
    s = GameState()
    s.pawns = [(8, 0), (7, 4)]             # player 1 wins next move by stepping to row 8
    s.walls_left = [10, 10]
    move = AlphaBetaAgent(depth=2).choose_move(s)
    assert move[0] == "wall"
    s.apply(move)
    assert pathfinding.distance(s, 1) > 1


def test_alphabeta_matches_minimax_score_with_fewer_nodes():
    s = GameState()
    for m in [("move", 7, 4), ("move", 1, 4), ("move", 6, 4), ("move", 2, 4)]:
        s.apply(m)
    mm = MinimaxAgent(depth=2, max_walls=6, seed=0)
    ab = AlphaBetaAgent(depth=2, max_walls=6, seed=0)
    mm.choose_move(s)
    ab.choose_move(s)
    assert mm.last_score == ab.last_score
    assert ab.nodes < mm.nodes


def test_all_agents_return_legal_moves():
    s = GameState()
    for agent in (RandomAgent(1), GreedyAgent(1), make_agent("Easy", 1), make_agent("Medium", 1)):
        for _ in range(6):
            if s.winner() is not None:
                return
            move = agent.choose_move(s)
            assert s.is_legal(move)
            s.apply(move)
