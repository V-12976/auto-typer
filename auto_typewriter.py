# auto_typewriter.py
import ctypes
import random
import re
import struct
import threading
import time
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk, messagebox
from typing import Callable

import pyautogui
import pyperclip

# Windows API
user32 = ctypes.windll.user32
imm32 = ctypes.windll.imm32

# IME 常量
IME_CMODE_NATIVE = 0x0001


def get_ime_mode() -> int:
    """获取当前输入法模式"""
    try:
        hwnd = user32.GetForegroundWindow()
        himc = imm32.ImmGetContext(hwnd)
        if himc:
            mode = wintypes.DWORD()
            imm32.ImmGetConversionStatus(himc, ctypes.byref(mode), None)
            imm32.ImmReleaseContext(hwnd, himc)
            return mode.value
    except Exception:
        pass
    return 0


def is_ime_english() -> bool:
    """检查输入法是否为英文模式"""
    return (get_ime_mode() & IME_CMODE_NATIVE) == 0


def force_ime_english() -> bool:
    """强制输入法切换为英文模式"""
    try:
        hwnd = user32.GetForegroundWindow()
        himc = imm32.ImmGetContext(hwnd)
        if himc:
            # 设置为英文模式
            imm32.ImmSetConversionStatus(himc, 0, 0)
            imm32.ImmReleaseContext(hwnd, himc)
            return True
    except Exception:
        pass
    return False


