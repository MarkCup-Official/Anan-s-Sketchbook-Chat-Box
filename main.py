# hotkey_demo.py
import keyboard
import time
import pyperclip
from text_fit_draw import draw_text_auto
import io
from PIL import Image
import win32clipboard

DELAY= 0.1

current_bg = "base.png"
def copy_png_bytes_to_clipboard(png_bytes: bytes):
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


def cut_all_and_get_text() -> str:
    """
    模拟 Ctrl+A / Ctrl+X 剪切全部文本，并返回剪切得到的内容。
    delay: 每步之间的延时（秒），默认0.1秒。
    """
    # 备份原剪贴板
    old_clip = pyperclip.paste()

    # 清空剪贴板，防止读到旧数据
    pyperclip.copy("")

    # 发送 Ctrl+A 和 Ctrl+X
    keyboard.send('ctrl+a')
    keyboard.send('ctrl+x')
    time.sleep(DELAY)

    # 获取剪切后的内容
    new_clip = pyperclip.paste()

    return new_clip

def Start():
    global current_bg

    print("Start generate...")

    text=cut_all_and_get_text()
    if text == "":
        print("no text")
        return




    for marker, bg_image in [
        ("安安正常", "base.png"),
        ("安安开心", "开心.png"),
        ("安安生气", "生气.png"),
        ("安安无语", "无语.png"),
        ("安安病娇", "病娇.png"),
        ("安安魔女化", "魔女化.png"),
        ("安安脸红", "脸红.png")
    ]:
        if marker in text:
            current_bg = bg_image
            text = text.replace(marker, "").strip()
            print(f"使用 {bg_image} 作为背景")
            break

    image_source = current_bg
    print("Get text: "+text)

    if image_source == "魔女化.png":
        # 魔女化图片(541x648)使用底部居中的文本区域
        top_left = (80, 548)
        bottom_right = (580, 548+80)
        text_height =128
    else:
        # 其他图片使用原来的文本区域
        top_left = (119, 450)
        bottom_right = (119 + 279, 450 + 175)
        text_height = 64

    png_bytes = draw_text_auto(
        image_source=image_source,
        top_left=top_left,
        bottom_right=bottom_right,
        text=text,
        color=(0, 0, 0),
        max_font_height=text_height,
        font_path="font.ttf"
    )
    copy_png_bytes_to_clipboard(png_bytes)

    keyboard.send('ctrl+v')

    time.sleep(DELAY)
    keyboard.send('enter')




# 绑定 Ctrl+Alt+H 作为全局热键
ok=keyboard.add_hotkey('enter', Start, suppress=True)

print("Starting...")
print("Hot key bind: "+str(bool(ok)))

# 保持程序运行
keyboard.wait()
