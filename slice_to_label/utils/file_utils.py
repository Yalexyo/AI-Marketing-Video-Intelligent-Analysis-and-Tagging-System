"""
文件处理工具函数
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def scan_video_files(
    directory: str, 
    supported_formats: Optional[List[str]] = None
) -> List[str]:
    """
    扫描目录中的视频文件，并过滤无效文件
    
    Args:
        directory: 目录路径
        supported_formats: 支持的格式列表
        
    Returns:
        视频文件路径列表
    """
    if supported_formats is None:
        supported_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    
    video_files = []
    filtered_count = 0  # 过滤文件计数
    
    if not os.path.exists(directory):
        logger.error(f"目录不存在: {directory}")
        return video_files
    
    def _should_filter_video_file(file_path: Path) -> bool:
        """判断视频文件是否应该被过滤"""
        # 🎯 用户反馈：多镜头视频也应该被分析，只过滤真正失败的文件
        # 只过滤❌前缀的文件（分析失败），♻️文件允许正常分析
        if file_path.stem.startswith("❌"):
            return True
        return False
    
    for file_path in Path(directory).rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in supported_formats:
            # 🚨 新增：过滤逻辑
            if _should_filter_video_file(file_path):
                filtered_count += 1
                logger.debug(f"🚫 过滤视频文件: {file_path.name} (质量问题)")
                continue
            video_files.append(str(file_path))
    
    if filtered_count > 0:
        logger.info(f"🚫 文件扫描过滤了 {filtered_count} 个质量问题视频文件")
    
    return sorted(video_files)


def save_json_result(data: Dict[str, Any], output_file: str) -> bool:
    """
    保存JSON结果到文件
    
    Args:
        data: 要保存的数据
        output_file: 输出文件路径
        
    Returns:
        是否保存成功
    """
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存JSON文件失败 {output_file}: {e}")
        return False


def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    加载JSON文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        JSON数据或None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载JSON文件失败 {file_path}: {e}")
        return None


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    获取文件基本信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件信息字典
    """
    try:
        stat = os.stat(file_path)
        return {
            "path": file_path,
            "name": os.path.basename(file_path),
            "size_mb": stat.st_size / (1024 * 1024),
            "exists": True
        }
    except Exception as e:
        return {
            "path": file_path,
            "name": os.path.basename(file_path),
            "error": str(e),
            "exists": False
        }


def ensure_output_directory(output_dir: str) -> str:
    """
    确保输出目录存在
    
    Args:
        output_dir: 输出目录路径
        
    Returns:
        确保存在的目录路径
    """
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def filter_files_by_size(
    file_paths: List[str], 
    min_size_mb: float = 0.5, 
    max_size_mb: float = 100.0
) -> List[str]:
    """
    根据文件大小过滤文件
    
    Args:
        file_paths: 文件路径列表
        min_size_mb: 最小文件大小(MB)
        max_size_mb: 最大文件大小(MB)
        
    Returns:
        过滤后的文件路径列表
    """
    filtered_files = []
    
    for file_path in file_paths:
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if min_size_mb <= size_mb <= max_size_mb:
                filtered_files.append(file_path)
            else:
                logger.debug(f"文件大小不符合要求: {file_path} ({size_mb:.2f}MB)")
        except Exception as e:
            logger.warning(f"无法获取文件大小: {file_path}, {e}")
    
    return filtered_files 