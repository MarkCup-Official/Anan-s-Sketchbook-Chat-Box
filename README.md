# 安安的素描本聊天框

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-windows-lightgrey)](https://en.wikipedia.org/wiki/Microsoft_Windows)
[![License](https://img.shields.io/github/license/Sheyiyuan/Anan-s-Sketchbook-Chat-Box)](LICENSE)

这是一个将你在文本输入框中输入的文字和图片绘制到夏目安安的素描本上的工具。它能够创建出与游戏内容类似的效果，适用于微信，QQ等聊天软件。

![演示效果](img/example.png)

## 功能特点

- 🎨 低存在感：资源占用极少，配置得当的情况下可以长时间放在后台
- 🖼️ 图片支持：可自动图片到素描本指定区域(暂时仅限一张)
- 😊 表情差分：支持多种表情底图切换，丰富表达方式
- ⌨️ 快捷键操作：通过热键快速切换表情和生成图片
- 🔧 高度可配置：几乎所有参数都可以通过配置文件自定义
- 🔄 自动发送：生成图像后可自动粘贴并发送消息
- 🎨 现代化界面：使用CustomTkinter构建的现代化用户界面

## 系统要求

- Windows 7 或更高版本（暂不支持 macOS/Linux）
- Python 3.8 或更高版本
- 依赖库详见 [requirements.txt](requirements.txt)

## 安装部署
教程视频 https://www.bilibili.com/video/BV16G1mBUECy  
文本教程 https://www.bilibili.com/opus/1131995010930049048
### 安装python以部署
1. 安装Python：下载并安装Python 3.8 或更高版本。已安装可跳过该步骤  
python官方下载地址：https://www.python.org/downloads/  
国内镜像：https://mirrors.tuna.tsinghua.edu.cn/python/  
直链下载链接：https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe  
镜像下载链接：https://mirrors.tuna.tsinghua.edu.cn/python/3.8.2/python-3.8.2-amd64.exe  
安装时勾选"添加 Python 到 PATH"  

2. 下载代码
点击绿色 Code 按钮，选择 Download Zip，等待下载完成
若下载速度过慢，可以使用 https://github.akams.cn/ 加速下载  

3. 安装依赖库  
按下 Win + R → 输入 cmd → 回车 打开cmd终端  
使用 cd 命令进入项目所在目录，例如：cd "D:\anan"  
确保此时cmd显示的路径是你之前解压的路径, 输入 ```pip install -r requirements.txt```  
此操作会自动安装所有依赖库

### 直接下载exe文件
1. 点击下载 [main.exe](https://github.com/HZBHZB1234/Anan-s-Sketchbook-Chat-Box-re/releases/tag/v1.0.0)  
可使用 https://github.akams.cn/ 加速下载 
### 使用git进行部署的方法此处不再赘述



## 使用方法

### 基本使用

1. 使用文本编辑器打开 [config.yaml](config.yaml) 配置相关参数
2. 运行主程序：
   ```bash
   python main.py
   ```
   若先前已经添加至PATH，双击 main.py 即可启动程序
3. 在聊天应用中输入文字或粘贴图片
4. 按下回车键（默认热键），程序将自动生成素描本图像并发送

### 表情差分切换

支持以下表情标签切换，一次切换持续有效：
- `#普通#`
- `#开心#`
- `#生气#`
- `#无语#`
- `#脸红#`
- `#病娇#`

也可通过 Alt+数字键快速切换：
- Alt+1: #普通#
- Alt+2: #开心#
- Alt+3: #生气#
- Alt+4: #无语#
- Alt+5: #脸红#
- Alt+6: #病娇#

### 特殊文本效果

在文本中输入 `[]` 或 `【】` 包裹的字符会变为紫色显示。

### 配置参数

主要可配置项包括：
- 热键设置（全局热键、表情切换热键等）
- 允许运行的进程列表（如 QQ、微信等）
- 文本框和图片框的坐标范围
- 自动粘贴和发送选项
- 延迟时间（如出现故障可适当增大）
- 字体文件路径
- 底图和遮罩图路径

详细配置说明请参见 [config.py](config.py) 文件。

## 故障排除

如果遇到以下问题，请尝试相应解决方案：

1. **图像发送失败**：尝试增大 [main.py](main.py) 中的 `DELAY` 值（默认为 0.1 秒）
2. **热键无效**：确保程序具有管理员权限运行
3. **特定应用不生效**：检查 `ALLOWED_PROCESSES` 配置是否包含目标应用进程名

## 许可证

本项目基于MIT协议传播，仅供个人学习交流使用，不拥有相关素材的版权。进行分发时应注意不违反素材版权与官方二次创造协定。

## 另附

本项目fork自 [Anan-s-Sketchbook-Chat-Box](https://github.com/MarkCup-Official/Anan-s-Sketchbook-Chat-Box)  

较原版本相比，添加了以下功能：
- 添加了快捷键切换表情
- 添加了release版本
---

如需在 macOS 或 Linux 上使用，请参考 [跨平台分支](https://github.com/Sheyiyuan/Anan-s-Sketchbook-Chat-Box)。