class MouseClickDetector:
    """鼠标点击检测器，检测目标窗口外的点击"""

    def __init__(self) -> None:
        self._callback: Callable[[], None] | None = None
        self._enabled = False
        self._paused = False  # 暂停检测（避免死循环）
        self._hook = None
        self._target_hwnd: int = 0

    def _low_level_mouse_hook(self, nCode: int, wParam: int, lParam) -> int:
        """低级鼠标钩子回调"""
        if self._enabled and not self._paused and nCode >= 0:
            # wParam: WM_LBUTTONDOWN = 0x0201, WM_RBUTTONDOWN = 0x0204
            if wParam in (0x0201, 0x0204):  # 鼠标按下
                # 获取点击坐标
                x = lParam.contents.value & 0xFFFF
                y = (lParam.contents.value >> 16) & 0xFFFF

                # 获取点击位置的窗口
                clicked_hwnd = user32.WindowFromPoint(
                    ctypes.wintypes.POINT(x, y)
                )

                # 如果点击的不是目标窗口，触发回调
                if clicked_hwnd != self._target_hwnd:
                    if self._callback:
                        threading.Thread(target=self._callback, daemon=True).start()

        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def start(self, target_hwnd: int, callback: Callable[[], None]) -> None:
        """开始监听，target_hwnd是目标窗口句柄"""
        self._target_hwnd = target_hwnd
        self._callback = callback
        self._enabled = True
        self._paused = False

        # 定义钩子过程
        self._hook_proc = ctypes.CFUNCTYPE(
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_ulong)
        )(self._low_level_mouse_hook)

        # WH_MOUSE_LL = 14
        self._hook = user32.SetWindowsHookExA(14, self._hook_proc, None, 0)

    def pause_detection(self) -> None:
        """暂停检测（暂停打字时调用，避免死循环）"""
        self._paused = True

    def resume_detection(self) -> None:
        """恢复检测"""
        self._paused = False

    def stop(self) -> None:
        """停止监听"""
        self._enabled = False
        self._paused = False
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None


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
        self._mouse_detector = MouseClickDetector()
        self._target_hwnd: int = 0
        self._saved_clipboard: str = ""

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
        target_hwnd: int,
        on_progress: Callable[[int, int], None] | None = None,
        on_complete: Callable[[], None] | None = None,
        on_mouse_click: Callable[[], None] | None = None
    ) -> None:
        """开始打字（启动后台线程）"""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("Typing already in progress")
            self._pause_event.set()  # Not paused by default
            self._stop_event.clear()
            self._position = 0
            self._target_hwnd = target_hwnd

        # 保存剪贴板内容
        try:
            self._saved_clipboard = pyperclip.paste()
        except Exception:
            self._saved_clipboard = ""

        # 强制输入法为英文
        force_ime_english()

        # 设置鼠标点击回调
        if on_mouse_click:
            self._mouse_detector.start(target_hwnd, on_mouse_click)

        def typing_loop() -> None:
            last_ime_check = time.time()

            for i, char in enumerate(text):
                if self._stop_event.is_set():
                    break
                # Wait while paused, with periodic stop check
                while not self._pause_event.wait(timeout=0.1):
                    if self._stop_event.is_set():
                        break

                if self._stop_event.is_set():
                    break

                # 定期检查并锁定输入法为英文（每0.3秒）
                if time.time() - last_ime_check > 0.3:
                    last_ime_check = time.time()
                    if not is_ime_english():
                        force_ime_english()

                self._type_char(char)
                self._position = i + 1
                if on_progress:
                    on_progress(self._position, len(text))
                time.sleep(speed_controller.get_interval())

            # 清理鼠标钩子
            self._mouse_detector.stop()

            # 恢复剪贴板内容
            try:
                pyperclip.copy(self._saved_clipboard)
            except Exception:
                pass

            if not self._stop_event.is_set() and on_complete:
                on_complete()

        with self._lock:
            self._thread = threading.Thread(target=typing_loop, daemon=True)
            self._thread.start()

    def pause(self) -> None:
        """暂停打字"""
        self._pause_event.clear()
        self._mouse_detector.pause_detection()  # 暂停鼠标检测

    def resume(self) -> None:
        """继续打字"""
        self._pause_event.set()
        # 延迟恢复鼠标检测，给用户时间点击目标窗口
        threading.Timer(0.5, self._mouse_detector.resume_detection).start()
        # 强制输入法为英文
        force_ime_english()

    def stop(self) -> None:
        """停止打字"""
        self._mouse_detector.stop()
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
        self.status_var.set("3秒后开始... 请切换到目标窗口并点击输入框")
        self._countdown(3, lambda: self._start_typing(text, speed_controller))

    def _countdown(self, seconds: int, callback: Callable[[], None]) -> None:
        """倒计时"""
        if seconds > 0:
            self.status_var.set(f"{seconds}秒后开始... 请切换到目标窗口并点击输入框")
            self.root.after(1000, lambda: self._countdown(seconds - 1, callback))
        else:
            callback()

    def _start_typing(self, text: str, speed_controller: SpeedController) -> None:
        """实际开始打字"""
        # 获取当前活动窗口作为目标窗口
        target_hwnd = user32.GetForegroundWindow()

        # 检测目标窗口的输入法状态
        # 获取目标窗口的输入法上下文
        himc = imm32.ImmGetContext(target_hwnd)
        if himc:
            mode = wintypes.DWORD()
            imm32.ImmGetConversionStatus(himc, ctypes.byref(mode), None)
            imm32.ImmReleaseContext(target_hwnd, himc)
            is_english = (mode.value & IME_CMODE_NATIVE) == 0
        else:
            is_english = True  # 无法获取时默认允许

        if not is_english:
            messagebox.showwarning("提示", "目标窗口的输入法不是英文模式，请切换到英文输入法后重新开始")
            self.status_var.set("就绪")
            return

        # 强制锁定输入法为英文
        force_ime_english()

        self.status_var.set("状态: 打字中...")
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        self.clear_btn.config(state=tk.DISABLED)

        self.engine.start_typing(
            text,
            speed_controller,
            target_hwnd,
            on_progress=self._on_progress,
            on_complete=self._on_complete,
            on_mouse_click=self._on_mouse_click
        )

    def _on_progress(self, position: int, total: int) -> None:
        """进度更新回调"""
        self.root.after(0, lambda: self.status_var.set(f"状态: 打字中 ({position}/{total})"))

    def _on_complete(self) -> None:
        """完成回调"""
        self.root.after(0, self._reset_state)

    def _on_mouse_click(self) -> None:
        """鼠标点击回调 - 检测到点击就暂停"""
        def handle():
            self.status_var.set("已暂停 - 检测到鼠标点击")
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