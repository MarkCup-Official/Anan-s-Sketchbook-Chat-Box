"""
Windows操作系统适配器实现
"""

import sys
import io
from .base_adapter import BaseOSAdapter

class WindowsAdapter(BaseOSAdapter):
    """Windows操作系统适配器"""
    def __init__(self):
        try:
            import keyboard
            import win32clipboard
            from PIL import Image
            
            self.keyboard = keyboard
            self.win32clipboard = win32clipboard
            self.Image = Image
        except ImportError as e:
            print(f"错误：在Windows系统上缺少必要的依赖。请运行 'pip install keyboard pywin32 Pillow': {str(e)}")
            sys.exit(1)

    def copy_png_bytes_to_clipboard(self, png_bytes):
        image = self.Image.open(io.BytesIO(png_bytes))
        with io.BytesIO() as output:
            image.convert("RGB").save(output, "BMP")
            bmp_data = output.getvalue()[14:]
        self.win32clipboard.OpenClipboard()
        self.win32clipboard.EmptyClipboard()
        self.win32clipboard.SetClipboardData(self.win32clipboard.CF_DIB, bmp_data)
        self.win32clipboard.CloseClipboard()

    def send_keystroke(self, key_combo):
        self.keyboard.send(key_combo)

    def try_get_image(self):
        try:
            self.win32clipboard.OpenClipboard()
            if self.win32clipboard.IsClipboardFormatAvailable(self.win32clipboard.CF_DIB):
                data = self.win32clipboard.GetClipboardData(self.win32clipboard.CF_DIB)
                if data:
                    # 将 DIB 数据转换为字节流，供 Pillow 打开
                    bmp_data = data
                    # DIB 格式缺少 BMP 文件头，需要手动加上
                    header = b'BM' + (len(bmp_data) + 14).to_bytes(4, 'little') + b'\x00\x00\x00\x00\x36\x00\x00\x00'
                    image = self.Image.open(io.BytesIO(header + bmp_data))
                    return image
        except Exception as e:
            print("无法从剪贴板获取图像：", e)
        finally:
            try:
                self.win32clipboard.CloseClipboard()
            except:
                pass
        return None

    def start_hotkey_listener(self, hotkey, start_func, block_hotkey=False):
        ok = self.keyboard.add_hotkey(hotkey, start_func, suppress=block_hotkey)
        print("Starting...")
        print(f"Hot key bind: {str(bool(ok))}")
        print(f"监听热键: {hotkey}")
        self.keyboard.wait()