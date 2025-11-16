#!/bin/bash

# =============================================================================
# 🚀 一键DD - 视频智能分类处理程序
# 功能：一键完成从切片到最终分类文件的全流程处理
# 版本：v2.0 - 支持品牌感知的产品介绍分类
# 作者：AI Video Master
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

log_phase() {
    echo -e "${MAGENTA}[PHASE]${NC} $1"
}

# 显示欢迎信息
show_welcome() {
    clear
    echo -e "${MAGENTA}"
    echo "════════════════════════════════════════════════════════════════"
    echo "🚀 一键DD - AI视频智能分类处理程序 v2.0"
    echo "════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo -e "${CYAN}🎯 核心功能：${NC}"
    echo "  🔄 一键完成：切片 → 一级标签 → 二级标签 → 最终文件"
    echo "  🤖 智能分类：DeepSeek + Claude 双AI引擎"
    echo "  🏷️ 品牌感知：支持蕴淳、水奶、蓝钻三品牌自动识别"
    echo "  📁 语义命名：{二级标签}_{视频主题描述}.mp4"
    echo "  📊 全程监控：详细进度显示和错误处理"
    echo ""
    echo -e "${YELLOW}🎯 品牌感知分类体系：${NC}"
    echo "  🍼 产品介绍_蕴淳 → HMO功效、A2标签识别、营养科学、专业认证..."
    echo "  🍼 产品介绍_水奶 → 便携特性、即饮演示、新鲜品质、奶源介绍..."
    echo "  🍼 产品介绍_蓝钻 → 高端配方、升级特性、营养科学、专业认证..."
    echo "  🌟 使用效果 → 营养健康、智能发育、安全保护、成长标志..."
    echo "  🎁 促销机制 → 价格优势、限时活动、赠品套装、会员权益..."
    echo "  🪝 钩子 → 问题场景、需求痛点、紧迫时机、决策困扰..."
    echo ""
    echo -e "${YELLOW}⚡ 处理流程：${NC}"
    echo "  🏷️  阶段0: 视频标签分析 (5-10分钟) - 如需要"
    echo "  📋 阶段1: 一级主标签分类 (3-5分钟)"
    echo "  📊 阶段2: 二级副标签聚类 (8-15分钟)"
    echo "  📁 阶段3: 智能文件生成 (2-3分钟)"
    echo "  🎉 总耗时: 15-50分钟 (取决于文件数量和处理阶段)"
    echo ""
    echo -e "${YELLOW}💡 适用场景：${NC}"
    echo "  ✅ 批量处理大量视频切片"
    echo "  ✅ 需要精准的品牌分类"
    echo "  ✅ 要求语义化文件命名"
    echo "  ✅ 追求一键式完整流程"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo ""
}

