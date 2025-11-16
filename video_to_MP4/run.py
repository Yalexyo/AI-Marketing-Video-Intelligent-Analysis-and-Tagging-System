#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video to MP4 Converter - 主运行脚本

批量视频格式转换工具的主要入口点，提供命令行接口和核心功能调用。

作者: AI Assistant
版本: 0.1.0
创建时间: 2024
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from typing import Optional

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.batch_processor import BatchProcessor
from src.config_manager import ConfigManager
from src.utils import setup_logging, check_ffmpeg, validate_paths


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="批量视频格式转换工具 - 将多种格式转换为 MP4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 转换单个文件
  python run.py --input video.avi --output ./output/

  # 批量转换文件夹
  python run.py --input ./videos/ --output ./converted/

  # 指定质量和线程数
  python run.py --input ./videos/ --output ./converted/ --quality high --workers 4

  # 使用配置文件
  python run.py --config config/custom_config.txt
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入视频文件或目录路径"
    )

    parser.add_argument(
        "--output", "-o", 
        type=str,
        help="输出目录路径"
    )

    parser.add_argument(
        "--quality", "-q",
        choices=["low", "medium", "high", "ultra"],
        default="medium",
        help="转换质量 (默认: medium)"
    )

    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=2,
        help="并行处理线程数 (默认: 2)"
    )

    parser.add_argument(
        "--resolution", "-r",
        type=str,
        help="输出分辨率 (例如: 1920x1080, 1280x720)"
    )

    parser.add_argument(
        "--bitrate", "-b",
        type=str,
        help="视频比特率 (例如: 2M, 1000k)"
    )

    parser.add_argument(
        "--fps",
        type=int,
        help="输出帧率"
    )

    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="跳过已存在的输出文件"
    )

    parser.add_argument(
        "--preserve-structure",
        action="store_true", 
        help="保持输入目录的文件夹结构"
    )

    parser.add_argument(
        "--config", "-c",
        type=str,
        help="配置文件路径"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别 (默认: INFO)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际转换文件"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Video to MP4 Converter v0.1.0"
    )

    return parser.parse_args()


def validate_arguments(args):
    """验证命令行参数"""
    errors = []

    if not args.input:
        errors.append("必须指定输入文件或目录 (--input)")

    if not args.output:
        errors.append("必须指定输出目录 (--output)")

    if args.workers <= 0:
        errors.append("线程数必须大于 0")

    if args.workers > 8:
        logging.warning("线程数过高可能影响系统性能，建议不超过 8")

    if errors:
        for error in errors:
            print(f"错误: {error}")
        sys.exit(1)


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 验证参数
    validate_arguments(args)
    
    # 设置日志
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # 检查 FFmpeg 是否可用
        if not check_ffmpeg():
            logger.error("FFmpeg 未找到，请确保已安装并添加到 PATH")
            sys.exit(1)
        
        # 加载配置
        config_manager = ConfigManager(args.config)
        config = config_manager.get_config()
        
        # 覆盖配置文件中的设置（如果命令行有指定）
        if args.quality:
            config['conversion']['quality'] = args.quality
        if args.workers:
            config['processing']['workers'] = args.workers
        if args.resolution:
            config['conversion']['resolution'] = args.resolution
        if args.bitrate:
            config['conversion']['bitrate'] = args.bitrate
        if args.fps:
            config['conversion']['fps'] = args.fps
        if args.skip_existing:
            config['processing']['skip_existing'] = True
        if args.preserve_structure:
            config['processing']['preserve_structure'] = True
        
        # 验证路径
        input_path, output_path = validate_paths(args.input, args.output)
        
        logger.info(f"开始视频转换任务")
        logger.info(f"输入路径: {input_path}")
        logger.info(f"输出路径: {output_path}")
        logger.info(f"转换质量: {config['conversion']['quality']}")
        logger.info(f"并行线程: {config['processing']['workers']}")
        
        if args.dry_run:
            logger.info("预览模式: 不会实际转换文件")
        
        # 创建批处理器
        processor = BatchProcessor(config, dry_run=args.dry_run)
        
        # 开始处理
        if input_path.is_file():
            # 单文件转换
            result = processor.process_single_file(input_path, output_path)
        else:
            # 批量转换目录
            result = processor.process_directory(input_path, output_path)
        
        # 输出结果统计
        logger.info("转换完成!")
        logger.info(f"成功转换: {result.get('success_count', 0)} 个文件")
        logger.info(f"跳过文件: {result.get('skipped_count', 0)} 个文件") 
        logger.info(f"失败文件: {result.get('failed_count', 0)} 个文件")
        
        if result.get('failed_files'):
            logger.warning("失败的文件:")
            for failed_file in result['failed_files']:
                logger.warning(f"  - {failed_file}")
        
        return 0 if result.get('failed_count', 0) == 0 else 1
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return 1
    except Exception as e:
        logger.error(f"运行时发生错误: {str(e)}")
        logger.debug("详细错误信息:", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 