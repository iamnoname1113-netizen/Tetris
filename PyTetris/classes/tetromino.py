"""Class Tetromino - Quản lý khối tetromino và thuật toán xoay ma trận."""

from typing import List, Tuple
import random
from constants import COLORS
from constants import BOARD_WIDTH
class Tetromino:
    """Lớp đại diện cho một khối tetromino sử dụng ma trận vuông."""

    # Chỉ lưu DUY NHẤT 1 trạng thái ban đầu dưới dạng ma trận vuông (NxN).
    # Việc dùng ma trận vuông đảm bảo tâm xoay của khối luôn cố định.
    SHAPES = {
        'I': [
            [0, 0, 0, 0],
            [1, 1, 1, 1],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ],
        'O': [
            [1, 1],
            [1, 1]
        ],
        'T': [
            [0, 1, 0],
            [1, 1, 1],
            [0, 0, 0]
        ],
        'S': [
            [0, 1, 1],
            [1, 1, 0],
            [0, 0, 0]
        ],
        'Z': [
            [1, 1, 0],
            [0, 1, 1],
            [0, 0, 0]
        ],
        'J': [
            [1, 0, 0],
            [1, 1, 1],
            [0, 0, 0]
        ],
        'L': [
            [0, 0, 1],
            [1, 1, 1],
            [0, 0, 0]
        ]
    }

    def __init__(self, shape_type: str = None) -> None:
        """Khởi tạo một tetromino ngẫu nhiên hoặc theo loại chỉ định."""
        if shape_type is None:
            shape_type = random.choice(list(self.SHAPES.keys()))
        self.type = shape_type
        self.color = COLORS[shape_type]        # Màu thật từ constants
        # self.color = (255, 255, 255)         # Mock color để test
        
        # Gán ma trận ban đầu thay vì phải truyền index [self.rotation]
        self.shape = self.SHAPES[shape_type]
        
        # Tọa độ gốc: Tinh chỉnh lại x để các ma trận vuông rơi ngay giữa bàn chơi
        self.x = BOARD_WIDTH//2
        self.y = 0

    def rotate(self) -> None:
        
        # N là kích thước của ma trận vuông
        N = len(self.shape)
        
        # Bước 1: Tạo ra một ma trận rỗng mới (toàn số 0) có cùng kích thước N x N
        rotated_shape = [[0 for _ in range(N)] for _ in range(N)]
        
        # Bước 2: Dùng 2 vòng lặp lồng nhau duyệt qua từng ô của ma trận CŨ
        for r in range(N):          
            for c in range(N):      
                
                # Bước 3: Đẩy giá trị sang tọa độ MỚI theo công thức toán học
                # Hàng mới = Cột cũ (c)
                # Cột mới = N - 1 - Hàng cũ (r)
                rotated_shape[c][N - 1 - r] = self.shape[r][c]
                
        # Bước 4: Cập nhật lại bản vẽ của khối gạch bằng ma trận mới đã xoay
        self.shape = rotated_shape

    def get_positions(self) -> List[Tuple[int, int]]:
        """
        Trả về danh sách tọa độ (x, y) thực tế của các ô chứa giá trị 1 trên lưới game.
        Dùng để xử lý thuật toán check va chạm (Collision Detection).
        """
        positions = []
        #enumerate: vị trí + giá trị
        for row_idx, row in enumerate(self.shape):
            for col_idx, cell in enumerate(row):
                if cell:  # Chỉ lấy tọa độ của những ô mang giá trị 1
                    positions.append((self.x + col_idx, self.y + row_idx))
        return positions