# 检查系统依赖
check_system_dependencies() {
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
    
    # 检查必要的脚本文件
    local required_scripts=("视频分类_一级主标签.sh" "视频分类_二级副标签.sh" "视频分类_文件生成.sh")
    for script in "${required_scripts[@]}"; do
        if [ ! -f "$script" ]; then
            log_error "缺少必要脚本: $script"
            exit 1
        fi
    done
    
    # 检查视频标签分析脚本
    if [ ! -f "视频标签.sh" ]; then
        log_error "缺少必要脚本: 视频标签.sh"
        exit 1
    fi
    
    # 🔍 2. 统计有效视频文件数量（新逻辑：♻️文件也能被分析）
    # 旧逻辑：同时过滤♻️和❌文件
    # 新逻辑：只过滤❌文件，♻️文件允许正常分析
    slice_count=$(find "🎬Slice" -type f \( -name "*.mp4" -o -name "*.mov" -o -name "*.avi" -o -name "*.mkv" \) ! -name "❌*" 2>/dev/null | wc -l)

    # �� 3. 统计分析文件数量（包含♻️前缀的分析文件）
    json_count=$(find "🎬Slice" -type f -name "*_analysis.json" ! -name "❌*" 2>/dev/null | wc -l)
    
    # 全局变量，标记是否需要执行标签分析
    NEED_LABEL_ANALYSIS=false
    
    # 🔧 修复：智能判断是否需要标签分析
    if [ "$slice_count" -eq 0 ]; then
        log_error "🎬Slice 目录下未找到有效视频切片文件，请先运行视频切片程序"
        exit 1
    elif [ "$json_count" -eq 0 ]; then
        log_warn "🎬Slice 目录下未找到已标注的JSON文件，将自动执行视频标签分析"
        NEED_LABEL_ANALYSIS=true
    else
        # 🔧 新增：智能比较分析文件覆盖率
        # 使用bash内置算术运算，避免依赖bc命令
        if [ "$slice_count" -gt 0 ]; then
            coverage_percentage=$(( (json_count * 100) / slice_count ))
        else
            coverage_percentage=0
        fi
        
        # 如果分析文件数量少于视频文件数量，需要重新分析
        if [ "$json_count" -lt "$slice_count" ]; then
            missing_count=$((slice_count - json_count))
            log_warn "🎬 发现不完整的标签分析：$json_count/$slice_count 个文件已分析（覆盖率：${coverage_percentage}%）"
            log_warn "⚠️ 缺少 $missing_count 个文件的分析结果，将自动执行视频标签分析"
            log_warn "🚫 已自动排除带♻️和❌前缀的问题文件"
            NEED_LABEL_ANALYSIS=true
        else
            log_info "✅ 所有有效视频切片已完成标签分析"
        fi
    fi
    
    log_info "✅ 系统依赖检查通过"
    if [ "$NEED_LABEL_ANALYSIS" = true ]; then
        log_info "🎬 发现 $slice_count 个视频切片，需要标签分析"
    else
        log_info "🎬 发现 $slice_count 个视频切片（包含多镜头视频）"
        log_info "🎯 新逻辑：多镜头视频（♻️前缀）也会被正常分析，不再跳过"
        log_info "🚫 只过滤分析失败的视频文件（❌前缀）"
        log_info "📋 发现 $json_count 个已标注切片"
    fi
}

# 检查API配置
check_api_configuration() {
    log_step "🔧 检查API配置..."
    
    # 检查统一环境变量文件
    if [ ! -f ".env" ]; then
        log_error "❌ 项目根目录 .env 文件不存在"
        log_error "一键DD功能必需API密钥，请创建 .env 文件并配置以下API密钥："
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
        log_error "一键DD功能必需DeepSeek API密钥，请在项目根目录 .env 中配置："
        log_error "DEEPSEEK_API_KEY=your_deepseek_api_key"
        exit 1
    fi
    
    # 显示配置的API
    api_list=$(printf ", %s" "${api_keys_found[@]}")
    api_list=${api_list:2}  # 移除开头的", "
    log_info "✅ API配置检查通过 (已配置: $api_list)"
    
    # 智能升级机制提示
    if [[ " ${api_keys_found[@]} " =~ " OpenRouter/Claude " ]]; then
        log_info "🤖 智能双AI架构：DeepSeek + Claude智能升级"
    else
        log_info "🤖 标准模式：使用DeepSeek单模型（建议配置OpenRouter获得智能升级）"
    fi
}

