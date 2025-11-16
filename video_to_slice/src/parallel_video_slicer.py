#!/usr/bin/env python3
"""
并行视频切片器 - FFmpeg并行优化版本
解决真正的性能瓶颈：FFmpeg切片过程的并行化

主要优化：
1. 并行执行FFmpeg切片任务
2. 智能任务调度和资源管理
3. 进度监控和错误处理
4. 保持与原VideoSlicer的兼容性
"""

import os
import logging
import subprocess
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class ParallelVideoSlicer:
    """并行视频切片处理器"""
    
    def __init__(self, max_workers: int = 4):
        """
        初始化并行视频切片器
        
        Args:
            max_workers: 最大并发FFmpeg进程数（默认4，根据CPU核心数调整）
        """
        self.temp_dir = Path("./temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        self.segments_output_dir = Path("./output_slices")
        self.segments_output_dir.mkdir(exist_ok=True)
        
        # 并行配置
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        logger.info(f"初始化并行视频切片器 - 最大并发FFmpeg进程: {max_workers}")
    
    def _format_time_for_ffmpeg(self, seconds: float) -> str:
        """将秒数转换为FFmpeg时间格式 (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def _extract_single_segment(self, video_path: str, start_time: float, end_time: float, 
                               segment_index: int, semantic_type: str, video_id: str, 
                               output_dir: str = None) -> Dict[str, Any]:
        """
        提取单个视频片段（线程安全版本）
        
        Returns:
            包含结果信息的字典
        """
        segment_filename = f"{video_id}_semantic_seg_{segment_index}_{semantic_type.replace(' ', '_')}.mp4"
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = Path(output_dir) / segment_filename
        else:
            output_path = self.segments_output_dir / segment_filename
        
        start_process_time = time.time()
        
        try:
            # 格式化时间参数
            start_time_str = self._format_time_for_ffmpeg(start_time)
            duration = end_time - start_time
            duration_str = self._format_time_for_ffmpeg(duration)
            
            # 构建FFmpeg命令（关键帧对齐模式 - 解决静止画面）
            cmd = [
                "ffmpeg", "-y",
                "-ss", start_time_str,           # 输入前定位（更精确）
                "-i", str(video_path),
                "-t", duration_str,
                "-c:v", "libx264",               # 重新编码视频流
                "-c:a", "aac",                   # 重新编码音频流
                "-preset", "fast",               # 快速编码预设
                "-crf", "23",                    # 高质量编码
                "-avoid_negative_ts", "make_zero",
                "-fflags", "+genpts",
                "-reset_timestamps", "1",         # 重置时间戳从0开始
                str(output_path)
            ]
            
            # 执行FFmpeg命令
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False,
                timeout=300  # 5分钟超时
            )
            
            end_process_time = time.time()
            processing_time = end_process_time - start_process_time
            
            if result.returncode != 0:
                logger.error(f"FFmpeg切分失败 {segment_filename}: {result.stderr}")
                return {
                    "success": False,
                    "segment_index": segment_index,
                    "output_path": str(output_path),
                    "error": f"FFmpeg failed: {result.stderr}",
                    "processing_time": processing_time
                }
            
            # 验证输出文件
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                return {
                    "success": False,
                    "segment_index": segment_index,
                    "output_path": str(output_path),
                    "error": "Output file is empty or missing",
                    "processing_time": processing_time
                }
            
            file_size = os.path.getsize(output_path)
            logger.debug(f"成功切片 {segment_filename} ({file_size} bytes, {processing_time:.1f}s)")
            
            return {
                "success": True,
                "segment_index": segment_index,
                "output_path": str(output_path),
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "file_size": file_size,
                "processing_time": processing_time
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg切片超时: {segment_filename}")
            return {
                "success": False,
                "segment_index": segment_index,
                "output_path": str(output_path),
                "error": "FFmpeg timeout",
                "processing_time": time.time() - start_process_time
            }
        except Exception as e:
            logger.error(f"切片过程异常 {segment_filename}: {e}")
            return {
                "success": False,
                "segment_index": segment_index,
                "output_path": str(output_path),
                "error": str(e),
                "processing_time": time.time() - start_process_time
            }
    
    def extract_segments_parallel(self, video_path: str, segments: List[Dict[str, Any]], 
                                 video_id: str, output_dir: str = None,
                                 progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        并行提取多个视频片段
        
        Args:
            video_path: 原始视频文件路径
            segments: 片段信息列表，每个包含start_time, end_time, type等
            video_id: 视频ID
            output_dir: 输出目录
            progress_callback: 进度回调函数
            
        Returns:
            切片结果列表
        """
        if not segments:
            logger.warning("没有片段需要提取")
            return []
        
        total_segments = len(segments)
        logger.info(f"开始并行提取 {total_segments} 个视频片段 (最大并发: {self.max_workers})")
        
        if progress_callback:
            progress_callback(0, f"开始并行切片 {total_segments} 个片段...")
        
        start_time = time.time()
        
        # 提交所有切片任务
        future_to_segment = {}
        for i, segment in enumerate(segments):
            future = self.executor.submit(
                self._extract_single_segment,
                video_path,
                segment['start_time'],
                segment['end_time'],
                segment.get('index', i + 1),
                segment.get('type', f'片段{i+1}'),
                video_id,
                output_dir
            )
            future_to_segment[future] = segment
        
        # 收集结果
        results = []
        completed = 0
        
        for future in as_completed(future_to_segment):
            try:
                result = future.result()
                results.append(result)
                completed += 1
                
                # 进度回调
                progress = int((completed / total_segments) * 100)
                if progress_callback:
                    status = "成功" if result['success'] else "失败"
                    progress_callback(
                        progress,
                        f"切片进度 {completed}/{total_segments} - {result.get('output_path', 'unknown')} ({status})"
                    )
                
                # 日志输出
                if result['success']:
                    logger.info(f"✅ 切片完成 {completed}/{total_segments}: {Path(result['output_path']).name}")
                else:
                    logger.error(f"❌ 切片失败 {completed}/{total_segments}: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                logger.error(f"处理切片任务时发生异常: {e}")
                results.append({
                    "success": False,
                    "segment_index": -1,
                    "output_path": "unknown",
                    "error": str(e),
                    "processing_time": 0
                })
                completed += 1
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # 统计结果
        successful_slices = [r for r in results if r['success']]
        failed_slices = [r for r in results if not r['success']]
        
        logger.info(f"🎉 并行切片完成!")
        logger.info(f"📊 成功: {len(successful_slices)}/{total_segments} 个片段")
        logger.info(f"❌ 失败: {len(failed_slices)} 个片段")
        logger.info(f"⏱️  总耗时: {total_duration:.1f}秒")
        
        if successful_slices:
            avg_time = sum([r['processing_time'] for r in successful_slices]) / len(successful_slices)
            logger.info(f"📈 平均每片段耗时: {avg_time:.1f}秒")
            
            # 计算理论顺序处理时间
            total_sequential_time = sum([r['processing_time'] for r in successful_slices])
            if total_sequential_time > total_duration:
                speedup = total_sequential_time / total_duration
                logger.info(f"🚀 并行加速比: {speedup:.1f}x")
        
        return results
    
    def extract_segment(self, video_path: str, start_time: float, end_time: float, 
                       segment_index: int, semantic_type: str, video_id: str, 
                       output_dir: str = None) -> Optional[str]:
        """
        兼容原VideoSlicer的单片段提取接口
        """
        result = self._extract_single_segment(
            video_path, start_time, end_time, segment_index, 
            semantic_type, video_id, output_dir
        )
        
        if result['success']:
            return result['output_path']
        else:
            logger.error(f"片段提取失败: {result.get('error', 'Unknown error')}")
            return None
    
    def create_slices_from_shots(self, video_path: str, shots: List[Dict[str, Any]], 
                                video_name: str, output_dir: str = None,
                                progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        从镜头信息创建视频切片（并行版本）
        
        Args:
            video_path: 原始视频路径
            shots: 镜头信息列表
            video_name: 视频名称
            output_dir: 输出目录
            progress_callback: 进度回调
            
        Returns:
            切片结果列表
        """
        if not shots:
            logger.warning("没有镜头信息，无法创建切片")
            return []
        
        # 准备输出目录 - 修复：确保创建slices子目录
        if output_dir:
            final_output_dir = Path(output_dir) / video_name / "slices"
        else:
            final_output_dir = self.segments_output_dir / video_name / "slices"
        
        final_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"基于 {len(shots)} 个镜头创建视频切片")
        logger.info(f"输出目录: {final_output_dir}")
        
        # 执行并行切片
        results = self.extract_segments_parallel(
            video_path=video_path,
            segments=shots,
            video_id=video_name,
            output_dir=str(final_output_dir),
            progress_callback=progress_callback
        )
        
        # 转换为兼容格式
        slices = []
        for result in results:
            if result['success']:
                slices.append({
                    'file_path': result['output_path'],
                    'start_time': result.get('start_time', 0),
                    'end_time': result.get('end_time', 0),
                    'duration': result.get('duration', 0),
                    'segment_index': result.get('segment_index', 0),
                    'file_size': result.get('file_size', 0),
                    'processing_time': result.get('processing_time', 0)
                })
        
        return slices
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True) 