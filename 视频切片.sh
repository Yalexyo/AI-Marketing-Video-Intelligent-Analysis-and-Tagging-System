#!/bin/bash

# =============================================================================
# 🎬 AI视频切片处理程序
# 功能：自动处理🍭Origin目录下的所有视频，生成智能切片
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
    clear
    echo -e "${MAGENTA}"
    echo "════════════════════════════════════════════════════════════════"
    echo "🎬 AI视频切片处理程序 v1.0"
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo -e "${CYAN}功能说明：${NC}"
    echo "  • 🔧 自动设置虚拟环境和安装依赖"
    echo "  • 🔍 自动扫描 🍭Origin 目录下的所有视频文件"
    echo "  • ✂️  执行本地智能切片（FFmpeg场景检测，不合并）"
    echo "  • 📁 输出到 🎬Slice 目录"
    echo ""
    echo -e "${YELLOW}注意：切片过程可能需要5-20分钟，请保持网络连接${NC}"
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
    
    # 检查ffmpeg是否安装
    if ! command -v ffmpeg &> /dev/null; then
        log_error "ffmpeg 未安装，请先安装 ffmpeg: brew install ffmpeg"
        exit 1
    fi
    
    # 检查输入目录
    if [ ! -d "🍭Origin" ]; then
        log_error "🍭Origin 目录不存在，请确保视频文件放在此目录下"
        exit 1
    fi
    
    # 检查必要的模块目录
    if [ ! -d "video_to_slice" ]; then
        log_error "video_to_slice 模块目录不存在"
        exit 1
    fi
    
    # 检查视频文件（支持大小写不敏感）
    video_count=$(find "🍭Origin" \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.avi" -o -iname "*.mkv" \) 2>/dev/null | wc -l)
    if [ "$video_count" -eq 0 ]; then
        log_error "🍭Origin 目录下未找到支持的视频文件（mp4/mov/avi/mkv）"
        exit 1
    fi
    
    log_info "✅ 系统依赖检查通过"
    log_info "📹 发现 $video_count 个视频文件"
}

# 设置虚拟环境
setup_environment() {
    log_step "🔧 设置切片处理环境..."
    
    cd video_to_slice
    
    if [ ! -f "pyproject.toml" ]; then
        log_error "video_to_slice 缺少 pyproject.toml 文件"
        exit 1
    fi
    
    # 同步依赖
    if uv sync --quiet; then
        log_info "✅ video_to_slice 环境就绪"
    else
        log_error "❌ video_to_slice 环境设置失败"
        exit 1
    fi
    
    cd ..
    log_info "✅ 切片处理环境设置完成"
}

# 显示视频文件列表
show_video_list() {
    log_step "📹 扫描到的视频文件："
    echo ""
    find "🍭Origin" \( -iname "*.mp4" -o -iname "*.mov" -o -iname "*.avi" -o -iname "*.mkv" \) 2>/dev/null | while read video; do
        filename=$(basename "$video")
        filesize=$(du -h "$video" | cut -f1)
        echo -e "  🎬 ${BLUE}$filename${NC} (${filesize})"
    done
    echo ""
}

# 用户确认
user_confirm() {
    echo -e "${YELLOW}⚠️  即将开始视频切片处理：${NC}"
    echo "  ✂️  本地智能切片（FFmpeg场景检测）"
    echo ""
    echo -e "${YELLOW}预计耗时：5-20分钟（取决于视频数量和长度）${NC}"
    echo ""
    read -p "是否继续？(y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "用户取消操作"
        exit 0
    fi
}

# 执行视频切片
execute_video_slicing() {
    log_step "✂️  开始执行本地智能切片..."
    echo ""
    
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
    
    cd video_to_slice
    
    # 验证Google Cloud凭据（已由项目环境变量自动配置）
    if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        log_info "✅ Google Cloud凭据已配置: $(basename "$GOOGLE_APPLICATION_CREDENTIALS")"
    else
        log_warn "⚠️ Google Cloud凭据未配置，将使用本地FFmpeg模式"
    fi
    
    log_info "🚀 启动本地切片处理..."
    
    # 执行切片命令：本地模式，不合并，详细输出
    if uv run run.py \
        --input ../🍭Origin \
        --mode local \
        --verbose \
        --concurrent 1 \
        --ffmpeg-workers 4; then
        
        log_info "✅ 视频切片完成"
        
        # 统计切片结果
        slice_count=$(find "../🎬Slice" -name "*.mp4" 2>/dev/null | wc -l)
        log_info "📊 生成切片总数: $slice_count 个"
        
        cd ..
        return 0
        
    else
        log_error "❌ 视频切片失败"
        cd ..
        exit 1
    fi
}

# 显示结果统计
show_results() {
    log_step "📊 切片结果统计"
    echo ""
    
    # 切片统计
    total_slices=$(find "🎬Slice" -name "*.mp4" 2>/dev/null | wc -l)
    
    # 按视频统计
    echo -e "${CYAN}📈 总体统计：${NC}"
    echo "  🎬 总切片数: $total_slices 个"
    echo ""
    
    echo -e "${CYAN}📁 按视频统计：${NC}"
    for video_dir in $(find "🎬Slice" -maxdepth 1 -type d -name "video_*" 2>/dev/null); do
        video_name=$(basename "$video_dir")
        slices_count=$(find "$video_dir/slices" -name "*.mp4" 2>/dev/null | wc -l)
        echo "  📹 $video_name: $slices_count 个切片"
    done
    echo ""
    
    echo -e "${CYAN}📂 输出目录结构：${NC}"
    echo "  🎬Slice/"
    echo "  ├── video_1/slices/     # 视频切片文件"
    echo "  ├── video_2/slices/     # 视频切片文件"
    echo "  └── ..."
    echo ""
}

# 打开结果目录
open_results() {
    log_step "🔍 结果预览"
    echo ""
    
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
}

# 错误处理
handle_error() {
    log_error "切片处理过程中发生错误"
    echo ""
    echo -e "${YELLOW}🔧 常见问题排查：${NC}"
    echo "  1. 检查 ffmpeg 是否正确安装"
    echo "  2. 检查磁盘空间是否充足"
    echo "  3. 检查视频文件是否损坏"
    echo "  4. 检查 🍭Origin 目录权限"
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
    show_video_list
    user_confirm
    
    echo ""
    log_step "🚀 开始执行视频切片处理..."
    echo ""
    
    # 记录开始时间
    start_time=$(date +%s)
    
    # 执行切片处理
    execute_video_slicing
    
    # 记录结束时间
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    minutes=$((duration / 60))
    seconds=$((duration % 60))
    
    # 显示结果
    echo ""
    echo -e "${GREEN}🎉 视频切片处理完成！${NC}"
    echo -e "${CYAN}⏱️  总耗时: ${minutes}分${seconds}秒${NC}"
    echo ""
    
    show_results
    open_results
    
    echo ""
    log_info "切片处理完毕，可继续使用标签处理程序！"
    echo ""
    read -p "按任意键退出..." -n 1 -r
}

# 运行主程序
main "$@" 