# 显示处理概览
show_processing_overview() {
    log_step "📋 处理概览："
    echo ""
    
    # 统计切片文件
    total_json=0
    total_main_tagged=0
    total_secondary_tagged=0
    
    for video_dir in $(find "🎬Slice" -maxdepth 1 -type d ! -name "." ! -name ".." ! -name "🎬Slice" 2>/dev/null | grep -v "\.DS_Store"); do
        # 检查是否包含slices子目录
        if [ ! -d "$video_dir/slices" ]; then
            continue
        fi
        video_name=$(basename "$video_dir")
        json_count=$(find "$video_dir/slices" -name "*_analysis.json" 2>/dev/null | wc -l)
        
        # 统计已有标签的文件
        main_tag_count=0
        secondary_tag_count=0
        if [ "$json_count" -gt 0 ]; then
            for json_file in $(find "$video_dir/slices" -name "*_analysis.json" 2>/dev/null); do
                if grep -q '"main_tag"' "$json_file" 2>/dev/null; then
                    ((main_tag_count++))
                fi
                if grep -q '"secondary_category"' "$json_file" 2>/dev/null; then
                    ((secondary_tag_count++))
                fi
            done
        fi
        
        total_json=$((total_json + json_count))
        total_main_tagged=$((total_main_tagged + main_tag_count))
        total_secondary_tagged=$((total_secondary_tagged + secondary_tag_count))
        
        echo -e "  📹 ${BLUE}$video_name${NC}: $json_count 个切片 (一级:$main_tag_count, 二级:$secondary_tag_count)"
    done
    
    echo ""
    echo -e "${CYAN}📊 当前状态：${NC}"
    if [ "$NEED_LABEL_ANALYSIS" = true ]; then
        slice_count=$(find "🎬Slice" -name "*.mp4" 2>/dev/null | wc -l)
        echo "  🎬 发现视频切片: $slice_count 个"
        echo "  🏷️ 需要标签分析: $slice_count 个（阶段0）"
        echo "  📋 待一级分类: $slice_count 个（阶段1）"
        echo "  📊 待二级分类: $slice_count 个（阶段2）"
        echo "  📁 待文件生成: $slice_count 个（阶段3）"
    else
        echo "  📋 总已标注切片: $total_json 个"
        echo "  🎯 已有一级主标签: $total_main_tagged 个"
        echo "  📊 已有二级分类: $total_secondary_tagged 个"
        echo "  🆕 待处理: $((total_json - total_main_tagged)) 个（一级）"
        echo "  🆕 待处理: $((total_json - total_secondary_tagged)) 个（二级）"
    fi
    echo ""
    
    echo -e "${CYAN}🎯 预计处理时间：${NC}"
    
    # 根据是否需要标签分析调整时间估算
    if [ "$NEED_LABEL_ANALYSIS" = true ]; then
        slice_count=$(find "🎬Slice" -name "*.mp4" 2>/dev/null | wc -l)
        if [ "$slice_count" -lt 20 ]; then
            echo "  ⏱️ 完整流程 (<20个文件): 20-25分钟"
            echo "    ├── 🏷️ 阶段0 (标签分析): 8-12分钟"
            echo "    ├── 📋 阶段1 (一级分类): 3-5分钟"
            echo "    ├── 📊 阶段2 (二级分类): 6-8分钟"
            echo "    └── 📁 阶段3 (文件生成): 2-3分钟"
        elif [ "$slice_count" -lt 50 ]; then
            echo "  ⏱️ 完整流程 (20-50个文件): 25-35分钟"
            echo "    ├── 🏷️ 阶段0 (标签分析): 12-18分钟"
            echo "    ├── 📋 阶段1 (一级分类): 4-6分钟"
            echo "    ├── 📊 阶段2 (二级分类): 8-12分钟"
            echo "    └── 📁 阶段3 (文件生成): 3-5分钟"
        else
            echo "  ⏱️ 完整流程 (>50个文件): 35-50分钟"
            echo "    ├── 🏷️ 阶段0 (标签分析): 18-30分钟"
            echo "    ├── 📋 阶段1 (一级分类): 6-10分钟"
            echo "    ├── 📊 阶段2 (二级分类): 10-15分钟"
            echo "    └── 📁 阶段3 (文件生成): 3-8分钟"
        fi
    else
        if [ "$total_json" -lt 50 ]; then
            echo "  ⏱️ 部分流程 (<50个文件): 10-15分钟"
            echo "    ├── 📋 阶段1 (一级分类): 3-5分钟"
            echo "    ├── 📊 阶段2 (二级分类): 6-8分钟"
            echo "    └── 📁 阶段3 (文件生成): 2-3分钟"
        elif [ "$total_json" -lt 200 ]; then
            echo "  ⏱️ 部分流程 (50-200个文件): 15-25分钟"
            echo "    ├── 📋 阶段1 (一级分类): 4-8分钟"
            echo "    ├── 📊 阶段2 (二级分类): 8-15分钟"
            echo "    └── 📁 阶段3 (文件生成): 3-5分钟"
        else
            echo "  ⏱️ 部分流程 (>200个文件): 25-40分钟"
            echo "    ├── 📋 阶段1 (一级分类): 8-15分钟"
            echo "    ├── 📊 阶段2 (二级分类): 15-25分钟"
            echo "    └── 📁 阶段3 (文件生成): 5-10分钟"
        fi
    fi
    echo ""
}

