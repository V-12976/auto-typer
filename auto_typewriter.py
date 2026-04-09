# auto_typewriter.py
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

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


class TypewriterEngine:
    """打字引擎，负责模拟键盘输入"""

    def __init__(self) -> None:
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default
        self._stop_event = threading.Event()
        self._position: int = 0
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def _type_char(self, char: str) -> None:
        """输入单个字符，处理中英文"""
        if char.isascii():
            pyautogui.write(char)
        else:
            # 中文和Unicode字符通过剪贴板输入
            pyperclip.copy(char)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.05)  # 等待粘贴完成

    def start_typing(
        self,
        text: str,
        speed_controller: SpeedController,
        on_progress: Callable[[int, int], None] | None = None,
        on_complete: Callable[[], None] | None = None
    ) -> None:
        """开始打字（启动后台线程）"""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("Typing already in progress")
            self._pause_event.set()  # Not paused by default
            self._stop_event.clear()
            self._position = 0

        def typing_loop() -> None:
            for i, char in enumerate(text):
                if self._stop_event.is_set():
                    break
                # Wait while paused, with periodic stop check
                while not self._pause_event.wait(timeout=0.1):
                    if self._stop_event.is_set():
                        break

                if self._stop_event.is_set():
                    break

                self._type_char(char)
                self._position = i + 1
                if on_progress:
                    on_progress(self._position, len(text))
                time.sleep(speed_controller.get_interval())

            if not self._stop_event.is_set() and on_complete:
                on_complete()

        with self._lock:
            self._thread = threading.Thread(target=typing_loop, daemon=True)
            self._thread.start()

    def pause(self) -> None:
        """暂停打字"""
        self._pause_event.clear()

    def resume(self) -> None:
        """继续打字"""
        self._pause_event.set()

    def stop(self) -> None:
        """停止打字"""
        self._stop_event.set()
        self._pause_event.set()  # Unblock any paused wait

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._thread is not None and self._thread.is_alive()

    def is_paused(self) -> bool:
        """检查是否暂停"""
        return not self._pause_event.is_set()