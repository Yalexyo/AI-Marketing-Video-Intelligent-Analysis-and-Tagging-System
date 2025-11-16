#!/bin/bash

# =============================================================================
# 🎯 视频分类文件生成脚本 (原:视频文件优化整理)
# 功能：基于二级AI聚类结果生成最终分类文件结构
# 命名：{二级标签}_{视频主题描述}.mp4
# 版本：v2.0 - 基于JSON增强数据的智能文件生成
# =============================================================================

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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
    echo -e "${CYAN}"
    echo "════════════════════════════════════════════════════════════════"
    echo "🎯 视频分类文件生成程序 v2.0"
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo -e "${YELLOW}功能说明：${NC}"
    echo "  • 📊 基于增强JSON数据进行智能文件生成"
    echo "  • 🔍 读取一级主标签和二级分类结果"
    echo "  • 📝 使用语义化命名：{二级标签}_{视频主题描述}.mp4"
    echo "  • 📁 创建扁平化目录结构，提升使用体验"
    echo "  • 📄 生成详细CSV报告供数据分析"
    echo ""
    echo -e "${YELLOW}前置条件 (必需)：${NC}"
    echo "  ✅ 步骤1: ./视频分类_一级主标签.sh (JSON增强: main_tag字段)"
    echo "  ✅ 步骤2: ./视频分类_二级副标签.sh (JSON增强: secondary_category字段)"
    echo "  📂 步骤3: 本脚本 (文件生成: 最终分类结构)"
    echo ""
    echo -e "${YELLOW}新架构优势：${NC}"
    echo "  🎯 数据驱动：直接从增强JSON读取分析结果"
    echo "  ⚡ 高效处理：无需依赖中间目录结构"
    echo "  📂 智能命名：营养科学_HMO成分介绍.mp4"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo ""
}

# 检查前置条件
check_prerequisites() {
    log_step "🔍 检查前置条件..." >&2
    
    local has_main_tag=false
    local has_secondary=false
    
    # 检查🎬Slice目录
    if [ ! -d "🎬Slice" ]; then
        log_error "🎬Slice 目录不存在" >&2
        exit 1
    fi
    
    # 检查JSON文件
    local json_count=$(find "🎬Slice" -name "*_analysis.json"  | wc -l)
    if [ "$json_count" -eq 0 ]; then
        log_error "未找到分析JSON文件，请先运行视频分析" >&2
        exit 1
    fi
    
    # 检查一级主标签完整性
    local main_tag_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"main_tag"' {} \; | wc -l)
    if [ "$main_tag_count" -gt 0 ]; then
        has_main_tag=true
        log_info "✅ 一级主标签: $main_tag_count/$json_count 个文件已分析" >&2
    else
        log_error "❌ 未找到一级主标签分析结果" >&2
        log_error "请先运行：./视频分类_一级主标签.sh" >&2
        exit 1
    fi
    
    # 检查二级分析完整性
    local secondary_count=$(find "🎬Slice" -name "*_analysis.json"  -exec grep -l '"secondary_category"' {} \; | wc -l)
    if [ "$secondary_count" -gt 0 ]; then
        has_secondary=true
        log_info "✅ 二级分类: $secondary_count/$json_count 个文件已分析" >&2
    else
        log_error "❌ 未找到二级分析结果" >&2
        log_error "请先运行：./视频分类_二级副标签.sh" >&2
        exit 1
    fi
    
    # 完整性检查
    if [ "$has_main_tag" = true ] && [ "$has_secondary" = true ]; then
        log_info "🎯 前置条件检查通过，可以开始文件生成" >&2
        
        # 创建输出目录
        local timestamp=$(date +"%Y%m%d_%H%M%S")
        local output_dir="📁生成结果/视频分类文件生成_${timestamp}"
        
        if [ ! -d "📁生成结果" ]; then
            mkdir -p "📁生成结果"
        fi
        
        mkdir -p "$output_dir"
        log_info "📁 创建输出目录: $(basename "$output_dir")" >&2
        
        echo "$output_dir"
    else
        log_error "❌ 前置条件不满足，无法继续" >&2
        exit 1
    fi
}

