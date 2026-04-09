# auto_typewriter.py
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import pyautogui
import pyperclip


class SpeedController:
    """速度控制器，支持固定和随机两种模式"""

    def __init__(
        self,
        mode: str = 'fixed',
        fixed_speed: float = 10,
        min_speed: float = 5,
        max_speed: float = 15
    ) -> None:
        if fixed_speed <= 0 or min_speed <= 0 or max_speed <= 0:
            raise ValueError("Speed must be positive")
        if min_speed > max_speed:
            raise ValueError("min_speed must not exceed max_speed")
        self.mode = mode
        self.fixed_speed = fixed_speed
        self.min_speed = min_speed
        self.max_speed = max_speed

    def get_interval(self) -> float:
        """获取下次输入的间隔时间（秒）"""
        if self.mode == 'fixed':
            return 1.0 / self.fixed_speed
        elif self.mode == 'random':
            speed = random.uniform(self.min_speed, self.max_speed)
            return 1.0 / speed
        else:
            raise ValueError(f"Invalid mode: {self.mode}")