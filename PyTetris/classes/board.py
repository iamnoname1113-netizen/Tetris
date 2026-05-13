"""Class Board - Quản lý bàn chơi, va chạm, xóa hàng."""

from typing import List, Optional
from classes.tetromino import Tetromino
from constants import BOARD_WIDTH, BOARD_HEIGHT


class Board:
    """Lớp quản lý ma trận bàn chơi Tetris."""

    def __init__(self) -> None:
        """Khởi tạo bàn chơi trống."""
        self.width = BOARD_WIDTH
        self.height = BOARD_HEIGHT
        self.grid: List[List[int]] = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.pending_garbage: int = 0

    def is_valid_move(self, tetromino: Tetromino, dx: int = 0, dy: int = 0) -> bool:
        """Kiểm tra nước đi có hợp lệ không (va chạm biên + va chạm khối cũ)."""
        for x, y in tetromino.get_positions():
            new_x = x + dx
            new_y = y + dy
            # Va chạm biên
            if new_x < 0 or new_x >= self.width or new_y >= self.height:
                return False
            # Bỏ qua ô trên bàn (new_y < 0 là vùng spawn)
            if new_y < 0:
                continue
            # Va chạm khối đã đặt (kể cả ô rác 'G')
            if self.grid[new_y][new_x] != 0:
                return False
        return True


    def is_valid_position(self, tetromino: Tetromino) -> bool:
        """Kiểm tra vị trí hiện tại (không dịch chuyển) có hợp lệ không."""
        return self.is_valid_move(tetromino, dx=0, dy=0)

    def place_tetromino(self, tetromino: Tetromino) -> None:
        """Đặt khối vào bàn và cập nhật grid."""
        for x, y in tetromino.get_positions():
            if y >= 0:
                self.grid[y][x] = tetromino.type  # lưu loại khối để vẽ màu

    def clear_lines(self) -> int:
        """Xóa các hàng đầy và trả về số hàng đã xóa."""
        lines_cleared = 0
        new_grid = [row for row in self.grid if any(cell == 0 for cell in row)]
        lines_cleared = self.height - len(new_grid)
        # Thêm hàng trống ở trên
        for _ in range(lines_cleared):
            new_grid.insert(0, [0] * self.width)
        self.grid = new_grid
        return lines_cleared

    def is_game_over(self) -> bool:
        """Kiểm tra game over (có khối chạm trần)."""
        return any(cell != 0 for cell in self.grid[0])

    def add_garbage(self, lines: int) -> None:
        """Đẩy rác từ dưới lên, chừa 1 lỗ ngẫu nhiên cho mỗi dòng."""
        import random
        if lines <= 0:
            return
        
        # Đẩy các dòng hiện tại lên
        for i in range(lines):
            self.grid.pop(0)
            
        # Thêm các dòng rác ở dưới
        for _ in range(lines):
            row = ['G'] * self.width
            hole = random.randint(0, self.width - 1)
            row[hole] = 0
            self.grid.append(row)

    @property
    def column_heights(self):
        from utils.heuristics import column_heights
        return column_heights(self.grid)

    @property
    def count_holes(self):
        from utils.heuristics import count_holes
        return count_holes(self.grid)

    @property
    def aggregate_height(self):
        from utils.heuristics import aggregate_height
        return aggregate_height(self.grid)

    @property
    def bumpiness(self):
        from utils.heuristics import bumpiness
        return bumpiness(self.grid)