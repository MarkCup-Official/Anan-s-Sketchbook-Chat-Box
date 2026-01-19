import logging
import os
import yaml
from typing import Dict, Optional, Tuple, List
from pydantic import BaseModel, field_validator


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
    baseimage_mapping: Dict[str, str] = {"#普通#": "BaseImages\\base.png"}
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
    emotion_switch_hotkeys: Dict[str, str] = {"alt+1": "#普通#"}
    """表情切换快捷键映射"""
    text_wrap_algorithm: str = "original"
    """文本换行算法，可选值："original"(原始算法), "knuth_plass"(改进的Knuth-Plass算法)"""

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("delay")
    @classmethod
    def validate_delay(cls, v: float) -> float:
        """验证延时值在合理范围内"""
        if v < 0:
            return 0.1
        if v > 5.0:
            return 5.0
        return v

    @field_validator("logging_level")
    @classmethod
    def validate_logging_level(cls, v: str) -> str:
        """验证日志等级是否有效"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            return "INFO"
        return v.upper()

    @field_validator("text_wrap_algorithm")
    @classmethod
    def validate_wrap_algorithm(cls, v: str) -> str:
        """验证换行算法是否有效"""
        valid_algorithms = ["original", "knuth_plass"]
        if v.lower() not in valid_algorithms:
            return "original"
        return v.lower()


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
        logging.warning(f"配置文件 {config_file} 不存在，使用默认配置")
        return Config()

    try:
        # 读取YAML配置文件
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # 处理空配置文件的情况
        if config_data is None:
            logging.warning(f"配置文件 {config_file} 为空，使用默认配置")
            return Config()

        # 处理坐标值，确保它们是元组而不是列表
        if "text_box_topleft" in config_data and isinstance(
            config_data["text_box_topleft"], list
        ):
            config_data["text_box_topleft"] = tuple(config_data["text_box_topleft"])

        if "image_box_bottomright" in config_data and isinstance(
            config_data["image_box_bottomright"], list
        ):
            config_data["image_box_bottomright"] = tuple(
                config_data["image_box_bottomright"]
            )

        # 创建并返回配置对象
        return Config(**config_data)
    except yaml.YAMLError as e:
        logging.error(f"解析配置文件失败: {e}")
        return Config()
    except Exception as e:
        logging.error(f"加载配置文件时发生错误: {e}")
        return Config()
