#!/bin/bash

# =============================================================================
# 🎯 AI视频二级副标签分析程序
# 功能：基于已有一级主标签，进行智能二级副标签细分聚类
# 作者：AI Video Master
# 版本：v2.0 - 专注二级副标签分析
# =============================================================================

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 设置脚本目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# 显示欢迎信息
show_welcome() {
    clear
    echo -e "${MAGENTA}"
    echo "════════════════════════════════════════════════════════════════"
    echo "🎯 AI视频二级副标签分析程序 v2.0"
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo -e "${CYAN}功能说明：${NC}"
    echo "  • 🔧 基于已有一级主标签进行二级细分聚类"
    echo "  • 🤖 使用双层AI架构（DeepSeek + Claude智能升级）"
    echo "  • 📊 为每个主类别提供4-6个专业子分类"
    echo "  • 📁 生成详细的聚类分析报告和CSV文件"
    echo "  • 🎯 支持批量处理和智能置信度过滤"
    echo ""
    echo -e "${YELLOW}二级副标签分类体系：${NC}"
    echo "  🌟 使用效果 → 营养健康、智能发育、安全保护、品质好消化、口感品味、成长标志"
    echo "  🍼 产品介绍 → 核心配方、品牌价值、产品特色、科学依据"
    echo "  🎁 促销机制 → 价格优势、限时活动、赠品套装、会员权益"
    echo "  🪝 钩子 → 问题场景、需求痛点、紧迫时机、决策困扰"
    echo ""
    echo -e "${YELLOW}💡 前置条件：必须先运行'视频分类_一级主标签.sh'完成一级分类${NC}"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
}

# 检查依赖环境
check_dependencies() {
    log_step "🔧 检查系统依赖..."
    
    # 检查uv是否安装
    if ! command -v uv &> /dev/null; then
        log_error "uv 未安装，请先安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    # 检查输入目录
    if [ ! -d "🎬Slice" ]; then
        log_error "🎬Slice 目录不存在，请先运行视频切片和标签程序"
        exit 1
    fi
    
    # 检查必要的模块目录
    if [ ! -d "label_to_classifier" ]; then
        log_error "label_to_classifier 模块目录不存在"
        exit 1
    fi
    
    # 检查已分类的JSON文件（必须有一级主标签）- 支持灵活的文件夹结构
    main_tag_count=$(find "🎬Slice" -name "*_analysis.json" -exec grep -l '"main_tag"' {} \; 2>/dev/null | wc -l)
    if [ "$main_tag_count" -eq 0 ]; then
        log_error "❌ 未找到已分类的一级主标签文件"
        log_error "请先运行 './视频分类_一级主标签.sh' 完成一级主标签分类"
        exit 1
    fi
    
    log_info "✅ 系统依赖检查通过"
    log_info "📋 发现 $main_tag_count 个已分类的一级主标签文件"
}

# 设置虚拟环境
setup_environment() {
    log_step "🔧 设置二级副标签分析环境..."
    
    cd label_to_classifier
    
    if [ ! -f "pyproject.toml" ]; then
        log_error "label_to_classifier 缺少 pyproject.toml 文件"
        exit 1
    fi
    
    # 同步依赖
    if uv sync --quiet; then
        log_info "✅ label_to_classifier 环境就绪"
    else
        log_error "❌ label_to_classifier 环境设置失败"
        exit 1
    fi
    
    cd ..
    log_info "✅ 二级副标签分析环境设置完成"
}

