"""
classes/settings.py — Global mutable game settings singleton.

All scenes read from and write to this single object so preferences
persist across scene switches within the same session.
"""


class Settings:
    """Singleton-style settings container. Import and use the module-level `settings` instance."""

    def __init__(self):
        self.sound_enabled: bool = True      # master SFX toggle
        self.music_enabled: bool = True      # background music toggle
        self.effects_enabled: bool = True    # visual effects (drop trail, shake, glow)
        self.ghost_enabled: bool = True      # ghost piece preview
        self.shake_enabled: bool = True      # screen-shake on hard drop
        self.glow_enabled: bool = True       # block glow/shadow effect

        # Battle bot difficulty: "medium" | "hard"
        self.bot_difficulty: str = "medium"


# Module-level singleton — import this everywhere
settings = Settings()