# 从JSON文件提取完整信息
extract_json_info() {
    local json_file="$1"
    
    if [ ! -f "$json_file" ]; then
        echo "||"
        return
    fi
    
    # 提取主要字段
    local main_tag=$(grep '"main_tag"' "$json_file" | head -1 | sed 's/.*"main_tag": "\([^"]*\)".*/\1/' | sed 's/[<>:"/\\|?*]/_/g')
    local secondary_category=$(grep '"secondary_category"' "$json_file" | head -1 | sed 's/.*"secondary_category": "\([^"]*\)".*/\1/' | sed 's/[<>:"/\\|?*]/_/g')
    local object_desc=$(grep '"object"' "$json_file" | head -1 | sed 's/.*"object": "\([^"]*\)".*/\1/' | sed 's/[<>:"/\\|?*]/_/g')
    
    # 清理和格式化
    [ -z "$main_tag" ] && main_tag="未分类"
    [ -z "$secondary_category" ] && secondary_category="其他"
    [ -z "$object_desc" ] && object_desc="视频片段"
    
    echo "$main_tag|$secondary_category|$object_desc"
}

# 安全的文件名生成
generate_safe_filename() {
    local secondary_tag="$1"
    local theme_desc="$2"
    local extension="$3"
    
    # 清理二级标签和主题描述
    local clean_tag=$(echo "$secondary_tag" | sed 's/[<>:"/\\|?*]/_/g')
    local clean_desc=$(echo "$theme_desc" | sed 's/[<>:"/\\|?*]/_/g')
    
    # 限制文件名长度
    if [ ${#clean_desc} -gt 30 ]; then
        clean_desc="${clean_desc:0:27}..."
    fi
    
    echo "${clean_tag}_${clean_desc}.${extension}"
}

# 处理文件名冲突
handle_filename_conflict() {
    local target_dir="$1"
    local base_filename="$2"
    
    local counter=1
    local filename="$base_filename"
    local name_part="${base_filename%.*}"
    local ext_part="${base_filename##*.}"
    
    while [ -f "$target_dir/$filename" ]; do
        filename="${name_part}_${counter}.${ext_part}"
        ((counter++))
    done
    
    echo "$filename"
}

# 处理单个视频文件
process_single_video() {
    local json_file="$1"
    local output_dir="$2"
    
    # 提取JSON信息
    local json_info=$(extract_json_info "$json_file")
    local main_tag=$(echo "$json_info" | cut -d'|' -f1)
    local secondary_category=$(echo "$json_info" | cut -d'|' -f2)
    local object_desc=$(echo "$json_info" | cut -d'|' -f3)
    
    # 跳过未分类或其他类别
    if [ "$main_tag" = "未分类" ] || [[ "$main_tag" == *"其他"* ]]; then
        return 0
    fi
    
    # 构建视频文件路径
    local json_dir=$(dirname "$json_file")
    local json_name=$(basename "$json_file" _analysis.json)
    local video_file=""
    
    # 查找对应的视频文件
    for ext in mp4 mov avi mkv; do
        local candidate="$json_dir/$json_name.$ext"
        if [ -f "$candidate" ]; then
            video_file="$candidate"
            break
        fi
    done
    
    if [ -z "$video_file" ] || [ ! -f "$video_file" ]; then
        log_warn "⚠️ 未找到视频文件: $json_name" >&2
        return 1
    fi
    
    # 创建主标签目录
    local main_tag_dir="$output_dir/$main_tag"
    mkdir -p "$main_tag_dir"
    
    # 生成新文件名
    local extension="${video_file##*.}"
    local new_filename=$(generate_safe_filename "$secondary_category" "$object_desc" "$extension")
    
    # 处理文件名冲突
    new_filename=$(handle_filename_conflict "$main_tag_dir" "$new_filename")
    
    # 复制文件
    if cp "$video_file" "$main_tag_dir/$new_filename"; then
        log_info "  ✅ $(basename "$video_file") → $main_tag/$new_filename" >&2
        return 0
    else
        log_error "  ❌ 复制失败: $(basename "$video_file")" >&2
        return 1
    fi
}

# 主处理函数
process_file_generation() {
    local output_dir=$(check_prerequisites)
    
    log_step "🚀 开始视频分类文件生成..." >&2
    log_info "📁 输出目录: $(basename "$output_dir")" >&2
    
    local total_processed=0
    local total_failed=0
    local total_skipped=0
    
    # 查找所有的JSON分析文件
    local json_files=$(find "🎬Slice" -name "*_analysis.json" )
    local total_files=$(echo "$json_files" | wc -l)
    
    log_info "📊 发现 $total_files 个分析文件，开始处理..." >&2
    
    # 按主标签分组统计
    local current_count=0
    local effect_count=0
    local product_count=0
    local promo_count=0
    local hook_count=0
    
    # 处理每个JSON文件
    while IFS= read -r json_file; do
        if [ -f "$json_file" ]; then
            ((current_count++))
            
            # 显示进度
            if [ $((current_count % 10)) -eq 0 ]; then
                log_info "📈 进度: $current_count/$total_files" >&2
            fi
            
            # 获取主标签信息
            local json_info=$(extract_json_info "$json_file")
            local main_tag=$(echo "$json_info" | cut -d'|' -f1)
            
            # 统计主标签
            if [ -n "$main_tag" ] && [ "$main_tag" != "未分类" ]; then
                case "$main_tag" in
                    *"使用效果"*) ((effect_count++)) ;;
                    *"产品介绍"*) ((product_count++)) ;;
                    *"促销机制"*) ((promo_count++)) ;;
                    *"钩子"*) ((hook_count++)) ;;
                esac
            fi
            
            # 处理单个视频文件
            if process_single_video "$json_file" "$output_dir"; then
                ((total_processed++))
            elif [ $? -eq 1 ]; then
                ((total_failed++))
            else
                ((total_skipped++))
            fi
        fi
    done <<< "$json_files"
    
    log_info "✅ 视频分类文件生成完成" >&2
    log_info "📊 总计：成功 $total_processed 个，失败 $total_failed 个，跳过 $total_skipped 个" >&2
    
    # 显示主标签分布
    echo "" >&2
    log_info "🎯 主标签分布：" >&2
    [ "$effect_count" -gt 0 ] && log_info "  📁 🌟 使用效果: $effect_count 个文件" >&2
    [ "$product_count" -gt 0 ] && log_info "  📁 🍼 产品介绍: $product_count 个文件" >&2
    [ "$promo_count" -gt 0 ] && log_info "  📁 🎁 促销机制: $promo_count 个文件" >&2
    [ "$hook_count" -gt 0 ] && log_info "  📁 🪝 钩子: $hook_count 个文件" >&2
    
    echo "$output_dir"
}

