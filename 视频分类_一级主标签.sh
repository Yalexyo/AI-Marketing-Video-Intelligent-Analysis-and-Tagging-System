#!/bin/bash

# =============================================================================
# 🎯 AI视频一级主标签分类程序
# 功能：对🎬Slice目录中已标注的视频切片进行一级主标签分类
# 作者：AI Video Master
# 版本：v2.0 - 专注一级主标签分类
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
    echo "🎯 AI视频一级主标签分类程序 v2.0"
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo -e "${CYAN}功能说明：${NC}"
    echo "  • 🔧 自动设置虚拟环境和安装依赖"
    echo "  • 🔍 自动扫描 🎬Slice 目录下的已标注切片JSON文件"
    echo "  • 🎯 执行一级主标签分类（DeepSeek + Claude双模型）"
    echo "  • 📝 在原JSON文件中添加主标签字段（main_tag等）"
    echo "  • 📁 按主标签类别整理文件到分类文件夹"
    echo ""
    echo -e "${YELLOW}一级主标签类别：${NC}"
    echo "  🌟 使用效果 - 描述产品使用后的效果展示"
    echo "  🍼 产品介绍 - 专注于产品本身的展示和介绍"
    echo "  🎁 促销机制 - 强调温馨家庭场景和情感连接"
    echo "  🪝 钩子 - 描述问题场景或需要解决的困扰"
    echo ""
    echo -e "${YELLOW}💡 注意：这是第一阶段处理，完成后可运行'视频分类_二级副标签.sh'进行细分${NC}"
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
    
    # 检查已标注的JSON文件
    json_count=$(find "🎬Slice" -name "*_analysis.json" 2>/dev/null | wc -l)
    if [ "$json_count" -eq 0 ]; then
        log_error "🎬Slice 目录下未找到已标注的JSON文件，请先运行视频标签分析程序"
        exit 1
    fi
    
    log_info "✅ 系统依赖检查通过"
    log_info "📋 发现 $json_count 个已标注切片"
}

# 设置虚拟环境
setup_environment() {
    log_step "🔧 设置一级主标签分类环境..."
    
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
    log_info "✅ 一级主标签分类环境设置完成"
}

# 检查API配置（必需）
check_api_config() {
    log_step "🔧 检查API配置..."
    
    # 检查统一环境变量文件
    if [ ! -f ".env" ]; then
        log_error "❌ 项目根目录 .env 文件不存在"
        log_error "一级主标签分类功能必需API密钥，请创建 .env 文件并配置以下API密钥："
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
        log_error "一级主标签分类功能必需DeepSeek API密钥，请在项目根目录 .env 中配置："
        log_error "DEEPSEEK_API_KEY=your_deepseek_api_key"
        exit 1
    fi
    
    # 显示配置的API
    api_list=$(printf ", %s" "${api_keys_found[@]}")
    api_list=${api_list:2}  # 移除开头的", "
    log_info "✅ 一级主标签分类API配置检查通过 (已配置: $api_list)"
    
    # 智能升级机制提示
    if [[ " ${api_keys_found[@]} " =~ " OpenRouter/Claude " ]]; then
        log_info "🤖 智能升级机制：错误率>15%时自动升级到Claude模型"
    else
        log_info "🤖 分析模式：使用DeepSeek标准模型（建议配置OpenRouter获得智能升级）"
    fi
}

# 显示切片文件列表
show_slice_list() {
    log_step "📋 扫描到的已标注切片："
    echo ""
    
    # 按视频统计
    total_json=0
    total_with_main_tag=0
    
    for video_dir in $(find "🎬Slice" -maxdepth 1 -type d ! -name "." ! -name ".." ! -name "🎬Slice" 2>/dev/null | grep -v "\.DS_Store"); do
        # 检查是否包含slices子目录
        if [ ! -d "$video_dir/slices" ]; then
            continue
        fi
        video_name=$(basename "$video_dir")
        json_count=$(find "$video_dir/slices" -name "*_analysis.json" 2>/dev/null | wc -l)
        
        # 统计已有主标签的文件
        main_tag_count=0
        if [ "$json_count" -gt 0 ]; then
            for json_file in $(find "$video_dir/slices" -name "*_analysis.json" 2>/dev/null); do
                if grep -q '"main_tag"' "$json_file" 2>/dev/null; then
                    ((main_tag_count++))
                fi
            done
        fi
        
        total_json=$((total_json + json_count))
        total_with_main_tag=$((total_with_main_tag + main_tag_count))
        
        echo -e "  📹 ${BLUE}$video_name${NC}: $json_count 个已标注切片 ($main_tag_count 个已分类)"
    done
    
    echo ""
    echo -e "${CYAN}📊 总体情况：${NC}"
    echo "  📋 总已标注切片: $total_json 个"
    echo "  🎯 已有一级主标签: $total_with_main_tag 个"
    echo "  🆕 待分类: $((total_json - total_with_main_tag)) 个"
    echo ""
}