# 检查API配置（必需）
check_api_config() {
    log_step "🔧 检查API配置..."
    
    # 检查统一环境变量文件
    if [ ! -f ".env" ]; then
        log_error "❌ 项目根目录 .env 文件不存在"
        log_error "二级副标签分析功能必需API密钥，请创建 .env 文件并配置以下API密钥："
        log_error "1. DEEPSEEK_API_KEY=your_deepseek_api_key （主分析模型）"
        log_error "2. OPENROUTER_API_KEY=your_openrouter_api_key （升级模型，可选）"
        exit 1
    fi
    
    # 检查API密钥配置
    has_api_key=false
    api_keys_found=()
    
    # 检查DeepSeek API密钥（主要模型）
    if (grep -q "DEEPSEEK_API_KEY=" .env && ! grep -q "DEEPSEEK_API_KEY=$" .env); then
        log_info "  ✅ DeepSeek API密钥已配置（主分析模型）"
        has_api_key=true
        api_keys_found+=("DeepSeek")
    fi
    
    # 检查OpenRouter API密钥（升级模型，可选）
    if (grep -q "OPENROUTER_API_KEY=" .env && ! grep -q "OPENROUTER_API_KEY=$" .env); then
        log_info "  ✅ OpenRouter API密钥已配置（Claude升级模型）"
        api_keys_found+=("OpenRouter/Claude")
    else
        log_warn "  ⚠️ OpenRouter API密钥未配置，将只使用DeepSeek模型"
    fi
    
    if [ "$has_api_key" = false ]; then
        log_error "❌ 未检测到有效的主分析API密钥配置"
        log_error "二级副标签分析功能必需DeepSeek API密钥，请在项目根目录 .env 中配置："
        log_error "DEEPSEEK_API_KEY=your_deepseek_api_key"
        exit 1
    fi
    
    # 显示配置的API
    api_list=$(printf ", %s" "${api_keys_found[@]}")
    api_list=${api_list:2}  # 移除开头的", "
    log_info "✅ 二级副标签分析API配置检查通过 (已配置: $api_list)"
    
    # 智能升级机制提示
    if [[ " ${api_keys_found[@]} " =~ " OpenRouter/Claude " ]]; then
        log_info "🤖 双层AI架构：DeepSeek主模型 + Claude智能升级（严格模式）"
    else
        log_info "🤖 分析模式：使用DeepSeek单模型（建议配置OpenRouter获得智能升级）"
    fi
}

# 显示一级主标签统计
show_main_tag_stats() {
    log_step "📋 一级主标签分布统计："
    echo ""
    
    # 初始化类别计数
    effect_count=0      # 🌟 使用效果
    product_count=0     # 🍼 产品介绍  
    promo_count=0       # 🎁 促销机制
    hook_count=0        # 🪝 钩子
    total_classified=0
    
    # 统计各主标签数量 - 支持灵活的文件夹结构
    for json_file in $(find "🎬Slice" -name "*_analysis.json" 2>/dev/null); do
        if grep -q '"main_tag"' "$json_file" 2>/dev/null; then
            ((total_classified++))
            
            # 提取主标签并统计
            main_tag=$(grep '"main_tag"' "$json_file" | head -1 | sed 's/.*"main_tag": "\([^"]*\)".*/\1/')
            case "$main_tag" in
                *"使用效果"*) ((effect_count++)) ;;
                *"产品介绍"*) ((product_count++)) ;;
                *"促销机制"*) ((promo_count++)) ;;
                *"钩子"*) ((hook_count++)) ;;
            esac
        fi
    done
    
    echo -e "${CYAN}📊 一级主标签分布（待进行二级分析）：${NC}"
    if [ "$total_classified" -gt 0 ]; then
        if [ "$effect_count" -gt 0 ]; then
            percentage=$(echo "scale=1; $effect_count * 100 / $total_classified" | bc -l)
            echo "  🌟 使用效果: $effect_count 个 (${percentage}%) → 将细分为6个子类别"
        fi
        
        if [ "$product_count" -gt 0 ]; then
            percentage=$(echo "scale=1; $product_count * 100 / $total_classified" | bc -l)
            echo "  🍼 产品介绍: $product_count 个 (${percentage}%) → 将细分为4个子类别"
        fi
        
        if [ "$promo_count" -gt 0 ]; then
            percentage=$(echo "scale=1; $promo_count * 100 / $total_classified" | bc -l)
            echo "  🎁 促销机制: $promo_count 个 (${percentage}%) → 将细分为4个子类别"
        fi
        
        if [ "$hook_count" -gt 0 ]; then
            percentage=$(echo "scale=1; $hook_count * 100 / $total_classified" | bc -l)
            echo "  🪝 钩子: $hook_count 个 (${percentage}%) → 将细分为4个子类别"
        fi
    fi
    echo "  📊 总计: $total_classified 个已分类文件待进行二级分析"
    echo ""
}

