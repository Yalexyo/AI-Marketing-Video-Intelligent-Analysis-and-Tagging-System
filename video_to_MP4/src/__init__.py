#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video to MP4 Converter - 核心模块包

批量视频格式转换工具的核心功能模块。
"""

from .video_converter import VideoConverter
from .batch_processor import BatchProcessor
from .config_manager import ConfigManager
from .converter_config import ConversionConfig, ConversionPresets, FormatSupport
from .utils import (
    setup_logging, check_ffmpeg, validate_paths,
    get_video_files, format_file_size, format_duration
)

__version__ = "0.1.0"
__author__ = "AI Assistant"
__description__ = "批量视频格式转换工具"

__all__ = [
    "VideoConverter",
    "BatchProcessor", 
    "ConfigManager",
    "ConversionConfig",
    "ConversionPresets",
    "FormatSupport",
    "setup_logging",
    "check_ffmpeg",
    "validate_paths",
    "get_video_files",
    "format_file_size", 
    "format_duration"
] 