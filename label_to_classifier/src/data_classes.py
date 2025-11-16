#!/usr/bin/env python3
"""
📊 数据类定义
提取并统一管理所有数据结构，避免文件间的循环依赖
"""

from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class EnhancedClusterInfo:
    """增强聚类信息数据结构"""
    cluster_id: str           # 聚类ID
    cluster_name: str         # 聚类名称
    main_category: str        # 主分类
    sub_category: str         # 子分类
    slice_count: int         # 切片数量
    total_duration: float    # 总时长
    avg_confidence: float    # 平均置信度
    avg_secondary_confidence: float  # 平均二级置信度
    representative_tags: List[str]  # 代表性标签
    folder_path: str         # 文件夹路径
    source_files: List[str]  # 源文件列表
    ai_reasoning: str        # AI分析推理

@dataclass
class EnhancedClusterResult:
    """增强聚类结果"""
    main_modules: Dict[str, List[EnhancedClusterInfo]]  # 主模块及其子聚类
    cluster_mapping: Dict[str, str]  # 切片到聚类的映射
    unclustered_slices: List[Dict]   # 未聚类的切片
    unclassified_slices: List[Dict]  # 未分类的切片
    metadata: Dict                   # 聚类元数据
    processing_stats: Dict           # 处理统计
    ai_analysis_stats: Dict          # AI分析统计 