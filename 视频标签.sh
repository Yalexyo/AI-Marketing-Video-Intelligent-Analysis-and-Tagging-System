#!/bin/bash

# =============================================================================
# 🏷️ AI视频标签分析程序
# 功能：对🎬Slice目录中的视频切片进行AI标签分析和中文翻译
# 作者：AI Video Master
# 版本：v1.0
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
    # 自动模式下不清屏
    if [ "$AUTO_MODE" != "true" ]; then
        clear
    fi
    echo -e "${MAGENTA}"
    echo "════════════════════════════════════════════════════════════════"
    echo "🏷️ AI视频标签分析程序 v1.0"
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo -e "${CYAN}功能说明：${NC}"
    echo "  • 🔧 自动设置虚拟环境和安装依赖"
    echo "  • 🔍 自动扫描 🎬Slice 目录下的所有视频切片"
    echo "  • 🏷️  执行AI标签分析（三级智能回退）"
    echo "  • ♻️  多场景智能检测（自动为多场景视频添加标识）"
    echo "  • 📁 输出原始标注JSON文件到切片目录（统一格式）"
    echo ""
    echo -e "${YELLOW}注意：标签分析过程可能需要15-30分钟，翻译将统一在后处理阶段进行${NC}"
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
        log_error "🎬Slice 目录不存在，请先运行视频切片程序"
        exit 1
    fi
    
    # 检查必要的模块目录
    if [ ! -d "slice_to_label" ]; then
        log_error "slice_to_label 模块目录不存在"
        exit 1
    fi
    
    # 检查切片文件
    slice_count=$(find "🎬Slice" -name "*.mp4" 2>/dev/null | wc -l)
    if [ "$slice_count" -eq 0 ]; then
        log_error "🎬Slice 目录下未找到切片文件，请先运行视频切片程序"
        exit 1
    fi
    
    log_info "✅ 系统依赖检查通过"
    log_info "🎬 发现 $slice_count 个视频切片"
}

# 设置虚拟环境
setup_environment() {
    log_step "🔧 设置标签分析环境..."
    
    cd slice_to_label
    
    if [ ! -f "pyproject.toml" ]; then
        log_error "slice_to_label 缺少 pyproject.toml 文件"
        exit 1
    fi
    
    # 同步依赖
    if uv sync --quiet; then
        log_info "✅ slice_to_label 环境就绪"
    else
        log_error "❌ slice_to_label 环境设置失败"
        exit 1
    fi
    
    cd ..
    log_info "✅ 标签分析环境设置完成"
}

