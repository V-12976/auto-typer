# Auto Typewriter 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个自动打字脚本，通过GUI界面接收文本，模拟键盘输入逐字打出。

**Architecture:** 单文件Python脚本 `auto_typewriter.py`，包含SpeedController速度控制类、TypewriterEngine打字引擎类、GUIApp Tkinter界面类。打字循环在独立线程运行避免阻塞GUI。

**Tech Stack:** Python 3.x, tkinter (标准库), pyautogui, pyperclip

---

## File Structure

```
c:\Users\fbif9\PycharmProjects\TTS\
├── auto_typewriter.py      # 主脚本（创建）
└── tests/
    └── test_speed_controller.py  # SpeedController单元测试（创建）
```

---

### Task 1: 安装依赖

**Files:**
- None (环境配置)

- [ ] **Step 1: 安装pyautogui和pyperclip**

```bash
pip install pyautogui pyperclip
```

Expected: Successfully installed packages

- [ ] **Step 2: 验证安装成功**

```bash
python -c "import pyautogui; import pyperclip; print('Dependencies OK')"
```

Expected: Output "Dependencies OK"

---

### Task 2: 实现SpeedController类

**Files:**
- Create: `tests/test_speed_controller.py`
- Create: `auto_typewriter.py` (SpeedController部分)

- [ ] **Step 1: 创建测试文件并编写SpeedController测试**

```python
# tests/test_speed_controller.py
import pytest
from auto_typewriter import SpeedController


def test_fixed_speed_mode():
    """固定速度模式返回常量间隔"""
    controller = SpeedController(mode='fixed', fixed_speed=10)
    interval = controller.get_interval()
    assert interval == 0.1  # 1/10 = 0.1秒


def test_random_speed_mode_within_range():
    """随机速度模式返回在范围内的间隔"""
    controller = SpeedController(mode='random', min_speed=5, max_speed=15)
    for _ in range(100):  # 多次测试确保范围正确
        interval = controller.get_interval()
        assert 0.0667 <= interval <= 0.2  # 1/15≈0.067, 1/5=0.2


def test_fixed_speed_boundary():
    """固定速度边界值测试"""
    controller = SpeedController(mode='fixed', fixed_speed=1)
    assert controller.get_interval() == 1.0

    controller = SpeedController(mode='fixed', fixed_speed=50)
    assert controller.get_interval() == 0.02


def test_default_values():
    """默认参数测试"""
    controller = SpeedController()
    assert controller.mode == 'fixed'
    assert controller.fixed_speed == 10
    assert controller.min_speed == 5
    assert controller.max_speed == 15
```

- [ ] **Step 2: 运行测试验证失败（类未定义）**

```bash
pytest tests/test_speed_controller.py -v
```

Expected: FAIL - ImportError or ModuleNotFoundError

- [ ] **Step 3: 创建auto_typewriter.py并实现SpeedController类**

```python
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_speed_controller.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_speed_controller.py auto_typewriter.py
git commit -m "feat: add SpeedController with tests"
```

---

### Task 3: 实现TypewriterEngine类

**Files:**
- Modify: `auto_typewriter.py` (添加TypewriterEngine类)

- [ ] **Step 1: 添加TypewriterEngine类定义**

在 `auto_typewriter.py` 的 `SpeedController` 类后添加：

```python
class TypewriterEngine:
    """打字引擎，负责模拟键盘输入"""

    def __init__(self) -> None:
        self._paused: bool = False
        self._stopped: bool = False
        self._position: int = 0
        self._thread: threading.Thread | None = None

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
        on_progress: callable = None,
        on_complete: callable = None
    ) -> None:
        """开始打字（启动后台线程）"""
        self._paused = False
        self._stopped = False
        self._position = 0

        def typing_loop():
            for i, char in enumerate(text):
                if self._stopped:
                    break
                while self._paused:
                    time.sleep(0.1)
                    if self._stopped:
                        break

                self._type_char(char)
                self._position = i + 1
                if on_progress:
                    on_progress(self._position, len(text))
                time.sleep(speed_controller.get_interval())

            if not self._stopped and on_complete:
                on_complete()

        self._thread = threading.Thread(target=typing_loop, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        """暂停打字"""
        self._paused = True

    def resume(self) -> None:
        """继续打字"""
        self._paused = False

    def stop(self) -> None:
        """停止打字"""
        self._stopped = True
        self._paused = False

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._thread is not None and self._thread.is_alive()

    def is_paused(self) -> bool:
        """检查是否暂停"""
        return self._paused
```

