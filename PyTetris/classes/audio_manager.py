import pygame
import time
from constants import *
from classes.settings import settings

class AudioManager:
    """
    Drop-in replacement for SoundManager with channel pool and throttle map.
    """
    def __init__(self):
        pygame.mixer.init(channels=AUDIO_CHANNELS)
        
        self.sounds = {}
        self._load_sound("clear", CLEAR_SOUND)
        self._load_sound("drop", DROP_SOUND)
        self._load_sound("rotate", ROTATE_SOUND)
        self._load_sound("levelup", LEVELUP_SOUND)
        self._load_sound("gameover", GAMEOVER_SOUND)
        
        self.last_played = {
            "clear": 0.0,
            "drop": 0.0,
            "rotate": 0.0,
            "levelup": 0.0,
            "gameover": 0.0
        }

    def _load_sound(self, key, path):
        try:
            self.sounds[key] = pygame.mixer.Sound(path)
        except:
            self.sounds[key] = None

    def play(self, key):
        if not settings.sound_enabled:
            return
        if not getattr(self, 'sounds', None) or key not in self.sounds:
            return

        sound = self.sounds[key]
        if not sound:
            return

        now = time.time() * 1000
        throttle = AUDIO_THROTTLE_MS.get(key, 0)
        if now - self.last_played[key] >= throttle:
            sound.play()
            self.last_played[key] = now

    def play_bgm(self):
        if not settings.music_enabled:
            return
        try:
            pygame.mixer.music.load(BG_MUSIC)
            pygame.mixer.music.play(-1)
        except:
            pass

    def stop_bgm(self):
        pygame.mixer.music.stop()
