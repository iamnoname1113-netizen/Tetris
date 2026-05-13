"""Quản lý điểm số và high score."""

import json
import os
from typing import List, Tuple
from constants import SCORE_TABLE


class ScoreManager:
    """Lớp quản lý điểm số và lưu high score."""

    def __init__(self) -> None:
        self.score = 0
        self.level = 1
        self.lines = 0
        self.high_scores: List[Tuple[str, int]] = []
        self.load_high_scores()

    def add_score(self, lines_cleared: int) -> None:
        """Tính điểm theo số hàng xóa."""
        self.score += SCORE_TABLE[lines_cleared] * self.level
        self.lines += lines_cleared
        self.level = self.lines // 10 + 1

    def save_high_score(self, player_name: str = "Player") -> None:
        """Lưu high score vào file JSON."""
        self.high_scores.append((player_name, self.score))
        self.high_scores.sort(key=lambda x: x[1], reverse=True)
        self.high_scores = self.high_scores[:5]
        with open("high_scores.json", "w", encoding="utf-8") as f:
            json.dump(self.high_scores, f)

    def load_high_scores(self) -> None:
        """Đọc high score từ file."""
        if os.path.exists("high_scores.json"):
            with open("high_scores.json", "r", encoding="utf-8") as f:
                self.high_scores = json.load(f)