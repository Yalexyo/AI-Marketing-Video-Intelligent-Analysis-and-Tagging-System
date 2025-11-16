#!/usr/bin/env python3
"""
批量视频转录为SRT字幕文件 - 🔒 严格质量保证版

从指定文件夹批量读取视频文件，使用阿里云DashScope API进行语音转录，
生成时间戳精确的高质量SRT字幕文件。

🔒 质量保证特性:
    - 严格验证时间戳片段的存在和有效性
    - 拒绝生成低质量或无时间戳的SRT文件
    - 详细的质量统计和错误分类报告
    - 90%以上有效片段比例要求
    - 时间戳重叠和文本缺失检测

使用方法:
    python batch_video_to_srt.py --input_dir /path/to/videos --output_dir /path/to/srt --api_key your_api_key

环境变量:
    DASHSCOPE_API_KEY: 阿里云DashScope API密钥

依赖包:
    pip install dashscope moviepy requests
"""

import os
import sys
import argparse
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import json

# 添加当前目录到路径，以便导入本地模块
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from dashscope_audio_analyzer import DashScopeAudioAnalyzer
    from srt_utils import to_srt
except ImportError as e:
    print(f"导入依赖模块失败: {e}")
    print("请确保安装所需依赖:")
    print("pip install dashscope moviepy requests")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('batch_video_to_srt.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class BatchVideoTranscriber:
    """批量视频转录为SRT"""
    
    def __init__(self, api_key: Optional[str] = None, fine_grained: bool = True):
        """
        初始化批量转录器
        
        Args:
            api_key: DashScope API密钥，如果为None则从环境变量获取
            fine_grained: 是否使用精细化SRT（基于词级时间戳）
        """
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self.fine_grained = fine_grained  # 新增：精细度控制
        
        if not self.api_key:
            logger.error("未设置DASHSCOPE_API_KEY，请通过环境变量或命令行参数提供")
            raise ValueError("DashScope API密钥未设置")
        
        # 初始化DashScope分析器
        self.analyzer = DashScopeAudioAnalyzer(api_key=self.api_key)
        
        if not self.analyzer.is_available():
            logger.error("DashScope分析器初始化失败")
            raise RuntimeError("DashScope分析器不可用")
        
        logger.info(f"DashScope分析器初始化成功 - 精细化模式: {'开启' if fine_grained else '关闭'}")
    
    def _validate_segments_quality(self, segments: List[Dict[str, Any]], video_name: str) -> Dict[str, Any]:
        """
        🔒 严格验证时间戳片段质量
        
        Args:
            segments: 时间戳片段列表
            video_name: 视频文件名（用于日志）
            
        Returns:
            Dict: 质量检查结果
        """
        if not segments:
            return {
                "passed": False,
                "error": "无时间戳片段",
                "stats": "0个片段"
            }
        
        valid_segments = 0
        invalid_segments = 0
        total_duration = 0
        min_duration = float('inf')
        max_duration = 0
        overlap_errors = 0
        text_missing = 0
        timestamp_errors = 0
        
        previous_end = 0
        
        for i, segment in enumerate(segments):
            # 检查必需字段
            if not all(key in segment for key in ['start', 'end', 'text']):
                logger.warning(f"片段 {i+1} 缺少必需字段: {segment}")
                invalid_segments += 1
                continue
            
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            text = segment.get('text', '').strip()
            
            # 🔍 时间戳有效性检查
            if start_time < 0 or end_time <= start_time:
                logger.warning(f"片段 {i+1} 时间戳无效: {start_time:.3f}s -> {end_time:.3f}s")
                timestamp_errors += 1
                invalid_segments += 1
                continue
            
            # 🔍 文本内容检查
            if not text:
                logger.warning(f"片段 {i+1} 文本为空")
                text_missing += 1
                invalid_segments += 1
                continue
            
            # 🔍 时间重叠检查
            if start_time < previous_end:
                logger.warning(f"片段 {i+1} 时间重叠: {start_time:.3f}s < {previous_end:.3f}s")
                overlap_errors += 1
            
            # 📊 统计有效片段
            duration = end_time - start_time
            total_duration += duration
            min_duration = min(min_duration, duration)
            max_duration = max(max_duration, duration)
            previous_end = end_time
            valid_segments += 1
            
            logger.debug(f"✅ 片段 {i+1}: {start_time:.3f}s-{end_time:.3f}s ({duration:.1f}s) - {text[:30]}...")
        
        # 🔒 质量标准判定
        total_segments = len(segments)
        valid_ratio = valid_segments / total_segments if total_segments > 0 else 0
        
        # 严格的质量要求
        min_valid_ratio = 0.9  # 至少90%的片段必须有效
        min_segments = 1       # 至少要有1个有效片段
        max_error_ratio = 0.1  # 错误率不能超过10%
        
        # 构建质量统计信息
        avg_duration = total_duration / valid_segments if valid_segments > 0 else 0
        error_ratio = (timestamp_errors + text_missing) / total_segments if total_segments > 0 else 0
        
        stats = f"{valid_segments}/{total_segments}个有效片段 (比例:{valid_ratio:.1%}), " \
                f"平均时长:{avg_duration:.1f}s, 时长范围:{min_duration:.1f}s-{max_duration:.1f}s, " \
                f"错误率:{error_ratio:.1%}"
        
        # 🔒 严格判定逻辑
        if valid_segments < min_segments:
            return {
                "passed": False,
                "error": f"有效片段不足 ({valid_segments} < {min_segments})",
                "stats": stats
            }
        
        if valid_ratio < min_valid_ratio:
            return {
                "passed": False,
                "error": f"有效片段比例过低 ({valid_ratio:.1%} < {min_valid_ratio:.1%})",
                "stats": stats
            }
        
        if error_ratio > max_error_ratio:
            return {
                "passed": False,
                "error": f"错误率过高 ({error_ratio:.1%} > {max_error_ratio:.1%})",
                "stats": stats
            }
        
        # ✅ 质量检查通过
        logger.info(f"✅ 质量检查通过 - {video_name}: {stats}")
        
        return {
            "passed": True,
            "error": None,
            "stats": stats,
            "details": {
                "total_segments": total_segments,
                "valid_segments": valid_segments,
                "invalid_segments": invalid_segments,
                "valid_ratio": valid_ratio,
                "error_ratio": error_ratio,
                "total_duration": total_duration,
                "avg_duration": avg_duration,
                "min_duration": min_duration if min_duration != float('inf') else 0,
                "max_duration": max_duration,
                "timestamp_errors": timestamp_errors,
                "text_missing": text_missing,
                "overlap_errors": overlap_errors
            }
        }
    
    def extract_audio_from_video(self, video_path: str, temp_dir: str) -> Optional[str]:
        """
        从视频文件中提取音频
        
        Args:
            video_path: 视频文件路径
            temp_dir: 临时目录
            
        Returns:
            音频文件路径，失败时返回None
        """
        try:
            logger.info(f"正在从视频提取音频: {Path(video_path).name}")
            
            video = VideoFileClip(video_path)
            if video.audio is None:
                logger.warning(f"视频文件没有音轨: {video_path}")
                return None
            
            audio_path = os.path.join(temp_dir, f"{Path(video_path).stem}.mp3")
            video.audio.write_audiofile(
                audio_path, 
                codec='mp3', 
                logger=None
            )
            video.close()
            
            logger.info(f"音频提取成功: {audio_path}")
            return audio_path
            
        except Exception as e:
            logger.error(f"音频提取失败 {video_path}: {e}")
            return None
    
    def transcribe_video_to_srt(self, video_path: str, output_srt_path: str) -> bool:
        """
        将单个视频转录为SRT文件
        
        Args:
            video_path: 视频文件路径
            output_srt_path: 输出SRT文件路径
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1. 提取音频
                audio_path = self.extract_audio_from_video(video_path, temp_dir)
                if not audio_path:
                    return False
                
                # 2. 转录音频 - 支持精细化模式
                logger.info(f"正在转录音频: {Path(video_path).name}")
                trans_result = self.analyzer.transcribe_audio(
                    audio_path,
                    fine_grained=getattr(self, 'fine_grained', False)
                )
                
                if not trans_result.get("success"):
                    logger.error(f"转录失败: {trans_result.get('error', '未知错误')}")
                    return False
                
                # 3. 🔒 严格的质量保证 - 必须有精确时间戳片段
                segments = trans_result.get('segments', [])
                if not segments or len(segments) == 0:
                    logger.error(f"❌ 转录质量不合格: 缺少时间戳片段 - {Path(video_path).name}")
                    logger.error("🔒 质量保证: 拒绝生成低质量SRT文件")
                    return False
                
                # 4. 🔍 验证时间戳片段质量
                quality_check = self._validate_segments_quality(segments, Path(video_path).name)
                if not quality_check["passed"]:
                    logger.error(f"❌ 时间戳质量检查失败 - {Path(video_path).name}")
                    logger.error(f"🔒 质量问题: {quality_check['error']}")
                    return False
                
                # 5. ✅ 生成高质量SRT字幕（支持精细化）
                logger.info(f"📊 质量统计: {quality_check['stats']}")
                
                # 检查是否有精细化SRT可用
                if hasattr(self, 'fine_grained') and self.fine_grained and trans_result.get('fine_grained_srt'):
                    srt_content = trans_result.get('fine_grained_srt')
                    logger.info(f"🎯 使用精细化SRT生成字幕 (词级时间戳)")
                else:
                    srt_content = to_srt(segments)
                    logger.info(f"📝 使用标准SRT生成字幕 (句子级时间戳)")
                
                # 记录词级统计信息
                word_count = len(trans_result.get('word_segments', []))
                if word_count > 0:
                    logger.info(f"📊 词级时间戳: {word_count}个词")
                
                # 5. 保存SRT文件
                os.makedirs(os.path.dirname(output_srt_path), exist_ok=True)
                with open(output_srt_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                
                logger.info(f"SRT文件保存成功: {output_srt_path}")
                return True
                
        except Exception as e:
            logger.error(f"转录视频失败 {video_path}: {e}")
            return False
    
    def transcribe_video_to_srt_with_details(self, video_path: str, output_srt_path: str,
                                           preset_vocabulary_id: Optional[str] = None) -> Dict[str, Any]:
        """
        将单个视频转录为SRT文件 - 返回详细结果
        
        Args:
            video_path: 视频文件路径
            output_srt_path: 输出SRT文件路径
            preset_vocabulary_id: 预设词汇表ID (默认使用婴幼儿奶粉专用热词表)
            
        Returns:
            Dict: 详细的转录结果，包含质量统计信息
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1. 提取音频
                audio_path = self.extract_audio_from_video(video_path, temp_dir)
                if not audio_path:
                    return {
                        "success": False,
                        "error": "音频提取失败",
                        "error_type": "audio_extraction_failed"
                    }
                
                # 2. 转录音频 - 使用预设词汇表ID和精细化模式
                logger.info(f"正在转录音频: {Path(video_path).name}")
                trans_result = self.analyzer.transcribe_audio(
                    audio_path,
                    preset_vocabulary_id=preset_vocabulary_id,
                    fine_grained=getattr(self, 'fine_grained', False)
                )
                
                # 🎯 保存原始转录结果用于词级语义分析
                self.last_transcription_result = trans_result
                
                if not trans_result.get("success"):
                    return {
                        "success": False,
                        "error": f"转录失败: {trans_result.get('error', '未知错误')}",
                        "error_type": "transcription_failed"
                    }
                
                # 3. 🔒 严格的质量保证 - 必须有精确时间戳片段
                segments = trans_result.get('segments', [])
                if not segments or len(segments) == 0:
                    return {
                        "success": False,
                        "quality_rejected": True,
                        "error": "转录质量不合格: 缺少时间戳片段",
                        "error_type": "no_timestamps"
                    }
                
                # 4. 🔍 验证时间戳片段质量
                quality_check = self._validate_segments_quality(segments, Path(video_path).name)
                if not quality_check["passed"]:
                    return {
                        "success": False,
                        "quality_rejected": True,
                        "error": f"时间戳质量检查失败: {quality_check['error']}",
                        "error_type": "quality_check_failed",
                        "quality_stats": quality_check["stats"]
                    }
                
                # 5. ✅ 生成高质量SRT字幕（支持精细化）
                logger.info(f"📊 质量统计: {quality_check['stats']}")
                
                # 检查是否有精细化SRT可用
                if hasattr(self, 'fine_grained') and self.fine_grained and trans_result.get('fine_grained_srt'):
                    srt_content = trans_result.get('fine_grained_srt')
                    logger.info(f"🎯 使用精细化SRT生成字幕 (词级时间戳)")
                else:
                    srt_content = to_srt(segments)
                    logger.info(f"📝 使用标准SRT生成字幕 (句子级时间戳)")
                
                # 记录词级统计信息
                word_count = len(trans_result.get('word_segments', []))
                if word_count > 0:
                    logger.info(f"📊 词级时间戳: {word_count}个词")
                
                # 6. 保存SRT文件
                os.makedirs(os.path.dirname(output_srt_path), exist_ok=True)
                with open(output_srt_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                
                logger.info(f"✅ 高质量SRT文件保存成功: {output_srt_path}")
                
                return {
                    "success": True,
                    "srt_path": output_srt_path,
                    "quality_stats": quality_check["stats"],
                    "quality_details": quality_check["details"],
                    "transcript_text": trans_result.get("transcript", "")
                }
                
        except Exception as e:
            logger.error(f"转录视频失败 {video_path}: {e}")
            return {
                "success": False,
                "error": f"处理异常: {str(e)}",
                "error_type": "processing_exception"
            }
    
    def batch_process(self, input_dir: str, output_dir: str, 
                     supported_formats: List[str] = None,
                     preset_vocabulary_id: Optional[str] = None) -> Dict[str, Any]:
        """
        批量处理文件夹中的视频文件 - 🍭Origin驱动架构
        
        Args:
            input_dir: 输入视频文件夹 (🍭Origin)
            output_dir: 输出SRT文件夹 (📄SRT)
            supported_formats: 支持的视频格式列表
            preset_vocabulary_id: 预设词汇表ID (默认使用婴幼儿奶粉专用热词表)
            
        Returns:
            处理结果统计
        """
        if supported_formats is None:
            supported_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        
        # 检查输入目录
        if not os.path.exists(input_dir):
            logger.error(f"输入目录不存在: {input_dir}")
            return {"success": False, "error": "输入目录不存在"}
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 扫描视频文件
        video_files = []
        for file in os.listdir(input_dir):
            file_path = os.path.join(input_dir, file)
            if os.path.isfile(file_path):
                file_ext = Path(file).suffix.lower()
                if file_ext in supported_formats:
                    video_files.append(file)
        
        if not video_files:
            logger.warning(f"在输入目录中未找到支持的视频文件: {input_dir}")
            return {"success": False, "error": "未找到支持的视频文件"}
        
        logger.info(f"发现 {len(video_files)} 个视频文件，开始批量处理...")
        
        # 批量处理 - 增强统计信息
        results = {
            "total_files": len(video_files),
            "success_count": 0,
            "failed_count": 0,
            "quality_rejected_count": 0,  # 🔒 质量不合格被拒绝的数量
            "success_files": [],
            "failed_files": [],
            "quality_rejected_files": [],  # 🔒 质量不合格文件列表
            "output_directory": output_dir,
            "quality_stats": {  # 📊 质量统计信息
                "total_segments": 0,
                "valid_segments": 0,
                "avg_segment_duration": 0,
                "total_transcript_duration": 0
            }
        }
        
        for i, video_file in enumerate(video_files, 1):
            logger.info(f"处理进度: {i}/{len(video_files)} - {video_file}")
            
            video_path = os.path.join(input_dir, video_file)
            video_name = Path(video_file).stem
            
            # 🍭Origin架构：为每个视频创建专用目录
            video_output_dir = os.path.join(output_dir, video_name)
            os.makedirs(video_output_dir, exist_ok=True)
            
            # 🍭Origin架构：输出文件名格式 {视频名}_full.srt
            srt_filename = f"{video_name}_full.srt"
            output_srt_path = os.path.join(video_output_dir, srt_filename)
            
            # 🔍 调试：打印路径信息
            logger.info(f"🔍 调试路径信息:")
            logger.info(f"   视频文件: {video_file}")
            logger.info(f"   视频名称: {video_name}")
            logger.info(f"   输出目录: {video_output_dir}")
            logger.info(f"   SRT文件名: {srt_filename}")
            logger.info(f"   完整路径: {output_srt_path}")
            logger.info(f"   路径是否存在: {os.path.exists(output_srt_path)}")
            
            # 跳过已存在的SRT文件
            if os.path.exists(output_srt_path):
                logger.info(f"SRT文件已存在，跳过: {output_srt_path}")
                results["success_count"] += 1
                results["success_files"].append({
                    "video_file": video_file,
                    "srt_file": f"{video_name}/{srt_filename}",
                    "status": "已存在"
                })
                continue
            
            # 处理视频 - 使用预设词汇表ID
            transcription_result = self.transcribe_video_to_srt_with_details(
                video_path, 
                output_srt_path,
                preset_vocabulary_id=preset_vocabulary_id
            )
            
            if transcription_result["success"]:
                results["success_count"] += 1
                success_info = {
                    "video_file": video_file,
                    "srt_file": f"{video_name}/{srt_filename}",
                    "status": "新生成",
                    "quality_stats": transcription_result.get("quality_stats", {})
                }
                results["success_files"].append(success_info)
                
                # 📊 累计质量统计
                quality_details = transcription_result.get("quality_details", {})
                if quality_details:
                    results["quality_stats"]["total_segments"] += quality_details.get("total_segments", 0)
                    results["quality_stats"]["valid_segments"] += quality_details.get("valid_segments", 0)
                    results["quality_stats"]["total_transcript_duration"] += quality_details.get("total_duration", 0)
                
                logger.info(f"✅ 成功: {video_file} -> {video_name}/{srt_filename}")
                
            elif transcription_result.get("quality_rejected"):
                # 🔒 质量不合格
                results["quality_rejected_count"] += 1
                results["quality_rejected_files"].append({
                    "video_file": video_file,
                    "error": transcription_result["error"],
                    "error_type": "quality_rejected"
                })
                logger.error(f"🔒 质量拒绝: {video_file} - {transcription_result['error']}")
                
            else:
                # ❌ 其他失败
                results["failed_count"] += 1
                results["failed_files"].append({
                    "video_file": video_file,
                    "error": transcription_result.get("error", "转录失败"),
                    "error_type": transcription_result.get("error_type", "unknown")
                })
                logger.error(f"❌ 失败: {video_file} - {transcription_result.get('error', '未知错误')}")
        
        # 📊 计算平均片段时长
        total_segments = results["quality_stats"]["total_segments"]
        total_duration = results["quality_stats"]["total_transcript_duration"]
        if total_segments > 0:
            results["quality_stats"]["avg_segment_duration"] = total_duration / total_segments
        
        # 输出统计结果
        logger.info("=" * 60)
        logger.info("🎉 批量处理完成!")
        logger.info("=" * 60)
        
        # 📈 基本统计
        logger.info(f"📁 总文件数: {results['total_files']}")
        logger.info(f"✅ 成功转录: {results['success_count']}")
        logger.info(f"🔒 质量拒绝: {results['quality_rejected_count']}")
        logger.info(f"❌ 其他失败: {results['failed_count']}")
        logger.info(f"📂 输出目录: {output_dir}")
        
        # 📊 质量统计
        if results['success_count'] > 0:
            logger.info("=" * 40)
            logger.info("📊 质量统计报告:")
            quality_stats = results["quality_stats"]
            logger.info(f"   总时间戳片段: {quality_stats['total_segments']}")
            logger.info(f"   有效片段数: {quality_stats['valid_segments']}")
            logger.info(f"   总转录时长: {quality_stats['total_transcript_duration']:.1f}秒")
            if quality_stats["avg_segment_duration"] > 0:
                logger.info(f"   平均片段时长: {quality_stats['avg_segment_duration']:.1f}秒")
            
            # 计算质量率
            if quality_stats['total_segments'] > 0:
                quality_rate = quality_stats['valid_segments'] / quality_stats['total_segments']
                logger.info(f"   时间戳质量率: {quality_rate:.1%}")
        
        # 🔒 质量拒绝详情
        if results["quality_rejected_files"]:
            logger.warning("=" * 40)
            logger.warning("🔒 质量不合格文件:")
            for rejected in results["quality_rejected_files"]:
                logger.warning(f"   - {rejected['video_file']}: {rejected['error']}")
        
        # ❌ 其他失败详情
        if results["failed_files"]:
            logger.warning("=" * 40)
            logger.warning("❌ 其他失败文件:")
            for failed in results["failed_files"]:
                logger.warning(f"   - {failed['video_file']}: {failed['error']}")
        
        # 🎯 质量保证总结
        logger.info("=" * 40)
        success_rate = results['success_count'] / results['total_files'] if results['total_files'] > 0 else 0
        quality_reject_rate = results['quality_rejected_count'] / results['total_files'] if results['total_files'] > 0 else 0
        
        logger.info(f"🎯 质量保证总结:")
        logger.info(f"   成功率: {success_rate:.1%}")
        logger.info(f"   质量拒绝率: {quality_reject_rate:.1%}")
        logger.info(f"   质量标准: 严格模式 🔒")
        
        if success_rate >= 0.8:
            logger.info("✨ 整体质量: 优秀")
        elif success_rate >= 0.6:
            logger.info("📈 整体质量: 良好")
        else:
            logger.warning("⚠️ 整体质量: 需要改进")
        
        return {"success": True, "results": results}


def main():
    """主函数 - 命令行入口"""
    parser = argparse.ArgumentParser(
        description="批量视频转录为SRT字幕文件 - 🔒 严格质量保证版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🔒 质量保证特性:
    - 严格验证时间戳片段存在性和有效性
    - 拒绝生成低质量或无时间戳的SRT文件  
    - 90%以上有效片段比例要求，10%以下错误率限制
    - 详细的质量统计和错误分类报告
    - 时间戳重叠检测和文本缺失验证

使用示例:
    # 基本用法 - 严格质量模式
    python batch_video_to_srt.py -i /path/to/videos -o /path/to/srt

    # 指定API密钥
    python batch_video_to_srt.py -i videos/ -o srt/ --api_key your_dashscope_key

    # 详细模式 - 查看质量检查过程
    python batch_video_to_srt.py -v

    # 使用默认目录（相对于当前目录）
    python batch_video_to_srt.py

环境变量:
    DASHSCOPE_API_KEY: 阿里云DashScope API密钥

注意: 本工具采用严格质量保证，只生成高质量的精确时间戳SRT文件！
        """
    )
    
    # 获取当前目录
    current_dir = Path(__file__).resolve().parent
    default_input = current_dir / "input_videos"
    default_output = current_dir / "output_srt"
    
    parser.add_argument(
        "-i", "--input_dir",
        type=str,
        default=str(default_input),
        help=f"输入视频文件夹路径 (默认: {default_input})"
    )
    
    parser.add_argument(
        "-o", "--output_dir", 
        type=str,
        default=str(default_output),
        help=f"输出SRT文件夹路径 (默认: {default_output})"
    )
    
    parser.add_argument(
        "--api_key",
        type=str,
        help="DashScope API密钥 (可选，优先级高于环境变量)"
    )
    
    parser.add_argument(
        "--formats",
        type=str,
        nargs="+",
        default=[".mp4", ".mov", ".avi", ".mkv", ".webm"],
        help="支持的视频格式 (默认: .mp4 .mov .avi .mkv .webm)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出模式"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 打印配置信息
    logger.info("批量视频转录为SRT - 开始运行")
    logger.info(f"输入目录: {args.input_dir}")
    logger.info(f"输出目录: {args.output_dir}")
    logger.info(f"支持格式: {args.formats}")
    
    try:
        # 初始化转录器
        transcriber = BatchVideoTranscriber(api_key=args.api_key)
        
        # 批量处理
        result = transcriber.batch_process(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            supported_formats=args.formats
        )
        
        if result["success"]:
            results = result["results"]
            if results["failed_count"] == 0:
                logger.info("🎉 所有文件都已成功处理!")
                sys.exit(0)
            else:
                logger.warning(f"⚠️ 部分文件处理失败 ({results['failed_count']}/{results['total_files']})")
                sys.exit(1)
        else:
            logger.error(f"❌ 批量处理失败: {result['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        sys.exit(130)
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main() 