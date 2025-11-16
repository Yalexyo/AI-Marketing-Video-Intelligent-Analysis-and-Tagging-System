#!/usr/bin/env python3
"""
AI Video Master 5.0 - 并行批量视频处理器 (精简版)
专注于并行处理，移除所有串行处理代码

主要特性:
1. 异步并行处理多个视频文件
2. 信号量控制并发数量（遵循API配额限制）
3. FFmpeg并行切片优化
4. 实时进度监控和错误处理
5. 重试机制和容错处理
6. 详细的性能统计报告
7. 本地转场检测（无需云服务）

添加语义合并功能，支持将相关性强的片段进行智能整合
"""

import asyncio
import json
import logging
import os
import sys
import time
import argparse
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from tenacity import retry, wait_random_exponential, stop_after_attempt

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('parallel_video_slice.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

try:
    from google_video_analyzer import GoogleVideoAnalyzer
    from parallel_video_slicer import ParallelVideoSlicer
    from semantic_segment_merger import SemanticSegmentMerger
except ImportError as e:
    logger.error(f"依赖模块导入失败: {e}")
    logger.error("请确保所有依赖文件在同一目录下")
    sys.exit(1)


class LocalSceneDetector:
    """本地转场检测器 - 基于FFmpeg和图像差异分析"""
    
    def __init__(self, threshold: float = 0.4, min_scene_duration: float = 2.0):
        """
        初始化本地转场检测器
        
        Args:
            threshold: 转场检测阈值 (0.1-1.0，越小越敏感)
            min_scene_duration: 最小镜头时长（秒）
        """
        self.threshold = threshold
        self.min_scene_duration = min_scene_duration
        
    def detect_scenes(self, video_path: str, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        检测视频中的转场点
        
        Args:
            video_path: 视频文件路径
            progress_callback: 进度回调函数
            
        Returns:
            镜头列表，每个包含start_time, end_time, duration等信息
        """
        try:
            if progress_callback:
                progress_callback(10, "开始本地转场检测...")
            
            # 1. 获取视频时长
            duration = self._get_video_duration(video_path)
            if duration <= 0:
                logger.error(f"无法获取视频时长: {video_path}")
                return []
            
            if progress_callback:
                progress_callback(20, f"视频时长: {duration:.1f}秒，分析转场...")
            
            # 2. 使用FFmpeg的scene检测滤镜
            scene_changes = self._detect_with_ffmpeg(video_path, progress_callback)
            
            if not scene_changes:
                logger.warning("FFmpeg转场检测未找到切换点，使用智能默认切片")
                return self._create_smart_default_shots(video_path, duration)
            
            if progress_callback:
                progress_callback(80, f"检测到 {len(scene_changes)} 个转场点，生成镜头...")
            
            # 3. 转换为镜头列表
            shots = self._convert_to_shots(scene_changes, duration)
            
            # 4. 合并过短的镜头
            shots = self._merge_short_scenes(shots)
            
            if progress_callback:
                progress_callback(100, f"转场检测完成: {len(shots)} 个镜头")
            
            logger.info(f"✅ 本地转场检测完成: {len(shots)} 个镜头")
            return shots
            
        except Exception as e:
            logger.error(f"本地转场检测失败: {e}")
            # 兜底方案：智能默认切片
            duration = self._get_video_duration(video_path)
            return self._create_smart_default_shots(video_path, duration)
    
    def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                "-of", "csv=p=0", video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                logger.error(f"ffprobe获取时长失败: {result.stderr}")
                return 0
                
        except Exception as e:
            logger.error(f"获取视频时长异常: {e}")
            return 0
    
    def _detect_with_ffmpeg(self, video_path: str, progress_callback: Optional[callable] = None) -> List[float]:
        """使用FFmpeg的scene检测滤镜"""
        try:
            # 创建临时文件保存检测结果
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # FFmpeg scene检测命令
            cmd = [
                "ffmpeg", "-i", video_path,
                "-filter:v", f"select='gt(scene,{self.threshold})',showinfo",
                "-f", "null", "-",
                "-v", "info"
            ]
            
            if progress_callback:
                progress_callback(30, "执行FFmpeg转场分析...")
            
            # 执行FFmpeg命令
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5分钟超时
            )
            
            if progress_callback:
                progress_callback(60, "解析转场检测结果...")
            
            # 解析输出中的时间戳
            scene_times = []
            for line in result.stderr.split('\n'):
                if 'pts_time:' in line:
                    try:
                        # 提取时间戳: pts_time:12.345
                        time_str = line.split('pts_time:')[1].split()[0]
                        scene_time = float(time_str)
                        scene_times.append(scene_time)
                    except (IndexError, ValueError):
                        continue
            
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
            
            # 去重并排序
            scene_times = sorted(list(set(scene_times)))
            
            logger.info(f"FFmpeg检测到 {len(scene_times)} 个转场点")
            return scene_times
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg转场检测超时")
            return []
        except Exception as e:
            logger.error(f"FFmpeg转场检测异常: {e}")
            return []
    
    def _convert_to_shots(self, scene_times: List[float], total_duration: float) -> List[Dict[str, Any]]:
        """将转场时间点转换为镜头列表"""
        shots = []
        
        # 添加开始时间
        times = [0.0] + scene_times + [total_duration]
        times = sorted(list(set(times)))  # 去重排序
        
        for i in range(len(times) - 1):
            start_time = times[i]
            end_time = times[i + 1]
            duration = end_time - start_time
            
            if duration > 1.5:  # 至少1.5秒
                shots.append({
                    'index': len(shots) + 1,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'type': f'镜头{len(shots) + 1}',
                    'confidence': 0.8
                })
        
        return shots
    
    def _merge_short_scenes(self, shots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """改进的镜头合并算法 - 根据min_scene_duration决定是否合并"""
        if not shots:
            return shots
        
        # 如果min_scene_duration很小(<=0.5)，说明用户想要严格按转场点切分，跳过合并
        if self.min_scene_duration <= 0.5:
            logger.info(f"严格转场模式: 保持 {len(shots)} 个原始镜头，不进行合并")
            # 只重新编号，不合并
            for i, shot in enumerate(shots):
                shot['index'] = i + 1
                shot['type'] = f"镜头{i + 1}"
            return shots
        
        # 正常合并逻辑
        merged_shots = []
        i = 0
        
        while i < len(shots):
            current_shot = shots[i].copy()
            
            # 向前合并所有相邻的短镜头
            while (i + 1 < len(shots) and 
                   (current_shot['duration'] < self.min_scene_duration or
                    shots[i + 1]['duration'] < self.min_scene_duration)):
                
                next_shot = shots[i + 1]
                current_shot['end_time'] = next_shot['end_time']
                current_shot['duration'] = current_shot['end_time'] - current_shot['start_time']
                i += 1
                
                # 如果合并后的片段已经够长，就停止合并
                if current_shot['duration'] >= self.min_scene_duration * 1.5:
                    break
            
            # 重新编号和命名
            current_shot['index'] = len(merged_shots) + 1
            current_shot['type'] = f"镜头{len(merged_shots) + 1}"
            merged_shots.append(current_shot)
            i += 1
        
        logger.info(f"镜头合并: {len(shots)} -> {len(merged_shots)} 个镜头")
        return merged_shots
    
    def _create_smart_default_shots(self, video_path: str, duration: float) -> List[Dict[str, Any]]:
        """创建智能默认切片（比固定时间切片更合理）"""
        shots = []
        
        if duration <= 0:
            return shots
        
        # 根据视频长度动态调整片段时长
        if duration <= 30:
            segment_duration = 5.0    # 短视频：5秒一段
        elif duration <= 120:
            segment_duration = 10.0   # 中等视频：10秒一段
        elif duration <= 300:
            segment_duration = 15.0   # 长视频：15秒一段
        else:
            segment_duration = 20.0   # 超长视频：20秒一段
        
        current_time = 0
        index = 1
        
        while current_time < duration:
            end_time = min(current_time + segment_duration, duration)
            
            shots.append({
                'index': index,
                'start_time': current_time,
                'end_time': end_time,
                'duration': end_time - current_time,
                'type': f'片段{index}',
                'confidence': 0.6  # 较低置信度，表示是默认切片
            })
            
            current_time = end_time
            index += 1
        
        logger.info(f"智能默认切片: {len(shots)} 个片段，每个约 {segment_duration} 秒")
        return shots


class ParallelBatchProcessor:
    """并行批处理器 - 支持语义片段合并"""
    
    def __init__(self, 
                 output_dir: str = "./data/output",
                 temp_dir: str = "./data/temp", 
                 max_concurrent: int = 3,
                 ffmpeg_workers: int = 4,
                 enable_semantic_merge: bool = True,
                 similarity_threshold: float = 0.92,  # 提高到92%（非常严格）
                 max_merge_duration: float = 25.0):   # 降低到25秒（更严格）
        """
        初始化并行批处理器
        
        Args:
            output_dir: 输出目录
            temp_dir: 临时目录
            max_concurrent: 最大视频并发数
            ffmpeg_workers: FFmpeg工作线程数
            enable_semantic_merge: 是否启用语义合并
            similarity_threshold: 语义相似度阈值
            max_merge_duration: 最大合并时长
        """
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)
        self.max_concurrent = max_concurrent
        self.ffmpeg_workers = ffmpeg_workers
        
        # 语义合并配置
        self.enable_semantic_merge = enable_semantic_merge
        self.similarity_threshold = similarity_threshold
        self.max_merge_duration = max_merge_duration

        # 创建目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.video_analyzer = GoogleVideoAnalyzer()
        self.video_slicer = ParallelVideoSlicer(max_workers=ffmpeg_workers)
        # 根据语义合并设置调整本地检测器行为
        if self.enable_semantic_merge:
            self.local_scene_detector = LocalSceneDetector(threshold=0.4, min_scene_duration=3.0)  # 启用基础合并
        else:
            self.local_scene_detector = LocalSceneDetector(threshold=0.4, min_scene_duration=0.1)  # 几乎不合并，严格按转场点切分
        
        # 初始化语义合并器
        if self.enable_semantic_merge:
            self.semantic_merger = SemanticSegmentMerger(
                similarity_threshold=similarity_threshold,
                max_merge_duration=max_merge_duration
            )
            logger.info("✅ 语义合并功能已启用")
        else:
            self.semantic_merger = None
            logger.info("⚠️  语义合并功能已禁用")

        logger.info(f"并行批处理器初始化完成")
        logger.info(f"视频并发数: {max_concurrent}")
        logger.info(f"FFmpeg线程数: {ffmpeg_workers}")
        logger.info(f"✅ 本地转场检测器已就绪")
    
    def _validate_video_file(self, video_path: str) -> bool:
        """验证视频文件"""
        try:
            if not os.path.exists(video_path):
                return False
            
            file_size = os.path.getsize(video_path)
            if file_size == 0:
                return False
            
            # 简单的文件格式检查
            valid_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'}
            if Path(video_path).suffix.lower() not in valid_extensions:
                return False
            
            return True
        except Exception:
            return False
    
    def _create_default_shots(self, video_path: str, segment_duration: float = 10.0) -> List[Dict[str, Any]]:
        """
        创建本地转场检测切片（当Google Cloud分析失败时的兜底方案）
        使用FFmpeg scene检测算法进行智能镜头识别，保持镜头完整性
        
        Args:
            video_path: 视频文件路径
            segment_duration: 兜底固定时长（秒）- 仅在转场检测也失败时使用
            
        Returns:
            智能切片列表
        """
        logger.info("🎬 使用本地转场检测器进行智能切片...")
        
        # 使用本地转场检测器
        shots = self.local_scene_detector.detect_scenes(video_path)
        
        if shots:
            logger.info(f"✅ 本地转场检测成功: {len(shots)} 个镜头")
            return shots
        else:
            logger.warning("⚠️  转场检测失败，使用智能默认切片")
            # 最后的兜底方案
            return self.local_scene_detector._create_smart_default_shots(
                video_path, 
                self.local_scene_detector._get_video_duration(video_path)
            )
    
    def _validate_slice_quality(self, slices: List[Dict[str, Any]], video_name: str) -> Dict[str, Any]:
        """验证切片质量"""
        if not slices:
            return {
                "passed": False,
                "error": "没有生成任何切片",
                "details": {}
            }
        
        # 基本质量检查
        total_slices = len(slices)
        valid_slices = 0
        total_duration = 0
        
        for slice_info in slices:
            if 'file_path' in slice_info and os.path.exists(slice_info['file_path']):
                file_size = os.path.getsize(slice_info['file_path'])
                if file_size > 1024:  # 至少1KB
                    valid_slices += 1
                    total_duration += slice_info.get('duration', 0)
        
        success_rate = (valid_slices / total_slices) * 100 if total_slices > 0 else 0
        
        return {
            "passed": success_rate >= 80,  # 80%成功率为通过
            "success_rate": success_rate,
            "total_slices": total_slices,
            "valid_slices": valid_slices,
            "total_duration": total_duration,
            "error": f"成功率过低: {success_rate:.1f}%" if success_rate < 80 else None,
            "details": {
                "video_name": video_name,
                "quality_threshold": 80,
                "check_time": datetime.now().isoformat()
            }
        }
    
    def process_single_video(self, 
                           video_path: str,
                           features: List[str] = None,
                           progress_callback: Optional[callable] = None,
                           default_segment_duration: float = 10.0,
                           analysis_mode: str = "auto") -> Dict[str, Any]:
        """
        处理单个视频文件 - 支持Google Cloud失败时的本地兜底方案
        
        Args:
            video_path: 视频文件路径
            features: 分析功能列表
            progress_callback: 进度回调函数
            default_segment_duration: 默认片段时长（当云分析失败时使用）
            
        Returns:
            处理结果字典
        """
        start_time = time.time()
        video_name = Path(video_path).stem
        
        logger.info(f"🔍 开始分析视频: {video_name}")
        
        # 验证视频文件
        if not self._validate_video_file(video_path):
            return {
                "success": False,
                "video_name": video_name,
                "error": f"视频文件无效或不存在: {video_path}",
                "processing_time": time.time() - start_time
            }
        
        if progress_callback:
            progress_callback(10, f"开始分析视频: {video_name}")
        
        try:
            # 根据分析模式选择处理方式
            if analysis_mode == "local":
                # 强制使用本地转场检测
                logger.info(f"🔧 强制使用本地转场检测模式")
                analysis_result = {"success": False, "error": "强制使用本地模式"}
            elif analysis_mode == "google":
                # 强制使用Google Cloud分析
                logger.info(f"☁️  强制使用Google Cloud分析模式")
                analysis_result = self.video_analyzer.analyze_video(
                    video_path=video_path,
                    features=features or ["shot_detection"],
                    progress_callback=lambda p, m: progress_callback(10 + p * 0.5, m) if progress_callback else None,
                    auto_cleanup_storage=True,  # 自动清理临时文件
                    bucket_name="video-slice-bucket"  # 指定存储桶
                )
            else:  # auto模式
                # 自动选择：首先尝试Google Cloud分析
                logger.info(f"🤖 自动模式：尝试Google Cloud分析")
                analysis_result = self.video_analyzer.analyze_video(
                    video_path=video_path,
                    features=features or ["shot_detection"],
                    progress_callback=lambda p, m: progress_callback(10 + p * 0.5, m) if progress_callback else None,
                    auto_cleanup_storage=True,  # 自动清理临时文件
                    bucket_name="video-slice-bucket"  # 指定存储桶
                )
            
            if not analysis_result["success"]:
                logger.warning(f"Google Cloud分析失败: {analysis_result.get('error', '未知错误')}")
                logger.info(f"🔄 切换到本地转场检测方案 (FFmpeg智能识别镜头切换)")
                
                # 使用本地默认切片方案
                shots = self._create_default_shots(video_path, default_segment_duration)
                if not shots:
                    return {
                        "success": False,
                        "video_name": video_name,
                        "error": "无法创建默认切片方案",
                        "processing_time": time.time() - start_time
                    }

                analysis_result = {
                    "success": True,
                    "shots": shots,
                    "fallback_mode": True
                }
            else:
                # Google Cloud分析成功，提取shots数据
                shots = self.video_analyzer.extract_shots(analysis_result)
                if not shots:
                    logger.warning("Google Cloud分析成功但未检测到镜头，使用本地兜底方案")
                    shots = self._create_default_shots(video_path, default_segment_duration)
                    if not shots:
                        return {
                            "success": False,
                            "video_name": video_name,
                            "error": "Google Cloud和本地方案都无法创建切片",
                            "processing_time": time.time() - start_time
                        }
                    analysis_result["fallback_mode"] = True
                
                # 更新analysis_result以包含shots数据
                analysis_result["shots"] = shots
            
            # 安全获取shots，确保键存在
            shots = analysis_result.get("shots", [])
            if not shots:
                logger.error("分析结果中没有找到shots数据")
                return {
                    "success": False,
                    "video_name": video_name,
                    "error": "分析结果中没有shots数据",
                    "processing_time": time.time() - start_time
                }

            if progress_callback:
                progress_callback(60, f"检测到 {len(shots)} 个片段，开始切片...")
            
            logger.info(f"📊 检测到 {len(shots)} 个视频片段")
            
            # 创建视频输出目录
            video_output_dir = self.output_dir / video_name
            video_output_dir.mkdir(parents=True, exist_ok=True)

            # 执行视频切片
            slices = self.video_slicer.create_slices_from_shots(
                video_path=video_path,
                shots=shots,
                video_name=video_name,
                output_dir=str(self.output_dir),
                progress_callback=lambda p, m: progress_callback(60 + p * 0.3, m) if progress_callback else None
            )

            if progress_callback:
                progress_callback(90, f"切片完成，验证质量...")
            
            # 验证切片质量
            quality_check = self._validate_slice_quality(slices, video_name)
            
            # 保存切片信息
            slices_file = video_output_dir / f"{video_name}_slices.json"
            slice_info = {
                    "video_name": video_name,
                "video_path": video_path,
                "total_slices": len(slices),
                "fallback_mode": analysis_result.get("fallback_mode", False),
                "processing_time": time.time() - start_time,
                "quality_check": quality_check,
                "slices": slices
            }
            
            with open(slices_file, 'w', encoding='utf-8') as f:
                json.dump(slice_info, f, ensure_ascii=False, indent=2)
            
            # 语义合并（如果启用）- 支持本地转场检测
            if self.enable_semantic_merge and self.semantic_merger:
                if progress_callback:
                    progress_callback(95, f"执行语义合并...")
                
                try:
                    logger.info(f"🔗 开始语义合并: {len(slices)} 个片段")
                    # 语义合并应该在slices目录下进行，直接替换原始切片
                    slices_dir = video_output_dir / "slices"
                    merge_result = self.semantic_merger.merge_segments(
                        slices, video_name, str(slices_dir)
                    )
                    
                    if merge_result.get("success") and merge_result.get("segments"):
                        # 🔧 根本性修复：用合并后的切片替换原始切片，确保统一数据源
                        merged_segments = merge_result["segments"]
                        slice_info["original_slices"] = slice_info["slices"]  # 备份原始数据
                        slice_info["slices"] = merged_segments  # 替换为合并后的最终结果
                        slice_info["total_slices"] = len(merged_segments)  # 更新总数
                        slice_info["merged_from_count"] = len(slice_info["original_slices"])  # 记录原始数量
                        slice_info["merge_applied"] = True  # 标记已应用合并
                        slice_info["merge_compression_ratio"] = merge_result.get("compression_ratio", 1.0)  # 记录压缩比
                        
                        with open(slices_file, 'w', encoding='utf-8') as f:
                            json.dump(slice_info, f, ensure_ascii=False, indent=2)
                    
                        logger.info(f"🔗 语义合并完成: {len(slices)} -> {len(merged_segments)} 个片段")
                    else:
                        logger.info("🔗 语义合并：未找到可合并的片段")
                    
                except Exception as e:
                    logger.warning(f"语义合并失败: {e}")
            elif self.enable_semantic_merge:
                logger.warning("语义合并已启用但合并器未初始化")

            if progress_callback:
                progress_callback(100, f"处理完成: {len(slices)} 个切片")
            
            processing_time = time.time() - start_time

            logger.info(f"✅ 视频处理完成: {video_name}")
            logger.info(f"📊 生成切片: {len(slices)} 个")
            logger.info(f"⏱️  处理时间: {processing_time:.1f}秒")

            return {
                "success": True,
                "video_name": video_name,
                "video_path": video_path,
                "total_slices": len(slices),
                "fallback_mode": analysis_result.get("fallback_mode", False),
                "processing_time": processing_time,
                "quality_passed": quality_check["passed"],
                "slices": slices
            }

        except Exception as e:
            error_msg = f"视频处理异常: {str(e)}"
            logger.error(f"❌ {video_name}: {error_msg}")
            
            return {
                "success": False,
                "video_name": video_name,
                "error": error_msg,
                "processing_time": time.time() - start_time
            }
    
    @retry(
        wait=wait_random_exponential(multiplier=1, max=120),
        stop=stop_after_attempt(3)
    )
    async def async_process_video(self, video_path: str, features: List[str] = None) -> Dict[str, Any]:
        """
        异步处理单个视频文件
        
        Args:
            video_path: 视频文件路径
            features: 分析功能列表
            
        Returns:
            处理结果字典
        """
        async with self.semaphore:  # 限制并发数
            video_name = Path(video_path).stem
            
            try:
                logger.info(f"🎬 开始异步处理视频: {video_name}")
                start_time = time.time()
                
                # 使用线程池执行同步的视频处理
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    self.process_single_video, 
                    video_path, 
                    features
                )
                
                end_time = time.time()
                duration = end_time - start_time
                
                if result.get("success"):
                    logger.info(f"✅ 视频处理完成: {video_name} ({duration:.1f}秒)")
                else:
                    logger.error(f"❌ 视频处理失败: {video_name}")
                
                return result
                
            except Exception as e:
                error_msg = f"异步处理视频失败 {video_name}: {str(e)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "video_name": video_name,
                    "error": error_msg,
                    "slices_count": 0,
                    "slices": []
                }
    
    async def parallel_batch_process(self, video_files: List[str], 
                                   features: List[str] = None,
                                   progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        并行批量处理视频文件
        
        Args:
            video_files: 视频文件路径列表
            features: 分析功能列表
            progress_callback: 进度回调函数
            
        Returns:
            批处理结果
        """
        total_videos = len(video_files)
        self.stats["total_videos"] = total_videos
        
        logger.info(f"🚀 开始并行处理 {total_videos} 个视频文件 (最大并发: {self.max_concurrent})")
        
        if progress_callback:
            progress_callback(0, f"开始并行处理 {total_videos} 个视频...")
        
        start_time = time.time()
        
        # 创建异步任务列表
        tasks = []
        for i, video_file in enumerate(video_files):
            task = self.async_process_video(str(video_file), features)
            tasks.append(task)
        
        # 并行执行所有任务，使用as_completed获取进度
        results = []
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results.append(result)
                completed += 1
                
                # 更新统计信息
                if result.get("success"):
                    self.stats["processed_videos"] += 1
                    self.stats["total_slices"] += result.get("slices_count", 0)
                else:
                    self.stats["failed_videos"] += 1
                    self.stats["processing_errors"].append({
                        "video": result.get("video_name", "unknown"),
                        "error": result.get("error", "unknown error")
                    })
                
                # 进度回调
                progress = int((completed / total_videos) * 100)
                if progress_callback:
                    progress_callback(
                        progress, 
                        f"已完成 {completed}/{total_videos} 个视频 "
                        f"(成功: {self.stats['processed_videos']}, "
                        f"失败: {self.stats['failed_videos']})"
                    )
                
                logger.info(f"📊 进度: {completed}/{total_videos} ({progress}%)")
                
            except Exception as e:
                logger.error(f"处理任务时发生异常: {e}")
                results.append({
                    "success": False,
                    "video_name": "unknown",
                    "error": str(e),
                    "slices_count": 0,
                    "slices": []
                })
                completed += 1
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # 生成详细报告
        report_data = {
            'batch_stats': self.stats.copy(),
            'processing_results': results,
            'parallel_info': {
                'max_concurrent': self.max_concurrent,
                'total_duration_seconds': total_duration,
                'average_time_per_video': total_duration / total_videos if total_videos > 0 else 0,
                'estimated_sequential_time': sum([r.get('duration', 94) for r in results if r.get('success')]),
                'time_saved_percentage': 0
            },
            'generated_at': datetime.now().isoformat()
        }
        
        # 计算时间节省
        estimated_sequential = report_data['parallel_info']['estimated_sequential_time']
        if estimated_sequential > 0:
            time_saved = max(0, (estimated_sequential - total_duration) / estimated_sequential * 100)
            report_data['parallel_info']['time_saved_percentage'] = time_saved
        
        # 保存报告
        report_file = self.output_dir / "parallel_batch_processing_report.json"
        
        # 清理批处理报告中的numpy数组
        cleaned_batch_report = self._clean_for_json_serialization(report_data)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_batch_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"🎉 并行批处理完成!")
        logger.info(f"📊 处理统计: 成功 {self.stats['processed_videos']}/{total_videos} 个视频")
        logger.info(f"🎬 总计生成: {self.stats['total_slices']} 个视频切片")
        logger.info(f"⏱️  总耗时: {total_duration:.1f}秒")
        logger.info(f"📄 详细报告: {report_file}")
        
        if report_data['parallel_info']['time_saved_percentage'] > 0:
            logger.info(f"🚀 性能提升: 节省了 {report_data['parallel_info']['time_saved_percentage']:.1f}% 的时间!")
        
        return {
            "success": True,
            "stats": self.stats,
            "results": results,
            "report_file": str(report_file),
            "total_duration": total_duration,
            "parallel_info": report_data['parallel_info']
        }
    
    def process_batch_sync(self, input_dir: str, file_patterns: List[str] = None, 
                          features: List[str] = None,
                          default_segment_duration: float = 10.0,
                          analysis_mode: str = "auto") -> Dict[str, Any]:
        """
        同步批处理视频文件（支持语义合并）
        
        Args:
            input_dir: 输入目录
            file_patterns: 文件匹配模式
            features: 分析功能列表
            
        Returns:
            批处理结果
        """
        if not file_patterns:
            file_patterns = ["*.mp4", "*.MP4", "*.avi", "*.AVI", "*.mov", "*.MOV", "*.mkv", "*.MKV"]
        if not features:
            features = ["shot_detection"]

        input_path = Path(input_dir)
        
        if not input_path.exists():
            logger.error(f"输入目录不存在: {input_dir}")
            return {
                "success": False,
                "error": f"Input directory does not exist: {input_dir}"
            }

        # 收集视频文件
        video_files = []
        for pattern in file_patterns:
            video_files.extend(input_path.glob(pattern))

        if not video_files:
            logger.warning(f"未找到匹配的视频文件: {file_patterns}")
            return {
                "success": False,
                "error": f"No video files found matching patterns: {file_patterns}"
            }

        logger.info(f"🎬 发现 {len(video_files)} 个视频文件")
        logger.info(f"🔧 语义合并: {'启用' if self.enable_semantic_merge else '禁用'}")
        if self.enable_semantic_merge:
            logger.info(f"📊 相似度阈值: {self.similarity_threshold}")
            logger.info(f"⏱️  最大合并时长: {self.max_merge_duration}秒")

        batch_start_time = time.time()
        results = []
        
        # 使用线程池进行并行处理
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # 提交所有任务
            future_to_video = {
                executor.submit(self.process_single_video, str(video_file), features, None, default_segment_duration, analysis_mode): video_file
                for video_file in video_files
            }

            # 收集结果
            for future in as_completed(future_to_video):
                video_file = future_to_video[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        merge_info = ""
                        if self.enable_semantic_merge and result.get('compression_ratio', 1.0) > 1.0:
                            merge_info = f" (压缩比: {result['compression_ratio']:.1f}x)"
                        logger.info(f"✅ 完成 {len(results)}/{len(video_files)}: {result['video_name']}{merge_info}")
                    else:
                        logger.error(f"❌ 失败 {len(results)}/{len(video_files)}: {video_file.name} - {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"❌ 处理异常: {video_file.name} - {e}")
                    results.append({
                        "success": False,
                        "video_name": video_file.stem,
                        "error": str(e),
                        "duration": 0
                    })

        # 生成批处理报告
        batch_end_time = time.time()
        batch_duration = batch_end_time - batch_start_time

        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]

        # 计算语义合并统计
        total_original_slices = sum(r.get('original_slices', 0) for r in successful_results)
        total_final_slices = sum(r.get('slices_count', 0) for r in successful_results)
        total_compression_ratio = total_original_slices / max(1, total_final_slices)

        batch_report = {
            "timestamp": datetime.now().isoformat(),
            "input_directory": str(input_path),
            "output_directory": str(self.output_dir),
            "file_patterns": file_patterns,
            "features": features,
            "semantic_merge_enabled": self.enable_semantic_merge,
            "similarity_threshold": self.similarity_threshold,
            "max_merge_duration": self.max_merge_duration,
            "total_duration": batch_duration,
            "stats": {
                "total_videos": len(video_files),
                "processed_videos": len(successful_results),
                "failed_videos": len(failed_results),
                "total_slices": total_final_slices,
                "original_slices": total_original_slices,
                "compression_ratio": total_compression_ratio,
                "average_time_per_video": batch_duration / max(1, len(video_files))
            },
            "parallel_info": {
                "max_concurrent_videos": self.max_concurrent,
                "ffmpeg_workers": self.ffmpeg_workers,
                "estimated_sequential_time": sum(r.get('duration', 0) for r in results),
                "actual_parallel_time": batch_duration,
                "time_saved_percentage": max(0, (sum(r.get('duration', 0) for r in results) - batch_duration) / max(batch_duration, 0.001) * 100),
                "average_time_per_video": batch_duration / max(1, len(results))
            },
            "results": results
        }

        # 保存批处理报告
        report_file = self.output_dir / "parallel_batch_processing_report.json"
        
        # 清理批处理报告中的numpy数组
        cleaned_batch_report = self._clean_for_json_serialization(batch_report)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_batch_report, f, indent=2, ensure_ascii=False)

        # 输出统计信息
        logger.info(f"🎉 批处理完成!")
        logger.info(f"📊 成功处理: {len(successful_results)}/{len(video_files)} 个视频")
        if failed_results:
            logger.info(f"❌ 失败: {len(failed_results)} 个视频")
        logger.info(f"🎬 总切片数: {total_final_slices}")
        if self.enable_semantic_merge and total_compression_ratio > 1.0:
            logger.info(f"🧠 语义压缩比: {total_compression_ratio:.1f}x")
        logger.info(f"⏱️  总时间: {batch_duration:.1f}秒")
        logger.info(f"📄 报告文件: {report_file}")

        return {
            "success": len(successful_results) > 0,
            "stats": batch_report["stats"],
            "parallel_info": batch_report["parallel_info"],
            "total_duration": batch_duration,
            "report_file": str(report_file),
            "results": results
        }

    def _clean_for_json_serialization(self, obj):
        """
        递归清理对象以准备JSON序列化，移除所有numpy数组和不可序列化的对象
        
        Args:
            obj: 要清理的对象
            
        Returns:
            清理后的可序列化对象
        """
        import numpy as np
        
        if isinstance(obj, np.ndarray):
            # numpy数组转换为列表
            return obj.tolist()
        elif isinstance(obj, dict):
            # 递归清理字典
            cleaned_dict = {}
            for key, value in obj.items():
                # 跳过特定的不可序列化字段
                if key in ['clip_features', 'features', 'model_output']:
                    continue
                try:
                    cleaned_dict[key] = self._clean_for_json_serialization(value)
                except (TypeError, ValueError):
                    # 如果值不能序列化，就跳过
                    continue
            return cleaned_dict
        elif isinstance(obj, list):
            # 递归清理列表
            return [self._clean_for_json_serialization(item) for item in obj]
        elif hasattr(obj, 'tolist') and callable(getattr(obj, 'tolist')):
            # 支持tolist的numpy类型
            try:
                return obj.tolist()
            except:
                return str(obj)
        elif hasattr(obj, '__dict__'):
            # 自定义对象转换为字典
            return self._clean_for_json_serialization(obj.__dict__)
        else:
            # 基本类型直接返回
            return obj


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI Video Master 5.0 - 并行批量视频切片工具")
    parser.add_argument("input_dir", help="输入视频目录")
    parser.add_argument("-o", "--output", default="./data/output", help="输出目录")
    parser.add_argument("-t", "--temp", default="./data/temp", help="临时目录")
    parser.add_argument("-f", "--features", nargs="+", 
                       choices=["shot_detection", "label_detection", "face_detection", "text_detection"],
                       default=["shot_detection"],
                       help="分析功能 (默认仅镜头检测，性能最佳)")
    parser.add_argument("-c", "--concurrent", type=int, default=3,
                       help="视频级最大并发数 (默认3，建议不超过3以遵循API配额)")
    parser.add_argument("-w", "--ffmpeg-workers", type=int, default=4,
                       help="FFmpeg并行切片工作线程数 (默认4，建议2-8)")
    parser.add_argument("--patterns", nargs="+", 
                       default=["*.mp4", "*.MP4", "*.avi", "*.AVI", "*.mov", "*.MOV", "*.mkv", "*.MKV"],
                       help="文件匹配模式(支持大小写)")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 检查环境变量
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        if not os.path.exists("google_credentials.json"):
            logger.error("请设置 GOOGLE_APPLICATION_CREDENTIALS 环境变量")
            logger.error("或将Google Cloud凭据文件放在当前目录下并命名为 google_credentials.json")
            return 1
    
    try:
        # 创建并行处理器
        processor = ParallelBatchProcessor(
            output_dir=args.output,
            temp_dir=args.temp,
            max_concurrent=args.concurrent,
            ffmpeg_workers=args.ffmpeg_workers
        )
        
        # 执行并行批处理
        result = processor.process_batch_sync(
            input_dir=args.input_dir,
            file_patterns=args.patterns,
            features=args.features
        )
        
        if result["success"]:
            print(f"\n✅ 并行批处理完成!")
            print(f"📊 处理统计: {result['stats']['processed_videos']}/{result['stats']['total_videos']} 个视频成功")
            print(f"🎬 总计生成: {result['stats']['total_slices']} 个视频切片")
            print(f"⏱️  总耗时: {result['total_duration']:.1f}秒")
            print(f"📄 详细报告: {result['report_file']}")
            
            if result['parallel_info']['time_saved_percentage'] > 0:
                print(f"🚀 性能提升: 节省了 {result['parallel_info']['time_saved_percentage']:.1f}% 的时间!")
            
            return 0
        else:
            print(f"\n❌ 并行批处理失败: {result['error']}")
            return 1
            
    except KeyboardInterrupt:
        logger.info("用户中断处理")
        return 130
    except Exception as e:
        logger.error(f"程序异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 