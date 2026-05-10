"""
constants.py — PyTetris global constants.

Single source of truth for every magic number in the project.
All tuning knobs (bot delays, heuristic weights, DAS/ARR) live here
so difficulty adjustments never require touching game logic.
"""

# ── Grid ──────────────────────────────────────────────────────────────────────
BOARD_WIDTH  = 15
BOARD_HEIGHT = 25
BLOCK_SIZE   = 30

# ── Window ────────────────────────────────────────────────────────────────────
# Classic mode: board + one right panel
PANEL_WIDTH       = 300
SCREEN_WIDTH      = BOARD_WIDTH * BLOCK_SIZE + PANEL_WIDTH   # 750
SCREEN_HEIGHT     = BOARD_HEIGHT * BLOCK_SIZE                # 750

# Battle mode: two boards + centre panel
BATTLE_SIDE_PANEL = 220          # width of each stat column (left/right)
BATTLE_MID_PANEL  = 200          # centre column (scores + next pieces)
BATTLE_WIDTH      = (BOARD_WIDTH * BLOCK_SIZE) * 2 + BATTLE_MID_PANEL  # 1100
# BATTLE_HEIGHT == SCREEN_HEIGHT (same grid height)

# ── Palette ───────────────────────────────────────────────────────────────────
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
GRAY        = (128, 128, 128)
DARK_GRAY   = (40,  40,  40)
BLUE        = (0,   0,   255)
PURE_BLUE   = (0,   255, 255)
YELLOW      = (255, 255, 0)
PURPLE      = (128, 0,   128)
GREEN       = (0,   200, 0)
BRIGHT_GREEN= (0,   255, 0)
RED         = (255, 0,   0)
ORANGE      = (255, 165, 0)
PINK        = (255, 192, 203)

# UI colours (shared across scenes)
UI_BG        = (18,  18,  22)
PANEL_BG     = (28,  28,  35)
PANEL_BORDER = (55,  55,  70)
BTN_NORMAL   = (50,  50,  60)
BTN_HOVER    = (70,  70,  85)
BTN_GREEN    = (40,  160, 60)
BTN_GREEN_HV = (55,  190, 75)
BTN_RED      = (180, 40,  40)
BTN_RED_HV   = (210, 55,  55)
TEXT_DIM     = (140, 140, 160)
GOLD         = (255, 200, 50)
ACCENT_BLUE   = (60,  120, 255)
ACCENT_RED    = (220, 50,  50)
ACCENT_ORANGE = (255, 140,  30)
GARBAGE_COLOR = (80,  80,  90)    # colour key 'G' rendered on board

# Piece colours
COLORS = {
    'I': PURE_BLUE,
    'O': YELLOW,
    'T': PINK,
    'S': BRIGHT_GREEN,
    'Z': RED,
    'J': BLUE,
    'L': ORANGE,
    'G': GARBAGE_COLOR,   # garbage line cell — added for battle mode
}

# ── Engine ────────────────────────────────────────────────────────────────────
FPS                = 60
INITIAL_FALL_SPEED = 0.8   # seconds per one-cell drop at level 1

def fall_speed_for_level(level: int) -> float:
    """Gravity curve: subtract 0.07 s per level, floor at 0.05 s."""
    return max(0.05, INITIAL_FALL_SPEED - (level - 1) * 0.07)

# ── Scoring table ─────────────────────────────────────────────────────────────
# Index = lines cleared in one lock event (0..4).
# Multiply by current level to get final points.
#
#   0 lines →    0 pts   (no reward)
#   1 line  →   40 pts   Single
#   2 lines →  100 pts   Double
#   3 lines →  300 pts   Triple
#   4 lines → 1200 pts   Tetris
#
SCORE_TABLE = [0, 40, 100, 300, 1200]

# Garbage lines sent to opponent per clear (Battle Mode only).
# Index = lines cleared.  0-and-1-line clears send nothing.
#
#   0 lines → 0 garbage
#   1 line  → 0 garbage
#   2 lines → 1 garbage   Double
#   3 lines → 2 garbage   Triple
#   4 lines → 4 garbage   Tetris
#
GARBAGE_TABLE = [0, 0, 1, 2, 4]

# ── Audio paths ───────────────────────────────────────────────────────────────
SOUNDS_DIR     = "sounds"
CLEAR_SOUND    = f"{SOUNDS_DIR}/clear.wav"
DROP_SOUND     = f"{SOUNDS_DIR}/drop.wav"
ROTATE_SOUND   = f"{SOUNDS_DIR}/rotate.wav"
LEVELUP_SOUND  = f"{SOUNDS_DIR}/level_up.wav"
GAMEOVER_SOUND = f"{SOUNDS_DIR}/game_over.wav"
BG_MUSIC       = f"{SOUNDS_DIR}/bg_music.wav"

