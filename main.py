import time
import pyperclip
import platform

# 导入操作系统适配器
from os_adapters import os_adapter

# 导入配置和功能模块
from config import DELAY, FONT_FILE, BASEIMAGE_FILE, AUTO_SEND_IMAGE, AUTO_PASTE_IMAGE, BLOCK_HOTKEY, HOTKEY, \
    SEND_HOTKEY, PASTE_HOTKEY, CUT_HOTKEY, SELECT_ALL_HOTKEY, TEXT_BOX_TOPLEFT, IMAGE_BOX_BOTTOMRIGHT, \
    BASE_OVERLAY_FILE, USE_BASE_OVERLAY
from text_fit_draw import draw_text_auto
from image_fit_paste import paste_image_auto

# 检测当前操作系统
current_os = platform.system()

# macOS特定的热键适配
if current_os == 'Darwin':
    # 在macOS上将热键中的ctrl替换为cmd，将alt替换为opt
    HOTKEY = os_adapter.adapt_hotkey_for_macos(HOTKEY)
    SELECT_ALL_HOTKEY = os_adapter.adapt_hotkey_for_macos(SELECT_ALL_HOTKEY)
    CUT_HOTKEY = os_adapter.adapt_hotkey_for_macos(CUT_HOTKEY)
    PASTE_HOTKEY = os_adapter.adapt_hotkey_for_macos(PASTE_HOTKEY)
    SEND_HOTKEY = os_adapter.adapt_hotkey_for_macos(SEND_HOTKEY)


# 使用操作系统适配器进行剪贴板操作
def copy_png_bytes_to_clipboard(png_bytes: bytes):
    os_adapter.copy_png_bytes_to_clipboard(png_bytes)


# 使用操作系统适配器进行键盘事件模拟
def send_keystroke(key_combo):
    os_adapter.send_keystroke(key_combo)


# 使用操作系统适配器尝试获取图像
def try_get_image():
    return os_adapter.try_get_image()


# 剪切全部文本并获取内容
def cut_all_and_get_text() -> str:
    """
    模拟全选/剪切全部文本，并返回剪切得到的内容。
    """
    # 备份原剪贴板
    old_clip = pyperclip.paste()

    # 清空剪贴板，防止读到旧数据
    pyperclip.copy("")

    # 发送全选和剪切快捷键（使用跨平台函数）
    send_keystroke(SELECT_ALL_HOTKEY)
    send_keystroke(CUT_HOTKEY)
    time.sleep(DELAY)

    # 获取剪切后的内容
    new_clip = pyperclip.paste()

    return new_clip


# 主要处理逻辑
def Start():
    print("Start generate...")

    text = cut_all_and_get_text()
    image = try_get_image()

    if text == "" and image is None:
        print("no text or image")
        return

    png_bytes = None

    if image is not None:
        print("Get image")

        try:
            png_bytes = paste_image_auto(
                image_source=BASEIMAGE_FILE,
                image_overlay=BASE_OVERLAY_FILE if USE_BASE_OVERLAY else None,
                top_left=TEXT_BOX_TOPLEFT,
                bottom_right=IMAGE_BOX_BOTTOMRIGHT,
                content_image=image,
                align="center",
                valign="middle",
                padding=12,
                allow_upscale=True,
                keep_alpha=True,  # 使用内容图 alpha 作为蒙版
            )
        except Exception as e:
            print("Generate image failed:", e)
            return

    elif text != "":
        print("Get text: " + text)

        try:
            png_bytes = draw_text_auto(
                image_source=BASEIMAGE_FILE,
                image_overlay=BASE_OVERLAY_FILE if USE_BASE_OVERLAY else None,
                top_left=TEXT_BOX_TOPLEFT,
                bottom_right=IMAGE_BOX_BOTTOMRIGHT,
                text=text,
                color=(0, 0, 0),
                max_font_height=64,  # 例如限制最大字号高度为 64 像素
                font_path=FONT_FILE,
            )
        except Exception as e:
            print("Generate image failed:", e)
            return

    if png_bytes is None:
        print("Generate image failed!")
        return

    copy_png_bytes_to_clipboard(png_bytes)

    if AUTO_PASTE_IMAGE:
        send_keystroke(PASTE_HOTKEY)  # 使用跨平台函数

        time.sleep(DELAY)

        if AUTO_SEND_IMAGE:
            send_keystroke(SEND_HOTKEY)  # 使用跨平台函数

    print("Generate image successed!")


# 主程序入口
if __name__ == "__main__":
    try:
        # 使用操作系统适配器启动热键监听
        os_adapter.start_hotkey_listener(HOTKEY, Start, BLOCK_HOTKEY or HOTKEY == SEND_HOTKEY)
    except Exception as e:
        print(f"发生错误: {e}")
    except KeyboardInterrupt:
        print("\n程序已被用户中断。")
    finally:
        print("程序已退出。")