# 用户确认
user_confirm() {
    echo -e "${YELLOW}🚀 即将开始一键DD全流程处理：${NC}"
    echo ""
    echo -e "${CYAN}📋 处理阶段：${NC}"
    # 根据是否需要标签分析显示阶段0
    if [ "$NEED_LABEL_ANALYSIS" = true ]; then
        echo "  🔄 阶段0: 视频标签分析（基础识别）"
        echo "    ├── 🎯 物体识别 (产品、人物、场景)"
        echo "    ├── 🎭 情绪检测 (开心、温馨、专业)"
        echo "    ├── 🏷️ 品牌元素 (包装、logo、标识)"
        echo "    └── 🌐 自动翻译 (统一中文格式)"
        echo ""
    fi
    echo "  🔄 阶段1: 一级主标签分类（品牌感知）"
    echo "    ├── 🍼 产品介绍_蕴淳 (HMO、A2、营养科学)"
    echo "    ├── 🍼 产品介绍_水奶 (便携、即饮、新鲜)"
    echo "    ├── 🍼 产品介绍_蓝钻 (高端、升级、品质)"
    echo "    ├── 🌟 使用效果 (营养健康、智能发育)"
    echo "    ├── 🎁 促销机制 (价格、活动、赠品)"
    echo "    └── 🪝 钩子 (问题、痛点、困扰)"
    echo ""
    echo "  🔄 阶段2: 二级副标签聚类分析"
    echo "    └── 为每个主标签进行4-7个子分类细分"
    echo ""
    echo "  🔄 阶段3: 智能文件生成"
    echo "    └── 生成语义化命名的最终分类文件"
    echo ""
    echo -e "${CYAN}🤖 AI处理机制：${NC}"
    echo "  🥇 主模型：DeepSeek Chat（快速高效）"
    echo "  🏆 升级模型：Claude 4 Sonnet（高精度验证）"
    echo "  📈 智能切换：错误率>15%时自动升级"
    echo "  🎯 置信度过滤：仅保留高置信度结果"
    echo ""
    echo -e "${CYAN}📁 最终输出：${NC}"
    echo "  📂 📁生成结果/视频分类文件生成_时间戳/"
    echo "  ├── 🍼 产品介绍_蕴淳/"
    echo "  │   ├── HMO功效_母乳低聚糖介绍.mp4"
    echo "  │   └── A2标签识别_A2蛋白优势.mp4"
    echo "  ├── 🍼 产品介绍_水奶/"
    echo "  │   ├── 便携特性_随身携带演示.mp4"
    echo "  │   └── 即饮演示_开盖即饮.mp4"
    echo "  └── 🌟 使用效果/"
    echo "      ├── 营养健康_宝宝活力表现.mp4"
    echo "      └── 智能发育_认知能力提升.mp4"
    echo ""
    echo -e "${YELLOW}⚠️ 注意事项：${NC}"
    if [ "$NEED_LABEL_ANALYSIS" = true ]; then
        echo "  💰 API调用费用：完整流程 (预估$3-15，含视觉分析)"
        echo "  ⏱️ 处理时间：20-50分钟不等 (含阶段0)"
    else
        echo "  💰 API调用费用：部分流程 (预估$2-8，无视觉分析)"
        echo "  ⏱️ 处理时间：15-40分钟不等 (跳过阶段0)"
    fi
    echo "  🔄 可中断恢复：支持断点续传"
    echo "  💾 自动备份：原文件安全保护"
    echo ""
    read -p "确认开始一键DD处理？(y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "用户取消操作"
        exit 0
    fi
}

