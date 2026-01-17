# hotkey_demo.py
import atexit
import io
import logging
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Optional

import keyboard
import psutil
import pyperclip
import win32clipboard
import win32gui
import win32process
from PIL import Image

from config_loader import load_config
from image_fit_paste import paste_image_auto
from text_fit_draw import draw_text_auto

config = load_config()

logging.basicConfig(
    level=getattr(logging, config.logging_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# 当前使用的表情索引（只保留表情相关变量）
current_emotion = "#普通#"
last_used_image_file = config.baseimage_mapping.get(
    current_emotion, config.baseimage_file
)

# 用于线程安全的锁
_emotion_lock = threading.Lock()
# 用于防止热键处理重入的标志
_is_processing = threading.Lock()
# 线程池，避免频繁创建线程
_thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ImageGen")
# 缓存允许的进程列表（小写）
_allowed_processes_lower = (
    [p.lower() for p in config.allowed_processes] if config.allowed_processes else []
)


def release_all_modifiers():
    """
    释放所有可能被按住的修饰键
    这是一个轻量级的状态清理，不会影响热键注册
    """
    try:
        for key in [
            "alt",
            "ctrl",
            "shift",
            "win",
            "left alt",
            "right alt",
            "left ctrl",
            "right ctrl",
            "left shift",
            "right shift",
        ]:
            try:
                keyboard.release(key)
            except Exception:
                pass
        logging.debug("修饰键已释放")
    except Exception as e:
        logging.debug(f"释放修饰键时出错: {e}")


def register_emotion_switch_hotkeys_internal():
    """内部函数：注册表情切换快捷键（不输出日志）"""

    def switch_emotion(emotion_tag):
        global current_emotion, last_used_image_file
        with _emotion_lock:
            current_emotion = emotion_tag
            last_used_image_file = config.baseimage_mapping.get(
                emotion_tag, config.baseimage_file
            )
        logging.info(f"已切换到表情: {emotion_tag} ({last_used_image_file})")

    for hotkey, emotion_tag in config.emotion_switch_hotkeys.items():
        keyboard.add_hotkey(
            hotkey,
            switch_emotion,
            args=(emotion_tag,),
            suppress=True,
            trigger_on_release=False,
        )


def register_emotion_switch_hotkeys():
    """注册表情切换快捷键（首次注册，带日志）"""
    register_emotion_switch_hotkeys_internal()
    logging.info("表情切换快捷键已注册")


def is_vertical_image(image: Image.Image) -> bool:
    """
    判断图像是否为竖图
    """
    # 使用配置的区域比例来判断
    x1, y1 = config.text_box_topleft
    x2, y2 = config.image_box_bottomright
    region_ratio = (x2 - x1) / (y2 - y1) if (y2 - y1) > 0 else 1
    return image.height * region_ratio > image.width


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


def safe_send_key(hotkey: str):
    """
    安全地发送按键，确保修饰键状态正确释放

    这个函数在发送按键后会释放所有修饰键，
    防止 Alt/Ctrl/Shift 被卡住导致后续热键失效
    """
    try:
        keyboard.send(hotkey)
        time.sleep(0.02)  # 短暂延迟
    except Exception as e:
        logging.warning(f"发送按键 {hotkey} 失败: {e}")
    finally:
        # 释放所有可能被卡住的修饰键
        try:
            for key in ["alt", "ctrl", "shift"]:
                keyboard.release(key)
        except Exception:
            pass


def copy_png_bytes_to_clipboard(png_bytes: bytes, max_retries: int = 3) -> bool:
    """
    将 PNG 字节流复制到剪贴板（转换为 DIB 格式）

    Args:
        png_bytes: PNG 图像的字节数据
        max_retries: 最大重试次数

    Returns:
        bool: 是否成功复制到剪贴板
    """
    # 打开 PNG 字节为 Image
    image = Image.open(io.BytesIO(png_bytes))
    # 转换成 BMP 字节流（去掉 BMP 文件头的前 14 个字节）
    with io.BytesIO() as output:
        image.convert("RGB").save(output, "BMP")
        bmp_data = output.getvalue()[14:]

    # 打开剪贴板并写入 DIB 格式，带重试机制
    for attempt in range(max_retries):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data)
                return True
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            logging.warning(f"复制到剪贴板失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(0.1)  # 短暂延迟后重试

    logging.error("无法将图像复制到剪贴板")
    return False


def try_get_image(max_retries: int = 3) -> Optional[Image.Image]:
    """
    尝试从剪贴板获取图像，如果没有图像则返回 None。
    仅支持 Windows。

    Args:
        max_retries: 最大重试次数

    Returns:
        Optional[Image.Image]: 获取到的图像，或 None
    """
    for attempt in range(max_retries):
        clipboard_opened = False
        try:
            win32clipboard.OpenClipboard()
            clipboard_opened = True

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
            # 复制图像数据以避免剪贴板关闭后数据失效
            image_data = io.BytesIO(header + bmp_data)
            image = Image.open(image_data)
            # 加载图像数据到内存，避免延迟加载问题
            image.load()
            return image.copy()

        except Exception as e:
            if attempt < max_retries - 1:
                logging.debug(
                    f"从剪贴板获取图像失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(0.1)
            else:
                logging.error("无法从剪贴板获取图像：%s", e)
        finally:
            if clipboard_opened:
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass

    return None


def process_text_and_image(text: str, image: Optional[Image.Image]) -> Optional[bytes]:
    """
    同时处理文本和图像内容，将其绘制到同一张图片上
    """
    if text == "" and image is None:
        return None

    # 获取配置的区域坐标
    x1, y1 = config.text_box_topleft
    x2, y2 = config.image_box_bottomright
    region_width = x2 - x1
    region_height = y2 - y1

    # 只有图像的情况
    if text == "" and image is not None:
        logging.info("从剪切板中捕获了图片内容")
        try:
            return paste_image_auto(
                image_source=last_used_image_file,
                image_overlay=(
                    config.base_overlay_file if config.use_base_overlay else None
                ),
                top_left=(x1, y1),
                bottom_right=(x2, y2),
                content_image=image,
                align="center",
                valign="middle",
                padding=12,
                allow_upscale=True,
                keep_alpha=True,
            )
        except Exception as e:
            logging.error("生成图片失败: %s", e)
            return None

    # 只有文本的情况
    elif text != "" and image is None:
        logging.info("从文本生成图片: " + text)
        try:
            return draw_text_auto(
                image_source=last_used_image_file,
                image_overlay=(
                    config.base_overlay_file if config.use_base_overlay else None
                ),
                top_left=(x1, y1),
                bottom_right=(x2, y2),
                text=text,
                color=(0, 0, 0),
                max_font_height=64,
                font_path=config.font_file,
                wrap_algorithm=config.text_wrap_algorithm,  # 添加这一行以使用配置的算法
            )
        except Exception as e:
            logging.error("生成图片失败: %s", e)
            return None

    # 同时有图像和文本的情况
    else:
        logging.info("同时处理文本和图片内容")
        logging.info("文本内容: " + text)
        try:
            # 根据图像方向决定排布方式
            if is_vertical_image(image):
                logging.info("使用左右排布（竖图）")
                # 左右排布：图像在左，文本在右
                # 计算左右区域宽度（各占一半，留出间距）
                spacing = 10  # 左右区域之间的间距
                left_width = region_width // 2 - spacing // 2
                right_width = region_width - left_width - spacing

                # 左区域（图像）
                left_region_right = x1 + left_width
                # 右区域（文本）
                right_region_left = left_region_right + spacing

                # 先绘制左半部分的图像
                intermediate_bytes = paste_image_auto(
                    image_source=last_used_image_file,
                    image_overlay=None,  # 暂时不应用overlay
                    top_left=(x1, y1),
                    bottom_right=(left_region_right, y2),
                    content_image=image,
                    align="center",
                    valign="middle",
                    padding=12,
                    allow_upscale=True,
                    keep_alpha=True,
                )

                # 在已有图像基础上添加右半部分的文本
                final_bytes = draw_text_auto(
                    image_source=io.BytesIO(intermediate_bytes),
                    image_overlay=(
                        config.base_overlay_file if config.use_base_overlay else None
                    ),
                    top_left=(right_region_left, y1),
                    bottom_right=(x2, y2),
                    text=text,
                    color=(0, 0, 0),
                    max_font_height=64,
                    font_path=config.font_file,
                    wrap_algorithm=config.text_wrap_algorithm,  # 添加这一行以使用配置的算法
                )
            else:
                logging.info("使用上下排布（横图）")
                # 上下排布：图像在上，文本在下
                # 动态计算图像和文本的区域分配
                # 根据文本长度和图像尺寸计算合适的比例

                # 估算文本所需高度（使用最大字体高度的一半作为初始估算）
                estimated_text_height = min(region_height // 2, 100)

                # 图像区域（上半部分）
                image_region_bottom = y1 + (region_height - estimated_text_height)

                # 文本区域（下半部分）
                text_region_top = image_region_bottom
                text_region_bottom = y2

                # 先绘制图像
                intermediate_bytes = paste_image_auto(
                    image_source=last_used_image_file,
                    image_overlay=None,  # 暂时不应用overlay
                    top_left=(x1, y1),
                    bottom_right=(x2, image_region_bottom),
                    content_image=image,
                    align="center",
                    valign="middle",
                    padding=12,
                    allow_upscale=True,
                    keep_alpha=True,
                )

                # 在已有图像基础上添加文本
                final_bytes = draw_text_auto(
                    image_source=io.BytesIO(intermediate_bytes),
                    image_overlay=(
                        config.base_overlay_file if config.use_base_overlay else None
                    ),
                    top_left=(x1, text_region_top),
                    bottom_right=(x2, text_region_bottom),
                    text=text,
                    color=(0, 0, 0),
                    max_font_height=64,
                    font_path=config.font_file,
                    wrap_algorithm=config.text_wrap_algorithm,  # 添加这一行以使用配置的算法
                )

            return final_bytes

        except Exception as e:
            logging.error("生成图片失败: %s", e)
            return None


def generate_image_async():
    """
    在线程池中触发图片生成
    这样不会阻塞键盘库的事件循环，确保热键持续可用
    """
    # 先释放修饰键，避免干扰
    release_all_modifiers()

    # 短暂延迟，确保按键完全释放
    time.sleep(0.1)

    # 使用线程池执行，避免频繁创建线程
    _thread_pool.submit(generate_image_worker)


def generate_image_worker():
    """
    生成图像的主函数
    只处理 QQ 输入框中的内容，不读取系统剪贴板原有内容
    """
    global last_used_image_file  # 保存上次使用差分

    # 使用锁防止重入
    if not _is_processing.acquire(blocking=False):
        logging.debug("正在处理中，跳过本次触发")
        return

    old_clipboard_content = ""
    try:
        # 检查是否设置了允许的进程列表，如果设置了，则检查当前进程是否在允许列表中
        if _allowed_processes_lower:
            current_process = get_foreground_window_process_name()
            if (
                current_process is None
                or current_process not in _allowed_processes_lower
            ):
                logging.info(f"当前进程 {current_process} 不在允许列表中，跳过执行")
                # 如果不是在允许的进程中，直接发送原始热键
                if not config.block_hotkey:
                    safe_send_key(config.hotkey)
                return

        # 备份原剪贴板文本内容
        try:
            old_clipboard_content = pyperclip.paste()
        except Exception:
            old_clipboard_content = ""

        # 先清空剪贴板，确保不会读取到旧内容
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
        except Exception:
            pass

        # 短暂等待确保剪贴板清空
        time.sleep(0.05)

        # 剪切 QQ 输入框中的全部内容 (Ctrl+A, Ctrl+X)
        safe_send_key(config.select_all_hotkey)
        time.sleep(0.05)
        safe_send_key(config.cut_hotkey)
        time.sleep(config.delay)

        # 现在从剪贴板读取内容（此时剪贴板中的内容就是输入框的内容）
        # 读取文本
        try:
            user_input = pyperclip.paste()
        except Exception:
            user_input = ""

        # 读取图片（如果输入框中有图片）
        user_pasted_image = try_get_image()

        logging.debug(f"输入框图片: {user_pasted_image is not None}")
        logging.debug(f"输入框文本: {user_input}")

        if user_input == "" and user_pasted_image is None:
            logging.info("未检测到文本或图片输入，取消生成")
            return

        logging.info("开始尝试生成图片...")

        # 查找发送内容是否包含更换差分指令 #差分名#, 如果有则更换差分并移除关键字
        for keyword, img_file in config.baseimage_mapping.items():
            if keyword not in user_input:
                continue
            last_used_image_file = img_file
            user_input = user_input.replace(keyword, "").strip()
            logging.info(f"检测到关键词 '{keyword}'，使用底图: {last_used_image_file}")
            break

        png_bytes = process_text_and_image(user_input, user_pasted_image)

        if png_bytes is None:
            logging.error("生成图片失败！未生成 PNG 字节。")
            return

        if not copy_png_bytes_to_clipboard(png_bytes):
            logging.error("复制图片到剪贴板失败")
            return

        if config.auto_paste_image:
            time.sleep(0.05)  # 等待剪贴板稳定
            safe_send_key(config.paste_hotkey)
            time.sleep(config.delay)

            if config.auto_send_image:
                safe_send_key(config.send_hotkey)

        logging.info("成功地生成并发送图片！")
    except Exception as e:
        logging.error(f"生成图片过程中发生错误: {e}")
    finally:
        # 尝试恢复原始剪贴板内容
        try:
            if old_clipboard_content:
                pyperclip.copy(old_clipboard_content)
        except Exception as e:
            logging.warning(f"恢复剪贴板内容失败: {e}")

        # 释放锁
        _is_processing.release()

        # 释放所有修饰键，确保热键正常工作
        time.sleep(0.1)  # 短暂等待确保所有按键操作完成
        release_all_modifiers()


# 防止重复清理的标志
_cleanup_done = False
_cleanup_lock = threading.Lock()


def cleanup():
    """
    清理函数，在程序退出时调用
    确保只执行一次清理操作
    """
    global _cleanup_done

    with _cleanup_lock:
        if _cleanup_done:
            return
        _cleanup_done = True

    logging.info("正在清理资源...")

    # 关闭线程池
    try:
        _thread_pool.shutdown(wait=False)
        logging.info("线程池已关闭")
    except Exception as e:
        logging.error(f"关闭线程池时出错: {e}")

    # 清理键盘钩子
    try:
        keyboard.unhook_all()
        logging.info("键盘钩子已清理完成")
    except Exception as e:
        logging.error(f"清理键盘钩子时出错: {e}")

    # 确保剪贴板被关闭
    try:
        win32clipboard.CloseClipboard()
    except Exception:
        pass  # 剪贴板可能已经关闭

    logging.info("资源清理完成")


def signal_handler(signum, frame):
    """
    信号处理函数，用于处理 Ctrl+C 等信号
    """
    logging.info(f"收到信号 {signum}，正在退出...")
    cleanup()
    sys.exit(0)


def init_hotkeys():
    """
    初始化所有热键注册
    """
    # 绑定主热键
    keyboard.add_hotkey(
        config.hotkey,
        generate_image_async,
        suppress=config.block_hotkey or config.hotkey == config.send_hotkey,
    )
    logging.info("主热键已绑定: " + config.hotkey)

    # 注册表情切换快捷键
    register_emotion_switch_hotkeys()
    logging.info(
        "表情切换快捷键已注册: " + str(list(config.emotion_switch_hotkeys.keys()))
    )


# 注册清理函数
atexit.register(cleanup)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
# Windows 特有的 SIGBREAK 信号（Ctrl+Break）
if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, signal_handler)


def main():
    """
    程序主入口
    """
    # 初始化热键
    init_hotkeys()

    logging.info("允许的进程: " + str(config.allowed_processes))
    logging.info("程序已启动，按 Ctrl+C 可安全退出")

    try:
        # 使用循环代替 keyboard.wait()，以便更好地处理退出
        while True:
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                logging.info("收到键盘中断信号")
                break
    except Exception as e:
        logging.error(f"程序异常: {e}")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
