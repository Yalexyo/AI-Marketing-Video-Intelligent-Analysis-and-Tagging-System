#!/usr/bin/env python3
"""
📄 JSON文件处理器
专门处理🎬Slice目录下的切片JSON文件，添加main_tag字段
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class SliceJsonProcessor:
    """切片JSON文件处理器"""
    
    def __init__(self, slice_base_dir: str = "../🎬Slice"):
        """初始化JSON处理器"""
        self.slice_base_dir = Path(slice_base_dir)
        if not self.slice_base_dir.exists():
            raise ValueError(f"切片目录不存在: {self.slice_base_dir}")
        
        logger.info(f"✅ JSON处理器初始化完成，切片目录: {self.slice_base_dir}")
    
    def get_all_video_directories(self) -> List[str]:
        """获取所有视频目录名称"""
        video_dirs = []
        
        for item in self.slice_base_dir.iterdir():
            # 检查是否为目录且包含slices子目录（排除.DS_Store等系统文件）
            if (item.is_dir() and 
                item.name not in [".", "..", "🎬Slice"] and 
                not item.name.startswith(".") and
                (item / "slices").exists()):
                video_dirs.append(item.name)
        
        video_dirs.sort()
        logger.info(f"📁 找到 {len(video_dirs)} 个视频目录: {video_dirs}")
        return video_dirs
    
    def get_slice_json_files(self, video_name: str) -> List[Path]:
        """获取指定视频的所有切片JSON文件"""
        video_dir = self.slice_base_dir / video_name / "slices"
        
        if not video_dir.exists():
            logger.warning(f"⚠️ 视频切片目录不存在: {video_dir}")
            return []
        
        json_files = []
        for file in video_dir.iterdir():
            if file.is_file() and file.name.endswith("_analysis.json"):
                json_files.append(file)
        
        json_files.sort()
        logger.info(f"📄 {video_name} 找到 {len(json_files)} 个JSON文件")
        return json_files
    
    def read_json_file(self, json_file_path: Path) -> Optional[Dict[str, Any]]:
        """读取JSON文件内容"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"❌ 读取JSON文件失败 {json_file_path}: {e}")
            return None
    
    def write_json_file(self, json_file_path: Path, data: Dict[str, Any]) -> bool:
        """写入JSON文件"""
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"❌ 写入JSON文件失败 {json_file_path}: {e}")
            return False
    
    def extract_labels_for_classification(self, json_data: Dict[str, Any]) -> str:
        """从JSON数据中提取用于分类的Labels内容"""
        # 提取关键字段组成分析文本
        labels_parts = []
        
        # 主要字段
        object_field = json_data.get("object", "")
        scene_field = json_data.get("scene", "")
        emotion_field = json_data.get("emotion", "")
        brand_elements = json_data.get("brand_elements", "")
        
        if object_field and object_field != "无":
            labels_parts.append(f"对象: {object_field}")
        
        if scene_field and scene_field != "无":
            labels_parts.append(f"场景: {scene_field}")
        
        if emotion_field and emotion_field != "无":
            labels_parts.append(f"情绪: {emotion_field}")
        
        if brand_elements and brand_elements != "无":
            labels_parts.append(f"品牌元素: {brand_elements}")
        
        # 拼接成完整的labels文本
        labels_text = " | ".join(labels_parts)
        
        if not labels_text.strip():
            labels_text = f"对象: {object_field}, 场景: {scene_field}, 情绪: {emotion_field}"
        
        return labels_text
    
    def update_json_with_main_tag(self, json_file_path: Path, main_tag: str, confidence: float, analysis: Dict[str, Any]) -> bool:
        """更新JSON文件，添加main_tag字段"""
        try:
            # 读取原始数据
            data = self.read_json_file(json_file_path)
            if data is None:
                return False
            
            # 添加main_tag相关字段
            data["main_tag"] = main_tag
            data["main_tag_confidence"] = confidence
            data["main_tag_reasoning"] = analysis.get("reasoning", "")
            data["main_tag_keywords"] = analysis.get("matched_keywords", [])
            data["main_tag_processed_at"] = self._get_timestamp()
            
            # 写回文件
            success = self.write_json_file(json_file_path, data)
            
            if success:
                logger.info(f"✅ 更新成功: {json_file_path.name} -> {main_tag}")
            else:
                logger.error(f"❌ 更新失败: {json_file_path.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 更新JSON文件异常 {json_file_path}: {e}")
            return False
    
    def check_if_already_processed(self, json_data: Dict[str, Any]) -> bool:
        """检查JSON文件是否已经处理过"""
        return "main_tag" in json_data and json_data.get("main_tag", "").strip() != ""
    
    def get_processing_statistics(self, video_name: str) -> Dict[str, int]:
        """获取指定视频的处理统计信息"""
        json_files = self.get_slice_json_files(video_name)
        
        stats = {
            "total_files": len(json_files),
            "already_processed": 0,
            "needs_processing": 0,
            "invalid_files": 0
        }
        
        for json_file in json_files:
            data = self.read_json_file(json_file)
            if data is None:
                stats["invalid_files"] += 1
            elif self.check_if_already_processed(data):
                stats["already_processed"] += 1
            else:
                stats["needs_processing"] += 1
        
        return stats
    
    def get_all_processing_statistics(self) -> Dict[str, Dict[str, int]]:
        """获取所有视频的处理统计信息"""
        video_dirs = self.get_all_video_directories()
        all_stats = {}
        
        total_summary = {
            "total_files": 0,
            "already_processed": 0,
            "needs_processing": 0,
            "invalid_files": 0
        }
        
        for video_name in video_dirs:
            stats = self.get_processing_statistics(video_name)
            all_stats[video_name] = stats
            
            # 累计到总计
            for key in total_summary:
                total_summary[key] += stats[key]
        
        all_stats["TOTAL"] = total_summary
        return all_stats
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def backup_json_file(self, json_file_path: Path) -> bool:
        """备份JSON文件"""
        try:
            backup_path = json_file_path.with_suffix(".json.backup")
            
            # 如果备份已存在，跳过
            if backup_path.exists():
                return True
            
            import shutil
            shutil.copy2(json_file_path, backup_path)
            logger.debug(f"🔄 备份文件: {backup_path.name}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ 备份文件失败 {json_file_path}: {e}")
            return False 