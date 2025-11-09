# --- 1. 导入必要的库 ---
from io import BytesIO  # 用于在内存中读写 "字节" 数据，这里用来保存最终的PNG图片
from typing import Tuple, Union, Literal , Optional ,List # 用于 "类型提示"，让代码更易读
from PIL import Image, ImageDraw, ImageFont # 导入Pillow库，用于 "打开/创建图片"、"在图片上绘画"、"加载字体"
import os # 用于检查文件是否存在 (例如字体文件)

# --- 2. 定义类型别名 (让代码更清晰) ---
# 'Align' 只允许是 "left"、"center"、"right" 三个字符串之一
Align = Literal["left", "center", "right"]
# 'VAlign' 只允许是 "top"、"middle"、"bottom" 三个字符串之一
VAlign = Literal["top", "middle", "bottom"]

def draw_text_auto(
    # --- 3. 函数参数定义 ---
    image_source: Union[str, Image.Image], # 底图：可以是一个 "文件路径" (str)，也可以是 "已打开的Pillow图片" (Image.Image)
    top_left: Tuple[int, int],              # (x1, y1) 矩形区域的 "左上角" 坐标
    bottom_right: Tuple[int, int],          # (x2, y2) 矩形区域的 "右下角" 坐标
    text: str,                              # 要绘制的 "原始文本"
    color: Tuple[int, int, int] = (0, 0, 0), # 默认文字颜色 (R, G, B)，默认是黑色
    max_font_height: Optional[int] = None,   # "可选"：限制最大字号。如果不设置(None)，它会尝试填满整个区域
    font_path: Optional[str] = None,         # "可选"：字体文件 (.ttf) 的路径
    align: Align = "center",                 # 水平对齐方式
    valign: VAlign = "middle",               # 垂直对齐方式
    line_spacing: float = 0.15,              # "行间距" (0.15 表示 15% 的额外间距)
    bracket_color: Tuple[int, int, int] = (128, 0, 128),  # "中括号" [] 或 【】 及其内部文字的 "特殊颜色"，默认紫色
    image_overlay: Union[str, Image.Image, None]=None, # "可选"：一个 "遮罩" 图片，会覆盖在 "最上层"
) -> bytes: # "返回值"：函数最终会返回 "PNG图片的字节流" (bytes)
    """
    函数文档：
    在指定矩形内自适应字号绘制文本；
    中括号及括号内文字使用 bracket_color。
    """

    # --- 4. 准备底图和画布 ---
    
    # 1. 打开底图
    if isinstance(image_source, Image.Image):
        # 如果传入的是 "Pillow图片对象"，就 "复制" 一份来用 (防止修改原图)
        img = image_source.copy()
    else:
        # 如果传入的是 "文件路径" (str)，就 "打开" 它
        # .convert("RGBA") 确保图片是 RGBA 模式，这样可以处理透明度
        img = Image.open(image_source).convert("RGBA")
        
    # 2. 创建 "画笔" 对象，之后的所有 "绘制" 操作都由 'draw' 来完成
    draw = ImageDraw.Draw(img)

    # 3. (可选) 准备 "遮罩" 图层
    if image_overlay is not None:
        if isinstance(image_overlay, Image.Image):
            img_overlay = image_overlay.copy() # 同上，复制一份
        else:
            # 如果是路径，就打开它。如果文件不存在 (os.path.isfile)，就设为 None
            img_overlay = Image.open(image_overlay).convert("RGBA") if os.path.isfile(image_overlay) else None

    # 4. 计算 "文字区域" 的坐标和宽高
    x1, y1 = top_left
    x2, y2 = bottom_right
    if not (x2 > x1 and y2 > y1):
        # 如果坐标不合法 (例如右下角在左上角上面)，就报错
        raise ValueError("无效的文字区域。")
    # 'region_w' 和 'region_h' 是允许绘制文字的 "最大宽度" 和 "最大高度"
    region_w, region_h = x2 - x1, y2 - y1

    # --- 5. 定义 "内部" 辅助函数 ---
    
    # 辅助函数 1: 加载字体
    def _load_font(size: int) -> ImageFont.FreeTypeFont:
        """根据 "字号" (size) 加载字体文件"""
        if font_path and os.path.exists(font_path):
            # 1. 优先使用 "config" 中指定的字体
            return ImageFont.truetype(font_path, size=size)
        try:
            # 2. 如果没指定，尝试一个 "常见的" 跨平台字体
            return ImageFont.truetype("DejaVuSans.ttf", size=size)
        except Exception:
            # 3. 如果都失败了，使用 Pillow "自带" 的默认字体 (很小，不好看)
            return ImageFont.load_default()

    # 辅助函数 2: 自动换行
    def wrap_lines(txt: str, font: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
        """将长文本 (txt) 根据 "最大宽度" (max_w) 切割成 "多行" (List[str])"""
        lines: list[str] = [] # 存储最终的 "行" 列表
        
        # 1. 首先按 "换行符" (\n) 分割成 "段落" (para)
        #    (如果 txt 是空字符串，or [""] 确保至少有一个空段落)
        for para in txt.splitlines() or [""]:
            # 2. 检查这段文字是否包含 "空格" (用于判断是 "英文" 还是 "中文")
            has_space = (" " in para)
            
            # 3. "拆分单位" (units)
            #    - 如果是英文 (has_space=True)，就按 "单词" 拆分
            #    - 如果是中文 (has_space=False)，就按 "单个字" 拆分
            units = para.split(" ") if has_space else list(para)
            
            buf = "" # "当前行" 的缓冲区

            # 4. "连接单位" 的小函数 (英文单词间加空格，中文不加)
            def unit_join(a: str, b: str) -> str:
                if not a: return b # 如果缓冲区是空的，直接返回
                return (a + " " + b) if has_space else (a + b)

            # 5. 遍历所有 "单位" (单词或汉字)
            for u in units:
                # 6. "试一试"：把 "当前单位" (u) 加到 "缓冲区" (buf) 后面
                trial = unit_join(buf, u)
                
                # 7. "量一量"：用画笔 "测量" 试排的 "trial" 有多宽
                w = draw.textlength(trial, font=font)
                
                # 8. "判断"
                if w <= max_w:
                    # 8a. "放得下"：把 "trial" 存入缓冲区，成为 "当前行"
                    buf = trial
                else:
                    # 8b. "放不下"：
                    # (1) 把 "上一轮" 的缓冲区 (buf) "存" 起来，作为 "一行"
                    if buf:
                        lines.append(buf)
                    
                    # (2) "特殊处理"：如果一个 "单词" (u) 本身就 "超过一行" 了 (例如一个超长链接)
                    if has_space and len(u) > 1:
                        tmp = ""
                        # "暴力拆分" 这个单词，一个 "字母" 一个字母地试
                        for ch in u:
                            if draw.textlength(tmp + ch, font=font) <= max_w:
                                tmp += ch
                            else:
                                if tmp: lines.append(tmp)
                                tmp = ch
                        buf = tmp # 拆分后剩下的部分
                    else:
                        # (3) "普通处理"：
                        #    - 如果 "当前单位" (u) 没超长，就把它作为 "下一行" 的 "开头"
                        #    - 如果 "当前单位" (u) (例如一个中文标点) 也超长了，就单独占一行
                        if draw.textlength(u, font=font) <= max_w:
                            buf = u
                        else:
                            lines.append(u)
                            buf = ""
                            
            # 9. "收尾"：把 "最后" 缓冲区 (buf) 里剩下的内容存为 "最后一行"
            if buf != "":
                lines.append(buf)
                
            # 10. "处理空行"：如果用户输入了 "两个" 换行符，(para == "") 
            #     就在 "行列表" (lines) 中也加一个 "空行"
            if para == "" and (not lines or lines[-1] != ""):
                lines.append("")
                
        return lines

    # 辅助函数 3: 测量文字块
    def measure_block(lines: List[str], font: ImageFont.FreeTypeFont) -> Tuple[int, int, int]:
        """测量 "多行" 文本 "整体" 的宽度、高度和 "单行" 高度"""
        # 1. 获取字体的 "基线" (ascent) 和 "下沉" (descent)
        ascent, descent = font.getmetrics()
        
        # 2. "单行高度" = 字体高度 * (1 + 行间距)
        line_h = int((ascent + descent) * (1 + line_spacing))
        
        # 3. "总宽度" = "最宽" 的那一行 (max_w)
        max_w = 0
        for ln in lines:
            max_w = max(max_w, int(draw.textlength(ln, font=font)))
            
        # 4. "总高度" = 单行高度 * 行数
        total_h = max(line_h * max(1, len(lines)), 1) # (最少 1px 高)
        
        return max_w, total_h, line_h

    # --- 6. "二分查找" 最佳字号 ---
    # 这是 "自适应" 的核心：我们要找到一个 "最大" 的字号 (size)，
    # 使得文字用这个字号 "排版后" (w, h)，"刚好" 能塞进 "矩形区域" (region_w, region_h)
    
    # 1. "搜索上限" (hi)：字号 "最大" 不可能超过 "区域高度" (region_h) 或 "用户限制" (max_font_height)
    hi = min(region_h, max_font_height) if max_font_height else region_h
    # 2. "搜索下限" (lo)：字号 "最小" 为 1
    lo = 1
    # 3. "最佳" 结果的 "暂存" 变量
    best_size, best_lines, best_line_h, best_block_h = 1, [], 1, 1

    # 4. 开始 "二分" 循环 (当 "下限" 小于等于 "上限" 时)
    while lo <= hi:
        # 5. "猜" 一个 "中间" 的字号
        mid = (lo + hi) // 2
        
        # 6. "测试" 这个字号：
        font = _load_font(mid)                           # (a) 加载字体
        lines = wrap_lines(text, font, region_w)         # (b) 自动换行
        w, h, lh = measure_block(lines, font)            # (c) 测量总宽高
        
        # 7. "判断" 测试结果
        if w <= region_w and h <= region_h:
            # 7a. "放得下！"：
            # (1) "记住" 这个字号 (mid) 和它的排版结果 (lines, lh, h)
            best_size, best_lines, best_line_h, best_block_h = mid, lines, lh, h
            # (2) "再试试更大的"：把 "下限" (lo) 提高到 mid + 1
            lo = mid + 1
        else:
            # 7b. "放不下..." (太宽或太高)：
            # (1) "必须用更小的"：把 "上限" (hi) 降低到 mid - 1
            hi = mid - 1

    # 8. (特殊情况) 如果连 1 号字都 "放不下" (best_size 没被更新过)
    if best_size == 1 and not best_lines:
        font = _load_font(1)
        best_lines = wrap_lines(text, font, region_w)
        _, best_block_h, best_line_h = measure_block(best_lines, font)
        best_size = 1
    else:
        # 9. (正常情况) 循环结束，"best_size" 就是 "最佳字号"
        #    我们 "最后" 加载一次 "最佳" 的字体和排版
        font = _load_font(best_size)

    # --- 7. "解析" 特殊颜色 (中括号) ---
    # 目标：把 "一行文字" (str) -> 转换成 "带颜色分段" 的列表 
    # 例如： "你好[朋友]" -> [ ("你好", 黑色), ("[", 紫色), ("朋友", 紫色), ("]", 紫色) ]
    
    def parse_color_segments(s: str, in_bracket: bool) -> Tuple[List[Tuple[str, Tuple[int, int, int]]], bool]:
        """
        解析一行的 "颜色片段"
        'in_bracket' 是 "上一行" 结束时 "是否在" 括号里 (用于处理 "跨行" 的括号)
        """
        segs: list[tuple[str, Tuple[int, int, int]]] = [] # "片段" 列表
        buf = "" # "当前颜色" 的 "文字缓冲区"
        
        for ch in s: # 遍历 "这一行" 的 "每个" 字符
            if ch == "[" or ch == "【":
                # 1. 遇到 "开" 括号
                if buf: # (a) "清空" 缓冲区，把 "括号前" 的文字按 "当前" 颜色存入
                    segs.append((buf, bracket_color if in_bracket else color))
                    buf = ""
                # (b) "存入" "开括号" 本身 (使用 "括号色")
                segs.append((ch, bracket_color))
                in_bracket = True # "标记"：我们 "进入" 括号了
            elif ch == "]" or ch == "】":
                # 2. 遇到 "关" 括号
                if buf: # (a) "清空" 缓冲区，把 "括号内" 的文字按 "括号色" 存入
                    segs.append((buf, bracket_color))
                    buf = ""
                # (b) "存入" "关括号" 本身 (使用 "括号色")
                segs.append((ch, bracket_color))
                in_bracket = False # "标记"：我们 "离开" 括号了
            else:
                # 3. "普通" 字符：加入 "缓冲区"
                buf += ch
                
        # 4. "收尾"：把 "最后" 缓冲区里剩下的文字存入
        if buf:
            segs.append((buf, bracket_color if in_bracket else color))
            
        # 5. 返回 "片段列表" 和 "当前行" 结束时的 "括号状态" (给 "下一行" 用)
        return segs, in_bracket

    # --- 8. 计算 "起始" 绘制坐标 (垂直对齐) ---
    if valign == "top":
        # "顶" 对齐：从 "区域顶部" (y1) 开始画
        y_start = y1
    elif valign == "middle":
        # "中" 对齐：(区域高度 - 文字总高度) / 2
        y_start = y1 + (region_h - best_block_h) // 2
    else: # "bottom"
        # "底" 对齐：从 "区域底部" (y2) 减去 "文字总高度" 的地方开始画
        y_start = y2 - best_block_h

    # --- 9. "真正" 开始绘制！ ---
    y = y_start # 'y' 是 "当前行" 的 "顶部" 坐标
    in_bracket = False # "初始状态"：不在括号里
    
    # 1. 遍历 "每一行" (来自 "最佳" 排版 'best_lines')
    for ln in best_lines:
        # 2. "测量" "当前行" 的 "宽度" (用于 "水平对齐")
        line_w = int(draw.textlength(ln, font=font))
        
        # 3. "计算" "当前行" 的 "起始 x" 坐标
        if align == "left":
            x = x1
        elif align == "center":
            x = x1 + (region_w - line_w) // 2
        else: # "right"
            x = x2 - line_w
            
        # 4. "解析" "当前行" 的 "颜色片段"
        #    'in_bracket' 状态会 "传递" 到下一次循环
        segments, in_bracket = parse_color_segments(ln, in_bracket)
        
        # 5. "遍历" "这一行" 的 "所有" 片段 (一个片段 = 一段文字 + 一个颜色)
        for seg_text, seg_color in segments:
            if seg_text: # (防止空字符串)
                # 6. "开画！"：在 (x, y) 坐标，用 "指定字体" 和 "指定颜色" 绘制 "片段文字"
                draw.text((x, y), seg_text, font=font, fill=seg_color)
                # 7. "移动" "x" 坐标：(x = x + 刚画的片段宽度)
                #    为 "下一个" 片段做准备
                x += int(draw.textlength(seg_text, font=font))
                
        # 8. "移动" "y" 坐标：(y = y + 单行高度)
        #    为 "下一行" 做准备
        y += best_line_h
        
        # 9. (保险) 如果画的高度 "超出" 区域了，就 "停止" (防止越界)
        if y - y_start > region_h:
            break

    # --- 10. 绘制 "遮罩" (在所有文字 "画完" 之后) ---
    if image_overlay is not None and img_overlay is not None:
        # 1. 'img.paste(遮罩, 坐标, 遮罩)'
        #    第3个参数 'img_overlay' 表示 "使用 '遮罩' 自己的透明通道"
        #    这样 "遮罩" 的 "透明" 部分 "不会" 覆盖 "底图"
        img.paste(img_overlay, (0, 0), img_overlay)
    elif image_overlay is not None and img_overlay is None:
        # (如果指定了遮罩路径，但文件不存在)
        print("Warning: overlay image is not exist.")

    # --- 11. "输出" 最终图片 ---
    
    # 1. 创建一个 "内存中" 的 "文件"
    buf = BytesIO()
    # 2. "保存" P好的图片 (img) 到 "内存" (buf) 中，格式为 "PNG"
    img.save(buf, format="PNG")
    # 3. "返回" 内存中 PNG 文件的 "所有字节" (bytes)
    return buf.getvalue()
