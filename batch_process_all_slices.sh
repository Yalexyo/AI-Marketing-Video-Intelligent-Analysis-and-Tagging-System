#!/bin/bash

# =============================================================================
# 🎬 批量处理所有视频切片目录
# 功能：处理🍭Origin下所有视频目录的slices文件夹
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

echo -e "${MAGENTA}"
echo "════════════════════════════════════════════════════════════════"
echo "🎬 批量处理所有视频切片目录"
echo "════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# 扫描🍭Origin目录下的所有视频目录
echo -e "${CYAN}🔍 扫描🍭Origin目录...${NC}"
video_dirs=()
for dir in 🍭Origin/*/; do
    if [ -d "$dir" ] && [ -d "${dir}slices" ]; then
        video_dirs+=("$dir")
        echo -e "  📁 发现: $(basename "$dir")"
    fi
done

total_dirs=${#video_dirs[@]}
echo -e "${GREEN}✅ 总共发现 $total_dirs 个视频目录${NC}"
echo ""

# 显示处理计划
echo -e "${YELLOW}📋 处理计划：${NC}"
for i in "${!video_dirs[@]}"; do
    dir="${video_dirs[$i]}"
    video_name=$(basename "$dir")
    slice_count=$(find "${dir}slices" -name "*.mp4" 2>/dev/null | wc -l)
    echo -e "  $((i+1)). $video_name (${slice_count}个切片)"
done
echo ""

# 用户确认
echo -e "${YELLOW}⚠️  即将开始批量处理：${NC}"
echo "  🛠️  处理模式：本地FFmpeg转场检测"
echo "  📁 输出位置：🎬Slice目录"
echo "  ⏱️  预计耗时：10-30分钟"
echo ""
read -p "是否继续？(y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}用户取消操作${NC}"
    exit 0
fi

# 开始批量处理
echo -e "${GREEN}🚀 开始批量处理...${NC}"
echo ""

start_time=$(date +%s)
success_count=0
failed_count=0

for i in "${!video_dirs[@]}"; do
    dir="${video_dirs[$i]}"
    video_name=$(basename "$dir")
    slice_count=$(find "${dir}slices" -name "*.mp4" 2>/dev/null | wc -l)
    
    echo -e "${BLUE}[$((i+1))/$total_dirs] 处理: $video_name (${slice_count}个切片)${NC}"
    
    # 执行处理
    cd video_to_slice
    if uv run run.py --input "../${dir}slices" --mode local --concurrent 1 --quiet; then
        echo -e "${GREEN}  ✅ 处理完成${NC}"
        ((success_count++))
    else
        echo -e "${RED}  ❌ 处理失败${NC}"
        ((failed_count++))
    fi
    cd ..
    
    echo ""
done

# 统计结果
end_time=$(date +%s)
duration=$((end_time - start_time))
minutes=$((duration / 60))
seconds=$((duration % 60))

echo -e "${MAGENTA}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 批量处理完成！${NC}"
echo -e "${CYAN}📊 处理统计：${NC}"
echo -e "  ✅ 成功: $success_count/$total_dirs"
echo -e "  ❌ 失败: $failed_count/$total_dirs"
echo -e "  ⏱️  总耗时: ${minutes}分${seconds}秒"
echo ""

# 显示结果统计
echo -e "${CYAN}📁 输出结果统计：${NC}"
total_output_dirs=$(find "🎬Slice" -maxdepth 1 -type d ! -name "🎬Slice" ! -name "✅" | wc -l)
echo -e "  📂 总输出目录: $total_output_dirs 个"
echo -e "  📍 输出位置: 🎬Slice/"
echo ""

read -p "按任意键退出..." -n 1 -r
echo "" 