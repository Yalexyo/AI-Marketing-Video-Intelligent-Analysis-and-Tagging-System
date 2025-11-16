# Video to MP4 Converter

批量视频格式转换工具，支持将多种视频格式转换为 MP4 格式。

## 🚀 功能特性

- **多格式支持**: 支持 AVI, MOV, MKV, WMV, FLV, WEBM 等主流视频格式
- **批量处理**: 支持批量转换整个文件夹中的视频文件
- **并行转换**: 支持多线程并行处理，提高转换效率
- **进度显示**: 实时显示转换进度和状态
- **自定义配置**: 支持自定义输出质量、分辨率等参数
- **错误处理**: 完善的错误处理和日志记录

## 📋 系统要求

- Python 3.10+
- FFmpeg (系统需要安装 FFmpeg)

## 🛠️ 安装

### 1. 环境准备

确保系统已安装 FFmpeg：

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# 下载 FFmpeg 并添加到系统 PATH
```

### 2. 项目安装

```bash
# 克隆或进入项目目录
cd video_to_MP4

# 使用 UV 安装依赖
uv venv
source .venv/bin/activate  # macOS/Linux
uv pip install -e .
```

## 🎯 使用方法

### 基础用法

```bash
# 转换单个文件
python run.py --input /path/to/video.avi --output /path/to/output/

# 批量转换文件夹
python run.py --input /path/to/input_folder/ --output /path/to/output_folder/

# 指定转换质量
python run.py --input /path/to/input/ --output /path/to/output/ --quality high

# 并行处理（4个线程）
python run.py --input /path/to/input/ --output /path/to/output/ --workers 4
```

### 配置文件

复制并修改配置文件：

```bash
cp config/config.example.env config/env_config.txt
```

在 `config/env_config.txt` 中设置：
- 默认输出质量
- 并行处理线程数
- 日志级别等

### 支持的格式

**输入格式**: AVI, MOV, MKV, WMV, FLV, WEBM, M4V, 3GP, TS, MPG, MPEG
**输出格式**: MP4 (H.264 编码)

## 📁 项目结构

```
video_to_MP4/
├── src/                    # 核心源代码
│   ├── video_converter.py  # 视频转换核心逻辑
│   ├── batch_processor.py  # 批量处理管理器
│   ├── config_manager.py   # 配置管理
│   └── utils.py           # 工具函数
├── config/                # 配置文件
│   ├── env_config.txt     # 环境配置
│   └── converter_config.py # 转换器配置
├── data/                  # 数据目录
│   ├── input/            # 输入视频文件
│   ├── output/           # 输出 MP4 文件
│   └── temp/             # 临时文件
├── logs/                 # 日志文件
├── cache/                # 缓存文件
├── tests/                # 测试文件
├── run.py               # 主运行脚本
└── README.md            # 项目说明
```

## 🔧 高级用法

### 自定义转换参数

```python
from src.video_converter import VideoConverter

converter = VideoConverter(
    quality='high',           # 质量: low, medium, high, ultra
    resolution='1920x1080',   # 分辨率
    bitrate='2M',            # 比特率
    fps=30                   # 帧率
)

converter.convert_file('input.avi', 'output.mp4')
```

### 批量处理配置

```python
from src.batch_processor import BatchProcessor

processor = BatchProcessor(
    workers=4,              # 并行线程数
    skip_existing=True,     # 跳过已存在的文件
    preserve_structure=True # 保持目录结构
)

processor.process_directory('/input/', '/output/')
```

## 📊 性能优化

- **并行处理**: 根据 CPU 核心数调整 workers 参数
- **内存管理**: 大文件转换时会自动分段处理
- **缓存机制**: 避免重复转换相同文件
- **进度监控**: 实时显示转换状态和估计剩余时间

## 🐛 故障排除

### 常见问题

1. **FFmpeg 未找到**
   ```
   解决: 确保 FFmpeg 已安装并在 PATH 中
   ```

2. **转换失败**
   ```
   检查: 输入文件是否损坏，格式是否支持
   ```

3. **内存不足**
   ```
   调整: 减少并行线程数，或分批处理大文件
   ```

### 日志检查

查看详细日志：
```bash
tail -f logs/video_converter_$(date +%Y%m%d).log
```

## 📝 更新日志

- **v0.1.0**: 初始版本，支持基础视频格式转换

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## �� 许可证

MIT License 