# 检查API配置（必需）
check_api_config() {
    log_step "🔧 检查API配置..."
    
    # 🆕 自动加载项目根目录的环境变量
    if [ -f ".env" ]; then
        log_info "📁 自动加载项目根目录环境变量..."
        set -a  # 自动导出变量
        while IFS= read -r line; do
            # 跳过注释和空行
            if [[ ! "$line" =~ ^[[:space:]]*# ]] && [[ -n "${line// }" ]]; then
                # 直接导出变量
                if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
                    export "$line"
                fi
            fi
        done < ".env"
        set +a  # 关闭自动导出
        log_info "✅ 项目环境变量已自动加载"
    fi
    
    # 检查slice_to_label的API配置
    cd slice_to_label
    
    # 检查是否有.env文件，如果没有则从项目根目录的环境变量中获取
    if [ ! -f ".env" ]; then
        log_info "💡 slice_to_label/.env 不存在，使用项目根目录环境变量"
        
        # 检查项目根目录环境变量中的API密钥
        if [ -n "$DASHSCOPE_API_KEY" ] || [ -n "$GOOGLE_AI_API_KEY" ] || [ -n "$GEMINI_API_KEY" ] || [ -n "$OPENROUTER_API_KEY" ]; then
            log_info "✅ 检测到项目根目录中的AI分析API密钥"
        else
            log_error "❌ 未在项目根目录环境变量中找到AI分析API密钥"
            log_error "请在项目根目录 .env 文件中配置以下API密钥："
            log_error "1. DASHSCOPE_API_KEY=your_dashscope_api_key （DashScope API，用于Qwen模型，第一优先级）"
            log_error "2. GOOGLE_AI_API_KEY=your_google_ai_api_key （Google直接API，用于Gemini升级模型，第二优先级）"
            log_error "3. OPENROUTER_API_KEY=your_openrouter_api_key （OpenRouter API，用于Gemini 2.5 Pro，最后回退）"
            log_error "获取API密钥："
            log_error "- DashScope: https://dashscope.aliyun.com/"
            log_error "- OpenRouter: https://openrouter.ai/"
            log_error "- Gemini直接: https://ai.google.dev/"
            exit 1
        fi
    else
        # 检查API密钥配置（至少需要一个分析模型）
        has_api_key=false
        api_keys_found=()
        
        # 检查DashScope API密钥（Qwen API的实际名称）
        if (grep -q "DASHSCOPE_API_KEY=" .env && ! grep -q "DASHSCOPE_API_KEY=$" .env) || 
           (grep -q "QWEN_API_KEY=" .env && ! grep -q "QWEN_API_KEY=$" .env); then
            log_info "  ✅ DashScope/Qwen API密钥已配置（主分析模型，第一优先级）"
            has_api_key=true
            api_keys_found+=("DashScope/Qwen")
        fi
        
        # 检查Gemini相关API密钥（支持OpenRouter和直接调用）
        if (grep -q "GOOGLE_AI_API_KEY=" .env && ! grep -q "GOOGLE_AI_API_KEY=$" .env) ||
           (grep -q "GEMINI_API_KEY=" .env && ! grep -q "GEMINI_API_KEY=$" .env); then
            log_info "  ✅ Gemini直接API密钥已配置（Google升级模型，第二优先级）"
            has_api_key=true
            api_keys_found+=("Gemini直接")
        elif (grep -q "OPENROUTER_API_KEY=" .env && ! grep -q "OPENROUTER_API_KEY=$" .env); then
            log_info "  ✅ OpenRouter API密钥已配置（Gemini 2.5 Pro通过OpenRouter，最后回退）"
            has_api_key=true
            api_keys_found+=("OpenRouter/Gemini")
        fi
        
        if [ "$has_api_key" = false ]; then
            log_error "❌ 未检测到有效的分析API密钥配置"
            log_error "AI标签功能必需分析API密钥，请在 slice_to_label/.env 中配置以下任一API密钥："
            log_error "1. DASHSCOPE_API_KEY=your_dashscope_api_key （DashScope API，用于Qwen模型，第一优先级）"
            log_error "2. GOOGLE_AI_API_KEY=your_google_ai_api_key （Google直接API，用于Gemini升级模型，第二优先级）"
            log_error "3. OPENROUTER_API_KEY=your_openrouter_api_key （OpenRouter API，用于Gemini 2.5 Pro，最后回退）"
            log_error "获取API密钥："
            log_error "- DashScope: https://dashscope.aliyun.com/"
            log_error "- OpenRouter: https://openrouter.ai/"
            log_error "- Gemini直接: https://ai.google.dev/"
            exit 1
        fi
    fi
    
    cd ..
    
    # 显示配置的API（优先使用项目根目录环境变量）
    api_keys_found=()
    if [ -n "$DASHSCOPE_API_KEY" ]; then
        api_keys_found+=("DashScope/Qwen(1st)")
    fi
    if [ -n "$GOOGLE_AI_API_KEY" ] || [ -n "$GEMINI_API_KEY" ]; then
        api_keys_found+=("Gemini直接(2nd)")
    fi
    if [ -n "$OPENROUTER_API_KEY" ]; then
        api_keys_found+=("OpenRouter/Gemini(3rd)")
    fi
    
    api_list=$(printf ", %s" "${api_keys_found[@]}")
    api_list=${api_list:2}  # 移除开头的", "
    log_info "✅ 分析API配置检查通过 (已配置: $api_list)"
    
    # 检查翻译API（可选）
    if [ -n "$DEEPSEEK_API_KEY" ]; then
        log_info "💡 检测到DeepSeek API，支持后处理翻译功能"
    else
        log_warn "⚠️ 未配置DeepSeek API，分析结果将保持原始格式"
        log_warn "💡 如需中文翻译，可在项目根目录 .env 中配置 DEEPSEEK_API_KEY"
    fi
}

# 显示切片文件列表
show_slice_list() {
    log_step "🎬 扫描到的视频切片："
    echo ""
    
    # 按视频统计
    for video_dir in $(find "🎬Slice" -maxdepth 1 -type d ! -name "." ! -name ".." ! -name "🎬Slice" 2>/dev/null | grep -v "\.DS_Store"); do
        # 检查是否包含slices子目录
        if [ -d "$video_dir/slices" ]; then
            video_name=$(basename "$video_dir")
            slices_count=$(find "$video_dir/slices" -name "*.mp4" 2>/dev/null | wc -l)
            labels_count=$(find "$video_dir/slices" -name "*_analysis.json" 2>/dev/null | wc -l)
            echo -e "  📹 ${BLUE}$video_name${NC}: $slices_count 个切片 ($labels_count 个已标注)"
        fi
    done
    echo ""
}

# 用户确认
user_confirm() {
    echo -e "${YELLOW}⚠️  即将开始AI标签分析，整个过程包括：${NC}"
    echo "  🏷️  AI标签分析（三级智能回退，统一使用专业prompt）"
    echo "  ♻️  多场景智能检测（自动标识复杂场景）"
    echo "  📋 格式统一处理（去除方括号等多余符号）"
    echo "  🌐 自动批量翻译（确保统一中文格式）"
    echo "  💾 输出最终标注JSON文件"
    echo ""
    echo -e "${CYAN}✨ 新增功能特性：${NC}"
    echo "  🎯 自动检测混合语言输出"
    echo "  🔄 智能翻译英文字段为中文"
    echo "  ✅ 确保最终获得统一的中文标准格式"
    echo "  🧠 智能推断缺失的情绪标签"
    echo "  ♻️  多场景检测（自动为多场景MP4添加♻️前缀）"
    echo "  🎯 智能关键词提取（支持98个可配置关键词）"
    echo "  🖼️  优化帧提取（最多8帧智能采样）"
    echo ""
    echo -e "${CYAN}📊 分析流程（三级智能回退）：${NC}"
    echo "  1️⃣ Qwen VL Max分析（主模型，低成本，输出中文）"
    echo "  2️⃣ 失败时回退到Google原生Gemini（升级模型，高精度，输出英文）"
    echo "  3️⃣ 再失败时回退到OpenRouter Gemini（最后回退，输出英文）"
    echo "  4️⃣ 自动翻译英文部分为中文"
    echo "  5️⃣ 多场景检测和MP4文件智能重命名"
    echo "  6️⃣ 输出统一的中文标准格式"
    echo ""
    echo -e "${YELLOW}预计耗时：15-35分钟（取决于切片数量和网络状况）${NC}"
    echo ""
    
    # 自动模式跳过用户确认
    if [ "$AUTO_MODE" = "true" ]; then
        log_info "🤖 自动模式：跳过用户确认，直接开始分析"
    else
        read -p "是否继续？(y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "用户取消操作"
            exit 0
        fi
    fi
}

# 执行AI标签分析
execute_ai_labeling() {
    log_step "🏷️  开始执行AI标签分析..."
    echo ""
    
    cd slice_to_label
    
    log_info "🤖 启动AI标签分析..."
    
    # 获取所有有切片的视频（支持灵活的文件夹结构和空格目录名）
    video_dirs_array=()
    while IFS= read -r -d '' potential_dir; do
        # 方法1: 检查slices子目录
        if [ -d "$potential_dir/slices" ]; then
            video_dirs_array+=("$potential_dir")
        # 方法2: 检查直接在目录下是否有视频文件
        elif find "$potential_dir" -maxdepth 1 -name "*.mp4" -o -name "*.mov" -o -name "*.avi" -o -name "*.mkv" | grep -q .; then
            video_dirs_array+=("$potential_dir")
        fi
    done < <(find "../🎬Slice" -maxdepth 1 -type d ! -name "." ! -name ".." ! -name "🎬Slice" -print0 2>/dev/null | grep -zv "\.DS_Store")
    
    if [ ${#video_dirs_array[@]} -eq 0 ]; then
        log_error "❌ 未找到包含视频文件的目录"
        cd ..
        exit 1
    fi
    
    total_success=0
    total_failed=0
    
    # 为每个视频执行标签分析（支持灵活的文件夹结构和空格目录名）
    for video_dir in "${video_dirs_array[@]}"; do
        video_name=$(basename "$video_dir")
        log_info "🎬 分析视频: $video_name"
        
        # 根据文件夹结构动态确定slice_type
        if [ -d "$video_dir/slices" ]; then
            slice_type="slices"
        else
            slice_type="all"
        fi
        
        if uv run python run_analysis.py \
            --slice-dir ../🎬Slice \
            --video "$video_name" \
            --slice-type "$slice_type" \
            --analysis-type dual; then
            
            log_info "✅ $video_name 标签分析完成"
            ((total_success++))
        else
            log_error "❌ $video_name 标签分析失败"
            ((total_failed++))
        fi
    done
    
    log_info "📊 标签分析统计: 成功 $total_success 个，失败 $total_failed 个"
    
    # 🔄 自动执行批量翻译，确保统一中文格式
    echo ""
    log_step "🌐 开始自动批量翻译（统一中文格式）..."
    
    # 检查是否有DeepSeek API
    if [ -n "$DEEPSEEK_API_KEY" ]; then
        translation_success=0
        translation_failed=0
        
        # 为每个成功分析的视频执行翻译 - 支持灵活的文件夹结构和空格目录名
        for video_dir in "${video_dirs_array[@]}"; do
            video_name=$(basename "$video_dir")
            video_base_dir="../🎬Slice/$video_name"
            
            # 检查分析文件位置（支持slices子目录和直接目录）
            analysis_count=0
            actual_dir=""
            
            # 方法1: 检查slices子目录
            if [ -d "$video_base_dir/slices" ]; then
                analysis_count=$(find "$video_base_dir/slices" -name "*_analysis.json" 2>/dev/null | wc -l)
                if [ "$analysis_count" -gt 0 ]; then
                    actual_dir="$video_base_dir/slices/"
                fi
            fi
            
            # 方法2: 检查直接在目录下
            if [ "$analysis_count" -eq 0 ]; then
                analysis_count=$(find "$video_base_dir" -maxdepth 1 -name "*_analysis.json" 2>/dev/null | wc -l)
                if [ "$analysis_count" -gt 0 ]; then
                    actual_dir="$video_base_dir/"
                fi
            fi
            
            if [ "$analysis_count" -gt 0 ] && [ -n "$actual_dir" ]; then
                log_info "🔄 翻译视频: $video_name ($analysis_count 个分析文件)"
                
                if uv run python batch_translate.py "$actual_dir"; then
                    log_info "✅ $video_name 翻译完成"
                    ((translation_success++))
                else
                    log_warn "⚠️ $video_name 翻译失败"
                    ((translation_failed++))
                fi
            else
                log_warn "⚠️ $video_name 没有分析文件，跳过翻译"
            fi
        done
        
        echo ""
        log_info "🌐 批量翻译统计: 成功 $translation_success 个，失败 $translation_failed 个"
        
        if [ "$translation_success" -gt 0 ]; then
            log_info "🎉 翻译完成！所有分析结果已统一为中文标准格式"
        fi
    else
        log_warn "⚠️ 未配置DeepSeek API，跳过自动翻译"
        log_warn "💡 分析结果保持原始格式（英文+中文混合）"
        log_warn "🔧 如需统一中文格式，请配置 DEEPSEEK_API_KEY 后重新运行"
    fi
    
    cd ..
}

# 显示结果统计
show_results() {
    log_step "📊 标签分析结果统计"
    echo ""
    
    # 切片统计
    total_slices=$(find "🎬Slice" -name "*.mp4" 2>/dev/null | wc -l)
    
    # 标签统计
    total_labels=$(find "🎬Slice" -name "*_analysis.json" 2>/dev/null | wc -l)
    
    # 按视频统计
    echo -e "${CYAN}📈 总体统计：${NC}"
    echo "  🎬 总切片数: $total_slices 个"
    echo "  🏷️  总标签数: $total_labels 个"
    
    # 检查是否进行了翻译
    cd slice_to_label
    if [ -n "$DEEPSEEK_API_KEY" ]; then
        echo "  📝 输出格式: 统一中文标准格式（已自动翻译）"
        echo "  🌐 翻译状态: ✅ 已完成自动翻译"
    else
        echo "  📝 输出格式: 原始格式（英文+中文混合）"
        echo "  🌐 翻译状态: ⚠️ 未配置翻译API"
    fi
    cd ..
    echo ""
    
    echo -e "${CYAN}📁 按视频统计：${NC}"
    for video_dir in $(find "🎬Slice" -maxdepth 1 -type d ! -name "." ! -name ".." ! -name "🎬Slice" 2>/dev/null | grep -v "\.DS_Store"); do
        # 检查是否包含slices子目录
        if [ -d "$video_dir/slices" ]; then
            video_name=$(basename "$video_dir")
            slices_count=$(find "$video_dir/slices" -name "*.mp4" 2>/dev/null | wc -l)
            labels_count=$(find "$video_dir/slices" -name "*_analysis.json" 2>/dev/null | wc -l)
            
            echo "  📹 $video_name: $slices_count 个切片, $labels_count 个标签"
        fi
    done
    echo ""
    
    echo -e "${CYAN}📂 输出目录结构：${NC}"
    echo "  🎬Slice/"
    echo "  ├── video_1/slices/     # 切片文件 + 中文标签JSON"
    echo "  ├── video_2/slices/     # 切片文件 + 中文标签JSON"
    echo "  └── ..."
    echo ""
    
    echo -e "${CYAN}🎯 格式特性：${NC}"
    # 检查翻译状态
    cd slice_to_label
    if [ -n "$DEEPSEEK_API_KEY" ]; then
        echo "  ✅ 统一中文格式：所有字段都是中文"
        echo "  ✅ 清洁输出：已去除方括号等多余符号"
        echo "  ✅ 智能情绪：自动推断缺失的情绪标签"
        echo "  ✅ 完整字段：object, scene, emotion, brand_elements"
        echo "  ♻️  多场景检测：自动为多场景MP4添加♻️前缀标识"
        echo "  🎯 智能提取：支持98个可配置关键词的语义分析"
        echo "  🖼️  优化帧提取：最多8帧的智能质量采样"
    else
        echo "  ⚠️ 混合语言：Gemini输出英文，Qwen输出中文"
        echo "  ✅ 清洁输出：已去除方括号等多余符号"
        echo "  ♻️  多场景检测：自动为多场景MP4添加♻️前缀标识"
        echo "  🎯 智能提取：支持98个可配置关键词的语义分析"
        echo "  🖼️  优化帧提取：最多8帧的智能质量采样"
        echo "  💡 建议：配置DeepSeek API获得统一中文格式"
        echo ""
        echo -e "${CYAN}🔧 统一格式方法：${NC}"
        echo "  1. 在 slice_to_label/.env 中配置 DEEPSEEK_API_KEY"
        echo "  2. 手动运行翻译："
        echo "     cd slice_to_label && uv run python batch_translate.py '../🎬Slice/video_1/slices/'"
    fi
    cd ..
    echo ""
}

# 打开结果目录
open_results() {
    log_step "🔍 结果预览"
    echo ""
    
    # 自动模式跳过打开目录询问
    if [ "$AUTO_MODE" = "true" ]; then
        log_info "🤖 自动模式：跳过目录打开询问"
        log_info "📁 结果目录：$(pwd)/🎬Slice"
    else
        read -p "是否打开结果目录查看？(y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if command -v open &> /dev/null; then
                open "🎬Slice"
                log_info "📁 已打开结果目录"
            else
                log_info "📁 结果目录：$(pwd)/🎬Slice"
            fi
        fi
    fi
}

# 错误处理
handle_error() {
    log_error "标签分析过程中发生错误"
    echo ""
    echo -e "${YELLOW}🔧 常见问题排查：${NC}"
    echo "  1. 检查网络连接是否正常"
    echo "  2. 检查API密钥配置"
    echo "  3. 检查磁盘空间是否充足"
    echo "  4. 检查视频切片文件是否存在"
    echo ""
    # 自动模式跳过按键提示
    if [ "$AUTO_MODE" != "true" ]; then
        read -p "按任意键退出..." -n 1 -r
    fi
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
    log_step "🚀 开始执行AI标签分析流程..."
    echo ""
    
    # 记录开始时间
    start_time=$(date +%s)
    
    # 执行处理流程
    execute_ai_labeling
    echo ""
    
    # 记录结束时间
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    minutes=$((duration / 60))
    seconds=$((duration % 60))
    
    # 显示结果
    echo ""
    echo -e "${GREEN}🎉 AI标签分析完成！${NC}"
    echo -e "${CYAN}⏱️  总耗时: ${minutes}分${seconds}秒${NC}"
    echo ""
    
    show_results
    open_results
    
    echo ""
    log_info "标签分析完毕，感谢使用！"
    echo ""
    # 自动模式跳过按键提示
    if [ "$AUTO_MODE" != "true" ]; then
        read -p "按任意键退出..." -n 1 -r
    fi
}

# 运行主程序
main "$@" 