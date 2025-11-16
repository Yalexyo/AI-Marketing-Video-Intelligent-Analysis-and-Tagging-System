#!/usr/bin/env python3
"""
批量SRT转产品介绍视频处理器
协调整个处理流程：SRT解析 -> AI分析 -> 视频生成
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

try:
    from .srt_parser import SRTParser
    from .deepseek_analyzer import DeepSeekAnalyzer
    from .video_generator import VideoGenerator
    from .env_loader import validate_config, get_config_summary
except ImportError:
    from srt_parser import SRTParser
    from deepseek_analyzer import DeepSeekAnalyzer
    from video_generator import VideoGenerator
    from env_loader import validate_config, get_config_summary

logger = logging.getLogger(__name__)

class BatchSRTToProductProcessor:
    """批量SRT转产品介绍视频处理器"""
    
    def __init__(self, input_video_dir: str, api_key: Optional[str] = None):
        """
        初始化批量处理器
        
        Args:
            input_video_dir: 原始视频目录路径
            api_key: DeepSeek API密钥
        """
        self.input_video_dir = Path(input_video_dir)
        
        # 验证配置
        if not validate_config():
            raise ValueError("配置验证失败，请检查API密钥设置")
        
        # 初始化各个组件
        self.srt_parser = SRTParser()
        self.ai_analyzer = DeepSeekAnalyzer(api_key=api_key)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("批量处理器初始化完成")
        
        # 记录配置信息
        config_summary = get_config_summary()
        self.logger.info(f"配置摘要: {config_summary}")
    
    def process_batch(self, srt_dir: Path, output_dir: str, 
                     temp_dir: str = "data/temp") -> Tuple[Dict, Path]:
        """
        批量处理SRT文件
        
        Args:
            srt_dir: SRT文件目录
            output_dir: 输出视频目录
            temp_dir: 临时目录
            
        Returns:
            处理结果摘要
        """
        start_time = time.time()
        
        self.temp_dir = Path(temp_dir)
        self.output_dir = Path(output_dir)
        
        # 确保目录存在
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("开始批量处理")
        self.logger.info(f"SRT目录: {srt_dir}")
        self.logger.info(f"输出目录: {self.output_dir}")
        self.logger.info(f"原始视频目录: {self.input_video_dir}")
        
        srt_files = self._scan_srt_files(srt_dir)
        self.logger.info(f"发现{len(srt_files)}个SRT文件")
            
        all_processing_results = []
        all_video_results = []

        # 初始化视频生成器
        video_generator = VideoGenerator(
            input_dir=str(self.input_video_dir),
            output_dir=str(self.output_dir)
        )
        self.logger.info("视频生成器初始化完成")
            
        for i, srt_file in enumerate(srt_files):
            self.logger.info(f"处理文件 {i+1}/{len(srt_files)}: {srt_file.name}")
                
            processing_result, video_results = self._process_file(
                srt_file, video_generator
            )
            all_processing_results.append(processing_result)
            all_video_results.extend(video_results)
            
        # 生成并保存报告
        report = self._generate_report(all_processing_results, all_video_results, start_time)
        report_path = self._save_report(report, self.output_dir)
            
        # 🚀 自动整理文件到结构化目录
        # self._auto_organize_outputs()
        
        # 清理临时文件
        self._cleanup_temp_dir()
        
        return report, report_path

    def _process_file(self, srt_file: Path, video_generator: 'VideoGenerator') -> Tuple[Dict, List[Dict]]:
        """处理单个SRT文件，分析并为每个主题生成视频"""
        
        # 🚀 清理该视频的旧产品介绍文件，避免重复累积
        self._clean_old_product_videos(srt_file.stem)
        
        # 1. 解析SRT
        segments = self.srt_parser.parse_srt_file(srt_file)
        if not segments:
            return {'filename': srt_file.name, 'success': False, 'error': 'SRT解析失败'}, []

        # 2. AI分析所有主题
        product_mentions = self.ai_analyzer.analyze_srt_content(segments, srt_file.name)
        if not product_mentions:
            return {'filename': srt_file.name, 'success': False, 'error': 'AI未识别到产品主题'}, []
        
        # 🎯 只保留高置信度的核心产品主题，过滤低质量内容
        core_mentions = [m for m in product_mentions if m.confidence >= 0.8]
        if not core_mentions:
            self.logger.warning(f"未找到高置信度主题，使用所有识别的主题")
            core_mentions = product_mentions
        
        self.logger.info(f"AI分析完成，识别到{len(product_mentions)}个主题，筛选出{len(core_mentions)}个核心主题")

        # 3. 为每个核心主题生成视频
        video_results = []
        for mention in core_mentions:
            self.logger.info(f"为主题 '{mention.topic}' 生成视频...")
            
            # 创建一个符合旧版逻辑的 "segment_info"
            segment_info_for_video = {
                'start_time': mention.start_time,
                'end_time': mention.end_time,
                'topic': mention.topic,
                'sequence_ids': mention.sequence_ids,
                'summary': mention.summary,
                'keywords': mention.keywords,
                'logic_pattern': mention.logic_pattern,
                'confidence': mention.confidence,
                'scene_type': mention.scene_type,
                'duration': mention.duration
            }

            video_result = video_generator.generate_video_from_segment(
                srt_filename=srt_file.name,
                segment_info=segment_info_for_video,
                use_topic_as_filename=True # <--- 新增逻辑
            )
            video_results.append(video_result)

            if video_result['success']:
                self.logger.info(f"成功生成视频: {video_result['output_path']}")
            else:
                self.logger.error(f"主题 '{mention.topic}' 视频生成失败: {video_result['error']}")

        # 4. 构建处理结果
        processing_result = {
            'filename': srt_file.name,
            'success': True,
            'error': None,
            'segments_count': len(segments),
            'product_mentions': core_mentions,  # 只返回核心主题
            'analysis_summary': self.ai_analyzer.get_analysis_summary(core_mentions)
        }
        
        return processing_result, video_results

    def _clean_old_product_videos(self, video_stem: str):
        """清理指定视频的旧产品介绍文件（视频+SRT）"""
        try:
            # 清理视频文件
            mp4_pattern = f"{video_stem}_*.mp4"
            old_videos = list(self.output_dir.glob(mp4_pattern))
            
            # 清理SRT文件
            srt_pattern = f"{video_stem}_*.srt"
            old_srts = list(self.output_dir.glob(srt_pattern))
            
            old_files = old_videos + old_srts
            
            if old_files:
                self.logger.info(f"清理{len(old_files)}个旧的产品文件...")
                for old_file in old_files:
                    old_file.unlink()
                    self.logger.debug(f"删除: {old_file.name}")
            
        except Exception as e:
            self.logger.warning(f"清理旧文件时出错: {e}")

    def _scan_srt_files(self, srt_dir: Path) -> List[Path]:
        """扫描目录下的SRT文件（递归扫描子目录）"""
        # 🔍 递归搜索所有SRT文件，包括子目录
        srt_files = list(srt_dir.rglob('*.srt'))
        
        # 🚫 过滤掉已经是产品切片的SRT文件，避免重复处理和时间戳错误
        filtered_files = []
        for srt_file in srt_files:
            # 排除包含产品主题名称的切片文件
            exclude_keywords = ['启赋蕴淳', '启赋水奶', '启赋蓝钻', '_product', '产品介绍', '核心配方', '便携']
            if any(keyword in srt_file.name for keyword in exclude_keywords):
                self.logger.info(f"跳过产品切片SRT文件: {srt_file.name}")
                continue
                
            # ✅ 只处理完整SRT文件（根据架构设计原则）
            if '_full.srt' in srt_file.name:
                filtered_files.append(srt_file)
                self.logger.info(f"找到完整SRT文件: {srt_file}")
            else:
                self.logger.debug(f"跳过非完整SRT文件: {srt_file.name}")
        
        filtered_files.sort()  # 按文件名排序
        return filtered_files
    
    def _generate_report(self, processing_results: List[Dict], 
                        video_results: List[Dict], start_time: float) -> Dict:
        """生成处理报告"""
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 统计SRT处理结果
        srt_total = len(processing_results)
        srt_success = sum(1 for r in processing_results if r['success'])
        srt_failed = srt_total - srt_success
        
        # 统计视频生成结果
        video_total = len(video_results)
        video_success = sum(1 for r in video_results if r['success'])
        video_failed = video_total - video_success
        
        # 收集AI分析统计
        total_segments_analyzed = sum(
            len(r.get('product_mentions', [])) for r in processing_results if r['success']
        )
        
        best_confidences = [
            r['product_mentions'][0].confidence 
            for r in processing_results 
            if r['success'] and r['product_mentions']
        ]
        
        avg_confidence = sum(best_confidences) / len(best_confidences) if best_confidences else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'processing_time': processing_time,
            'summary': {
                'srt_processing': {
                    'total': srt_total,
                    'success': srt_success,
                    'failed': srt_failed,
                    'success_rate': srt_success / srt_total if srt_total > 0 else 0
                },
                'video_generation': {
                    'total': video_total,
                    'success': video_success,
                    'failed': video_failed,
                    'success_rate': video_success / video_total if video_total > 0 else 0
                },
                'ai_analysis': {
                    'total_segments_analyzed': total_segments_analyzed,
                    'avg_confidence': avg_confidence,
                    'segments_with_products': len(best_confidences)
                }
            },
            'detailed_results': {
                'srt_processing': [{
                    'filename': r['filename'],
                    'success': r['success'],
                    'error': r['error'],
                    'segments_count': r['segments_count'],
                    'product_mentions': r['product_mentions'],
                    'analysis_summary': r['analysis_summary']
                } for r in processing_results],
                'video_generation': video_results
            },
            'config_used': get_config_summary()
        }
        
        return report
    
    def _save_report(self, report: Dict, output_dir: Path) -> Path:
        """保存处理报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"srt_to_product_report_{timestamp}.json"
        report_file = output_dir / report_filename
        
        try:
            # 将ProductSegment对象转换为可序列化的字典
            serializable_report = self._make_serializable(report)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_report, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"报告已保存: {report_file}")
            return report_file
            
        except Exception as e:
            self.logger.error(f"保存报告失败: {e}")
            return output_dir / "report_save_failed.txt"
    
    def _make_serializable(self, obj):
        """将对象转换为可JSON序列化的格式"""
        if hasattr(obj, '__dict__'):
            # 处理自定义对象（如ProductSegment）
            return {
                'topic': getattr(obj, 'topic', '未定义'),
                'sequence_ids': getattr(obj, 'sequence_ids', []),
                'summary': getattr(obj, 'summary', ''),
                'start_time': obj.start_time,
                'end_time': obj.end_time,
                'duration': obj.duration,
                'confidence': obj.confidence,
                'keywords': obj.keywords,
                'logic_pattern': getattr(obj, 'logic_pattern', '其他'),
                'scene_type': getattr(obj, 'scene_type', '未分类')
            }
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        else:
            return obj
    
    def get_input_video_files(self) -> List[Path]:
        """获取输入视频目录中的视频文件列表"""
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(self.input_video_dir.glob(f'*{ext}'))
            video_files.extend(self.input_video_dir.glob(f'*{ext.upper()}'))
        
        return sorted(video_files)
    
    def validate_input_setup(self, srt_dir: Path) -> Dict:
        """验证输入设置"""
        srt_dir = Path(srt_dir)
        
        # 检查SRT目录
        if not srt_dir.exists():
            return {'valid': False, 'error': f'SRT目录不存在: {srt_dir}'}
        
        # 检查原始视频目录
        if not self.input_video_dir.exists():
            return {'valid': False, 'error': f'原始视频目录不存在: {self.input_video_dir}'}
        
        # 扫描文件
        srt_files = self._scan_srt_files(srt_dir)
        video_files = self.get_input_video_files()
        
        if not srt_files:
            return {'valid': False, 'error': 'SRT目录中未找到.srt文件'}
        
        if not video_files:
            return {'valid': False, 'error': '原始视频目录中未找到视频文件'}
        
        # 检查匹配情况
        matched_pairs = []
        unmatched_srt = []
        
        for srt_file in srt_files:
            base_name = srt_file.stem
            matched = False
            
            for video_file in video_files:
                if video_file.stem == base_name:
                    matched_pairs.append((srt_file.name, video_file.name))
                    matched = True
                    break
            
            if not matched:
                unmatched_srt.append(srt_file.name)
        
        return {
            'valid': True,
            'srt_files_count': len(srt_files),
            'video_files_count': len(video_files),
            'matched_pairs': matched_pairs,
            'unmatched_srt': unmatched_srt,
            'expected_outputs': len(matched_pairs)
        } 

    def _cleanup_temp_dir(self):
        """清理临时目录"""
        # 实现清理临时目录的逻辑
        pass

    def _cleanup_temp_files(self):
        """清理临时文件"""
        # 实现清理临时文件的逻辑
        pass

    # def _auto_organize_outputs(self):
    #     """自动整理输出文件到结构化目录"""
    #     try:
    #         import sys
    #         # 添加MCP服务器路径以便导入auto_organizer
    #         mcp_path = Path(__file__).parent.parent.parent / "mcp_server"
    #         if str(mcp_path) not in sys.path:
    #             sys.path.append(str(mcp_path))
    #         from auto_organizer import AutoOrganizer
    #         # 创建整理器实例（基于项目根目录）
    #         base_dir = Path(__file__).parent.parent.parent
    #         organizer = AutoOrganizer(str(base_dir))
    #         # 执行自动整理
    #         result = organizer.auto_organize_after_tool('srt_to_product', str(self.output_dir))
    #         if result['success']:
    #             self.logger.info(f"✅ 自动整理完成: 整理了{result['organized_files']}个文件")
    #             for file_info in organizer.organized_files:
    #                 self.logger.info(f"  📁 {file_info}")
    #         else:
    #             self.logger.warning(f"⚠️ 自动整理存在问题: {result['errors']}个错误")
    #             for error in organizer.errors:
    #                 self.logger.warning(f"  ❌ {error}")
    #     except ImportError as e:
    #         self.logger.warning(f"⚠️ 无法导入auto_organizer，跳过自动整理: {e}")
    #     except Exception as e:
    #         self.logger.error(f"❌ 自动整理失败: {e}") 