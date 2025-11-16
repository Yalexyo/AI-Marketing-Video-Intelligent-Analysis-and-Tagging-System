#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频转换核心模块

实现单个视频文件的转换逻辑，支持多种格式转换为 MP4。
"""

import os
import subprocess
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import ffmpeg

from .converter_config import ConversionConfig
from .utils import get_video_info, format_file_size, format_duration


class VideoConverter:
    """视频转换器类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化视频转换器
        
        Args:
            config: 转换配置字典
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 转换统计
        self.stats = {
            "total_processed": 0,
            "total_success": 0,
            "total_failed": 0,
            "total_time": 0.0
        }
    
    def convert_file(self, input_path: Path, output_path: Path, 
                     progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        转换单个视频文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            progress_callback: 进度回调函数
            
        Returns:
            转换结果字典
        """
        start_time = datetime.now()
        self.logger.info(f"开始转换: {input_path.name}")
        
        try:
            # 获取输入文件信息
            input_info = get_video_info(input_path)
            self.logger.debug(f"输入文件信息: {input_info}")
            
            # 构建转换参数
            conversion_args = self._build_conversion_args(input_info)
            
            # 创建临时输出文件
            temp_output = self._create_temp_output_path(output_path)
            
            # 执行转换
            result = self._execute_conversion(
                input_path, temp_output, conversion_args, progress_callback
            )
            
            if result["success"]:
                # 移动临时文件到最终位置
                self._finalize_output(temp_output, output_path)
                
                # 获取输出文件信息
                output_info = get_video_info(output_path)
                
                # 计算转换统计
                conversion_time = (datetime.now() - start_time).total_seconds()
                self.stats["total_processed"] += 1
                self.stats["total_success"] += 1
                self.stats["total_time"] += conversion_time
                
                self.logger.info(
                    f"转换成功: {input_path.name} -> {output_path.name} "
                    f"({format_duration(conversion_time)})"
                )
                
                return {
                    "success": True,
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                    "input_info": input_info,
                    "output_info": output_info,
                    "conversion_time": conversion_time,
                    "message": "转换成功"
                }
            else:
                # 清理临时文件
                self._cleanup_temp_file(temp_output)
                
                self.stats["total_processed"] += 1
                self.stats["total_failed"] += 1
                
                self.logger.error(f"转换失败: {input_path.name} - {result['error']}")
                
                return {
                    "success": False,
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                    "error": result["error"],
                    "message": f"转换失败: {result['error']}"
                }
        
        except Exception as e:
            self.stats["total_processed"] += 1
            self.stats["total_failed"] += 1
            
            error_msg = f"转换过程中发生异常: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "success": False,
                "input_path": str(input_path),
                "output_path": str(output_path),
                "error": error_msg,
                "message": f"转换异常: {str(e)}"
            }
    
    def _build_conversion_args(self, input_info: Dict[str, Any]) -> List[str]:
        """构建转换参数"""
        # 获取质量预设
        quality = self.config.get("quality", "medium")
        quality_preset = ConversionConfig.get_quality_preset(quality)
        
        # 合并配置
        conversion_config = {**quality_preset, **self.config}
        
        # 根据输入文件调整配置
        conversion_config = self._adjust_config_for_input(conversion_config, input_info)
        
        # 构建 FFmpeg 参数
        args = ConversionConfig.build_ffmpeg_args(conversion_config)
        
        self.logger.debug(f"转换参数: {' '.join(args)}")
        return args
    
    def _adjust_config_for_input(self, config: Dict[str, Any], 
                                input_info: Dict[str, Any]) -> Dict[str, Any]:
        """根据输入文件调整转换配置"""
        adjusted_config = config.copy()
        
        # 处理分辨率设置
        resolution = adjusted_config.get("resolution")
        if resolution == "original":
            # 如果设置为"original"，则删除分辨率设置以保持原分辨率
            adjusted_config.pop("resolution", None)
        elif not resolution and input_info.get("width"):
            # 如果没有指定分辨率，保持原始分辨率
            adjusted_config["resolution"] = f"{input_info['width']}x{input_info['height']}"
        
        # 如果没有指定帧率，保持原始帧率
        if not adjusted_config.get("fps") and input_info.get("fps"):
            adjusted_config["fps"] = min(int(input_info["fps"]), 60)
        
        # 根据文件大小调整比特率
        file_size_mb = input_info.get("size", 0) / (1024 * 1024)
        if file_size_mb > self.config.get("large_file_threshold", 1024):
            self.logger.info(f"检测到大文件 ({format_file_size(input_info.get('size', 0))}), 调整编码参数")
            adjusted_config["preset"] = "fast"  # 使用更快的预设
        
        return adjusted_config
    
    def _create_temp_output_path(self, output_path: Path) -> Path:
        """创建临时输出文件路径"""
        temp_dir = output_path.parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        temp_prefix = self.config.get("temp_prefix", "temp_convert_")
        temp_name = f"{temp_prefix}{output_path.name}"
        
        return temp_dir / temp_name
    
    def _execute_conversion(self, input_path: Path, output_path: Path, 
                           args: List[str], progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """执行视频转换"""
        try:
            # 构建完整的 FFmpeg 命令
            cmd = ["ffmpeg", "-i", str(input_path)] + args + ["-y", str(output_path)]
            
            self.logger.debug(f"执行命令: {' '.join(cmd)}")
            
            # 如果有进度回调，使用进度监控
            if progress_callback:
                return self._execute_with_progress(cmd, progress_callback)
            else:
                return self._execute_simple(cmd)
        
        except Exception as e:
            return {
                "success": False,
                "error": f"执行转换命令失败: {str(e)}"
            }
    
    def _execute_simple(self, cmd: List[str]) -> Dict[str, Any]:
        """简单执行转换命令"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=None  # 不设置超时，让大文件可以完成转换
            )
            
            if result.returncode == 0:
                return {"success": True}
            else:
                error_msg = result.stderr or "未知错误"
                return {
                    "success": False,
                    "error": f"FFmpeg 转换失败: {error_msg}"
                }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "转换超时"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"执行命令时发生错误: {str(e)}"
            }
    
    def _execute_with_progress(self, cmd: List[str], 
                              progress_callback: callable) -> Dict[str, Any]:
        """带进度监控的执行转换命令"""
        try:
            # 使用 Popen 进行实时输出监控
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )
            
            # 监控进度
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    # 解析 FFmpeg 输出中的进度信息
                    progress_info = self._parse_ffmpeg_progress(output)
                    if progress_info and progress_callback:
                        progress_callback(progress_info)
            
            # 等待进程完成
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                return {"success": True}
            else:
                return {
                    "success": False,
                    "error": f"FFmpeg 转换失败: {stderr}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"带进度执行失败: {str(e)}"
            }
    
    def _parse_ffmpeg_progress(self, output: str) -> Optional[Dict[str, Any]]:
        """解析 FFmpeg 输出中的进度信息"""
        try:
            # FFmpeg 进度输出格式示例:
            # frame=  123 fps= 25 q=23.0 size=    1024kB time=00:00:05.00 bitrate=1677.7kbits/s speed=1.02x
            if "time=" in output and "fps=" in output:
                parts = output.strip().split()
                progress_info = {}
                
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        progress_info[key] = value
                
                # 提取有用的信息
                if "time" in progress_info:
                    time_str = progress_info["time"]
                    # 转换时间格式 00:00:05.00 到秒
                    time_parts = time_str.split(":")
                    if len(time_parts) == 3:
                        hours = float(time_parts[0])
                        minutes = float(time_parts[1])
                        seconds = float(time_parts[2])
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        
                        return {
                            "processed_time": total_seconds,
                            "fps": progress_info.get("fps", ""),
                            "speed": progress_info.get("speed", ""),
                            "bitrate": progress_info.get("bitrate", "")
                        }
        
        except Exception:
            pass
        
        return None
    
    def _finalize_output(self, temp_path: Path, final_path: Path):
        """完成输出文件处理"""
        try:
            # 确保输出目录存在
            final_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 移动临时文件到最终位置
            temp_path.rename(final_path)
            
            # 清理临时目录（如果为空）
            temp_dir = temp_path.parent
            try:
                temp_dir.rmdir()
            except OSError:
                pass  # 目录不为空，忽略
        
        except Exception as e:
            self.logger.error(f"完成输出文件时出错: {e}")
            raise
    
    def _cleanup_temp_file(self, temp_path: Path):
        """清理临时文件"""
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception as e:
            self.logger.warning(f"清理临时文件失败 {temp_path}: {e}")
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """获取转换统计信息"""
        avg_time = 0
        if self.stats["total_success"] > 0:
            avg_time = self.stats["total_time"] / self.stats["total_success"]
        
        return {
            "total_processed": self.stats["total_processed"],
            "total_success": self.stats["total_success"],
            "total_failed": self.stats["total_failed"],
            "success_rate": (
                self.stats["total_success"] / max(self.stats["total_processed"], 1) * 100
            ),
            "total_time": self.stats["total_time"],
            "average_time_per_file": avg_time
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_processed": 0,
            "total_success": 0,
            "total_failed": 0,
            "total_time": 0.0
        } 