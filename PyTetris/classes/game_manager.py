from classes.board import Board
from classes.player import Player
from classes.bot import Bot
from utils.score_manager import ScoreManager
from utils.bag_generator import BagGenerator
from constants import GARBAGE_TABLE


class _NullSound:
    """Drop-in replacement for AudioManager that does nothing."""
    def play(self, _key): pass
    def stop(self, _key=None): pass


_NULL_SOUND = _NullSound()


class GameManager:
    def __init__(self, bot_config, bot_weights):
        # ── Each side gets its own independent 7-bag generator ──────────────
        self.player_bag = BagGenerator()
        self.bot_bag    = BagGenerator()

        self.player_board = Board()
        self.bot_board    = Board()

        from pygame import K_LEFT, K_RIGHT, K_DOWN, K_UP, K_SPACE
        self.player = Player(K_LEFT, K_RIGHT, K_DOWN, K_UP, K_SPACE)
        self.bot    = Bot(bot_config, bot_weights)

        self.player_score = ScoreManager()
        self.bot_score    = ScoreManager()

        self.player_piece      = self.player_bag.get_next()
        self.player_next_piece = self.player_bag.get_next()

        self.bot_piece      = self.bot_bag.get_next()
        self.bot_next_piece = self.bot_bag.get_next()

        self.winner = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _apply_garbage(self, board):
        if board.pending_garbage > 0:
            board.add_garbage(board.pending_garbage)
            board.pending_garbage = 0

    # ── Piece locks ───────────────────────────────────────────────────────────

    def lock_player_piece(self, sound_manager=None):
        """Lock player piece, send garbage to bot.
        sound_manager=None → silence (battle mode: pass None to mute)."""
        sfx = sound_manager if sound_manager is not None else _NULL_SOUND

        self.player_board.place_tetromino(self.player_piece)
        lines = self.player_board.clear_lines()

        if lines > 0:
            sfx.play("clear")
            self.player_score.add_score(lines)
            garbage = GARBAGE_TABLE[lines]
            if garbage > 0:
                self.bot_board.pending_garbage += garbage
        else:
            sfx.play("drop")

        self._apply_garbage(self.player_board)

        self.player_piece      = self.player_next_piece
        self.player_next_piece = self.player_bag.get_next()

        if self.player_board.is_game_over():
            self.winner = "bot"

    def lock_bot_piece(self, sound_manager=None):
        """Lock bot piece, send garbage to player.
        sound_manager=None → silence bot SFX entirely."""
        # Bot sounds are intentionally silenced — bot clears lines so fast
        # that audio mixer saturates and causes lag.
        self.bot_board.place_tetromino(self.bot_piece)
        lines = self.bot_board.clear_lines()

        if lines > 0:
            self.bot_score.add_score(lines)
            garbage = GARBAGE_TABLE[lines]
            if garbage > 0:
                self.player_board.pending_garbage += garbage

        self._apply_garbage(self.bot_board)

        self.bot_piece      = self.bot_next_piece
        self.bot_next_piece = self.bot_bag.get_next()
        self.bot.reset()

        if self.bot_board.is_game_over():
            self.winner = "player"
