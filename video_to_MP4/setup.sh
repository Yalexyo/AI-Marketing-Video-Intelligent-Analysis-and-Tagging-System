#!/bin/bash
# Video to MP4 Converter 安装脚本

set -e

echo "🚀 Video to MP4 Converter 安装脚本"
echo "=================================="

# 检查 Python 版本
echo "📋 检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python 版本检查通过: $python_version"
else
    echo "❌ Python 版本不符合要求 (需要 >= 3.10, 当前: $python_version)"
    exit 1
fi

# 检查 FFmpeg
echo "📋 检查 FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    ffmpeg_version=$(ffmpeg -version 2>&1 | head -n 1 | awk '{print $3}')
    echo "✅ FFmpeg 已安装: $ffmpeg_version"
else
    echo "❌ FFmpeg 未找到，请先安装 FFmpeg"
    echo ""
    echo "安装方法:"
    echo "  macOS:   brew install ffmpeg"
    echo "  Ubuntu:  sudo apt update && sudo apt install ffmpeg"
    echo "  CentOS:  sudo yum install ffmpeg"
    echo ""
    exit 1
fi

# 检查 UV 包管理器
echo "📋 检查 UV 包管理器..."
if command -v uv &> /dev/null; then
    uv_version=$(uv --version 2>&1 | awk '{print $2}')
    echo "✅ UV 已安装: $uv_version"
else
    echo "📦 安装 UV 包管理器..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    
    if command -v uv &> /dev/null; then
        echo "✅ UV 安装成功"
    else
        echo "❌ UV 安装失败，请手动安装"
        echo "请访问: https://github.com/astral-sh/uv"
        exit 1
    fi
fi

# 创建虚拟环境
echo "🔧 创建虚拟环境..."
if [ -d ".venv" ]; then
    echo "虚拟环境已存在，跳过创建"
else
    uv venv
    echo "✅ 虚拟环境创建成功"
fi

# 激活虚拟环境并安装依赖
echo "📦 安装项目依赖..."
source .venv/bin/activate

# 使用 UV 安装依赖
uv pip install -e .

echo "✅ 依赖安装完成"

# 创建必要的目录
echo "📁 创建必要目录..."
mkdir -p data/{input,output,temp}
mkdir -p logs
mkdir -p cache

echo "✅ 目录创建完成"

# 复制配置文件
echo "⚙️  设置配置文件..."
if [ ! -f "config/env_config.txt" ]; then
    cp config/config.example.env config/env_config.txt
    echo "✅ 配置文件已创建: config/env_config.txt"
else
    echo "配置文件已存在，跳过创建"
fi

# 运行测试
echo "🧪 运行基础测试..."
python3 -c "
import sys
sys.path.insert(0, 'src')
from src.utils import check_ffmpeg
from src.config_manager import ConfigManager

# 测试 FFmpeg
if check_ffmpeg():
    print('✅ FFmpeg 功能测试通过')
else:
    print('❌ FFmpeg 功能测试失败')
    sys.exit(1)

# 测试配置管理
try:
    config_manager = ConfigManager()
    config = config_manager.get_config()
    print('✅ 配置管理测试通过')
except Exception as e:
    print(f'❌ 配置管理测试失败: {e}')
    sys.exit(1)

print('🎉 所有基础测试通过!')
"

if [ $? -eq 0 ]; then
    echo "🎉 安装完成!"
    echo ""
    echo "使用方法:"
    echo "  # 激活环境"
    echo "  source .venv/bin/activate"
    echo ""
    echo "  # 转换单个文件"
    echo "  python run.py --input video.avi --output ./output/"
    echo ""
    echo "  # 批量转换目录"
    echo "  python run.py --input ./videos/ --output ./converted/"
    echo ""
    echo "  # 查看帮助"
    echo "  python run.py --help"
    echo ""
    echo "配置文件: config/env_config.txt"
    echo "日志目录: logs/"
    echo ""
else
    echo "❌ 安装过程中出现错误"
    exit 1
fi 