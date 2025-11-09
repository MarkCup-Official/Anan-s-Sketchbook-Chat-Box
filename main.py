# --- 1. 导入必要的库 ---
import keyboard  # 用于监听和模拟键盘按键（例如：监听热键、模拟Ctrl+V）
import time      # 用于在两次键盘操作之间添加短暂延迟，确保系统有时间反应
import pyperclip # 用于读取和写入剪贴板中的 "文本" 内容
import io        # 用于在内存中处理 "字节流" 数据，比如图片文件
from PIL import Image # Pillow库，Python中最强大的图像处理库，用于打开、P图、保存图片

# 下面这些是 Windows 特有的库，用于更底层的操作
import win32clipboard # 用于处理剪贴板中的 "非文本" 数据，尤其是 "图片"
import win32gui       # 用于获取当前激活的窗口信息pip install -U pywin32
import win32process   # 用于根据窗口信息获取对应的 "进程ID" (PID)
import psutil         # 一个跨平台的库，用于根据 "进程ID" 获取进程的详细信息（比如 .exe 的名字）

from typing import Optional, Tuple # 用于给函数参数添加 "类型提示"，让代码更易读（例如：一个参数"可能"是None）

# --- 2. 从 config.py 配置文件中导入所有设置 ---
# 这会导入你在 config 文件中定义的所有大写变量
from config import (
    DELAY,                  # 操作间的延迟时间（秒）
    FONT_FILE,              # 字体文件的路径
    BASEIMAGE_MAPPING,      # 关键词 -> 表情底图 的 "字典"
    BASEIMAGE_FILE,         # 默认的表情底图
    AUTO_SEND_IMAGE,        # P完图后是否自动发送
    AUTO_PASTE_IMAGE,       # P完图后是否自动粘贴
    BLOCK_HOTKEY,           # 是否 "拦截" 原始的热键按键
    HOTKEY,                 # 触发P图的 "热键" (例如 "enter")
    SEND_HOTKEY,            # 模拟 "发送" 的快捷键 (例如 "enter")
    PASTE_HOTKEY,           # 模拟 "粘贴" 的快捷键 (例如 "ctrl+v")
    CUT_HOTKEY,             # 模拟 "剪切" 的快捷key (例如 "ctrl+x")
    SELECT_ALL_HOTKEY,      # 模拟 "全选" 的快捷key (例如 "ctrl+a")
    TEXT_BOX_TOPLEFT,       # P图中 "文字/图片" 区域的左上角坐标
    IMAGE_BOX_BOTTOMRIGHT,  # P图中 "文字/图片" 区域的右下角坐标
    BASE_OVERLAY_FILE,      # 覆盖在最上层的 "遮罩" 图片（比如对话框）
    USE_BASE_OVERLAY,       # 是否启用 "遮罩"
    ALLOWED_PROCESSES       # 允许本脚本生效的程序列表（例如 ["qq.exe"])
)

# --- 3. 导入我们自己写的 P图 函数 ---
from text_fit_draw import draw_text_auto     # 导入 "画文字" 的函数
from image_fit_paste import paste_image_auto # 导入 "贴图片" 的函数

# --- 4. 全局变量 ---
# current_image_file 用于 "记住" 当前正在使用的是哪张底图（例如 "开心.png"）
# 它是一个全局变量，这样程序就可以在多次按键之间 "保持记忆"
current_image_file = BASEIMAGE_FILE # 程序刚启动时，使用默认底图


def get_foreground_window_process_name() -> Optional[str]:
    """
    获取当前 "最前面" (用户正在使用) 的窗口，并返回它的进程名 (例如 "qq.exe")
    """
    try:
        # 1. 获取当前激活窗口的 "句柄" (handle)，这是一个唯一的窗口ID
        hwnd = win32gui.GetForegroundWindow()
        # 2. 通过窗口句柄，获取创建这个窗口的 "进程ID" (PID)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        # 3. 使用 psutil 库，通过 PID 获取进程的详细信息
        process = psutil.Process(pid)
        # 4. 返回进程的 .exe 名字，并统一转为小写字母，方便比较
        return process.name().lower()
    except Exception as e:
        # 如果中途出错 (例如没有权限获取、窗口已关闭等)，就打印错误信息
        print(f"无法获取当前进程名称: {e}")
        return None # 并返回 None (空)

