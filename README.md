# 安安的素描本聊天框

本项目fork自https://github.com/MarkCup-Official/Anan-s-Sketchbook-Chat-Box，请支持原作者大佬

本项目只做了略微改动，低技术力轻喷

## 修改声明

本项目相比原项目，增加了更多差分（目前就新增了一种），支持使用时随机调用差分包，并支持调用响应的表情差分

<img src="https://github.com/RikinYoung/Anan-s-Sketchbook-Chat-Box-MoreAnan/blob/main/BaseImages1/base.png" width="300px">
<img src="https://github.com/RikinYoung/Anan-s-Sketchbook-Chat-Box-MoreAnan/blob/main/BaseImages2/base.png" width="300px">

## 部署

本项目只支持windows

其中`font.ttf`为字体文件, 可以自由修改成其他字体, 本项目不拥有字体版权, 仅做引用.

`base_overlay.png`为透明底的安安袖子, 用于防止文字和图片覆盖在袖子上方（本项目暂时默认禁用）. 如果分辨率不一样的安安图片, 需要修改`config.py`的 `TEXT_BOX_TOPLEFT` 和 `IMAGE_BOX_BOTTOMRIGHT`, 定义文本框的大小.


## 使用

先安装依赖库: `pip install -r requirements.txt `

使用文本编辑器打开`config.py`即可看到方便修改的参数, 可以设置热键, 图片路径, 字体路径, 指定的应用, 表情差分关键词等

运行`main.py`即可开始监听回车, 在指定应用中按下回车会自动拦截按键, 生成图片后自动发送 (自动发送功能可以在`config.py`中关闭).

特殊的, 在文本中输入\[\]或者【】, 被包裹的字符会变成紫色.

输入文本框中的图片也可以被直接绘制在素描本上.

输入`#普通#`, `#开心#`, `#生气#`, `#无语#`, `#脸红#`, `#病娇#`可以切换标签差分，不输入则为万能表情（默认表情）. 可以通过修改`BASEIMAGE_MAPPING`来增加更多查分

如果发送失败等可以尝试适当增大`main.py`第10行的`DELAY`