- [ ] **Step 2: 验证语法正确**

```bash
python -c "from auto_typewriter import TypewriterEngine; e = TypewriterEngine(); print('Engine OK')"
```

Expected: Output "Engine OK"

- [ ] **Step 3: Commit**

```bash
git add auto_typewriter.py
git commit -m "feat: add TypewriterEngine class"
```

---

### Task 4: 实现GUI框架

**Files:**
- Modify: `auto_typewriter.py` (添加GUIApp类)

- [ ] **Step 1: 添加GUIApp类基础结构**

在 `auto_typewriter.py` 的 `TypewriterEngine` 类后添加：

```python
class GUIApp:
    """Tkinter GUI应用"""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Auto Typewriter v1.0")
        self.root.geometry("500x400")
        self.root.resizable(True, True)

        # 居中显示窗口
        self._center_window()

        # 初始化引擎和控制器
        self.engine = TypewriterEngine()
        self.speed_controller = SpeedController()

        # 构建界面
        self._build_widgets()

    def _center_window(self) -> None:
        """窗口居中"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_widgets(self) -> None:
        """构建所有界面组件"""
        # 文本输入区
        self._build_text_area()

        # 速度设置区
        self._build_speed_panel()

        # 控制按钮区
        self._build_buttons()

        # 状态栏
        self._build_status_bar()

    def _build_text_area(self) -> None:
        """构建文本输入框"""
        text_frame = ttk.LabelFrame(self.root, text="文本输入", padding=10)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.text_input = tk.Text(text_frame, height=10, wrap=tk.WORD)
        self.text_input.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_input.yview)
        self.text_input.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_speed_panel(self) -> None:
        """构建速度设置面板"""
        speed_frame = ttk.LabelFrame(self.root, text="速度设置", padding=10)
        speed_frame.pack(fill=tk.X, padx=10, pady=5)

        # 速度模式选择
        self.speed_mode = tk.StringVar(value='fixed')

        fixed_radio = ttk.Radiobutton(
            speed_frame, text="固定速度:", variable=self.speed_mode, value='fixed',
            command=self._on_speed_mode_change
        )
        fixed_radio.grid(row=0, column=0, sticky=tk.W)

        self.fixed_speed_var = tk.StringVar(value='10')
        fixed_entry = ttk.Entry(speed_frame, textvariable=self.fixed_speed_var, width=8)
        fixed_entry.grid(row=0, column=1)

        fixed_label = ttk.Label(speed_frame, text="字/秒")
        fixed_label.grid(row=0, column=2, sticky=tk.W)

        random_radio = ttk.Radiobutton(
            speed_frame, text="随机速度:", variable=self.speed_mode, value='random',
            command=self._on_speed_mode_change
        )
        random_radio.grid(row=1, column=0, sticky=tk.W)

        ttk.Label(speed_frame, text="最小").grid(row=1, column=1, sticky=tk.E)
        self.min_speed_var = tk.StringVar(value='5')
        min_entry = ttk.Entry(speed_frame, textvariable=self.min_speed_var, width=8)
        min_entry.grid(row=1, column=2)

        ttk.Label(speed_frame, text="最大").grid(row=1, column=3, sticky=tk.E)
        self.max_speed_var = tk.StringVar(value='15')
        max_entry = ttk.Entry(speed_frame, textvariable=self.max_speed_var, width=8)
        max_entry.grid(row=1, column=4)

    def _build_buttons(self) -> None:
        """构建控制按钮"""
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        self.start_btn = ttk.Button(button_frame, text="开始", command=self._on_start, width=10)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.pause_btn = ttk.Button(button_frame, text="暂停", command=self._on_pause, width=10, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(button_frame, text="停止", command=self._on_stop, width=10, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(button_frame, text="清空", command=self._on_clear, width=10)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

    def _build_status_bar(self) -> None:
        """构建状态栏"""
        status_frame = ttk.Frame(self.root, padding=5)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.status_var = tk.StringVar(value="状态: 就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT)

    def _on_speed_mode_change(self) -> None:
        """速度模式切换时更新控制器"""
        self._update_speed_controller()

    def _update_speed_controller(self) -> None:
        """根据GUI设置更新速度控制器"""
        mode = self.speed_mode.get()
        try:
            if mode == 'fixed':
                fixed_speed = float(self.fixed_speed_var.get())
                self.speed_controller = SpeedController(mode='fixed', fixed_speed=fixed_speed)
            else:
                min_speed = float(self.min_speed_var.get())
                max_speed = float(self.max_speed_var.get())
                self.speed_controller = SpeedController(mode='random', min_speed=min_speed, max_speed=max_speed)
        except ValueError:
            pass  # 忽略无效输入，保持原值

    def run(self) -> None:
        """启动应用"""
        self.root.mainloop()
```