# 用户确认
user_confirm() {
    # 检查自动模式
    if [ "$AUTO_MODE" = "true" ]; then
        log_info "🤖 自动模式：跳过用户确认，直接开始二级副标签分析"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  即将开始二级副标签分析，整个过程包括：${NC}"
    echo "  🎯 基于一级主标签进行智能二级细分聚类"
    echo "  🤖 双层AI架构：DeepSeek → Claude（严格模式，无回退）"
    echo "  📊 为每个主类别生成4-6个专业子分类"
    echo "  📁 生成详细的聚类报告和CSV文件"
    echo "  🎯 智能置信度过滤（min_confidence=0.5）"
    echo ""
    echo -e "${CYAN}🤖 双层AI架构机制：${NC}"
    echo "  🥇 主模型：DeepSeek Chat（快速精准）"
    echo "  🏆 升级模型：Claude 4 Sonnet（高精度验证）"
    echo "  📈 严格模式：DeepSeek失败→Claude处理→都失败则报错"
    echo "  🎯 置信度要求：≥0.5才接受分类结果"
    echo ""
    echo -e "${CYAN}📋 二级副标签分类预览：${NC}"
    echo "  🌟 使用效果 → 营养健康、智能发育、安全保护、品质好消化、口感品味、成长标志"
    echo "  🍼 产品介绍 → 核心配方、品牌价值、产品特色、科学依据"
    echo "  🎁 促销机制 → 价格优势、限时活动、赠品套装、会员权益"
    echo "  🪝 钩子 → 问题场景、需求痛点、紧迫时机、决策困扰"
    echo ""
    echo -e "${CYAN}🔧 处理策略：${NC}"
    echo "  ✅ 错误容忍模式：单个主标签失败不影响其他标签处理"
    echo "  🔄 智能重试机制：API失败自动重试（2次，超时3秒）"
    echo "  💰 成本优化：精简提示词，减少API调用"
    echo "  📊 详细统计：生成完整的分析报告和成功率统计"
    echo ""
    echo -e "${YELLOW}预计耗时：10-25分钟（取决于文件数量和API响应速度）${NC}"
    echo ""
    read -p "是否继续？(y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "用户取消操作"
        exit 0
    fi
}

# 执行二级副标签分析
execute_secondary_classification() {
    log_step "🎯 开始执行二级副标签分析..."
    echo ""
    
    cd label_to_classifier
    
    log_info "🤖 启动双层AI智能聚类系统..."
    
    # 执行AI聚类分析（仅分析模式，不复制文件）
    if uv run python run.py ai-cluster-analysis-only; then
        log_info "✅ 二级副标签AI分析完成，JSON文件已增强"
        log_info "💡 下一步：运行 './视频文件优化整理.sh' 进行文件整理"
        cd ..
        return 0
    else
        log_error "❌ 二级副标签分析失败"
        cd ..
        return 1
    fi
}



# 显示二级分类结果统计
show_secondary_results() {
    log_step "📊 二级副标签分析结果统计"
    echo ""
    
    echo -e "${CYAN}📈 二级副标签AI分析成果：${NC}"
    echo "  📊 JSON文件已增强：添加了二级分类字段 (仅增强模式，无结果目录)"
    echo ""
    
    # 统计各主标签的二级分类结果
    total_files=0
    total_secondary_enhanced=0
    
    echo -e "${CYAN}🏷️ JSON文件中的二级分析字段统计：${NC}"
    
    # 统计🌟 使用效果
    effect_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"main_tag".*"使用效果"' {} \; 2>/dev/null | wc -l)
    if [ "$effect_count" -gt 0 ]; then
        secondary_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"secondary_category"' {} \; -exec grep -l '"main_tag".*"使用效果"' {} \; 2>/dev/null | sort | uniq -d | wc -l)
        echo "  🌟 使用效果: $effect_count 个文件 (其中 $secondary_count 个已有二级分析)"
        total_files=$((total_files + effect_count))
        total_secondary_enhanced=$((total_secondary_enhanced + secondary_count))
    fi
    
    # 统计🍼 产品介绍
    product_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"main_tag".*"产品介绍"' {} \; 2>/dev/null | wc -l)
    if [ "$product_count" -gt 0 ]; then
        secondary_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"secondary_category"' {} \; -exec grep -l '"main_tag".*"产品介绍"' {} \; 2>/dev/null | sort | uniq -d | wc -l)
        echo "  🍼 产品介绍: $product_count 个文件 (其中 $secondary_count 个已有二级分析)"
        total_files=$((total_files + product_count))
        total_secondary_enhanced=$((total_secondary_enhanced + secondary_count))
    fi
    
    # 统计🎁 促销机制
    promo_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"main_tag".*"促销机制"' {} \; 2>/dev/null | wc -l)
    if [ "$promo_count" -gt 0 ]; then
        secondary_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"secondary_category"' {} \; -exec grep -l '"main_tag".*"促销机制"' {} \; 2>/dev/null | sort | uniq -d | wc -l)
        echo "  🎁 促销机制: $promo_count 个文件 (其中 $secondary_count 个已有二级分析)"
        total_files=$((total_files + promo_count))
        total_secondary_enhanced=$((total_secondary_enhanced + secondary_count))
    fi
    
    # 统计🪝 钩子
    hook_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"main_tag".*"钩子"' {} \; 2>/dev/null | wc -l)
    if [ "$hook_count" -gt 0 ]; then
        secondary_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"secondary_category"' {} \; -exec grep -l '"main_tag".*"钩子"' {} \; 2>/dev/null | sort | uniq -d | wc -l)
        echo "  🪝 钩子: $hook_count 个文件 (其中 $secondary_count 个已有二级分析)"
        total_files=$((total_files + hook_count))
        total_secondary_enhanced=$((total_secondary_enhanced + secondary_count))
    fi
    
    # 统计未分类文件
    other_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"main_tag".*"其他"' {} \; 2>/dev/null | wc -l)
    if [ "$other_count" -gt 0 ]; then
        echo "  🧫 其他/未分类: $other_count 个文件"
        total_files=$((total_files + other_count))
    fi
    
    echo ""
    echo -e "${CYAN}📊 二级分析统计：${NC}"
    echo "  📋 总一级分类文件: $total_files 个"
    echo "  🎯 已增强二级分析文件: $total_secondary_enhanced 个"
    if [ "$total_files" -gt 0 ]; then
        percentage=$(echo "scale=1; $total_secondary_enhanced * 100 / $total_files" | bc -l)
        echo "  📈 二级分析完成率: ${percentage}%"
    fi
    echo "  💾 JSON字段增强: secondary_category, secondary_confidence等"
    echo "  📁 下一步：运行 './视频分类_文件生成.sh' 生成最终文件结构"
    echo ""
}



