#!/usr/bin/env python3
"""
📁 统一切片文件管理器 - Unified Slice File Manager
合并json_processor和enhanced_clustering_manager中重复的文件操作功能
提供统一的文件访问接口，减少代码重复

设计原则:
- DRY: Don't Repeat Yourself - 消除重复代码
- 单一职责：专门负责文件操作
- 接口统一：为所有文件操作提供一致的接口
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SliceFileManager:
    """统一切片文件管理器 - 提供一站式文件操作服务"""
    
    def __init__(self, slice_base_dir: str = "../🎬Slice"):
        """
        初始化文件管理器
        
        Args:
            slice_base_dir: 切片基础目录路径
        """
        self.slice_base_dir = Path(slice_base_dir)
        if not self.slice_base_dir.exists():
            raise ValueError(f"切片目录不存在: {self.slice_base_dir}")
        
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.info(f"✅ 统一切片文件管理器初始化完成，目录: {self.slice_base_dir}")
    
    # ==================== 目录操作 ====================
    
    def get_all_video_directories(self) -> List[str]:
        """
        获取所有视频目录名称 - 支持灵活的文件夹结构
        
        Returns:
            List[str]: 视频目录名称列表，已排序
        """
        video_dirs = []
        
        for item in self.slice_base_dir.iterdir():
            # 检查是否为目录（排除.DS_Store等系统文件）
            if (item.is_dir() and 
                item.name not in [".", "..", "🎬Slice"] and 
                not item.name.startswith(".")):
                
                # 检查是否包含分析JSON文件（支持有slices子目录或直接在目录下）
                has_analysis_files = False
                
                # 方法1: 检查slices子目录
                slices_dir = item / "slices"
                if slices_dir.exists():
                    if any(slices_dir.glob("*_analysis.json")):
                        has_analysis_files = True
                
                # 方法2: 检查直接在目录下
                if not has_analysis_files:
                    if any(item.glob("*_analysis.json")):
                        has_analysis_files = True
                
                if has_analysis_files:
                    video_dirs.append(item.name)
        
        video_dirs.sort()
        self.logger.info(f"📁 找到 {len(video_dirs)} 个视频目录: {video_dirs}")
        return video_dirs
    
    def get_video_slice_directory(self, video_name: str) -> Optional[Path]:
        """
        获取指定视频的切片目录路径
        
        Args:
            video_name: 视频名称
            
        Returns:
            Optional[Path]: 切片目录路径，不存在则返回None
        """
        slice_dir = self.slice_base_dir / video_name / "slices"
        
        if not slice_dir.exists():
            self.logger.warning(f"⚠️ 视频切片目录不存在: {slice_dir}")
            return None
        
        return slice_dir
    
    # ==================== JSON文件操作 ====================
    
    def get_slice_json_files(self, video_name: str) -> List[Path]:
        """
        获取指定视频的所有切片JSON文件 - 支持灵活的文件夹结构
        
        Args:
            video_name: 视频名称
            
        Returns:
            List[Path]: JSON文件路径列表，已排序
        """
        video_dir = self.slice_base_dir / video_name
        
        if not video_dir.exists():
            self.logger.warning(f"⚠️ 视频目录不存在: {video_dir}")
            return []
        
        json_files = []
        
        # 方法1: 检查slices子目录
        slices_dir = video_dir / "slices"
        if slices_dir.exists():
            for file in slices_dir.iterdir():
                if file.is_file() and file.name.endswith("_analysis.json"):
                    json_files.append(file)
        
        # 方法2: 检查直接在视频目录下
        if not json_files:  # 如果slices目录没有找到文件，检查直接目录
            for file in video_dir.iterdir():
                if file.is_file() and file.name.endswith("_analysis.json"):
                    json_files.append(file)
        
        json_files.sort()
        self.logger.debug(f"📄 {video_name} 找到 {len(json_files)} 个JSON文件")
        return json_files
    
    def get_all_slice_json_files(self) -> List[Path]:
        """
        获取所有视频的切片JSON文件
        
        Returns:
            List[Path]: 所有JSON文件路径列表
        """
        all_json_files = []
        
        for video_name in self.get_all_video_directories():
            json_files = self.get_slice_json_files(video_name)
            all_json_files.extend(json_files)
        
        self.logger.info(f"📄 总计找到 {len(all_json_files)} 个JSON文件")
        return all_json_files
    
    def read_json_file(self, json_file_path: Path) -> Optional[Dict[str, Any]]:
        """
        读取JSON文件内容
        
        Args:
            json_file_path: JSON文件路径
            
        Returns:
            Optional[Dict[str, Any]]: JSON数据，读取失败返回None
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            self.logger.error(f"❌ 读取JSON文件失败 {json_file_path}: {e}")
            return None
    
    def write_json_file(self, json_file_path: Path, data: Dict[str, Any]) -> bool:
        """
        写入JSON文件
        
        Args:
            json_file_path: JSON文件路径
            data: 要写入的数据
            
        Returns:
            bool: 写入是否成功
        """
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"❌ 写入JSON文件失败 {json_file_path}: {e}")
            return False
    
    # ==================== 数据提取与处理 ====================
    
    def extract_labels_for_classification(self, json_data: Dict[str, Any]) -> str:
        """
        从JSON数据中提取用于分类的Labels内容
        
        Args:
            json_data: JSON数据字典
            
        Returns:
            str: 格式化的labels文本
        """
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
    
    def check_if_already_processed(self, json_data: Dict[str, Any]) -> bool:
        """
        检查JSON文件是否已经处理过（包含main_tag）
        
        Args:
            json_data: JSON数据字典
            
        Returns:
            bool: 是否已处理
        """
        return "main_tag" in json_data and json_data.get("main_tag", "").strip() != ""
    
    def estimate_slice_duration(self, json_file: Path) -> float:
        """
        估算切片时长
        
        Args:
            json_file: JSON文件路径
            
        Returns:
            float: 估算的时长（秒）
        """
        try:
            # 从文件名提取时长信息
            filename = json_file.stem
            
            # 查找类似 "_10.5s_" 的模式
            import re
            duration_match = re.search(r'_(\d+\.?\d*)s_', filename)
            if duration_match:
                return float(duration_match.group(1))
            
            # 默认估算：根据文件大小
            file_size = json_file.stat().st_size
            estimated_duration = max(3.0, min(30.0, file_size / 1000))  # 基于文件大小的简单估算
            
            return estimated_duration
            
        except Exception as e:
            self.logger.warning(f"⚠️ 估算切片时长失败 {json_file}: {e}")
            return 5.0  # 默认时长
    
    # ==================== 批量数据收集 ====================
    
    def _resolve_video_file_path(self, json_file: Path, json_data: Dict[str, Any]) -> str:
        """
        智能解析视频文件路径 - 处理♻️前缀和路径匹配问题
        
        Args:
            json_file: JSON文件路径
            json_data: JSON数据内容
            
        Returns:
            str: 实际的视频文件路径
        """
        try:
            # 方法1：优先使用JSON中记录的file_path
            if "file_path" in json_data:
                recorded_path = json_data["file_path"]
                if isinstance(recorded_path, str) and recorded_path:
                    # 解析路径，支持相对路径和绝对路径
                    if recorded_path.startswith("../"):
                        # 相对路径，基于当前工作目录解析
                        resolved_path = Path(recorded_path).resolve()
                    else:
                        # 绝对路径或当前目录路径
                        resolved_path = Path(recorded_path)
                    
                    # 检查文件是否存在
                    if resolved_path.exists():
                        return str(resolved_path)
                    else:
                        self.logger.debug(f"JSON记录路径不存在: {resolved_path}")
            
            # 方法2：使用JSON中记录的file_name
            if "file_name" in json_data:
                recorded_name = json_data["file_name"]
                if isinstance(recorded_name, str) and recorded_name:
                    candidate_path = json_file.parent / recorded_name
                    if candidate_path.exists():
                        return str(candidate_path)
                    else:
                        self.logger.debug(f"JSON记录文件名不存在: {candidate_path}")
            
            # 方法3：智能匹配 - 尝试多种文件名模式
            base_name = json_file.stem.replace("_analysis", "")
            candidate_names = [
                f"{base_name}.mp4",           # 标准名称
                f"♻️{base_name}.mp4",         # 带♻️前缀
                f"❌{base_name}.mp4",         # 带❌前缀
            ]
            
            for candidate_name in candidate_names:
                candidate_path = json_file.parent / candidate_name
                if candidate_path.exists():
                    return str(candidate_path)
            
            # 方法4：模糊匹配 - 在同目录下搜索相似文件名
            video_extensions = [".mp4", ".mov", ".avi", ".mkv"]
            for file_path in json_file.parent.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                    # 移除特殊前缀进行比较
                    clean_name = file_path.stem.replace("♻️", "").replace("❌", "")
                    if clean_name == base_name:
                        return str(file_path)
            
            # 方法5：兜底方案 - 返回推测的路径（可能不存在）
            fallback_path = json_file.parent / f"{base_name}.mp4"
            self.logger.warning(f"⚠️ 无法找到匹配的视频文件，使用兜底路径: {fallback_path}")
            return str(fallback_path)
            
        except Exception as e:
            self.logger.error(f"❌ 解析视频文件路径异常 {json_file}: {e}")
            # 返回兜底路径
            return str(json_file.parent / f"{json_file.stem.replace('_analysis', '')}.mp4")

    def _should_filter_file(self, json_file: Path, json_data: Dict[str, Any]) -> bool:
        """
        判断文件是否需要过滤（例如，带❌前缀，或quality_status为failed）
        
        Args:
            json_file: JSON文件路径
            json_data: JSON数据内容
            
        Returns:
            bool: 是否需要过滤
        """
        # 🎯 用户反馈：多镜头视频也应该被分析，只过滤真正失败的文件
        # 只过滤❌前缀的文件（分析失败），♻️文件允许正常分析
        if json_file.stem.startswith("❌"):
            return True
        
        # 检查quality_status是否为failed
        if json_data.get("quality_status") == "failed":
            return True
        
        return False

    def _resolve_valid_video_file_path(self, json_file: Path, json_data: Dict[str, Any]) -> str:
        """
        智能解析视频文件路径 - 仅对有效文件使用
        
        Args:
            json_file: JSON文件路径
            json_data: JSON数据内容
            
        Returns:
            str: 实际的视频文件路径
        """
        try:
            # 方法1：优先使用JSON中记录的file_path
            if "file_path" in json_data:
                recorded_path = json_data["file_path"]
                if isinstance(recorded_path, str) and recorded_path:
                    # 解析路径，支持相对路径和绝对路径
                    if recorded_path.startswith("../"):
                        # 相对路径，基于当前工作目录解析
                        resolved_path = Path(recorded_path).resolve()
                    else:
                        # 绝对路径或当前目录路径
                        resolved_path = Path(recorded_path)
                    
                    # 检查文件是否存在
                    if resolved_path.exists():
                        return str(resolved_path)
                    else:
                        self.logger.debug(f"JSON记录路径不存在: {resolved_path}")
            
            # 方法2：使用JSON中记录的file_name
            if "file_name" in json_data:
                recorded_name = json_data["file_name"]
                if isinstance(recorded_name, str) and recorded_name:
                    candidate_path = json_file.parent / recorded_name
                    if candidate_path.exists():
                        return str(candidate_path)
                    else:
                        self.logger.debug(f"JSON记录文件名不存在: {candidate_path}")
            
            # 方法3：智能匹配 - 尝试多种文件名模式
            base_name = json_file.stem.replace("_analysis", "")
            candidate_names = [
                f"{base_name}.mp4",           # 标准名称
                f"♻️{base_name}.mp4",         # 带♻️前缀
                f"❌{base_name}.mp4",         # 带❌前缀
            ]
            
            for candidate_name in candidate_names:
                candidate_path = json_file.parent / candidate_name
                if candidate_path.exists():
                    return str(candidate_path)
            
            # 方法4：模糊匹配 - 在同目录下搜索相似文件名
            video_extensions = [".mp4", ".mov", ".avi", ".mkv"]
            for file_path in json_file.parent.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                    # 移除特殊前缀进行比较
                    clean_name = file_path.stem.replace("♻️", "").replace("❌", "")
                    if clean_name == base_name:
                        return str(file_path)
            
            # 方法5：兜底方案 - 返回推测的路径（可能不存在）
            fallback_path = json_file.parent / f"{base_name}.mp4"
            self.logger.warning(f"⚠️ 无法找到匹配的视频文件，使用兜底路径: {fallback_path}")
            return str(fallback_path)
            
        except Exception as e:
            self.logger.error(f"❌ 解析视频文件路径异常 {json_file}: {e}")
            # 返回兜底路径
            return str(json_file.parent / f"{json_file.stem.replace('_analysis', '')}.mp4")

    def collect_all_slice_data(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        收集所有切片数据 - 支持灵活的文件夹结构，并过滤无效文件
        
        Returns:
            Tuple[List[Dict], List[Dict]]: (已分类数据, 未分类数据)
        """
        try:
            classified_data = []
            unclassified_data = []
            
            processing_stats = {
                "total_files": 0,
                "classified_files": 0,
                "unclassified_files": 0,
                "invalid_files": 0,
                "filtered_files": 0  # 🆕 新增：过滤的文件数量
            }
            
            # 收集所有视频目录的JSON文件
            for video_name in self.get_all_video_directories():
                self.logger.info(f"📁 处理视频目录: {video_name}")
                
                # 获取该视频的所有JSON文件
                json_files = self.get_slice_json_files(video_name)
                processing_stats["total_files"] += len(json_files)
                
                for json_file in json_files:
                    try:
                        # 读取JSON数据
                        json_data = self.read_json_file(json_file)
                        if not json_data:
                            processing_stats["invalid_files"] += 1
                            continue
                        
                        # 🚨 新增：质量过滤逻辑
                        if self._should_filter_file(json_file, json_data):
                            processing_stats["filtered_files"] += 1
                            self.logger.debug(f"🚫 过滤文件: {json_file.name} (质量问题)")
                            continue
                        
                        # 估算时长
                        duration = json_data.get("duration", 0)
                        if duration == 0:
                            duration = self.estimate_slice_duration(json_file)
                        
                        # 提取labels内容
                        labels_content = self.extract_labels_for_classification(json_data)
                        
                        # 🔧 修复：仅对有效文件使用智能路径解析
                        resolved_file_path = self._resolve_valid_video_file_path(json_file, json_data)
                        
                        # 构建切片数据
                        slice_data = {
                            "file_path": resolved_file_path,
                            "analysis_file": str(json_file),
                            "duration": duration,
                            "labels": labels_content,
                            "video_name": video_name,
                            "slice_name": json_file.stem.replace("_analysis", ""),
                            "raw_data": json_data  # 保存原始数据
                        }
                        
                        # 检查是否已分类
                        if self.check_if_already_processed(json_data):
                            processing_stats["classified_files"] += 1
                            
                            # 提取主标签和相关信息
                            main_tag = json_data.get("main_tag", "")
                            confidence = json_data.get("main_tag_confidence", 0)
                            
                            slice_data.update({
                                "main_tag": main_tag,
                                "confidence": confidence
                            })
                            
                            classified_data.append(slice_data)
                        else:
                            processing_stats["unclassified_files"] += 1
                            
                            # 分析未分类原因
                            unclassified_reason = self._analyze_unclassified_reason(json_data, labels_content)
                            slice_data.update({
                                "unclassified_reason": unclassified_reason
                            })
                            
                            unclassified_data.append(slice_data)
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ 处理文件 {json_file.name} 时出错: {e}")
                        processing_stats["invalid_files"] += 1
                        continue
            
            self.logger.info(f"📊 数据收集完成: {len(classified_data)} 个已分类切片, {len(unclassified_data)} 个未分类切片")
            self.logger.info(f"🚫 已过滤 {processing_stats['filtered_files']} 个质量问题文件")
            self.logger.info(f"📈 处理统计: {processing_stats}")
            
            return classified_data, unclassified_data
        except Exception as e:
            self.logger.error(f"❌ 收集所有切片数据时发生错误: {e}")
            return [], []
    
    def _analyze_unclassified_reason(self, json_data: Dict[str, Any], labels_content: str) -> str:
        """
        分析未分类的原因
        
        Args:
            json_data: JSON数据
            labels_content: labels内容
            
        Returns:
            str: 未分类原因描述
        """
        if not labels_content or labels_content.strip() == "":
            return "视觉分析数据为空或无效"
        
        if json_data.get("main_tag_status") == "unclassified":
            return json_data.get("unclassified_reason", "AI分析置信度不足")
        
        return "未进行主标签分类"
    
    # ==================== 统计信息 ====================
    
    def get_processing_statistics(self, video_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取处理统计信息
        
        Args:
            video_name: 指定视频名称，None表示统计所有视频
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        if video_name:
            # 单个视频的统计
            json_files = self.get_slice_json_files(video_name)
            
            stats = {
                "video_name": video_name,
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
        else:
            # 所有视频的统计
            video_dirs = self.get_all_video_directories()
            all_stats = {}
            
            total_summary = {
                "total_videos": len(video_dirs),
                "total_files": 0,
                "already_processed": 0,
                "needs_processing": 0,
                "invalid_files": 0
            }
            
            for video_name in video_dirs:
                stats = self.get_processing_statistics(video_name)
                all_stats[video_name] = stats
                
                # 累计到总计
                for key in ["total_files", "already_processed", "needs_processing", "invalid_files"]:
                    total_summary[key] += stats[key]
            
            all_stats["TOTAL"] = total_summary
            return all_stats
    
    # ==================== 工具方法 ====================
    
    def get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def backup_json_file(self, json_file_path: Path) -> bool:
        """
        备份JSON文件
        
        Args:
            json_file_path: 要备份的JSON文件路径
            
        Returns:
            bool: 备份是否成功
        """
        try:
            backup_path = json_file_path.with_suffix(".json.backup")
            
            # 如果备份已存在，跳过
            if backup_path.exists():
                return True
            
            import shutil
            shutil.copy2(json_file_path, backup_path)
            self.logger.debug(f"🔄 备份文件: {backup_path.name}")
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️ 备份文件失败 {json_file_path}: {e}")
            return False
    
    def update_json_with_main_tag(self, json_file_path: Path, main_tag: str, 
                                 confidence: float, analysis: Dict[str, Any]) -> bool:
        """
        更新JSON文件，添加main_tag字段
        
        Args:
            json_file_path: JSON文件路径
            main_tag: 主标签
            confidence: 置信度
            analysis: 分析结果
            
        Returns:
            bool: 更新是否成功
        """
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
            data["main_tag_processed_at"] = self.get_timestamp()
            
            # 写回文件
            success = self.write_json_file(json_file_path, data)
            
            if success:
                self.logger.info(f"✅ 更新成功: {json_file_path.name} -> {main_tag}")
            else:
                self.logger.error(f"❌ 更新失败: {json_file_path.name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 更新JSON文件异常 {json_file_path}: {e}")
            return False 