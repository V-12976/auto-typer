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
        self.mode = mode
        self.fixed_speed = fixed_speed
        self.min_speed = min_speed
        self.max_speed = max_speed

    def get_interval(self) -> float:
        """获取下次输入的间隔时间（秒）"""
        if self.mode == 'fixed':
            return 1.0 / self.fixed_speed
        else:
            speed = random.uniform(self.min_speed, self.max_speed)
            return 1.0 / speed