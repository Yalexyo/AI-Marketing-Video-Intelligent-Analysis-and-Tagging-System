#!/usr/bin/env python3
"""
视频生成器 - SRT转产品介绍视频
基于AI分析结果从原始视频中切片生成产品介绍视频
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, List
import ffmpeg
import subprocess
import re

try:
    from .deepseek_analyzer import ProductSegment
    from .env_loader import get_video_quality
    from .srt_parser import SRTSegment
except ImportError:
    from deepseek_analyzer import ProductSegment
    from env_loader import get_video_quality
    from srt_parser import SRTSegment

logger = logging.getLogger(__name__)

class VideoGenerator:
    """视频生成器"""
    
    def __init__(self, input_dir: str, output_dir: str, 
                 video_quality: str = "medium", temp_dir: str = "data/temp"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.video_quality = video_quality
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.temp_files = []
        
        # 🍭Origin原始视频目录 (优先查找)
        self.origin_dir = Path("../🍭Origin")
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"视频生成器初始化完成 (🍭Origin驱动架构)")
        self.logger.info(f"🍭Origin目录: {self.origin_dir}")
        self.logger.info(f"输入目录: {self.input_dir}")
        self.logger.info(f"输出目录: {self.output_dir}")
        self.logger.info(f"视频质量: {self.video_quality}")
        
        # 支持的视频格式
        self.supported_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv']
    
    def _sanitize_filename(self, text: str) -> str:
        """清理文件名中的无效字符"""
        # 移除或替换Windows和macOS/Linux文件名中的无效字符
        text = re.sub(r'[\s/\\:\*\?"<>\|]+', '_', text)
        return text[:50] # 限制文件名长度
    
    def generate_product_video(self, srt_filename: str, 
                              product_segment: ProductSegment) -> Optional[Path]:
        """
        生成产品介绍视频
        
        Args:
            srt_filename: SRT文件名（用于匹配原始视频文件）
            product_segment: 产品介绍片段信息
            
        Returns:
            生成的视频文件路径，失败返回None
        """
        try:
            # 查找对应的原始视频文件
            video_path = self._find_source_video(srt_filename)
            if not video_path:
                self.logger.error(f"未找到对应的原始视频文件: {srt_filename}")
                return None
            
            # 生成输出文件名
            output_filename = self._generate_output_filename(srt_filename)
            output_path = self.output_dir / output_filename
            
            # 切片视频
            success = self._slice_video(
                video_path=video_path,
                start_time=product_segment.start_time,
                end_time=product_segment.end_time,
                output_path=output_path
            )
            
            if success:
                self.logger.info(f"成功生成产品视频: {output_filename}")
                self.logger.info(f"场景类型: {product_segment.scene_type}")
                self.logger.info(f"时间段: {product_segment.start_time:.3f}s - {product_segment.end_time:.3f}s")
                self.logger.info(f"时长: {product_segment.duration:.1f}s")
                self.logger.info(f"置信度: {product_segment.confidence:.2f}")
                return output_path
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"生成产品视频失败: {e}")
            return None
    
    def _find_source_video(self, srt_filename: str) -> Optional[Path]:
        """查找对应的原始视频文件 - 🍭Origin优先架构"""
        # 从SRT文件名获取基础名称（去掉.srt扩展名）
        base_name = Path(srt_filename).stem
        
        # 🎯 第一优先级：在🍭Origin目录中查找匹配的视频文件
        if self.origin_dir.exists():
            for ext in self.supported_formats:
                video_path = self.origin_dir / f"{base_name}{ext}"
                if video_path.exists():
                    self.logger.debug(f"🍭Origin中找到对应视频文件: {video_path}")
                    return video_path
            
            # 在🍭Origin中尝试模糊匹配
            for video_file in self.origin_dir.glob('*'):
                if video_file.suffix.lower() in self.supported_formats:
                    video_stem = video_file.stem
                    if base_name in video_stem or video_stem in base_name:
                        self.logger.debug(f"🍭Origin中模糊匹配到视频文件: {video_file}")
                        return video_file
        
        # 🛡️ 兜底方案：在输入目录中查找匹配的视频文件（向后兼容）
        for ext in self.supported_formats:
            video_path = self.input_dir / f"{base_name}{ext}"
            if video_path.exists():
                self.logger.debug(f"输入目录中找到对应视频文件: {video_path}")
                return video_path
        
        # 如果找不到完全匹配的，尝试模糊匹配
        for video_file in self.input_dir.glob('*'):
            if video_file.suffix.lower() in self.supported_formats:
                video_stem = video_file.stem
                if base_name in video_stem or video_stem in base_name:
                    self.logger.debug(f"输入目录中模糊匹配到视频文件: {video_file}")
                    return video_file
        
        return None
    
    def _generate_output_filename(self, srt_filename: str) -> str:
        """
        生成输出文件名
        
        Args:
            srt_filename: SRT文件名
            
        Returns:
            格式化的输出文件名：{视频名称}_product.mp4
        """
        base_name = Path(srt_filename).stem
        return f"{base_name}_product.mp4"
    
    def _slice_video(self, video_path: Path, start_time: float, 
                    end_time: float, output_path: Path) -> bool:
        """
        切片视频
        
        Args:
            video_path: 原始视频路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            output_path: 输出视频路径
            
        Returns:
            是否成功
        """
        try:
            # 检查时间范围
            if start_time < 0:
                start_time = 0
            
            if start_time >= end_time:
                self.logger.error(f"无效的时间范围: {start_time}s - {end_time}s")
                return False
            
            # 计算时长
            duration = end_time - start_time
            
            self.logger.debug(f"使用ffmpeg切片视频: {video_path}")
            self.logger.debug(f"切片时间: {start_time:.1f}s - {end_time:.1f}s (时长: {duration:.1f}s)")
            
            # 使用ffmpeg切片视频 - 使用流复制提高速度
            (
                ffmpeg
                .input(str(video_path), ss=start_time, t=duration)
                .output(str(output_path), vcodec='copy', acodec='copy')  # 使用流复制，大幅提升速度
                .overwrite_output()
                .run(quiet=True)
            )
            
            # 检查输出文件是否存在
            if output_path.exists() and output_path.stat().st_size > 0:
                self.logger.debug(f"视频切片成功: {output_path}")
                return True
            else:
                self.logger.error(f"视频切片失败: 输出文件不存在或为空")
                return False
            
        except ffmpeg.Error as e:
            self.logger.error(f"FFmpeg错误: {e}")
            return False
        except Exception as e:
            self.logger.error(f"视频切片失败: {e}")
            return False
    
    def generate_video_from_segment(self, srt_filename: str, segment_info: dict, 
                                    use_topic_as_filename: bool = False) -> Dict:
        """从单个产品片段生成视频"""
        base_name = Path(srt_filename).stem
        input_video = self._find_matching_video(base_name)
        
        if not input_video:
            return {'success': False, 'error': f'未找到匹配的视频: {base_name}.mp4'}

        start_time = segment_info['start_time']
        end_time = segment_info['end_time']
        
        if use_topic_as_filename:
            topic = segment_info.get('topic', 'product')
            sanitized_topic = self._sanitize_filename(topic)
            output_filename = f"{base_name}_{sanitized_topic}.mp4"
            srt_filename_output = f"{base_name}_{sanitized_topic}.srt"
        else:
            output_filename = f"{base_name}_product.mp4"
            srt_filename_output = f"{base_name}_product.srt"

        output_path = self.output_dir / output_filename
        srt_output_path = self.output_dir / srt_filename_output

        # 1. 生成视频切片
        video_success = self._slice_video(
            video_path=input_video,
            start_time=start_time,
            end_time=end_time,
            output_path=output_path
        )

        # 2. 生成对应的SRT切片文件
        srt_success = self._generate_srt_slice(
            original_srt_path=self._find_original_srt(srt_filename),
            start_time=start_time,
            end_time=end_time,
            output_srt_path=srt_output_path
        )

        if video_success:
            file_size_mb = round(output_path.stat().st_size / (1024 * 1024), 1)
            duration_seconds = round(end_time - start_time, 1)
            
            result = {
                'success': True,
                'output_path': str(output_path),
                'srt_path': str(srt_output_path) if srt_success else None,
                'file_size_mb': file_size_mb,
                'duration_seconds': duration_seconds,
                'start_time': start_time,
                'end_time': end_time
            }
            
            self.logger.info(f"视频生成成功: {output_filename} ({file_size_mb}MB, {duration_seconds}s)")
            if srt_success:
                self.logger.info(f"SRT切片生成成功: {srt_filename_output}")
            else:
                self.logger.warning(f"SRT切片生成失败: {srt_filename_output}")
                
            return result
        else:
            return {'success': False, 'error': '视频切片失败'}

    def _find_original_srt(self, srt_filename: str) -> Path:
        """查找原始SRT文件路径"""
        # 从多个可能的位置查找SRT文件
        possible_paths = [
            Path(f"../📄SRT/video_1/{srt_filename}"),  # 相对路径
            Path(f"../📄SRT/{srt_filename}"),          # 备用路径
            self.input_dir / srt_filename,               # 输入目录
        ]
        
        for path in possible_paths:
            if path.exists():
                self.logger.debug(f"找到原始SRT文件: {path}")
                return path
        
        self.logger.warning(f"未找到原始SRT文件: {srt_filename}")
        return None

    def _generate_srt_slice(self, original_srt_path: Path, start_time: float, 
                           end_time: float, output_srt_path: Path) -> bool:
        """
        生成SRT切片文件
        
        ⚠️  重要说明：此SRT切片文件仅用于与视频配对，提供精确的字幕时间戳
        🚫 绝不应该被当作新的输入源重新处理！
        ✅ 唯一输入源应该永远是原始完整SRT文件
        
        Args:
            original_srt_path: 原始完整SRT文件路径
            start_time: 切片开始时间（秒）
            end_time: 切片结束时间（秒）  
            output_srt_path: 输出SRT切片路径
            
        Returns:
            是否成功生成
        """
        if not original_srt_path or not original_srt_path.exists():
            self.logger.error(f"原始SRT文件不存在: {original_srt_path}")
            return False
            
        try:
            from .srt_parser import SRTParser
        except ImportError:
            from srt_parser import SRTParser
            
            # 解析原始SRT
            parser = SRTParser()
            segments = parser.parse_srt_file(original_srt_path)
            
            if not segments:
                self.logger.error("原始SRT解析失败")
                return False
            
            # 筛选时间范围内的片段
            selected_segments = []
            for segment in segments:
                # 判断片段是否与目标时间范围重叠
                if (segment.start_time < end_time and segment.end_time > start_time):
                    # 调整时间戳，使其相对于切片开始时间
                    adjusted_start = max(0, segment.start_time - start_time)
                    adjusted_end = segment.end_time - start_time
                    
                    # 确保结束时间不超过切片长度
                    slice_duration = end_time - start_time
                    adjusted_end = min(adjusted_end, slice_duration)
                    
                    if adjusted_end > adjusted_start:
                        selected_segments.append({
                            'index': len(selected_segments) + 1,
                            'start_time': adjusted_start,
                            'end_time': adjusted_end,
                            'text': segment.text
                        })
            
            if not selected_segments:
                self.logger.warning("未找到匹配的SRT片段")
                return False
            
            # 生成SRT内容
            srt_content = self._format_srt_content(selected_segments)
            
            # 写入文件，并添加元数据注释
            header_comment = f"""# 产品切片SRT配套文件
