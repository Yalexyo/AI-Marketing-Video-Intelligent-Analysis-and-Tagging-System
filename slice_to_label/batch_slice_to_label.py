#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量视频切片标签提取器 - 双层识别机制版本

基于主程序的双层识别机制：
1. 第一层（AI-B）：通用物体/场景/情绪识别 + 主谓宾动作识别  
2. 第二层（AI-A）：条件触发的品牌专用检测

参考架构：batch_video_to_srt.py
"""

import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# 添加当前目录到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from config.slice_config import validate_config, get_output_config, get_quality_control
from src.ai_analyzers import DualStageAnalyzer, BatchSliceAnalyzer
from utils.file_utils import scan_video_files, ensure_output_directory

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('slice_to_label.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class BatchSliceToLabelProcessor:
    """
    批量切片标签提取处理器
    
    基于主程序的双层识别机制实现
    参考：batch_video_to_srt.py 的架构模式
    """
    
    def __init__(self):
        """初始化处理器"""
        self.output_config = get_output_config()
        self.quality_control = get_quality_control()
        
        # 确保输出目录存在
        for dir_key, dir_path in self.output_config.items():
            if dir_key.endswith("_dir"):
                Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # 初始化分析器
        self.dual_analyzer = DualStageAnalyzer()
        self.batch_analyzer = BatchSliceAnalyzer()
        
        logger.info("✅ 批量切片标签提取处理器初始化完成")
        logger.info("🎯 双层识别机制：AI-B通用识别 + AI-A条件品牌检测")
    
    def process_directory(
        self, 
        input_dir: str, 
        output_dir: Optional[str] = None,
        file_pattern: str = "*.mp4"
    ) -> Dict[str, Any]:
        """
        处理整个目录的视频文件
        
        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径（可选）
            file_pattern: 文件匹配模式
            
        Returns:
            处理结果字典
        """
        logger.info(f"🎯 开始处理目录: {input_dir}")
        logger.info(f"📁 文件模式: {file_pattern}")
        
        # 扫描视频文件
        video_files = scan_video_files(input_dir)
        
        if not video_files:
            logger.warning(f"未找到匹配的视频文件: {input_dir}")
            return {
                "success": False,
                "error": "未找到匹配的视频文件",
                "input_dir": input_dir,
                "file_pattern": file_pattern
            }
        
        logger.info(f"📹 发现 {len(video_files)} 个视频文件")
        
        # 确定输出目录
        if not output_dir:
            output_dir = self.output_config["output_dir"]
        
        # 确保output_dir是字符串类型
        if output_dir is None:
            output_dir = str(Path.cwd() / "output")
        
        ensure_output_directory(output_dir)
        
        # 批量处理
        batch_result = self._process_file_list(video_files, output_dir)
        
        # 添加输入目录信息到结果中
        batch_result["input_directory"] = input_dir
        
        return batch_result
    
    def process_single_file(self, video_path: str, analysis_type: str = "full") -> Dict[str, Any]:
        """
        处理单个视频文件
        
        Args:
            video_path: 视频文件路径
            analysis_type: 分析类型 ("visual", "audio", "full")
            
        Returns:
            处理结果字典
        """
        try:
            logger.info(f"🎯 开始处理单个文件: {video_path}")
            logger.info(f"📊 分析类型: {analysis_type}")
            
            # 验证文件
            if not Path(video_path).exists():
                return {"error": f"文件不存在: {video_path}", "success": False}
            
            # 执行分析
            result = self.dual_analyzer.analyze_video_slice(video_path, analysis_type)
            
            if result.get("success"):
                # 添加文件信息
                result["file_path"] = str(video_path)
                result["file_name"] = Path(video_path).name
                result["file_size_mb"] = Path(video_path).stat().st_size / (1024 * 1024)
                result["analysis_type"] = analysis_type
                result["processed_at"] = time.time()
                
                logger.info(f"✅ 单文件处理成功: {Path(video_path).name}")
                return result
            else:
                logger.error(f"❌ 单文件处理失败: {result.get('error', '未知错误')}")
                return result
                
        except Exception as e:
            logger.error(f"单文件处理异常: {str(e)}")
            return {"error": str(e), "success": False}
    
    def process_batch(self, input_dir: str, analysis_type: str = "full", max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        批量处理视频文件
        
        Args:
            input_dir: 输入目录
            analysis_type: 分析类型 ("visual", "audio", "full")
            max_files: 最大处理文件数，None为无限制
            
        Returns:
            批量处理结果
        """
        try:
            logger.info(f"🎯 开始批量处理")
            logger.info(f"📂 输入目录: {input_dir}")
            logger.info(f"📊 分析类型: {analysis_type}")
            logger.info(f"📋 最大文件数: {max_files or '无限制'}")
            
            # 扫描视频文件
            video_files = self._scan_video_files(input_dir)
            
            if not video_files:
                return {"error": "未找到视频文件", "success": False}
            
            # 限制文件数量
            if max_files:
                video_files = video_files[:max_files]
            
            logger.info(f"📋 找到 {len(video_files)} 个视频文件")
            
            # 批量处理
            results = []
            failed_files = []
            
            for i, video_file in enumerate(video_files, 1):
                logger.info(f"🎬 处理进度: {i}/{len(video_files)} - {Path(video_file).name}")
                
                try:
                    result = self.process_single_file(video_file, analysis_type)
                    
                    if result.get("success"):
                        results.append(result)
                    else:
                        failed_files.append({
                            "file": video_file,
                            "error": result.get("error", "未知错误")
                        })
                        
                except Exception as e:
                    logger.error(f"处理文件失败: {video_file}, 错误: {e}")
                    failed_files.append({
                        "file": video_file,
                        "error": str(e)
                    })
                
                # 简单的进度显示
                if i % 10 == 0:
                    logger.info(f"📊 已处理 {i} 个文件，成功 {len(results)} 个")
            
            # 生成批量处理报告
            batch_report = self._generate_batch_report(results, failed_files, analysis_type)
            
            # 保存结果
            output_file = self._save_batch_results(results, analysis_type)
            batch_report["output_file"] = output_file
            
            logger.info(f"✅ 批量处理完成，成功 {len(results)} 个，失败 {len(failed_files)} 个")
            return batch_report
            
        except Exception as e:
            logger.error(f"批量处理异常: {str(e)}")
            return {"error": str(e), "success": False}
    
    def _process_file_list(
        self, 
        video_files: List[str], 
        output_dir: str
    ) -> Dict[str, Any]:
        """
        处理文件列表
        
        Args:
            video_files: 视频文件路径列表
            output_dir: 输出目录
            
        Returns:
            批量处理结果
        """
        logger.info(f"🚀 开始批量双层识别分析，共 {len(video_files)} 个文件")
        
        start_time = time.time()
        
        # 执行批量分析
        batch_result = self.batch_analyzer.analyze_batch(
            video_files=video_files,
            progress_callback=self._progress_callback
        )
        
        # 保存批量结果
        summary_file = self._save_batch_summary(batch_result, output_dir)
        batch_result["summary_file"] = summary_file
        
        # 保存详细结果
        details_file = self._save_detailed_results(batch_result, output_dir)
        batch_result["details_file"] = details_file
        
        # 生成报告
        report_file = self._generate_analysis_report(batch_result, output_dir)
        batch_result["report_file"] = report_file
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 添加处理信息
        batch_result.update({
            "processing_duration": duration,
            "output_directory": output_dir,
            "processing_timestamp": datetime.now().isoformat()
        })
        
        self._print_processing_summary(batch_result)
        
        return batch_result
    
    def _progress_callback(self, message: str):
        """进度回调函数"""
        logger.info(f"📊 {message}")
    
    def _save_single_result(self, result: Dict[str, Any], output_dir: str) -> str:
        """保存单个分析结果 - 使用结构化文件名"""
        file_path = Path(result["file_path"])
        file_name = file_path.stem
        
        # 清理文件名，确保只包含安全字符
        clean_name = "".join(c for c in file_name if c.isalnum() or c in ('_', '-'))
        
        # 使用结构化命名：视频文件名_analysis.json
        output_file = Path(output_dir) / f"{clean_name}_analysis.json"
        
        try:
            # 构建结构化结果数据
            structured_result = {
                'file_info': {
                    'filename': file_path.name,
                    'file_path': str(file_path),
                    'file_size_mb': round(file_path.stat().st_size / (1024 * 1024), 2) if file_path.exists() else 0,
                    'directory': file_path.parent.name
                },
                'analysis_info': {
                    'analysis_time': datetime.now().isoformat(),
                    'analyzer_version': 'dual_stage_v1.0',
                    'analysis_method': result.get('analysis_method', 'dual_stage'),
                    'success': result.get('success', True)
                },
                'content_analysis': {
                    'interaction': result.get('object', '未知'),
                    'scene': result.get('scene', '未知'),
                    'emotion': result.get('emotion', '未知'),
                    'confidence': result.get('confidence', 0.8)
                },
                'brand_detection': {
                    'brand_elements': result.get('brand_elements', '无'),
                    'brand_detected': result.get('brand_elements', '无') != '无',
                    'stage2_triggered': result.get('stage2_triggered', False)
                },
                                 'technical_details': {
                     'key_frames_extracted': result.get('key_frames_count', 0),
                     'processing_time_seconds': result.get('processing_time', 0),
                     'stage1_success': result.get('stage1_success', True),
                     'stage2_success': result.get('stage2_success', True) if result.get('stage2_triggered') else None
                 }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(structured_result, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"💾 结构化结果已保存: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"保存单个结果失败: {e}")
            return ""
    
    def _save_batch_summary(self, batch_result: Dict[str, Any], output_dir: str) -> str:
        """保存批量分析汇总 - 使用结构化命名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 从批量结果中获取输入目录信息
        input_info = batch_result.get('input_directory', 'unknown')
        if isinstance(input_info, str):
            dir_name = Path(input_info).name
        else:
            dir_name = 'mixed'
        
        summary_file = Path(output_dir) / f"batch_summary_{dir_name}_{timestamp}.json"
        
        try:
            # 准备汇总数据（不包含详细结果）
            summary_data = {
                "processing_info": {
                    "total_files": batch_result["total_files"],
                    "success_count": batch_result["success_count"],
                    "failed_count": batch_result["failed_count"],
                    "duration": batch_result["duration"],
                    "timestamp": datetime.now().isoformat()
                },
                "statistics": batch_result["statistics"],
                "dual_stage_metrics": {
                    "stage2_trigger_rate": batch_result["statistics"].get("stage2_trigger_rate", 0),
                    "average_confidence": batch_result["statistics"].get("average_confidence", 0),
                    "top_interactions": dict(list(batch_result["statistics"].get("interaction_frequency", {}).items())[:5]),
                    "top_brands": dict(list(batch_result["statistics"].get("brand_frequency", {}).items())[:5])
                }
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📄 批量分析汇总已保存: {summary_file}")
            return str(summary_file)
            
        except Exception as e:
            logger.error(f"保存批量汇总失败: {e}")
            return ""
    
    def _save_detailed_results(self, batch_result: Dict[str, Any], output_dir: str) -> str:
        """保存详细分析结果 - 使用结构化命名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 从批量结果中获取输入目录信息
        input_info = batch_result.get('input_directory', 'unknown')
        if isinstance(input_info, str):
            dir_name = Path(input_info).name
        else:
            dir_name = 'mixed'
        
        details_file = Path(output_dir) / f"batch_details_{dir_name}_{timestamp}.json"
        
        try:
            with open(details_file, 'w', encoding='utf-8') as f:
                json.dump(batch_result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📋 详细分析结果已保存: {details_file}")
            return str(details_file)
            
        except Exception as e:
            logger.error(f"保存详细结果失败: {e}")
            return ""
    
    def _generate_analysis_report(self, batch_result: Dict[str, Any], output_dir: str) -> str:
        """生成分析报告 - 使用结构化命名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 从批量结果中获取输入目录信息
        input_info = batch_result.get('input_directory', 'unknown')
        if isinstance(input_info, str):
            dir_name = Path(input_info).name
        else:
            dir_name = 'mixed'
        
        report_file = Path(output_dir) / f"analysis_report_{dir_name}_{timestamp}.md"
        
        try:
            statistics = batch_result["statistics"]
            
            report_content = f"""# 双层识别机制分析报告

## 📊 处理概况

- **总文件数**: {batch_result["total_files"]}
- **成功处理**: {batch_result["success_count"]}
- **处理失败**: {batch_result["failed_count"]}
- **成功率**: {(batch_result["success_count"] / batch_result["total_files"] * 100):.1f}%
- **处理时长**: {batch_result["duration"]:.2f} 秒
- **平均置信度**: {statistics.get("average_confidence", 0):.2f}

## 🎯 双层识别机制表现

### 第二阶段触发率
- **品牌检测触发率**: {statistics.get("stage2_trigger_rate", 0):.1f}%
- 说明：检测到产品相关交互并触发品牌专用检测的比例

### 第一阶段：通用识别结果

#### 🎭 交互行为频次 (主谓宾结构)
"""
            
            # 添加交互频次统计
            interaction_freq = statistics.get("interaction_frequency", {})
            if interaction_freq:
                for interaction, count in sorted(interaction_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
                    report_content += f"- **{interaction}**: {count} 次\n"
            else:
                report_content += "- 暂无交互数据\n"
            
            report_content += f"""
#### 🏞️ 场景环境频次
"""
            
            # 添加场景频次统计
            scene_freq = statistics.get("scene_frequency", {})
            if scene_freq:
                for scene, count in sorted(scene_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
                    report_content += f"- **{scene}**: {count} 次\n"
            else:
                report_content += "- 暂无场景数据\n"
            
            report_content += f"""
#### 😊 情绪表达频次
"""
            
            # 添加情绪频次统计
            emotion_freq = statistics.get("emotion_frequency", {})
            if emotion_freq:
                for emotion, count in sorted(emotion_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
                    report_content += f"- **{emotion}**: {count} 次\n"
            else:
                report_content += "- 暂无情绪数据\n"
            
            report_content += f"""
### 第二阶段：品牌专用检测结果

#### 🏷️ 核心品牌识别频次
"""
            
            # 添加品牌频次统计
            brand_freq = statistics.get("brand_frequency", {})
            if brand_freq:
                for brand, count in sorted(brand_freq.items(), key=lambda x: x[1], reverse=True):
                    report_content += f"- **{brand}**: {count} 次\n"
            else:
                report_content += "- 未检测到核心品牌\n"
            
            report_content += f"""
## 📈 标签统计

### 高频标签 TOP 15
"""
            
            # 添加高频标签统计
            tag_freq = statistics.get("tag_frequency", {})
            if tag_freq:
                for tag, count in sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:15]:
                    report_content += f"- **{tag}**: {count} 次\n"
            else:
                report_content += "- 暂无标签数据\n"
            
            report_content += f"""
## 🛠️ 技术说明

### 双层识别机制
1. **第一层（AI-B）**: 专注通用物体/场景/情绪识别，强调主谓宾动作描述
2. **第二层（AI-A）**: 仅在检测到产品相关交互时触发，进行核心品牌专用检测

### 识别优势
- **防误识别**: 品牌检测与基础识别分离，避免品牌规则干扰通用识别
- **精准触发**: 只有在检测到产品相关行为时才启动品牌检测
- **主谓宾结构**: 第一阶段强调行为/交互的完整描述

---
*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"📖 分析报告已生成: {report_file}")
            return str(report_file)
            
        except Exception as e:
            logger.error(f"生成分析报告失败: {e}")
            return ""
    
    def _print_processing_summary(self, batch_result: Dict[str, Any]):
        """打印处理摘要"""
        print("\n" + "="*60)
        print("🎯 双层识别机制处理完成")
        print("="*60)
        print(f"📊 总文件数: {batch_result['total_files']}")
        print(f"✅ 成功处理: {batch_result['success_count']}")
        print(f"❌ 处理失败: {batch_result['failed_count']}")
        print(f"📈 成功率: {(batch_result['success_count'] / batch_result['total_files'] * 100):.1f}%")
        print(f"⏱️ 处理时长: {batch_result['duration']:.2f} 秒")
        
        statistics = batch_result['statistics']
        print(f"🎯 第二阶段触发率: {statistics.get('stage2_trigger_rate', 0):.1f}%")
        print(f"📊 平均置信度: {statistics.get('average_confidence', 0):.2f}")
        
        # 显示高频标签
        tag_freq = statistics.get('tag_frequency', {})
        if tag_freq:
            top_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"🏷️ 高频标签: {', '.join([f'{tag}({count})' for tag, count in top_tags])}")
        
        # 显示检测到的品牌
        brand_freq = statistics.get('brand_frequency', {})
        if brand_freq:
            brands = list(brand_freq.keys())
            print(f"🎁 检测品牌: {', '.join(brands)}")
        else:
            print("🎁 检测品牌: 无")
        
        print(f"📁 输出目录: {batch_result.get('output_directory', 'N/A')}")
        print("="*60)

    def _generate_batch_report(self, results: List[Dict], failed_files: List[Dict], analysis_type: str) -> Dict[str, Any]:
        """生成批量处理报告（优化为片段分析）"""
        try:
            total_files = len(results) + len(failed_files)
            success_rate = len(results) / total_files * 100 if total_files > 0 else 0
            
            # 统计分析方法
            analysis_methods = {}
            for result in results:
                method = result.get("analysis_method", "unknown")
                analysis_methods[method] = analysis_methods.get(method, 0) + 1
            
            # 统计标签频次（片段级别）
            tag_stats = self._generate_segment_tag_statistics(results)
            
            # 质量统计
            quality_stats = self._generate_quality_statistics(results)
            
            # 音频分析统计（如果包含音频分析）
            audio_stats = self._generate_audio_statistics(results) if analysis_type in ["audio", "full"] else {}
            
            report = {
                "success": True,
                "summary": {
                    "total_files": total_files,
                    "successful_files": len(results),
                    "failed_files": len(failed_files),
                    "success_rate": f"{success_rate:.1f}%",
                    "analysis_type": analysis_type
                },
                "analysis_methods": analysis_methods,
                "tag_statistics": tag_stats,
                "quality_statistics": quality_stats,
                "failed_files": failed_files[:10]  # 只显示前10个失败文件
            }
            
            # 添加音频统计（如果有）
            if audio_stats:
                report["audio_statistics"] = audio_stats
            
            return report
            
        except Exception as e:
            logger.error(f"生成批量报告失败: {str(e)}")
            return {"error": str(e), "success": False}
    
    def _generate_segment_tag_statistics(self, results: List[Dict]) -> Dict[str, Any]:
        """生成片段级别的标签统计"""
        try:
            # 统计各类标签
            object_tags = {}
            scene_tags = {}
            emotion_tags = {}
            brand_tags = {}
            
            for result in results:
                # 统计object标签
                objects = result.get("object", "").split(", ")
                for obj in objects:
                    if obj.strip():
                        object_tags[obj.strip()] = object_tags.get(obj.strip(), 0) + 1
                
                # 统计scene标签
                scenes = result.get("scene", "").split(", ")
                for scene in scenes:
                    if scene.strip():
                        scene_tags[scene.strip()] = scene_tags.get(scene.strip(), 0) + 1
                
                # 统计emotion标签
                emotion = result.get("emotion", "").strip()
                if emotion:
                    emotion_tags[emotion] = emotion_tags.get(emotion, 0) + 1
                
                # 统计brand标签
                brands = result.get("brand_elements", "").split(", ")
                for brand in brands:
                    if brand.strip():
                        brand_tags[brand.strip()] = brand_tags.get(brand.strip(), 0) + 1
            
            return {
                "top_objects": dict(sorted(object_tags.items(), key=lambda x: x[1], reverse=True)[:10]),
                "top_scenes": dict(sorted(scene_tags.items(), key=lambda x: x[1], reverse=True)[:10]),
                "top_emotions": dict(sorted(emotion_tags.items(), key=lambda x: x[1], reverse=True)[:10]),
                "top_brands": dict(sorted(brand_tags.items(), key=lambda x: x[1], reverse=True)[:10]),
                "total_unique_objects": len(object_tags),
                "total_unique_scenes": len(scene_tags),
                "total_unique_emotions": len(emotion_tags),
                "total_unique_brands": len(brand_tags)
            }
            
        except Exception as e:
            logger.error(f"生成标签统计失败: {str(e)}")
            return {}
    
    def _generate_audio_statistics(self, results: List[Dict]) -> Dict[str, Any]:
        """生成音频分析统计"""
        try:
            audio_results = [r for r in results if r.get("transcription")]
            
            if not audio_results:
                return {"message": "无音频分析结果"}
            
            # 转录统计
            total_transcriptions = len(audio_results)
            avg_transcription_length = sum(len(r.get("transcription", "")) for r in audio_results) / total_transcriptions
            
            # 音频置信度统计
            audio_confidences = [r.get("transcription_confidence", 0) for r in audio_results if r.get("transcription_confidence")]
            avg_audio_confidence = sum(audio_confidences) / len(audio_confidences) if audio_confidences else 0
            
            return {
                "total_audio_analyzed": total_transcriptions,
                "avg_transcription_length": f"{avg_transcription_length:.1f} 字符",
                "avg_audio_confidence": f"{avg_audio_confidence:.2f}",
                "audio_success_rate": f"{total_transcriptions / len(results) * 100:.1f}%"
            }
            
        except Exception as e:
            logger.error(f"生成音频统计失败: {str(e)}")
            return {"error": str(e)}

    def _save_batch_results(self, results: List[Dict], analysis_type: str) -> str:
        """保存批量处理结果"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_config["output_dir"] / f"batch_analysis_{analysis_type}_{timestamp}.json"
            
            # 确保输出目录存在
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存结果
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📁 批量结果已保存: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"保存批量结果失败: {str(e)}")
            return ""
    
    def _generate_quality_statistics(self, results: List[Dict]) -> Dict[str, Any]:
        """生成质量统计"""
        try:
            if not results:
                return {}
            
            # 置信度统计
            confidences = [r.get("confidence", 0) for r in results]
            avg_confidence = sum(confidences) / len(confidences)
            high_confidence_count = sum(1 for c in confidences if c > 0.7)
            
            # 文件大小统计
            file_sizes = [r.get("file_size_mb", 0) for r in results]
            avg_file_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
            
            return {
                "avg_confidence": f"{avg_confidence:.2f}",
                "high_confidence_rate": f"{high_confidence_count / len(results) * 100:.1f}%",
                "avg_file_size_mb": f"{avg_file_size:.2f}",
                "total_processed": len(results)
            }
            
        except Exception as e:
            logger.error(f"生成质量统计失败: {str(e)}")
            return {}

    def _scan_video_files(self, directory: str) -> List[str]:
        """扫描目录中的视频文件，并过滤无效文件"""
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.m4v', '.webm']
        video_files = []
        filtered_count = 0  # 过滤文件计数
        
        def _should_filter_video_file(file_path: Path) -> bool:
            """判断视频文件是否应该被过滤"""
            # 🎯 用户反馈：多镜头视频也应该被分析，只过滤真正失败的文件
            # 只过滤❌前缀的文件（分析失败），♻️文件允许正常分析
            if file_path.stem.startswith("❌"):
                return True
            return False
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in video_extensions:
                    # 🚨 新增：过滤逻辑
                    if _should_filter_video_file(file_path):
                        filtered_count += 1
                        logger.debug(f"🚫 过滤视频文件: {file_path.name} (质量问题)")
                        continue
                    video_files.append(str(file_path))
        
        if filtered_count > 0:
            logger.info(f"🚫 批量处理过滤了 {filtered_count} 个质量问题视频文件")
        
        return sorted(video_files)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="批量视频片段标签分析工具 - 基于双层识别机制",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 双层视觉机制（推荐）
  python batch_slice_to_label.py --input data/segments --type dual
  
  # 双层机制+音频增强
  python batch_slice_to_label.py --input data/segments --type enhanced
  
  # 单文件分析
  python batch_slice_to_label.py --file segment_001.mp4 --type dual
  
  # 批量处理（限制文件数）
  python batch_slice_to_label.py --input data/segments --type dual --max-files 50
        """
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input", "-i",
        type=str,
        help="输入目录路径（批量处理）"
    )
    input_group.add_argument(
        "--file", "-f", 
        type=str,
        help="单个视频文件路径"
    )
    
    # 分析类型
    parser.add_argument(
        "--type", "-t",
        choices=["dual", "enhanced"],
        default="dual",
        help="分析类型：dual(双层视觉机制), enhanced(双层+音频增强) [默认: dual]"
    )
    
    # 批量处理选项
    parser.add_argument(
        "--max-files",
        type=int,
        help="最大处理文件数（仅批量处理时有效）"
    )
    
    # 输出选项
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出目录路径（可选，默认使用配置中的路径）"
    )
    
    # 调试选项
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出模式"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🔍 详细输出模式已启用")
    
    try:
        # 验证配置
        if not validate_config():
            logger.error("❌ 配置验证失败，请检查API密钥和配置")
            return 1
        
        logger.info("🎯 slice_to_label 批量分析工具启动")
        logger.info(f"📊 分析类型: {args.type}")
        
        # 创建处理器
        processor = BatchSliceToLabelProcessor()
        
        # 执行处理
        if args.file:
            # 单文件处理
            logger.info(f"🎬 单文件模式: {args.file}")
            result = processor.process_single_file(args.file, args.type)
            
            if result.get("success"):
                logger.info("✅ 单文件处理成功")
                print(f"\n🎯 分析结果:")
                print(f"📁 文件: {result.get('file_name', 'N/A')}")
                print(f"📊 分析方法: {result.get('analysis_method', 'N/A')}")
                print(f"🏷️ 物体标签: {result.get('object', '无')}")
                print(f"🎬 场景标签: {result.get('scene', '无')}")
                print(f"😊 情绪标签: {result.get('emotion', '无')}")
                print(f"🏢 品牌标签: {result.get('brand_elements', '无')}")
                print(f"📈 置信度: {result.get('confidence', 0):.2f}")
                
                if result.get('transcription'):
                    print(f"🎤 语音转录: {result.get('transcription', '')[:100]}...")
                
            else:
                logger.error(f"❌ 单文件处理失败: {result.get('error', '未知错误')}")
                return 1
                
        else:
            # 批量处理
            logger.info(f"📂 批量处理模式: {args.input}")
            result = processor.process_batch(args.input, args.type, args.max_files)
            
            if result.get("success"):
                summary = result.get("summary", {})
                logger.info("✅ 批量处理完成")
                print(f"\n📊 批量处理总结:")
                print(f"📋 总文件数: {summary.get('total_files', 0)}")
                print(f"✅ 成功文件: {summary.get('successful_files', 0)}")
                print(f"❌ 失败文件: {summary.get('failed_files', 0)}")
                print(f"📈 成功率: {summary.get('success_rate', '0%')}")
                print(f"📊 分析类型: {summary.get('analysis_type', 'N/A')}")
                
                if result.get("output_file"):
                    print(f"📁 结果文件: {result.get('output_file')}")
                
                # 显示标签统计
                tag_stats = result.get("tag_statistics", {})
                if tag_stats:
                    print(f"\n🏷️ 标签统计:")
                    print(f"🔍 物体类型: {tag_stats.get('total_unique_objects', 0)} 种")
                    print(f"🎬 场景类型: {tag_stats.get('total_unique_scenes', 0)} 种")
                    print(f"😊 情绪类型: {tag_stats.get('total_unique_emotions', 0)} 种")
                    print(f"🏢 品牌类型: {tag_stats.get('total_unique_brands', 0)} 种")
                
                # 显示音频统计（如果有）
                audio_stats = result.get("audio_statistics", {})
                if audio_stats and audio_stats.get("total_audio_analyzed"):
                    print(f"\n🎤 音频分析统计:")
                    print(f"📝 转录文件: {audio_stats.get('total_audio_analyzed', 0)} 个")
                    print(f"📏 平均长度: {audio_stats.get('avg_transcription_length', 'N/A')}")
                    print(f"📈 音频置信度: {audio_stats.get('avg_audio_confidence', 'N/A')}")
                    print(f"✅ 音频成功率: {audio_stats.get('audio_success_rate', 'N/A')}")
                
            else:
                logger.error(f"❌ 批量处理失败: {result.get('error', '未知错误')}")
                return 1
        
        logger.info("🎉 分析任务完成")
        return 0
        
    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断操作")
        return 1
    except Exception as e:
        logger.error(f"💥 程序异常: {str(e)}")
        return 1

if __name__ == "__main__":
    main() 