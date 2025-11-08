# 安安的素描本聊天框

本项目是一个将你在一个文本输入框中的文字或图片写到安安的素描本上的项目

## AI声明

本项目 90% 的代码由AI生成（在加上 MacOS 适配后浓度可能更高了）

## 部署

本项目支持 windows 和 macos

本项目不提供字体文件和安安图片，需要你自己想办法加进来，分别命名为 `font.ttf`，`base.png` 和 `base_overlay.png`。
其中 `font.ttf` 为字体文件，`base.png`为安安拿素描本的照片，`base_overlay.png` 为透明底的安安袖子, 用于防止文字和图片覆盖在袖子上方.
如果分辨率不一样的安安图片, 需要修改`config.py`的 `TEXT_BOX_TOPLEFT` 和 `IMAGE_BOX_BOTTOMRIGHT`, 定义文本框的大小.

依赖库安装: `pip install -r requirements.txt `

## 使用

使用文本编辑器打开 `config.py` 即可看到方便修改的参数，可以设置热键，图片路径，字体路径等

运行 `main.py` 即可开始监听回车，按下回车会自动拦截按键，生成图片后自动发送 (自动发送功能可以在config.py中关闭)。

如果发送失败等可以尝试适当增大 `config.py` 第46行的 `DELAY`

详细教程: https://www.bilibili.com/opus/1131995010930049048

## 关于 MacOS 系统的说明

> 此处 MacOS 的测试环境为 MacOS Tahoe 26.0.1

如果你在 MacOS 下使用需要使用管理员权限（sudo）运行。 

另外，MacOS 由于安全限制，使用了与 Windows 系统下不同的实现。经测试在 QQ 等软件中修饰键和回车一起输入时回车会被吃掉，请自行设置其他快捷键。

在使用中文输入法时偶尔会触发输入法而调用图片生成的情况，该 bug 目前还未解决，一般重试即可，不影响正常使用。

## 关于 Linux 系统的说明

> 此处 Linux 的测试环境为 Arch Linux with Gnome (Wayland)

写了一下午没有一个能跑动的版本，先咕咕了。等大佬来做吧（摆烂）。

## 另外的分支
[增加了表情差分功能的分支, 暂不支持图片的插入](https://github.com/WrightHua/Anan-s-Sketchbook-Chat-Box/tree/main)