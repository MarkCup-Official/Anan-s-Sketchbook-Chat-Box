import customtkinter as ctk
from tkinter import messagebox, scrolledtext
import threading
import logging
import ctypes
from typing import TYPE_CHECKING
import os
import sys
from PIL import Image, ImageDraw, ImageFont

# 尝试导入pystray，如果不存在则稍后处理
try:
    from pystray import Icon as TrayIcon, MenuItem as TrayMenuItem
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

if TYPE_CHECKING:
    from main import AnanSketchbookApp

class AnanSketchbookUI:
    def __init__(self, app: 'AnanSketchbookApp'):
        self.app = app
        
        # 启用高DPI支持
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 设置高DPI感知
        except:
            pass
            
        ctk.set_appearance_mode("System")  # 跟随系统主题
        ctk.set_default_color_theme("blue")  # 使用蓝色主题
        
        self.root = ctk.CTk()
        self.root.title("安安的素描本聊天框")
        self.root.geometry("650x500")
        self.root.minsize(500, 400)  # 设置最小尺寸
        self.root.resizable(True, True)  # 允许调整窗口大小
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 设置窗口图标
        self.setup_window_icon()
        
        # 在创建窗口之后初始化字体
        self.init_fonts()
        
        # 创建日志处理器
        self.log_handler = UITextHandler(self)
        self.log_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        
        # 设置UI元素
        self.setup_ui()
        
        # 最小化状态
        self.is_minimized = False
        
    def setup_window_icon(self):
        """设置窗口图标"""
        try:
            # 使用预先准备的图标文件
            if os.path.exists("icon.ico"):
                # 优先使用ICO文件作为窗口图标
                self.root.iconbitmap("icon.ico")
            elif os.path.exists("icon.png"):
                # 如果没有ICO文件，则使用PNG文件
                import tkinter as tk
                tk_image = tk.PhotoImage(file="icon.png")
                self.root.iconphoto(False, tk_image)
        except Exception as e:
            print(f"设置窗口图标失败: {e}")
        
    def init_fonts(self):
        """初始化字体，在窗口创建后调用"""
        # 从配置中获取UI设置
        ui_settings = self.app.config.ui_settings
        # 设置更清晰的字体
        self.custom_font = ctk.CTkFont(family=ui_settings.font_family, size=ui_settings.font_size)
        self.title_font = ctk.CTkFont(family=ui_settings.font_family, size=ui_settings.title_font_size, weight="bold")
        self.header_font = ctk.CTkFont(family=ui_settings.font_family, size=ui_settings.font_size + 1, weight="bold")
        
    def setup_ui(self):
        # 创建顶部标题栏
        self.create_header()
        
        # 创建notebook用于分隔配置和日志
        self.notebook = ctk.CTkTabview(self.root, segmented_button_selected_color=("#50a5f5", "#2a75b0"))
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # 添加标签页
        self.config_tab = self.notebook.add("配置")
        self.log_tab = self.notebook.add("日志")
        
        # 配置界面元素
        self.setup_config_ui()
        
        # 日志界面元素
        self.setup_log_ui()
        
        # 创建底部状态栏
        self.create_status_bar()
        
    def create_header(self):
        """创建顶部标题栏"""
        header_frame = ctk.CTkFrame(self.root, height=60, corner_radius=0, fg_color=("#3090f0", "#2070c0"))
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="安安的素描本聊天框", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        )
        title_label.pack(side="left", padx=20, pady=10)
        
        # 添加版本信息
        version_label = ctk.CTkLabel(
            header_frame,
            text="v1.0",
            font=ctk.CTkFont(size=12),
            text_color="white"
        )
        version_label.pack(side="right", padx=20, pady=10)
        
    def setup_config_ui(self):
        # 创建滚动框架以适应高DPI下的内容
        config_canvas = ctk.CTkScrollableFrame(self.config_tab, corner_radius=10)
        config_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 添加欢迎信息
        welcome_frame = ctk.CTkFrame(config_canvas, corner_radius=10, fg_color=("#e6f2ff", "#1a2c47"))
        welcome_frame.pack(fill="x", padx=5, pady=5)
        
        welcome_label = ctk.CTkLabel(
            welcome_frame,
            text="欢迎使用安安的素描本聊天框！\n在这里配置您的个性化设置",
            font=self.header_font,
            wraplength=500,
            justify="center",
            text_color=("#1a3d70", "#c0ddf5")
        )
        welcome_label.pack(pady=15)
        
        # 主配置框架
        main_config_frame = ctk.CTkFrame(config_canvas, corner_radius=10)
        main_config_frame.pack(fill="x", padx=5, pady=10)
        
        ctk.CTkLabel(main_config_frame, text="基础设置", font=self.header_font, text_color=("#205090", "#60a0f0")).pack(pady=(15, 10))
        
        # 热键配置
        hotkey_frame = ctk.CTkFrame(main_config_frame, corner_radius=8)
        hotkey_frame.pack(fill="x", pady=5, padx=20)
        ctk.CTkLabel(hotkey_frame, text="全局热键:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.hotkey_var = ctk.StringVar(value=self.app.config.hotkey)
        hotkey_entry = ctk.CTkEntry(hotkey_frame, textvariable=self.hotkey_var, width=200, font=self.custom_font)
        hotkey_entry.pack(side="right", padx=10, pady=10)
        
        # 延迟配置
        delay_frame = ctk.CTkFrame(main_config_frame, corner_radius=8)
        delay_frame.pack(fill="x", pady=5, padx=20)
        ctk.CTkLabel(delay_frame, text="操作延迟(秒):", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.delay_var = ctk.DoubleVar(value=self.app.config.delay)
        delay_entry = ctk.CTkEntry(delay_frame, textvariable=self.delay_var, width=200, font=self.custom_font)
        delay_entry.pack(side="right", padx=10, pady=10)
        
        # 坐标配置框架
        coord_frame = ctk.CTkFrame(config_canvas, corner_radius=10)
        coord_frame.pack(fill="x", padx=5, pady=10)
        
        ctk.CTkLabel(coord_frame, text="坐标设置", font=self.header_font, text_color=("#205090", "#60a0f0")).pack(pady=(15, 10))
        
        # 文本框坐标说明
        text_coord_desc = ctk.CTkLabel(
            coord_frame, 
            text="设置文本在素描本上的显示区域", 
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        text_coord_desc.pack(pady=(0, 10))
        
        # 左上角坐标
        topleft_frame = ctk.CTkFrame(coord_frame, corner_radius=8)
        topleft_frame.pack(fill="x", pady=5, padx=20)
        ctk.CTkLabel(topleft_frame, text="左上角坐标(X,Y):", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.topleft_x_var = ctk.IntVar(value=self.app.config.text_box_topleft[0])
        self.topleft_y_var = ctk.IntVar(value=self.app.config.text_box_topleft[1])
        topleft_x_entry = ctk.CTkEntry(topleft_frame, textvariable=self.topleft_x_var, width=100, font=self.custom_font)
        topleft_x_entry.pack(side="right", padx=(0, 10), pady=10)
        topleft_y_entry = ctk.CTkEntry(topleft_frame, textvariable=self.topleft_y_var, width=100, font=self.custom_font)
        topleft_y_entry.pack(side="right", padx=(0, 10), pady=10)
        
        # 右下角坐标
        bottomright_frame = ctk.CTkFrame(coord_frame, corner_radius=8)
        bottomright_frame.pack(fill="x", pady=5, padx=20)
        ctk.CTkLabel(bottomright_frame, text="右下角坐标(X,Y):", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.bottomright_x_var = ctk.IntVar(value=self.app.config.image_box_bottomright[0])
        self.bottomright_y_var = ctk.IntVar(value=self.app.config.image_box_bottomright[1])
        bottomright_x_entry = ctk.CTkEntry(bottomright_frame, textvariable=self.bottomright_x_var, width=100, font=self.custom_font)
        bottomright_x_entry.pack(side="right", padx=(0, 10), pady=10)
        bottomright_y_entry = ctk.CTkEntry(bottomright_frame, textvariable=self.bottomright_y_var, width=100, font=self.custom_font)
        bottomright_y_entry.pack(side="right", padx=(0, 10), pady=10)
        
        # 功能开关框架
        switches_frame = ctk.CTkFrame(config_canvas, corner_radius=10)
        switches_frame.pack(fill="x", padx=5, pady=10)
        
        ctk.CTkLabel(switches_frame, text="功能开关", font=self.header_font, text_color=("#205090", "#60a0f0")).pack(pady=(15, 10))
        
        # 自动粘贴开关
        self.auto_paste_var = ctk.BooleanVar(value=self.app.config.auto_paste_image)
        auto_paste_switch = ctk.CTkSwitch(
            switches_frame, 
            text="自动粘贴图片", 
            variable=self.auto_paste_var,
            font=self.custom_font,
            onvalue=True,
            offvalue=False,
            progress_color=("#3090f0", "#50a5f5")
        )
        auto_paste_switch.pack(anchor="w", pady=5, padx=20)
        
        # 自动发送开关
        self.auto_send_var = ctk.BooleanVar(value=self.app.config.auto_send_image)
        auto_send_switch = ctk.CTkSwitch(
            switches_frame, 
            text="自动发送图片", 
            variable=self.auto_send_var,
            font=self.custom_font,
            onvalue=True,
            offvalue=False,
            progress_color=("#3090f0", "#50a5f5")
        )
        auto_send_switch.pack(anchor="w", pady=5, padx=20)
        
        # 阻塞热键开关
        self.block_hotkey_var = ctk.BooleanVar(value=self.app.config.block_hotkey)
        block_hotkey_switch = ctk.CTkSwitch(
            switches_frame, 
            text="阻塞热键", 
            variable=self.block_hotkey_var,
            font=self.custom_font,
            onvalue=True,
            offvalue=False,
            progress_color=("#3090f0", "#50a5f5")
        )
        block_hotkey_switch.pack(anchor="w", pady=5, padx=20)
        
        # 控制按钮框架
        button_frame = ctk.CTkFrame(config_canvas, corner_radius=10)
        button_frame.pack(fill="x", padx=5, pady=(15, 10))
        
        ctk.CTkButton(
            button_frame, 
            text="保存配置", 
            command=self.save_config, 
            font=self.custom_font,
            corner_radius=8,
            height=35,
            fg_color=("#3090f0", "#2070c0"),
            hover_color=("#2070c0", "#105090")
        ).pack(side="left", padx=(20, 10), pady=15)
        
        ctk.CTkButton(
            button_frame, 
            text="应用配置", 
            command=self.apply_config, 
            font=self.custom_font,
            corner_radius=8,
            height=35,
            fg_color=("#3090f0", "#2070c0"),
            hover_color=("#2070c0", "#105090")
        ).pack(side="left", padx=10, pady=15)
        
        ctk.CTkButton(
            button_frame, 
            text="高级配置", 
            command=self.open_advanced_config, 
            font=self.custom_font,
            corner_radius=8,
            height=35,
            fg_color=("#3090f0", "#2070c0"),
            hover_color=("#2070c0", "#105090")
        ).pack(side="left", padx=10, pady=15)
        
        ctk.CTkButton(
            button_frame, 
            text="折叠到托盘", 
            command=self.minimize, 
            font=self.custom_font,
            corner_radius=8,
            height=35,
            fg_color=("#60a0f0", "#3070c0"),
            hover_color=("#5090e0", "#2060a0")
        ).pack(side="right", padx=(10, 20), pady=15)
        
    def open_advanced_config(self):
        """打开高级配置窗口"""
        # 创建高级配置窗口
        self.advanced_window = ctk.CTkToplevel(self.root)
        self.advanced_window.title("高级配置")
        self.advanced_window.geometry("600x500")
        self.advanced_window.resizable(True, True)
        self.advanced_window.transient(self.root)  # 设置为父窗口的临时窗口
        self.advanced_window.grab_set()  # 模态窗口
        
        # 居中显示
        self.center_window(self.advanced_window, 600, 500)
        
        # 创建标签页控件
        advanced_notebook = ctk.CTkTabview(self.advanced_window)
        advanced_notebook.pack(fill="both", expand=True, padx=15, pady=15)
        
        # 添加各个配置标签页
        general_tab = advanced_notebook.add("通用设置")
        shortcuts_tab = advanced_notebook.add("快捷键设置")
        process_tab = advanced_notebook.add("进程设置")
        emotions_tab = advanced_notebook.add("表情设置")
        ui_tab = advanced_notebook.add("界面设置")
        
        # 设置各个配置标签页
        self.setup_general_advanced_config(general_tab)
        self.setup_shortcuts_advanced_config(shortcuts_tab)
        self.setup_process_advanced_config(process_tab)
        self.setup_emotions_advanced_config(emotions_tab)
        self.setup_ui_advanced_config(ui_tab)
        
        # 创建按钮框架
        button_frame = ctk.CTkFrame(self.advanced_window, corner_radius=10)
        button_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        # 添加按钮
        ctk.CTkButton(
            button_frame,
            text="保存并关闭",
            command=self.save_advanced_config_and_close,
            font=self.custom_font,
            corner_radius=8,
            height=35,
            fg_color=("#3090f0", "#2070c0"),
            hover_color=("#2070c0", "#105090")
        ).pack(side="left", padx=10, pady=15)
        
        ctk.CTkButton(
            button_frame,
            text="应用配置",
            command=self.apply_advanced_config,
            font=self.custom_font,
            corner_radius=8,
            height=35,
            fg_color=("#3090f0", "#2070c0"),
            hover_color=("#2070c0", "#105090")
        ).pack(side="left", padx=10, pady=15)
        
        ctk.CTkButton(
            button_frame,
            text="取消",
            command=self.advanced_window.destroy,
            font=self.custom_font,
            corner_radius=8,
            height=35,
            fg_color="transparent",
            border_width=2,
            border_color=("#60a0f0", "#3070c0"),
            hover_color=("#e6f2ff", "#1a2c47"),
            text_color=("#205090", "#c0ddf5")
        ).pack(side="right", padx=10, pady=15)
        
    def center_window(self, window, width, height):
        """居中显示窗口"""
        # 获取屏幕尺寸
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        
        # 设置窗口位置和大小
        window.geometry(f'{width}x{height}+{x}+{y}')
        
    def setup_general_advanced_config(self, parent):
        """设置通用配置"""
        # 创建滚动框架
        scrollable_frame = ctk.CTkScrollableFrame(parent, corner_radius=10)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 字体文件配置
        font_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        font_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(font_frame, text="字体文件:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_font_file_var = ctk.StringVar(value=self.app.config.font_file)
        font_entry = ctk.CTkEntry(font_frame, textvariable=self.adv_font_file_var, width=300, font=self.custom_font)
        font_entry.pack(side="right", padx=10, pady=10)
        
        # 底图文件配置
        baseimage_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        baseimage_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(baseimage_frame, text="默认底图文件:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_baseimage_file_var = ctk.StringVar(value=self.app.config.baseimage_file)
        baseimage_entry = ctk.CTkEntry(baseimage_frame, textvariable=self.adv_baseimage_file_var, width=300, font=self.custom_font)
        baseimage_entry.pack(side="right", padx=10, pady=10)
        
        # 置顶图层文件配置
        overlay_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        overlay_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(overlay_frame, text="置顶图层文件:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_base_overlay_file_var = ctk.StringVar(value=self.app.config.base_overlay_file)
        overlay_entry = ctk.CTkEntry(overlay_frame, textvariable=self.adv_base_overlay_file_var, width=300, font=self.custom_font)
        overlay_entry.pack(side="right", padx=10, pady=10)
        
        # 日志等级配置
        log_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        log_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(log_frame, text="日志等级:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_logging_level_var = ctk.StringVar(value=self.app.config.logging_level)
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        log_option = ctk.CTkOptionMenu(log_frame, values=log_levels, variable=self.adv_logging_level_var, font=self.custom_font,
                                       fg_color=("#e6f2ff", "#1a2c47"), button_color=("#3090f0", "#2070c0"),
                                       button_hover_color=("#2070c0", "#105090"), text_color=("#1a3d70", "#c0ddf5"))
        log_option.pack(side="right", padx=10, pady=10)
        
        # 使用置顶图层开关
        overlay_switch_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        overlay_switch_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(overlay_switch_frame, text="使用置顶图层:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_use_base_overlay_var = ctk.BooleanVar(value=self.app.config.use_base_overlay)
        overlay_switch = ctk.CTkSwitch(
            overlay_switch_frame,
            text="",
            variable=self.adv_use_base_overlay_var,
            onvalue=True,
            offvalue=False,
            progress_color=("#3090f0", "#50a5f5")
        )
        overlay_switch.pack(side="right", padx=10, pady=10)
        
    def setup_shortcuts_advanced_config(self, parent):
        """设置快捷键配置"""
        # 创建滚动框架
        scrollable_frame = ctk.CTkScrollableFrame(parent, corner_radius=10)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 全选快捷键配置
        select_all_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        select_all_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(select_all_frame, text="全选快捷键:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_select_all_hotkey_var = ctk.StringVar(value=self.app.config.select_all_hotkey)
        select_all_entry = ctk.CTkEntry(select_all_frame, textvariable=self.adv_select_all_hotkey_var, width=200, font=self.custom_font)
        select_all_entry.pack(side="right", padx=10, pady=10)
        
        # 剪切快捷键配置
        cut_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        cut_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(cut_frame, text="剪切快捷键:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_cut_hotkey_var = ctk.StringVar(value=self.app.config.cut_hotkey)
        cut_entry = ctk.CTkEntry(cut_frame, textvariable=self.adv_cut_hotkey_var, width=200, font=self.custom_font)
        cut_entry.pack(side="right", padx=10, pady=10)
        
        # 黏贴快捷键配置
        paste_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        paste_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(paste_frame, text="黏贴快捷键:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_paste_hotkey_var = ctk.StringVar(value=self.app.config.paste_hotkey)
        paste_entry = ctk.CTkEntry(paste_frame, textvariable=self.adv_paste_hotkey_var, width=200, font=self.custom_font)
        paste_entry.pack(side="right", padx=10, pady=10)
        
        # 发送快捷键配置
        send_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        send_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(send_frame, text="发送快捷键:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_send_hotkey_var = ctk.StringVar(value=self.app.config.send_hotkey)
        send_entry = ctk.CTkEntry(send_frame, textvariable=self.adv_send_hotkey_var, width=200, font=self.custom_font)
        send_entry.pack(side="right", padx=10, pady=10)
        
    def setup_process_advanced_config(self, parent):
        """设置进程配置"""
        frame = ctk.CTkFrame(parent, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(frame, text="允许运行此程序的进程列表", font=self.header_font, text_color=("#205090", "#60a0f0")).pack(pady=10)
        ctk.CTkLabel(frame, text="每行输入一个进程名称，例如: qq.exe", font=("Microsoft YaHei", 10)).pack()
        
        # 创建文本框用于输入进程列表
        self.adv_allowed_processes_text = ctk.CTkTextbox(frame, font=("Microsoft YaHei", 10), height=200,
                                                         fg_color=("#e6f2ff", "#1a2c47"), text_color=("#1a3d70", "#c0ddf5"))
        self.adv_allowed_processes_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 填充当前配置
        processes_text = "\n".join(self.app.config.allowed_processes)
        self.adv_allowed_processes_text.insert("0.0", processes_text)
        
    def setup_emotions_advanced_config(self, parent):
        """设置表情配置"""
        # 创建滚动框架
        scrollable_frame = ctk.CTkScrollableFrame(parent, corner_radius=10)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(scrollable_frame, text="表情切换快捷键映射", font=self.header_font, text_color=("#205090", "#60a0f0")).pack(pady=10)
        ctk.CTkLabel(scrollable_frame, text="格式: 快捷键=表情标签，每行一个", font=("Microsoft YaHei", 10)).pack()
        
        # 创建文本框用于输入表情映射
        self.adv_emotion_switch_text = ctk.CTkTextbox(scrollable_frame, font=("Microsoft YaHei", 10), height=300,
                                                      fg_color=("#e6f2ff", "#1a2c47"), text_color=("#1a3d70", "#c0ddf5"))
        self.adv_emotion_switch_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 填充当前配置
        emotion_lines = []
        for hotkey, emotion in self.app.config.emotion_switch_hotkeys.items():
            emotion_lines.append(f"{hotkey}={emotion}")
        emotion_text = "\n".join(emotion_lines)
        self.adv_emotion_switch_text.insert("0.0", emotion_text)
        
    def setup_ui_advanced_config(self, parent):
        """设置界面配置"""
        # 创建滚动框架
        scrollable_frame = ctk.CTkScrollableFrame(parent, corner_radius=10)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 字体家族配置
        font_family_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        font_family_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(font_family_frame, text="字体家族:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_ui_font_family_var = ctk.StringVar(value=self.app.config.ui_settings.font_family)
        font_family_entry = ctk.CTkEntry(font_family_frame, textvariable=self.adv_ui_font_family_var, width=200, font=self.custom_font)
        font_family_entry.pack(side="right", padx=10, pady=10)
        
        # 字体大小配置
        font_size_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        font_size_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(font_size_frame, text="字体大小:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_ui_font_size_var = ctk.IntVar(value=self.app.config.ui_settings.font_size)
        font_size_entry = ctk.CTkEntry(font_size_frame, textvariable=self.adv_ui_font_size_var, width=200, font=self.custom_font)
        font_size_entry.pack(side="right", padx=10, pady=10)
        
        # 标题字体大小配置
        title_font_size_frame = ctk.CTkFrame(scrollable_frame, corner_radius=8)
        title_font_size_frame.pack(fill="x", pady=5, padx=5)
        ctk.CTkLabel(title_font_size_frame, text="标题字体大小:", font=self.custom_font).pack(side="left", padx=10, pady=10)
        self.adv_ui_title_font_size_var = ctk.IntVar(value=self.app.config.ui_settings.title_font_size)
        title_font_size_entry = ctk.CTkEntry(title_font_size_frame, textvariable=self.adv_ui_title_font_size_var, width=200, font=self.custom_font)
        title_font_size_entry.pack(side="right", padx=10, pady=10)
        
    def save_advanced_config_and_close(self):
        """保存高级配置并关闭窗口"""
        self.apply_advanced_config()
        self.advanced_window.destroy()
        
    def apply_advanced_config(self):
        """应用高级配置"""
        try:
            # 更新通用配置
            self.app.config.font_file = self.adv_font_file_var.get()
            self.app.config.baseimage_file = self.adv_baseimage_file_var.get()
            self.app.config.base_overlay_file = self.adv_base_overlay_file_var.get()
            self.app.config.logging_level = self.adv_logging_level_var.get()
            self.app.config.use_base_overlay = self.adv_use_base_overlay_var.get()
            
            # 更新快捷键配置
            self.app.config.select_all_hotkey = self.adv_select_all_hotkey_var.get()
            self.app.config.cut_hotkey = self.adv_cut_hotkey_var.get()
            self.app.config.paste_hotkey = self.adv_paste_hotkey_var.get()
            self.app.config.send_hotkey = self.adv_send_hotkey_var.get()
            
            # 更新进程配置
            processes_text = self.adv_allowed_processes_text.get("0.0", "end").strip()
            self.app.config.allowed_processes = [p.strip() for p in processes_text.split("\n") if p.strip()]
            
            # 更新表情配置
            emotion_text = self.adv_emotion_switch_text.get("0.0", "end").strip()
            emotion_dict = {}
            for line in emotion_text.split("\n"):
                if "=" in line:
                    hotkey, emotion = line.split("=", 1)
                    emotion_dict[hotkey.strip()] = emotion.strip()
            self.app.config.emotion_switch_hotkeys = emotion_dict
            
            # 更新界面配置
            self.app.config.ui_settings.font_family = self.adv_ui_font_family_var.get()
            self.app.config.ui_settings.font_size = self.adv_ui_font_size_var.get()
            self.app.config.ui_settings.title_font_size = self.adv_ui_title_font_size_var.get()
            
            # 显示成功消息
            messagebox.showinfo("成功", "高级配置已应用")
            
        except Exception as e:
            messagebox.showerror("错误", f"应用配置时出错: {str(e)}")
        
    def setup_log_ui(self):
        # 日志显示区域
        log_text_frame = ctk.CTkFrame(self.log_tab, corner_radius=10)
        log_text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 添加日志标题
        log_header_frame = ctk.CTkFrame(log_text_frame, corner_radius=8, fg_color=("#e6f2ff", "#1a2c47"))
        log_header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(log_header_frame, text="运行日志", font=self.header_font, text_color=("#205090", "#60a0f0")).pack(side="left", padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(
            log_text_frame, 
            state='disabled', 
            wrap='word',
            height=10,
            bg="#202020" if ctk.get_appearance_mode() == "Dark" else "#ffffff",
            fg="#ffffff" if ctk.get_appearance_mode() == "Dark" else "#000000",
            font=(self.app.config.ui_settings.font_family, 9)
        )
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # 日志控制按钮
        log_control_frame = ctk.CTkFrame(self.log_tab, corner_radius=10)
        log_control_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            log_control_frame, 
            text="清空日志", 
            command=self.clear_log, 
            font=self.custom_font,
            corner_radius=8,
            height=35,
            fg_color=("#3090f0", "#2070c0"),
            hover_color=("#2070c0", "#105090")
        ).pack(side="left", padx=(20, 10), pady=15)
        
        ctk.CTkButton(
            log_control_frame, 
            text="折叠到托盘", 
            command=self.minimize, 
            font=self.custom_font,
            corner_radius=8,
            height=35,
            fg_color=("#60a0f0", "#3070c0"),
            hover_color=("#5090e0", "#2060a0")
        ).pack(side="right", padx=(10, 20), pady=15)
        
    def create_status_bar(self):
        """创建底部状态栏"""
        self.status_frame = ctk.CTkFrame(self.root, height=30, corner_radius=0, fg_color=("#e6f2ff", "#1a2c47"))
        self.status_frame.pack(fill="x", side="bottom", padx=0, pady=0)
        self.status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame, 
            text="就绪", 
            font=ctk.CTkFont(size=12),
            text_color=("#1a3d70", "#c0ddf5")
        )
        self.status_label.pack(side="left", padx=15, pady=5)
        
        # 显示当前热键
        hotkey_info = ctk.CTkLabel(
            self.status_frame,
            text=f"热键: {self.app.config.hotkey}",
            font=ctk.CTkFont(size=12),
            text_color=("#1a3d70", "#c0ddf5")
        )
        hotkey_info.pack(side="right", padx=15, pady=5)
        
    def update_status(self, message: str):
        """更新状态栏信息"""
        self.status_label.configure(text=message)
        self.root.update_idletasks()
        
    def save_config(self):
        """保存配置到文件"""
        try:
            # TODO: 实现配置保存到文件
            messagebox.showinfo("提示", "配置保存功能将在后续实现")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置时发生错误: {str(e)}")
            
    def apply_config(self):
        """应用配置到运行时"""
        try:
            self.update_status("正在应用配置...")
            
            # 更新应用配置
            self.app.config.hotkey = self.hotkey_var.get()
            self.app.config.delay = self.delay_var.get()
            self.app.config.text_box_topleft = (self.topleft_x_var.get(), self.topleft_y_var.get())
            self.app.config.image_box_bottomright = (self.bottomright_x_var.get(), self.bottomright_y_var.get())
            self.app.config.auto_paste_image = self.auto_paste_var.get()
            self.app.config.auto_send_image = self.auto_send_var.get()
            self.app.config.block_hotkey = self.block_hotkey_var.get()
            
            # 重新注册热键
            self.app.rebind_hotkey()
            
            # 更新状态栏
            self.update_status("配置已应用")
            
            messagebox.showinfo("提示", "配置已应用")
        except Exception as e:
            self.update_status("配置应用失败")
            messagebox.showerror("错误", f"应用配置时发生错误: {str(e)}")
            
    def minimize(self):
        """最小化窗口到系统托盘"""
        self.update_status("正在最小化到系统托盘...")
        self.is_minimized = True
        # 隐藏主窗口
        self.root.withdraw()
        
        # 如果pystray可用，则创建系统托盘图标
        if PYSTRAY_AVAILABLE:
            self.create_tray_icon()
        else:
            # 如果pystray不可用，则使用标准的窗口最小化方法
            self.root.iconify()
            self.update_status("已最小化到任务栏")

    def create_tray_icon(self):
        """创建系统托盘图标"""
        # 创建托盘图标菜单
        menu = (
            TrayMenuItem('显示', self.restore),
            TrayMenuItem('退出', self.confirm_exit_from_tray),
        )
        
        # 尝试加载图标，如果没有则使用默认图标
        icon_image = self.create_default_icon()
        
        # 创建并运行托盘图标
        self.tray_icon = TrayIcon(
            "安安的素描本聊天框",
            icon_image,
            "安安的素描本聊天框",
            menu
        )
        
        # 添加双击事件处理
        def on_tray_icon_click(icon, query):
            if query == TrayIcon.DoubleClick:
                self.restore()
        
        self.tray_icon.on_click = on_tray_icon_click
        
        # 在单独的线程中运行托盘图标
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()
        self.update_status("已最小化到系统托盘")

    def create_default_icon(self):
        """创建默认的托盘图标"""
        # 尝试加载预先准备的图标文件
        try:
            if os.path.exists("icon.png"):
                icon = Image.open("icon.png")
                # 调整图标大小为托盘图标标准尺寸
                icon = icon.resize((64, 64), Image.Resampling.LANCZOS)
                return icon
            else:
                # 如果没有图标文件，则创建一个默认图标
                return self.generate_default_icon()
        except Exception as e:
            print(f"加载托盘图标失败: {e}")
            # 出现异常时也创建默认图标
            return self.generate_default_icon()
    
    def generate_default_icon(self):
        """生成默认的托盘图标"""
        # 创建一个64x64的图标
        icon = Image.new('RGBA', (64, 64), (70, 130, 180, 255))  # Steel blue color
        
        # 创建绘图对象
        draw = ImageDraw.Draw(icon)
        
        # 绘制一个简单的笔记本图标
        # 笔记本封面
        draw.rectangle([10, 5, 54, 59], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=2)
        
        # 笔记本螺旋装订线
        for i in range(5):
            y = 15 + i * 10
            draw.ellipse([5, y-2, 10, y+2], fill=(169, 169, 169, 255))  # Dark gray spiral
            
        # 在笔记本上绘制一个简单的"P"字符表示"Paper"
        try:
            # 尝试使用默认字体
            font = ImageFont.load_default()
            draw.text((25, 20), "P", fill=(0, 0, 0, 255), font=font)
        except:
            # 如果无法加载字体，就画一个简单的形状
            draw.rectangle([25, 20, 35, 30], fill=(0, 0, 0, 255))
            
        return icon

    def restore(self):
        """恢复窗口"""
        self.is_minimized = False
        
        # 停止托盘图标（如果存在）
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        
        # 恢复主窗口
        self.root.deiconify()
        self.root.lift()
        self.update_status("就绪")

    def confirm_exit_from_tray(self):
        """托盘退出确认"""
        # 停止托盘图标（如果存在）
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
            
        self.app.stop()
        self.root.destroy()

    def on_closing(self):
        """处理窗口关闭事件"""
        # 显示选项对话框
        from tkinter import messagebox
        
        # 创建一个顶层窗口作为对话框的父窗口
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("确认操作")
        dialog.geometry("350x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)  # 设置为瞬态窗口
        dialog.grab_set()  # 模态对话框
        
        # 居中显示对话框
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (350 // 2)
        y = (dialog.winfo_screenheight() // 2) - (180 // 2)
        dialog.geometry(f"350x180+{x}+{y}")
        
        # 对话框内容
        label = ctk.CTkLabel(dialog, text="确定要退出安安的素描本聊天框吗？", font=self.header_font)
        label.pack(pady=20)
        
        desc_label = ctk.CTkLabel(
            dialog, 
            text="选择\"隐藏\"可以最小化到系统托盘继续运行", 
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60")
        )
        desc_label.pack(pady=(0, 10))
        
        # 按钮框架
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)
        
        def hide_window():
            dialog.destroy()
            self.minimize()
            
        def close_app():
            dialog.destroy()
            # 停止托盘图标（如果存在）
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.stop()
                
            self.app.stop()
            self.root.destroy()
            
        def cancel_action():
            dialog.destroy()
            
        # 创建三个按钮
        hide_btn = ctk.CTkButton(
            button_frame, 
            text="隐藏到托盘", 
            command=hide_window,
            fg_color=("#60a0f0", "#3070c0"),
            hover_color=("#5090e0", "#2060a0"),
            width=80
        )
        hide_btn.pack(side="left", padx=5)
        
        close_btn = ctk.CTkButton(
            button_frame, 
            text="退出程序", 
            command=close_app, 
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            width=80
        )
        close_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            button_frame, 
            text="取消", 
            command=cancel_action,
            fg_color=("#3090f0", "#2070c0"),
            hover_color=("#2070c0", "#105090"),
            width=80
        )
        cancel_btn.pack(side="left", padx=5)
        
        # 确保对话框获得焦点
        dialog.focus_force()
        
    def append_log(self, message: str):
        """添加日志消息到UI"""
        self.log_text.config(state='normal')
        self.log_text.insert(ctk.END, message + '\n')
        self.log_text.config(state='disabled')
        self.log_text.see(ctk.END)
        
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, ctk.END)
        self.log_text.config(state='disabled')


class UITextHandler(logging.Handler):
    """自定义日志处理器，将日志输出到UI"""
    
    def __init__(self, ui: AnanSketchbookUI):
        super().__init__()
        self.ui = ui
        
    def emit(self, record):
        msg = self.format(record)
        # 使用线程安全的方式更新UI
        if self.ui.root:
            self.ui.root.after(0, self.ui.append_log, msg)