- [ ] **Step 2: 验证GUI可以启动（仅测试框架）**

```bash
timeout 2 python -c "from auto_typewriter import GUIApp; app = GUIApp(); print('GUI OK')" || echo "Timeout expected"
```

Expected: Output "GUI OK" (timeout是预期行为，因为mainloop会阻塞)

- [ ] **Step 3: Commit**

```bash
git add auto_typewriter.py
git commit -m "feat: add GUI framework with widgets"
```

---

### Task 5: 实现按钮事件处理

**Files:**
- Modify: `auto_typewriter.py` (添加事件处理方法)

- [ ] **Step 1: 在GUIApp类中添加事件处理方法**

在 `GUIApp` 类的 `run` 方法之前添加以下方法：

```python
    def _on_start(self) -> None:
        """开始按钮事件"""
        text = self.text_input.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请输入文本")
            return

        self._update_speed_controller()

        # 倒计时3秒
        self.status_var.set("3秒后开始... 请切换到目标窗口")
        self._countdown(3, lambda: self._start_typing(text))

    def _countdown(self, seconds: int, callback: callable) -> None:
        """倒计时"""
        if seconds > 0:
            self.status_var.set(f"{seconds}秒后开始... 请切换到目标窗口")
            self.root.after(1000, lambda: self._countdown(seconds - 1, callback))
        else:
            callback()

    def _start_typing(self, text: str) -> None:
        """实际开始打字"""
        self.status_var.set("状态: 打字中...")
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        self.clear_btn.config(state=tk.DISABLED)

        self.engine.start_typing(
            text,
            self.speed_controller,
            on_progress=self._on_progress,
            on_complete=self._on_complete
        )

    def _on_progress(self, position: int, total: int) -> None:
        """进度更新回调"""
        self.root.after(0, lambda: self.status_var.set(f"状态: 打字中 ({position}/{total})"))

    def _on_complete(self) -> None:
        """完成回调"""
        self.root.after(0, self._reset_state)

    def _on_pause(self) -> None:
        """暂停按钮事件"""
        if self.engine.is_paused():
            self.engine.resume()
            self.pause_btn.config(text="暂停")
            self.status_var.set("状态: 打字中...")
        else:
            self.engine.pause()
            self.pause_btn.config(text="继续")
            self.status_var.set("状态: 已暂停")

    def _on_stop(self) -> None:
        """停止按钮事件"""
        self.engine.stop()
        self._reset_state()

    def _on_clear(self) -> None:
        """清空按钮事件"""
        self.text_input.delete('1.0', tk.END)

    def _reset_state(self) -> None:
        """重置界面状态"""
        self.status_var.set("状态: 完成")
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED, text="暂停")
        self.stop_btn.config(state=tk.DISABLED)
        self.clear_btn.config(state=tk.NORMAL)
```

- [ ] **Step 2: 验证语法正确**

```bash
python -c "from auto_typewriter import GUIApp; print('Event handlers OK')"
```

Expected: Output "Event handlers OK"

- [ ] **Step 3: Commit**

```bash
git add auto_typewriter.py
git commit -m "feat: add button event handlers"
```