def copy_png_bytes_to_clipboard(png_bytes: bytes):
    """
    将内存中的 PNG 图片数据 (bytes) 复制到 Windows 剪贴板。
    这是本脚本中最复杂但最关键的函数之一。
    QQ、微信这类软件不认识内存中的 PNG 格式，但它们认识 Windows 的 CF_DIB 格式 (一种BMP图片)。
    所以我们需要先把 PNG -> BMP -> CF_DIB。
    """
    
    # 1. 使用 PIL 的 Image.open 从 "内存中" 读取 PNG 字节数据
    # io.BytesIO(png_bytes) 创建了一个 "内存中的文件"
    image = Image.open(io.BytesIO(png_bytes))
    
    # 2. 将图片转换为 Windows 剪贴板 "认识" 的格式
    # 我们用一个 "内存输出流" (output) 来保存转换后的图片
    with io.BytesIO() as output:
        # 3. 将图片转换成 "RGB" 模式 (去掉透明通道) 并保存为 "BMP" 格式到 output 中
        image.convert("RGB").save(output, "BMP")
        # 4. 获取 BMP 格式的 "全部" 字节数据
        bmp_full_data = output.getvalue()
        # 5. 关键一步：Windows 的 CF_DIB 格式是 "没有文件头" 的 BMP 数据。
        #    BMP 文件头固定为 14 个字节，我们把它 "切掉"
        bmp_data = bmp_full_data[14:]

    # 6. 使用 win32clipboard 库，把处理好的 DIB 数据放入剪贴板
    try:
        win32clipboard.OpenClipboard()     # 打开剪贴板 (锁定，防止其他程序写入)
        win32clipboard.EmptyClipboard()    # 清空剪贴板
        # 7. 放入我们的数据，并 "明确" 告诉系统，我们放的是 "CF_DIB" (图片) 格式
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data)
    finally:
        win32clipboard.CloseClipboard()    # 无论成功与否，"必须" 关闭剪贴板 (解锁)


def cut_all_and_get_text() -> Tuple[str, object]:
    """
    模拟 "Ctrl+A" (全选) 和 "Ctrl+X" (剪切)，
    从当前输入框中 "偷" 走所有文本。
    返回 "偷" 到的文本 和 "原始" 的剪贴板内容。
    """
    
    # 1. 备份！非常重要！先把用户剪贴板里 "原来" 的文本存起来
    old_clip = pyperclip.paste()

    # 2. 清空剪贴板 (使用 pyperclip)，确保我们等下读到的是 "新" 数据
    pyperclip.copy("")

    # 3. 模拟按键：发送 "全选" (例如 Ctrl+A)
    keyboard.send(SELECT_ALL_HOTKEY)
    # 4. 模拟按键：发送 "剪切" (例如 Ctrl+X)
    #    这时，输入框中的文本就被 "剪" 到了剪贴板里
    keyboard.send(CUT_HOTKEY)
    # 5. 等待一小会儿 (例如 0.1 秒)，给操作系统一点反应时间
    time.sleep(DELAY)

    # 6. 从剪贴板中读取刚刚 "剪" 到的内容
    new_clip = pyperclip.paste()

    # 7. 返回 "新" 内容 (偷来的文本) 和 "旧" 内容 (备份的)
    return new_clip, old_clip

def try_get_image() -> Optional[Image.Image]:
    """
    尝试从剪贴板获取 "图片"。
    (这个函数在 cut_all_and_get_text 之后运行)
    如果用户在聊天框里不是打字，而是 "选中" 了一张图片 (比如截图后粘贴在输入框里)，
    那么上一步的 "Ctrl+X" (剪切) 会把 "图片" 放入剪贴板。
    这个函数就是用来检查这种情况的。
    """
    try:
        win32clipboard.OpenClipboard() # 打开剪贴板
        
        # 1. 检查剪贴板中 "是否包含" CF_DIB (图片) 格式的数据
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            # 2. 如果有，就把它取出来
            data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
            if data:
                # 3. 这时 "data" 是 "没有文件头" 的 BMP 数据，PIL 不认识
                #    我们必须 "手动" 给它加上一个 14 字节的 BMP 文件头
                header = b'BM' + (len(data) + 14).to_bytes(4, 'little') + b'\x00\x00\x00\x00\x36\x00\x00\x00'
                
                # 4. 现在 "header + data" 是一个 "完整" 的 BMP 图像数据
                #    使用 PIL 从内存中读取它
                image = Image.open(io.BytesIO(header + data))
                return image # 成功！返回 PIL Image 对象
                
    except Exception as e:
        print("无法从剪贴板获取图像：", e)
    finally:
        # 5. 无论如何，"必须" 关闭剪贴板
        try:
            win32clipboard.CloseClipboard()
        except:
            pass # 如果关闭失败 (比如没打开过)，就忽略
            
    return None # 如果没有图片或出错，返回 None


