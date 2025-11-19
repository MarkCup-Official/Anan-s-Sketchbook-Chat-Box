# filename: text_fit_draw.py
import os
from io import BytesIO
from typing import List, Literal, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

RGBColor = Tuple[int, int, int]

Align = Literal["left", "center", "right"]
VAlign = Literal["top", "middle", "bottom"]


def _is_emoji(char: str) -> bool:
    """
    检测字符是否为emoji
    只返回True如果字符确实是emoji，其他所有字符（包括中文、英文、标点等）都返回False
    
    规则：
    - emoji字体只负责emoji字符
    - 无论是英语还是中文，只要不是emoji，都用普通字体
    """
    if not char:
        return False
    
    # 获取第一个字符的Unicode码点
    code_point = ord(char[0])
    
    # emoji的Unicode范围（精确范围，不会误判中文和英文）
    emoji_ranges = [
        (0x1F600, 0x1F64F),  # 表情符号 (Emoticons) - 😀-🙏
        (0x1F300, 0x1F5FF),  # 符号和象形文字 (Misc Symbols and Pictographs) - 🌀-🗿
        (0x1F680, 0x1F6FF),  # 交通和地图符号 (Transport and Map) - 🚀-🛿
        (0x1F1E0, 0x1F1FF),  # 旗帜 (Regional Indicators) - 🇠-🇿
        (0x2702, 0x27B0),    # 装饰符号 (Dingbats) - ✂-➰
        (0x1F900, 0x1F9FF),  # 补充符号和象形文字 (Supplemental Symbols and Pictographs) - 🤀-🧿
        (0x1FA00, 0x1FA6F),  # 扩展-A (Symbols Extended-A)
        (0x1FA70, 0x1FAFF),  # 扩展-B (Symbols Extended-B)
        (0x2600, 0x26FF),    # 杂项符号 (Misc Symbols) - ☀-⛿
        (0x2700, 0x27BF),    # 装饰符号 (Dingbats) - ✀-➿
    ]
    
    # 检查主字符是否在emoji范围内
    for start, end in emoji_ranges:
        if start <= code_point <= end:
            return True
    
    # 检查是否是组合emoji（包含零宽连接符的情况，如 👨‍👩‍👧‍👦）
    if '\u200D' in char:  # Zero Width Joiner
        # 检查组合emoji的各个部分是否都是emoji
        parts = [p for p in char.split('\u200D') if p]
        if parts:
            # 检查每个部分是否都是emoji
            for part in parts:
                part_code = ord(part[0]) if part else 0
                is_emoji_part = False
                for start, end in emoji_ranges:
                    if start <= part_code <= end:
                        is_emoji_part = True
                        break
                if not is_emoji_part:
                    return False
            return True
    
    return False


def _load_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    """
    加载指定路径的字体文件，如果失败则加载默认字体。
    """
    if font_path and os.path.exists(font_path):
        return ImageFont.truetype(font_path, size=size)
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except Exception:
        return ImageFont.load_default()  # type: ignore # 如果没有可用的 TTF 字体，则加载默认位图字体


def wrap_lines(
    draw: ImageDraw.ImageDraw, txt: str, font: ImageFont.FreeTypeFont, max_w: int
) -> List[str]:
    """
    将文本按指定宽度拆分为多行。
    """
    lines: List[str] = []

    for para in txt.splitlines() or [""]:
        has_space = " " in para
        units = para.split(" ") if has_space else list(para)
        buf = ""

        def unit_join(a: str, b: str) -> str:
            if not a:
                return b
            return (a + " " + b) if has_space else (a + b)

        for u in units:
            trial = unit_join(buf, u)
            w = draw.textlength(trial, font=font)

            # 如果加入当前单元后宽度未超限，则继续累积
            if w <= max_w:
                buf = trial
                continue

            # 否则先将缓冲区内容作为一行输出
            if buf:
                lines.append(buf)

            # 处理当前单元
            if has_space and len(u) > 1:
                tmp = ""
                for ch in u:
                    if draw.textlength(tmp + ch, font=font) <= max_w:
                        tmp += ch
                        continue

                    if tmp:
                        lines.append(tmp)
                    tmp = ch
                buf = tmp
                continue

            if draw.textlength(u, font=font) <= max_w:
                buf = u
            else:
                lines.append(u)
                buf = ""
        if buf != "":
            lines.append(buf)
        if para == "" and (not lines or lines[-1] != ""):
            lines.append("")
    return lines


def _is_bracket_token(tok: str) -> bool:
    return tok.startswith("【") and tok.endswith("】")