# 通用超时执行函数（macOS兼容）
execute_with_timeout() {
    local timeout_seconds=$1
    local command_name=$2
    shift 2
    local command_args="$@"
    
    # macOS兼容性：检查timeout命令是否可用
    TIMEOUT_CMD=""
    if command -v timeout &> /dev/null; then
        TIMEOUT_CMD="timeout $timeout_seconds"
    elif command -v gtimeout &> /dev/null; then
        TIMEOUT_CMD="gtimeout $timeout_seconds"
    else
        log_warn "⚠️ timeout命令不可用，将直接执行$command_name（无超时限制）"
    fi
    
    if [ -n "$TIMEOUT_CMD" ]; then
        if $TIMEOUT_CMD bash -c "$command_args"; then
            return 0
        else
            local exit_code=$?
            if [ $exit_code -eq 124 ]; then
                log_error "❌ $command_name 超时：处理超过 $((timeout_seconds/60)) 分钟"
            else
                log_error "❌ $command_name 失败 (退出码: $exit_code)"
            fi
            return $exit_code
        fi
    else
        # 没有timeout命令，直接执行
        if bash -c "$command_args"; then
            return 0
        else
            local exit_code=$?
            log_error "❌ $command_name 失败 (退出码: $exit_code)"
            return $exit_code
        fi
    fi
}

# 执行阶段0：视频标签分析（如果需要）
execute_phase0() {
    if [ "$NEED_LABEL_ANALYSIS" != true ]; then
        log_info "⏭️  跳过阶段0：已存在标签分析结果"
        return 0
    fi
    
    log_phase "🏷️ 阶段0: 视频标签分析"
    echo ""
    
    log_info "🚀 启动视频标签分析..."
    log_info "🎬 检测到需要分析的视频切片"
    
    # 检查是否存在脚本
    if [ ! -f "视频标签.sh" ]; then
        log_error "❌ 未找到 视频标签.sh 脚本"
        return 1
    fi
    
    # 执行视频标签分析（自动模式）
    if execute_with_timeout 1800 "阶段0" '
        export AUTO_MODE=true
        exec ./视频标签.sh
    '; then
        # 再次检查是否生成了标注文件
        new_json_count=$(find "🎬Slice" -name "*_analysis.json" 2>/dev/null | wc -l)
        if [ "$new_json_count" -gt 0 ]; then
            log_info "✅ 阶段0完成：视频标签分析成功 ($new_json_count 个文件已标注)"
            return 0
        else
            log_error "❌ 阶段0失败：未生成标注文件"
            return 1
        fi
    else
        return 1
    fi
}

# 执行阶段1：一级主标签分类
execute_phase1() {
    log_phase "🎯 阶段1: 一级主标签分类（品牌感知）"
    echo ""
    
    log_info "🚀 启动一级主标签分类..."
    
    # 检查是否存在脚本
    if [ ! -f "视频分类_一级主标签.sh" ]; then
        log_error "❌ 未找到 视频分类_一级主标签.sh 脚本"
        return 1
    fi
    
    # 执行一级分类（自动模式）
    if execute_with_timeout 1800 "阶段1" '
        export AUTO_MODE=true
        exec ./视频分类_一级主标签.sh
    '; then
        log_info "✅ 阶段1完成：一级主标签分类成功"
        return 0
    else
        return 1
    fi
}

# 执行阶段2：二级副标签分析
execute_phase2() {
    log_phase "📊 阶段2: 二级副标签聚类分析"
    echo ""
    
    # 检查阶段2结果
    # 支持灵活的文件夹结构：既支持 /slices/ 子文件夹，也支持直接在项目目录下
    main_tag_count=$(find "🎬Slice" -name "*_analysis.json" -exec grep -l '"main_tag"' {} \; 2>/dev/null | wc -l)
    if [ "$main_tag_count" -eq 0 ]; then
        log_error "❌ 阶段1未完成：未找到一级主标签分析结果"
        return 1
    fi
    
    log_info "🚀 启动二级副标签分析..."
    log_info "📋 检测到 $main_tag_count 个已分类的一级主标签文件"
    
    # 检查是否存在脚本
    if [ ! -f "视频分类_二级副标签.sh" ]; then
        log_error "❌ 未找到 视频分类_二级副标签.sh 脚本"
        return 1
    fi
    
    # 执行二级分析（自动模式）
    if execute_with_timeout 2400 "阶段2" '
        export AUTO_MODE=true
        exec ./视频分类_二级副标签.sh
    '; then
        log_info "✅ 阶段2完成：二级副标签分析成功"
        return 0
    else
        return 1
    fi
}

