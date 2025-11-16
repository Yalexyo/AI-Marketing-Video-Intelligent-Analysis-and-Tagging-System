#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块

提供项目所需的各种工具函数，包括日志设置、文件操作、格式检查等。
"""

import os
import sys
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
from datetime import datetime
import json


def setup_logging(log_level: str = "INFO", enable_file_logging: bool = True):
    """设置日志系统"""
    # 创建 logs 目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 设置日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    if enable_file_logging:
        log_filename = f"video_converter_{datetime.now().strftime('%Y%m%d')}.log"
        log_file = log_dir / log_filename
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def check_ffmpeg() -> bool:
    """检查 FFmpeg 是否可用"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


def get_ffmpeg_version() -> Optional[str]:
    """获取 FFmpeg 版本信息"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            # 解析版本信息
            lines = result.stdout.split('\n')
            if lines:
                version_line = lines[0]
                if 'ffmpeg version' in version_line:
                    return version_line.split('ffmpeg version ')[1].split(' ')[0]
    except Exception:
        pass
    return None


def validate_paths(input_path: str, output_path: str) -> Tuple[Path, Path]:
    """验证输入和输出路径"""
    # 转换为 Path 对象
    input_p = Path(input_path).resolve()
    output_p = Path(output_path).resolve()
    
    # 检查输入路径
    if not input_p.exists():
        raise FileNotFoundError(f"输入路径不存在: {input_p}")
    
    # 创建输出目录
    if input_p.is_file():
        # 输入是文件，输出应该是目录
        output_p.mkdir(parents=True, exist_ok=True)
    else:
        # 输入是目录，输出也应该是目录
        output_p.mkdir(parents=True, exist_ok=True)
    
    return input_p, output_p


def get_video_files(directory: Path, supported_formats: List[str]) -> List[Path]:
    """获取目录中的所有支持的视频文件"""
    video_files = []
    
    for format_ext in supported_formats:
        # 支持大小写不敏感的搜索
        pattern = f"*.{format_ext.lower()}"
        video_files.extend(directory.rglob(pattern))
        
        pattern = f"*.{format_ext.upper()}"
        video_files.extend(directory.rglob(pattern))
    
    # 去重并排序
    video_files = sorted(list(set(video_files)))
    
    return video_files


def get_file_size(file_path: Path) -> int:
    """获取文件大小（字节）"""
    try:
        return file_path.stat().st_size
    except OSError:
        return 0


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """格式化时长显示"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}分{secs:.1f}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}时{minutes}分{secs:.1f}秒"


def get_video_info(video_path: Path) -> Dict[str, Any]:
    """获取视频文件信息"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(video_path)
        ]
        
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            
            # 提取视频流信息
            video_stream = None
            audio_stream = None
            
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video" and not video_stream:
                    video_stream = stream
                elif stream.get("codec_type") == "audio" and not audio_stream:
                    audio_stream = stream
            
            # 格式化信息
            video_info = {
                "duration": float(info.get("format", {}).get("duration", 0)),
                "size": int(info.get("format", {}).get("size", 0)),
                "bitrate": int(info.get("format", {}).get("bit_rate", 0)),
                "format_name": info.get("format", {}).get("format_name", "unknown")
            }
            
            if video_stream:
                video_info.update({
                    "width": int(video_stream.get("width", 0)),
                    "height": int(video_stream.get("height", 0)),
                    "fps": eval(video_stream.get("r_frame_rate", "0/1")),
                    "video_codec": video_stream.get("codec_name", "unknown")
                })
            
            if audio_stream:
                video_info.update({
                    "audio_codec": audio_stream.get("codec_name", "unknown"),
                    "audio_bitrate": int(audio_stream.get("bit_rate", 0)),
                    "sample_rate": int(audio_stream.get("sample_rate", 0))
                })
            
            return video_info
    
    except Exception as e:
        logging.warning(f"无法获取视频信息 {video_path}: {e}")
    
    return {}


def clean_temp_files(temp_dir: Path, prefix: str = "temp_convert_"):
    """清理临时文件"""
    try:
        if temp_dir.exists() and temp_dir.is_dir():
            for temp_file in temp_dir.glob(f"{prefix}*"):
                try:
                    if temp_file.is_file():
                        temp_file.unlink()
                    elif temp_file.is_dir():
                        shutil.rmtree(temp_file)
                except Exception as e:
                    logging.warning(f"无法删除临时文件 {temp_file}: {e}")
    except Exception as e:
        logging.error(f"清理临时文件时出错: {e}")


def ensure_unique_filename(file_path: Path) -> Path:
    """确保文件名唯一，如果存在则添加数字后缀"""
    if not file_path.exists():
        return file_path
    
    base = file_path.stem
    suffix = file_path.suffix
    parent = file_path.parent
    counter = 1
    
    while True:
        new_name = f"{base}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def calculate_progress_eta(completed: int, total: int, start_time: float) -> str:
    """计算进度和预计剩余时间"""
    if completed == 0 or total == 0:
        return "计算中..."
    
    current_time = datetime.now().timestamp()
    elapsed = current_time - start_time
    
    if elapsed == 0:
        return "计算中..."
    
    rate = completed / elapsed
    remaining = total - completed
    
    if rate > 0:
        eta_seconds = remaining / rate
        return format_duration(eta_seconds)
    
    return "未知"


def is_video_file(file_path: Path, supported_formats: List[str]) -> bool:
    """检查文件是否为支持的视频格式"""
    if not file_path.is_file():
        return False
    
    extension = file_path.suffix.lower().lstrip('.')
    return extension in [fmt.lower() for fmt in supported_formats]


def create_directory_structure(source_path: Path, target_base: Path) -> Path:
    """在目标路径中创建与源路径相同的目录结构"""
    # 计算相对路径
    try:
        # 如果 source_path 是某个基础路径的子路径
        relative_path = source_path.parent.name
        target_dir = target_base / relative_path
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir
    except Exception:
        # 如果无法创建相对路径，就使用目标基础路径
        return target_base 