# 原始文件: {original_srt_path.name}
# 切片时间: {start_time:.1f}s - {end_time:.1f}s
# 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ⚠️  此文件仅用于与视频配对，不应作为输入源重新处理！

"""
            
            with open(output_srt_path, 'w', encoding='utf-8') as f:
                f.write(header_comment + srt_content)
            
            self.logger.debug(f"生成SRT切片: {output_srt_path}, 包含{len(selected_segments)}个片段")
            return True
                    
        except Exception as e:
            self.logger.error(f"生成SRT切片失败: {e}")
            return False

    def _format_srt_content(self, segments: list) -> str:
        """格式化SRT内容"""
        srt_lines = []
        
        for segment in segments:
            # 格式化时间戳
            start_formatted = self._format_srt_timestamp(segment['start_time'])
            end_formatted = self._format_srt_timestamp(segment['end_time'])
            
            srt_lines.append(str(segment['index']))
            srt_lines.append(f"{start_formatted} --> {end_formatted}")
            srt_lines.append(segment['text'])
            srt_lines.append("")  # 空行分隔
        
        return '\n'.join(srt_lines)

    def _format_srt_timestamp(self, seconds: float) -> str:
        """格式化SRT时间戳 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def batch_generate_videos(self, tasks: List[Dict]) -> List[Dict]:
        """批量生成产品介绍视频（旧版，保留以备用）"""
        results = []
        for task in tasks:
            result = self.generate_video_from_segment(
                srt_filename=task['srt_filename'],
                segment_info=task['product_segment'].__dict__
            )
            results.append(result)
        return results
    
    def get_statistics(self, results: List[Dict]) -> Dict:
        """获取生成统计信息"""
        total = len(results)
        success_count = sum(1 for r in results if r['success'])
        failed_count = total - success_count
        
        total_duration = 0
        total_confidence = 0
        all_keywords = []
        
        for result in results:
            if result['success'] and result['segment_info']:
                total_duration += result['segment_info']['duration']
                total_confidence += result['segment_info']['confidence']
                all_keywords.extend(result['segment_info']['keywords'])
        
        avg_duration = total_duration / success_count if success_count > 0 else 0
        avg_confidence = total_confidence / success_count if success_count > 0 else 0
        unique_keywords = len(set(all_keywords))
        
        return {
            'total_tasks': total,
            'success_count': success_count,
            'failed_count': failed_count,
            'success_rate': success_count / total if total > 0 else 0,
            'avg_duration': avg_duration,
            'avg_confidence': avg_confidence,
            'total_duration': total_duration,
            'unique_keywords': unique_keywords
        }
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            for temp_file in self.temp_dir.glob('*'):
                if temp_file.is_file():
                    temp_file.unlink()
            self.logger.debug("临时文件清理完成")
        except Exception as e:
            self.logger.warning(f"清理临时文件失败: {e}") 

    def _find_matching_video(self, base_name: str) -> Optional[Path]:
        """根据SRT基本名称查找匹配的视频文件 - 🍭Origin优先架构"""
        # 🎯 第一优先级：在🍭Origin目录中查找匹配的视频文件
        if self.origin_dir.exists():
            for ext in self.supported_formats:
                video_path = self.origin_dir / f"{base_name}{ext}"
                if video_path.exists():
                    self.logger.debug(f"🍭Origin中找到对应视频文件: {video_path}")
                    return video_path
            
            # 在🍭Origin中尝试模糊匹配
            for video_file in self.origin_dir.glob('*'):
                if video_file.suffix.lower() in self.supported_formats:
                    video_stem = video_file.stem
                    if base_name in video_stem or video_stem in base_name:
                        self.logger.debug(f"🍭Origin中模糊匹配到视频文件: {video_file}")
                        return video_file
        
        # 🛡️ 兜底方案：在输入目录中查找匹配的视频文件（向后兼容）
        for ext in self.supported_formats:
            video_path = self.input_dir / f"{base_name}{ext}"
            if video_path.exists():
                self.logger.debug(f"输入目录中找到对应视频文件: {video_path}")
                return video_path
        
        # 如果找不到完全匹配的，尝试模糊匹配
        for video_file in self.input_dir.glob('*'):
            if video_file.suffix.lower() in self.supported_formats:
                video_stem = video_file.stem
                if base_name in video_stem or video_stem in base_name:
                    self.logger.debug(f"输入目录中模糊匹配到视频文件: {video_file}")
                    return video_file
        
        return None 