# --- 5. 核心功能函数：Start() ---
# 当用户按下 "热键" (HOTKEY) 时，这个函数会被调用
def Start():
    # 声明我们将要 "修改" 全局变量 current_image_file
    global current_image_file
    
    # --- 步骤 A: 检查当前程序是否 "允许" 运行 ---
    if ALLOWED_PROCESSES: # 如果列表不是空的 (即设置了限制)
        # 1. 获取当前是什么程序 (例如 "qq.exe")
        current_process = get_foreground_window_process_name()
        
        # 2. 检查当前程序名 "是否不在" 允许的列表中
        if current_process is None or current_process not in [p.lower() for p in ALLOWED_PROCESSES]:
            print(f"当前进程 {current_process} 不在允许列表中，跳过执行")
            
            # 3. 如果 "不拦截" 热键 (BLOCK_HOTKEY 为 False)
            #    我们就 "假装" 用户按下了原始的键
            #    例如：热键是 "enter"，在浏览器里按 "enter"，P图不执行，但 "enter" 键会正常触发 (换行)
            if not BLOCK_HOTKEY:
                keyboard.send(HOTKEY)
            return # 退出 Start() 函数，P图流程结束

    print("Start generate...") # 打印日志，表示P图开始

    # --- 步骤 B: 取走输入框的内容 ---
    #    步骤：
    #    1. "cut_all_and_get_text" 会模拟 "Ctrl+X"。
    #    2. 如果用户选中了文字，"Ctrl+X" 会剪切 "文字"。
    #    3. 如果用户选中了图片 (QQ/微信里)，"Ctrl+X" 会剪切 "图片"。
    
    text, old_clipboard_content = cut_all_and_get_text() # 先尝试 "剪切"
    image = try_get_image() # 再检查剪贴板里 "是不是图片"
    
    # "text" 是剪到的文字 (如果剪到的是图片，text 会是空字符串 "")
    # "image" 是剪到的图片 (如果剪到的是文字，image 会是 None)
    # "old_clipboard_content" 是 "运行前" 剪贴板里的 "文字" (用于恢复)

    # --- 步骤 C: 检查是否 "什么都没偷到" ---
    if text == "" and image is None:
        print("剪贴板和输入框都是空的，P图终止")
        # 恢复原始剪贴板 (防止 "Ctrl+A/X" 把用户原来的剪贴板清空了)
        pyperclip.copy(old_clipboard_content) 
        return # 退出

    
    png_bytes = None # 初始化一个变量，用于存放最终P好的图片数据

    # --- 步骤 D: P图逻辑 (二选一) ---
    
    # 情况 1: 如果 "偷" 到的是 "图片" (image 不是 None)
    if image is not None:
        print("检测到输入为 [图片]，开始合成...")
        try:
            # 调用 "贴图片" 函数
            png_bytes = paste_image_auto(
                image_source = current_image_file,  # 底图 (用当前"记住"的表情)
                image_overlay = BASE_OVERLAY_FILE if USE_BASE_OVERLAY else None, # 遮罩
                top_left = TEXT_BOX_TOPLEFT,        # 粘贴区域左上角
                bottom_right = IMAGE_BOX_BOTTOMRIGHT, # 粘贴区域右下角
                content_image = image,              # "偷" 来的那张图片
                align = "center",
                valign = "middle",
                padding = 12,
                allow_upscale = True,
                keep_alpha = True,
            )
        except Exception as e:
            print(f"合成图片失败: {e}")
            pyperclip.copy(old_clipboard_content) # 出错了也要恢复剪贴板
            return

    # 情况 2: 如果 "偷" 到的是 "文字" (text 不是 "")
    elif text != "":
        print(f"检测到输入为 [文字]: {text}")
        
        # 2a. P图前，先检查文字中是否包含 "切换表情" 的关键词
        for keyword, img_file in BASEIMAGE_MAPPING.items(): # 遍历 config 里的关键词字典
            if keyword in text:
                print(f"检测到关键词 '{keyword}'，切换底图为: {img_file}")
                current_image_file = img_file # 切换 "全局" 底图
                text = text.replace(keyword, "").strip() # 从文字中 "删除" 这个关键词
                break # 找到一个就停止，防止一个句子触发多个
        
        # 2b. 开始P图
        try:
            # 调用 "画文字" 函数
            png_bytes = draw_text_auto(
                image_source = current_image_file,  # 底图 (可能是刚切换的)
                image_overlay = BASE_OVERLAY_FILE if USE_BASE_OVERLAY else None, # 遮罩
                top_left = TEXT_BOX_TOPLEFT,        # 绘画区域左上角
                bottom_right = IMAGE_BOX_BOTTOMRIGHT, # 绘画区域右下角
                text = text,                        # "偷" 来的文字 (已去除关键词)
                color = (0, 0, 0),                  # 字体颜色 (黑色)
                max_font_height = 64,               # 限制最大字号
                font_path = FONT_FILE,            # 字体文件
            )
        except Exception as e:
            print(f"绘制文字失败: {e}")
            pyperclip.copy(old_clipboard_content) # 出错了也要恢复剪贴板
            return

    # --- 步骤 E: 检查 P图 是否成功 ---
    if png_bytes is None:
        print("生成图片失败！(未知错误)")
        pyperclip.copy(old_clipboard_content) # 恢复剪贴板
        return

    # --- 步骤 F: P图成功！将图片 "发送" 出去 ---
    
    # 1. 把P好的图片 (png_bytes) 放入 "剪贴板"
    copy_png_bytes_to_clipboard(png_bytes)
    
    # 2. 检查 config 是否配置了 "自动粘贴"
    if AUTO_PASTE_IMAGE:
        # 模拟 "粘贴" (例如 Ctrl+V)
        keyboard.send(PASTE_HOTKEY)
        
        time.sleep(DELAY) # 暂停一下，等待粘贴操作完成
        
        # 3. 检查 config 是否配置了 "自动发送" (必须在自动粘贴后)
        if AUTO_SEND_IMAGE:
            # 模拟 "发送" (例如 Enter)
            keyboard.send(SEND_HOTKEY)

    # --- 步骤 G: 善后 ---
    # "必须" 把用户 "原始" 的剪贴板内容 "还" 回去
    # 否则，如果用户 "Ctrl+C" 了一段文字，用了P图，会发现剪贴板内容变了
    pyperclip.copy(old_clipboard_content)
    
    print("图片生成并处理成功！")


