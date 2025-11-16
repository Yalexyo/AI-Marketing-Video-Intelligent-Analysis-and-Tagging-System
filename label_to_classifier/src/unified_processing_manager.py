#!/usr/bin/env python3
"""
🚀 统一处理管理器
整合主标签分类和二级聚类功能，实现内存中的流式数据处理
架构优化版：避免中间文件读写，提升性能
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

from .slice_file_manager import SliceFileManager
from .primary_ai_classifier import PrimaryAIClassifier
from .secondary_ai_classifier import SecondaryAIClassifier
from .tag_system_manager import TagSystemManager
from .data_classes import EnhancedClusterInfo, EnhancedClusterResult
from .unified_config_manager import get_unified_config_manager

# 设置日志
logger = logging.getLogger(__name__)


class UnifiedProcessingManager:
    """🚀 统一处理管理器 - 内存中流式处理，避免中间文件读写"""
    
    def __init__(self, slice_base_dir: Optional[str] = None):
        """初始化统一处理管理器"""
        # 🔧 加载统一配置
        self.config_manager = get_unified_config_manager()
        self.config = self.config_manager.get_config()
        
        # 使用配置设置目录
        self.slice_base_dir = Path(slice_base_dir or self.config.processing.slice_base_dir)
        
        # 🔧 初始化核心组件
        try:
            self.file_manager = SliceFileManager(str(self.slice_base_dir))
            self.primary_classifier = PrimaryAIClassifier()
            self.secondary_classifier = SecondaryAIClassifier()
            self.tag_manager = TagSystemManager()
            
            logger.info("✅ 统一处理管理器组件初始化成功")
            logger.info(f"📁 使用切片目录: {self.slice_base_dir}")
            logger.info(f"⚙️ 置信度阈值: {self.config.processing.min_confidence_threshold}")
        except Exception as e:
            logger.error(f"❌ 组件初始化失败: {e}")
            raise
        
        # 4大主模块映射
        self.MAIN_MODULES = {
            "🪝 钩子": {
                "description": "宝宝哭闹、家长焦虑、喂养困扰、专家建议、问题解决",
                "folder_name": "🪝_钩子"
            },
            "🍼 产品介绍_蕴淳": {
                "description": "启赋蕴淳产品展示、HMO母乳低聚糖、OPN活性蛋白、营养科学、惠氏背景",
                "folder_name": "🍼_产品介绍_蕴淳"
            },
            "🍼 产品介绍_水奶": {
                "description": "启赋水奶展示、便携装特性、A2奶源、即饮方便、新鲜品质",
                "folder_name": "🍼_产品介绍_水奶"
            },
            "🍼 产品介绍_蓝钻": {
                "description": "启赋蓝钻高端系列、升级配方、顶级品质、旗舰产品",
                "folder_name": "🍼_产品介绍_蓝钻"
            },
            "🌟 使用效果": {
                "description": "宝宝活泼、效果展示、满意反馈、健康发育、快乐玩耍",
                "folder_name": "🌟_使用效果"
            },
            "🎁 促销机制": {
                "description": "亲子互动、温馨场景、家庭和谐、情感连接、推荐引导",
                "folder_name": "🎁_促销机制"
            }
        }
        
        # 处理统计
        self.processing_stats = {
            "total_files": 0,
            "classified_by_primary": 0,
            "classified_by_secondary": 0,
            "unclassified": 0,
            "failed": 0,
            "skipped": 0
        }
        
        # AI分析统计
        self.ai_analysis_stats = {
            "primary_ai_calls": 0,
            "secondary_ai_calls": 0,
            "successful_primary_classifications": 0,
            "successful_secondary_classifications": 0,
            "failed_classifications": 0,
            "low_confidence_classifications": 0
        }
        
        logger.info("✅ 统一处理管理器初始化完成 - 内存流式处理模式")
    
    def perform_unified_classification_and_clustering(self, 
                                                     force_reprocess: bool = False,
                                                     output_base_dir: Optional[Path] = None) -> EnhancedClusterResult:
        """
        🚀 统一智能分类和聚类 - 内存中流式处理
        第一层：主标签AI分类 + 第二层：智能子类别聚类
        """
        try:
            if not output_base_dir:
                base_output_dir = Path(self.config.processing.output_base_dir)
                output_base_dir = base_output_dir / f"统一AI分类v4_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            output_base_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"🚀 开始统一智能分类处理，输出目录: {output_base_dir}")
            
            # 第一步：收集所有切片数据
            all_slice_data = self._collect_all_slice_data_for_processing()
            
            if not all_slice_data:
                logger.warning("⚠️ 没有找到任何切片数据")
                return EnhancedClusterResult({}, {}, [], [], {}, {}, {})
            
            logger.info(f"📊 共收集到 {len(all_slice_data)} 个切片文件")
            
            # 第二步：🤖 主标签AI分类（内存中处理）
            classified_data, unclassified_data = self._perform_primary_classification_in_memory(
                all_slice_data, force_reprocess
            )
            
            logger.info(f"📊 主标签分类完成: 分类 {len(classified_data)} 个，未分类 {len(unclassified_data)} 个")
            
            # 第三步：处理未分类数据
            if unclassified_data:
                self._create_unclassified_folder(unclassified_data, output_base_dir)
            
            # 第四步：按主标签分组
            main_tag_groups = self._group_by_main_tag(classified_data)
            
            # 第五步：🤖 二级AI智能聚类（内存中处理）
            main_modules = {}
            cluster_mapping = {}
            
            for main_tag, slices in main_tag_groups.items():
                if not slices:
                    continue
                
                logger.info(f"🤖 处理主模块二级分类: {main_tag} ({len(slices)} 个切片)")
                
                # 创建主模块文件夹
                main_folder = output_base_dir / self.MAIN_MODULES[main_tag]["folder_name"]
                main_folder.mkdir(parents=True, exist_ok=True)
                
                # 🤖 进行二级AI智能聚类（内存中处理）
                sub_clusters = self._perform_secondary_classification_in_memory(
                    main_tag, slices, main_folder
                )
                
                main_modules[main_tag] = sub_clusters
                
                # 记录映射关系
                for cluster in sub_clusters:
                    for slice_data in slices:
                        slice_file = slice_data.get("file_path", "")
                        if slice_file:
                            cluster_mapping[slice_file] = cluster.cluster_id
            
            # 第六步：生成元数据和报告
            metadata = self._generate_unified_metadata(main_modules, output_base_dir, classified_data, unclassified_data)
            
            # 创建结果
            cluster_result = EnhancedClusterResult(
                main_modules=main_modules,
                cluster_mapping=cluster_mapping,
                unclustered_slices=[],
                unclassified_slices=unclassified_data,
                metadata=metadata,
                processing_stats=self.processing_stats,
                ai_analysis_stats=self.ai_analysis_stats
            )
            
            # 导出报告
            self._export_unified_report(cluster_result, output_base_dir)
            
            logger.info(f"✅ 统一智能分类完成，共生成 {len(main_modules)} 个主模块")
            logger.info(f"🤖 AI分析统计: {self.ai_analysis_stats}")
            return cluster_result
            
        except Exception as e:
            logger.error(f"❌ 统一智能分类失败: {e}")
            return EnhancedClusterResult({}, {}, [], [], {}, {}, {})
    
    def _collect_all_slice_data_for_processing(self) -> List[Dict[str, Any]]:
        """收集所有切片数据，包含文件路径和JSON数据，并过滤无效文件"""
        all_data = []
        
        try:
            video_dirs = self.file_manager.get_all_video_directories()
            
            for video_name in video_dirs:
                json_files = self.file_manager.get_slice_json_files(video_name)
                
                for json_file in json_files:
                    json_data = self.file_manager.read_json_file(json_file)
                    if json_data:
                        # 🚨 新增：质量过滤逻辑
                        if self._should_filter_file(json_file, json_data):
                            logger.debug(f"🚫 过滤文件: {json_file.name} (质量问题)")
                            continue
                        
                        # 🔧 修复：仅对有效文件使用智能路径解析
                        resolved_file_path = self.file_manager._resolve_valid_video_file_path(json_file, json_data)
                        
                        # 构建完整的切片数据结构
                        slice_data = {
                            "slice_name": json_file.stem.replace("_analysis", ""),
                            "video_name": video_name,
                            "file_path": resolved_file_path,
                            "analysis_file": str(json_file),
                            "json_data": json_data,  # 内存中保持JSON数据
                            "labels": self.file_manager.extract_labels_for_classification(json_data),
                            "duration": json_data.get("duration", 0),
                            "object": json_data.get("object", ""),
                            "scene": json_data.get("scene", ""),
                            "emotion": json_data.get("emotion", ""),
                            "brand_elements": json_data.get("brand_elements", "")
                        }
                        all_data.append(slice_data)
                        self.processing_stats["total_files"] += 1
            
            logger.info(f"📊 收集完成: 共 {len(all_data)} 个有效切片文件")
            return all_data
            
        except Exception as e:
            logger.error(f"❌ 数据收集失败: {e}")
            return []
    
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
        
        # 检查success字段是否为false
        if json_data.get("success") == False:
            return True
        
        # 检查文件路径是否包含❌标记（♻️标记允许通过）
        file_path = json_data.get("file_path", "")
        if isinstance(file_path, str) and "❌" in file_path:
            return True
        
        return False
    
    def _perform_primary_classification_in_memory(self, 
                                                all_slice_data: List[Dict], 
                                                force_reprocess: bool = False) -> Tuple[List[Dict], List[Dict]]:
        """🤖 在内存中执行主标签分类，避免文件读写"""
        classified_data = []
        unclassified_data = []
        
        for slice_data in all_slice_data:
            try:
                json_data = slice_data["json_data"]
                
                # 检查是否已处理（除非强制重新处理）
                if not force_reprocess and self.file_manager.check_if_already_processed(json_data):
                    # 如果已经有主标签，直接使用
                    if json_data.get("main_tag"):
                        slice_data["main_tag"] = json_data["main_tag"]
                        slice_data["confidence"] = json_data.get("confidence", 0.0)
                        classified_data.append(slice_data)
                        self.processing_stats["skipped"] += 1
                        continue
                
                # 提取标签进行分类
                labels_text = slice_data["labels"]
                
                if not labels_text or labels_text.strip() == "":
                    # 标记为未分类
                    slice_data["unclassified_reason"] = "视觉分析数据为空或无效"
                    unclassified_data.append(slice_data)
                    self.processing_stats["unclassified"] += 1
                    continue
                
                # 🤖 调用主标签AI分类器
                classification_result = self.primary_classifier.classify_single_item({
                    "labels": labels_text,
                    "slice_name": slice_data["slice_name"]
                })
                
                self.ai_analysis_stats["primary_ai_calls"] += 1
                
                if classification_result and classification_result.get("success"):
                    main_tag = classification_result.get("main_tag", "")
                    confidence = classification_result.get("confidence", 0.0)
                    
                    # 标准化主标签
                    normalized_tag = self.tag_manager.normalize_main_tag(main_tag)
                    
                    if normalized_tag and confidence >= self.config.processing.min_confidence_threshold:
                        # 成功分类
                        slice_data["main_tag"] = normalized_tag
                        slice_data["confidence"] = confidence
                        slice_data["analysis"] = classification_result.get("analysis", {})
                        
                        # 🔄 同时更新JSON文件（保持数据一致性）
                        self._update_json_file_with_classification(slice_data, classification_result)
                        
                        classified_data.append(slice_data)
                        self.ai_analysis_stats["successful_primary_classifications"] += 1
                        self.processing_stats["classified_by_primary"] += 1
                        
                        logger.debug(f"✅ 分类成功: {slice_data['slice_name']} -> {normalized_tag} ({confidence:.2f})")
                    else:
                        # 置信度不足
                        reason = f"置信度不足 ({confidence:.2f})"
                        slice_data["unclassified_reason"] = reason
                        unclassified_data.append(slice_data)
                        self.ai_analysis_stats["low_confidence_classifications"] += 1
                        self.processing_stats["unclassified"] += 1
                else:
                    # AI分类失败
                    slice_data["unclassified_reason"] = "AI分类器调用失败"
                    unclassified_data.append(slice_data)
                    self.ai_analysis_stats["failed_classifications"] += 1
                    self.processing_stats["failed"] += 1
                
            except Exception as e:
                logger.error(f"❌ 处理切片失败 {slice_data['slice_name']}: {e}")
                slice_data["unclassified_reason"] = f"处理异常: {str(e)}"
                unclassified_data.append(slice_data)
                self.processing_stats["failed"] += 1
        
        logger.info(f"📊 主标签分类完成: 成功 {len(classified_data)} 个，失败 {len(unclassified_data)} 个")
        return classified_data, unclassified_data
    
    def _group_by_main_tag(self, classified_data: List[Dict]) -> Dict[str, List[Dict]]:
        """按主标签分组数据"""
        main_tag_groups = defaultdict(list)
        
        for slice_data in classified_data:
            main_tag = slice_data.get("main_tag", "")
            if main_tag in self.MAIN_MODULES:
                main_tag_groups[main_tag].append(slice_data)
            else:
                logger.warning(f"⚠️ 未知主标签: {main_tag}")
        
        return dict(main_tag_groups)
    
    def _perform_secondary_classification_in_memory(self, 
                                                  main_tag: str, 
                                                  slices: List[Dict], 
                                                  main_folder: Path) -> List[EnhancedClusterInfo]:
        """🤖 在内存中执行二级AI分类，避免文件读写"""
        if not slices:
            return []
        
        try:
            # 🤖 使用二级AI分类器进行批量分类
            enriched_slices = self.secondary_classifier.batch_classify_secondary(
                slices, main_tag, min_confidence=0.5
            )
            
            self.ai_analysis_stats["secondary_ai_calls"] += len(slices)
            
            # 按二级分类结果分组
            secondary_groups = defaultdict(list)
            for slice_data in enriched_slices:
                secondary_category = slice_data.get("secondary_category", "")
                secondary_confidence = slice_data.get("secondary_confidence", 0.0)
                
                if secondary_confidence >= 0.5 and secondary_category:
                    self.ai_analysis_stats["successful_secondary_classifications"] += 1
                    secondary_groups[secondary_category].append(slice_data)
                    
                    # 🔄 更新JSON文件
                    self._update_json_file_with_secondary_classification(slice_data)
                else:
                    # 低置信度分类
                    self.ai_analysis_stats["low_confidence_classifications"] += 1
                    secondary_groups["低置信度分类"].append(slice_data)
            
            # 为每个二级分类创建聚类信息
            sub_clusters = []
            for secondary_category, category_slices in secondary_groups.items():
                if category_slices:
                    cluster_info = self._create_cluster_info_from_memory(
                        main_tag, secondary_category, category_slices, main_folder
                    )
                    sub_clusters.append(cluster_info)
                    
                    # 组织文件到文件夹
                    self._organize_cluster_files(category_slices, main_folder, secondary_category)
            
            logger.info(f"✅ {main_tag} 二级分类完成: {len(sub_clusters)} 个子类别")
            return sub_clusters
            
        except Exception as e:
            logger.error(f"❌ {main_tag} 二级分类失败: {e}")
            return self._fallback_to_simple_grouping(main_tag, slices, main_folder)
    
    def _update_json_file_with_classification(self, slice_data: Dict, classification_result: Dict):
        """更新JSON文件的主标签分类结果"""
        try:
            analysis_file = Path(slice_data["analysis_file"])
            if analysis_file.exists():
                json_data = slice_data["json_data"]
                
                # 更新主标签字段
                json_data.update({
                    "main_tag": classification_result.get("main_tag", ""),
                    "confidence": classification_result.get("confidence", 0.0),
                    "analysis": classification_result.get("analysis", {}),
                    "main_tag_processed_at": datetime.now().isoformat()
                })
                
                # 写回文件
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logger.warning(f"⚠️ 更新JSON文件失败 {slice_data['slice_name']}: {e}")
    
    def _update_json_file_with_secondary_classification(self, slice_data: Dict):
        """更新JSON文件的二级分类结果"""
        try:
            analysis_file = Path(slice_data["analysis_file"])
            if analysis_file.exists():
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # 更新二级分类字段
                json_data.update({
                    "secondary_category": slice_data.get("secondary_category", ""),
                    "secondary_confidence": slice_data.get("secondary_confidence", 0.0),
                    "secondary_reasoning": slice_data.get("secondary_reasoning", ""),
                    "secondary_features": slice_data.get("secondary_features", []),
                    "secondary_processed_at": datetime.now().isoformat()
                })
                
                # 写回文件
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logger.warning(f"⚠️ 更新二级分类JSON文件失败 {slice_data['slice_name']}: {e}")
    
    def _create_cluster_info_from_memory(self, 
                                       main_tag: str, 
                                       secondary_category: str, 
                                       slices: List[Dict], 
                                       main_folder: Path) -> EnhancedClusterInfo:
        """从内存数据创建聚类信息"""
        cluster_id = f"{main_tag}_{secondary_category}_{len(slices)}"
        
        # 计算统计信息
        total_duration = sum(s.get("duration", 0) for s in slices)
        avg_confidence = sum(s.get("confidence", 0) for s in slices) / len(slices)
        avg_secondary_confidence = sum(s.get("secondary_confidence", 0) for s in slices) / len(slices)
        
        # 提取代表性标签
        representative_tags = []
        for slice_data in slices[:3]:  # 取前3个作为代表
            if slice_data.get("object"):
                representative_tags.append(f"物体: {slice_data['object']}")
            if slice_data.get("scene"):
                representative_tags.append(f"场景: {slice_data['scene']}")
            if slice_data.get("emotion"):
                representative_tags.append(f"情感: {slice_data['emotion']}")
        
        # AI推理（如果有的话）
        ai_reasoning = ""
        if slices and slices[0].get("secondary_reasoning"):
            ai_reasoning = slices[0]["secondary_reasoning"]
        
        return EnhancedClusterInfo(
            cluster_id=cluster_id,
            cluster_name=secondary_category,
            main_category=main_tag,
            sub_category=secondary_category,
            slice_count=len(slices),
            total_duration=total_duration,
            avg_confidence=avg_confidence,
            avg_secondary_confidence=avg_secondary_confidence,
            representative_tags=representative_tags,
            folder_path=str(main_folder),
            source_files=[s.get("file_path", "") for s in slices],
            ai_reasoning=ai_reasoning
        )
    
    def _organize_cluster_files(self, slices: List[Dict], main_folder: Path, category_name: str):
        """组织聚类文件到文件夹 - 支持语义化命名，直接放置在主目录下"""
        try:
            # 不创建子目录，直接使用主目录
            # 用于处理文件名冲突的计数器
            filename_counter = {}
            
            for slice_data in slices:
                # 生成语义化文件名
                secondary_tag = slice_data.get("secondary_category", category_name)
                object_desc = slice_data.get("object", "视频片段")
                
                # 清理文件名中的特殊字符
                clean_tag = self._clean_filename(secondary_tag)
                clean_desc = self._clean_filename(object_desc)
                
                # 限制描述长度
                if len(clean_desc) > 30:
                    clean_desc = clean_desc[:27] + "..."
                
                # 生成基础文件名
                base_filename = f"{clean_tag}_{clean_desc}"
                
                # 处理文件名冲突
                if base_filename in filename_counter:
                    filename_counter[base_filename] += 1
                    final_filename = f"{base_filename}_{filename_counter[base_filename]}"
                else:
                    filename_counter[base_filename] = 0
                    final_filename = base_filename
                
                # 复制视频文件 - 直接放到主目录下
                source_video = Path(slice_data.get("file_path", ""))
                if source_video.exists():
                    target_video = main_folder / f"{final_filename}.mp4"
                    shutil.copy2(source_video, target_video)
                    logger.debug(f"✅ 文件已复制: {source_video.name} → {final_filename}.mp4")
                
                # 复制分析文件 - 直接放到主目录下
                source_analysis = Path(slice_data.get("analysis_file", ""))
                if source_analysis.exists():
                    target_analysis = main_folder / f"{final_filename}_analysis.json"
                    shutil.copy2(source_analysis, target_analysis)
                    
        except Exception as e:
            logger.warning(f"⚠️ 组织文件失败 {category_name}: {e}")
    
    def _clean_filename(self, text: str) -> str:
        """清理文件名中的特殊字符"""
        if not text:
            return "未知"
        
        # 移除或替换特殊字符
        import re
        # 替换Windows和Unix文件系统不支持的字符
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', text)
        # 移除多余的空格和标点
        cleaned = re.sub(r'\s+', '_', cleaned.strip())
        # 移除开头和结尾的下划线
        cleaned = cleaned.strip('_')
        
        return cleaned if cleaned else "未知"
    
    def _create_unclassified_folder(self, unclassified_data: List[Dict], output_dir: Path):
        """创建未分类文件夹"""
        if not unclassified_data:
            return
        
        misc_folder = output_dir / "🧫其他"
        misc_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 创建未分类文件夹: 🧫其他 ({len(unclassified_data)} 个切片)")
        
        # 复制文件到未分类文件夹
        for slice_data in unclassified_data:
            self._organize_cluster_files([slice_data], output_dir, "🧫其他")
        
        # 生成未分类概览
        self._generate_unclassified_overview(unclassified_data, misc_folder)
    
    def _generate_unclassified_overview(self, unclassified_data: List[Dict], folder: Path):
        """生成未分类概览文件"""
        overview_file = folder / "📋_未分类原因分析.json"
        
        # 统计未分类原因
        reason_stats = defaultdict(int)
        for slice_data in unclassified_data:
            reason = slice_data.get("unclassified_reason", "未知原因")
            reason_stats[reason] += 1
        
        overview_data = {
            'category_name': '未分类片段',
            'slice_count': len(unclassified_data),
            'created_at': datetime.now().isoformat(),
            'reason_statistics': dict(reason_stats),
            'processing_stats': self.processing_stats,
            'ai_analysis_stats': self.ai_analysis_stats,
            'slices': [
                {
                    'slice_name': s.get("slice_name", ""),
                    'video_name': s.get("video_name", ""),
                    'file_path': s.get("file_path", ""),
                    'unclassified_reason': s.get("unclassified_reason", ""),
                    'duration': s.get("duration", 0),
                    'labels': s.get("labels", "")
                }
                for s in unclassified_data
            ],
            'recommendations': [
                "检查视觉分析数据的完整性",
                "确认文件是否损坏或格式异常", 
                "考虑重新运行主标签分类",
                "检查是否需要新增主标签类别"
            ]
        }
        
        with open(overview_file, 'w', encoding='utf-8') as f:
            json.dump(overview_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 未分类原因分析已生成: {overview_file}")
    
    def _fallback_to_simple_grouping(self, main_tag: str, slices: List[Dict], main_folder: Path) -> List[EnhancedClusterInfo]:
        """回退到简单分组"""
        logger.warning(f"⚠️ {main_tag} 使用简单分组回退方案")
        
        cluster_info = self._create_cluster_info_from_memory(
            main_tag, "通用分组", slices, main_folder
        )
        
        # 组织文件
        self._organize_cluster_files(slices, main_folder, "通用分组")
        
        return [cluster_info]
    
    def _generate_unified_metadata(self, main_modules: Dict, output_dir: Path, 
                                 classified_data: List[Dict], unclassified_data: List[Dict]) -> Dict:
        """生成统一处理元数据"""
        return {
            "processing_mode": "unified_in_memory",
            "created_at": datetime.now().isoformat(),
            "output_directory": str(output_dir),
            "total_main_modules": len(main_modules),
            "total_classified_slices": len(classified_data),
            "total_unclassified_slices": len(unclassified_data),
            "processing_stats": self.processing_stats,
            "ai_analysis_stats": self.ai_analysis_stats,
            "main_modules_summary": {
                tag: {
                    "cluster_count": len(clusters),
                    "total_slices": sum(c.slice_count for c in clusters)
                }
                for tag, clusters in main_modules.items()
            }
        }
    
    def _export_unified_report(self, cluster_result: EnhancedClusterResult, output_dir: Path):
        """导出统一处理报告"""
        report_file = output_dir / "📊_统一处理报告.json"
        
        report_data = {
            "processing_mode": "unified_in_memory",
            "created_at": datetime.now().isoformat(),
            "summary": {
                "total_main_modules": len(cluster_result.main_modules),
                "total_clusters": sum(len(clusters) for clusters in cluster_result.main_modules.values()),
                "total_slices": sum(c.slice_count for clusters in cluster_result.main_modules.values() for c in clusters),
                "unclassified_slices": len(cluster_result.unclassified_slices)
            },
            "processing_stats": cluster_result.processing_stats,
            "ai_analysis_stats": cluster_result.ai_analysis_stats,
            "main_modules": {
                tag: [
                    {
                        "cluster_name": c.cluster_name,
                        "slice_count": c.slice_count,
                        "avg_confidence": c.avg_confidence,
                        "avg_secondary_confidence": c.avg_secondary_confidence,
                        "representative_tags": c.representative_tags
                    }
                    for c in clusters
                ]
                for tag, clusters in cluster_result.main_modules.items()
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 统一处理报告已生成: {report_file}") 