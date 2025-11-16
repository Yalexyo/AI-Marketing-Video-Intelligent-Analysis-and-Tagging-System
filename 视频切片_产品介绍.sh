#!/bin/bash

# 🎬 视频切片_产品介绍 一键执行程序
# 整合字幕提取 + 产品介绍切片的完整自动化流程
# Author: AI Video Master
# Version: v1.0

set -e  # 遇到错误立即退出

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 图标配置
SUCCESS_ICON="✅"
ERROR_ICON="❌"
WARNING_ICON="⚠️"
INFO_ICON="ℹ️"
PROCESS_ICON="🔄"
VIDEO_ICON="🎬"
SUBTITLE_ICON="📄"
AI_ICON="🤖"
SLICE_ICON="✂️"

# 项目路径配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIGIN_DIR="${SCRIPT_DIR}/🍭Origin"
SRT_DIR="${SCRIPT_DIR}/📄SRT"
SLICE_DIR="${SCRIPT_DIR}/🎬Slice"
VIDEO_TO_SRT_DIR="${SCRIPT_DIR}/video_to_srt"
SRT_TO_PRODUCT_DIR="${SCRIPT_DIR}/srt_to_product"

# 统计变量
TOTAL_VIDEOS=0
PROCESSED_VIDEOS=0
TOTAL_SUBTITLES=0
TOTAL_PRODUCT_SLICES=0
START_TIME=""
FAILED_VIDEOS=()

# 工具函数
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

print_header() {
    echo -e "${WHITE}"
    echo "════════════════════════════════════════════════════════════════"
    echo "  🎬 视频切片_产品介绍 自动化处理系统"
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo -e "  ${VIDEO_ICON} 🍭Origin → ${SUBTITLE_ICON} 字幕提取 → ${AI_ICON} AI分析 → ${SLICE_ICON} 产品切片"
    echo ""
    echo -e "功能特性："
    echo -e "  • 🎤 DashScope高精度语音识别（婴幼儿奶粉专用词汇优化）"
    echo -e "  • 🤖 DeepSeek AI智能分析（启赋、蕴淳、蓝钻品牌识别）"
    echo -e "  • ✂️  精准产品介绍切片（10-30秒最佳时长）"
    echo -e "  • 📊 完整JSON分析报告（品牌维度详细标注）"
    echo ""
    echo -e "注意：整个过程可能需要10-40分钟，请保持网络连接"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
}

check_dependencies() {
    log_step "${PROCESS_ICON} 检查系统依赖..."
    
    # 检查uv
    if ! command -v uv &> /dev/null; then
        log_error "uv 未安装，请先安装uv"
        echo "安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    # 检查ffmpeg
    if ! command -v ffmpeg &> /dev/null; then
        log_error "ffmpeg 未安装，请先安装ffmpeg"
        echo "macOS安装命令: brew install ffmpeg"
        exit 1
    fi
    
    # 检查video_to_srt目录
    if [ ! -d "$VIDEO_TO_SRT_DIR" ]; then
        log_error "video_to_srt 模块不存在: $VIDEO_TO_SRT_DIR"
        exit 1
    fi
    
    # 检查srt_to_product目录
    if [ ! -d "$SRT_TO_PRODUCT_DIR" ]; then
        log_error "srt_to_product 模块不存在: $SRT_TO_PRODUCT_DIR"
        exit 1
    fi
    
    # 检查Origin目录
    if [ ! -d "$ORIGIN_DIR" ]; then
        log_error "🍭Origin 目录不存在: $ORIGIN_DIR"
        exit 1
    fi
    
    log_success "${SUCCESS_ICON} 系统依赖检查通过"
}

setup_environments() {
    log_step "${PROCESS_ICON} 设置和检查虚拟环境..."
    
    # 设置video_to_srt环境
    log_info "  📄 设置 video_to_srt 环境..."
    cd "$VIDEO_TO_SRT_DIR"
    
    if [ ! -f "pyproject.toml" ]; then
        log_error "video_to_srt 缺少 pyproject.toml 文件"
        exit 1
    fi
    
    # 同步依赖
    if uv sync --quiet; then
        log_success "  ${SUCCESS_ICON} video_to_srt 环境就绪"
    else
        log_error "  ${ERROR_ICON} video_to_srt 环境设置失败"
        exit 1
    fi
    
    # 设置srt_to_product环境
    log_info "  🤖 设置 srt_to_product 环境..."
    cd "$SRT_TO_PRODUCT_DIR"
    
    if [ ! -f "pyproject.toml" ]; then
        log_error "srt_to_product 缺少 pyproject.toml 文件"
        exit 1
    fi
    
    # 同步依赖
    if uv sync --quiet; then
        log_success "  ${SUCCESS_ICON} srt_to_product 环境就绪"
    else
        log_error "  ${ERROR_ICON} srt_to_product 环境设置失败"
        exit 1
    fi
    
    cd "$SCRIPT_DIR"
    log_success "${SUCCESS_ICON} 所有虚拟环境设置完成"
}

