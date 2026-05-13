"""
utils/heuristics.py — Pure heuristic evaluation functions.

All functions are stateless: they take a Board (or grid snapshot) and
return a number.  No Pygame, no game-loop state, no side effects.

This module is the ONLY place that knows about AI scoring logic.
bot.py imports it; nothing else should need to.

Public API
----------
evaluate(board, weights)          → float
find_best_placements(piece, board, weights, next_piece=None)
                                  → list of (score, target_x, num_rotations)
                                    sorted best-first
"""

import copy
from typing import List, Tuple, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Board-level feature extractors
# All operate on a raw 2-D grid (list[list]) for easy scratch-copy usage.
# ─────────────────────────────────────────────────────────────────────────────

def column_heights(grid: list) -> List[int]:
    """
    Height of each column = distance from the top of the highest filled
    cell to the bottom of the grid.

    Empty column → height 0.
    """
    rows  = len(grid)
    cols  = len(grid[0]) if grid else 0
    heights = []
    for c in range(cols):
        h = 0
        for r in range(rows):
            if grid[r][c] != 0:
                h = rows - r
                break
        heights.append(h)
    return heights


def aggregate_height(grid: list) -> int:
    """Sum of all column heights."""
    return sum(column_heights(grid))


def count_holes(grid: list) -> int:
    """
    A hole is an empty cell that has at least one filled cell above it
    in the same column.

    Holes are very costly: every hole requires clearing at least one
    line above it to become reachable again.
    """
    rows = len(grid)
    cols = len(grid[0]) if grid else 0
    holes = 0
    for c in range(cols):
        block_found = False
        for r in range(rows):
            if grid[r][c] != 0:
                block_found = True
            elif block_found:
                holes += 1
    return holes


def bumpiness(grid: list) -> int:
    """
    Sum of absolute differences between adjacent column heights.

    A flat surface (bumpiness = 0) is optimal for setting up Tetrises.
    """
    heights = column_heights(grid)
    return sum(abs(heights[i] - heights[i + 1]) for i in range(len(heights) - 1))


def count_complete_lines(grid: list) -> int:
    """Number of rows in which every cell is filled."""
    return sum(1 for row in grid if all(cell != 0 for cell in row))