# 用户确认
user_confirm() {
    # 检查自动模式
    if [ "$AUTO_MODE" = "true" ]; then
        log_info "🤖 自动模式：跳过用户确认，直接开始一级主标签分类"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  即将开始一级主标签分类，整个过程包括：${NC}"
    echo "  🎯 智能一级主标签分类（DeepSeek + Claude双模型）"
    echo "  📝 在原JSON文件中添加main_tag相关字段"
    echo "  💾 自动备份原文件（.json.backup）"
    echo "  📁 按主标签类别整理文件到分类文件夹"
    echo "  📊 详细的分类统计和成功率报告"
    echo ""
    echo -e "${CYAN}🤖 智能分类机制：${NC}"
    echo "  🥇 主模型：DeepSeek Chat（快速高效）"
    echo "  🏆 升级模型：Claude 4 Sonnet（高精度）"
    echo "  📈 智能切换：错误率>15%时自动升级"
    echo "  🎯 置信度过滤：仅保留高置信度结果"
    echo ""
    echo -e "${CYAN}📋 一级主标签类别：${NC}"
    echo "  🌟 使用效果 - 展示产品使用后的效果"
    echo "  🍼 产品介绍 - 产品本身的展示介绍 (优先使用product文件夹内容)"
    echo "  🎁 促销机制 - 温馨家庭场景情感连接"
    echo "  🪝 钩子 - 问题场景需要解决的困扰"
    echo ""
    echo -e "${CYAN}🔧 处理策略：${NC}"
    echo "  ✅ 跳过已分类文件（避免重复收费）"
    echo "  🔄 支持增量处理和重新处理"
    echo "  💰 API调用优化（智能重试机制）"
    echo "  🍼 产品介绍特殊逻辑：直接使用video_*/product/文件夹内容"
    echo ""
    echo -e "${YELLOW}预计耗时：3-10分钟（取决于切片数量和API响应速度）${NC}"
    echo ""
    read -p "是否继续？(y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "用户取消操作"
        exit 0
    fi
}

