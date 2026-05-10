import random
from classes.tetromino import Tetromino

class BagGenerator:
    """
    7-bag Random Generator for Tetris.
    Ensures all 7 pieces appear in a random permutation before any repeats.
    """
    def __init__(self):
        self.bag = []
        self._refill()

    def _refill(self):
        self.bag = ['I', 'O', 'T', 'S', 'Z', 'J', 'L']
        random.shuffle(self.bag)

    def get_next(self) -> Tetromino:
        if not self.bag:
            self._refill()
        t_type = self.bag.pop(0)
        t = Tetromino()
        t.type = t_type
        from constants import COLORS
        t.color = COLORS[t_type]
        # Re-initialize shape based on type
        # Tetromino() initializes randomly, so we need to set it properly
        t.shape = t.SHAPES[t_type]
        return t
