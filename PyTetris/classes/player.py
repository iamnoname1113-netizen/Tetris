import pygame
from constants import DAS_DELAY_MS, ARR_DELAY_MS, SOFT_DROP_MULT

class Player:
    """
    Handles human input, translates keyboard events to piece moves,
    and manages DAS/ARR timers.
    """
    def __init__(self, key_left, key_right, key_down, key_rotate, key_hard_drop):
        self.key_left = key_left
        self.key_right = key_right
        self.key_down = key_down
        self.key_rotate = key_rotate
        self.key_hard_drop = key_hard_drop

        self.das_timer = 0.0
        self.arr_timer = 0.0
        self.active_key = None
        self.is_soft_dropping = False

    def handle_event(self, event, piece, board, sound_manager) -> str:
        """
        Handle a single Pygame event. Returns action string or 'none'.
        """
        if event.type == pygame.KEYDOWN:
            if event.key == self.key_left:
                self.active_key = self.key_left
                self.das_timer = 0.0
                if board.is_valid_move(piece, dx=-1):
                    piece.x -= 1
                    return "left"

            elif event.key == self.key_right:
                self.active_key = self.key_right
                self.das_timer = 0.0
                if board.is_valid_move(piece, dx=1):
                    piece.x += 1
                    return "right"

            elif event.key == self.key_down:
                self.is_soft_dropping = True
                if board.is_valid_move(piece, dy=1):
                    piece.y += 1
                    return "down"

            elif event.key == self.key_rotate:
                old_shape = [row[:] for row in piece.shape]
                old_x = piece.x
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
                        piece.x = old_x
                    else:
                        sound_manager.play("rotate")
                        return "rotate"
                else:
                    sound_manager.play("rotate")
                    return "rotate"

            elif event.key == self.key_hard_drop:
                return "drop"

        elif event.type == pygame.KEYUP:
            if event.key == self.key_down:
                self.is_soft_dropping = False
            elif event.key == self.active_key:
                self.active_key = None

        return "none"

    def update(self, dt_ms, piece, board) -> str:
        """
        Update DAS/ARR timers for held keys.
        """
        if not self.active_key:
            return "none"

        self.das_timer += dt_ms
        if self.das_timer >= DAS_DELAY_MS:
            self.arr_timer += dt_ms
            if self.arr_timer >= ARR_DELAY_MS:
                self.arr_timer = 0.0
                if self.active_key == self.key_left and board.is_valid_move(piece, dx=-1):
                    piece.x -= 1
                    return "left"
                elif self.active_key == self.key_right and board.is_valid_move(piece, dx=1):
                    piece.x += 1
                    return "right"
        return "none"