# --- 6. 程序主入口 (启动器) ---

print("Starting...")
print(f"热键已绑定: {HOTKEY}")
print(f"允许的进程: {ALLOWED_PROCESSES or '所有进程'}")

# 1. 注册全局热键！
#   - HOTKEY: 要监听的按键 (来自 config)
#   - Start: 按下热键时，要调用的 "函数"
#   - suppress: 是否 "拦截" 这个按键
#     - (BLOCK_HOTKEY or HOTKEY==SEND_HOTKEY)的逻辑：
#     - a) 如果 config 里 "BLOCK_HOTKEY" 设置为 True，则拦截
#     - b) 如果 "触发键" (HOTKEY) 和 "发送键" (SEND_HOTKEY) 是同一个键 (例如都是"enter")
#          则 "必须" 拦截 (suppress=True)，否则会无限循环 (P图->发送->P图->发送...)
ok = keyboard.add_hotkey(HOTKEY, Start, suppress=(BLOCK_HOTKEY or HOTKEY==SEND_HOTKEY))
if not ok:
    print("警告：绑定热键失败！可能是权限不足或按键被占用。")

# 2. 保持程序运行
#    keyboard.wait() 会让程序 "阻塞" 在这里，
#    使 Python 脚本不会退出，从而可以 "持续" 在后台监听热键。
#    你可以按 "Ctrl+C" 在命令行中终止它。
try:
    keyboard.wait()
except KeyboardInterrupt:
    print("\n程序已退出。")
