"""Quản lý âm thanh - SFX và nhạc nền."""

import pygame
import os
from constants import (CLEAR_SOUND, DROP_SOUND, ROTATE_SOUND,
					   LEVELUP_SOUND, GAMEOVER_SOUND, BG_MUSIC)

class SoundManager:
	def __init__(self) -> None:
		pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
		self.sounds = {}
		self.enabled = True

		self._load("clear",    CLEAR_SOUND)
		self._load("drop",     DROP_SOUND)
		self._load("rotate",   ROTATE_SOUND)
		self._load("levelup",  LEVELUP_SOUND)
		self._load("gameover", GAMEOVER_SOUND)

		self._init_bgm()

	def _load(self, name: str, path: str) -> None:
		if os.path.exists(path):
			try:
				self.sounds[name] = pygame.mixer.Sound(path)
			except Exception:
				pass

	def _init_bgm(self) -> None:
		if os.path.exists(BG_MUSIC):
			try:
				pygame.mixer.music.load(BG_MUSIC)
			except Exception:
				pass

	def play_bgm(self) -> None:
		try:
			pygame.mixer.music.play(-1)
		except Exception:
			pass

	def stop_bgm(self) -> None:
		try:
			pygame.mixer.music.stop()
		except Exception:
			pass

	def play(self, name: str) -> None:
		if self.enabled and name in self.sounds:
			self.sounds[name].play()