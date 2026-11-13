"""Tests for the Quoridor rules: pawn moves, jumps, walls, legality."""

from quoridor import pathfinding
from quoridor.board import GameState


def empty_board():
    return GameState()


def test_start_position():
    s = empty_board()
    assert s.pawns == [(8, 4), (0, 4)]
    assert s.walls_left == [10, 10]
    assert sorted(s.pawn_moves()) == [(7, 4), (8, 3), (8, 5)]


def test_opening_has_131_moves():
    # 3 pawn moves + 8 x 8 x 2 = 128 wall spots
    assert len(empty_board().legal_moves()) == 131


def test_horizontal_wall_blocks_two_columns():
    s = empty_board()
    s.place_wall_temp("h", 3, 4)
    assert s.is_blocked(3, 4, 1, 0) and s.is_blocked(3, 5, 1, 0)
    assert s.is_blocked(4, 4, -1, 0) and s.is_blocked(4, 5, -1, 0)
    assert not s.is_blocked(3, 3, 1, 0)
    assert not s.is_blocked(3, 6, 1, 0)


def test_vertical_wall_blocks_two_rows():
    s = empty_board()
    s.place_wall_temp("v", 3, 4)
    assert s.is_blocked(3, 4, 0, 1) and s.is_blocked(4, 4, 0, 1)
    assert s.is_blocked(3, 5, 0, -1) and s.is_blocked(4, 5, 0, -1)
    assert not s.is_blocked(2, 4, 0, 1)
    assert not s.is_blocked(5, 4, 0, 1)


def test_walls_cannot_overlap_or_cross():
    s = empty_board()
    s.place_wall_temp("h", 3, 4)
    assert not s.wall_fits("h", 3, 4)     # same spot
    assert not s.wall_fits("h", 3, 3)     # overlaps left half
    assert not s.wall_fits("h", 3, 5)     # overlaps right half
    assert not s.wall_fits("v", 3, 4)     # crosses in the middle
    assert s.wall_fits("h", 3, 6)         # touching end to end is fine
    assert s.wall_fits("v", 3, 3)         # T-shape is fine


def test_wall_outside_board_is_rejected():
    s = empty_board()
    assert not s.wall_fits("h", 8, 0)
    assert not s.wall_fits("v", 0, 8)
    assert not s.wall_fits("h", -1, 0)


def test_wall_that_seals_a_player_in_is_illegal():
    s = empty_board()
    # Close the groove above row 8 for columns 0-7. Player 0 (at (8, 4))
    # can still escape through column 8.
    for c in (0, 2, 4, 6):
        s.place_wall_temp("h", 7, c)
    assert pathfinding.has_path(s, 0)
    # This vertical wall would cut column 8 off: it fits, but it is illegal.
    assert s.wall_fits("v", 7, 7)
    assert not s.is_legal_wall("v", 7, 7)
    # A wall that leaves a route is still fine.
    assert s.is_legal_wall("v", 2, 2)


def test_no_walls_left():
    s = empty_board()
    s.walls_left[0] = 0
    assert not s.is_legal_wall("h", 3, 3)
    assert all(m[0] == "move" for m in s.legal_moves())


def test_straight_jump():
    s = empty_board()
    s.pawns = [(5, 4), (4, 4)]
    assert (3, 4) in s.pawn_moves(0)
    assert (4, 4) not in s.pawn_moves(0)


def test_diagonal_jump_when_wall_behind():
    s = empty_board()
    s.pawns = [(5, 4), (4, 4)]
    s.place_wall_temp("h", 3, 4)           # wall behind the opponent
    moves = s.pawn_moves(0)
    assert (3, 4) not in moves
    assert (4, 3) in moves and (4, 5) in moves


def test_diagonal_jump_at_board_edge():
    s = empty_board()
    s.pawns = [(1, 4), (0, 4)]             # opponent on the top edge
    moves = s.pawn_moves(0)
    assert (0, 3) in moves and (0, 5) in moves


def test_apply_and_undo_restore_state():
    s = empty_board()
    before = (list(s.pawns), list(s.walls_left), set(s.h_walls), s.turn)
    s.apply(("move", 7, 4))
    s.apply(("wall", "h", 6, 3))
    s.undo()
    s.undo()
    assert (s.pawns, s.walls_left, s.h_walls, s.turn) == before


def test_winner():
    s = empty_board()
    s.pawns = [(0, 2), (5, 5)]
    assert s.winner() == 0
