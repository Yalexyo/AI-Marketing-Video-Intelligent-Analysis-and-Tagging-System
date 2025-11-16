#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能关键帧提取器
根据视频时长、内容变化和场景切换智能提取关键帧
"""

import cv2
import numpy as np
import logging
from typing import List, Tuple, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class SmartFrameExtractor:
    """
    智能关键帧提取器
    根据视频特征自适应提取最具代表性的关键帧
    """
    
    def __init__(self):
        """初始化提取器"""
        # 时长分级策略
        self.duration_strategies = {
            "ultra_short": {"max_duration": 2.0, "min_frames": 1, "max_frames": 2},
            "short": {"max_duration": 5.0, "min_frames": 2, "max_frames": 3}, 
            "medium": {"max_duration": 15.0, "min_frames": 3, "max_frames": 5},
            "long": {"max_duration": 60.0, "min_frames": 5, "max_frames": 8},
            "very_long": {"max_duration": float('inf'), "min_frames": 8, "max_frames": 12}
        }
        
        # 内容变化检测阈值
        self.content_change_threshold = 0.3
        self.histogram_bins = 32
        
    def extract_key_frames(self, video_path: str) -> List[Dict[str, Any]]:
        """
        智能提取关键帧
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            关键帧列表，每个包含frame数据和元数据
        """
        try:
            cap = cv2.VideoCapture(video_path)
            
            # 获取视频基本信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"🎬 视频信息: {duration:.1f}秒, {fps:.1f}FPS, {total_frames}帧")
            
            # 根据时长确定提取策略
            strategy = self._get_duration_strategy(duration)
            logger.info(f"📋 提取策略: {strategy['strategy_name']} (目标帧数: {strategy['min_frames']}-{strategy['max_frames']})")
            
            # 执行智能提取
            key_frames = self._smart_extract(cap, fps, total_frames, duration, strategy)
            
            cap.release()
            
            logger.info(f"🖼️ 智能提取完成: {len(key_frames)} 个关键帧")
            return key_frames
            
        except Exception as e:
            logger.error(f"❌ 智能帧提取失败: {str(e)}")
            return []
    
    def _get_duration_strategy(self, duration: float) -> Dict[str, Any]:
        """根据视频时长选择提取策略"""
        for strategy_name, config in self.duration_strategies.items():
            if duration <= config["max_duration"]:
                return {
                    "strategy_name": strategy_name,
                    **config
                }
        
        # 默认返回最长时长策略
        return {
            "strategy_name": "very_long",
            **self.duration_strategies["very_long"]
        }
    
    def _smart_extract(self, cap, fps: float, total_frames: int, duration: float, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """智能提取关键帧"""
        key_frames = []
        
        # 方法1: 时间均匀分布 + 内容变化检测
        if duration <= 5.0:
            # 短视频：时间均匀分布
            key_frames = self._extract_time_distributed(cap, fps, total_frames, strategy)
        elif duration <= 15.0:
            # 中等视频：内容变化检测 + 时间分布
            key_frames = self._extract_content_aware(cap, fps, total_frames, strategy)
        else:
            # 长视频：混合策略
            key_frames = self._extract_hybrid_strategy(cap, fps, total_frames, strategy)
        
        return key_frames
    
    def _extract_time_distributed(self, cap, fps: float, total_frames: int, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """时间均匀分布提取"""
        key_frames = []
        target_count = min(strategy["max_frames"], max(strategy["min_frames"], total_frames // 10))
        
        if target_count == 1:
            # 只取中间帧
            frame_indices = [total_frames // 2]
        else:
            # 均匀分布
            step = total_frames // target_count
            frame_indices = [i * step for i in range(target_count)]
        
        for i, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                timestamp = frame_idx / fps
                key_frames.append({
                    "frame": frame,
                    "frame_index": frame_idx,
                    "timestamp": timestamp,
                    "extraction_method": "time_distributed",
                    "confidence": 0.9
                })
        
        return key_frames
    
    def _extract_content_aware(self, cap, fps: float, total_frames: int, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于内容变化的智能提取"""
        key_frames = []
        
        # 首先获取所有帧的直方图
        histograms = []
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        frame_step = max(1, total_frames // 50)  # 最多采样50个点进行内容分析
        
        for frame_idx in range(0, total_frames, frame_step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                hist = self._calculate_histogram(frame)
                histograms.append((frame_idx, hist))
        
        # 检测内容变化点
        change_points = self._detect_content_changes(histograms)
        
        # 在变化点附近提取关键帧
        selected_indices = self._select_representative_frames(change_points, total_frames, strategy)
        
        # 提取选定的帧
        for frame_idx in selected_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                timestamp = frame_idx / fps
                key_frames.append({
                    "frame": frame,
                    "frame_index": frame_idx,
                    "timestamp": timestamp,
                    "extraction_method": "content_aware",
                    "confidence": 0.85
                })
        
        return key_frames
    
    def _extract_hybrid_strategy(self, cap, fps: float, total_frames: int, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """混合策略：结合时间分布和内容变化"""
        key_frames = []
        
        # 50% 时间分布 + 50% 内容变化
        time_count = strategy["max_frames"] // 2
        content_count = strategy["max_frames"] - time_count
        
        # 时间分布帧
        time_strategy = {"min_frames": time_count, "max_frames": time_count}
        time_frames = self._extract_time_distributed(cap, fps, total_frames, time_strategy)
        
        # 内容变化帧
        content_strategy = {"min_frames": content_count, "max_frames": content_count}
        content_frames = self._extract_content_aware(cap, fps, total_frames, content_strategy)
        
        # 合并并去重
        all_frames = time_frames + content_frames
        unique_frames = self._deduplicate_frames(all_frames)
        
        return unique_frames[:strategy["max_frames"]]
    
    def _calculate_histogram(self, frame: np.ndarray) -> np.ndarray:
        """计算帧的颜色直方图"""
        # 转换为HSV色彩空间
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 计算3D直方图
        hist = cv2.calcHist([hsv], [0, 1, 2], None, 
                           [self.histogram_bins, self.histogram_bins, self.histogram_bins],
                           [0, 180, 0, 256, 0, 256])
        
        # 归一化
        hist = cv2.normalize(hist, hist).flatten()
        return hist
    
    def _detect_content_changes(self, histograms: List[Tuple[int, np.ndarray]]) -> List[int]:
        """检测内容变化点"""
        change_points = [histograms[0][0]]  # 总是包含第一帧
        
        for i in range(1, len(histograms)):
            prev_hist = histograms[i-1][1]
            curr_hist = histograms[i][1]
            
            # 计算直方图相关性
            correlation = cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_CORREL)
            
            # 如果相关性低于阈值，认为是内容变化点
            if correlation < (1 - self.content_change_threshold):
                change_points.append(histograms[i][0])
        
        return change_points
    
    def _select_representative_frames(self, change_points: List[int], total_frames: int, strategy: Dict[str, Any]) -> List[int]:
        """从变化点中选择代表性帧"""
        if len(change_points) <= strategy["max_frames"]:
            return change_points
        
        # 如果变化点太多，均匀选择
        step = len(change_points) // strategy["max_frames"]
        selected = [change_points[i * step] for i in range(strategy["max_frames"])]
        
        return selected
    
    def _deduplicate_frames(self, frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复帧"""
        seen_indices = set()
        unique_frames = []
        
        for frame_data in frames:
            frame_idx = frame_data["frame_index"]
            if frame_idx not in seen_indices:
                seen_indices.add(frame_idx)
                unique_frames.append(frame_data)
        
        # 按时间戳排序
        unique_frames.sort(key=lambda x: x["timestamp"])
        return unique_frames
    
    def get_extraction_summary(self, key_frames: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成提取摘要"""
        if not key_frames:
            return {"error": "无关键帧"}
        
        methods = {}
        for frame_data in key_frames:
            method = frame_data.get("extraction_method", "unknown")
            methods[method] = methods.get(method, 0) + 1
        
        total_duration = key_frames[-1]["timestamp"] if key_frames else 0
        
        return {
            "total_frames": len(key_frames),
            "extraction_methods": methods,
            "time_span": f"0.0-{total_duration:.1f}秒",
            "coverage": "完整覆盖" if len(key_frames) >= 3 else "部分覆盖",
            "avg_confidence": np.mean([f.get("confidence", 0.8) for f in key_frames])
        }

def extract_smart_frames(video_path: str) -> List[Dict[str, Any]]:
    """便捷函数：智能提取关键帧"""
    extractor = SmartFrameExtractor()
    return extractor.extract_key_frames(video_path)

if __name__ == "__main__":
    # 测试智能关键帧提取
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python smart_frame_extractor.py <video_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    if not Path(video_path).exists():
        print(f"❌ 视频文件不存在: {video_path}")
        sys.exit(1)
    
    print(f"🎯 开始智能关键帧提取: {video_path}")
    
    extractor = SmartFrameExtractor()
    key_frames = extractor.extract_key_frames(video_path)
    
    if key_frames:
        summary = extractor.get_extraction_summary(key_frames)
        print(f"\n📊 提取摘要:")
        print(f"   关键帧数量: {summary['total_frames']}")
        print(f"   时间跨度: {summary['time_span']}")
        print(f"   覆盖质量: {summary['coverage']}")
        print(f"   平均置信度: {summary['avg_confidence']:.2f}")
        print(f"   提取方法: {summary['extraction_methods']}")
        
        print(f"\n🖼️ 关键帧详情:")
        for i, frame_data in enumerate(key_frames, 1):
            print(f"   {i}. 时间戳: {frame_data['timestamp']:.1f}s, "
                  f"方法: {frame_data['extraction_method']}")
    else:
        print("❌ 未能提取关键帧") 