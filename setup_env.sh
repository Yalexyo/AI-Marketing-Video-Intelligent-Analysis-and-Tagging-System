#!/bin/bash
# 🚀 AI视频分析项目 - 环境设置脚本
# 一键设置所有子模块的Python环境和依赖

set -e  # 遇到错误立即退出

echo "🚀 AI视频分析项目环境设置"
echo "=" * 60

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "📁 项目目录: $PROJECT_ROOT"

# 检查uv是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ 错误: 未找到 uv 命令"
    echo "请先安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv 已安装: $(uv --version)"

# 定义所有子模块
MODULES=("label_to_classifier" "slice_to_label" "srt_to_product" "video_to_srt" "video_to_slice")

echo ""
echo "🔧 初始化子模块环境..."

for module in "${MODULES[@]}"; do
    if [ -d "$PROJECT_ROOT/$module" ]; then
        echo ""
        echo "📦 初始化模块: $module"
        echo "─" * 30
        
        cd "$PROJECT_ROOT/$module"
        
        # 检查是否有pyproject.toml
        if [ -f "pyproject.toml" ]; then
            echo "🔄 运行 uv sync..."
            if uv sync; then
                echo "✅ $module 环境初始化成功"
            else
                echo "❌ $module 环境初始化失败"
                exit 1
            fi
        else
            echo "⚠️  $module 没有 pyproject.toml 文件，跳过"
        fi
        
        cd "$PROJECT_ROOT"
    else
        echo "⚠️  模块目录不存在: $module"
    fi
done

echo ""
echo "🔧 检查.env文件..."

# 检查.env文件
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "⚠️  .env 文件不存在，创建模板文件..."
    
    # 尝试从现有配置中提取API密钥
    DEEPSEEK_KEY=""
    GOOGLE_KEY=""
    DASHSCOPE_KEY=""
    
    # 从slice_to_label配置提取
    if [ -f "$PROJECT_ROOT/slice_to_label/config/env_config.txt" ]; then
        DEEPSEEK_KEY=$(grep "DEEPSEEK_API_KEY=" "$PROJECT_ROOT/slice_to_label/config/env_config.txt" 2>/dev/null | cut -d'=' -f2- || echo "")
        GOOGLE_KEY=$(grep "GOOGLE_AI_API_KEY=" "$PROJECT_ROOT/slice_to_label/config/env_config.txt" 2>/dev/null | cut -d'=' -f2- || echo "")
        DASHSCOPE_KEY=$(grep "DASHSCOPE_API_KEY=" "$PROJECT_ROOT/slice_to_label/config/env_config.txt" 2>/dev/null | cut -d'=' -f2- || echo "")
    fi
    
    # 从feishu_pool配置提取
    if [ -f "$PROJECT_ROOT/feishu_pool/optimized_pool_config.json" ]; then
        FEISHU_APP_ID=$(grep -o '"app_id": "[^"]*"' "$PROJECT_ROOT/feishu_pool/optimized_pool_config.json" 2>/dev/null | cut -d'"' -f4 || echo "")
        FEISHU_APP_SECRET=$(grep -o '"app_secret": "[^"]*"' "$PROJECT_ROOT/feishu_pool/optimized_pool_config.json" 2>/dev/null | cut -d'"' -f4 || echo "")
        FEISHU_APP_TOKEN=$(grep -o '"app_token": "[^"]*"' "$PROJECT_ROOT/feishu_pool/optimized_pool_config.json" 2>/dev/null | cut -d'"' -f4 || echo "")
        
        if [ -z "$DEEPSEEK_KEY" ]; then
            DEEPSEEK_KEY=$(grep -o '"deepseek_api_key": "[^"]*"' "$PROJECT_ROOT/feishu_pool/optimized_pool_config.json" 2>/dev/null | cut -d'"' -f4 || echo "")
        fi
        
        OPENROUTER_KEY=$(grep -o '"openrouter_api_key": "[^"]*"' "$PROJECT_ROOT/feishu_pool/optimized_pool_config.json" 2>/dev/null | cut -d'"' -f4 || echo "")
    fi
    
    # 创建.env文件
    cat > "$PROJECT_ROOT/.env" << EOF
# AI视频分析项目 - 环境变量配置
# 请根据实际情况修改API密钥

# ========== AI模型API配置 ==========
DEEPSEEK_API_KEY=${DEEPSEEK_KEY:-your_deepseek_api_key_here}
OPENROUTER_API_KEY=${OPENROUTER_KEY:-your_openrouter_api_key_here}
GOOGLE_AI_API_KEY=${GOOGLE_KEY:-your_google_ai_api_key_here}
DASHSCOPE_API_KEY=${DASHSCOPE_KEY:-your_dashscope_api_key_here}

# ========== 飞书API配置 ==========
FEISHU_APP_ID=${FEISHU_APP_ID:-your_feishu_app_id}
FEISHU_APP_SECRET=${FEISHU_APP_SECRET:-your_feishu_app_secret}
FEISHU_APP_TOKEN=${FEISHU_APP_TOKEN:-your_feishu_app_token}

# ========== 阿里云OSS配置 ==========
OSS_ACCESS_KEY_ID=your_oss_access_key_id
OSS_ACCESS_KEY_SECRET=your_oss_access_key_secret
OSS_BUCKET_NAME=your_bucket_name
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
ENABLE_OSS=True

# ========== 其他配置 ==========
USE_ENHANCED_MAIN_TAG=false
MIN_CONFIDENCE_THRESHOLD=0.5
ENABLE_BACKUP=true
LOG_LEVEL=INFO
EOF
    
    echo "✅ 已创建 .env 模板文件"
    
    if [ -n "$DEEPSEEK_KEY" ] && [ "$DEEPSEEK_KEY" != "your_deepseek_api_key_here" ]; then
        echo "✅ 已自动填入现有的API密钥"
    else
        echo "⚠️  请编辑 .env 文件填入正确的API密钥"
    fi
else
    echo "✅ .env 文件已存在"
fi

echo ""
echo "🎉 环境设置完成！"
echo ""
echo "📖 下一步操作："
echo "1. 检查并编辑 .env 文件中的API密钥"
echo "2. 检查配置状态: ./auto_env.sh"
echo "3. 开始使用: 直接运行各功能脚本（已自动加载环境变量）"
echo ""
echo "💡 使用示例："
echo "   ./视频切片.sh              # 视频智能切片"
echo "   ./视频标签.sh              # AI标签分析"
echo "   ./视频分类.sh              # 主标签分类" 