# 显示后续操作建议
show_next_steps() {
    echo ""
    log_step "💡 下一步操作"
    echo ""
    echo -e "${CYAN}📁 生成最终文件结构：${NC}"
    echo "  🔄 运行: ./视频文件优化整理.sh"
    echo "  🎯 语义化命名: {二级标签}_{视频主题}.mp4"
    echo "  📂 扁平化结构: 直接在主标签下查找所需视频"
    echo ""
    echo -e "${CYAN}🔧 重新分析（如需要）：${NC}"
    echo "  🎯 仅重新二级分析: cd label_to_classifier && uv run python run.py ai-cluster-analysis-only"
echo "  📋 强制重新处理: cd label_to_classifier && uv run python run.py ai-cluster force"
    echo ""
    echo -e "${CYAN}📈 数据验证：${NC}"
    echo "  📝 检查JSON文件中的secondary_category字段"
    echo "  🎯 验证二级分类的置信度和合理性"
    echo ""
}

# 错误处理
handle_error() {
    log_error "二级副标签分析过程中发生错误"
    echo ""
    echo -e "${YELLOW}🔧 常见问题排查：${NC}"
    echo "  1. 检查是否已完成一级主标签分类"
    echo "  2. 检查网络连接是否正常"
    echo "  3. 检查API密钥配置是否正确"
    echo "  4. 检查磁盘空间是否充足"
    echo "  5. 确认DeepSeek API余额充足"
    echo ""
    echo -e "${CYAN}🔧 解决方案：${NC}"
    echo "  • 前置条件错误: 先运行 './视频分类_一级主标签.sh'"
    echo "  • API错误: 检查 .env 文件中的API密钥"
    echo "  • 网络错误: 检查防火墙和代理设置"
    echo "  • 内存不足: 关闭其他程序释放内存"
    echo ""
    read -p "按任意键退出..." -n 1 -r
    exit 1
}

# 主程序流程
main() {
    # 设置错误处理
    trap handle_error ERR
    
    # 执行步骤
    show_welcome
    check_dependencies
    setup_environment
    check_api_config
    show_main_tag_stats
    user_confirm
    
    echo ""
    log_step "🚀 开始执行二级副标签分析流程..."
    echo ""
    
    # 记录开始时间
    start_time=$(date +%s)
    
    # 执行处理流程
    if execute_secondary_classification; then
        # 记录结束时间
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        minutes=$((duration / 60))
        seconds=$((duration % 60))
        
        # 显示结果
        echo ""
        echo -e "${GREEN}🎉 二级副标签分析完成！${NC}"
        echo -e "${CYAN}⏱️  总耗时: ${minutes}分${seconds}秒${NC}"
        echo ""
        
        show_secondary_results
        show_next_steps
        
            echo ""
    log_info "🎯 二级副标签AI分析完成！JSON文件已增强，现在可以进行文件整理"
    log_info "📁 下一步：运行 './视频文件优化整理.sh' 生成最终文件结构"
    else
        echo ""
        log_error "❌ 二级副标签分析失败，请检查日志信息"
        echo ""
    fi
    
    echo ""
    if [ "$AUTO_MODE" != "true" ]; then
        read -p "按任意键退出..." -n 1 -r
    fi
}

# 运行主程序
main "$@" 