import pygame
import sys
from constants import *
from classes.classic_scene import ClassicScene
from classes.battle_scene import BattleScene

class PyTetrisApp:
    def __init__(self):
        pygame.init()
        # Start with classic dimensions
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("TETRIS")
        self.clock = pygame.time.Clock()
        self.scenes = {
            "classic": ClassicScene,
            "battle": BattleScene
        }
        self.current_scene = None
        self.switch_scene("classic")

    def switch_scene(self, scene_name: str):
        if scene_name == "battle":
            self.screen = pygame.display.set_mode((BATTLE_WIDTH, SCREEN_HEIGHT))
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            
        self.current_scene = self.scenes[scene_name](self.screen, self.clock, self)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.current_scene.handle_event(event)

            self.current_scene.update()
            self.current_scene.draw()
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    app = PyTetrisApp()
    app.run()