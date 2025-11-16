#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理管理器

负责管理多文件转换和并行处理，包括进度跟踪和错误处理。
"""

import os
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time
from tqdm import tqdm

from .video_converter import VideoConverter
from .utils import (
    get_video_files, get_file_size, format_file_size, 
    format_duration, ensure_unique_filename, 
    is_video_file, create_directory_structure,
    calculate_progress_eta
)


class BatchProcessor:
    """批量处理管理器"""
    
    def __init__(self, config: Dict[str, Any], dry_run: bool = False):
        """
        初始化批量处理器
        
        Args:
            config: 项目配置
            dry_run: 是否为预览模式
        """
        self.config = config
        self.dry_run = dry_run
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 处理配置
        self.processing_config = config.get("processing", {})
        self.file_config = config.get("files", {})
        
        # 并行配置
        self.workers = min(
            self.processing_config.get("workers", 2),
            self.processing_config.get("max_workers", 8)
        )
        
        # 处理统计
        self.stats = {
            "total_files": 0,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None
        }
        
        # 失败文件列表
        self.failed_files = []
        self.skipped_files = []
        
        # 进度锁
        self._progress_lock = threading.Lock()
    
    def process_directory(self, input_dir: Path, output_dir: Path) -> Dict[str, Any]:
        """
        批量处理目录中的视频文件
        
        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            
        Returns:
            处理结果统计
        """
        self.logger.info(f"开始批量处理目录: {input_dir}")
        self.stats["start_time"] = datetime.now()
        
        try:
            # 获取所有支持的视频文件
            supported_formats = self.file_config.get("supported_formats", [])
            video_files = get_video_files(input_dir, supported_formats)
            
            if not video_files:
                self.logger.warning(f"目录中没有找到支持的视频文件: {input_dir}")
                return self._build_result()
            
            self.stats["total_files"] = len(video_files)
            self.logger.info(f"找到 {len(video_files)} 个视频文件")
            
            if self.dry_run:
                return self._dry_run_process(video_files, input_dir, output_dir)
            
            # 执行实际处理
            return self._execute_batch_processing(video_files, input_dir, output_dir)
        
        except Exception as e:
            self.logger.error(f"批量处理目录时发生错误: {e}")
            raise
        finally:
            self.stats["end_time"] = datetime.now()
    
    def process_single_file(self, input_file: Path, output_dir: Path) -> Dict[str, Any]:
        """
        处理单个视频文件
        
        Args:
            input_file: 输入文件
            output_dir: 输出目录
            
        Returns:
            处理结果
        """
        self.logger.info(f"处理单个文件: {input_file}")
        self.stats["start_time"] = datetime.now()
        
        try:
            # 检查文件格式
            supported_formats = self.file_config.get("supported_formats", [])
            if not is_video_file(input_file, supported_formats):
                error_msg = f"不支持的文件格式: {input_file.suffix}"
                self.logger.error(error_msg)
                return {
                    "success_count": 0,
                    "failed_count": 1,
                    "skipped_count": 0,
                    "failed_files": [str(input_file)],
                    "message": error_msg
                }
            
            self.stats["total_files"] = 1
            
            if self.dry_run:
                return self._dry_run_single_file(input_file, output_dir)
            
            # 执行转换
            return self._execute_single_conversion(input_file, output_dir)
        
        except Exception as e:
            self.logger.error(f"处理单个文件时发生错误: {e}")
            raise
        finally:
            self.stats["end_time"] = datetime.now()
    
    def _dry_run_process(self, video_files: List[Path], 
                        input_dir: Path, output_dir: Path) -> Dict[str, Any]:
        """预览模式处理"""
        self.logger.info("=== 预览模式 - 不会实际转换文件 ===")
        
        total_size = 0
        for video_file in video_files:
            file_size = get_file_size(video_file)
            total_size += file_size
            
            # 构建输出路径
            output_path = self._build_output_path(video_file, input_dir, output_dir)
            
            self.logger.info(
                f"[预览] {video_file.name} "
                f"({format_file_size(file_size)}) -> {output_path.name}"
            )
        
        self.logger.info(f"预览完成: 总共 {len(video_files)} 个文件, "
                        f"总大小 {format_file_size(total_size)}")
        
        return {
            "success_count": 0,
            "failed_count": 0,
            "skipped_count": len(video_files),
            "total_size": total_size,
            "message": f"预览模式: {len(video_files)} 个文件待处理"
        }
    
    def _dry_run_single_file(self, input_file: Path, output_dir: Path) -> Dict[str, Any]:
        """预览模式处理单个文件"""
        file_size = get_file_size(input_file)
        output_path = self._build_output_path(input_file, input_file.parent, output_dir)
        
        self.logger.info(
            f"[预览] {input_file.name} "
            f"({format_file_size(file_size)}) -> {output_path.name}"
        )
        
        return {
            "success_count": 0,
            "failed_count": 0,
            "skipped_count": 1,
            "message": f"预览模式: {input_file.name} 待转换"
        }
    
    def _execute_batch_processing(self, video_files: List[Path], 
                                 input_dir: Path, output_dir: Path) -> Dict[str, Any]:
        """执行批量处理"""
        # 创建进度条
        with tqdm(total=len(video_files), desc="转换进度", unit="文件") as pbar:
            
            # 使用线程池进行并行处理
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                # 提交所有任务
                future_to_file = {
                    executor.submit(
                        self._process_single_video, 
                        video_file, input_dir, output_dir, pbar
                    ): video_file
                    for video_file in video_files
                }
                
                # 处理完成的任务
                for future in as_completed(future_to_file):
                    video_file = future_to_file[future]
                    try:
                        result = future.result()
                        if result["success"]:
                            self.stats["success"] += 1
                        else:
                            self.stats["failed"] += 1
                            self.failed_files.append(str(video_file))
                    except Exception as e:
                        self.logger.error(f"处理文件 {video_file} 时发生异常: {e}")
                        self.stats["failed"] += 1
                        self.failed_files.append(str(video_file))
                    
                    self.stats["processed"] += 1
        
        return self._build_result()
    
    def _execute_single_conversion(self, input_file: Path, output_dir: Path) -> Dict[str, Any]:
        """执行单个文件转换"""
        try:
            output_path = self._build_output_path(input_file, input_file.parent, output_dir)
            
            # 检查是否跳过已存在的文件
            if self._should_skip_file(output_path):
                self.logger.info(f"跳过已存在的文件: {output_path}")
                self.stats["skipped"] += 1
                self.skipped_files.append(str(input_file))
                return self._build_result()
            
            # 创建转换器
            converter = VideoConverter(self.config.get("conversion", {}))
            
            # 执行转换
            result = converter.convert_file(input_file, output_path)
            
            if result["success"]:
                self.stats["success"] += 1
            else:
                self.stats["failed"] += 1
                self.failed_files.append(str(input_file))
            
            self.stats["processed"] += 1
            
            return self._build_result()
        
        except Exception as e:
            self.logger.error(f"执行单个转换时发生错误: {e}")
            self.stats["failed"] += 1
            self.failed_files.append(str(input_file))
            return self._build_result()
    
    def _process_single_video(self, video_file: Path, input_dir: Path, 
                             output_dir: Path, pbar: tqdm) -> Dict[str, Any]:
        """处理单个视频文件（线程安全）"""
        try:
            output_path = self._build_output_path(video_file, input_dir, output_dir)
            
            # 检查是否跳过已存在的文件
            if self._should_skip_file(output_path):
                with self._progress_lock:
                    pbar.set_postfix_str(f"跳过: {video_file.name}")
                    pbar.update(1)
                    self.stats["skipped"] += 1
                    self.skipped_files.append(str(video_file))
                
                return {"success": True, "skipped": True}
            
            # 更新进度显示
            with self._progress_lock:
                pbar.set_postfix_str(f"转换: {video_file.name}")
            
            # 创建转换器
            converter = VideoConverter(self.config.get("conversion", {}))
            
            # 执行转换
            result = converter.convert_file(
                video_file, output_path,
                progress_callback=lambda p: self._update_file_progress(pbar, video_file, p)
            )
            
            # 更新进度条
            with self._progress_lock:
                if result["success"]:
                    pbar.set_postfix_str(f"完成: {video_file.name}")
                else:
                    pbar.set_postfix_str(f"失败: {video_file.name}")
                pbar.update(1)
            
            return result
        
        except Exception as e:
            with self._progress_lock:
                pbar.set_postfix_str(f"异常: {video_file.name}")
                pbar.update(1)
            
            self.logger.error(f"处理视频文件 {video_file} 时发生异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _update_file_progress(self, pbar: tqdm, video_file: Path, 
                             progress_info: Dict[str, Any]):
        """更新文件级进度"""
        try:
            # 计算进度百分比
            processed_time = progress_info.get("processed_time", 0)
            if processed_time > 0:
                speed = progress_info.get("speed", "").replace("x", "")
                if speed:
                    try:
                        speed_float = float(speed)
                        status = f"{video_file.name} ({speed}x)"
                        with self._progress_lock:
                            pbar.set_postfix_str(status)
                    except ValueError:
                        pass
        except Exception:
            pass  # 忽略进度更新错误
    
    def _build_output_path(self, input_file: Path, input_base: Path, 
                          output_base: Path) -> Path:
        """构建输出文件路径"""
        # 计算相对路径
        try:
            relative_path = input_file.relative_to(input_base)
        except ValueError:
            # 如果无法计算相对路径，使用文件名
            relative_path = Path(input_file.name)
        
        # 构建输出路径
        output_extension = self.file_config.get("output_extension", "mp4")
        output_name = relative_path.stem + "." + output_extension
        
        if self.processing_config.get("preserve_structure", True):
            # 保持目录结构
            output_path = output_base / relative_path.parent / output_name
        else:
            # 平铺到输出目录
            output_path = output_base / output_name
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 避免文件名冲突
        if not self.processing_config.get("skip_existing", True):
            output_path = ensure_unique_filename(output_path)
        
        return output_path
    
    def _should_skip_file(self, output_path: Path) -> bool:
        """检查是否应该跳过文件"""
        return (
            self.processing_config.get("skip_existing", True) and 
            output_path.exists()
        )
    
    def _build_result(self) -> Dict[str, Any]:
        """构建处理结果"""
        total_time = 0
        if self.stats["start_time"] and self.stats["end_time"]:
            total_time = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        return {
            "success_count": self.stats["success"],
            "failed_count": self.stats["failed"],
            "skipped_count": self.stats["skipped"],
            "total_files": self.stats["total_files"],
            "processed_files": self.stats["processed"],
            "total_time": total_time,
            "failed_files": self.failed_files.copy(),
            "skipped_files": self.skipped_files.copy(),
            "message": self._build_summary_message()
        }
    
    def _build_summary_message(self) -> str:
        """构建总结信息"""
        total = self.stats["total_files"]
        success = self.stats["success"]
        failed = self.stats["failed"]
        skipped = self.stats["skipped"]
        
        if total == 0:
            return "没有找到可处理的文件"
        
        parts = []
        if success > 0:
            parts.append(f"{success} 个成功")
        if failed > 0:
            parts.append(f"{failed} 个失败")
        if skipped > 0:
            parts.append(f"{skipped} 个跳过")
        
        message = f"处理完成: {', '.join(parts)}"
        
        if self.stats["start_time"] and self.stats["end_time"]:
            total_time = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            message += f", 耗时 {format_duration(total_time)}"
        
        return message 