# Video to MP4 Converter - 快速开始指南

## 🚀 5分钟快速开始

### 1. 安装依赖

```bash
# 运行安装脚本（自动检查环境、安装依赖）
./setup.sh
```

**或者手动安装：**

```bash
# 确保已安装 FFmpeg
brew install ffmpeg  # macOS
# sudo apt install ffmpeg  # Ubuntu

# 创建虚拟环境
uv venv
source .venv/bin/activate

# 安装依赖
uv pip install -e .
```

### 2. 准备视频文件

```bash
# 将待转换视频放入 data/input/ 目录
cp /path/to/your/videos/* data/input/
```

### 3. 开始转换

```bash
# 基础转换（默认中等质量）
python run.py --input data/input/ --output data/output/

# 高质量转换
python run.py --input data/input/ --output data/output/ --quality high

# 并行处理（4线程）
python run.py --input data/input/ --output data/output/ --workers 4
```

## 📋 支持的视频格式

**输入格式**: AVI, MOV, MKV, WMV, FLV, WEBM, M4V, 3GP, TS, MPG, MPEG, MTS, M2TS

**输出格式**: MP4 (H.264编码)

## ⚙️ 常用参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--quality` | 转换质量 | `low`, `medium`, `high`, `ultra` |
| `--workers` | 并行线程数 | `1-8` |
| `--resolution` | 输出分辨率 | `1920x1080`, `1280x720` |
| `--bitrate` | 视频比特率 | `2M`, `1000k` |
| `--fps` | 输出帧率 | `30`, `60` |
| `--skip-existing` | 跳过已存在文件 | 无需参数值 |
| `--dry-run` | 预览模式 | 无需参数值 |

## 🔧 配置文件

编辑 `config/env_config.txt` 自定义默认设置：

```bash
# 修改默认质量
DEFAULT_QUALITY=high

# 调整并行线程数
DEFAULT_WORKERS=4

# 启用硬件加速（如果支持）
USE_HARDWARE_ACCELERATION=true
```

## 📁 项目结构

```
video_to_MP4/
├── data/
│   ├── input/          # 输入视频文件
│   ├── output/         # 转换后的MP4文件
│   └── temp/           # 临时文件
├── logs/               # 日志文件
├── config/             # 配置文件
├── src/                # 核心代码
└── run.py             # 主程序
```

## 🎯 使用示例

### 批量转换目录

```bash
# 将 ~/Movies/ 中的所有视频转换为MP4
python run.py --input ~/Movies/ --output ~/Converted/ --quality high --workers 4
```

### 转换单个文件

```bash
# 转换单个文件
python run.py --input video.avi --output ./converted/
```

### 自定义分辨率和比特率

```bash
# 转换为720p，2Mbps比特率
python run.py --input data/input/ --output data/output/ --resolution 1280x720 --bitrate 2M
```

### 预览模式

```bash
# 查看将要处理的文件，不实际转换
python run.py --input data/input/ --output data/output/ --dry-run
```

## 🐛 问题排查

### FFmpeg 未找到
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg
```

### 内存不足
```bash
# 减少并行线程数
python run.py --input data/input/ --output data/output/ --workers 1
```

### 转换失败
```bash
# 查看详细日志
tail -f logs/video_converter_$(date +%Y%m%d).log
```

## 📊 性能参考

| 质量等级 | 文件大小 | 转换速度 | 适用场景 |
|----------|----------|----------|----------|
| `low` | 最小 | 最快 | 快速预览 |
| `medium` | 适中 | 较快 | 日常使用 |
| `high` | 较大 | 较慢 | 高质量需求 |
| `ultra` | 最大 | 最慢 | 专业用途 |

## 💡 小贴士

1. **硬件加速**: 在配置文件中启用硬件加速可显著提升转换速度
2. **批量处理**: 使用多线程处理可充分利用CPU资源
3. **存储空间**: 转换前确保有足够的磁盘空间
4. **文件备份**: 建议在转换前备份重要视频文件

---

更多详细信息请查看 [README.md](README.md) 