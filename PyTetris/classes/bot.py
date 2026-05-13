"""
classes/bot.py — Bot controller for Battle Mode (optimised).

The heavy heuristic search runs in a background daemon thread so the
main game loop never stalls waiting for AI evaluation.
"""

import copy
import random
import threading
from utils.heuristics import find_best_placements


# ── Lightweight board proxy for background thread ─────────────────────────────

class _BoardProxy:
    """Read-only snapshot of a Board, safe to use off the main thread."""
    __slots__ = ("grid", "width", "height")

    def __init__(self, grid, width, height):
        self.grid   = grid
        self.width  = width
        self.height = height

    def is_valid_position(self, piece):
        return self.is_valid_move(piece)

    def is_valid_move(self, piece, dx=0, dy=0):
        for x, y in piece.get_positions():
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= self.width or ny >= self.height:
                return False
            if ny < 0:
                continue
            if self.grid[ny][nx] != 0:
                return False
        return True


def _clone_piece(piece):
    p = copy.copy(piece)
    p.shape = [row[:] for row in piece.shape]
    return p


# ── Bot ───────────────────────────────────────────────────────────────────────

class Bot:
    _THINKING = "thinking"
    _MOVING   = "moving"
    _DROPPING = "dropping"
    _DONE     = "done"

    def __init__(self, config: dict, weights: dict) -> None:
        self.config  = config
        self.weights = weights
        self._state      = self._THINKING
        self._target_x   = 0
        self._target_rot = 0
        self._rots_done  = 0
        self._move_timer = 0.0
        self._drop_timer = 0.0
        self._searching  = False   # True while background thread is running

    # ── Public API ────────────────────────────────────────────────────────────

    def reset(self) -> None:
        self._state      = self._THINKING
        self._target_x   = 0
        self._target_rot = 0
        self._rots_done  = 0
        self._move_timer = 0.0
        self._drop_timer = 0.0
        self._searching  = False

    def tick(self, dt_ms: float, piece, board, next_piece=None) -> str:
        if self._state == self._THINKING:
            if not self._searching:
                # Instant bot: skip threading overhead, execute synchronously
                if self.config["delay_move_ms"] == 0 and self.config["delay_drop_ms"] == 0:
                    self._think_sync(piece, board, next_piece)
                    return self._instant_execute(piece, board)
                # All other bots: search in background thread, return "none" meanwhile
                self._launch_search(piece, board, next_piece)
            return "none"

        if self._state == self._MOVING:
            return self._tick_moving(dt_ms, piece, board)

        if self._state == self._DROPPING:
            return self._tick_dropping(dt_ms)

        return "none"   # _DONE: waiting for reset()

    # ── Background search ─────────────────────────────────────────────────────

    def _launch_search(self, piece, board, next_piece):
        """Snapshot board state and kick off search in a daemon thread."""
        self._searching = True

        piece_snap = _clone_piece(piece)
        proxy = _BoardProxy(
            grid=[row[:] for row in board.grid],
            width=board.width,
            height=board.height,
        )
        lookahead = self.config["lookahead"] and next_piece is not None
        next_snap = _clone_piece(next_piece) if lookahead else None
        mistake   = self.config["mistake_chance"]
        weights   = self.weights

        def _run():
            try:
                placements = find_best_placements(
                    piece_snap, proxy, weights,
                    next_piece=next_snap,
                )
                if not placements:
                    self._target_x   = piece_snap.x
                    self._target_rot = 0
                else:
                    idx = 0
                    if mistake > 0.0 and len(placements) > 1 and random.random() < mistake:
                        idx = 1
                    _, self._target_x, self._target_rot = placements[idx]
                self._rots_done = 0
                self._state     = self._MOVING   # atomic in CPython (GIL)
            except Exception:
                self._target_x   = piece_snap.x
                self._target_rot = 0
                self._state      = self._MOVING
            finally:
                self._searching = False

        threading.Thread(target=_run, daemon=True).start()

    def _think_sync(self, piece, board, next_piece):
        """Synchronous version used by instant bot only."""
        lookahead  = self.config["lookahead"] and next_piece is not None
        placements = find_best_placements(
            piece, board, self.weights,
            next_piece=next_piece if lookahead else None,
        )
        if not placements:
            self._target_x   = piece.x
            self._target_rot = 0
        else:
            idx = 0
            if (self.config["mistake_chance"] > 0.0
                    and len(placements) > 1
                    and random.random() < self.config["mistake_chance"]):
                idx = 1
            _, self._target_x, self._target_rot = placements[idx]
        self._rots_done = 0
        self._state     = self._MOVING

    # ── Moving ────────────────────────────────────────────────────────────────

    def _tick_moving(self, dt_ms: float, piece, board) -> str:
        self._move_timer += dt_ms
        if self._move_timer < self.config["delay_move_ms"]:
            return "none"
        self._move_timer = 0.0
        action = self._step_toward_target(piece, board)
        if action != "none":
            return action
        self._state      = self._DROPPING
        self._drop_timer = 0.0
        return "none"

    def _tick_dropping(self, dt_ms: float) -> str:
        self._drop_timer += dt_ms
        if self._drop_timer >= self.config["delay_drop_ms"]:
            self._state = self._DONE
            return "drop"
        return "none"

    # ── Instant bot ───────────────────────────────────────────────────────────

    def _instant_execute(self, piece, board) -> str:
        while True:
            action = self._step_toward_target(piece, board)
            if action == "none":
                break
            # _step_toward_target() already applied the move — no re-apply needed
        self._state = self._DONE
        return "drop"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _step_toward_target(self, piece, board) -> str:
        if self._rots_done < self._target_rot:
            self._apply_rotation(piece, board)
            self._rots_done += 1
            return "rotate"
        if piece.x < self._target_x:
            if board.is_valid_move(piece, dx=1):
                piece.x += 1
                return "right"
            else:
                self._target_x = piece.x
        if piece.x > self._target_x:
            if board.is_valid_move(piece, dx=-1):
                piece.x -= 1
                return "left"
            else:
                self._target_x = piece.x
        return "none"

    @staticmethod
    def _apply_rotation(piece, board) -> None:
        old_shape = [row[:] for row in piece.shape]
        old_x     = piece.x
        piece.rotate()
        if not board.is_valid_position(piece):
            kicked = False
            for nudge in [1, -1, 2, -2]:
                piece.x += nudge
                if board.is_valid_position(piece):
                    kicked = True
                    break
                piece.x = old_x
            if not kicked:
                piece.shape = old_shape
                piece.x     = old_x
