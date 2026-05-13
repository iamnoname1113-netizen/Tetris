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
        return Tetromino(self.bag.pop(0))
