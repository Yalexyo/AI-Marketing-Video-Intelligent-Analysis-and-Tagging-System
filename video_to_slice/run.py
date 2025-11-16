#!/usr/bin/env python3
"""
视频切片批处理脚本 - 🍭Origin驱动架构 (简化版)
直接输出到🎬Slice/{视频名}/slices/

使用示例:
python run.py                           # 处理🍭Origin中的所有视频
python run.py --input ../🍭Origin      # 指定输入目录
python run.py --help                    # 查看帮助
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 添加src目录到Python路径
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def scan_origin_videos(origin_dir: Path) -> dict:
    """扫描🍭Origin文件夹中的原始视频"""
    origin_mapping = {}
    
    if not origin_dir.exists():
        print(f"⚠️  🍭Origin目录不存在: {origin_dir}")
        return origin_mapping
    
    supported_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    
    for video_file in origin_dir.iterdir():
        if video_file.is_file() and video_file.suffix.lower() in supported_formats:
            video_name = video_file.stem
            origin_mapping[video_name] = video_file
            print(f"🍭 发现原始视频: {video_file.name} -> {video_name}")
    
    return origin_mapping

def setup_origin_output_structure(base_dir: Path) -> Path:
    """设置🍭Origin输出结构"""
    slice_output_dir = base_dir.parent / "🎬Slice"  # 在demo根目录下
    slice_output_dir.mkdir(exist_ok=True)
    print(f"🎬 Slice输出目录: {slice_output_dir}")
    return slice_output_dir

def main():
    parser = argparse.ArgumentParser(description="视频切片批处理 - 🍭Origin驱动架构")
    
    parser.add_argument(
        "--input", "-i",
        default="../🍭Origin",
        help="🍭Origin输入目录 (默认: ../🍭Origin)"
    )
    
    parser.add_argument(
        "--features", "-f",
                       nargs="+",
                       default=["shot_detection"],
        choices=["shot_detection", "label_detection", "text_detection", "face_detection"],
        help="视频分析功能 (默认: shot_detection)"
    )
    
    parser.add_argument(
        "--concurrent", "-c",
                       type=int, 
                       default=3,
        help="视频并发数 (默认: 3，建议1-4)"
    )
    
    parser.add_argument(
        "--ffmpeg-workers", "-w",
                       type=int, 
                       default=4,
        help="FFmpeg并行线程数 (默认: 4，建议2-8)"
    )
    
    parser.add_argument(
        "--patterns",
                       nargs="+",
                       default=["*.mp4", "*.MP4", "*.avi", "*.AVI", "*.mov", "*.MOV", "*.mkv", "*.MKV"],
        help="文件匹配模式 (默认: mp4,avi,mov,mkv,支持大小写)"
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
    
    parser.add_argument(
        "--mode", "-m",
        choices=["google", "local", "auto"],
        default="auto",
        help="分析模式: google=强制Google Cloud, local=强制本地转场检测, auto=自动选择 (默认: auto)"
    )
    
    parser.add_argument(
        "--semantic-merge", "-s",
        action="store_true",
        help="启用语义合并功能 (默认: 禁用)"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 显示启动信息
    if not args.quiet:
        print("🎬 视频切片批处理 - 🍭Origin驱动架构 (简化版)")
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
    slice_output_dir = setup_origin_output_structure(current_dir)
    
    # 为每个原始视频创建对应的输出目录
    for video_name, video_file in origin_videos.items():
        video_slice_dir = slice_output_dir / video_name / "slices"
        video_slice_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 {video_name} -> {video_slice_dir}")
    
    if not args.quiet:
        print(f"🎯 分析功能: {', '.join(args.features)}")
        print(f"🚀 视频并发数: {args.concurrent}")
        print(f"⚡ FFmpeg线程数: {args.ffmpeg_workers}")
        print(f"🧠 语义合并: {'启用' if args.semantic_merge else '禁用'}")
        print("=" * 60)
    
    # 检查环境变量
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        google_cred_path = current_dir / "config" / "video-ai-461014-d0c437ff635f.json"
        if google_cred_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(google_cred_path)
            logger.info(f"使用项目配置的Google凭据: {google_cred_path}")
        else:
            logger.error("❌ Google Cloud凭据未设置")
            logger.error("请设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量")
            logger.error("或将凭据文件放在 config/ 目录下")
            return 1
    
    try:
        # 导入并行处理器
        from parallel_batch_processor import ParallelBatchProcessor
        
        logger.info("🚀 启动并行批处理器...")
        
        # 创建处理器，直接输出到🎬Slice目录
        processor = ParallelBatchProcessor(
            output_dir=str(slice_output_dir),  # 直接输出到🎬Slice
            temp_dir=str(current_dir / "data" / "temp"),
            max_concurrent=args.concurrent,
            ffmpeg_workers=args.ffmpeg_workers,
            enable_semantic_merge=args.semantic_merge  # 根据命令行参数决定是否启用语义合并
        )
        
        # 执行处理
        result = processor.process_batch_sync(
            input_dir=str(input_dir),
            file_patterns=args.patterns,
            features=args.features,
            analysis_mode=args.mode  # 传递分析模式
        )
        
        # 显示结果
        if result["success"]:
            if not args.quiet:
                print("\n" + "=" * 60)
                print("✅ 并行批处理完成!")
                print(f"📊 处理统计: {result['stats']['processed_videos']}/{result['stats']['total_videos']} 个视频成功")
                print(f"🎬 总计生成: {result['stats']['total_slices']} 个视频切片")
                print(f"⏱️  总耗时: {result['total_duration']:.1f}秒")
                
                if result['parallel_info']['time_saved_percentage'] > 0:
                    print(f"🚀 性能提升: 节省了 {result['parallel_info']['time_saved_percentage']:.1f}% 的时间!")
                
                # 显示输出文件
                print(f"\n📂 输出目录: {slice_output_dir}")
                for video_name in origin_videos.keys():
                    slices_dir = slice_output_dir / video_name / "slices"
                    if slices_dir.exists():
                        slice_count = len(list(slices_dir.glob("*.mp4")))
                        print(f"  ✅ {video_name}/slices/ ({slice_count} 个切片)")
                    else:
                        print(f"  ❌ {video_name}/slices/ (未生成)")
                
                print("=" * 60)
            
            logger.info("处理完成，程序正常退出")
            return 0
        else:
            logger.error(f"❌ 批处理失败: {result.get('error', '未知错误')}")
            return 1
            
    except KeyboardInterrupt:
        logger.info("⚠️  用户中断处理")
        return 130
    except ImportError as e:
        logger.error(f"❌ 依赖模块导入失败: {e}")
        logger.error("请确保所有依赖文件在 src/ 目录下")
        return 1
    except Exception as e:
        logger.error(f"❌ 程序异常: {e}")
        if args.verbose:
            import traceback
            logger.error(f"详细错误信息:\n{traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 