# 生成CSV报告
generate_csv_report() {
    local output_dir="$1"
    local csv_file="$output_dir/视频分类文件生成报告.csv"
    
    log_step "📊 生成CSV报告..." >&2
    
    # 创建CSV表头
    echo "文件名,主标签,二级标签,视频主题,原始路径,新路径" > "$csv_file"
    
    # 扫描输出目录生成报告
    for main_tag_dir in "$output_dir"/*/; do
        [ ! -d "$main_tag_dir" ] && continue
        if [ -d "$main_tag_dir" ]; then
            local main_tag=$(basename "$main_tag_dir")
            
            for video_file in "$main_tag_dir"/*.mp4 "$main_tag_dir"/*.mov "$main_tag_dir"/*.avi "$main_tag_dir"/*.mkv; do
                [ ! -f "$video_file" ] && continue
                local filename=$(basename "$video_file")
                local secondary_tag=$(echo "$filename" | cut -d'_' -f1)
                local theme=$(echo "$filename" | cut -d'_' -f2- | sed 's/\.[^.]*$//')
                local relative_path="$(basename "$output_dir")/$main_tag/$filename"
                
                echo "\"$filename\",\"$main_tag\",\"$secondary_tag\",\"$theme\",\"🎬Slice/...\",\"$relative_path\"" >> "$csv_file"
            done
        fi
    done
    
    log_info "📄 CSV报告已生成: $(basename "$csv_file")" >&2
}

# 显示生成结果
show_generation_result() {
    local output_dir="$1"
    
    if [ ! -d "$output_dir" ]; then
        log_error "输出目录不存在: $output_dir" >&2
        return 1
    fi
    
    echo "" >&2
    log_step "📊 文件生成结果预览" >&2
    echo "" >&2
    
    # 显示生成后的目录结构
    echo -e "${CYAN}📂 生成后目录结构：${NC}" >&2
    echo "  📁$(basename "$output_dir")/" >&2
    
    local total_videos=0
    
    for main_tag_dir in "$output_dir"/*/; do
        [ ! -d "$main_tag_dir" ] && continue
        if [ -d "$main_tag_dir" ]; then
            local main_tag=$(basename "$main_tag_dir")
            local file_count=$(find "$main_tag_dir" -maxdepth 1 \( -name "*.mp4" -o -name "*.mov" -o -name "*.avi" -o -name "*.mkv" \) | wc -l)
            echo "  ├── $main_tag/ ($file_count 个视频文件)" >&2
            ((total_videos += file_count))
            
            # 显示前3个文件示例
            local example_count=0
            for video_file in "$main_tag_dir"/*.mp4 "$main_tag_dir"/*.mov "$main_tag_dir"/*.avi "$main_tag_dir"/*.mkv; do
                [ ! -f "$video_file" ] && continue
                if [ -f "$video_file" ] && [ $example_count -lt 3 ]; then
                    echo "  │   ├── $(basename "$video_file")" >&2
                    ((example_count++))
                fi
            done
            
            if [ $file_count -gt 3 ]; then
                echo "  │   └── ... (共 $file_count 个文件)" >&2
            fi
        fi
    done
    
    # 检查CSV报告
    local csv_file="$output_dir/视频分类文件生成报告.csv"
    if [ -f "$csv_file" ]; then
        echo "  └── 📄 $(basename "$csv_file")" >&2
    fi
    
    echo "" >&2
    echo -e "${GREEN}✅ 文件生成完成！总计生成 $total_videos 个视频文件${NC}" >&2
    echo -e "${GREEN}   📁 目录: $(basename "$output_dir")${NC}" >&2
    echo -e "${GREEN}   📝 命名格式: {二级标签}_{视频主题描述}.mp4${NC}" >&2
    echo -e "${GREEN}   📊 详细报告: 视频分类文件生成报告.csv${NC}" >&2
    echo "" >&2
    echo -e "${CYAN}🎉 恭喜！视频分类处理流程全部完成！${NC}" >&2
    echo -e "${CYAN}   现在您可以直接使用生成的分类文件进行视频制作和编辑${NC}" >&2
}

# 主函数
main() {
    show_welcome
    
    # 检查自动模式
    if [ "$AUTO_MODE" = "true" ]; then
        log_info "🤖 自动模式：跳过用户确认，直接开始文件生成"
        confirm="y"
    else
        echo "⚠️  即将开始视频分类文件生成："
        echo "  📊 基于增强JSON数据进行智能生成"
        echo "  🔄 读取一级和二级AI分析结果"
        echo "  📝 使用语义化文件命名: {二级标签}_{视频主题}.mp4"
        echo "  📁 创建扁平化目录结构"
        echo "  📄 生成详细CSV报告"
        echo ""
        echo -e "${YELLOW}📋 确认前置条件已完成：${NC}"
        echo "  ✅ 步骤1: ./视频分类_一级主标签.sh"
        echo "  ✅ 步骤2: ./视频分类_二级副标签.sh"
        echo ""
        read -p "确认前置条件完成，开始文件生成？(y/N): " confirm
    fi
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        # 执行主处理流程
        local output_dir=$(process_file_generation)
        
        if [ -n "$output_dir" ] && [ -d "$output_dir" ]; then
            # 生成CSV报告
            generate_csv_report "$output_dir"
            
            # 显示结果
            show_generation_result "$output_dir"
            
            echo "" >&2
            log_info "🎉 视频分类文件生成完成！" >&2
            log_info "📁 结果目录: $output_dir" >&2
        else
            log_error "❌ 处理失败或输出目录未创建"
        fi
    else
        if [ "$AUTO_MODE" != "true" ]; then
            log_info "操作已取消" >&2
            echo "" >&2
            echo -e "${YELLOW}💡 使用说明：${NC}" >&2
            echo "  🔄 请按顺序执行完整的视频分类流程：" >&2
            echo "  1️⃣ ./视频分类_一级主标签.sh   # 添加main_tag字段" >&2
            echo "  2️⃣ ./视频分类_二级副标签.sh   # 添加secondary_category字段" >&2
            echo "  3️⃣ ./视频分类_文件生成.sh     # 生成最终文件结构 (本脚本)" >&2
        fi
    fi
}

# 运行主函数
main "$@" 