check_api_config() {
    log_step "${PROCESS_ICON} 检查API配置..."
    
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
        log_success "  ${SUCCESS_ICON} 项目环境变量已自动加载"
    fi
    
    # 检查DashScope API密钥（字幕提取必需）
    if [ -n "$DASHSCOPE_API_KEY" ]; then
        log_success "  ${SUCCESS_ICON} DashScope API密钥已配置（来自项目环境变量）"
    else
        # 检查video_to_srt模块的独立配置
        cd "$VIDEO_TO_SRT_DIR"
        if [ -f ".env" ] && grep -q "DASHSCOPE_API_KEY=" .env && ! grep -q "DASHSCOPE_API_KEY=$" .env; then
            log_success "  ${SUCCESS_ICON} DashScope API密钥已配置（来自video_to_srt模块）"
        else
            log_error "  ${ERROR_ICON} DashScope API密钥未配置"
            log_error "字幕提取功能必需DashScope API密钥，请在项目根目录 .env 文件中配置："
            log_error "DASHSCOPE_API_KEY=your_dashscope_api_key"
            log_error "获取API密钥: https://dashscope.aliyun.com/"
            exit 1
        fi
        cd "$SCRIPT_DIR"
    fi
    
    # 检查DeepSeek API密钥（AI分析必需）
    if [ -n "$DEEPSEEK_API_KEY" ]; then
        log_success "  ${SUCCESS_ICON} DeepSeek API密钥已配置（来自项目环境变量）"
    else
        # 检查srt_to_product模块的独立配置
        cd "$SRT_TO_PRODUCT_DIR"
        if [ -f ".env" ] && grep -q "DEEPSEEK_API_KEY=" .env && ! grep -q "DEEPSEEK_API_KEY=$" .env; then
            log_success "  ${SUCCESS_ICON} DeepSeek API密钥已配置（来自srt_to_product模块）"
        else
            log_error "  ${ERROR_ICON} DeepSeek API密钥未配置"
            log_error "AI分析功能必需DeepSeek API密钥，请在项目根目录 .env 文件中配置："
            log_error "DEEPSEEK_API_KEY=your_deepseek_api_key"
            log_error "获取API密钥: https://platform.deepseek.com/"
            exit 1
        fi
        cd "$SCRIPT_DIR"
    fi
    
    log_success "${SUCCESS_ICON} API配置检查通过 (DashScope + DeepSeek)"
}

scan_videos() {
    log_step "${VIDEO_ICON} 扫描🍭Origin目录中的视频文件..."
    
    # 支持的视频格式
    VIDEO_EXTENSIONS=("*.mp4" "*.mov" "*.avi" "*.mkv" "*.webm" "*.wmv" "*.flv")
    
    # 扫描视频文件
    VIDEO_FILES=()
    for ext in "${VIDEO_EXTENSIONS[@]}"; do
        while IFS= read -r -d '' file; do
            VIDEO_FILES+=("$file")
        done < <(find "$ORIGIN_DIR" -maxdepth 1 -iname "$ext" -type f -print0 2>/dev/null)
    done
    
    TOTAL_VIDEOS=${#VIDEO_FILES[@]}
    
    if [ $TOTAL_VIDEOS -eq 0 ]; then
        log_error "未在🍭Origin目录中找到任何视频文件"
        log_info "请将视频文件放入: $ORIGIN_DIR"
        log_info "支持格式: ${VIDEO_EXTENSIONS[*]}"
        exit 1
    fi
    
    log_info "${SUCCESS_ICON} 发现 $TOTAL_VIDEOS 个视频文件"
    log_step "${VIDEO_ICON} 扫描到的视频文件："
    echo ""
    
    for video_file in "${VIDEO_FILES[@]}"; do
        filename=$(basename "$video_file")
        filesize=$(du -h "$video_file" | cut -f1)
        echo -e "  ${VIDEO_ICON} $filename ($filesize)"
    done
    
    echo ""
}

confirm_processing() {
    echo -e "${WARNING_ICON} 即将开始处理，整个过程包括："
    echo -e "  1️⃣  字幕提取（DashScope语音识别）"
    echo -e "  2️⃣  AI分析（DeepSeek产品介绍识别）"
    echo -e "  3️⃣  精准切片（10-30秒产品介绍片段）"
    echo ""
    echo -e "预计耗时：$(($TOTAL_VIDEOS * 8))-$(($TOTAL_VIDEOS * 15))分钟（取决于视频数量和长度）"
    echo ""
    
    while true; do
        read -p "是否继续？(y/N): " yn
        case $yn in
            [Yy]* ) break;;
            [Nn]* ) echo "已取消处理"; exit 0;;
            * ) echo "已取消处理"; exit 0;;
        esac
    done
}

