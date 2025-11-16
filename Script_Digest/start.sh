#!/bin/bash
# Script Digest 启动脚本

echo "🎬 Script Digest - 视频脚本智能匹配系统"
echo "=========================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3"
    exit 1
fi

# 激活虚拟环境（如果存在）
if [ -d ".venv" ]; then
    echo "🔧 激活虚拟环境..."
    source .venv/bin/activate
fi

# 运行主程序
echo "🚀 启动 Script Digest..."
python3 run.py 