# 执行阶段3：智能文件生成
execute_phase3() {
    log_phase "📁 阶段3: 智能文件生成（语义化命名）"
    echo ""
    
    # 🔍 智能处理状态检测
    log_info "🔍 智能检测当前文件处理状态..."
    
    # 🚨 防重复检查：检查是否已存在最近生成的结果
    existing_results=$(find "📁生成结果" -maxdepth 1 -type d \( -name "视频分类文件生成_*" -o -name "统一AI分类v4_*" \) -newer "🎬Slice" 2>/dev/null)
    
    if [ -n "$existing_results" ]; then
        log_info "🚨 发现最近生成的结果目录："
        echo "$existing_results" | while read -r result_dir; do
            if [ -d "$result_dir" ]; then
                result_name=$(basename "$result_dir")
                file_count=$(find "$result_dir" -name "*.mp4" -o -name "*.mov" -o -name "*.avi" -o -name "*.mkv" 2>/dev/null | wc -l)
                log_info "  📁 $result_name ($file_count 个视频文件)"
            fi
        done
        
        # 检查最新结果目录的文件数量
        latest_existing=$(echo "$existing_results" | sort | tail -1)
        if [ -d "$latest_existing" ]; then
            existing_file_count=$(find "$latest_existing" -name "*.mp4" -o -name "*.mov" -o -name "*.avi" -o -name "*.mkv" 2>/dev/null | wc -l)
            
            if [ $existing_file_count -gt 0 ]; then
                log_info "✅ 阶段3已完成：发现最近生成的完整结果 ($existing_file_count 个文件)"
                log_info "🎯 跳过重复处理，直接使用已有结果"
                return 0
            fi
        fi
    fi
    
    # 检查标准文件的分析状态（支持灵活的文件夹结构）
    total_slices_json=$(find "🎬Slice" -name "*_analysis.json" 2>/dev/null | wc -l)
    completed_main=$(find "🎬Slice" -name "*_analysis.json" -exec grep -l '"main_tag"' {} \; 2>/dev/null | wc -l)
    completed_secondary=$(find "🎬Slice" -name "*_analysis.json" -exec grep -l '"secondary_category"' {} \; 2>/dev/null | wc -l)
    
    # 计算未完成的文件数量
    pending_main=$((total_slices_json - completed_main))
    pending_secondary=$((total_slices_json - completed_secondary))
    
    log_info "📊 文件分析状态："
    log_info "  📁 总分析文件: $total_slices_json"
    log_info "  ✅ 已完成一级分析: $completed_main"
    log_info "  ✅ 已完成二级分析: $completed_secondary"
    log_info "  ⏳ 待处理: 一级($pending_main), 二级($pending_secondary)"
    
    # 检查阶段2是否完成
    if [ "$completed_secondary" -eq 0 ]; then
        log_error "❌ 阶段2未完成：未找到二级分析结果"
        return 1
    fi
    
    # 🚀 统一AI增强模式处理
    if [ $pending_main -eq 0 ] && [ $pending_secondary -eq 0 ]; then
        log_info "🎯 智能检测：所有文件已完成分析，AI增强模式将快速处理"
        log_info "⚡ AI增强模式将智能跳过重复分析，直接生成文件..."
    else
        log_info "🎯 智能检测：发现未完成分析的文件，AI增强模式将补充分析"
        log_info "🤖 AI增强模式将完成剩余分析并生成文件..."
    fi
    
    # 🤖 统一AI增强模式
    log_info "🤖 启动AI增强语义化文件生成..."
    
    # 检查label_to_classifier模块
    if [ ! -d "label_to_classifier" ]; then
        log_error "❌ 未找到 label_to_classifier 模块"
        return 1
    fi
    
    # 先记录执行前的结果目录数量
    local before_count=$(find "📁生成结果" -maxdepth 1 -type d -name "统一AI分类v4_*" 2>/dev/null | wc -l)
    
    if execute_with_timeout 600 "阶段3统一AI增强" '
        cd label_to_classifier
        uv run python run.py enhanced-cluster
        cd ..
    '; then
        # 命令执行成功，验证处理结果
        local after_count=$(find "📁生成结果" -maxdepth 1 -type d -name "统一AI分类v4_*" 2>/dev/null | wc -l)
        
        if [ $after_count -gt $before_count ]; then
            # 确实生成了新的结果目录
            latest_result=$(find "📁生成结果" -maxdepth 1 -type d -name "统一AI分类v4_*" 2>/dev/null | sort | tail -1)
            file_count=$(find "$latest_result" -name "*.mp4" -o -name "*.mov" -o -name "*.avi" -o -name "*.mkv" 2>/dev/null | wc -l)
            log_info "✅ 阶段3完成：统一AI增强模式处理成功 (生成 $file_count 个文件)"
            return 0
        else
            # 命令成功但没有生成新目录，重新检查状态
            log_warn "⚠️ 统一AI增强模式执行成功但没有生成新的结果目录"
            
            # 重新检查处理状态（支持灵活的文件夹结构）
            total_check=$(find "🎬Slice" -name "*_analysis.json" 2>/dev/null | wc -l)
            completed_check=$(find "🎬Slice" -name "*_analysis.json" -exec grep -l '"secondary_category"' {} \; 2>/dev/null | wc -l)
            pending_check=$((total_check - completed_check))
            
            if [ $pending_check -gt 0 ]; then
                log_warn "⚠️ 发现 $pending_check 个文件未完成二级分析，需要使用备用方案继续处理"
                log_info "📊 总文件: $total_check, 已完成: $completed_check, 待处理: $pending_check"
                # 不返回成功，继续执行备用方案
            else
                log_info "✅ 所有文件都已完成分析，统一AI增强模式执行成功"
                return 0  # 所有文件都完成了，可以安全返回成功
            fi
        fi
    fi
    
    # 统一AI增强模式失败
    log_error "❌ 统一AI增强模式执行失败"
    return 1
}

