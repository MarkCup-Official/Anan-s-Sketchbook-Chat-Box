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

from config_loader import load_config
from image_fit_paste import paste_image_auto
from text_fit_draw import draw_text_auto

config = load_config()

logging.basicConfig(
    level=getattr(logging, config.logging_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# 当前使用的表情索引
current_emotion = "#普通#"
last_used_image_file = config.baseimage_mapping[current_emotion]
ratio = 1

# 注册表情切换快捷键
def register_emotion_switch_hotkeys():
    """注册表情切换快捷键"""
    def switch_emotion(emotion_tag):
        global current_emotion, last_used_image_file
        current_emotion = emotion_tag
        last_used_image_file = config.baseimage_mapping.get(emotion_tag, config.baseimage_file)
        logging.info(f"已切换到表情: {emotion_tag} ({last_used_image_file})")
    
    for hotkey, emotion_tag in config.emotion_switch_hotkeys.items():
        # 为每个表情快捷键绑定切换函数
        keyboard.add_hotkey(hotkey, switch_emotion, args=(emotion_tag,), suppress=False)


def is_vertical_image(image: Image.Image) -> bool:
    """
    判断图像是否为竖图
    """
    return image.height * ratio > image.width


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


def cut_all_and_get_text() -> Tuple[str, str]:
    """
    模拟 Ctrl+A / Ctrl+X 剪切用户输入的全部文本，并返回剪切得到的内容和原始剪贴板的文本内容。

    这个函数会备份当前剪贴板中的文本内容，然后清空剪贴板。
    """
    # 备份原剪贴板(只能备份文本内容)
    old_clip = pyperclip.paste()

    # 清空剪贴板，防止读到旧数据
    pyperclip.copy("")

    # 发送 Ctrl+A 和 Ctrl+X
    keyboard.send(config.select_all_hotkey)
    keyboard.send(config.cut_hotkey)
    time.sleep(config.delay)

    # 获取剪切后的内容
    new_clip = pyperclip.paste()

    return new_clip, old_clip


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
        get_ratio(x1, y1, x2, y2)
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
                    image_overlay=config.base_overlay_file if config.use_base_overlay else None,
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
                    image_overlay=config.base_overlay_file if config.use_base_overlay else None,
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

    # `cut_all_and_get_text` 会清空剪切板，所以 `try_get_image` 要在前面调用
    user_pasted_image = try_get_image()
    user_input, old_clipboard_content = cut_all_and_get_text()
    logging.debug(f"用户粘贴图片: {user_pasted_image is not None}")
    logging.debug(f"用户输入的文本内容: {user_input}")
    logging.debug(f"历史剪贴板内容: {old_clipboard_content}")

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

    # 解析字符串中的url
    pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    urls = re.findall(pattern, user_input)
    url_to_add = ""
    if urls:
        logging.info(f"识别到链接{urls}")
        # 将urls从list转换为str并分行、格式化
        for urlId in range(len(urls)):
            url = urls[urlId]
            url_to_add += f"[{urlId}] {url} \n"

    copy_png_bytes_to_clipboard(png_bytes)

    if config.auto_paste_image:
        keyboard.send(config.paste_hotkey)

        time.sleep(config.delay)

        # 将链接补充到图片后面
        if urls:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, "\n" + url_to_add)
            win32clipboard.CloseClipboard()
            keyboard.send(config.paste_hotkey)
            time.sleep(config.delay)

        if config.auto_send_image:
            keyboard.send(config.send_hotkey)

    # 恢复原始剪贴板内容
    pyperclip.copy(old_clipboard_content)

    logging.info("成功地生成并发送图片！")

def get_ratio(x1, y1, x2, y2):
    try:
        global ratio
        ratio = (x2 - x1) / (y2 - y1)
        logging.info("比例: %s", ratio)
    except Exception as e:
        logging.error("计算比例时出错: %s", e)

# 绑定 Ctrl+Alt+H 作为全局热键
is_hotkey_bound = keyboard.add_hotkey(
    config.hotkey,
    generate_image,
    suppress=config.block_hotkey or config.hotkey == config.send_hotkey,
)

logging.info("热键绑定: " + str(bool(is_hotkey_bound)))
logging.info("允许的进程: " + str(config.allowed_processes))
logging.info("键盘监听已启动，按下 {} 以生成图片".format(config.hotkey))

# 注册表情切换快捷键
register_emotion_switch_hotkeys()
logging.info("表情切换快捷键已注册: " + str(config.emotion_switch_hotkeys))

# 保持程序运行
try:
    keyboard.wait()
except KeyboardInterrupt:
    pass  # 允许通过 Ctrl+C 退出程序
