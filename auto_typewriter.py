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


class GUIApp:
    """GUI应用程序，提供用户界面"""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Auto Typewriter v1.0")
        self.root.geometry("500x400")
        self._center_window()

        self._create_widgets()

    def _center_window(self) -> None:
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _create_widgets(self) -> None:
        """创建所有界面组件"""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Text input area with scrollbar
        text_frame = ttk.LabelFrame(main_frame, text="输入文本", padding="5")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.text_input = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_input.yview)
        self.text_input.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Speed panel
        speed_frame = ttk.LabelFrame(main_frame, text="速度设置", padding="5")
        speed_frame.pack(fill=tk.X, pady=(0, 10))

        self.speed_mode = tk.StringVar(value="fixed")
        ttk.Radiobutton(
            speed_frame,
            text="固定速度",
            variable=self.speed_mode,
            value="fixed"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            speed_frame,
            text="随机速度",
            variable=self.speed_mode,
            value="random"
        ).pack(side=tk.LEFT, padx=5)

        # Fixed speed input
        ttk.Label(speed_frame, text="固定速度(字符/秒):").pack(side=tk.LEFT, padx=(20, 5))
        self.fixed_speed_entry = ttk.Entry(speed_frame, width=8)
        self.fixed_speed_entry.insert(0, "10")
        self.fixed_speed_entry.pack(side=tk.LEFT)

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = ttk.Button(button_frame, text="开始", command=self._on_start)
        self.start_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.pause_btn = ttk.Button(button_frame, text="暂停", command=self._on_pause)
        self.pause_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.stop_btn = ttk.Button(button_frame, text="停止", command=self._on_stop)
        self.stop_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.clear_btn = ttk.Button(button_frame, text="清空", command=self._on_clear)
        self.clear_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Status bar
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _on_start(self) -> None:
        """开始按钮处理（占位方法，Task 5实现）"""
        pass

    def _on_pause(self) -> None:
        """暂停按钮处理（占位方法，Task 5实现）"""
        pass

    def _on_stop(self) -> None:
        """停止按钮处理（占位方法，Task 5实现）"""
        pass

    def _on_clear(self) -> None:
        """清空按钮处理（占位方法，Task 5实现）"""
        pass

    def run(self) -> None:
        """运行应用程序"""
        self.root.mainloop()