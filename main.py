# hotkey_demo.py
import io
import logging
import time
from typing import Optional, Tuple

import keyboard
import psutil
import pyperclip
import win32clipboard
import win32gui
import win32process
from PIL import Image

from config import Config
from image_fit_paste import paste_image_auto
from text_fit_draw import draw_text_auto

config = Config()

logging.basicConfig(
    level=getattr(logging, config.logging_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)

last_used_image_file = config.baseimage_file


def get_foreground_window_process_name() -> Optional[str]:
    """
    获取当前前台窗口的进程名称
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        return process.name().lower()

    except Exception as e:
        logging.error(f"无法获取当前进程名称: {e}")
        return None


def copy_png_bytes_to_clipboard(png_bytes: bytes):
    """
    将 PNG 字节流复制到剪贴板（转换为 DIB 格式）
    """
    # 打开 PNG 字节为 Image
    image = Image.open(io.BytesIO(png_bytes))
    # 转换成 BMP 字节流（去掉 BMP 文件头的前 14 个字节）
    with io.BytesIO() as output:
        image.convert("RGB").save(output, "BMP")
        bmp_data = output.getvalue()[14:]

    # 打开剪贴板并写入 DIB 格式
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data)
    win32clipboard.CloseClipboard()



def try_get_image() -> Optional[Image.Image]:
    """
    尝试从剪贴板获取图像，如果没有图像则返回 None。
    仅支持 Windows。
    """
    image = None  # 确保无论如何都定义了 image

    try:
        win32clipboard.OpenClipboard()

        # 检查剪贴板中是否有 DIB 格式的图像
        if not win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            return None

        # 获取 DIB 格式的图像数据
        data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
        if not data:
            return None

        # 将 DIB 数据转换为字节流，供 Pillow 打开
        bmp_data = data
        # DIB 格式缺少 BMP 文件头，需要手动加上
        # BMP 文件头是 14 字节，包含 "BM" 标识和文件大小信息
        header = (
            b"BM"
            + (len(bmp_data) + 14).to_bytes(4, "little")
            + b"\x00\x00\x00\x00\x36\x00\x00\x00"
        )
        image = Image.open(io.BytesIO(header + bmp_data))

    except Exception as e:
        logging.error("无法从剪贴板获取图像：%s", e)
    finally:
        try:
            win32clipboard.CloseClipboard()
        except:  # noqa: E722
            pass

    return image


def generate_image():
    """
    生成图像的主函数
    """
    global last_used_image_file  # 保存上次使用差分

    # 检查是否设置了允许的进程列表，如果设置了，则检查当前进程是否在允许列表中
    if config.allowed_processes:
        current_process = get_foreground_window_process_name()
        if current_process is None or current_process not in [
            p.lower() for p in config.allowed_processes
        ]:
            logging.info(f"当前进程 {current_process} 不在允许列表中，跳过执行")
            # 如果不是在允许的进程中，直接发送原始热键
            if not config.block_hotkey:
                keyboard.send(config.hotkey)
            return

    # 备份原剪贴板(只能备份文本内容)
    old_clipboard_content = pyperclip.paste()
    
    # 清空剪贴板，防止读到旧数据
    pyperclip.copy("")

    # 发送 Ctrl+A 和 Ctrl+X
    keyboard.send(config.select_all_hotkey)
    keyboard.send(config.cut_hotkey)
    time.sleep(config.delay)

    # 获取图片
    user_pasted_image = try_get_image()
    # 获取文本
    user_input = pyperclip.paste()
    logging.debug(f"用户粘贴图片: {user_pasted_image is not None}")
    logging.debug(f"用户输入的文本内容: {user_input}")
    logging.debug(f"历史剪贴板内容: {old_clipboard_content}")

    if user_input == "" and user_pasted_image is None:
        logging.info("未检测到文本或图片输入，取消生成")
        return

    logging.info("开始尝试生成图片...")

    png_bytes = None

    # 优先处理图片输入
    if user_pasted_image is not None:
        logging.info("从剪切板中捕获了图片内容")

        try:
            png_bytes = paste_image_auto(
                image_source=last_used_image_file,
                image_overlay=(
                    config.base_overlay_file if config.use_base_overlay else None
                ),
                top_left=config.text_box_topleft,
                bottom_right=config.image_box_bottomright,
                content_image=user_pasted_image,
                align="center",
                valign="middle",
                padding=12,
                allow_upscale=True,
                keep_alpha=True,  # 使用内容图 alpha 作为蒙版
            )
        except Exception as e:
            logging.error("生成图片失败: %s", e)
            return

    # 其次处理文本输入
    elif user_input != "":
        logging.info("从文本生成图片: " + user_input)

        # 查找发送内容是否包含更换差分指令 #差分名#, 如果有则更换差分并移除关键字
        for keyword, img_file in config.baseimage_mapping.items():
            if keyword not in user_input:
                continue
            last_used_image_file = img_file
            user_input = user_input.replace(keyword, "").strip()
            logging.info(f"检测到关键词 '{keyword}'，使用底图: {last_used_image_file}")
            break

        try:
            png_bytes = draw_text_auto(
                image_source=last_used_image_file,
                image_overlay=(
                    config.base_overlay_file if config.use_base_overlay else None
                ),
                top_left=config.text_box_topleft,
                bottom_right=config.image_box_bottomright,
                text=user_input,
                color=(0, 0, 0),
                max_font_height=64,
                font_path=config.font_file,
            )
        except Exception as e:
            logging.error("生成图片失败: %s", e)
            return

    if png_bytes is None:
        logging.error("生成图片失败！未生成 PNG 字节。")
        return

    copy_png_bytes_to_clipboard(png_bytes)

    if config.auto_paste_image:
        keyboard.send(config.paste_hotkey)

        time.sleep(config.delay)

        if config.auto_send_image:
            keyboard.send(config.send_hotkey)

    # 恢复原始剪贴板内容
    pyperclip.copy(old_clipboard_content)

    logging.info("成功地生成并发送图片！")


# 绑定 Ctrl+Alt+H 作为全局热键
is_hotkey_bound = keyboard.add_hotkey(
    config.hotkey,
    generate_image,
    suppress=config.block_hotkey or config.hotkey == config.send_hotkey,
)

logging.info("热键绑定: " + str(bool(is_hotkey_bound)))
logging.info("允许的进程: " + str(config.allowed_processes))
logging.info("键盘监听已启动，按下 {} 以生成图片".format(config.hotkey))

# 保持程序运行
try:
    keyboard.wait()
except KeyboardInterrupt:
    pass  # 允许通过 Ctrl+C 退出程序