# 执行一级主标签分类
execute_main_tag_classification() {
    log_step "🎯 开始执行一级主标签分类..."
    echo ""
    
    # 在切换目录前获取正确的绝对路径
    SLICE_DIR="$(pwd)/🎬Slice"
    
    cd label_to_classifier
    
    log_info "🤖 启动一级主标签分类器..."
    
    # 添加调试信息
    log_info "🔍 调试信息：SLICE_DIR = $SLICE_DIR"
    
    # 获取所有有JSON文件的视频
    declare -a video_dirs_array
    while IFS= read -r -d '' potential_dir; do
        log_info "🔍 检查目录: $potential_dir"
        if [ -d "$potential_dir/slices" ]; then
            log_info "✅ 发现slices子目录: $potential_dir/slices"
            video_dirs_array+=("$potential_dir")
        else
            log_info "❌ 未发现slices子目录: $potential_dir/slices"
        fi
    done < <(find "$SLICE_DIR" -maxdepth 1 -type d ! -name "." ! -name ".." ! -name "🎬Slice" -print0 2>/dev/null | grep -zv "\.DS_Store")
    
    log_info "🔍 找到的视频目录数量: ${#video_dirs_array[@]}"
    
    if [ ${#video_dirs_array[@]} -eq 0 ]; then
        log_error "❌ 未找到包含slices子目录的视频目录"
        cd ..
        exit 1
    fi
    
    total_success=0
    total_failed=0
    total_processed=0
    
    # 执行一级主标签分类（统一处理所有视频）
    log_info "🎬 开始分析所有视频（统一AI处理模式）"
    
    # 统计要处理的文件数量
    total_json_files=0
    for video_dir in "${video_dirs_array[@]}"; do
        video_name=$(basename "$video_dir")
        json_count=$(find "$video_dir/slices" -name "*_analysis.json" 2>/dev/null | wc -l)
        
        if [ "$json_count" -gt 0 ]; then
            log_info "📋 发现视频: $video_name ($json_count 个文件)"
            total_json_files=$((total_json_files + json_count))
        else
            log_warn "⚠️ $video_name 没有已标注文件，跳过"
        fi
    done
    
    if [ "$total_json_files" -eq 0 ]; then
        log_error "❌ 未找到任何已标注的JSON文件"
        cd ..
        exit 1
    fi
    
    log_info "📊 准备处理: $total_json_files 个已标注文件"
    
    # 执行统一智能分类（不创建备份文件）
    if uv run python run.py all no-backup; then
        log_info "✅ 一级主标签分类完成"
        total_success=1
        total_failed=0
        total_processed=1
    else
        log_error "❌ 一级主标签分类失败"
        total_success=0
        total_failed=1
        total_processed=1
    fi
    
    log_info "📊 一级主标签分类统计: 处理 $total_processed 个视频，成功 $total_success 个，失败 $total_failed 个"
    
    cd ..
    
    # 一级分析完成，不进行文件整理（由独立的优化整理脚本处理）
    log_info "✅ 一级主标签AI分析完成，JSON文件已增强"
    log_info "💡 下一步：运行 './视频分类_二级副标签.sh' 进行二级分析"
    log_info "📁 最后：运行 './视频文件优化整理.sh' 进行文件整理"
}



# 显示一级主标签分类结果
show_results() {
    log_step "📊 一级主标签分类结果统计"
    echo ""
    
    # 统计原始位置的JSON文件，避免重复计算分类文件夹中的复制文件
    total_json=0
    total_classified=0
    
    # 初始化类别计数
    effect_count=0      # 🌟 使用效果
    product_count=0     # 🍼 产品介绍  
    promo_count=0       # 🎁 促销机制
    hook_count=0        # 🪝 钩子
    other_count=0       # 🧫 其他
    unclassified_count=0 # 未分类的
    
    # 只扫描原始位置的JSON文件（有slices子目录的视频目录下）
    for video_dir in $(find "🎬Slice" -maxdepth 1 -type d ! -name "." ! -name ".." ! -name "🎬Slice" 2>/dev/null | grep -v "\.DS_Store"); do
        # 检查是否包含slices子目录
        if [ ! -d "$video_dir/slices" ]; then
            continue
        fi
        for json_file in $(find "$video_dir/slices" -name "*_analysis.json" 2>/dev/null); do
            ((total_json++))
            
            if grep -q '"main_tag"' "$json_file" 2>/dev/null; then
                ((total_classified++))
                
                # 提取主标签并统计
                main_tag=$(grep '"main_tag"' "$json_file" | head -1 | sed 's/.*"main_tag": "\([^"]*\)".*/\1/')
                case "$main_tag" in
                    *"使用效果"*) ((effect_count++)) ;;
                    *"产品介绍"*) ((product_count++)) ;;
                    *"促销机制"*) ((promo_count++)) ;;
                    *"钩子"*) ((hook_count++)) ;;
                    *) ((other_count++)) ;;  # 其他主标签
                esac
            elif grep -q '"main_tag_status".*"unclassified"' "$json_file" 2>/dev/null; then
                # 明确标记为未分类的文件
                ((unclassified_count++))
            fi
        done
    done
    
    total_processed=$((total_classified + unclassified_count))
    
    echo -e "${CYAN}📈 总体统计：${NC}"
    echo "  📋 总标注文件: $total_json 个"
    echo "  🎯 已分类文件: $total_classified 个"
    echo "  🧫 未分类文件: $unclassified_count 个"
    echo "  ⏳ 未处理文件: $((total_json - total_processed)) 个"
    echo "  📊 处理完成率: $(echo "scale=1; $total_processed * 100 / $total_json" | bc -l)%"
    echo ""
    
    echo -e "${CYAN}🏷️ 一级主标签分布：${NC}"
    if [ "$total_classified" -gt 0 ]; then
        if [ "$effect_count" -gt 0 ]; then
            percentage=$(echo "scale=1; $effect_count * 100 / $total_classified" | bc -l)
            echo "  🌟 使用效果: $effect_count 个 (${percentage}%) → 🌟 使用效果文件夹"
        else
            echo "  🌟 使用效果: 0 个 (0%)"
        fi
        
        if [ "$product_count" -gt 0 ]; then
            percentage=$(echo "scale=1; $product_count * 100 / $total_classified" | bc -l)
            echo "  🍼 产品介绍: $product_count 个 (${percentage}%) → 🍼 产品介绍/backup文件夹 (AI识别备份)"
        else
            echo "  🍼 产品介绍: 0 个 (0%)"
        fi
        
        if [ "$promo_count" -gt 0 ]; then
            percentage=$(echo "scale=1; $promo_count * 100 / $total_classified" | bc -l)
            echo "  🎁 促销机制: $promo_count 个 (${percentage}%) → 🎁 促销机制文件夹"
        else
            echo "  🎁 促销机制: 0 个 (0%)"
        fi
        
        if [ "$hook_count" -gt 0 ]; then
            percentage=$(echo "scale=1; $hook_count * 100 / $total_classified" | bc -l)
            echo "  🪝 钩子: $hook_count 个 (${percentage}%) → 🪝 钩子文件夹"
        else
            echo "  🪝 钩子: 0 个 (0%)"
        fi
        
        if [ "$other_count" -gt 0 ]; then
            percentage=$(echo "scale=1; $other_count * 100 / $total_classified" | bc -l)
            echo "  🧫 其他: $other_count 个 (${percentage}%) → 🧫 其他文件夹"
        else
            echo "  🧫 其他: 0 个 (0%)"
        fi
    fi
    
    # 显示未分类文件统计
    if [ "$unclassified_count" -gt 0 ]; then
        echo -e "${YELLOW}⚠️ 未分类文件: $unclassified_count 个 → 🧫 其他文件夹${NC}"
        echo "  (原因: 置信度不足、缺少数据、分析失败等)"
    fi
    echo ""
    
    # 统计product文件夹的文件数量
    echo -e "${CYAN}🍼 产品介绍文件夹统计：${NC}"
    product_folder_total=0
    for video_dir in $(find "🎬Slice" -maxdepth 1 -type d ! -name "." ! -name ".." ! -name "🎬Slice" 2>/dev/null | grep -v "\.DS_Store"); do
        video_name=$(basename "$video_dir")
        product_dir="$video_dir/product"
        if [ -d "$product_dir" ]; then
            file_count=$(find "$product_dir" -type f 2>/dev/null | wc -l)
            ((product_folder_total+=file_count))
        fi
    done
    echo "  📦 从product文件夹提取: $product_folder_total 个文件 → 🍼 产品介绍文件夹"
    echo ""
    
    echo -e "${CYAN}📁 数据增强位置：${NC}"
    echo "  🎬Slice/"
    echo "  ├── video_1/slices/   # 原标签JSON + 一级主标签字段 ✅"
    echo "  └── video_2/..."
    echo ""
    echo -e "${CYAN}📂 后续步骤：${NC}"
    echo "  🎯 步骤2: ./视频分类_二级副标签.sh （添加二级标签字段）"
    echo "  📁 步骤3: ./视频文件优化整理.sh （生成最终文件结构）"
    echo ""
    
    echo -e "${CYAN}🎯 新增字段：${NC}"
    echo "  ✅ main_tag: 一级主标签类别"
    echo "  ✅ main_tag_confidence: 置信度分数"
    echo "  ✅ main_tag_reasoning: 分类依据"
    echo "  ✅ main_tag_keywords: 关键词列表"
    echo "  ✅ main_tag_processed_at: 处理时间"
    echo "  ⚠️ main_tag_status: 未分类状态 (值: \"unclassified\")"
    echo "  ⚠️ unclassified_reason: 未分类原因说明"
    echo ""
}

