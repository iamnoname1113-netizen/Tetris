import pygame
import sys
from constants import *
from classes.tetromino import Tetromino
from classes.board import Board
from utils.score_manager import ScoreManager
from utils.bag_generator import BagGenerator
from classes.audio_manager import AudioManager
from classes.settings import settings


# ─── Shared drawing helpers ───────────────────────────────────────────────────

def draw_rounded(surf, color, rect, radius=10, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


# ─── Block surface cache ──────────────────────────────────────────────────────
# Key: (color_rgb, glow: bool)  →  Value: pre-rendered Surface
_block_cache: dict = {}
_ghost_cache: dict = {}   # Key: color_rgb → ghost Surface


def _make_block_surf(color: tuple, glow: bool) -> pygame.Surface:
    """Pre-render one block into a Surface (called once per unique color)."""
    s = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
    s.fill((*color, 255))

    if glow:
        bv = max(3, BLOCK_SIZE // 5)
        dot_r = max(2, BLOCK_SIZE // 7)

        # Top highlight strip
        hi = pygame.Surface((BLOCK_SIZE, bv), pygame.SRCALPHA)
        hi.fill((255, 255, 255, 60))
        s.blit(hi, (0, 0))

        # Left highlight strip
        ls = pygame.Surface((bv, BLOCK_SIZE), pygame.SRCALPHA)
        ls.fill((255, 255, 255, 40))
        s.blit(ls, (0, 0))

        # Bottom shadow strip
        bs = pygame.Surface((BLOCK_SIZE, bv), pygame.SRCALPHA)
        bs.fill((0, 0, 0, 80))
        s.blit(bs, (0, BLOCK_SIZE - bv))

        # Right shadow strip
        rs = pygame.Surface((bv, BLOCK_SIZE), pygame.SRCALPHA)
        rs.fill((0, 0, 0, 60))
        s.blit(rs, (BLOCK_SIZE - bv, 0))

        # Glint dot
        dot_surf = pygame.Surface((dot_r * 2, dot_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(dot_surf, (255, 255, 255, 90), (dot_r, dot_r), dot_r)
        s.blit(dot_surf, (BLOCK_SIZE // 4, BLOCK_SIZE // 4))

    # Border
    pygame.draw.rect(s, WHITE, s.get_rect(), 1)
    return s


def _make_ghost_surf(color: tuple) -> pygame.Surface:
    s = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
    gc = (color[0]//3, color[1]//3, color[2]//3, 110)
    s.fill(gc)
    border_c = (color[0]//2, color[1]//2, color[2]//2)
    pygame.draw.rect(s, border_c, s.get_rect(), 1)
    return s


def invalidate_block_cache():
    """Call whenever BLOCK_SIZE or glow setting changes."""
    _block_cache.clear()
    _ghost_cache.clear()


def draw_block(surf, color: tuple, rect: pygame.Rect, glow: bool = True):
    """Blit a pre-rendered block surface. O(1) per call after first render."""
    use_glow = glow and settings.glow_enabled
    key = (color, use_glow)
    cached = _block_cache.get(key)
    if cached is None:
        cached = _make_block_surf(color, use_glow)
        _block_cache[key] = cached
    surf.blit(cached, rect.topleft)


def draw_ghost_block(surf, color: tuple, rect: pygame.Rect):
    """Blit a pre-rendered ghost block surface."""
    cached = _ghost_cache.get(color)
    if cached is None:
        cached = _make_ghost_surf(color)
        _ghost_cache[color] = cached
    surf.blit(cached, rect.topleft)


# ─── Board background cache ───────────────────────────────────────────────────
# Pre-render the dark background + grid lines once per unique board size.
# Eliminates ~375 pygame.draw.rect calls per board per frame.
_board_bg_cache: dict = {}

def get_board_bg(width_cells: int, height_cells: int) -> pygame.Surface:
    key = (width_cells, height_cells)
    s = _board_bg_cache.get(key)
    if s is None:
        s = pygame.Surface((width_cells * BLOCK_SIZE, height_cells * BLOCK_SIZE))
        s.fill((10, 10, 14))
        for y in range(height_cells):
            for x in range(width_cells):
                pygame.draw.rect(s, (22, 22, 28),
                                 pygame.Rect(x * BLOCK_SIZE, y * BLOCK_SIZE,
                                             BLOCK_SIZE, BLOCK_SIZE), 1)
        _board_bg_cache[key] = s
    return s


# ─── Text surface cache ───────────────────────────────────────────────────────
# font.render() is slow; cache by (font_id, text, color).
# Static labels render once. Dynamic numbers cache per unique value string.
_text_cache: dict = {}

def render_text(font, text: str, color: tuple) -> pygame.Surface:
    key = (id(font), text, color)
    s = _text_cache.get(key)
    if s is None:
        s = font.render(text, True, color)
        _text_cache[key] = s
    return s


class Button:
    def __init__(self, x, y, w, h, text, color=BTN_NORMAL, hover=BTN_HOVER, font=None, radius=8):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover
        self.font = font
        self.radius = radius

    def draw(self, surf):
        mx, my = pygame.mouse.get_pos()
        is_hovered = self.rect.collidepoint(mx, my)
        c = self.hover_color if is_hovered else self.color

        # Shadow
        shadow = self.rect.move(3, 3)
        pygame.draw.rect(surf, (0, 0, 0, 100), shadow, border_radius=self.radius)

        draw_rounded(surf, c, self.rect, self.radius, 1, PANEL_BORDER)

        if is_hovered:
            hi = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
            hi.fill((255, 255, 255, 18))
            surf.blit(hi, self.rect.topleft)

        lbl = self.font.render(self.text, True, WHITE)
        surf.blit(lbl, lbl.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))


class ToggleButton(Button):
    """Button that shows ON/OFF state."""
    def __init__(self, x, y, w, h, label, get_fn, set_fn, font=None, radius=8):
        super().__init__(x, y, w, h, label, BTN_NORMAL, BTN_HOVER, font, radius)
        self.label = label
        self.get_fn = get_fn
        self.set_fn = set_fn

    def draw(self, surf):
        val = self.get_fn()
        self.color = BTN_GREEN if val else (60, 40, 40)
        self.hover_color = BTN_GREEN_HV if val else (90, 50, 50)
        self.text = f"{self.label}: {'ON' if val else 'OFF'}"
        super().draw(surf)

    def is_clicked(self, event):
        if super().is_clicked(event):
            self.set_fn(not self.get_fn())
            return True
        return False


# ─── Settings screen (reused by both Classic and Battle) ─────────────────────

class SettingsOverlay:
    """Full-screen settings panel drawn on top of whatever scene is behind it."""

    def __init__(self, screen, font_sm, font_md, font_lg, on_close):
        self.screen = screen
        self.font_sm = font_sm
        self.font_md = font_md
        self.font_lg = font_lg
        self.on_close = on_close
        self._build(screen.get_width(), screen.get_height())

    def _build(self, w, h):
        cx = w // 2
        btn_w, btn_h, gap = 320, 46, 10
        x0 = cx - btn_w // 2
        y0 = h // 2 - 160

        def make(i, label, getter, setter):
            return ToggleButton(x0, y0 + i*(btn_h+gap), btn_w, btn_h,
                                label, getter, setter, self.font_sm)

        self.toggles = [
            make(0, "Sound FX",
                 lambda: settings.sound_enabled,
                 lambda v: setattr(settings, "sound_enabled", v)),
            make(1, "Music",
                 lambda: settings.music_enabled,
                 lambda v: setattr(settings, "music_enabled", v)),
            make(2, "Visual Effects",
                 lambda: settings.effects_enabled,
                 lambda v: setattr(settings, "effects_enabled", v)),
            make(3, "Ghost Piece",
                 lambda: settings.ghost_enabled,
                 lambda v: setattr(settings, "ghost_enabled", v)),
            make(4, "Block Glow",
                 lambda: settings.glow_enabled,
                 lambda v: (setattr(settings, "glow_enabled", v), invalidate_block_cache())),
            make(5, "Screen Shake",
                 lambda: settings.shake_enabled,
                 lambda v: setattr(settings, "shake_enabled", v)),
        ]

        self.btn_close = Button(cx - 90, y0 + 6*(btn_h+gap) + 10, 180, 44,
                                "← BACK", BTN_NORMAL, BTN_HOVER, self.font_sm)

    def handle_event(self, event):
        for t in self.toggles:
            t.is_clicked(event)
        if self.btn_close.is_clicked(event):
            self.on_close()
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_TAB):
            self.on_close()

    def draw(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        cx = self.screen.get_width() // 2
        t = self.font_lg.render("SETTINGS", True, WHITE)
        self.screen.blit(t, t.get_rect(center=(cx, self.screen.get_height()//2 - 210)))

        for tog in self.toggles:
            tog.draw(self.screen)
        self.btn_close.draw(self.screen)


# ─── Classic Scene ────────────────────────────────────────────────────────────

class ClassicScene:
    STATE_MENU     = "menu"
    STATE_PLAYING  = "playing"
    STATE_PAUSED   = "paused"
    STATE_GAMEOVER = "gameover"
    STATE_SETTINGS = "settings"

    def __init__(self, screen, clock, app):
        self.screen = screen
        self.clock  = clock
        self.app    = app
        self.font_sm = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_md = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_lg = pygame.font.SysFont("Arial", 48, bold=True)
        self.font_xl = pygame.font.SysFont("Arial", 72, bold=True)
        self.sound         = AudioManager()
        self.score_manager = ScoreManager()
        self.state         = self.STATE_MENU
        self._init_game_objects()
        self._build_buttons()
        self.drop_trail   = []
        self._settings_overlay = SettingsOverlay(
            screen, self.font_sm, self.font_md, self.font_lg,
            on_close=lambda: setattr(self, "state", self._prev_state)
        )
        self._prev_state = self.STATE_MENU

    # ── Initialisation ────────────────────────────────────────────────────────

    def _init_game_objects(self):
        self.board         = Board()
        self.bag_generator = BagGenerator()
        self.current_piece = self.bag_generator.get_next()
        self.next_piece    = self.bag_generator.get_next()
        self.fall_time     = 0.0
        self.fall_speed    = fall_speed_for_level(1)
        self.drop_trail    = []

    def _build_buttons(self):
        cx = SCREEN_WIDTH // 2
        self.btn_play   = Button(cx-110, 0, 220, 50, "PLAY CLASSIC",
                                 BTN_GREEN,  BTN_GREEN_HV,  self.font_md, 10)
        self.btn_battle = Button(cx-110, 0, 220, 50, "BATTLE MODE",
                                 BTN_RED,    BTN_RED_HV,    self.font_md, 10)
        self.btn_settings_menu = Button(cx-110, 0, 220, 46, "⚙  SETTINGS",
                                        BTN_NORMAL, BTN_HOVER, self.font_sm, 8)

        py0 = SCREEN_HEIGHT // 2 - 60
        self.btn_resume  = Button(cx-100, py0,       200, 44, "RESUME",
                                  BTN_GREEN, BTN_GREEN_HV, self.font_sm, 8)
        self.btn_quit    = Button(cx-100, py0+56,    200, 44, "QUIT",
                                  BTN_NORMAL, BTN_HOVER,   self.font_sm, 8)
        self.btn_settings_pause = Button(cx-100, py0+112, 200, 44, "⚙  SETTINGS",
                                         BTN_NORMAL, BTN_HOVER, self.font_sm, 8)

        self.btn_restart = Button(cx-100, SCREEN_HEIGHT//2+60,  200, 44, "PLAY AGAIN",
                                  BTN_GREEN, BTN_GREEN_HV, self.font_sm, 8)
        self.btn_menu    = Button(cx-100, SCREEN_HEIGHT//2+115, 200, 44, "MAIN MENU",
                                  BTN_NORMAL, BTN_HOVER,   self.font_sm, 8)

    # ── Ghost & trail ─────────────────────────────────────────────────────────

    def _get_ghost_y(self):
        gy = self.current_piece.y
        while self.board.is_valid_move(self.current_piece, dy=(gy - self.current_piece.y + 1)):
            gy += 1
        return gy

    def _draw_ghost(self):
        if not settings.ghost_enabled:
            return
        ghost_y = self._get_ghost_y()
        off = ghost_y - self.current_piece.y
        if off == 0:
            return
        c = self.current_piece.color
        for x, y in self.current_piece.get_positions():
            dy = y + off
            if dy >= 0:
                r = pygame.Rect(x*BLOCK_SIZE, dy*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                draw_ghost_block(self.screen, c, r)

    def _spawn_trail(self):
        if not settings.effects_enabled:
            return
        color = self.current_piece.color
        ghost_y = self._get_ghost_y()
        off = ghost_y - self.current_piece.y
        if off == 0:
            return
        for x, y in self.current_piece.get_positions():
            for step in range(1, off + 1):
                ty = y + step
                if 0 <= ty < BOARD_HEIGHT:
                    ratio = step / off
                    alpha = int(200 * (1.0 - ratio * 0.7))
                    self.drop_trail.append([x, ty, alpha, color])

    def _update_trail(self):
        self.drop_trail = [t for t in self.drop_trail if t[2] > 0]
        for t in self.drop_trail:
            t[2] = max(0, t[2] - 28)

    def _draw_trail(self):
        # Reuse a single surface per unique alpha bucket to avoid per-frame allocs
        for x, y, alpha, color in self.drop_trail:
            r = pygame.Rect(x*BLOCK_SIZE, y*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
            key = (color, min(alpha, 130) // 10)  # quantise alpha to 14 buckets
            cached = _block_cache.get(('trail', key))
            if cached is None:
                cached = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
                cached.fill((*color, min(alpha, 130)))
                _block_cache[('trail', key)] = cached
            self.screen.blit(cached, r.topleft)

    # ── Board / UI drawing ────────────────────────────────────────────────────

    def draw_board(self):
        # Blit pre-rendered background (grid lines rendered once, not every frame)
        self.screen.blit(get_board_bg(self.board.width, self.board.height), (0, 0))
        for y in range(self.board.height):
            for x in range(self.board.width):
                val = self.board.grid[y][x]
                if val != 0:
                    r = pygame.Rect(x*BLOCK_SIZE, y*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                    draw_block(self.screen, COLORS.get(val, GARBAGE_COLOR), r)

        self._draw_trail()
        self._draw_ghost()

        for x, y in self.current_piece.get_positions():
            if y >= 0:
                r = pygame.Rect(x*BLOCK_SIZE, y*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                draw_block(self.screen, self.current_piece.color, r)

    def _panel_box(self, x, y, w, h, title=None):
        r = pygame.Rect(x, y, w, h)
        draw_rounded(self.screen, PANEL_BG, r, 10, 1, PANEL_BORDER)
        if title:
            lbl = render_text(self.font_sm, title, TEXT_DIM)
            self.screen.blit(lbl, (x + w//2 - lbl.get_width()//2, y + 8))

    def draw_ui(self):
        px = BOARD_WIDTH * BLOCK_SIZE
        pw = PANEL_WIDTH
        m  = 14

        # Score / Level / Lines
        for i, (lbl, val) in enumerate([
            ("SCORE", self.score_manager.score),
            ("LEVEL", self.score_manager.level),
            ("LINES", self.score_manager.lines),
        ]):
            bx, by = px + m, m + i * 68
            self._panel_box(bx, by, pw - m*2, 58, lbl)
            v = render_text(self.font_md, str(val), WHITE)
            self.screen.blit(v, (bx + (pw-m*2)//2 - v.get_width()//2, by + 28))

        # Next piece
        ny = m + 3*68 + 10
        self._panel_box(px+m, ny, pw-m*2, 110, "NEXT")
        ox, oy = px + m + 30, ny + 30
        for ri, row in enumerate(self.next_piece.shape):
            for ci, cell in enumerate(row):
                if cell:
                    r = pygame.Rect(ox+ci*BLOCK_SIZE, oy+ri*BLOCK_SIZE,
                                    BLOCK_SIZE, BLOCK_SIZE)
                    draw_block(self.screen, self.next_piece.color, r)

        # High scores
        hs_y = ny + 120
        hs_h = 30 + len(self.score_manager.high_scores)*26 + 10
        self._panel_box(px+m, hs_y, pw-m*2, hs_h, "HIGH SCORES")
        for i, (_, sc) in enumerate(self.score_manager.high_scores):
            color = GOLD if i == 0 else TEXT_DIM
            txt = render_text(self.font_sm, str(sc), color)
            self.screen.blit(txt, (px+pw-m*2-txt.get_width(), hs_y+30+i*26))

        # Controls hints (static — cached after first frame)
        hints = [("←→","MOVE"),("↑","ROTATE"),("↓","SOFT DROP"),
                 ("SPC","Hard drop"),("P","Pause"),("ESC","Menu")]
        hy = hs_y + hs_h + 10
        for key, desc in hints:
            k = render_text(self.font_sm, key,  PURE_BLUE)
            d = render_text(self.font_sm, desc, TEXT_DIM)
            self.screen.blit(k, (px+m+5,  hy))
            self.screen.blit(d, (px+m+55, hy))
            hy += 22

    def draw_menu(self):
        self.screen.fill(UI_BG)
        cx = SCREEN_WIDTH // 2

        # Title
        title_rect = pygame.Rect(cx-170, 55, 340, 95)
        draw_rounded(self.screen, (18, 18, 80), title_rect, 16, 2, (70, 70, 200))
        # Subtle gradient shimmer
        shimmer = pygame.Surface((340, 95), pygame.SRCALPHA)
        shimmer.fill((255,255,255, 12))
        self.screen.blit(shimmer, title_rect.topleft)
        t = self.font_xl.render("TETRIS", True, WHITE)
        self.screen.blit(t, t.get_rect(center=(cx, 103)))

        # High scores panel
        hs = self.score_manager.high_scores
        panel_h = 60 + len(hs)*30 + 10
        panel = pygame.Rect(cx-140, 170, 280, panel_h)
        draw_rounded(self.screen, PANEL_BG, panel, 12, 1, PANEL_BORDER)
        hs_title = self.font_sm.render("HIGH SCORES", True, TEXT_DIM)
        self.screen.blit(hs_title, hs_title.get_rect(center=(cx, panel.y+18)))
        for i, (_, sc) in enumerate(hs):
            color = GOLD if i == 0 else WHITE
            sc_txt = self.font_md.render(str(sc), True, color)
            self.screen.blit(sc_txt, sc_txt.get_rect(center=(cx, panel.y+45+i*30)))

        btn_y = panel.bottom + 18
        self.btn_play.rect.y   = btn_y
        self.btn_battle.rect.y = btn_y + 60
        self.btn_settings_menu.rect.y = btn_y + 120
        for btn in (self.btn_play, self.btn_battle, self.btn_settings_menu):
            btn.draw(self.screen)

    def draw_pause(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        cx = SCREEN_WIDTH // 2
        panel = pygame.Rect(cx-120, SCREEN_HEIGHT//2-130, 240, 280)
        draw_rounded(self.screen, PANEL_BG, panel, 14, 1, PANEL_BORDER)
        t = self.font_lg.render("PAUSED", True, WHITE)
        self.screen.blit(t, t.get_rect(center=(cx, SCREEN_HEIGHT//2-95)))
        for btn in (self.btn_resume, self.btn_quit, self.btn_settings_pause):
            btn.draw(self.screen)

    def draw_gameover(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))
        cx = SCREEN_WIDTH // 2
        panel = pygame.Rect(cx-140, SCREEN_HEIGHT//2-130, 280, 280)
        draw_rounded(self.screen, PANEL_BG, panel, 14, 1, PANEL_BORDER)
        go = self.font_lg.render("GAME OVER", True, RED)
        sc = self.font_md.render(f"Score: {self.score_manager.score}", True, WHITE)
        lv = self.font_sm.render(f"Level: {self.score_manager.level}", True, TEXT_DIM)
        self.screen.blit(go, go.get_rect(center=(cx, SCREEN_HEIGHT//2-90)))
        self.screen.blit(sc, sc.get_rect(center=(cx, SCREEN_HEIGHT//2-40)))
        self.screen.blit(lv, lv.get_rect(center=(cx, SCREEN_HEIGHT//2-10)))
        self.btn_restart.draw(self.screen)
        self.btn_menu.draw(self.screen)

    # ── Event handling ────────────────────────────────────────────────────────

    def handle_event(self, event):
        if self.state == self.STATE_SETTINGS:
            self._settings_overlay.handle_event(event)
            return

        if self.state == self.STATE_MENU:
            if self.btn_play.is_clicked(event):
                self.sound.play("drop")
                self._start_new_game()
            elif self.btn_battle.is_clicked(event):
                self.sound.play("drop")
                self.app.switch_scene("battle")
            elif self.btn_settings_menu.is_clicked(event):
                self._prev_state = self.STATE_MENU
                self.state = self.STATE_SETTINGS
            return

        if self.state == self.STATE_GAMEOVER:
            if self.btn_restart.is_clicked(event):
                self.sound.play("drop")
                self._start_new_game()
            elif self.btn_menu.is_clicked(event):
                self.sound.play("drop")
                self.state = self.STATE_MENU
            return

        if self.state == self.STATE_PAUSED:
            if self.btn_resume.is_clicked(event):
                self.sound.play("drop")
                self.state = self.STATE_PLAYING
            elif self.btn_quit.is_clicked(event):
                self.sound.play("drop")
                self.state = self.STATE_MENU
            elif self.btn_settings_pause.is_clicked(event):
                self._prev_state = self.STATE_PAUSED
                self.state = self.STATE_SETTINGS
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                self.state = self.STATE_PLAYING
            return

        if self.state == self.STATE_PLAYING:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = self.STATE_MENU
                    return
                if event.key == pygame.K_p:
                    self.state = self.STATE_PAUSED
                    return
                if event.key == pygame.K_TAB:
                    self._prev_state = self.STATE_PLAYING
                    self.state = self.STATE_SETTINGS
                    return
                if event.key == pygame.K_LEFT and self.board.is_valid_move(self.current_piece, dx=-1):
                    self.current_piece.x -= 1
                elif event.key == pygame.K_RIGHT and self.board.is_valid_move(self.current_piece, dx=1):
                    self.current_piece.x += 1
                elif event.key == pygame.K_DOWN and self.board.is_valid_move(self.current_piece, dy=1):
                    self.current_piece.y += 1
                elif event.key == pygame.K_UP:
                    old_shape = [r[:] for r in self.current_piece.shape]
                    old_x = self.current_piece.x
                    self.current_piece.rotate()
                    if not self.board.is_valid_position(self.current_piece):
                        kicked = False
                        for nudge in [1, -1, 2, -2]:
                            self.current_piece.x += nudge
                            if self.board.is_valid_position(self.current_piece):
                                kicked = True
                                break
                            self.current_piece.x = old_x
                        if not kicked:
                            self.current_piece.shape = old_shape
                            self.current_piece.x = old_x
                    else:
                        self.sound.play("rotate")
                elif event.key == pygame.K_SPACE:
                    self._spawn_trail()
                    while self.board.is_valid_move(self.current_piece, dy=1):
                        self.current_piece.y += 1
                    self._lock_piece()

    def _lock_piece(self):
        self.board.place_tetromino(self.current_piece)
        lines = self.board.clear_lines()
        prev_level = self.score_manager.level
        self.score_manager.add_score(lines)
        if lines > 0:
            self.sound.play("clear")
        else:
            self.sound.play("drop")
        if self.score_manager.level > prev_level:
            self.sound.play("levelup")
            self.fall_speed = fall_speed_for_level(self.score_manager.level)

        self.current_piece = self.next_piece
        self.next_piece    = self.bag_generator.get_next()
        self.fall_time     = 0.0

        if self.board.is_game_over():
            self.state = self.STATE_GAMEOVER
            self.sound.play("gameover")
            self.score_manager.save_high_score()

    def _start_new_game(self):
        self.score_manager = ScoreManager()
        self._init_game_objects()
        self.state = self.STATE_PLAYING

    # ── Update / Draw ─────────────────────────────────────────────────────────

    def update(self):
        self._update_trail()
        if self.state != self.STATE_PLAYING:
            return
        self.fall_time += self.clock.get_time() / 1000.0
        if self.fall_time >= self.fall_speed:
            self.fall_time = 0.0
            if self.board.is_valid_move(self.current_piece, dy=1):
                self.current_piece.y += 1
            else:
                self._lock_piece()

    def draw(self):
        if self.state == self.STATE_MENU:
            self.draw_menu()
        elif self.state == self.STATE_SETTINGS:
            # Draw whatever was behind settings first
            if self._prev_state == self.STATE_MENU:
                self.draw_menu()
            else:
                self.screen.fill(UI_BG)
                self.draw_board()
                self.draw_ui()
            self._settings_overlay.draw()
        else:
            self.screen.fill(UI_BG)
            self.draw_board()
            self.draw_ui()
            if self.state == self.STATE_PAUSED:
                self.draw_pause()
            elif self.state == self.STATE_GAMEOVER:
                self.draw_gameover()
