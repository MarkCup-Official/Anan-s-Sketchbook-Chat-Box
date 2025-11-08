"""
基础操作系统适配器类
"""


class BaseOSAdapter:
    """操作系统适配器基类"""

    def copy_png_bytes_to_clipboard(self, png_bytes):
        raise NotImplementedError("子类必须实现此方法")

    def send_keystroke(self, key_combo):
        raise NotImplementedError("子类必须实现此方法")

    def try_get_image(self):
        raise NotImplementedError("子类必须实现此方法")

    def start_hotkey_listener(self, hotkey, start_func, block_hotkey=False):
        raise NotImplementedError("子类必须实现此方法")