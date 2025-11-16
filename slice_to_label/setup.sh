#!/bin/bash

# slice_to_label UV环境设置脚本
# 严格按照项目UV规则配置

set -e

PROJECT_NAME="slice-to-label"
PROJECT_DIR="$(dirname "$0")"

echo "🎯 开始配置 ${PROJECT_NAME} UV环境..."

# 检查UV是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ UV未安装，请先安装UV:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 进入项目目录
cd "${PROJECT_DIR}"

echo "📁 当前工作目录: $(pwd)"

# 检查pyproject.toml是否存在
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml 文件不存在，请先创建"
    exit 1
fi

# 创建虚拟环境
echo "🔧 创建UV虚拟环境..."
uv venv --python 3.10

# 安装依赖
echo "📦 安装项目依赖..."
uv pip install -e .

# 安装开发依赖
echo "🛠️ 安装开发依赖..."
uv pip install -e ".[dev]"

# 创建必要的目录
echo "📁 创建项目目录结构..."
mkdir -p data/input
mkdir -p data/output  
mkdir -p results
mkdir -p cache
mkdir -p temp
mkdir -p logs

# 创建.env文件（如果不存在）
if [ ! -f ".env" ]; then
    echo "📝 创建.env配置文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件并填入您的API密钥"
fi

# 设置权限
chmod +x batch_slice_to_label.py

echo "✅ ${PROJECT_NAME} UV环境配置完成！"
echo ""
echo "🚀 使用方法："
echo "   source .venv/bin/activate  # 激活环境"
echo "   uv run python batch_slice_to_label.py --help  # 查看帮助"
echo ""
echo "📝 下一步："
echo "   1. 编辑 .env 文件，填入API密钥"
echo "   2. 将视频文件放入 data/input/ 目录"
echo "   3. 运行分析命令" 