#!/usr/bin/env python3
"""
语义片段合并器 - 基于视觉和语义相似性合并视频片段
使用CLIP模型进行多模态分析，实现智能片段整合

主要功能:
1. 视觉相似性分析
2. 语义内容理解
3. 相邻片段合并策略
4. 时间连贯性保证
"""

import os
import cv2
import numpy as np
import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import torch
    from transformers import CLIPProcessor, CLIPModel
    from PIL import Image
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    logger.warning("CLIP模型不可用，请安装: pip install torch transformers pillow")


class SemanticSegmentMerger:
    """语义片段合并器"""
    
    def __init__(self, 
                 similarity_threshold: float = 0.92,
                 max_merge_duration: float = 25.0,
                 min_segment_duration: float = 2.0):
        """
        初始化语义片段合并器
        
        Args:
            similarity_threshold: 语义相似度阈值 (0-1)
            max_merge_duration: 单个合并片段最大时长(秒)
            min_segment_duration: 最小片段时长(秒)
        """
        self.similarity_threshold = similarity_threshold
        self.max_merge_duration = max_merge_duration
        self.min_segment_duration = min_segment_duration
        
        # 初始化CLIP模型
        self.clip_model = None
        self.clip_processor = None
        self._init_clip_model()
        
        logger.info(f"语义片段合并器初始化完成")
        logger.info(f"相似度阈值: {similarity_threshold}")
        logger.info(f"最大合并时长: {max_merge_duration}秒")
        logger.info(f"最小片段时长: {min_segment_duration}秒")
    
    def _init_clip_model(self):
        """初始化CLIP模型"""
        if not CLIP_AVAILABLE:
            logger.warning("CLIP模块不可用，将使用基础相似性分析")
            print(f"⚠️ CLIP依赖未安装，将使用基础分析模式")
            return
        
        try:
            model_name = "openai/clip-vit-base-patch32"
            cache_dir = Path("./cache/clip").resolve()
            
            # 首先尝试加载离线模型
            logger.info(f"尝试加载离线CLIP模型: {model_name}")
            print(f"🔍 检查本地CLIP模型...")
            
            try:
                # 尝试离线加载
                self.clip_model = CLIPModel.from_pretrained(
                    model_name,
                    cache_dir=str(cache_dir),
                    local_files_only=True  # 只使用本地文件
                )
                self.clip_processor = CLIPProcessor.from_pretrained(
                    model_name,
                    cache_dir=str(cache_dir),
                    local_files_only=True
                )
                print("✅ 成功加载本地CLIP模型")
                
            except Exception as offline_error:
                logger.warning(f"离线模型加载失败: {offline_error}")
                print(f"⚠️ 本地模型不存在，尝试在线下载...")
                
                # 如果离线加载失败，尝试在线下载
                self.clip_model = CLIPModel.from_pretrained(
                    model_name,
                    cache_dir=str(cache_dir),
                    local_files_only=False
                )
                self.clip_processor = CLIPProcessor.from_pretrained(
                    model_name,
                    cache_dir=str(cache_dir),
                    local_files_only=False
                )
                print("✅ 在线下载模型成功")
            
            # 设置为评估模式
            self.clip_model.eval()
            
            # 检查GPU可用性
            if torch.cuda.is_available():
                self.clip_model = self.clip_model.to('cuda')
                logger.info("CLIP模型已加载到GPU")
                print("🎮 CLIP模型已加载到GPU")
            else:
                logger.info("CLIP模型使用CPU")
                print("💻 CLIP模型使用CPU")
                
            logger.info("CLIP模型初始化成功")
            
        except Exception as e:
            logger.warning(f"CLIP模型初始化失败: {e}")
            print(f"⚠️ CLIP模型初始化失败，将使用基础分析模式")
            print(f"   建议运行: uv run python download_models.py")
            self.clip_model = None
            self.clip_processor = None
    
    def extract_video_frames(self, video_path: str, num_frames: int = 5) -> List[np.ndarray]:
        """
        从视频中提取关键帧
        
        Args:
            video_path: 视频文件路径
            num_frames: 提取帧数
            
        Returns:
            帧图像列表
        """
        frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if total_frames <= 0:
                logger.warning(f"无法读取视频帧: {video_path}")
                return frames
            
            # 均匀采样帧
            frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
            
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    # 转换颜色空间 BGR -> RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(frame_rgb)
                else:
                    logger.warning(f"无法读取第{frame_idx}帧")
            
            cap.release()
            
        except Exception as e:
            logger.error(f"提取视频帧失败 {video_path}: {e}")
        
        return frames
    
    def compute_clip_features(self, frames: List[np.ndarray]) -> Optional[np.ndarray]:
        """
        使用CLIP计算视频帧特征
        
        Args:
            frames: 视频帧列表
            
        Returns:
            特征向量 或 None
        """
        if not self.clip_model or not frames:
            # 如果CLIP不可用，使用基础特征
            return self._compute_basic_features(frames)
        
        try:
            # 转换为PIL图像
            pil_images = [Image.fromarray(frame) for frame in frames]
            
            # 预处理图像
            inputs = self.clip_processor(images=pil_images, return_tensors="pt", padding=True)
            
            # 移动到GPU（如果可用）
            if torch.cuda.is_available():
                inputs = {k: v.to('cuda') for k, v in inputs.items()}
            
            # 计算图像特征
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
                
                # 取平均值作为视频特征
                video_features = torch.mean(image_features, dim=0)
                
                # 归一化
                video_features = video_features / video_features.norm(dim=-1, keepdim=True)
                
                return video_features.cpu().numpy()
                
        except Exception as e:
            logger.error(f"CLIP特征计算失败，使用基础特征: {e}")
            return self._compute_basic_features(frames)
    
    def _compute_basic_features(self, frames: List[np.ndarray]) -> Optional[np.ndarray]:
        """
        计算基础视觉特征（不依赖CLIP）
        
        Args:
            frames: 视频帧列表
            
        Returns:
            基础特征向量
        """
        if not frames:
            return None
        
        try:
            features = []
            
            for frame in frames:
                # 计算颜色直方图
                hist_b = cv2.calcHist([frame], [0], None, [32], [0, 256])
                hist_g = cv2.calcHist([frame], [1], None, [32], [0, 256])
                hist_r = cv2.calcHist([frame], [2], None, [32], [0, 256])
                
                # 归一化直方图
                hist_b = hist_b.flatten() / np.sum(hist_b)
                hist_g = hist_g.flatten() / np.sum(hist_g)
                hist_r = hist_r.flatten() / np.sum(hist_r)
                
                # 合并颜色特征
                color_features = np.concatenate([hist_r, hist_g, hist_b])
                
                # 计算亮度和对比度特征
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                brightness = np.mean(gray)
                contrast = np.std(gray)
                
                # 计算边缘特征
                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges > 0) / edges.size
                
                # 组合所有特征
                frame_features = np.concatenate([
                    color_features,
                    [brightness, contrast, edge_density]
                ])
                
                features.append(frame_features)
            
            # 取所有帧特征的平均值
            video_features = np.mean(features, axis=0)
            
            # 归一化
            video_features = video_features / np.linalg.norm(video_features)
            
            return video_features
            
        except Exception as e:
            logger.error(f"基础特征计算失败: {e}")
            return None
    
    def compute_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """计算语义相似性"""
        try:
            similarity = np.dot(features1, features2) / (
                np.linalg.norm(features1) * np.linalg.norm(features2)
            )
            return float((similarity + 1) / 2)  # 归一化到 [0, 1]
        except Exception as e:
            logger.error(f"相似度计算失败: {e}")
            return 0.0
    
    def analyze_segments_similarity(self, segments: List[Dict[str, Any]], progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        分析片段间的语义相似性，确保时间顺序的连贯性
        
        Args:
            segments: 视频片段列表
            progress_callback: 进度回调函数
            
        Returns:
            带有相似性信息的片段列表，按时间顺序排序
        """
        logger.info(f"开始分析 {len(segments)} 个片段的语义相似性")
        
        # 🚨 关键修复：首先按时间顺序排序所有片段
        logger.info("📊 按时间顺序排序片段...")
        sorted_segments = sorted(segments, key=lambda x: x.get('start_time', 0))
        
        # 验证时间顺序和连贯性
        logger.info("🔍 验证时间连贯性...")
        time_gaps = []
        for i in range(len(sorted_segments) - 1):
            current_end = sorted_segments[i].get('end_time', 0)
            next_start = sorted_segments[i + 1].get('start_time', 0)
            gap = next_start - current_end
            time_gaps.append(gap)
            if gap > 2.0:  # 超过2秒的时间间隔
                logger.warning(f"⚠️  片段 {i+1} 和 {i+2} 之间有 {gap:.1f}s 时间间隔")
        
        avg_gap = sum(time_gaps) / len(time_gaps) if time_gaps else 0
        logger.info(f"平均时间间隔: {avg_gap:.2f}s")
        
        if progress_callback:
            progress_callback(20, f"分析 {len(sorted_segments)} 个片段特征...")
        
        # 为每个片段计算特征
        for i, segment in enumerate(sorted_segments):
            if progress_callback and len(sorted_segments) > 1:
                progress = 20 + (i / len(sorted_segments)) * 20  # 20-40%
                progress_callback(progress, f"处理片段 {i+1}/{len(sorted_segments)}")
            
            if not os.path.exists(segment.get('file_path', '')):
                logger.warning(f"片段文件不存在: {segment.get('file_path')}")
                segment['clip_features'] = None
                segment['has_features'] = False
                continue
            
            # 提取视频帧
            frames = self.extract_video_frames(segment['file_path'])
            
            if frames:
                # 计算CLIP特征
                features = self.compute_clip_features(frames)
                segment['clip_features'] = features
                segment['has_features'] = features is not None
            else:
                segment['clip_features'] = None
                segment['has_features'] = False
            
            # 记录时间顺序索引
            segment['time_order_index'] = i
            
            logger.debug(f"片段 {i+1}/{len(sorted_segments)} 特征计算完成")
        
        # 🔑 关键：基于时间顺序计算相邻片段的相似度
        logger.info("🧠 计算时间相邻片段的语义相似度...")
        for i in range(len(sorted_segments) - 1):
            current_seg = sorted_segments[i]
            next_seg = sorted_segments[i + 1]
            
            # 额外验证：确保这两个片段在时间上是真正相邻的
            current_end = current_seg.get('end_time', 0)
            next_start = next_seg.get('start_time', 0)
            time_gap = next_start - current_end
            
            if (current_seg.get('has_features') and 
                next_seg.get('has_features') and
                time_gap <= 2.0):  # 只有时间间隔不超过2秒才计算相似度
                
                similarity = self.compute_similarity(
                    current_seg['clip_features'],
                    next_seg['clip_features']
                )
                
                current_seg['similarity_to_next'] = similarity
                current_seg['time_gap_to_next'] = time_gap
                logger.debug(f"片段 {i}->{i+1} 相似度: {similarity:.3f}, 时间间隔: {time_gap:.1f}s")
            else:
                current_seg['similarity_to_next'] = 0.0
                current_seg['time_gap_to_next'] = time_gap if time_gap <= 10.0 else 10.0
                if time_gap > 2.0:
                    logger.debug(f"片段 {i}->{i+1}: 时间间隔过大({time_gap:.1f}s)，不计算相似度")
        
        # 最后一个片段没有下一个
        if sorted_segments:
            sorted_segments[-1]['similarity_to_next'] = 0.0
            sorted_segments[-1]['time_gap_to_next'] = 0.0
        
        logger.info(f"✅ 完成语义相似性分析，共 {len(sorted_segments)} 个片段，按时间顺序排列")
        return sorted_segments
    
    def merge_similar_segments(self, 
                             segments: List[Dict[str, Any]], 
                             video_path: str,
                             output_dir: str) -> List[Dict[str, Any]]:
        """
        合并相似的片段，直接替换原始切片文件
        
        Args:
            segments: 已分析的片段列表
            video_path: 原始视频路径
            output_dir: 输出目录（slices文件夹）
            
        Returns:
            合并后的片段列表
        """
        if not segments:
            return []
        
        logger.info(f"🔗 开始严格语义合并")
        logger.info(f"📊 相似度阈值: {self.similarity_threshold} (严格模式)")
        logger.info(f"⏱️  最大合并时长: {self.max_merge_duration}秒")
        
        # 备份原始文件到临时目录
        backup_dir = Path(output_dir) / "backup_before_merge"
        backup_dir.mkdir(exist_ok=True)
        
        final_segments = []
        current_group = []
        files_to_delete = []  # 需要删除的原始文件
        
        # 遍历所有片段进行合并分组
        for i, segment in enumerate(segments):
            if not current_group:
                current_group = [segment]
                continue
            
            current_segment = current_group[-1]
            
            # 判断是否应该合并到当前组
            should_merge = self._should_merge_segments_strict(current_group, segment, current_segment)
            
            if should_merge:
                current_group.append(segment)
                logger.debug(f"📎 片段{segment.get('segment_index')} 加入合并组 (相似度: {current_segment.get('similarity_to_next', 0):.3f})")
            else:
                # 处理当前组
                result_segment = self._process_segment_group(
                    current_group, video_path, output_dir, backup_dir, len(final_segments)
                )
                if result_segment:
                    final_segments.append(result_segment)
                    # 如果是合并的，记录需要删除的原始文件
                    if result_segment.get('is_merged', False):
                        for seg in current_group:
                            files_to_delete.append(seg.get('file_path'))
                
                current_group = [segment]
        
        # 处理最后一组
        if current_group:
            result_segment = self._process_segment_group(
                current_group, video_path, output_dir, backup_dir, len(final_segments)
            )
            if result_segment:
                final_segments.append(result_segment)
                if result_segment.get('is_merged', False):
                    for seg in current_group:
                        files_to_delete.append(seg.get('file_path'))
        
        # 删除被合并的原始文件
        deleted_count = 0
        for file_path in files_to_delete:
            if file_path and os.path.exists(file_path):
                try:
                    # 先备份到backup目录
                    backup_path = backup_dir / Path(file_path).name
                    shutil.copy2(file_path, backup_path)
                    # 然后删除原文件
                    os.remove(file_path)
                    deleted_count += 1
                    logger.debug(f"🗑️  删除原始文件: {Path(file_path).name}")
                except Exception as e:
                    logger.warning(f"删除文件失败 {file_path}: {e}")
        
        logger.info(f"🎯 合并完成: {len(segments)} -> {len(final_segments)} 个片段")
        logger.info(f"🗑️  删除原始文件: {deleted_count} 个")
        logger.info(f"💾 备份文件保存在: {backup_dir}")
        
        return final_segments
    
    def _should_merge_segments(self, 
                              current_group: List[Dict[str, Any]], 
                              next_segment: Dict[str, Any],
                              current_segment: Dict[str, Any]) -> bool:
        """
        判断是否应该合并片段
        
        Args:
            current_group: 当前合并组
            next_segment: 下一个片段
            current_segment: 当前片段
            
        Returns:
            是否应该合并
        """
        # 检查相似度阈值
        similarity = current_segment.get('similarity_to_next', 0.0)
        if similarity < self.similarity_threshold:
            return False
        
        # 检查合并后时长
        group_duration = sum(seg.get('duration', 0) for seg in current_group)
        next_duration = next_segment.get('duration', 0)
        
        if group_duration + next_duration > self.max_merge_duration:
            return False
        
        # 检查时间连续性（容忍小的时间间隔）
        last_seg = current_group[-1]
        time_gap = abs(next_segment.get('start_time', 0) - last_seg.get('end_time', 0))
        
        if time_gap > 1.0:  # 超过1秒间隔就不合并
            return False
        
        return True
    
    def _should_merge_segments_strict(self, 
                                    current_group: List[Dict[str, Any]], 
                                    next_segment: Dict[str, Any],
                                    current_segment: Dict[str, Any]) -> bool:
        """
        严格模式下判断是否应该合并片段
        
        Args:
            current_group: 当前合并组
            next_segment: 下一个片段
            current_segment: 当前片段
            
        Returns:
            是否应该合并
        """
        # 检查相似度阈值（更严格）
        similarity = current_segment.get('similarity_to_next', 0.0)
        if similarity < self.similarity_threshold:
            return False
        
        # 检查合并后时长（更严格）
        group_duration = sum(seg.get('duration', 0) for seg in current_group)
        next_duration = next_segment.get('duration', 0)
        
        if group_duration + next_duration > self.max_merge_duration:
            return False
        
        # 检查时间连续性（更严格，容忍更小的时间间隔）
        last_seg = current_group[-1]
        time_gap = abs(next_segment.get('start_time', 0) - last_seg.get('end_time', 0))
        
        if time_gap > 0.5:  # 超过0.5秒间隔就不合并
            return False
        
        # 额外检查：不允许合并超过3个片段
        if len(current_group) >= 3:
            return False
        
        return True
    
    def _process_segment_group(self, 
                             segment_group: List[Dict[str, Any]], 
                             video_path: str,
                             output_dir: str,
                             backup_dir: Path,
                             index: int) -> Optional[Dict[str, Any]]:
        """
        处理片段组，如果需要合并则创建合并文件，否则保留原文件
        
        Args:
            segment_group: 要处理的片段组
            video_path: 原始视频路径
            output_dir: 输出目录（slices文件夹）
            backup_dir: 备份目录
            index: 片段索引
            
        Returns:
            处理后的片段信息
        """
        if not segment_group:
            return None
        
        # 如果只有一个片段，直接返回，不做任何修改
        if len(segment_group) == 1:
            segment = segment_group[0].copy()
            segment['is_merged'] = False
            segment['original_count'] = 1
            return segment
        
        try:
            # 多个片段需要合并
            start_time = min(seg.get('start_time', 0) for seg in segment_group)
            end_time = max(seg.get('end_time', 0) for seg in segment_group)
            duration = end_time - start_time
            
            # 生成合并后的文件名，直接保存在slices目录下
            video_name = Path(video_path).stem
            first_seg_index = segment_group[0].get('segment_index', 1)
            last_seg_index = segment_group[-1].get('segment_index', 1)
            
            merged_filename = f"{video_name}_merged_{first_seg_index:03d}-{last_seg_index:03d}.mp4"
            merged_path = Path(output_dir) / merged_filename
            
            # 使用FFmpeg合并片段
            success = self._merge_video_segments(video_path, start_time, end_time, str(merged_path))
            
            if success:
                merged_segment = {
                    'file_path': str(merged_path),
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'segment_index': first_seg_index,  # 使用第一个片段的索引
                    'file_size': merged_path.stat().st_size if merged_path.exists() else 0,
                    'is_merged': True,
                    'original_count': len(segment_group),
                    'original_segments': [seg.get('segment_index') for seg in segment_group],
                    'merge_similarity': sum(seg.get('similarity_to_next', 0) for seg in segment_group[:-1]) / max(1, len(segment_group) - 1)
                }
                
                logger.info(f"✅ 合并 {len(segment_group)} 个片段 -> {merged_filename}")
                return merged_segment
            else:
                logger.error(f"❌ 合并失败: {merged_filename}")
                return None
                
        except Exception as e:
            logger.error(f"处理片段组失败: {e}")
            return None
    
    def _create_merged_segment(self, 
                              segment_group: List[Dict[str, Any]], 
                              video_path: str,
                              output_dir: str,
                              index: int,
                              merge_session_dir: str) -> Optional[Dict[str, Any]]:
        """
        创建合并后的视频片段，保存到指定的合并会话目录
        
        Args:
            segment_group: 要合并的片段组
            video_path: 原始视频路径
            output_dir: 原输出目录
            index: 合并片段索引
            merge_session_dir: 本次合并会话目录
            
        Returns:
            合并后的片段信息
        """
        if not segment_group:
            return None
        
        # 如果只有一个片段，创建符号链接或复制引用
        if len(segment_group) == 1:
            segment = segment_group[0].copy()
            segment['is_merged'] = False
            segment['original_count'] = 1
            segment['merge_session'] = Path(merge_session_dir).name
            return segment
        
        try:
            # 计算合并时间范围
            start_time = min(seg.get('start_time', 0) for seg in segment_group)
            end_time = max(seg.get('end_time', 0) for seg in segment_group)
            duration = end_time - start_time
            
            # 生成结构化的输出文件名
            video_name = Path(video_path).stem
            timestamp = datetime.now().strftime("%H%M%S")
            merged_filename = f"{video_name}_merged_{index+1:03d}_from{len(segment_group)}clips_{timestamp}.mp4"
            merged_path = Path(merge_session_dir) / merged_filename
            
            # 使用FFmpeg合并片段
            success = self._merge_video_segments(video_path, start_time, end_time, str(merged_path))
            
            if success:
                merged_segment = {
                    'file_path': str(merged_path),
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'segment_index': index + 1,
                    'file_size': merged_path.stat().st_size if merged_path.exists() else 0,
                    'is_merged': True,
                    'original_count': len(segment_group),
                    'original_segments': [seg.get('segment_index') for seg in segment_group],
                    'merge_similarity': sum(seg.get('similarity_to_next', 0) for seg in segment_group[:-1]) / max(1, len(segment_group) - 1),
                    'merge_session': Path(merge_session_dir).name
                }
                
                logger.info(f"✅ 成功合并 {len(segment_group)} 个片段: {merged_filename}")
                return merged_segment
            else:
                logger.error(f"❌ 合并失败: {merged_filename}")
                return None
                
        except Exception as e:
            logger.error(f"创建合并片段失败: {e}")
            return None
    
    def _merge_video_segments(self, video_path: str, start_time: float, end_time: float, output_path: str) -> bool:
        """
        使用FFmpeg合并视频片段（精确时间定位版本）
        
        Args:
            video_path: 原始视频路径
            start_time: 开始时间
            end_time: 结束时间
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            # 格式化时间
            start_str = self._format_time_for_ffmpeg(start_time)
            duration = end_time - start_time
            duration_str = self._format_time_for_ffmpeg(duration)
            
            # FFmpeg命令（精确时间定位模式 - 解决静止画面问题）
            cmd = [
                "ffmpeg", "-y",
                "-ss", start_str,                # ⚠️ 关键：输入前定位，更精确
                "-i", video_path,
                "-t", duration_str,
                "-c:v", "libx264",               # ✅ 重新编码视频流，确保精确切割
                "-c:a", "aac",                   # ✅ 重新编码音频流
                "-preset", "fast",               # 快速编码预设
                "-crf", "23",                    # 高质量编码
                "-avoid_negative_ts", "make_zero",
                "-fflags", "+genpts",
                "-reset_timestamps", "1",         # ✅ 重置时间戳从0开始
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
            
            if result.returncode == 0:
                logger.debug(f"✅ 精确视频合并成功: {Path(output_path).name}")
                return True
            else:
                logger.error(f"FFmpeg合并失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"视频合并异常: {e}")
            return False
    
    def _format_time_for_ffmpeg(self, seconds: float) -> str:
        """将秒数转换为FFmpeg时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def process_segments(self, 
                        segments: List[Dict[str, Any]], 
                        video_path: str,
                        output_dir: str,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        完整的片段语义处理流程，支持时间戳子文件夹
        
        Args:
            segments: 原始片段列表
            video_path: 原始视频路径
            output_dir: 输出目录
            progress_callback: 进度回调
            
        Returns:
            处理结果
        """
        start_time = datetime.now()
        
        if progress_callback:
            progress_callback(10, "开始语义相似性分析...")
        
        # 1. 分析语义相似性
        analyzed_segments = self.analyze_segments_similarity(segments, progress_callback)
        
        if progress_callback:
            progress_callback(50, "开始合并相似片段...")
        
        # 2. 合并相似片段 (现在会自动创建时间戳子目录)
        merged_segments = self.merge_similar_segments(analyzed_segments, video_path, output_dir)
        
        if progress_callback:
            progress_callback(90, "生成处理报告...")
        
        # 3. 生成报告 (保存到主目录)
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # 清理片段数据中的numpy数组，准备JSON序列化
        cleaned_segments = []
        for segment in merged_segments:
            cleaned_segment = self._clean_for_json_serialization(segment)
            cleaned_segments.append(cleaned_segment)
        
        # 找到最新的合并会话目录
        latest_session = None
        if merged_segments:
            latest_session = merged_segments[0].get('merge_session')
        
        report = {
            'timestamp': end_time.isoformat(),
            'processing_time': processing_time,
            'original_segments': len(segments),
            'merged_segments': len(merged_segments),
            'compression_ratio': len(segments) / max(1, len(merged_segments)),
            'similarity_threshold': self.similarity_threshold,
            'max_merge_duration': self.max_merge_duration,
            'merge_session': latest_session,
            'segments': cleaned_segments
        }
        
        # 保存总报告到主目录
        timestamp_str = start_time.strftime("%Y%m%d_%H%M%S")
        report_path = Path(output_dir) / f"semantic_merge_report_{timestamp_str}.json"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"📄 报告已保存: {report_path}")
        except Exception as e:
            logger.warning(f"保存报告失败，但处理继续: {e}")
            # 即使保存报告失败，也不要影响主流程
        
        if progress_callback:
            progress_callback(100, f"语义合并完成! {len(segments)} -> {len(merged_segments)} 个片段")
        
        logger.info(f"🎉 语义片段合并完成!")
        logger.info(f"📊 原始片段: {len(segments)}")
        logger.info(f"📊 合并后片段: {len(merged_segments)}")
        logger.info(f"📊 压缩比: {report['compression_ratio']:.2f}x")
        logger.info(f"⏱️  处理时间: {processing_time:.1f}秒")
        logger.info(f"📄 报告已保存: {report_path}")
        
        return report
    
    def merge_segments(self, 
                      segments: List[Dict[str, Any]], 
                      video_name: str,
                      output_dir: str,
                      progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """
        语义合并片段的简化接口（用于CLI调用）
        
        Args:
            segments: 原始片段列表
            video_name: 视频名称
            output_dir: 输出目录
            progress_callback: 进度回调函数
            
        Returns:
            合并结果
        """
        try:
            if progress_callback:
                progress_callback(5, "初始化语义合并...")
            
            # 构造视频路径（从第一个片段推断）
            if not segments:
                if progress_callback:
                    progress_callback(0, "错误: 没有提供片段")
                return {"success": False, "error": "No segments provided"}
            
            if progress_callback:
                progress_callback(10, "查找原始视频文件...")
            
            # 从片段信息推断原始视频路径
            first_segment = segments[0]
            video_path = first_segment.get('video_path', '')
            
            if not video_path:
                # 尝试从file_path推断
                file_path = first_segment.get('file_path', '')
                if file_path:
                    # 尝试多个可能的路径
                    possible_paths = [
                        f"../🍭Origin/{video_name}.mp4",  # 相对于video_to_slice目录
                        f"🍭Origin/{video_name}.mp4",     # 相对于项目根目录
                        f"data/input/{video_name}.mp4",   # 传统路径
                        f"../🍭Origin/{video_name}.mov",  # 其他格式
                        f"🍭Origin/{video_name}.mov",
                        f"../🍭Origin/{video_name}.avi",
                        f"🍭Origin/{video_name}.avi"
                    ]
                    
                    for test_path in possible_paths:
                            if os.path.exists(test_path):
                                video_path = test_path
                                break
            
            if not video_path or not os.path.exists(video_path):
                if progress_callback:
                    progress_callback(0, f"错误: 找不到视频文件 {video_name}")
                logger.error(f"找不到原始视频文件: {video_name}")
                return {
                    "success": False, 
                    "error": f"Cannot find original video file for {video_name}"
                }
            
            if progress_callback:
                progress_callback(15, f"找到视频: {Path(video_path).name}")
            
            logger.info(f"开始处理视频: {video_path}")
            logger.info(f"片段数量: {len(segments)}")
            
            # 执行完整的语义处理
            result = self.process_segments(segments, video_path, output_dir, progress_callback)
            
            success = result.get('merged_segments', 0) > 0
            
            return {
                "success": success,
                "compression_ratio": result.get('compression_ratio', 1.0),
                "original_segments": result.get('original_segments', 0),
                "merged_segments": result.get('merged_segments', 0),
                "processing_time": result.get('processing_time', 0),
                "segments": result.get('segments', [])
            }
            
        except Exception as e:
            logger.error(f"语义合并失败: {e}")
            if progress_callback:
                progress_callback(0, f"错误: {str(e)[:30]}...")
            return {
                "success": False,
                "error": str(e)
            }

    def _clean_for_json_serialization(self, obj):
        """
        递归清理对象以准备JSON序列化，移除所有numpy数组和不可序列化的对象
        
        Args:
            obj: 要清理的对象
            
        Returns:
            清理后的可序列化对象
        """
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


if __name__ == "__main__":
    pass 