# ── Audio channel pool ────────────────────────────────────────────────────────
# Total Pygame mixer channels reserved for SFX.
# Each sound key gets its own dedicated channel so it never steals another.
AUDIO_CHANNELS = 8

# Minimum milliseconds between two plays of the *same* sound key.
# Prevents the doubled-clear-at-same-frame clipping problem.
# Lower = more responsive; higher = more protection against clipping.
AUDIO_THROTTLE_MS: dict = {
    "clear":    80,
    "drop":     40,
    "rotate":   30,
    "levelup": 200,
    "gameover": 500,
}

# ── DAS / ARR (Delayed Auto Shift / Auto Repeat Rate) ────────────────────────
# Applied to the human player only.
#
# DAS  = time (ms) before held key starts repeating
# ARR  = time (ms) between each repeat once DAS fires
# SOFT = gravity multiplier while ↓ is held (1.0 = normal speed)
#
DAS_DELAY_MS  = 160    # ms before auto-repeat starts
ARR_DELAY_MS  =  50    # ms between each auto-repeat step
SOFT_DROP_MULT = 20.0  # how many times faster soft-drop is vs gravity

# ── Bot difficulty configs ────────────────────────────────────────────────────
#
# Each config is a plain dict consumed by classes/bot.py.
# Add new difficulties here without touching bot.py.
#
# delay_move_ms   : ms the bot waits between each horizontal nudge / rotation
# delay_drop_ms   : ms the bot waits before executing the hard drop
# lookahead       : 0 = current piece only; 1 = also considers next piece
# mistake_chance  : probability [0.0, 1.0] of picking 2nd-best move instead
#                   of best (simulates human imperfection)
# instant_garbage : if True, counterplay garbage immediately (God mode)
#
BOT_NORMAL = {
    "delay_move_ms"  : 200,
    "delay_drop_ms"  : 500,
    "lookahead"      : 0,
    "mistake_chance" : 0.12,   # ~1-in-8 moves are sub-optimal
    "instant_garbage": False,
}

BOT_MEDIUM = {
    "delay_move_ms"  : 100,
    "delay_drop_ms"  : 250,
    "lookahead"      : 1,      # sees next piece
    "mistake_chance" : 0.05,   # rarely makes mistakes
    "instant_garbage": False,
}

BOT_HARD = {
    "delay_move_ms"  : 30,
    "delay_drop_ms"  : 80,
    "lookahead"      : 1,
    "mistake_chance" : 0.01,   # almost perfect
    "instant_garbage": True,
}

BOT_INVINCIBLE = {
    "delay_move_ms"  : 0,
    "delay_drop_ms"  : 0,
    "lookahead"      : 1,      # evaluates current + next piece together
    "mistake_chance" : 0.0,    # never makes a mistake
    "instant_garbage": True,
}

# ── Heuristic weights ─────────────────────────────────────────────────────────
#
# The evaluation function is:
#
#   score = w_lines   * complete_lines
#         + w_holes   * hole_count          (negative = penalise)
#         + w_height  * aggregate_height    (negative = penalise)
#         + w_bump    * bumpiness           (negative = penalise)
#         + w_tetris  * tetris_ready_bonus  (extra reward, invincible only)
#
# Positive weight → bot tries to MAXIMISE that term.
# Negative weight → bot tries to MINIMISE that term.
#
HEURISTIC_NORMAL = {
    "w_lines" :  3.0,
    "w_holes" : -7.0,
    "w_height": -0.5,
    "w_bump"  : -1.8,
    "w_tetris":  0.0,   # normal bot doesn't specifically hunt Tetrises
}

HEURISTIC_MEDIUM = {
    "w_lines" :  3.5,
    "w_holes" : -9.0,
    "w_height": -0.6,
    "w_bump"  : -2.0,
    "w_tetris":  2.0,
}

HEURISTIC_HARD = {
    "w_lines" :  4.0,
    "w_holes" : -11.0,
    "w_height": -0.75,
    "w_bump"  : -2.3,
    "w_tetris":  5.0,
}

HEURISTIC_INVINCIBLE = {
    "w_lines" :  4.0,
    "w_holes" : -12.0,  # extreme hole penalty — never buries
    "w_height":  -0.8,
    "w_bump"  :  -2.5,  # very flat surface for 4-wide well
    "w_tetris":  6.0,   # actively builds and clears Tetrises
}

# ── Bot difficulty map (used by BattleScene) ─────────────────────────────────
BOT_CONFIGS = {
    "medium": (BOT_MEDIUM,     HEURISTIC_MEDIUM),
    "hard":   (BOT_HARD,       HEURISTIC_HARD),
}