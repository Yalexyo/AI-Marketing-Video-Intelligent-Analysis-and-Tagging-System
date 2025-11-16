#!/bin/bash
# 🔧 AI视频分析项目 - 自动环境变量检查和加载脚本
# 一键检查环境变量配置状态，无需手动source
# 用法: ./auto_env.sh 或 source auto_env.sh

echo "🔧 AI视频分析项目 - 自动环境变量检查"
echo "=" * 50

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# 检查.env文件是否存在
ENV_FILE="$PROJECT_ROOT/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env 文件不存在"
    echo "💡 请先运行: ./setup_env.sh 创建环境配置"
    exit 1
fi

echo "📁 检查环境变量配置状态..."

# 临时加载环境变量进行检查（不影响当前shell）
(
    set -a
    source "$ENV_FILE" 2>/dev/null
    set +a
    
    echo ""
    echo "🔍 API密钥配置状态:"
    
    # 检查各个API密钥
    api_count=0
    
    if [ -n "$DEEPSEEK_API_KEY" ] && [ "$DEEPSEEK_API_KEY" != "your_deepseek_api_key_here" ]; then
        echo "✅ DEEPSEEK_API_KEY: 已配置"
        ((api_count++))
    else
        echo "❌ DEEPSEEK_API_KEY: 未配置或为默认值"
    fi
    
    if [ -n "$GOOGLE_AI_API_KEY" ] && [ "$GOOGLE_AI_API_KEY" != "your_google_ai_api_key_here" ]; then
        echo "✅ GOOGLE_AI_API_KEY: 已配置"
        ((api_count++))
    else
        echo "❌ GOOGLE_AI_API_KEY: 未配置或为默认值"
    fi
    
    if [ -n "$DASHSCOPE_API_KEY" ] && [ "$DASHSCOPE_API_KEY" != "your_dashscope_api_key_here" ]; then
        echo "✅ DASHSCOPE_API_KEY: 已配置"
        ((api_count++))
    else
        echo "❌ DASHSCOPE_API_KEY: 未配置或为默认值"
    fi
    
    if [ -n "$OPENROUTER_API_KEY" ] && [ "$OPENROUTER_API_KEY" != "your_openrouter_api_key_here" ]; then
        echo "✅ OPENROUTER_API_KEY: 已配置"
        ((api_count++))
    else
        echo "⚠️  OPENROUTER_API_KEY: 未配置（可选）"
    fi
    
    if [ -n "$FEISHU_APP_ID" ] && [ "$FEISHU_APP_ID" != "your_feishu_app_id" ]; then
        echo "✅ FEISHU_APP_ID: 已配置"
        ((api_count++))
    else
        echo "⚠️  FEISHU_APP_ID: 未配置（可选）"
    fi
    
    if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo "✅ GOOGLE_APPLICATION_CREDENTIALS: 已配置 ($(basename "$GOOGLE_APPLICATION_CREDENTIALS"))"
        ((api_count++))
    else
        echo "⚠️  GOOGLE_APPLICATION_CREDENTIALS: 未配置（视频切片功能需要）"
    fi
    
    echo ""
    echo "📊 配置统计:"
    echo "  ✅ 已配置API: $api_count 个"
    
    if [ "$api_count" -ge 3 ]; then
        echo "  🎉 配置完整，可以运行所有功能"
    elif [ "$api_count" -ge 2 ]; then
        echo "  ✅ 基本配置完成，可以运行大部分功能"
    else
        echo "  ⚠️  配置不足，可能影响功能使用"
    fi
)

echo ""
echo "💡 使用说明:"
echo "  📋 所有脚本现已支持自动环境变量加载"
echo "  🚀 直接运行脚本即可，无需手动加载环境变量："
echo ""
echo "    ./视频切片.sh              # 视频智能切片"
echo "    ./视频标签.sh              # AI标签分析"
echo "    ./视频分类.sh              # 主标签分类"
echo "    ./视频切片_产品介绍.sh      # 产品介绍切片"
echo "    ./视频数据_飞书上传.sh      # 飞书数据上传"
echo ""
echo "✨ 改进说明:"
echo "  🔧 每个脚本都会自动检查和加载项目根目录的 .env 文件"
echo "  📁 优先使用项目统一环境变量配置"
echo "  🔄 无需每次手动运行 source load_env.sh"
echo ""

# 如果脚本被source执行，则加载环境变量到当前shell
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    echo "🔄 检测到source执行，正在加载环境变量到当前shell..."
    set -a
    source "$ENV_FILE"
    set +a
    echo "✅ 环境变量已加载到当前shell"
fi 