---

### Task 6: 添加主入口

**Files:**
- Modify: `auto_typewriter.py` (添加main入口)

- [ ] **Step 1: 在文件末尾添加main入口**

```python
if __name__ == '__main__':
    try:
        import pyautogui
        import pyperclip
    except ImportError as e:
        print(f"错误: 缺少依赖库 - {e}")
        print("请运行: pip install pyautogui pyperclip")
        exit(1)

    app = GUIApp()
    app.run()
```

- [ ] **Step 2: 验证完整脚本可导入**

```bash
python -c "import auto_typewriter; print('Script OK')"
```

Expected: Output "Script OK"

- [ ] **Step 3: Commit**

```bash
git add auto_typewriter.py
git commit -m "feat: add main entry point"
```

---

### Task 7: 手动验证测试

**Files:**
- None (手动测试)

- [ ] **Step 1: 启动脚本**

```bash
python auto_typewriter.py
```

Expected: GUI窗口出现，居中显示

- [ ] **Step 2: 测试纯英文输入**

1. 在文本框输入: `Hello World`
2. 设置固定速度10字/秒
3. 打开记事本
4. 点击"开始"
5. 切换到记事本窗口
6. 验证文本逐字出现

Expected: Hello World正确输出到记事本

- [ ] **Step 3: 测试中文输入**

1. 清空文本框
2. 输入: `你好世界`
3. 点击"开始"
4. 切换到记事本
5. 验证中文正确出现

Expected: 你好世界正确输出

- [ ] **Step 4: 测试暂停/继续功能**

1. 输入较长文本（50字以上）
2. 开始打字
3. 打字中途点击"暂停"
4. 验证停止输入，按钮变为"继续"
5. 点击"继续"
6. 验证从断点继续打字

Expected: 暂停/继续功能正常工作

- [ ] **Step 5: 测试停止功能**

1. 输入较长文本
2. 开始打字
3. 中途点击"停止"
4. 验证立即停止，状态显示"完成"

Expected: 停止功能正常工作

- [ ] **Step 6: 测试随机速度模式**

1. 选择随机速度模式
2. 设置最小5字/秒，最大15字/秒
3. 开始打字
4. 观察输入间隔变化

Expected: 输入速度在范围内变化

---

### Task 8: 添加输入验证

**Files:**
- Modify: `auto_typewriter.py` (添加速度输入验证)

- [ ] **Step 1: 在_on_start方法开头添加速度验证**

修改 `_on_start` 方法：

```python
    def _on_start(self) -> None:
        """开始按钮事件"""
        text = self.text_input.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning("提示", "请输入文本")
            return

        # 验证速度输入
        try:
            if self.speed_mode.get() == 'fixed':
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

        self._update_speed_controller()

        # 倒计时3秒
        self.status_var.set("3秒后开始... 请切换到目标窗口")
        self._countdown(3, lambda: self._start_typing(text))
```

- [ ] **Step 2: 验证语法正确**

```bash
python -c "from auto_typewriter import GUIApp; print('Validation OK')"
```

Expected: Output "Validation OK"

- [ ] **Step 3: Commit**

```bash
git add auto_typewriter.py
git commit -m "feat: add speed input validation"
```

---

## Self-Review Checklist

### Spec Coverage

| Spec Requirement | Task |
|-----------------|------|
| GUI界面 | Task 4, 5 |
| 速度控制：固定+随机 | Task 2, 4 |
| 触发机制：3秒延时 | Task 5 |
| 控制功能：暂停/继续/停止 | Task 3, 5 |
| 字符支持：中英文标点 | Task 3 |
| 速度默认10字/秒，范围1-50 | Task 4, 8 |

### Placeholder Scan
- No TBD, TODO, or placeholder patterns found
- All code blocks contain complete implementation
- No "add appropriate handling" or similar vague steps

### Type Consistency
- `SpeedController` method `get_interval()` returns `float` - used correctly in TypewriterEngine
- `TypewriterEngine` callbacks `on_progress` and `on_complete` - used correctly in GUI
- Variable names consistent across tasks

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-09-auto-typewriter.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**