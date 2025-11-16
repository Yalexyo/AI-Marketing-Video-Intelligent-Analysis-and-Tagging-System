"""
飞书数据池管理系统

基于飞书多维表格的AI视频分析数据管理系统

主要功能：
- 视频基础信息管理
- 切片标签数据同步
- 云文档素材上传
- 数据池统一管理
"""

from .optimized_data_pool import OptimizedDataPoolManager, VideoBaseRecord, SliceTagRecord

__version__ = "2.0.0"
__author__ = "AI Video Master"

# 导出核心类
__all__ = [
    "OptimizedDataPoolManager",  # 优化数据池管理器
    "VideoBaseRecord",           # 视频基础记录
    "SliceTagRecord",           # 切片标签记录
]

# 快速使用示例
def quick_start_example():
    """快速开始示例"""
    print("""
    🚀 飞书数据池管理系统 - 快速开始
    
    # 1. 初始化数据池管理器
    from feishu_pool import OptimizedDataPoolManager
    
    manager = OptimizedDataPoolManager()
    
    # 2. 创建数据池
    manager.create_optimized_data_pool()
    
    # 3. 添加视频记录
    video_data = {
        "video_id": "video_1",
        "video_name": "测试视频",
        "srt_content": "字幕内容...",
        "file_size_mb": 100.5,
        "duration_seconds": 180,
        "resolution": "1920x1080"
    }
    record_id = manager.add_video_base_record(video_data)
    
    # 4. 添加切片记录（带文件上传）
    slice_data = {
        "slice_id": "slice_001",
        "video_id": "video_1",
        "start_time": 0.0,
        "end_time": 10.0,
        "duration_seconds": 10.0,
        "sub_tags": ["测试标签"],
        "subtitle_text": "切片字幕...",
        "confidence_score": 0.9
    }
    slice_record_id = manager.add_slice_tag_record(slice_data, "/path/to/slice.mp4")
    """)

if __name__ == "__main__":
    quick_start_example() 