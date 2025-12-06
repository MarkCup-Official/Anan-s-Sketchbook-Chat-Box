#PR description
## Summary
使用 Flutter 实现了该项目的 Android 版本，用于更方便地在手机上发送夏目安安的图片
## how to test/use(Release)
下载Android/apk/下的apk并在手机上安装
## Feature
由于移动端难以实现操纵剪贴板等功能，替代实现如下：
- 先生成图片，然后点击分享可以分享到微信等应用，发送给朋友
## Directory Structure
- flutter project: Android/src/anan_s_sketchbook/
- main code: Android/src/anan_s_sketchbook/lib/
- config: Android/src/anan_s_sketchbook/pubspec.yaml
- built apk: Android/apk/
- assets（你需要自行放入图片，见build process）: Android/src/anan_s_sketchbook/assets/
## Build Process
如果您要自行进行构建请遵循以下步骤：
- 安装flutter并完成环境配置
- 在Android/src/anan_s_sketchbook/下新建assets/BaseImages文件夹并把原来BaseImages下的图片放进去
- 在Android/src/anan_s_sketchbook/下新建assets/fonts文件夹并把原来的font.ttf放进去
- 在Android/src/anan_s_sketchbook/下运行flutter pub get;flutter pub run flutter_launcher_icons;flutter build apk --release三个命令
- 在flutter指示的位置找到build完成的apk