def tetris_ready_bonus(grid: list) -> float:
    """
    Reward for having exactly one column that is 4+ rows lower than its
    neighbours — the classic 'Tetris well'.  Returns 1.0 if such a well
    exists and the rest of the stack is reasonably flat; 0.0 otherwise.

    Only used by the Invincible bot (w_tetris > 0 in its weight dict).
    """
    heights = column_heights(grid)
    if not heights:
        return 0.0

    for i, h in enumerate(heights):
        neighbours = [heights[j] for j in range(len(heights)) if j != i]
        if not neighbours:
            continue
        avg_neighbour = sum(neighbours) / len(neighbours)
        # Well = this column is at least 4 units lower than average neighbour
        if avg_neighbour - h >= 4:
            return 1.0
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Composite evaluator
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(grid: list, weights: dict) -> float:
    """
    Combine all features into a single scalar score.

    Higher is better (bot maximises this value).

    Parameters
    ----------
    grid    : 2-D list representing the board state after a simulated lock
    weights : dict with keys w_lines, w_holes, w_height, w_bump, w_tetris
    """
    return (
        weights["w_lines"]  * count_complete_lines(grid)
      + weights["w_holes"]  * count_holes(grid)
      + weights["w_height"] * aggregate_height(grid)
      + weights["w_bump"]   * bumpiness(grid)
      + weights["w_tetris"] * tetris_ready_bonus(grid)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Placement search
# ─────────────────────────────────────────────────────────────────────────────

def find_best_placements(
    piece,
    board,
    weights: dict,
    next_piece=None,
) -> List[Tuple[float, int, int]]:
    """
    Enumerate every legal (rotation, column) placement of `piece` on
    `board`, score each one, and return a sorted list.

    Parameters
    ----------
    piece      : current Tetromino (not mutated)
    board      : Board instance (not mutated)
    weights    : heuristic weight dict
    next_piece : optional Tetromino for 1-deep lookahead

    Returns
    -------
    List of (score, target_x, num_rotations) sorted descending by score.
    The caller picks index 0 for best, index 1 for intentional mistake.
    """
    results: List[Tuple[float, int, int]] = []

    for num_rots in range(4):
        # Build a rotated copy of the piece
        test_piece = _clone_piece(piece)
        for _ in range(num_rots):
            test_piece.rotate()

        piece_cols = _occupied_cols(test_piece)
        if not piece_cols:
            continue
        min_col_offset = min(piece_cols)
        max_col_offset = max(piece_cols)

        # Slide across all valid columns
        for col in range(-min_col_offset, board.width - max_col_offset):
            candidate = _clone_piece(test_piece)
            candidate.x = col   # absolute x

            # Skip if starting position is invalid (piece spawned mid-board)
            if not board.is_valid_position(candidate):
                continue

            # Drop to floor
            while board.is_valid_move(candidate, dy=1):
                candidate.y += 1

            # Simulate placement on a scratch grid
            scratch_grid = _scratch_after_place(board.grid, candidate)
            _clear_scratch(scratch_grid)   # simulate line clear

            if next_piece is not None:
                # 1-deep lookahead: also evaluate best sub-placement of next piece
                score = _lookahead_score(scratch_grid, next_piece, weights)
            else:
                score = evaluate(scratch_grid, weights)

            results.append((score, candidate.x, num_rots))

    # Sort best-first; stable sort keeps earlier rotations preferred on ties
    results.sort(key=lambda t: t[0], reverse=True)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _clone_piece(piece):
    """Deep-copy a Tetromino without importing Tetromino (avoids circular dep)."""
    p = copy.copy(piece)
    p.shape = [row[:] for row in piece.shape]
    return p


def _occupied_cols(piece) -> List[int]:
    """Column offsets (relative to piece.x) that are filled."""
    return [cx - piece.x for cx, cy in piece.get_positions()]


def _scratch_after_place(grid: list, piece) -> list:
    """Return a new grid with piece cells written in."""
    scratch = [row[:] for row in grid]
    for cx, cy in piece.get_positions():
        if 0 <= cy < len(scratch) and 0 <= cx < len(scratch[0]):
            scratch[cy][cx] = piece.type
    return scratch


def _clear_scratch(grid: list) -> int:
    """
    Remove complete lines from grid in-place, prepend empty rows.
    Returns lines cleared.
    """
    cols        = len(grid[0]) if grid else 0
    new_grid    = [row for row in grid if any(cell == 0 for cell in row)]
    cleared     = len(grid) - len(new_grid)
    for _ in range(cleared):
        new_grid.insert(0, [0] * cols)
    grid[:] = new_grid
    return cleared


def _lookahead_score(grid: list, next_piece, weights: dict) -> float:
    """
    For each placement of next_piece on grid, find the best sub-score.
    Returns that best sub-score (1-ply lookahead).
    """
    best = float("-inf")

    for num_rots in range(4):
        test = _clone_piece(next_piece)
        for _ in range(num_rots):
            test.rotate()

        piece_cols = _occupied_cols(test)
        if not piece_cols:
            continue
        min_col_offset = min(piece_cols)
        max_col_offset = max(piece_cols)
        cols = len(grid[0]) if grid else 0

        for col in range(-min_col_offset, cols - max_col_offset):
            candidate = _clone_piece(test)
            candidate.x = col

            # Simple floor-drop on scratch grid (no Board object needed)
            candidate.y = 0
            while _can_move_down(candidate, grid):
                candidate.y += 1

            sub_grid = _scratch_after_place(grid, candidate)
            _clear_scratch(sub_grid)
            score = evaluate(sub_grid, weights)
            if score > best:
                best = score

    return best if best > float("-inf") else evaluate(grid, weights)


def _can_move_down(piece, grid: list) -> bool:
    rows = len(grid)
    cols = len(grid[0]) if grid else 0
    for cx, cy in piece.get_positions():
        ny = cy + 1
        if ny >= rows:
            return False
        if 0 <= cx < cols and ny >= 0 and grid[ny][cx] != 0:
            return False
    return True
