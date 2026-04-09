# Auto Typewriter 设计文档

## Context

用户需要在写作作业平台提交文本，但平台禁止直接粘贴，只能键盘逐字输入。用户已写好文本，需要重新打一遍很耗时。

**问题**：手动重复输入已完成文本，效率低，浪费时间。

**解决方案**：创建自动打字脚本，模拟键盘输入，将文本逐字打出。

**预期效果**：一键触发自动输入，节省时间，提高效率。

---

## Requirements

### 核心需求
- GUI界面：直观易用，可预览文本
- 速度控制：固定速度 + 随机变化两种模式
- 触发机制：点击开始后3秒延时，可切换窗口
- 控制功能：暂停/继续、停止/取消
- 字符支持：中文、英文、标点符号

### 速度规格
- 固定速度：默认10字/秒，范围1-50字/秒
- 随机速度：默认5-15字/秒范围，最小可设1，最大可设50

---

## Architecture

### 技术选型
- **GUI框架**：tkinter（Python标准库，无需额外安装）
- **键盘模拟**：pyautogui（成熟稳定，支持Unicode输入）
- **依赖管理**：单脚本 + pyproject.toml记录pyautogui依赖

### 文件结构
```
c:\Users\fbif9\PycharmProjects\TTS\
├── auto_typewriter.py    # 主脚本（单文件实现）
└── pyproject.toml        # 依赖记录（可选）
```

### 模块划分（单文件内）

1. **TypewriterEngine** - 打字引擎类
   - `start_typing(text, speed_config)` - 开始打字
   - `pause()` - 暂停
   - `resume()` - 继续打字
   - `stop()` - 停止并重置
   - `_type_char(char)` - 单字符输入（处理中英文）

2. **SpeedController** - 速度控制器
   - `get_interval()` - 获取下次输入间隔
   - 固定模式：返回常量间隔
   - 随机模式：返回随机间隔（在范围内）

3. **GUIApp** - Tkinter应用
   - 文本输入框（多行）
   - 速度设置面板（单选按钮 + 输入框）
   - 控制按钮（开始、暂停、停止、清空）
   - 状态栏（显示进度）

---

## Data Flow

```
用户输入文本 → GUI文本框
              ↓
用户配置速度 → SpeedController
              ↓
点击"开始" → 倒计时3秒 → TypewriterEngine.start_typing()
              ↓
         打字循环（逐字符）
              ↓
         pyautogui输入 → 目标窗口
              ↓
         状态更新 → GUI状态栏
```

---

## Implementation Details

### 中英文输入处理

pyautogui默认不支持中文直接输入。使用以下方法：

```python
import pyautogui
import pyperclip
import time

def type_char(char):
    # 英文和部分符号：直接输入
    if char.isascii():
        pyautogui.write(char)
    else:
        # 中文和Unicode字符：复制粘贴单字符
        pyperclip.copy(char)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.05)  # 等待粘贴完成
```

**注意**：此方法实际上是逐字符复制粘贴，但视觉效果与逐字输入相同。若需更真实的键盘模拟，可使用Windows API `SendInput`，但实现复杂度更高。

### 速度控制实现

```python
import random

class SpeedController:
    def __init__(self, mode='fixed', fixed_speed=10,
                 min_speed=5, max_speed=15):
        self.mode = mode
        self.fixed_speed = fixed_speed
        self.min_speed = min_speed
        self.max_speed = max_speed

    def get_interval(self):
        if self.mode == 'fixed':
            return 1.0 / self.fixed_speed
        else:
            speed = random.uniform(self.min_speed, self.max_speed)
            return 1.0 / speed
```

### 打字主循环

```python
def start_typing(self, text, speed_controller):
    self._paused = False
    self._stopped = False
    self._position = 0

    for i, char in enumerate(text):
        if self._stopped:
            break
        while self._paused:
            time.sleep(0.1)
            if self._stopped:
                break

        self._type_char(char)
        self._position = i + 1
        time.sleep(speed_controller.get_interval())
```

---

## GUI Layout

```
┌─────────────────────────────────────┐
│  Auto Typewriter v1.0               │
├─────────────────────────────────────┤
│  [文本输入框 - 多行滚动]              │
│  height=15行                        │
│                                     │
├─────────────────────────────────────┤
│  速度设置:                          │
│  ○ 固定速度: [10] 字/秒             │
│  ○ 随机速度: 最小[5] 最大[15]       │
├─────────────────────────────────────┤
│  [开始]  [暂停]  [停止]  [清空]      │
├─────────────────────────────────────┤
│  状态: 打字中 (12/100)              │
└─────────────────────────────────────┘
```

**窗口属性：**
- 尺寸：500x400像素
- 可调整大小
- 居中显示

---

## Error Handling

| 错误场景 | 处理方式 |
|---------|---------|
| pyautogui未安装 | 启动时提示安装命令 |
| 文本为空 | 点击开始时提示"请输入文本" |
| 目标窗口未激活 | 倒计时3秒给用户切换时间 |
| 打字中途出错 | 记录当前位置，显示错误，可继续 |

---

## Verification

### 手动测试步骤

1. 运行脚本：`python auto_typewriter.py`
2. 输入测试文本（包含中英文和标点）
3. 设置速度（固定10字/秒）
4. 打开记事本或目标平台窗口
5. 点击"开始"，观察倒计时
6. 切换到目标窗口
7. 验证文本逐字出现
8. 测试暂停/继续、停止功能

### 测试用例

| 测试 | 输入 | 预期 |
|-----|------|-----|
| 纯英文 | Hello World | 正确输出 |
| 纯中文 | 你好世界 | 正确输出 |
| 混合文本 | Hello世界！ | 正确输出 |
| 固定速度 | 5字/秒 | 观察间隔均匀 |
| 随机速度 | 5-15字/秒 | 观察间隔变化 |
| 暂停继续 | 50字文本 | 中途暂停后继续 |
| 停止 | 100字文本 | 中途停止，状态重置 |

---

## Dependencies

```toml
# pyproject.toml 或 requirements.txt
[project]
dependencies = [
    "pyautogui>=0.9.54",
    "pyperclip>=1.8.2",  # 中文输入支持
]
```

安装命令：
```bash
pip install pyautogui pyperclip
```

---

## Known Limitations

1. **中文输入方式**：使用复制粘贴而非真实键盘事件，部分平台可能检测剪贴板操作
2. **跨平台**：设计为Windows优先，macOS/Linux需测试
3. **管理员权限**：pyautogui不需要管理员权限，但某些受保护窗口可能无法接收输入