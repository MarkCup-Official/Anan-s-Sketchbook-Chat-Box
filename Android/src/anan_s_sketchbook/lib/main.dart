import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Sketchbook Chat Box',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const MyHomePage(),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key});

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  final TextEditingController _textController = TextEditingController();
  String _selectedEmotion = "普通";
  bool _isGenerating = false;
  Uint8List? _generatedImageBytes;

  final Rect _textArea = const Rect.fromLTWH(119, 450, 279, 175);

  // 字体配置
  final String _fontFamily = 'AppFont';

  // 表情映射
  final Map<String, String> _emotionMap = {
    "普通": "assets/BaseImages/base.png",
    "开心": "assets/BaseImages/开心.png",
    "生气": "assets/BaseImages/生气.png",
    "无语": "assets/BaseImages/无语.png",
    "脸红": "assets/BaseImages/脸红.png",
    "病娇": "assets/BaseImages/病娇.png",
    "闭眼": "assets/BaseImages/闭眼.png",
    "难受": "assets/BaseImages/难受.png",
    "害怕": "assets/BaseImages/害怕.png",
    "激动": "assets/BaseImages/激动.png",
    "惊讶": "assets/BaseImages/惊讶.png",
    "哭泣": "assets/BaseImages/哭泣.png",
  };

  final String _overlayImage = "assets/BaseImages/base_overlay.png";
  final bool _useOverlay = true;

  Future<ui.Image> _loadImage(String assetPath) async {
    final ByteData data = await rootBundle.load(assetPath);
    final Completer<ui.Image> completer = Completer();
    ui.decodeImageFromList(Uint8List.view(data.buffer), (ui.Image img) {
      completer.complete(img);
    });
    return completer.future;
  }

  TextSpan _buildTextSpan(String text, double fontSize) {
    final List<InlineSpan> children = [];
    final RegExp exp = RegExp(r'([【\[].*?[】\]])'); // 匹配中括号内容

    text.splitMapJoin(
      exp,
      onMatch: (m) {
        children.add(
          TextSpan(
            text: m.group(0),
            style: TextStyle(
              color: const Color.fromARGB(255, 128, 0, 128),
              fontSize: fontSize,
              fontFamily: _fontFamily,
            ),
          ),
        );
        return m.group(0)!;
      },
      onNonMatch: (n) {
        // 普通文本
        children.add(
          TextSpan(
            text: n,
            style: TextStyle(
              color: Colors.black,
              fontSize: fontSize,
              fontFamily: _fontFamily,
            ),
          ),
        );
        return n;
      },
    );

    return TextSpan(children: children);
  }

  Future<void> _generateImage() async {
    if (_textController.text.isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('请输入一些文字')));
      return;
    }

    setState(() {
      _isGenerating = true;
      _generatedImageBytes = null;
    });

    try {
      // 准备画布
      final ui.PictureRecorder recorder = ui.PictureRecorder();

      // 加载底图
      final String bgPath = _emotionMap[_selectedEmotion] ?? _emotionMap["普通"]!;
      final ui.Image bgImage = await _loadImage(bgPath);

      final Canvas canvas = Canvas(recorder);

      // 绘制底图
      canvas.drawImage(bgImage, Offset.zero, Paint());

      // 计算字号
      double minSize = 10.0;
      double maxSize = 100.0;
      double bestSize = minSize;

      // 二分查找合适的字号

      double currentSize = maxSize;
      TextPainter? bestPainter;

      while (currentSize >= minSize) {
        final TextSpan span = _buildTextSpan(_textController.text, currentSize);
        final TextPainter painter = TextPainter(
          text: span,
          textAlign: TextAlign.center,
          textDirection: TextDirection.ltr,
        );

        painter.layout(maxWidth: _textArea.width);

        if (painter.height <= _textArea.height) {
          bestSize = currentSize;
          bestPainter = painter;
          break; // 找到了最大的能放下的
        }

        currentSize -= 2.0;
      }

      // default
      if (bestPainter == null) {
        final TextSpan span = _buildTextSpan(_textController.text, minSize);
        bestPainter = TextPainter(
          text: span,
          textAlign: TextAlign.center,
          textDirection: TextDirection.ltr,
        );
        bestPainter.layout(maxWidth: _textArea.width);
      }

      final double x =
          _textArea.left + (_textArea.width - bestPainter.width) / 2;
      final double y =
          _textArea.top + (_textArea.height - bestPainter.height) / 2;

      bestPainter.paint(canvas, Offset(x, y));

      //绘制 Overlay
      if (_useOverlay) {
        try {
          final ui.Image overlayImg = await _loadImage(_overlayImage);
          canvas.drawImage(overlayImg, Offset.zero, Paint());
        } catch (e) {
          print("Overlay image not found or failed to load: $e");
        }
      }

      //生成图片
      final ui.Picture picture = recorder.endRecording();
      final ui.Image finalImage = await picture.toImage(
        bgImage.width,
        bgImage.height,
      );
      final ByteData? byteData = await finalImage.toByteData(
        format: ui.ImageByteFormat.png,
      );

      if (byteData != null) {
        final Uint8List pngBytes = byteData.buffer.asUint8List();

        setState(() {
          _generatedImageBytes = pngBytes;
        });
      }
    } catch (e) {
      print(e);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('生成失败: $e')));
      }
    } finally {
      if (mounted) {
        setState(() {
          _isGenerating = false;
        });
      }
    }
  }

  Future<void> _shareImage() async {
    if (_generatedImageBytes == null) return;

    try {
      // 保存到临时文件并分享
      final tempDir = await getTemporaryDirectory();
      final file = await File(
        '${tempDir.path}/sketchbook_share.png',
      ).create();
      await file.writeAsBytes(_generatedImageBytes!);

      // 分享
      await Share.shareXFiles([XFile(file.path)], text: 'Anan Sketchbook');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('分享失败: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sketchbook Chat Box'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 预览区域
            Container(
              height: 300,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey),
                color: Colors.grey[200],
              ),
              child: _generatedImageBytes != null
                  ? Image.memory(_generatedImageBytes!, fit: BoxFit.contain)
                  : const Center(child: Text('预览区域')),
            ),
            const SizedBox(height: 20),

            // 表情选择
            DropdownButtonFormField<String>(
              initialValue: _selectedEmotion,
              decoration: const InputDecoration(
                labelText: '选择表情',
                border: OutlineInputBorder(),
              ),
              items: _emotionMap.keys.map((String key) {
                return DropdownMenuItem<String>(value: key, child: Text(key));
              }).toList(),
              onChanged: (String? newValue) {
                if (newValue != null) {
                  setState(() {
                    _selectedEmotion = newValue;
                  });
                }
              },
            ),
            const SizedBox(height: 20),

            // 文本输入
            TextField(
              controller: _textController,
              maxLines: 5,
              decoration: const InputDecoration(
                labelText: '输入文字',
                hintText: '在这里输入你想说的话... 使用【】包含的内容会变色哦',
                border: OutlineInputBorder(),
              ),
              onChanged: (text) {
                for (var key in _emotionMap.keys) {
                  if (text.contains("#$key#")) {
                    setState(() {
                      _selectedEmotion = key;
                    });
                    break;
                  }
                }
              },
            ),
            const SizedBox(height: 20),

            // 生成按钮
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isGenerating ? null : _generateImage,
                    icon: _isGenerating
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.image),
                    label: Text(_isGenerating ? '生成中...' : '生成图片'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed:
                        _generatedImageBytes == null ? null : _shareImage,
                    icon: const Icon(Icons.share),
                    label: const Text('分享图片'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