create_output_dirs() {
    log_step "${PROCESS_ICON} 创建输出目录..."
    
    # 创建必要的目录
    mkdir -p "$SRT_DIR"
    mkdir -p "$SLICE_DIR"
    
    log_success "${SUCCESS_ICON} 输出目录创建完成"
}

process_video_to_srt() {
    local video_file="$1"
    local video_name=$(basename "$video_file" | sed 's/\.[^.]*$//')
    
    log_step "1️⃣ 开始字幕提取：$video_name"
    
    # 切换到video_to_srt目录
    cd "$VIDEO_TO_SRT_DIR"
    
    # 运行字幕提取 - 直接使用🍭Origin目录（video_to_srt的🍭Origin驱动架构）
    log_info "  ${SUBTITLE_ICON} 正在进行语音识别（DashScope API）..."
    if uv run run.py --input "$ORIGIN_DIR"; then
        # 检查生成的SRT文件
        local expected_srt_file="../📄SRT/$video_name/${video_name}_full.srt"
        if [ -f "$expected_srt_file" ]; then
            log_success "  ${SUCCESS_ICON} 字幕提取完成"
            TOTAL_SUBTITLES=$((TOTAL_SUBTITLES + 1))
        else
            log_error "  ${ERROR_ICON} SRT文件未生成：$expected_srt_file"
            FAILED_VIDEOS+=("$video_name (SRT文件未生成)")
            cd "$SCRIPT_DIR"
            return 1
        fi
    else
        log_error "  ${ERROR_ICON} 字幕提取失败：$video_name"
        FAILED_VIDEOS+=("$video_name (字幕提取失败)")
        cd "$SCRIPT_DIR"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
    return 0
}

process_srt_to_product() {
    local video_name="$1"
    
    log_step "2️⃣ 开始AI分析和产品切片：$video_name"
    
    # 查找对应的SRT文件（🍭Origin驱动架构：📄SRT/video_1/video_1_full.srt）
    local srt_file="$SRT_DIR/$video_name/${video_name}_full.srt"
    if [ ! -f "$srt_file" ]; then
        log_error "  ${ERROR_ICON} 未找到对应的SRT文件：$srt_file"
        FAILED_VIDEOS+=("$video_name (未找到SRT文件)")
        return 1
    fi
    
    # 切换到srt_to_product目录
    cd "$SRT_TO_PRODUCT_DIR"
    
    # 创建临时输入目录结构
    local temp_input_dir="data/input_temp"
    mkdir -p "$temp_input_dir"
    
    # 复制SRT文件到临时目录
    cp "$srt_file" "$temp_input_dir/"
    
    # 设置对应的原始视频路径（srt_to_product需要原始视频进行切片）
    local original_video="$ORIGIN_DIR/${video_name}".* 
    local video_extension=""
    for ext in mp4 mov avi mkv webm wmv flv; do
        if [ -f "$ORIGIN_DIR/${video_name}.${ext}" ]; then
            video_extension="$ext"
            break
        fi
    done
    
    if [ -z "$video_extension" ]; then
        log_error "  ${ERROR_ICON} 未找到原始视频文件：$video_name"
        FAILED_VIDEOS+=("$video_name (未找到原始视频)")
        rm -rf "$temp_input_dir"
        cd "$SCRIPT_DIR"
        return 1
    fi
    
    # 复制原始视频到临时目录（srt_to_product需要）
    cp "$ORIGIN_DIR/${video_name}.${video_extension}" "$temp_input_dir/"
    
    # 创建输出目录
    local product_output_dir="$SLICE_DIR/$video_name/product"
    mkdir -p "$product_output_dir"
    
    # 运行AI分析和产品切片
    log_info "  ${AI_ICON} 正在进行AI分析（DeepSeek API）..."
    log_info "  ${SLICE_ICON} 正在生成产品介绍切片（10-30秒）..."
    
    if uv run run.py "$temp_input_dir" -o "$product_output_dir" -v; then
        # 统计生成的切片数量
        local slice_count=$(find "$product_output_dir" -name "*.mp4" -type f | wc -l)
        log_success "  ${SUCCESS_ICON} 产品切片生成完成，共 $slice_count 个切片"
        TOTAL_PRODUCT_SLICES=$((TOTAL_PRODUCT_SLICES + slice_count))
    else
        log_error "  ${ERROR_ICON} 产品切片生成失败：$video_name"
        FAILED_VIDEOS+=("$video_name (产品切片失败)")
        # 清理临时目录
        rm -rf "$temp_input_dir"
        cd "$SCRIPT_DIR"
        return 1
    fi
    
    # 清理临时目录
    rm -rf "$temp_input_dir"
    cd "$SCRIPT_DIR"
    return 0
}

