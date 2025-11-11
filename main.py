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
# 导入UI模块
from ui import AnanSketchbookUI
import threading
import sys
import customtkinter as ctk

class AnanSketchbookApp:
    def __init__(self):
        self.config = load_config()
        self.setup_logging()
        
        # 初始化变量
        self.current_emotion = "#普通#"
        self.last_used_image_file = self.config.baseimage_mapping[self.current_emotion]
        self.ratio = 1
        self.running = True
        
        # 初始化UI
        self.ui = AnanSketchbookUI(self)
        
        # 注册表情切换快捷键
        self.register_emotion_switch_hotkeys()
        
        # 添加UI日志处理器
        logger = logging.getLogger()
        logger.addHandler(self.ui.log_handler)
        
        # 绑定初始热键
        self.is_hotkey_bound = keyboard.add_hotkey(
            self.config.hotkey,
            self.generate_image,
            suppress=self.config.block_hotkey or self.config.hotkey == self.config.send_hotkey,
        )
        
        self.ui.append_log("热键绑定: " + str(bool(self.is_hotkey_bound)))
        self.ui.append_log("允许的进程: " + str(self.config.allowed_processes))
        self.ui.append_log("键盘监听已启动，按下 {} 以生成图片".format(self.config.hotkey))
        self.ui.append_log("表情切换快捷键已注册: " + str(self.config.emotion_switch_hotkeys))

    def setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(
            level=getattr(logging, self.config.logging_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(message)s",
        )

    def rebind_hotkey(self):
        """重新绑定热键"""
        # 移除旧的热键绑定
        if self.is_hotkey_bound:
            keyboard.remove_hotkey(self.is_hotkey_bound)
        
        # 添加新的热键绑定
        self.is_hotkey_bound = keyboard.add_hotkey(
            self.config.hotkey,
            self.generate_image,
            suppress=self.config.block_hotkey or self.config.hotkey == self.config.send_hotkey,
        )
        
        self.ui.append_log(f"热键已重新绑定为: {self.config.hotkey}")

    def register_emotion_switch_hotkeys(self):
        """注册表情切换快捷键"""
        def switch_emotion(emotion_tag):
            self.current_emotion = emotion_tag
            self.last_used_image_file = self.config.baseimage_mapping.get(emotion_tag, self.config.baseimage_file)
            self.ui.append_log(f"已切换到表情: {emotion_tag} ({self.last_used_image_file})")
        
        for hotkey, emotion_tag in self.config.emotion_switch_hotkeys.items():
            # 为每个表情快捷键绑定切换函数
            keyboard.add_hotkey(hotkey, switch_emotion, args=(emotion_tag,), suppress=False)

    def is_vertical_image(self, image: Image.Image) -> bool:
        """
        判断图像是否为竖图
        """
        return image.height * self.ratio > image.width

    def get_foreground_window_process_name(self) -> Optional[str]:
        """
        获取当前前台窗口的进程名称
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name().lower()

        except Exception as e:
            self.ui.append_log(f"无法获取当前进程名称: {e}")
            return None

    def copy_png_bytes_to_clipboard(self, png_bytes: bytes):
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

    def cut_all_and_get_text(self) -> Tuple[str, str]:
        """
        模拟 Ctrl+A / Ctrl+X 剪切用户输入的全部文本，并返回剪切得到的内容和原始剪贴板的文本内容。

        这个函数会备份当前剪贴板中的文本内容，然后清空剪贴板。
        """
        # 备份原剪贴板(只能备份文本内容)
        old_clip = pyperclip.paste()

        # 清空剪贴板，防止读到旧数据
        pyperclip.copy("")

        # 发送 Ctrl+A 和 Ctrl+X
        keyboard.send(self.config.select_all_hotkey)
        keyboard.send(self.config.cut_hotkey)
        time.sleep(self.config.delay)

        # 获取剪切后的内容
        new_clip = pyperclip.paste()

        return new_clip, old_clip

    def try_get_image(self) -> Optional[Image.Image]:
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
            self.ui.append_log("无法从剪贴板获取图像：" + str(e))
        finally:
            try:
                win32clipboard.CloseClipboard()
            except:  # noqa: E722
                pass

        return image

    def process_text_and_image(self, text: str, image: Optional[Image.Image]) -> Optional[bytes]:
        """
        同时处理文本和图像内容，将其绘制到同一张图片上
        """
        if text == "" and image is None:
            return None

        # 获取配置的区域坐标
        x1, y1 = self.config.text_box_topleft
        x2, y2 = self.config.image_box_bottomright
        region_width = x2 - x1
        region_height = y2 - y1

        # 只有图像的情况
        if text == "" and image is not None:
            self.ui.append_log("从剪切板中捕获了图片内容")
            try:
                return paste_image_auto(
                    image_source=self.last_used_image_file,
                    image_overlay=(
                        self.config.base_overlay_file if self.config.use_base_overlay else None
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
                self.ui.append_log("生成图片失败: " + str(e))
                return None

        # 只有文本的情况
        elif text != "" and image is None:
            self.ui.append_log("从文本生成图片: " + text)
            try:
                return draw_text_auto(
                    image_source=self.last_used_image_file,
                    image_overlay=(
                        self.config.base_overlay_file if self.config.use_base_overlay else None
                    ),
                    top_left=(x1, y1),
                    bottom_right=(x2, y2),
                    text=text,
                    color=(0, 0, 0),
                    max_font_height=64,
                    font_path=self.config.font_file,
                )
            except Exception as e:
                self.ui.append_log("生成图片失败: " + str(e))
                return None

        # 同时有图像和文本的情况
        else:
            self.ui.append_log("同时处理文本和图片内容")
            self.ui.append_log("文本内容: " + text)
            self.get_ratio(x1, y1, x2, y2)
            try:
                # 根据图像方向决定排布方式
                if self.is_vertical_image(image):
                    self.ui.append_log("使用左右排布（竖图）")
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
                        image_source=self.last_used_image_file,
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
                        image_overlay=self.config.base_overlay_file if self.config.use_base_overlay else None,
                        top_left=(right_region_left, y1),
                        bottom_right=(x2, y2),
                        text=text,
                        color=(0, 0, 0),
                        max_font_height=64,
                        font_path=self.config.font_file,
                    )
                else:
                    self.ui.append_log("使用上下排布（横图）")
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
                        image_source=self.last_used_image_file,
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
                        image_overlay=self.config.base_overlay_file if self.config.use_base_overlay else None,
                        top_left=(x1, text_region_top),
                        bottom_right=(x2, text_region_bottom),
                        text=text,
                        color=(0, 0, 0),
                        max_font_height=64,
                        font_path=self.config.font_file,
                    )
                
                return final_bytes
                
            except Exception as e:
                self.ui.append_log("生成图片失败: " + str(e))
                return None

    def generate_image(self):
        """
        生成图像的主函数
        """
        # 保存上次使用差分
        last_used_image_file_backup = self.last_used_image_file

        # 检查是否设置了允许的进程列表，如果设置了，则检查当前进程是否在允许列表中
        if self.config.allowed_processes:
            current_process = self.get_foreground_window_process_name()
            if current_process is None or current_process not in [
                p.lower() for p in self.config.allowed_processes
            ]:
                self.ui.append_log(f"当前进程 {current_process} 不在允许列表中，跳过执行")
                # 如果不是在允许的进程中，直接发送原始热键
                if not self.config.block_hotkey:
                    keyboard.send(self.config.hotkey)
                return

        # `cut_all_and_get_text` 会清空剪切板，所以 `try_get_image` 要在前面调用
        user_pasted_image = self.try_get_image()
        user_input, old_clipboard_content = self.cut_all_and_get_text()
        self.ui.append_log(f"用户粘贴图片: {user_pasted_image is not None}")
        self.ui.append_log(f"用户输入的文本内容: {user_input}")
        self.ui.append_log(f"历史剪贴板内容: {old_clipboard_content}")

        if user_input == "" and user_pasted_image is None:
            self.ui.append_log("未检测到文本或图片输入，取消生成")
            return

        self.ui.append_log("开始尝试生成图片...")

        # 查找发送内容是否包含更换差分指令 #差分名#, 如果有则更换差分并移除关键字
        for keyword, img_file in self.config.baseimage_mapping.items():
            if keyword not in user_input:
                continue
            self.last_used_image_file = img_file
            user_input = user_input.replace(keyword, "").strip()
            self.ui.append_log(f"检测到关键词 '{keyword}'，使用底图: {self.last_used_image_file}")
            break

        png_bytes = self.process_text_and_image(user_input, user_pasted_image)

        if png_bytes is None:
            self.ui.append_log("生成图片失败！未生成 PNG 字节。")
            return

        self.copy_png_bytes_to_clipboard(png_bytes)

        if self.config.auto_paste_image:
            keyboard.send(self.config.paste_hotkey)

            time.sleep(self.config.delay)

            if self.config.auto_send_image:
                keyboard.send(self.config.send_hotkey)

        # 恢复原始剪贴板内容
        pyperclip.copy(old_clipboard_content)

        self.ui.append_log("成功地生成并发送图片！")

    def get_ratio(self, x1, y1, x2, y2):
        try:
            self.ratio = (x2 - x1) / (y2 - y1)
            self.ui.append_log("比例: " + str(self.ratio))
        except Exception as e:
            self.ui.append_log("计算比例时出错: " + str(e))

    def run(self):
        """运行应用程序"""
        try:
            # 启动键盘监听线程
            keyboard.start_recording()
            
            # 运行UI主循环
            self.ui.root.mainloop()
            
        except KeyboardInterrupt:
            self.ui.append_log("收到键盘中断信号，正在退出...")
            self.stop()
        except Exception as e:
            self.ui.append_log(f"运行时发生错误: {str(e)}")
            logging.exception(e)
            
    def stop(self):
        """停止应用程序"""
        self.running = False
        keyboard.unhook_all()
        self.ui.append_log("应用程序已停止")


def main():
    try:
        app = AnanSketchbookApp()
        app.run()
    except Exception as e:
        logging.exception(f"启动应用时发生错误: {e}")
        print(f"启动应用时发生错误: {e}")


if __name__ == "__main__":
    main()