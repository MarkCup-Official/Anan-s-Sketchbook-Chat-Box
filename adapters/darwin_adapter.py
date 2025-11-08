"""
macOS操作系统适配器实现
"""

import sys
import time
import io
import getpass
from .base_adapter import BaseOSAdapter


class DarwinAdapter(BaseOSAdapter):
    """macOS操作系统适配器"""

    def __init__(self):
        try:
            # 将macOS特定的模块导入移至初始化方法中
            from AppKit import NSPasteboard, NSData
            from Quartz import CGEventCreateKeyboardEvent, CGEventPost, kCGHIDEventTap
            from Quartz import kCGEventKeyDown, kCGEventKeyUp
            from pynput import keyboard as pynput_keyboard
            from PIL import Image
            
            self.NSPasteboard = NSPasteboard
            self.NSData = NSData
            self.CGEventCreateKeyboardEvent = CGEventCreateKeyboardEvent
            self.CGEventPost = CGEventPost
            self.kCGHIDEventTap = kCGHIDEventTap
            self.kCGEventKeyDown = kCGEventKeyDown
            self.kCGEventKeyUp = kCGEventKeyUp
            self.pynput_keyboard = pynput_keyboard
            self.Image = Image
        except ImportError as e:
            print(f"错误：在macOS系统上缺少必要的依赖。请运行 'pip install pyobjc pynput Pillow': {e.msg}")
            sys.exit(1)

    def adapt_hotkey_for_macos(self, hotkey):
        """在macOS上将热键中的ctrl替换为cmd，将alt替换为opt"""
        if isinstance(hotkey, str):
            # 处理单个热键组合
            adapted = hotkey.lower()
            # 将ctrl替换为cmd
            adapted = adapted.replace('ctrl+', 'cmd+')
            # 将alt替换为opt
            adapted = adapted.replace('alt+', 'opt+')
            return adapted
        return hotkey

    def copy_png_bytes_to_clipboard(self, png_bytes):
        pasteboard = self.NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        ns_data = self.NSData.dataWithBytes_length_(png_bytes, len(png_bytes))
        pasteboard.setData_forType_(ns_data, "public.png")

    def send_keystroke(self, key_combo):
        """macOS 键盘模拟实现"""

        def press_key(key_code):
            event = self.CGEventCreateKeyboardEvent(None, key_code, True)
            self.CGEventPost(self.kCGHIDEventTap, event)
            # 添加小延时确保按键事件被正确处理
            time.sleep(0.01)

        def release_key(key_code):
            event = self.CGEventCreateKeyboardEvent(None, key_code, False)
            self.CGEventPost(self.kCGHIDEventTap, event)
            # 添加小延时确保按键事件被正确处理
            time.sleep(0.01)

        # 手动定义macOS键盘键码
        kVK_ANSI_A = 0x00
        kVK_ANSI_C = 0x08
        kVK_ANSI_V = 0x09
        kVK_ANSI_X = 0x07
        kVK_Return = 0x24
        kVK_Command = 0x37
        kVK_Control = 0x3B
        kVK_Option = 0x3A
        kVK_Shift = 0x38
        kVK_ANSI_Z = 0x06
        kVK_ANSI_S = 0x01
        kVK_ANSI_D = 0x02
        kVK_ANSI_F = 0x03
        kVK_Delete = 0x75
        kVK_Backspace = 0x33
        kVK_Escape = 0x35
        kVK_Tab = 0x30
        kVK_Space = 0x31
        kVK_UpArrow = 0x7E
        kVK_DownArrow = 0x7D
        kVK_LeftArrow = 0x7B
        kVK_RightArrow = 0x7C

        # 解析热键组合，支持多个修饰键
        key_combo = key_combo.lower()

        # 记录所有需要按下的修饰键
        pressed_modifiers = []

        # 检查并提取修饰键
        if 'cmd+' in key_combo:
            pressed_modifiers.append(kVK_Command)
            key_combo = key_combo.replace('cmd+', '')

        if 'ctrl+' in key_combo:
            pressed_modifiers.append(kVK_Control)
            key_combo = key_combo.replace('ctrl+', '')

        if 'opt+' in key_combo:
            pressed_modifiers.append(kVK_Option)
            key_combo = key_combo.replace('opt+', '')

        if 'shift+' in key_combo:
            pressed_modifiers.append(kVK_Shift)
            key_combo = key_combo.replace('shift+', '')

        # 现在key_combo应该只剩下主键了
        main_key = key_combo.strip()

        # 扩展热键映射表，添加更多常用键
        key_map = {
            'a': kVK_ANSI_A,
            'c': kVK_ANSI_C,
            'v': kVK_ANSI_V,
            'x': kVK_ANSI_X,
            'z': kVK_ANSI_Z,
            's': kVK_ANSI_S,
            'd': kVK_ANSI_D,
            'f': kVK_ANSI_F,
            'enter': kVK_Return,
            'delete': kVK_Delete,
            'backspace': kVK_Backspace,
            'esc': kVK_Escape,
            'escape': kVK_Escape,
            'tab': kVK_Tab,
            'space': kVK_Space,
            'up': kVK_UpArrow,
            'down': kVK_DownArrow,
            'left': kVK_LeftArrow,
            'right': kVK_RightArrow
        }

        if main_key in key_map:
            key_code = key_map[main_key]

            # 按顺序按下所有修饰键
            for modifier_key in pressed_modifiers:
                press_key(modifier_key)

            # 按下目标键
            press_key(key_code)

            # 短暂延迟确保系统识别到组合键
            time.sleep(0.05)

            # 释放目标键
            release_key(key_code)

            # 按相反顺序释放所有修饰键
            for modifier_key in reversed(pressed_modifiers):
                release_key(modifier_key)

            time.sleep(0.05)  # 全局延迟
        else:
            print(f"警告：不支持的热键组合 '{key_combo}' 在macOS上")

    def try_get_image(self):
        try:
            pasteboard = self.NSPasteboard.generalPasteboard()

            # 检查剪贴板中是否有图像数据
            for type in pasteboard.types():
                if "image" in type.lower() or type == "public.png" or type == "public.tiff":
                    # 尝试获取图像数据
                    data = pasteboard.dataForType_(type)
                    if data:
                        # 将 NSData 转换为 bytes
                        png_bytes = data.bytes().tobytes()
                        return self.Image.open(io.BytesIO(png_bytes))

            # 尝试使用 PIL 的 ImageGrab
            try:
                from PIL import ImageGrab
                return ImageGrab.grabclipboard()
            except:
                pass
        except Exception as e:
            print("无法从剪贴板获取图像：", e)
        return None

    def start_hotkey_listener(self, hotkey, start_func, block_hotkey=False):
        if getpass.getuser() != 'root':
            print("\n重要提示：")
            print("在macOS系统上，监听全局键盘事件需要管理员权限。")
            print(f"请使用以下命令以管理员权限运行程序：\n\n  sudo python3 {sys.argv[0]}")
            print("\n程序将尝试继续运行，但可能无法正常监听热键...\n")
    
        print("Starting...")
        print(f"监听热键: {hotkey}")
        print("请按下热键来触发功能...")
    
        # 更强大的热键解析器，支持多个修饰键组合
        def parse_hotkey(hotkey_str):
            """解析热键字符串为修饰键和主键"""
            parts = hotkey_str.split('+')
            if len(parts) == 1:
                return set(), parts[0].strip()
            else:
                modifiers = set(parts[:-1])
                main_key = parts[-1].strip()
                return modifiers, main_key
    
        required_modifiers, target_main_key = parse_hotkey(hotkey.lower())
    
        # 记录当前按下的修饰键
        pressed_modifiers = set()
        # 添加一个标记，用于防止重复触发
        is_hotkey_triggered = False
        # 添加时间戳，用于防止短时间内多次触发
        last_trigger_time = 0
        # 设置触发间隔（秒），防止短时间内多次触发
        TRIGGER_INTERVAL = 0.5
    
        def on_press(key):
            nonlocal is_hotkey_triggered, last_trigger_time
            try:
                # 获取当前时间
                current_time = time.time()
                
                # 如果距离上次触发时间太短，直接返回
                if current_time - last_trigger_time < TRIGGER_INTERVAL:
                    return
    
                # 处理修饰键
                if key == self.pynput_keyboard.Key.cmd or key == self.pynput_keyboard.Key.cmd_l or key == self.pynput_keyboard.Key.cmd_r:
                    pressed_modifiers.add('cmd')
                    # 修饰键按下时重置触发标记
                    is_hotkey_triggered = False
                elif key == self.pynput_keyboard.Key.ctrl or key == self.pynput_keyboard.Key.ctrl_l or key == self.pynput_keyboard.Key.ctrl_r:
                    pressed_modifiers.add('ctrl')
                    is_hotkey_triggered = False
                elif key == self.pynput_keyboard.Key.alt or key == self.pynput_keyboard.Key.alt_l or key == self.pynput_keyboard.Key.alt_r:
                    pressed_modifiers.add('opt')  # 在macOS上，Alt就是Option
                    is_hotkey_triggered = False
                elif key == self.pynput_keyboard.Key.shift or key == self.pynput_keyboard.Key.shift_l or key == self.pynput_keyboard.Key.shift_r:
                    pressed_modifiers.add('shift')
                    is_hotkey_triggered = False
    
                # 检查是否匹配热键组合，但只在未触发过的情况下执行
                if not is_hotkey_triggered:
                    # 特殊处理回车键
                    if key == self.pynput_keyboard.Key.enter:
                        current_key_name = 'enter'
                        
                        # 检查是否是目标主键
                        if current_key_name == target_main_key:
                            # 处理macOS上的修饰键兼容性
                            adjusted_modifiers = required_modifiers.copy()
    
                            # 处理ctrl与cmd的兼容性
                            if 'ctrl' in adjusted_modifiers and 'cmd' in pressed_modifiers:
                                adjusted_modifiers.remove('ctrl')
    
                            # 处理alt与opt的兼容性
                            if 'alt' in adjusted_modifiers:
                                adjusted_modifiers.remove('alt')
                                adjusted_modifiers.add('opt')
    
                            # 检查修饰键是否匹配
                            if adjusted_modifiers.issubset(pressed_modifiers):
                                # 设置触发标记
                                is_hotkey_triggered = True
                                last_trigger_time = current_time
                                start_func()
                    # 处理字符键
                    elif hasattr(key, 'char') and key.char is not None:
                        key_char = key.char.lower()
    
                        # 检查是否是目标主键
                        if key_char == target_main_key:
                            # 处理macOS上ctrl与cmd的兼容性
                            adjusted_modifiers = required_modifiers.copy()
                            if 'ctrl' in adjusted_modifiers and 'cmd' in pressed_modifiers:
                                adjusted_modifiers.remove('ctrl')
    
                            # 同时支持opt和alt键名
                            if 'alt' in adjusted_modifiers:
                                adjusted_modifiers.remove('alt')
                                adjusted_modifiers.add('opt')
    
                            # 检查是否所有必要的修饰键都已按下
                            if adjusted_modifiers.issubset(pressed_modifiers):
                                # 设置触发标记
                                is_hotkey_triggered = True
                                last_trigger_time = current_time
                                start_func()
            except Exception as e:
                print(f"热键处理错误: {e}", exc_info=True)
    
        def on_release(key):
            nonlocal is_hotkey_triggered
            try:
                # 释放修饰键
                if key == self.pynput_keyboard.Key.cmd or key == self.pynput_keyboard.Key.cmd_l or key == self.pynput_keyboard.Key.cmd_r:
                    pressed_modifiers.discard('cmd')
                    # 修饰键释放时重置触发标记
                    is_hotkey_triggered = False
                elif key == self.pynput_keyboard.Key.ctrl or key == self.pynput_keyboard.Key.ctrl_l or key == self.pynput_keyboard.Key.ctrl_r:
                    pressed_modifiers.discard('ctrl')
                    is_hotkey_triggered = False
                elif key == self.pynput_keyboard.Key.alt or key == self.pynput_keyboard.Key.alt_l or key == self.pynput_keyboard.Key.alt_r:
                    pressed_modifiers.discard('opt')
                    is_hotkey_triggered = False
                elif key == self.pynput_keyboard.Key.shift or key == self.pynput_keyboard.Key.shift_l or key == self.pynput_keyboard.Key.shift_r:
                    pressed_modifiers.discard('shift')
                    is_hotkey_triggered = False
                # 普通键释放时也重置触发标记
                elif hasattr(key, 'char') or key == self.pynput_keyboard.Key.enter:
                    is_hotkey_triggered = False
            except Exception as e:
                print(f"热键释放处理错误: {e}")
    
        # 启动监听器，同时监听按键按下和释放事件
        with self.pynput_keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()