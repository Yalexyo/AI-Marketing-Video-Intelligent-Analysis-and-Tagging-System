#!/usr/bin/env python3
"""
产品介绍生成脚本 - 🍭Origin驱动架构
支持临时输入目录处理模式，适配一键脚本调用

使用示例:
python run.py input_dir                      # 处理指定输入目录（临时模式）
python run.py input_dir -o output_dir       # 指定输出目录
python run.py --help                        # 查看帮助
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import re
import json
from datetime import datetime

# 添加src目录到Python路径
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# 导入环境变量加载器
try:
    from env_loader import (
        get_deepseek_api_key, validate_config, get_config_summary,
        get_min_segment_duration, get_max_segment_duration
    )
except ImportError:
    from src.env_loader import (
        get_deepseek_api_key, validate_config, get_config_summary,
        get_min_segment_duration, get_max_segment_duration
    )

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def scan_temp_input_dir(input_dir: Path) -> tuple:
    """扫描临时输入目录，匹配SRT和视频文件对"""
    srt_files = []
    video_files = []
    
    # 支持的视频格式
    supported_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv']
    
    for file_path in input_dir.iterdir():
        if file_path.is_file():
            if file_path.suffix.lower() == '.srt':
                srt_files.append(file_path)
            elif file_path.suffix.lower() in supported_formats:
                video_files.append(file_path)
    
    # 匹配文件对
    matched_pairs = []
    for srt_file in srt_files:
        srt_stem = srt_file.stem
        # 查找匹配的视频文件
        for video_file in video_files:
            video_stem = video_file.stem
            if srt_stem == video_stem or srt_stem.startswith(video_stem):
                matched_pairs.append((srt_file, video_file))
                break
    
    return matched_pairs

def generate_simplified_json_report(segment_info: dict, video_file: Path, output_file: Path) -> Path:
    """生成简化的JSON分析报告"""
    
    # 提取品牌类型
    topic = segment_info.get('topic', '')
    product_brand_type = "未分类"
    if '蕴淳' in topic:
        product_brand_type = "启赋蕴淳"
    elif '水奶' in topic:
        product_brand_type = "启赋水奶"  
    elif '蓝钻' in topic:
        product_brand_type = "启赋蓝钻"
    elif '启赋' in topic:
        product_brand_type = "启赋蕴淳"  # 默认归类
        
    # 构建简化JSON结构
    report = {
        "basic_info": {
            "file_name": output_file.name,
            "original_video": video_file.name,
            "creation_time": datetime.now().isoformat(),
            "processing_version": "v2.0"
        },
        "timing_info": {
            "start_time": f"{int(segment_info.get('start_time', 0))//60:02d}:{int(segment_info.get('start_time', 0))%60:02d}.{int((segment_info.get('start_time', 0) % 1) * 1000):03d}",
            "end_time": f"{int(segment_info.get('end_time', 0))//60:02d}:{int(segment_info.get('end_time', 0))%60:02d}.{int((segment_info.get('end_time', 0) % 1) * 1000):03d}",
            "duration_seconds": round(segment_info.get('duration', 0), 2),
            "srt_segment_range": f"片段 {'-'.join(map(str, segment_info.get('sequence_ids', [])))}"
        },
        "product_analysis": {
            "confidence_score": round(segment_info.get('confidence', 0.0), 2),
            "brand_mentions": segment_info.get('keywords', [])[:3],  # 取前3个关键词作为品牌提及
            "product_categories": ["婴幼儿奶粉", "营养补充"],
            "key_selling_points": segment_info.get('keywords', []),
            "product_brand_type": product_brand_type,
            "topic": segment_info.get('topic', ''),
            "logic_pattern": segment_info.get('logic_pattern', '产品介绍型')
        }
    }
    
    # 保存JSON报告
    json_report_path = output_file.with_suffix('.json')
    with open(json_report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return json_report_path

def process_temp_input_mode(input_dir: Path, output_dir: Path, api_key: str) -> int:
    """处理临时输入目录模式"""
    
    print(f"🔍 扫描输入目录: {input_dir}")
    matched_pairs = scan_temp_input_dir(input_dir)
    
    if not matched_pairs:
        print("❌ 未找到匹配的SRT和视频文件对")
        return 1
    
    print(f"✅ 发现 {len(matched_pairs)} 个文件对")
    for srt_file, video_file in matched_pairs:
        print(f"  📄 {srt_file.name} + 🎬 {video_file.name}")
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 导入处理组件
        from srt_parser import SRTParser
        from deepseek_analyzer import DeepSeekAnalyzer  
        from video_generator import VideoGenerator
        
        # 初始化组件
        srt_parser = SRTParser()
        ai_analyzer = DeepSeekAnalyzer(api_key=api_key)
        video_generator = VideoGenerator(
            input_dir=str(input_dir),
            output_dir=str(output_dir)
        )
        
        print("\n🚀 开始处理...")
        
        total_slices = 0
        success_count = 0
        
        for srt_file, video_file in matched_pairs:
            print(f"\n📹 处理: {video_file.stem}")
            
            # 1. 解析SRT
            print(f"  📄 解析字幕...")
            segments = srt_parser.parse_srt_file(srt_file)
            if not segments:
                print(f"  ❌ SRT解析失败")
                continue
            
            # 2. AI分析
            print(f"  🤖 AI分析（DeepSeek）...")
            product_segments = ai_analyzer.analyze_srt_content(segments, srt_file.name)
            if not product_segments:
                print(f"  ❌ 未识别到产品介绍片段")
                continue
            
            # 过滤高置信度片段
            high_conf_segments = [s for s in product_segments if s.confidence >= 0.7]
            if not high_conf_segments:
                high_conf_segments = product_segments[:1]  # 至少保留一个最佳片段
            
            print(f"  ✂️ 识别到 {len(high_conf_segments)} 个产品介绍片段")
            
            # 3. 生成视频切片
            for i, segment in enumerate(high_conf_segments):
                try:
                    # 构建segment_info
                    segment_info = {
                        'start_time': segment.start_time,
                        'end_time': segment.end_time,
                        'topic': segment.topic,
                        'sequence_ids': segment.sequence_ids,
                        'summary': segment.summary,
                        'keywords': segment.keywords,
                        'logic_pattern': segment.logic_pattern,
                        'confidence': segment.confidence,
                        'duration': segment.duration
                    }
                    
                    # 生成视频切片
                    result = video_generator.generate_video_from_segment(
                        srt_filename=srt_file.name,
                        segment_info=segment_info,
                        use_topic_as_filename=True
                    )
                    
                    if result['success']:
                        output_file = Path(result['output_path'])
                        print(f"    ✅ 生成切片: {output_file.name}")
                        print(f"    ⏱️ 时长: {segment.duration:.1f}秒")
                        print(f"    🎯 置信度: {segment.confidence:.2f}")
                        
                        # 生成简化JSON报告
                        json_path = generate_simplified_json_report(segment_info, video_file, output_file)
                        print(f"    📊 分析报告: {json_path.name}")
                        
                        total_slices += 1
                        success_count += 1
                    else:
                        print(f"    ❌ 切片生成失败: {result.get('error', '未知错误')}")
                        
                except Exception as e:
                    print(f"    ❌ 处理片段失败: {e}")
                    continue
        
        print(f"\n📊 处理完成:")
        print(f"  ✅ 成功生成: {success_count} 个产品介绍切片")
        print(f"  📁 输出目录: {output_dir}")
        
        return 0 if success_count > 0 else 1
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return 1

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="产品介绍生成 - 支持临时输入目录模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python run.py data/input_temp              # 处理临时输入目录
  python run.py data/input_temp -o output    # 指定输出目录  
  python run.py data/input_temp -v           # 详细模式

输入目录格式:
  input_temp/
  ├── video_1.mp4
  ├── video_1.srt
  ├── video_2.mp4
  └── video_2.srt

输出格式:
  output/
  ├── video_1_product_1.mp4
  ├── video_1_product_1.json
  ├── video_1_product_2.mp4
  └── video_1_product_2.json
        """
    )
    
    parser.add_argument(
        "input_dir",
        help="输入目录路径（包含SRT和视频文件）"
    )
    
    parser.add_argument(
        "-o", "--output-dir",
        default="data/output",
        help="输出目录路径 (默认: data/output)"
    )
    
    parser.add_argument(
        "--api-key",
        help="DeepSeek API密钥 (可选，优先使用环境变量)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出模式"
    )
    
    parser.add_argument(
        "--quiet", "-q",
                       action="store_true",
        help="安静模式 (仅显示错误)"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("🎯 产品介绍生成 - 临时输入目录模式")
    print("=" * 60)
    
    # 设置路径
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        print(f"❌ 输入目录不存在: {input_dir}")
        return 1
    
    # 检查API密钥配置
    api_key = args.api_key or get_deepseek_api_key()
    if not api_key:
        print("❌ DeepSeek API密钥未设置")
        print("请检查以下配置:")
        print("1. 在项目根目录的.env文件中设置: DEEPSEEK_API_KEY=your_api_key")
        print("2. 或设置环境变量: export DEEPSEEK_API_KEY=your_api_key")
        print("3. 或使用命令行参数: --api-key your_api_key")
        return 1
    
    # 显示配置信息
    if not args.quiet:
        config_summary = get_config_summary()
        print("\n🤖 AI配置:")
        print(f"  📡 API已配置: {'✅' if config_summary['api_configured'] else '❌'}")
        print(f"  🧠 AI模型: {config_summary['model']}")
        print(f"  ⏱️ 时长范围: {config_summary['min_duration']}-{config_summary['max_duration']}秒")
        print(f"  🔥 创意度: {config_summary['temperature']}")
        print(f"  🎯 产品关键词: {config_summary['product_keywords_count']}个")
        print("=" * 60)
    
    # 处理临时输入目录
    return process_temp_input_mode(input_dir, output_dir, api_key)

if __name__ == "__main__":
    sys.exit(main()) 