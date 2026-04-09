# auto_typewriter.py
import ctypes
import random
import re
import threading
import time
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk, messagebox
from typing import Callable

import pyautogui
import pyperclip

# Windows IME 常量
IME_CMODE_ALPHANUMERIC = 0x0000  # 英文模式
IME_CMODE_NATIVE = 0x0001        # 中文模式

# Windows API 函数
imm32 = ctypes.windll.imm32
user32 = ctypes.windll.user32


def get_ime_mode() -> int:
    """获取当前输入法模式，返回IME_CMODE常量"""
    hwnd = user32.GetForegroundWindow()
    himc = imm32.ImmGetContext(hwnd)
    if himc:
        mode = wintypes.DWORD()
        imm32.ImmGetConversionStatus(himc, ctypes.byref(mode), None)
        imm32.ImmReleaseContext(hwnd, himc)
        return mode.value
    return IME_CMODE_ALPHANUMERIC


def is_ime_english() -> bool:
    """检查输入法是否为英文模式"""
    mode = get_ime_mode()
    return (mode & IME_CMODE_NATIVE) == 0


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
        self._target_window: int = 0
        self._check_interval: float = 0.3

    def _check_window_changed(self) -> bool:
        """检查活动窗口是否变化"""
        if self._target_window == 0:
            return False
        current_window = user32.GetForegroundWindow()
        return current_window != self._target_window

    def _check_ime_mode(self) -> bool:
        """检查输入法是否为英文，返回True表示正常"""
        return is_ime_english()

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
        on_complete: Callable[[], None] | None = None,
        on_window_change: Callable[[], None] | None = None,
        on_ime_change: Callable[[], None] | None = None
    ) -> None:
        """开始打字（启动后台线程）"""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("Typing already in progress")
            self._pause_event.set()  # Not paused by default
            self._stop_event.clear()
            self._position = 0
            self._target_window = user32.GetForegroundWindow()

        def typing_loop() -> None:
            last_check_time = time.time()

            for i, char in enumerate(text):
                if self._stop_event.is_set():
                    break
                # Wait while paused, with periodic stop check
                while not self._pause_event.wait(timeout=0.1):
                    if self._stop_event.is_set():
                        break

                if self._stop_event.is_set():
                    break

                # 定期检查窗口和输入法
                if time.time() - last_check_time > self._check_interval:
                    last_check_time = time.time()

                    # 检查窗口变化
                    if self._check_window_changed():
                        if on_window_change:
                            on_window_change()
                        break

                    # 检查输入法
                    if not self._check_ime_mode():
                        if on_ime_change:
                            on_ime_change()
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
        self.root.geometry("650x600")
        self.root.minsize(500, 450)
        self._center_window()

        # 初始化引擎
        self.engine = TypewriterEngine()

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
        # Status bar at bottom (pack first so it stays at bottom)
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Text input area with scrollbar
        text_frame = ttk.LabelFrame(main_frame, text="输入文本", padding="5")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.text_input = tk.Text(text_frame, wrap=tk.WORD, height=8)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_input.yview)
        self.text_input.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Word count label
        self.word_count_var = tk.StringVar(value="字符: 0 | 单词: 0 | 中文: 0")
        word_count_label = ttk.Label(main_frame, textvariable=self.word_count_var)
        word_count_label.pack(fill=tk.X, pady=(0, 5))

        # Bind text change event for real-time counting
        self.text_input.bind('<KeyRelease>', self._update_word_count)
        self.text_input.bind('<ButtonRelease>', self._update_word_count)

        # Speed panel
        speed_frame = ttk.LabelFrame(main_frame, text="速度设置", padding="5")
        speed_frame.pack(fill=tk.X, pady=(0, 10))

        self.speed_mode = tk.StringVar(value="fixed")
        ttk.Radiobutton(
            speed_frame,
            text="固定速度",
            variable=self.speed_mode,
            value="fixed"
        ).grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Radiobutton(
            speed_frame,
            text="随机速度",
            variable=self.speed_mode,
            value="random"
        ).grid(row=0, column=1, sticky=tk.W, padx=5)

        # Fixed speed input
        ttk.Label(speed_frame, text="速度(字/秒):").grid(row=1, column=0, sticky=tk.E, padx=(0, 5))
        self.fixed_speed_var = tk.StringVar(value='10')
        self.fixed_speed_entry = ttk.Entry(speed_frame, textvariable=self.fixed_speed_var, width=8)
        self.fixed_speed_entry.grid(row=1, column=1)

        # Random speed input (min/max)
        ttk.Label(speed_frame, text="最小:").grid(row=2, column=0, sticky=tk.E, padx=(0, 5))
        self.min_speed_var = tk.StringVar(value='5')
        ttk.Entry(speed_frame, textvariable=self.min_speed_var, width=8).grid(row=2, column=1)

        ttk.Label(speed_frame, text="最大:").grid(row=2, column=2, sticky=tk.E, padx=(5, 5))
        self.max_speed_var = tk.StringVar(value='15')
        ttk.Entry(speed_frame, textvariable=self.max_speed_var, width=8).grid(row=2, column=3)

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

    def _on_start(self) -> None:
        """开始按钮处理"""
        text = self.text_input.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请输入文本")
            return

        # 检查输入法
        if not is_ime_english():
            messagebox.showwarning("提示", "请先切换到英文输入法（Shift或Ctrl+Space）")
            return

        # 验证速度输入
        try:
            mode = self.speed_mode.get()
            if mode == 'fixed':
                speed = float(self.fixed_speed_var.get())
                if not 1 <= speed <= 50:
                    messagebox.showwarning("提示", "速度范围: 1-50字/秒")
                    return
            else:
                min_speed = float(self.min_speed_var.get())
                max_speed = float(self.max_speed_var.get())
                if not 1 <= min_speed <= 50 or not 1 <= max_speed <= 50:
                    messagebox.showwarning("提示", "速度范围: 1-50字/秒")
                    return
                if min_speed > max_speed:
                    messagebox.showwarning("提示", "最小速度不能大于最大速度")
                    return
        except ValueError:
            messagebox.showwarning("提示", "请输入有效的数字")
            return

        try:
            speed_controller = self._update_speed_controller()
        except ValueError as e:
            messagebox.showwarning("提示", str(e))
            return

        # 倒计时3秒
        self.status_var.set("3秒后开始... 请切换到目标窗口")
        self._countdown(3, lambda: self._start_typing(text, speed_controller))

    def _countdown(self, seconds: int, callback: Callable[[], None]) -> None:
        """倒计时"""
        if seconds > 0:
            self.status_var.set(f"{seconds}秒后开始... 请切换到目标窗口")
            self.root.after(1000, lambda: self._countdown(seconds - 1, callback))
        else:
            callback()

    def _start_typing(self, text: str, speed_controller: SpeedController) -> None:
        """实际开始打字"""
        self.status_var.set("状态: 打字中...")
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        self.clear_btn.config(state=tk.DISABLED)

        self.engine.start_typing(
            text,
            speed_controller,
            on_progress=self._on_progress,
            on_complete=self._on_complete,
            on_window_change=self._on_window_change,
            on_ime_change=self._on_ime_change
        )

    def _on_progress(self, position: int, total: int) -> None:
        """进度更新回调"""
        self.root.after(0, lambda: self.status_var.set(f"状态: 打字中 ({position}/{total})"))

    def _on_complete(self) -> None:
        """完成回调"""
        self.root.after(0, self._reset_state)

    def _on_window_change(self) -> None:
        """窗口切换回调"""
        def handle():
            self.status_var.set("已暂停 - 检测到窗口切换")
            self._auto_pause()
        self.root.after(0, handle)

    def _on_ime_change(self) -> None:
        """输入法切换回调"""
        def handle():
            self.status_var.set("已暂停 - 请切换到英文输入法")
            self._auto_pause()
        self.root.after(0, handle)

    def _auto_pause(self) -> None:
        """自动暂停"""
        self.engine.pause()
        self.pause_btn.config(text="继续")

    def _on_pause(self) -> None:
        """暂停按钮处理"""
        if self.engine.is_paused():
            self.engine.resume()
            self.pause_btn.config(text="暂停")
            self.status_var.set("状态: 打字中...")
        else:
            self.engine.pause()
            self.pause_btn.config(text="继续")
            self.status_var.set("状态: 已暂停")

    def _on_stop(self) -> None:
        """停止按钮处理"""
        self.engine.stop()
        self._reset_state()

    def _on_clear(self) -> None:
        """清空按钮处理"""
        self.text_input.delete('1.0', tk.END)

    def _update_word_count(self, event=None) -> None:
        """更新词数统计"""
        text = self.text_input.get('1.0', tk.END).strip()

        # 字符数（含标点和空格）
        char_count = len(text)

        # 单词数（英文单词）
        words = re.findall(r'[a-zA-Z]+', text)
        word_count = len(words)

        # 中文字数（仅汉字）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        chinese_count = len(chinese_chars)

        self.word_count_var.set(f"字符: {char_count} | 单词: {word_count} | 中文: {chinese_count}")

    def _reset_state(self) -> None:
        """重置界面状态"""
        self.status_var.set("状态: 完成")
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED, text="暂停")
        self.stop_btn.config(state=tk.DISABLED)
        self.clear_btn.config(state=tk.NORMAL)

    def _update_speed_controller(self) -> SpeedController:
        """根据当前设置创建速度控制器"""
        mode = self.speed_mode.get()
        try:
            fixed_speed = float(self.fixed_speed_var.get())
            min_speed = float(self.min_speed_var.get())
            max_speed = float(self.max_speed_var.get())
        except ValueError:
            raise ValueError("Speed values must be valid numbers")

        return SpeedController(
            mode=mode,
            fixed_speed=fixed_speed,
            min_speed=min_speed,
            max_speed=max_speed
        )

    def run(self) -> None:
        """运行应用程序"""
        self.root.mainloop()


if __name__ == '__main__':
    app = GUIApp()
    app.run()