process_all_videos() {
    log_step "${PROCESS_ICON} 开始执行自动化处理流程..."
    echo ""
    
    START_TIME=$(date)
    local start_timestamp=$(date +%s)
    
    for video_file in "${VIDEO_FILES[@]}"; do
        local video_name=$(basename "$video_file" | sed 's/\.[^.]*$//')
        
        echo -e "${WHITE}================================${NC}"
        echo -e "${WHITE}正在处理: $video_name${NC}"
        echo -e "${WHITE}进度: $((PROCESSED_VIDEOS + 1))/$TOTAL_VIDEOS${NC}"
        echo -e "${WHITE}================================${NC}"
        
        # 第1步：字幕提取
        if process_video_to_srt "$video_file"; then
            # 第2步：AI分析和产品切片
            if process_srt_to_product "$video_name"; then
                PROCESSED_VIDEOS=$((PROCESSED_VIDEOS + 1))
                log_success "${SUCCESS_ICON} $video_name 处理完成"
            fi
        fi
        
        echo ""
    done
    
    local end_timestamp=$(date +%s)
    local total_time=$((end_timestamp - start_timestamp))
    local total_minutes=$((total_time / 60))
    local total_seconds=$((total_time % 60))
    
    echo -e "${WHITE}================================${NC}"
    echo -e "${WHITE}处理完成！${NC}"
    echo -e "${WHITE}================================${NC}"
    
    # 显示统计信息
    show_final_statistics "$total_minutes" "$total_seconds"
}

show_final_statistics() {
    local total_minutes="$1"
    local total_seconds="$2"
    
    echo ""
    log_step "${SUCCESS_ICON} 处理统计报告"
    echo ""
    echo -e "${GREEN}📈 总体统计：${NC}"
    echo -e "  ${VIDEO_ICON} 总视频数: $TOTAL_VIDEOS 个"
    echo -e "  ${SUCCESS_ICON} 成功处理: $PROCESSED_VIDEOS 个"
    echo -e "  ${SUBTITLE_ICON} 总字幕数: $TOTAL_SUBTITLES 个"
    echo -e "  ${SLICE_ICON} 总产品切片: $TOTAL_PRODUCT_SLICES 个"
    echo -e "  ⏱️  总耗时: ${total_minutes}分${total_seconds}秒"
    echo ""
    
    if [ ${#FAILED_VIDEOS[@]} -gt 0 ]; then
        echo -e "${RED}❌ 失败列表：${NC}"
        for failed in "${FAILED_VIDEOS[@]}"; do
            echo -e "  ${ERROR_ICON} $failed"
        done
        echo ""
    fi
    
    echo -e "${GREEN}📁 输出目录：${NC}"
    echo -e "  ${SUBTITLE_ICON} 字幕文件: $SRT_DIR"
    echo -e "  ${SLICE_ICON} 产品切片: $SLICE_DIR"
    echo ""
    
    # 按视频显示详细统计
    echo -e "${CYAN}📁 按视频统计：${NC}"
    for video_file in "${VIDEO_FILES[@]}"; do
        local video_name=$(basename "$video_file" | sed 's/\.[^.]*$//')
        local product_dir="$SLICE_DIR/$video_name/product"
        
        if [ -d "$product_dir" ]; then
            local slice_count=$(find "$product_dir" -name "*.mp4" -type f | wc -l)
            local json_count=$(find "$product_dir" -name "*.json" -type f | wc -l)
            echo -e "  ${VIDEO_ICON} $video_name: $slice_count 个切片, $json_count 个分析报告"
        else
            echo -e "  ${ERROR_ICON} $video_name: 处理失败"
        fi
    done
    echo ""
}

open_results() {
    log_step "${SUCCESS_ICON} 打开结果目录..."
    
    # 在macOS上打开结果目录
    if command -v open &> /dev/null; then
        open "$SLICE_DIR"
        log_success "${SUCCESS_ICON} 已打开产品切片目录"
    fi
}

# 主程序入口
main() {
    print_header
    check_dependencies
    setup_environments
    check_api_config
    scan_videos
    confirm_processing
    create_output_dirs
    process_all_videos
    open_results
    
    echo -e "${GREEN}🎉 视频切片_产品介绍 处理完成！${NC}"
    echo ""
}

# 错误处理
trap 'echo -e "\n${RED}${ERROR_ICON} 程序被中断${NC}"; exit 1' INT TERM

# 运行主程序
main "$@" 