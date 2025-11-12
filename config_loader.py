import os
import yaml
from typing import Dict, Any, Tuple, List
from pydantic import BaseModel


class UISettings(BaseModel):
    """UI设置模型类"""
    font_family: str = "Microsoft YaHei"
    font_size: int = 10
    title_font_size: int = 12
    window_width: int = 650
    window_height: int = 500
    theme: str = "blue"  # 可选: blue, green, dark-blue


class Config(BaseModel):
    """配置模型类"""
    hotkey: str = "enter"
    """全局热键, 用于 keyboard 库"""
    allowed_processes: List[str] = []
    """允许的进程列表"""
    select_all_hotkey: str = "ctrl+a"
    """全选快捷键"""
    cut_hotkey: str = "ctrl+x"
    """剪切快捷键"""
    paste_hotkey: str = "ctrl+v"
    """黏贴快捷键"""
    send_hotkey: str = "enter"
    """发送消息快捷键"""
    block_hotkey: bool = False
    """阻塞热键"""
    delay: float = 0.1
    """操作延时（秒）"""
    font_file: str = "font.ttf"
    """字体文件路径"""
    baseimage_mapping: Dict[str, str] = {
        "#普通#": "BaseImages\\base.png"
    }
    """差分表情映射字典"""
    baseimage_file: str = "BaseImages\\base.png"
    """默认底图文件路径"""
    text_box_topleft: Tuple[int, int] = (119, 450)
    """文本框左上角坐标"""
    image_box_bottomright: Tuple[int, int] = (398, 625)
    """文本框右下角坐标"""
    base_overlay_file: str = "BaseImages\\base_overlay.png"
    """底图置顶图层文件路径"""
    use_base_overlay: bool = True
    """是否使用底图置顶图层"""
    auto_paste_image: bool = True
    """是否自动黏贴图片"""
    auto_send_image: bool = True
    """是否自动发送图片"""
    logging_level: str = "INFO"
    """日志记录等级"""
    emotion_switch_hotkeys: Dict[str, str] = {
        "alt+1": "#普通#"
    }
    """表情切换快捷键映射"""
    ui_settings: UISettings = UISettings()
    """UI设置"""

    class Config:
        arbitrary_types_allowed = True


def load_config(config_file: str = "config.yaml") -> Config:
    """
    从YAML文件加载配置
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        Config: 配置对象
    """
    # 如果配置文件不存在，使用默认配置
    if not os.path.exists(config_file):
        return Config()
    
    # 读取YAML配置文件
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    # 处理坐标值，确保它们是元组而不是列表
    if 'text_box_topleft' in config_data and isinstance(config_data['text_box_topleft'], list):
        config_data['text_box_topleft'] = tuple(config_data['text_box_topleft'])
    
    if 'image_box_bottomright' in config_data and isinstance(config_data['image_box_bottomright'], list):
        config_data['image_box_bottomright'] = tuple(config_data['image_box_bottomright'])
    
    # 处理UI设置
    if 'ui_settings' in config_data:
        config_data['ui_settings'] = UISettings(**config_data['ui_settings'])
    
    # 创建并返回配置对象
    return Config(**config_data)