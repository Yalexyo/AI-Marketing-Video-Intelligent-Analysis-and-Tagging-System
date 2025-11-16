#!/usr/bin/env python3
"""
视频转字幕批处理脚本 - 🍭Origin驱动架构
直接输出到📄SRT/{视频名}/{视频名}_full.srt

使用示例:
python run.py                           # 处理🍭Origin中的所有视频
python run.py --input ../🍭Origin      # 指定输入目录
python run.py --help                    # 查看帮助
"""

import os
import sys
import argparse
from pathlib import Path

# 添加src目录到Python路径
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from batch_video_to_srt import BatchVideoTranscriber
from env_loader import get_dashscope_api_key, get_default_vocab_id

def scan_origin_videos(origin_dir: Path) -> dict:
    """扫描🍭Origin文件夹中的原始视频"""
    origin_mapping = {}
    
    if not origin_dir.exists():
        print(f"⚠️  🍭Origin目录不存在: {origin_dir}")
        return origin_mapping
    
    supported_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv']
    
    for video_file in origin_dir.iterdir():
        if video_file.is_file() and video_file.suffix.lower() in supported_formats:
            video_name = video_file.stem
            origin_mapping[video_name] = video_file
            print(f"🍭 发现原始视频: {video_file.name} -> {video_name}")
    
    return origin_mapping

def setup_origin_output_structure(base_dir: Path) -> Path:
    """设置🍭Origin驱动的输出结构"""
    srt_dir = base_dir.parent / "📄SRT"
    srt_dir.mkdir(exist_ok=True)
    print(f"📄 SRT输出目录: {srt_dir}")
    return srt_dir

def main():
    parser = argparse.ArgumentParser(
        description="视频转字幕批处理 - 🍭Origin驱动架构",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🍭Origin驱动架构说明:
  输入: 🍭Origin/{视频名}.mp4
  输出: 📄SRT/{视频名}/{视频名}_full.srt

使用示例:
  python run.py                           # 处理🍭Origin中的所有视频
  python run.py --input ../🍭Origin      # 指定🍭Origin目录
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        default="../🍭Origin",
        help="🍭Origin输入目录 (默认: ../🍭Origin)"
    )
    
    args = parser.parse_args()
    
    print("🎬 视频转字幕批处理 - 🍭Origin驱动架构")
    print("=" * 60)
    
    # 设置路径
    current_dir = Path(__file__).parent
    input_dir = Path(args.input)
    if not input_dir.is_absolute():
        input_dir = current_dir / input_dir
    
    # 扫描🍭Origin视频
    print("🔍 扫描🍭Origin视频...")
    origin_videos = scan_origin_videos(input_dir)
    
    if not origin_videos:
        print("❌ 未在🍭Origin中找到支持的视频文件")
        return 1
    
    print(f"✅ 发现 {len(origin_videos)} 个视频文件")
    
    # 设置🍭Origin输出结构
    srt_output_dir = setup_origin_output_structure(current_dir)
    
    print("\n🚀 开始批量转录...")
    
    try:
        # 获取API密钥
        api_key = get_dashscope_api_key()
        if not api_key:
            print("❌ 未设置DASHSCOPE_API_KEY，请检查环境配置")
            return 1
        
        # 创建批处理器 - 启用精细化模式以获得更准确的时间戳分割
        transcriber = BatchVideoTranscriber(api_key=api_key, fine_grained=True)
        
        # 获取预设词汇表ID
        vocab_id = get_default_vocab_id()
        
        # 使用batch_process方法 - 现在直接输出到🍭Origin架构
        result = transcriber.batch_process(
            input_dir=str(input_dir),
            output_dir=str(srt_output_dir),
            supported_formats=[".mp4", ".mov", ".avi", ".mkv", ".webm"],
            preset_vocabulary_id=vocab_id
        )
        
        print("\n" + "=" * 60)
        print("📊 处理完成统计:")
        print(f"✅ 成功: {result.get('results', {}).get('success_count', 0)}")
        print(f"❌ 失败: {result.get('results', {}).get('failed_count', 0)}")
        print(f"🔒 质量拒绝: {result.get('results', {}).get('quality_rejected_count', 0)}")
        
        # 显示最终输出文件状态
        print(f"\n📂 输出目录: {srt_output_dir}")
        for video_name in origin_videos.keys():
            srt_file = srt_output_dir / video_name / f"{video_name}_full.srt"
            if srt_file.exists():
                print(f"  ✅ {video_name}/{video_name}_full.srt")
            else:
                print(f"  ❌ {video_name}/{video_name}_full.srt (未生成)")
        
        return 0 if result.get('results', {}).get('failed_count', 0) == 0 else 1
        
    except Exception as e:
        print(f"❌ 批处理失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 