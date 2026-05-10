import pygame
import sys
import math
import random
from constants import *
from classes.game_manager import GameManager
from classes.audio_manager import AudioManager
from classes.settings import settings
from classes.classic_scene import (draw_rounded, draw_block, draw_ghost_block,
                                   get_board_bg, render_text,
                                   Button, ToggleButton, SettingsOverlay)


# ─── Screen-shake helper ──────────────────────────────────────────────────────

class ScreenShake:
    def __init__(self):
        self._timer    = 0      # remaining frames
        self._strength = 0      # max pixel offset
        self._decay    = 0.85   # strength multiplier per frame

    def trigger(self, strength=10, duration=18):
        self._strength = strength
        self._timer    = duration

    def get_offset(self):
        if self._timer <= 0:
            return (0, 0)
        self._timer    -= 1
        self._strength *= self._decay
        angle = random.uniform(0, math.tau)
        r     = self._strength
        return (int(math.cos(angle) * r), int(math.sin(angle) * r))


# ─── Difficulty selector overlay ─────────────────────────────────────────────

class DifficultyOverlay:
    """Pre-game overlay to pick bot difficulty before battle starts."""

    CONFIGS = {
        "medium": {
            "label": "MEDIUM",
            "color": (50, 160, 50),
            "hover": (70, 200, 70),
            "desc":  ["• 1-ply lookahead", "• Rarely makes mistakes", "• No instant garbage"],
        },
        "hard": {
            "label": "HARD",
            "color": (200, 80, 20),
            "hover": (240, 110, 40),
            "desc":  ["• 1-ply lookahead", "• Almost perfect play", "• Instant garbage counter"],
        },
    }

    def __init__(self, screen, font_sm, font_md, font_lg, font_xl, on_start, on_back):
        self.screen   = screen
        self.font_sm  = font_sm
        self.font_md  = font_md
        self.font_lg  = font_lg
        self.font_xl  = font_xl
        self.on_start = on_start
        self.on_back  = on_back
        self._build()

    def _build(self):
        w, h = self.screen.get_size()
        cx = w // 2
        card_w, card_h = 260, 220
        gap = 30

        total = card_w * 2 + gap
        left_x = cx - total // 2

        self.cards = {}
        for i, (key, cfg) in enumerate(self.CONFIGS.items()):
            x = left_x + i * (card_w + gap)
            y = h // 2 - card_h // 2 - 10
            btn = Button(x, y + card_h + 14, card_w, 44,
                         f"▶  {cfg['label']}",
                         cfg["color"], cfg["hover"], self.font_md, radius=10)
            self.cards[key] = {"rect": pygame.Rect(x, y, card_w, card_h),
                               "btn": btn, "cfg": cfg}

        self.btn_back = Button(cx - 90, h // 2 + card_h // 2 + 70,
                               180, 44, "← BACK", BTN_NORMAL, BTN_HOVER, self.font_sm)

    def handle_event(self, event):
        for key, card in self.cards.items():
            if card["btn"].is_clicked(event):
                settings.bot_difficulty = key
                self.on_start(key)
        if self.btn_back.is_clicked(event):
            self.on_back()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.on_back()

    def draw(self):
        w, h = self.screen.get_size()
        cx = w // 2

        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        title = self.font_xl.render("BATTLE MODE", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(cx, h // 2 - 180)))

        sub = self.font_sm.render("Choose bot difficulty", True, TEXT_DIM)
        self.screen.blit(sub, sub.get_rect(center=(cx, h // 2 - 130)))

        for key, card in self.cards.items():
            r = card["rect"]
            is_sel = settings.bot_difficulty == key
            border_c = GOLD if is_sel else PANEL_BORDER
            draw_rounded(self.screen, PANEL_BG, r, 14, 2, border_c)

            cfg = card["cfg"]
            lbl = self.font_lg.render(cfg["label"], True,
                                      cfg["color"] if not is_sel else GOLD)
            self.screen.blit(lbl, lbl.get_rect(center=(r.centerx, r.y + 40)))

            for di, line in enumerate(cfg["desc"]):
                dl = self.font_sm.render(line, True, TEXT_DIM)
                self.screen.blit(dl, dl.get_rect(center=(r.centerx, r.y + 90 + di * 28)))

            if is_sel:
                star = self.font_sm.render("★ SELECTED", True, GOLD)
                self.screen.blit(star, star.get_rect(center=(r.centerx, r.bottom - 18)))

            card["btn"].draw(self.screen)

        self.btn_back.draw(self.screen)


# ─── Battle Scene ─────────────────────────────────────────────────────────────

class BattleScene:
    STATE_DIFFICULTY = "difficulty"
    STATE_PLAYING    = "playing"
    STATE_PAUSED     = "paused"
    STATE_GAMEOVER   = "gameover"
    STATE_SETTINGS   = "settings"

    def __init__(self, screen, clock, app):
        self.screen = screen
        self.clock  = clock
        self.app    = app

        self.font_sm = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_md = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_lg = pygame.font.SysFont("Arial", 48, bold=True)
        self.font_xl = pygame.font.SysFont("Arial", 72, bold=True)

        self.sound = AudioManager()
        self.shake = ScreenShake()
        self.state = self.STATE_DIFFICULTY

        self._diff_overlay = DifficultyOverlay(
            screen, self.font_sm, self.font_md, self.font_lg, self.font_xl,
            on_start=self._start_battle,
            on_back=lambda: self.app.switch_scene("classic"),
        )
        self._settings_overlay = SettingsOverlay(
            screen, self.font_sm, self.font_md, self.font_lg,
            on_close=lambda: setattr(self, "state", self._prev_state),
        )
        self._prev_state = self.STATE_PLAYING

        self.gm = None
        self._game_surf = None   # allocated once on first draw, reused thereafter
        self._build_buttons()
        self._bot_locking = False

    def _build_buttons(self):
        cx = BATTLE_WIDTH // 2
        py0 = SCREEN_HEIGHT // 2 - 80
        self.btn_resume   = Button(cx-100, py0,       200, 44, "RESUME",
                                   BTN_GREEN, BTN_GREEN_HV, self.font_sm)
        self.btn_settings_pause = Button(cx-100, py0+56,  200, 44, "⚙  SETTINGS",
                                         BTN_NORMAL, BTN_HOVER, self.font_sm)
        self.btn_quit     = Button(cx-100, py0+112,   200, 44, "QUIT",
                                   BTN_NORMAL, BTN_HOVER, self.font_sm)
        self.btn_restart  = Button(cx-100, SCREEN_HEIGHT//2+70,  200, 44, "PLAY AGAIN",
                                   BTN_GREEN, BTN_GREEN_HV, self.font_sm)
        self.btn_menu     = Button(cx-100, SCREEN_HEIGHT//2+125, 200, 44, "MAIN MENU",
                                   BTN_NORMAL, BTN_HOVER, self.font_sm)

    def _start_battle(self, difficulty: str):
        bot_cfg, bot_weights = BOT_CONFIGS[difficulty]
        self.gm = GameManager(bot_cfg, bot_weights)
        self.player_fall_time  = 0.0
        self.player_fall_speed = fall_speed_for_level(1)
        self.bot_fall_time     = 0.0
        self.bot_fall_speed    = fall_speed_for_level(1)
        self._bot_locking      = False
        self._game_surf        = None   # reset so it's reallocated at new resolution
        self.state = self.STATE_PLAYING

    # ── Board drawing ─────────────────────────────────────────────────────────

    def _draw_board(self, board, piece, offset_x):
        # Blit pre-rendered grid background
        self.screen.blit(get_board_bg(board.width, board.height), (offset_x, 0))
        for y in range(board.height):
            for x in range(board.width):
                val = board.grid[y][x]
                if val != 0:
                    r = pygame.Rect(offset_x + x*BLOCK_SIZE, y*BLOCK_SIZE,
                                    BLOCK_SIZE, BLOCK_SIZE)
                    draw_block(self.screen, COLORS.get(val, GARBAGE_COLOR), r)

        # Ghost
        if settings.ghost_enabled:
            actual_y = piece.y
            ghost_y  = actual_y
            while board.is_valid_move(piece, dy=(ghost_y - actual_y + 1)):
                ghost_y += 1
            off = ghost_y - actual_y
            if off > 0:
                c = piece.color
                for px2, py2 in piece.get_positions():
                    dy = py2 + off
                    if dy >= 0:
                        r = pygame.Rect(offset_x + px2*BLOCK_SIZE,
                                        dy*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                        draw_ghost_block(self.screen, c, r)

        # Active piece
        for px2, py2 in piece.get_positions():
            if py2 >= 0:
                r = pygame.Rect(offset_x + px2*BLOCK_SIZE, py2*BLOCK_SIZE,
                                BLOCK_SIZE, BLOCK_SIZE)
                draw_block(self.screen, piece.color, r)

    def _draw_ui(self):
        cx = BATTLE_WIDTH // 2
        mid_x = BOARD_WIDTH * BLOCK_SIZE
        pygame.draw.rect(self.screen, PANEL_BG,
                         pygame.Rect(mid_x, 0, BATTLE_MID_PANEL, SCREEN_HEIGHT))

        # Title (static — cached after first render)
        lbl = render_text(self.font_md, "VS", WHITE)
        self.screen.blit(lbl, lbl.get_rect(center=(cx, 28)))

        diff_label = settings.bot_difficulty.upper()
        diff_color = (50, 200, 50) if diff_label == "MEDIUM" else (220, 100, 30)
        dl = render_text(self.font_sm, f"BOT: {diff_label}", diff_color)
        self.screen.blit(dl, dl.get_rect(center=(cx, 52)))

        pygame.draw.line(self.screen, PANEL_BORDER, (cx-80, 68), (cx+80, 68), 1)

        def draw_side(label, score, next_piece, label_color, y0):
            lbl2 = render_text(self.font_sm, label, label_color)
            self.screen.blit(lbl2, lbl2.get_rect(center=(cx, y0)))
            sc = render_text(self.font_md, str(score), WHITE)
            self.screen.blit(sc, sc.get_rect(center=(cx, y0 + 26)))
            nx_l = render_text(self.font_sm, "NEXT", TEXT_DIM)
            self.screen.blit(nx_l, nx_l.get_rect(center=(cx, y0 + 52)))
            cols = len(next_piece.shape[0]) if next_piece.shape else 4
            bx0 = cx - cols * BLOCK_SIZE // 2
            for ri, row in enumerate(next_piece.shape):
                for ci, cell in enumerate(row):
                    if cell:
                        r = pygame.Rect(bx0 + ci*BLOCK_SIZE,
                                        y0 + 72 + ri*BLOCK_SIZE,
                                        BLOCK_SIZE, BLOCK_SIZE)
                        draw_block(self.screen, next_piece.color, r)

        draw_side("PLAYER", self.gm.player_score.score,
                  self.gm.player_next_piece, ACCENT_BLUE, 78)
        pygame.draw.line(self.screen, PANEL_BORDER, (cx-80, 240), (cx+80, 240), 1)
        draw_side("BOT", self.gm.bot_score.score,
                  self.gm.bot_next_piece, ACCENT_RED, 250)

        # Garbage meters
        pygame.draw.line(self.screen, PANEL_BORDER, (cx-80, 415), (cx+80, 415), 1)
        self.screen.blit(render_text(self.font_sm, "INCOMING", TEXT_DIM),
                         render_text(self.font_sm, "INCOMING", TEXT_DIM).get_rect(center=(cx, 428)))

        pip_w, pip_h = 18, 10
        pg = self.gm.player_board.pending_garbage
        for i in range(min(pg, 8)):
            pygame.draw.rect(self.screen, ACCENT_BLUE,
                             pygame.Rect(cx - 76 + i*(pip_w+2), 444, pip_w, pip_h), border_radius=3)
        pg_c = ACCENT_BLUE if pg else TEXT_DIM
        pg_s = render_text(self.font_sm, f"P: {pg}", pg_c)
        self.screen.blit(pg_s, pg_s.get_rect(center=(cx, 462)))

        bg = self.gm.bot_board.pending_garbage
        for i in range(min(bg, 8)):
            pygame.draw.rect(self.screen, ACCENT_RED,
                             pygame.Rect(cx - 76 + i*(pip_w+2), 478, pip_w, pip_h), border_radius=3)
        bg_c = ACCENT_RED if bg else TEXT_DIM
        bg_s = render_text(self.font_sm, f"B: {bg}", bg_c)
        self.screen.blit(bg_s, bg_s.get_rect(center=(cx, 496)))

        # Controls (static — cached after first frame)
        pygame.draw.line(self.screen, PANEL_BORDER, (cx-80, 518), (cx+80, 518), 1)
        hints = [("←→","Move"),("↑","Rotate"),("SPC","Drop"),("P","Pause"),("TAB","Settings")]
        hy = 530
        for key, desc in hints:
            k = render_text(self.font_sm, key,  PURE_BLUE)
            d = render_text(self.font_sm, desc, TEXT_DIM)
            self.screen.blit(k, k.get_rect(right=cx-4, centery=hy))
            self.screen.blit(d, d.get_rect(left=cx+4,  centery=hy))
            hy += 22

    def _draw_pause(self):
        overlay = pygame.Surface((BATTLE_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))
        cx = BATTLE_WIDTH // 2
        panel = pygame.Rect(cx-120, SCREEN_HEIGHT//2-120, 240, 290)
        draw_rounded(self.screen, PANEL_BG, panel, 14, 1, PANEL_BORDER)
        t = self.font_lg.render("PAUSED", True, WHITE)
        self.screen.blit(t, t.get_rect(center=(cx, SCREEN_HEIGHT//2-85)))
        for btn in (self.btn_resume, self.btn_settings_pause, self.btn_quit):
            btn.draw(self.screen)

    def _draw_gameover(self):
        overlay = pygame.Surface((BATTLE_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        cx = BATTLE_WIDTH // 2
        panel = pygame.Rect(cx-170, SCREEN_HEIGHT//2-150, 340, 320)
        draw_rounded(self.screen, PANEL_BG, panel, 14, 1, PANEL_BORDER)

        if self.gm.winner == "player":
            win_text, win_color = "YOU WIN! 🏆", ACCENT_BLUE
        else:
            win_text, win_color = "BOT WINS!", ACCENT_RED

        go = self.font_lg.render(win_text, True, win_color)
        self.screen.blit(go, go.get_rect(center=(cx, SCREEN_HEIGHT//2-110)))

        diff_lbl = self.font_sm.render(f"Difficulty: {settings.bot_difficulty.upper()}",
                                       True, TEXT_DIM)
        self.screen.blit(diff_lbl, diff_lbl.get_rect(center=(cx, SCREEN_HEIGHT//2-70)))

        p_sc = self.font_md.render(f"Player: {self.gm.player_score.score}", True, WHITE)
        b_sc = self.font_md.render(f"Bot:    {self.gm.bot_score.score}",   True, WHITE)
        self.screen.blit(p_sc, p_sc.get_rect(center=(cx, SCREEN_HEIGHT//2-30)))
        self.screen.blit(b_sc, b_sc.get_rect(center=(cx, SCREEN_HEIGHT//2+5)))

        self.btn_restart.draw(self.screen)
        self.btn_menu.draw(self.screen)

    # ── Events ────────────────────────────────────────────────────────────────

    def handle_event(self, event):
        if self.state == self.STATE_DIFFICULTY:
            self._diff_overlay.handle_event(event)
            return

        if self.state == self.STATE_SETTINGS:
            self._settings_overlay.handle_event(event)
            return

        if self.state == self.STATE_GAMEOVER:
            if self.btn_restart.is_clicked(event):
                self.sound.play("drop")
                self._diff_overlay = DifficultyOverlay(
                    self.screen, self.font_sm, self.font_md,
                    self.font_lg, self.font_xl,
                    on_start=self._start_battle,
                    on_back=lambda: self.app.switch_scene("classic"),
                )
                self.state = self.STATE_DIFFICULTY
            elif self.btn_menu.is_clicked(event):
                self.sound.play("drop")
                self.app.switch_scene("classic")
            return

        if self.state == self.STATE_PAUSED:
            if self.btn_resume.is_clicked(event):
                self.sound.play("drop")
                self.state = self.STATE_PLAYING
            elif self.btn_settings_pause.is_clicked(event):
                self._prev_state = self.STATE_PAUSED
                self.state = self.STATE_SETTINGS
            elif self.btn_quit.is_clicked(event):
                self.sound.play("drop")
                self.app.switch_scene("classic")
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                self.state = self.STATE_PLAYING
            return

        if self.state == self.STATE_PLAYING:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.app.switch_scene("classic")
                    return
                if event.key == pygame.K_p:
                    self.state = self.STATE_PAUSED
                    return
                if event.key == pygame.K_TAB:
                    self._prev_state = self.STATE_PLAYING
                    self.state = self.STATE_SETTINGS
                    return

            action = self.gm.player.handle_event(
                event, self.gm.player_piece, self.gm.player_board, self.sound)
            if action == "drop":
                while self.gm.player_board.is_valid_move(self.gm.player_piece, dy=1):
                    self.gm.player_piece.y += 1
                self.gm.lock_player_piece(self.sound)
                self.player_fall_time = 0.0

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self):
        if self.state != self.STATE_PLAYING or self.gm is None:
            return
        dt_ms = self.clock.get_time()

        # Player gravity
        self.gm.player.update(dt_ms, self.gm.player_piece, self.gm.player_board)
        self.player_fall_time += dt_ms / 1000.0
        if self.player_fall_time >= self.player_fall_speed:
            self.player_fall_time = 0.0
            if self.gm.player_board.is_valid_move(self.gm.player_piece, dy=1):
                self.gm.player_piece.y += 1
            else:
                self.gm.lock_player_piece(self.sound)

        # Bot logic + gravity
        if not self._bot_locking:
            bot_action = self.gm.bot.tick(
                dt_ms, self.gm.bot_piece, self.gm.bot_board, self.gm.bot_next_piece)

            if bot_action == "drop":
                self._bot_locking = True
                while self.gm.bot_board.is_valid_move(self.gm.bot_piece, dy=1):
                    self.gm.bot_piece.y += 1
                self.gm.lock_bot_piece()   # no sound — bot is too fast
                self.bot_fall_time = 0.0
                self._bot_locking  = False
            # bot rotate sound intentionally omitted — too frequent at Hard difficulty
            elif self.gm.bot._state not in ("done", "thinking"):
                self.bot_fall_time += dt_ms / 1000.0
                if self.bot_fall_time >= self.bot_fall_speed:
                    self.bot_fall_time = 0.0
                    if not self.gm.bot_board.is_valid_move(self.gm.bot_piece, dy=1):
                        pass   # bot will handle drop

        if self.gm.winner:
            self.state = self.STATE_GAMEOVER
            self.sound.play("gameover")

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self):
        if self.state == self.STATE_DIFFICULTY:
            self.screen.fill(UI_BG)
            self._diff_overlay.draw()
            return

        # Use a persistent off-screen surface — never reallocate each frame
        if self._game_surf is None:
            self._game_surf = pygame.Surface(self.screen.get_size())
        self._game_surf.fill(UI_BG)

        bot_offset = BOARD_WIDTH * BLOCK_SIZE + BATTLE_MID_PANEL

        # Render boards + UI into the cached surface
        old_screen = self.screen
        self.screen = self._game_surf
        self._draw_board(self.gm.player_board, self.gm.player_piece, 0)
        self._draw_ui()
        self._draw_board(self.gm.bot_board, self.gm.bot_piece, bot_offset)
        self.screen = old_screen

        # Blit to real screen (no shake offset since we removed shake)
        old_screen.blit(self._game_surf, (0, 0))

        # Overlays on top
        if self.state == self.STATE_PAUSED:
            self._draw_pause()
        elif self.state == self.STATE_GAMEOVER:
            self._draw_gameover()
        elif self.state == self.STATE_SETTINGS:
            self._settings_overlay.draw()