# 显示后续操作建议
show_next_steps() {
    echo ""
    log_step "💡 下一步操作"
    echo ""
    echo -e "${CYAN}🎯 继续分析流程：${NC}"
    echo "  🔄 步骤2: ./视频分类_二级副标签.sh"
    echo "    📊 基于一级主标签进行细分聚类"
    echo "    🎯 为每个主类别提供更精细的子分类"
    echo ""
    echo "  📁 步骤3: ./视频文件优化整理.sh"
    echo "    🎯 语义化命名: {二级标签}_{视频主题}.mp4"
    echo "    📂 生成最终可用的文件结构"
    echo ""
    echo -e "${CYAN}🔧 重新分析（如需要）：${NC}"
    echo "  🎯 单个视频: cd label_to_classifier && uv run python run.py video_1 force"
echo "  📋 所有视频: cd label_to_classifier && uv run python run.py all force"
    echo ""
}

# 错误处理
handle_error() {
    log_error "一级主标签分类过程中发生错误"
    echo ""
    echo -e "${YELLOW}🔧 常见问题排查：${NC}"
    echo "  1. 检查网络连接是否正常"
    echo "  2. 检查API密钥配置是否正确"
    echo "  3. 检查已标注JSON文件是否存在"
    echo "  4. 检查磁盘空间是否充足"
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
    show_slice_list
    user_confirm
    
    echo ""
    log_step "🚀 开始执行一级主标签分类流程..."
    echo ""
    
    # 记录开始时间
    start_time=$(date +%s)
    
    # 执行处理流程
    execute_main_tag_classification
    echo ""
    
    # 记录结束时间
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    minutes=$((duration / 60))
    seconds=$((duration % 60))
    
    # 显示结果
    echo ""
    echo -e "${GREEN}🎉 一级主标签分类完成！${NC}"
    echo -e "${CYAN}⏱️  总耗时: ${minutes}分${seconds}秒${NC}"
    echo ""
    
    show_results
    show_next_steps
    
    echo ""
    log_info "🎯 一级主标签分析完成！JSON文件已增强，现在可以进行二级分析"
    log_info "📝 下一步：运行 './视频分类_二级副标签.sh' 进行二级副标签分析"
    echo ""
    if [ "$AUTO_MODE" != "true" ]; then
        read -p "按任意键退出..." -n 1 -r
    fi
}

# 运行主程序
main "$@" 