def _split_long_token(draw: ImageDraw.ImageDraw, token: str, font: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
    """
    将过长的 token 切成多个子 token，每个子 token 宽度 <= max_w（尽量）。
    对于成对括号 token，会尝试在不拆开括号两端的情况下拆内部；当确实无法放下时，
    会把内部切成多个段并把括号字符附在首/尾段上，从而在必要时可拆开。
    """
    # 快速返回
    if draw.textlength(token, font=font) <= max_w:
        return [token]

    # 检查是否为成对括号 token
    if _is_bracket_token(token) and len(token) > 2:
        inner = token
        # 先尝试把整个 bracket token 当作一个单位（失败），则分割 inner
        chunks_inner: List[str] = []
        buf = ""
        for ch in inner:
            trial = buf + ch
            # 为首段和末段我们会额外加上括号宽度，先用 conservative 估计：
            # 这里不把括号加到 trial 中判断（下面会在生成带括号的段时二次检查）
            if draw.textlength(trial, font=font) <= max_w:
                buf = trial
            else:
                if buf == "":
                    # 单字符也超过 max_w，强行发出单字符（避免死循环）
                    chunks_inner.append(ch)
                    buf = ""
                else:
                    chunks_inner.append(buf)
                    buf = ch
        if buf:
            chunks_inner.append(buf)

        safe: List[str] = []
        for piece in chunks_inner:
            if draw.textlength(piece, font=font) <= max_w:
                safe.append(piece)
            else:
                # break into characters
                tmp = ""
                for ch in piece:
                    trial = tmp + ch
                    if draw.textlength(trial, font=font) <= max_w:
                        tmp = trial
                    else:
                        if tmp:
                            safe.append(tmp)
                        tmp = ch
                if tmp:
                    safe.append(tmp)
        return safe

    # 非括号长 token：按字符累积拆分
    parts: List[str] = []
    buf = ""
    for ch in token:
        trial = buf + ch
        if draw.textlength(trial, font=font) <= max_w:
            buf = trial
        else:
            if buf == "":
                # 单字符也超限（极端），强行放这个字符
                parts.append(ch)
                buf = ""
            else:
                parts.append(buf)
                buf = ch
    if buf:
        parts.append(buf)
    return parts


def tokenize(
        draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int
) -> List[str]:
    """
    先按逻辑切分为 tokens（保括号），
    然后对每个 token 检查宽度，必要时用 _split_long_token 拆分。
    返回最终可供 DP 使用的 token 列表（保证每个 token 宽度尽量 <= max_w）。
    """
    tokens = []
    buf = ""
    in_bracket = False
    for ch in text:
        if ch in "【[":
            if buf:
                tokens.append(buf)
            buf = "【"
            in_bracket = True
        elif ch in "】]":
            buf += "】"
            tokens.append(buf)
            buf = ""
            in_bracket = False
        elif in_bracket:
            buf += ch
        elif ch.isspace():
            if buf:
                tokens.append(buf)
                buf = ""
            # preserve single space as token so DP can consider spaces explicitly if you want
            tokens.append(ch)
        else:
            # treat ASCII letters as part of word, else treat single char
            if ch.isascii() and ch.isalpha():
                buf += ch
            else:
                if buf:
                    tokens.append(buf)
                    buf = ""
                tokens.append(ch)
    if buf:
        tokens.append(buf)

    # now split tokens that are too long
    final_tokens: List[str] = []
    for tok in tokens:
        if tok == "":
            continue
        if draw.textlength(tok, font=font) <= max_w:
            final_tokens.append(tok)
        else:
            splits = _split_long_token(draw, tok, font, max_w)
            final_tokens.extend(splits)
    return final_tokens


def wrap_lines_knuth_plass(
        draw: ImageDraw.ImageDraw, txt: str, font: ImageFont.FreeTypeFont, max_w: int
) -> List[str]:
    """
    将文本按指定宽度拆分为多行。
    简化的 Knuth–Plass 算法
    """
    tokens = tokenize(draw, txt, font, max_w)
    n = len(tokens)
    widths = [draw.textlength(t, font=font) for t in tokens]
    cum = [0.0] * (n + 1)
    for i in range(n):
        cum[i + 1] = cum[i] + widths[i]

    INF = float("inf")
    dp = [INF] * (n + 1)
    prev = [-1] * (n + 1)
    dp[0] = 0.0

    for i in range(1, n + 1):
        # iterate j backwards for early break when width > max_w
        for j in range(i - 1, -1, -1):
            line_width = cum[i] - cum[j]
            if line_width > max_w:
                break
            remaining = max_w - line_width
            badness = remaining ** 2
            if i == n:  # 最后一行不计惩罚
                badness = 0.0
            cost = dp[j] + badness
            if cost < dp[i]:
                dp[i] = cost
                prev[i] = j

    # if prev[n] == -1 then even after splitting there's no feasible layout (理论上不应发生)
    if prev[n] == -1:
        # fallback to greedy splitting (保证有结果)
        lines = []
        cur = ""
        for tok in tokens:
            trial = cur + tok
            if draw.textlength(trial, font=font) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = tok
        if cur:
            lines.append(cur)
        return lines

    # 回溯
    lines = []
    idx = n
    while idx > 0:
        j = prev[idx]
        lines.append("".join(tokens[j:idx]))
        idx = j
    lines.reverse()
    return lines


def parse_color_segments(
    s: str, in_bracket: bool, bracket_color: RGBColor, color: RGBColor
) -> Tuple[List[Tuple[str, RGBColor]], bool]:
    """
    解析字符串为带颜色信息的片段列表。
    中括号及其内部内容使用 bracket_color。
    """
    segs: List[Tuple[str, RGBColor]] = []
    buf = ""
    for ch in s:
        if ch == "[" or ch == "【":
            if buf:
                segs.append((buf, bracket_color if in_bracket else color))
                buf = ""
            segs.append((ch, bracket_color))
            in_bracket = True
        elif ch == "]" or ch == "】":
            if buf:
                segs.append((buf, bracket_color))
                buf = ""
            segs.append((ch, bracket_color))
            in_bracket = False
        else:
            buf += ch
    if buf:
        segs.append((buf, bracket_color if in_bracket else color))
    return segs, in_bracket


def parse_text_segments_with_font(
    text: str, 
    emoji_font: ImageFont.FreeTypeFont,
    normal_font: ImageFont.FreeTypeFont
) -> List[Tuple[str, ImageFont.FreeTypeFont]]:
    """
    将文本按字符分割，为每个字符分配对应的字体（emoji或普通字体）
    返回 (文本片段, 字体) 的列表
    规则：只有emoji字符使用emoji字体，其他所有字符（中文、英文、标点等）都使用普通字体
    """
    segments: List[Tuple[str, ImageFont.FreeTypeFont]] = []
    current_segment = ""
    current_font = normal_font
    
    i = 0
    while i < len(text):
        char = text[i]
        
        # 检查是否是emoji字符
        is_emoji_char = _is_emoji(char)
        target_font = emoji_font if is_emoji_char else normal_font
        
        # 如果字体类型改变，保存当前片段并开始新片段
        if target_font != current_font and current_segment:
            segments.append((current_segment, current_font))
            current_segment = char
            current_font = target_font
        else:
            current_segment += char
            current_font = target_font
        
        i += 1
    
    # 添加最后一个片段
    if current_segment:
        segments.append((current_segment, current_font))
    
    return segments


def measure_block(
    draw: ImageDraw.ImageDraw,
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    line_spacing: float,
) -> Tuple[int, int, int]:
    """
    测量文本块的宽度、高度和行高。

    :return: (最大宽度, 总高度, 行高)
    """
    ascent, descent = font.getmetrics()
    line_h = int((ascent + descent) * (1 + line_spacing))
    max_w = 0
    for ln in lines:
        max_w = max(max_w, int(draw.textlength(ln, font=font)))
    total_h = max(line_h * max(1, len(lines)), 1)
    return max_w, total_h, line_h


def draw_text_auto(
    image_source: Union[str, Image.Image],
    top_left: Tuple[int, int],
    bottom_right: Tuple[int, int],
    text: str,
    color: RGBColor = (0, 0, 0),
    max_font_height: Optional[int] = None,
    font_path: Optional[str] = None,
    emoji_font_path: Optional[str] = None,  # 新增参数：emoji字体路径
    align: Align = "center",
    valign: VAlign = "middle",
    line_spacing: float = 0.15,
    bracket_color: RGBColor = (128, 0, 128),  # 中括号及内部内容颜色
    image_overlay: Union[str, Image.Image, None] = None,
    wrap_algorithm: str = "original"  # 新增参数，用于选择换行算法
) -> bytes:
    """
    在指定矩形内自适应字号绘制文本；
    中括号及括号内文字使用 bracket_color。
    如果提供了 emoji_font_path，emoji字符将使用emoji字体，其他字符使用普通字体。
    """

    # --- 1. 打开图像 ---
    if isinstance(image_source, Image.Image):
        img = image_source.copy()
    else:
        img = Image.open(image_source).convert("RGBA")
    draw = ImageDraw.Draw(img)

    if image_overlay is not None:
        if isinstance(image_overlay, Image.Image):
            img_overlay = image_overlay.copy()
        else:
            img_overlay = (
                Image.open(image_overlay).convert("RGBA")
                if os.path.isfile(image_overlay)
                else None
            )
    else:
        img_overlay = None

    x1, y1 = top_left
    x2, y2 = bottom_right
    if not (x2 > x1 and y2 > y1):
        raise ValueError("无效的文字区域。")
    region_w, region_h = x2 - x1, y2 - y1

    # --- 2. 搜索最大字号 ---
    # 使用普通字体进行字号计算（因为emoji字体主要用于显示）
    hi = min(region_h, max_font_height) if max_font_height else region_h
    lo, best_size, best_lines, best_line_h, best_block_h = 1, 0, [], 0, 0

    while lo <= hi:
        mid = (lo + hi) // 2
        font = _load_font(font_path, mid)
        # 根据配置选择换行算法
        if wrap_algorithm == "knuth_plass":
            lines = wrap_lines_knuth_plass(draw, text, font, region_w)
        else:
            lines = wrap_lines(draw, text, font, region_w)
        w, h, lh = measure_block(draw, lines, font, line_spacing)
        if w <= region_w and h <= region_h:
            best_size, best_lines, best_line_h, best_block_h = mid, lines, lh, h
            lo = mid + 1
        else:
            hi = mid - 1

    if best_size == 0:
        font = _load_font(font_path, 1)
        # 根据配置选择换行算法
        if wrap_algorithm == "knuth_plass":
            best_lines = wrap_lines_knuth_plass(draw, text, font, region_w)
        else:
            best_lines = wrap_lines(draw, text, font, region_w)
        best_block_h, best_line_h = 1, 1
        best_size = 1
    else:
        font = _load_font(font_path, best_size)

    # 加载emoji字体（如果提供了路径）
    emoji_font = None
    if emoji_font_path and os.path.exists(emoji_font_path):
        emoji_font = _load_font(emoji_font_path, best_size)

    # --- 3. 垂直对齐 ---
    if valign == "top":
        y_start = y1
    elif valign == "middle":
        y_start = y1 + (region_h - best_block_h) // 2
    else:
        y_start = y2 - best_block_h

    # --- 4. 绘制 ---
    y = y_start
    in_bracket = False
    for ln in best_lines:
        # 计算整行的宽度（用于对齐）
        if emoji_font:
            # 如果有emoji字体，需要分别计算每个片段的宽度
            line_w = 0
            segments_with_font = parse_text_segments_with_font(ln, emoji_font, font)
            for seg_text, seg_font in segments_with_font:
                line_w += int(draw.textlength(seg_text, font=seg_font))
        else:
            line_w = int(draw.textlength(ln, font=font))
        
        # 水平对齐
        if align == "left":
            x = x1
        elif align == "center":
            x = x1 + (region_w - line_w) // 2
        else:
            x = x2 - line_w
        
        # 解析颜色片段
        segments, in_bracket = parse_color_segments(
            ln, in_bracket, bracket_color, color
        )
        
        # 绘制每个片段
        for seg_text, seg_color in segments:
            if seg_text:
                if emoji_font:
                    # 如果启用了emoji字体，按字符/片段选择字体
                    font_segments = parse_text_segments_with_font(seg_text, emoji_font, font)
                    for font_seg_text, font_seg_font in font_segments:
                        if font_seg_text:
                            # 检查是否是emoji字符，如果是则启用彩色渲染
                            is_emoji_seg = _is_emoji(font_seg_text[0]) if font_seg_text else False
                            if is_emoji_seg:
                                # 对于emoji，使用embedded_color=True以支持彩色渲染
                                try:
                                    draw.text((x, y), font_seg_text, font=font_seg_font, embedded_color=True)
                                except TypeError:
                                    # 如果PIL版本不支持embedded_color，回退到普通方式
                                    draw.text((x, y), font_seg_text, font=font_seg_font, fill=seg_color)
                            else:
                                # 非emoji字符使用指定颜色
                                draw.text((x, y), font_seg_text, font=font_seg_font, fill=seg_color)
                            x += int(draw.textlength(font_seg_text, font=font_seg_font))
                else:
                    # 没有emoji字体，使用普通字体
                    draw.text((x, y), seg_text, font=font, fill=seg_color)
                    x += int(draw.textlength(seg_text, font=font))
        
        y += best_line_h
        if y - y_start > region_h:
            break

    # 覆盖置顶图层（如果有）
    if image_overlay is not None and img_overlay is not None:
        img.paste(img_overlay, (0, 0), img_overlay)
    elif image_overlay is not None and img_overlay is None:
        print("Warning: overlay image is not exist.")

    # --- 5. 输出 PNG ---
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
