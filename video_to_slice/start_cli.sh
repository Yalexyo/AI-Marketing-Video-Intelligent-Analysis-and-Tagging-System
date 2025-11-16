#!/bin/bash

# AI Video Master 5.0 启动脚本

echo "🎬 AI Video Master 5.0 - 启动中..."

# 检查Python版本
if ! python3 --version >/dev/null 2>&1; then
    echo "❌ 错误: 未找到Python3，请先安装Python 3.10+"
    exit 1
fi

# 检查UV工具
if command -v uv >/dev/null 2>&1; then
    echo "✅ 使用UV运行程序..."
    uv run python video_cli.py
else
    echo "⚠️  UV未找到，使用标准Python..."
    # 激活虚拟环境（如果存在）
    if [ -d ".venv" ]; then
        echo "🔧 激活虚拟环境..."
        source .venv/bin/activate
    fi
    python3 video_cli.py
fi
