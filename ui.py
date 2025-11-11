import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import AnanSketchbookApp

class AnanSketchbookUI:
    def __init__(self, app: 'AnanSketchbookApp'):
        self.app = app
        self.root = tk.Tk()
        self.root.title("安安的素描本聊天框")
        self.root.geometry("600x400")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 创建日志处理器
        self.log_handler = UITextHandler(self)
        self.log_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        
        # 设置UI元素
        self.setup_ui()
        
        # 最小化状态
        self.is_minimized = False
        
    def setup_ui(self):
        # 创建notebook用于分隔配置和日志
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置页面
        self.config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="配置")
        
        # 日志页面
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="日志")
        
        # 配置界面元素
        self.setup_config_ui()
        
        # 日志界面元素
        self.setup_log_ui()
        
    def setup_config_ui(self):
        # 主配置框架
        main_config_frame = ttk.LabelFrame(self.config_frame, text="主要配置", padding=10)
        main_config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 热键配置
        hotkey_frame = ttk.Frame(main_config_frame)
        hotkey_frame.pack(fill=tk.X, pady=2)
        ttk.Label(hotkey_frame, text="全局热键:").pack(side=tk.LEFT)
        self.hotkey_var = tk.StringVar(value=self.app.config.hotkey)
        ttk.Entry(hotkey_frame, textvariable=self.hotkey_var, width=20).pack(side=tk.RIGHT)
        
        # 延迟配置
        delay_frame = ttk.Frame(main_config_frame)
        delay_frame.pack(fill=tk.X, pady=2)
        ttk.Label(delay_frame, text="操作延迟(秒):").pack(side=tk.LEFT)
        self.delay_var = tk.DoubleVar(value=self.app.config.delay)
        ttk.Entry(delay_frame, textvariable=self.delay_var, width=20).pack(side=tk.RIGHT)
        
        # 文本框坐标配置
        textbox_frame = ttk.LabelFrame(self.config_frame, text="文本框坐标", padding=10)
        textbox_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 左上角坐标
        topleft_frame = ttk.Frame(textbox_frame)
        topleft_frame.pack(fill=tk.X, pady=2)
        ttk.Label(topleft_frame, text="左上角坐标(X,Y):").pack(side=tk.LEFT)
        self.topleft_x_var = tk.IntVar(value=self.app.config.text_box_topleft[0])
        self.topleft_y_var = tk.IntVar(value=self.app.config.text_box_topleft[1])
        ttk.Entry(topleft_frame, textvariable=self.topleft_x_var, width=10).pack(side=tk.RIGHT)
        ttk.Entry(topleft_frame, textvariable=self.topleft_y_var, width=10).pack(side=tk.RIGHT, padx=(0, 5))
        
        # 右下角坐标
        bottomright_frame = ttk.Frame(textbox_frame)
        bottomright_frame.pack(fill=tk.X, pady=2)
        ttk.Label(bottomright_frame, text="右下角坐标(X,Y):").pack(side=tk.LEFT)
        self.bottomright_x_var = tk.IntVar(value=self.app.config.image_box_bottomright[0])
        self.bottomright_y_var = tk.IntVar(value=self.app.config.image_box_bottomright[1])
        ttk.Entry(bottomright_frame, textvariable=self.bottomright_x_var, width=10).pack(side=tk.RIGHT)
        ttk.Entry(bottomright_frame, textvariable=self.bottomright_y_var, width=10).pack(side=tk.RIGHT, padx=(0, 5))
        
        # 功能开关框架
        switches_frame = ttk.LabelFrame(self.config_frame, text="功能开关", padding=10)
        switches_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 自动粘贴开关
        self.auto_paste_var = tk.BooleanVar(value=self.app.config.auto_paste_image)
        auto_paste_check = ttk.Checkbutton(
            switches_frame, 
            text="自动粘贴图片", 
            variable=self.auto_paste_var
        )
        auto_paste_check.pack(anchor=tk.W)
        
        # 自动发送开关
        self.auto_send_var = tk.BooleanVar(value=self.app.config.auto_send_image)
        auto_send_check = ttk.Checkbutton(
            switches_frame, 
            text="自动发送图片", 
            variable=self.auto_send_var
        )
        auto_send_check.pack(anchor=tk.W)
        
        # 阻塞热键开关
        self.block_hotkey_var = tk.BooleanVar(value=self.app.config.block_hotkey)
        block_hotkey_check = ttk.Checkbutton(
            switches_frame, 
            text="阻塞热键", 
            variable=self.block_hotkey_var
        )
        block_hotkey_check.pack(anchor=tk.W)
        
        # 控制按钮框架
        button_frame = ttk.Frame(self.config_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(button_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="应用配置", command=self.apply_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="折叠", command=self.minimize).pack(side=tk.RIGHT)
        
    def setup_log_ui(self):
        # 日志显示区域
        log_text_frame = ttk.Frame(self.log_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_text_frame, 
            state='disabled', 
            wrap='word',
            height=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 日志控制按钮
        log_control_frame = ttk.Frame(self.log_frame)
        log_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(log_control_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT)
        ttk.Button(log_control_frame, text="折叠", command=self.minimize).pack(side=tk.RIGHT)
        
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
            
            messagebox.showinfo("提示", "配置已应用")
        except Exception as e:
            messagebox.showerror("错误", f"应用配置时发生错误: {str(e)}")
            
    def minimize(self):
        """最小化窗口到右下角"""
        self.is_minimized = True
        # 缩小窗口并移动到右下角
        self.root.geometry("200x50+{}+{}".format(
            self.root.winfo_screenwidth() - 210,
            self.root.winfo_screenheight() - 90
        ))
        
        # 移除标题栏和边框，只保留内容区域
        self.root.overrideredirect(True)
        
        # 创建弹出按钮替代标题栏
        self.popup_button = tk.Button(
            self.root, 
            text="安安的素描本", 
            command=self.restore,
            bg="#4a90e2",
            fg="white"
        )
        self.popup_button.pack(fill=tk.BOTH, expand=True)
        
    def restore(self):
        """恢复窗口"""
        self.is_minimized = False
        # 恢复正常窗口
        self.root.geometry("600x400")
        self.root.overrideredirect(False)
        
        # 销毁弹出按钮
        if hasattr(self, 'popup_button'):
            self.popup_button.destroy()
            
        # 重新设置UI
        self.setup_ui()
        
    def on_closing(self):
        """处理窗口关闭事件"""
        if messagebox.askokcancel("退出", "确定要退出安安的素描本聊天框吗？"):
            self.app.stop()
            self.root.destroy()
            
    def append_log(self, message: str):
        """添加日志消息到UI"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)
        
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
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