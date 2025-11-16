"""
slice_to_label 工具包

基于双层识别机制的视频片段标签分析工具
专门针对已有视频切片进行精准的语义标签分析

核心功能：
- 视觉双层识别机制
- DeepSeek片段级语音分析  
- 多模态标签提取
- 批量处理支持
"""

__version__ = "1.0.0"
__author__ = "AI Video Analysis Team"
__description__ = "视频片段智能标签分析工具"

# 导出主要类
from ..src.ai_analyzers import DualStageAnalyzer, BatchSliceAnalyzer

__all__ = [
    "DualStageAnalyzer",
    "BatchSliceAnalyzer"
] 