# 显示最终结果
show_final_results() {
    log_step "🎉 一键DD处理完成！"
    echo ""
    
    # 查找最新的生成结果目录（支持多种命名格式）
    latest_result=$(find "📁生成结果" -maxdepth 1 -type d \( -name "视频分类文件生成_*" -o -name "统一AI分类v4_*" -o -name "整合语义化文件_*" -o -name "临时语义化转换_*" \) 2>/dev/null | sort | tail -1)
    
    if [ -n "$latest_result" ] && [ -d "$latest_result" ]; then
        echo -e "${GREEN}📁 输出目录: $(basename "$latest_result")${NC}"
        echo ""
        
        # 统计各主标签的文件数量
        local total_files=0
        echo -e "${CYAN}📊 分类结果统计：${NC}"
        
        for main_tag_dir in "$latest_result"/*/; do
            [ ! -d "$main_tag_dir" ] && continue
            if [ -d "$main_tag_dir" ]; then
                local main_tag=$(basename "$main_tag_dir")
                local file_count=$(find "$main_tag_dir" -maxdepth 1 \( -name "*.mp4" -o -name "*.mov" -o -name "*.avi" -o -name "*.mkv" \) | wc -l)
                echo "  📁 $main_tag: $file_count 个视频文件"
                ((total_files += file_count))
            fi
        done
        
        echo ""
        echo -e "${GREEN}✅ 总计生成: $total_files 个分类视频文件${NC}"
        echo -e "${GREEN}📝 命名格式: {二级标签}_{视频主题描述}.mp4${NC}"
        
        # 检查CSV报告
        local csv_file="$latest_result/视频分类文件生成报告.csv"
        if [ -f "$csv_file" ]; then
            echo -e "${GREEN}📊 详细报告: $(basename "$csv_file")${NC}"
        fi
        
        echo ""
        echo -e "${CYAN}🎯 文件示例：${NC}"
        local example_count=0
        for main_tag_dir in "$latest_result"/*/; do
            [ ! -d "$main_tag_dir" ] && continue
            if [ -d "$main_tag_dir" ] && [ $example_count -lt 6 ]; then
                local main_tag=$(basename "$main_tag_dir")
                for video_file in "$main_tag_dir"/*.mp4 "$main_tag_dir"/*.mov "$main_tag_dir"/*.avi "$main_tag_dir"/*.mkv; do
                    [ ! -f "$video_file" ] && continue
                    if [ -f "$video_file" ] && [ $example_count -lt 6 ]; then
                        echo "  📄 $main_tag/$(basename "$video_file")"
                        ((example_count++))
                        break
                    fi
                done
            fi
        done
        
    else
        log_warn "⚠️ 未找到生成结果目录"
    fi
    
    echo ""
    echo -e "${MAGENTA}🎉 恭喜！一键DD处理流程全部完成！${NC}"
    echo -e "${MAGENTA}现在您可以直接使用生成的品牌分类文件进行视频制作${NC}"
}

# 错误处理
handle_error() {
    local exit_code=$?
    log_error "一键DD处理过程中发生错误 (退出码: $exit_code)"
    echo ""
    echo -e "${YELLOW}🔧 常见问题排查：${NC}"
    echo "  1. 检查网络连接是否正常"
    echo "  2. 检查API密钥配置是否正确"
    echo "  3. 检查已标注JSON文件是否存在"
    echo "  4. 检查磁盘空间是否充足"
    echo "  5. 确认DeepSeek API余额充足"
    echo ""
    echo -e "${CYAN}🔧 恢复建议：${NC}"
    echo "  • 可以单独运行失败的阶段脚本"
    echo "  • 检查 .env 文件中的API密钥"
    echo "  • 确保🎬Slice目录包含已标注的JSON文件"
    echo "  • 检查label_to_classifier模块是否正常"
    echo ""
    read -p "按任意键退出..." -n 1 -r
    exit $exit_code
}

# 主程序流程
main() {
    # 设置错误处理
    trap handle_error ERR
    
    # 记录开始时间
    start_time=$(date +%s)
    
    # 执行步骤
    show_welcome
    check_system_dependencies
    check_api_configuration
    show_processing_overview
    user_confirm
    
    echo ""
    log_phase "🚀 开始一键DD全流程处理..."
    echo ""
    
    # 执行四个阶段（从阶段0开始）
    if execute_phase0; then
        echo ""
        sleep 2
        
        if execute_phase1; then
        echo ""
        sleep 2
        
        if execute_phase2; then
            echo ""
            sleep 2
            
            if execute_phase3; then
                # 记录结束时间
                end_time=$(date +%s)
                duration=$((end_time - start_time))
                minutes=$((duration / 60))
                seconds=$((duration % 60))
                
                echo ""
                echo -e "${GREEN}🎉 一键DD全流程处理成功！${NC}"
                echo -e "${CYAN}⏱️  总耗时: ${minutes}分${seconds}秒${NC}"
                echo ""
                
                show_final_results
                else
                    log_error "❌ 阶段3失败，文件生成未完成"
                    exit 1
                fi
            else
                log_error "❌ 阶段2失败，二级分析未完成"
                exit 1
            fi
        else
            log_error "❌ 阶段1失败，一级分类未完成"
            exit 1
        fi
    else
        log_error "❌ 阶段0失败，视频标签分析未完成"
        exit 1
    fi
    
    echo ""
    log_info "🎯 一键DD处理完成！现在您可以使用生成的分类文件"
    echo ""
    read -p "按任意键退出..." -n 1 -r
}

# 运行主程序
main "$@" 