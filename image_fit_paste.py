# filename: image_fit_paste.py
import logging
import os
from functools import lru_cache
from io import BytesIO
from typing import Literal, Tuple, Union

from PIL import Image

Align = Literal["left", "center", "right"]
VAlign = Literal["top", "middle", "bottom"]

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def _load_image_cached(image_path: str) -> Image.Image:
    """
    缓存加载图像文件，避免重复读取磁盘。
    """
    return Image.open(image_path).convert("RGBA")


def _get_base_image(image_source: Union[str, Image.Image, BytesIO]) -> Image.Image:
    """获取底图，支持路径、Image对象或BytesIO"""
    if isinstance(image_source, Image.Image):
        return image_source.copy()
    elif isinstance(image_source, BytesIO):
        return Image.open(image_source).convert("RGBA")
    else:
        return _load_image_cached(image_source).copy()


def paste_image_auto(
    image_source: Union[str, Image.Image, BytesIO],
    top_left: Tuple[int, int],
    bottom_right: Tuple[int, int],
    content_image: Image.Image,
    align: Align = "center",
    valign: VAlign = "middle",
    padding: int = 0,
    allow_upscale: bool = False,
    keep_alpha: bool = True,
    image_overlay: Union[str, Image.Image, None] = None,
) -> bytes:
    """
    在指定矩形内放置一张图片（content_image），按比例缩放至"最大但不超过"该矩形。

    :param image_source: 底图路径、Image对象或BytesIO
    :param top_left: 指定矩形区域（左上坐标）
    :param bottom_right: 指定矩形区域（右下坐标）
    :param content_image: 待放入的图片（PIL.Image.Image）
    :param align: 水平对齐方式
    :param valign: 垂直对齐方式
    :param padding: 矩形内边距（像素），四边统一
    :param allow_upscale: 是否允许放大（默认只缩小不放大）
    :param keep_alpha: True 时保留透明通道并用其作为粘贴蒙版
    :param image_overlay: 可选的置顶覆盖图

    返回：最终 PNG 的 bytes。
    """
    if not isinstance(content_image, Image.Image):
        raise TypeError("content_image 必须为 PIL.Image.Image")

    img = _get_base_image(image_source)

    # 加载覆盖图（使用缓存）
    img_overlay = None
    if image_overlay is not None:
        if isinstance(image_overlay, Image.Image):
            img_overlay = image_overlay.copy()
        elif os.path.isfile(image_overlay):
            img_overlay = _load_image_cached(image_overlay).copy()

    x1, y1 = top_left
    x2, y2 = bottom_right
    if not (x2 > x1 and y2 > y1):
        raise ValueError("无效的粘贴区域。")

    # 计算可用区域（考虑 padding）
    region_w = max(1, (x2 - x1) - 2 * padding)
    region_h = max(1, (y2 - y1) - 2 * padding)

    cw, ch = content_image.size
    if cw <= 0 or ch <= 0:
        raise ValueError("content_image 尺寸无效。")

    # 计算缩放比例（contain：不超过区域，并保持纵横比）
    scale = min(region_w / cw, region_h / ch)

    if not allow_upscale:
        scale = min(1.0, scale)

    # 至少保证 1x1
    new_w = max(1, int(round(cw * scale)))
    new_h = max(1, int(round(ch * scale)))

    # 选择高质量插值
    resized = content_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 计算粘贴坐标（考虑对齐与 padding）
    if align == "left":
        px = x1 + padding
    elif align == "center":
        px = x1 + padding + (region_w - new_w) // 2
    else:  # "right"
        px = x2 - padding - new_w

    if valign == "top":
        py = y1 + padding
    elif valign == "middle":
        py = y1 + padding + (region_h - new_h) // 2
    else:  # "bottom"
        py = y2 - padding - new_h

    # 处理透明度：若 keep_alpha=True 且有 alpha，则用 alpha 作为 mask 粘贴
    if keep_alpha and ("A" in resized.getbands()):
        img.paste(resized, (px, py), resized)
    else:
        img.paste(resized, (px, py))

    # 覆盖置顶图层（如果有）
    if img_overlay is not None:
        img.paste(img_overlay, (0, 0), img_overlay)
    elif image_overlay is not None:
        logger.warning("Overlay image does not exist: %s", image_overlay)

    # 输出 PNG bytes
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
