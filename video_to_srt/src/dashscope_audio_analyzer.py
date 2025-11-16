"""
DashScope语音转录分析器

专门处理阿里云DashScope语音转录、热词分析、专业词汇矫正功能的模块
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path

# 导入环境变量加载器
try:
    from .env_loader import get_dashscope_api_key, get_default_vocab_id
except ImportError:
    # 处理直接运行时的导入问题
    from env_loader import get_dashscope_api_key, get_default_vocab_id

logger = logging.getLogger(__name__)


class DashScopeAudioAnalyzer:
    """DashScope语音转录分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化DashScope语音分析器
        
        Args:
            api_key: DashScope API密钥
        """
        self.api_key = api_key or get_dashscope_api_key()
        self.base_url = "https://dashscope.aliyuncs.com"
        
        if not self.api_key:
            logger.warning("未设置DASHSCOPE_API_KEY，DashScope语音分析器不可用")
        else:
            self._initialize_client()
    
    def _initialize_client(self):
        """初始化DashScope客户端"""
        try:
            import dashscope
            dashscope.api_key = self.api_key
            logger.info("DashScope语音分析器初始化成功")
        except ImportError as e:
            logger.error(f"无法导入DashScope: {str(e)}")
            self.api_key = None
        except Exception as e:
            logger.error(f"DashScope语音分析器初始化失败: {str(e)}")
            self.api_key = None
    
    def is_available(self) -> bool:
        """检查分析器是否可用"""
        return self.api_key is not None
    
    def transcribe_audio(
        self,
        audio_path: str,
        language: str = "zh",
        format_result: bool = True,
        preset_vocabulary_id: Optional[str] = None,
        fine_grained: bool = False
    ) -> Dict[str, Any]:
        """
        转录音频文件为文本和时间戳
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码（zh/en）
            format_result: 是否格式化为SRT（废弃，保持兼容性）
            preset_vocabulary_id: 预设词汇表ID（热词表）
            fine_grained: 是否使用精细化时间戳（词级别）
            
        Returns:
            Dict: 包含转录结果的字典
                - success: bool - 是否成功
                - transcript: str - 转录文本
                - segments: List[Dict] - 时间戳片段
                - error: str - 错误信息（如果失败）
        """
        try:
            # 🔧 步骤1: 上传音频到OSS（DashScope录音文件识别需要公网URL）
            oss_url = self._upload_audio_to_oss(audio_path)
            if not oss_url:
                return {
                    "success": False,
                    "error": "音频文件上传失败",
                    "transcript": "",
                    "segments": []
                }
            
            # 🔧 步骤2: 调用DashScope ASR API
            result = self._call_dashscope_asr(
                oss_url=oss_url,
                language=language,
                preset_vocabulary_id=preset_vocabulary_id
            )
            
            # 🔧 步骤3: 解析结果时传递fine_grained参数
            if result.get("success"):
                raw_output = result.get("raw_output")
                if raw_output:
                    parsed_result = self._parse_dashscope_result(raw_output, fine_grained=fine_grained)
                    return parsed_result
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 音频转录失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "segments": []
            }
    
    def _upload_audio_to_oss(self, audio_path: str) -> Optional[str]:
        """上传音频文件到OSS"""
        try:
            import oss2
            
            # 从环境变量获取OSS配置
            access_key_id = os.environ.get('OSS_ACCESS_KEY_ID')
            access_key_secret = os.environ.get('OSS_ACCESS_KEY_SECRET')
            endpoint = os.environ.get('OSS_ENDPOINT', 'https://oss-cn-shanghai.aliyuncs.com')
            bucket_name = os.environ.get('OSS_BUCKET_NAME')
            
            if not all([access_key_id, access_key_secret, bucket_name]):
                logger.warning("OSS配置不完整，尝试回退方案")
                return self._fallback_upload_to_oss(audio_path)
            
            # 创建Bucket对象
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            
            # 生成OSS对象名
            file_name = Path(audio_path).name
            timestamp = int(time.time())
            oss_key = f"upload/{timestamp}_{file_name}"
            
            # 上传文件
            logger.info(f"📤 上传音频到OSS: {oss_key}")
            bucket.put_object_from_file(oss_key, audio_path)
            
            # 生成公网访问URL
            oss_url = f"https://{bucket_name}.{endpoint.replace('https://', '')}/{oss_key}"
            logger.info(f"✅ OSS上传成功: {oss_url}")
            
            return oss_url
            
        except ImportError:
            logger.warning("oss2模块未安装，尝试回退方案")
            return self._fallback_upload_to_oss(audio_path)
        except Exception as e:
            logger.error(f"OSS上传失败: {str(e)}")
            return self._fallback_upload_to_oss(audio_path)
    
    def _fallback_upload_to_oss(self, audio_path: str) -> Optional[str]:
        """回退的OSS上传方案"""
        try:
            import oss2
            
            access_key_id = os.environ.get('OSS_ACCESS_KEY_ID')
            access_key_secret = os.environ.get('OSS_ACCESS_KEY_SECRET')
            endpoint = os.environ.get('OSS_ENDPOINT', 'https://oss-cn-shanghai.aliyuncs.com')
            bucket_name = os.environ.get('OSS_BUCKET_NAME')
            
            if not all([access_key_id, access_key_secret, bucket_name]):
                logger.error("❌ OSS配置缺失，无法上传音频文件")
                return None
            
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            
            file_name = Path(audio_path).name
            timestamp = int(time.time())
            oss_key = f"upload/{timestamp}_{file_name}"
            
            logger.info(f"📤 使用oss2库上传: {oss_key}")
            
            with open(audio_path, 'rb') as f:
                bucket.put_object(oss_key, f)
            
            oss_url = f"https://{bucket_name}.{endpoint.replace('https://', '')}/{oss_key}"
            logger.info(f"✅ oss2上传成功: {oss_url}")
            
            return oss_url
            
        except Exception as e:
            error_details = {
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
            
            # 如果是OSS特定错误，提取更多信息
            if hasattr(e, 'status'):
                error_details['status'] = e.status
            if hasattr(e, 'code'):
                error_details['code'] = e.code
            if hasattr(e, 'request_id'):
                error_details['request_id'] = e.request_id
                
            logger.error(f"📤 oss2上传失败: {error_details}")
            return None
    
    def _call_dashscope_asr(
        self, 
        oss_url: str, 
        language: str = "zh",
        preset_vocabulary_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用DashScope ASR API进行语音识别（基于官方文档的paraformer-v2录音文件识别）
        
        官方文档：https://help.aliyun.com/zh/model-studio/paraformer-recorded-speech-recognition-python-sdk
        
        Args:
            oss_url: OSS文件URL（必须是公网可访问的URL）
            language: 语言代码（zh/en/ja/ko等）
            preset_vocabulary_id: 预设词汇表ID
            
        Returns:
            转录结果字典
        """
        try:
            import dashscope
            from dashscope.audio.asr import Transcription
            from http import HTTPStatus
            
            logger.info(f"🎤 开始DashScope录音文件识别")
            logger.info(f"📁 音频URL: {oss_url}")
            logger.info(f"🌐 目标语言: {language}")
            
            # 🔧 根据官方文档配置paraformer-v2参数
            params = {
                'model': 'paraformer-v2',              # 官方推荐：最新多语种模型
                'file_urls': [oss_url],                # 文件URL列表（公网可访问）
                'language_hints': [language],          # 语言提示（提升识别效果）
                
                # 🎯 核心功能参数（时间戳相关）
                'enable_words': True,                  # ✅ 关键：启用词级别时间戳
                'enable_punctuation_prediction': True, # ✅ 官方推荐：标点符号预测
                'enable_inverse_text_normalization': True,  # ✅ 官方推荐：ITN
                
                # 🔧 优化参数
                'enable_disfluency': False,            # 不过滤语气词（保持原始内容）
                'enable_sample_rate_adaptive': True,   # 自动降采样（适配任意采样率）
            }
            
            # 🎯 热词处理 - 使用预设词汇表ID
            if preset_vocabulary_id:
                params["vocabulary_id"] = preset_vocabulary_id
                logger.info(f"🍼 使用婴幼儿奶粉专用热词表: {preset_vocabulary_id}")
            else:
                logger.info("🚫 未指定热词表，使用基础识别")
            
            logger.info(f"🔧 API调用参数: {params}")
            
            # 🔧 使用官方推荐的异步调用方式
            logger.info("📤 提交录音文件识别任务...")
            task_response = Transcription.async_call(**params)
            
            if task_response.status_code != HTTPStatus.OK:
                error_msg = f"任务提交失败: {getattr(task_response, 'message', '未知错误')}"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "transcript": "",
                    "segments": []
                }
            
            # 🔧 获取任务ID并等待完成
            task_id = task_response.output['task_id']
            logger.info(f"📋 任务ID: {task_id}，等待转录完成...")
            
            # 🔧 轮询任务状态
            max_wait_time = 300  # 最大等待时间：5分钟
            poll_interval = 2    # 轮询间隔：2秒
            waited_time = 0
            
            while waited_time < max_wait_time:
                transcribe_response = Transcription.wait(task=task_id)
                
                if transcribe_response.status_code == HTTPStatus.OK:
                    task_status = transcribe_response.output.get('task_status')
                    logger.info(f"🔄 任务状态: {task_status}")
                    
                    if task_status == 'SUCCEEDED':
                        break
                    elif task_status in ['FAILED', 'CANCELED']:
                        error_msg = f"任务失败: {task_status}"
                        logger.error(f"❌ {error_msg}")
                        return {
                            "success": False,
                            "error": error_msg,
                            "transcript": "",
                            "segments": []
                        }
                
                time.sleep(poll_interval)
                waited_time += poll_interval
            
            # 检查响应状态
            if transcribe_response.status_code == HTTPStatus.OK:
                logger.info("🎉 录音文件识别成功！开始解析结果...")
                
                # 解析识别结果
                result = self._parse_dashscope_result(transcribe_response.output)
                
                # 记录成功统计
                if result.get("success"):
                    segments_count = len(result.get("segments", []))
                    text_length = len(result.get("transcript", ""))
                    logger.info(f"📊 识别统计: 文本长度={text_length}字符, 时间戳片段={segments_count}个")
                
                return result
                
            else:
                # 处理识别失败
                error_msg = f"DashScope录音文件识别失败: {getattr(transcribe_response, 'message', '未知错误')}"
                status_code = getattr(transcribe_response, 'status_code', 'unknown')
                
                logger.error(f"❌ {error_msg} (状态码: {status_code})")
                
                return {
                    "success": False,
                    "error": f"{error_msg} (状态码: {status_code})",
                    "transcript": "",
                    "segments": [],
                    "error_type": "api_error",
                    "status_code": status_code
                }
                
        except ImportError as e:
            error_msg = f"DashScope SDK导入失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": f"{error_msg}。请安装最新版DashScope SDK: pip install dashscope --upgrade",
                "transcript": "",
                "segments": [],
                "error_type": "import_error"
            }
        except Exception as e:
            logger.error(f"❌ DashScope ASR调用失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
                "segments": [],
                "error_type": "api_error"
            }
    
    def _parse_dashscope_result(self, output: Dict[str, Any], fine_grained: bool = False) -> Dict[str, Any]:
        """
        解析DashScope转录结果 - 修复版本
        
        Args:
            output: DashScope API返回的output字段
            fine_grained: 是否使用精细化时间戳（词级别）
            
        Returns:
            标准化的转录结果
        """
        try:
            # 提取转录结果
            results = output.get('results', [])
            if not results:
                logger.warning("⚠️ 转录结果为空")
                return {
                    "success": False,
                    "error": "转录结果为空",
                    "transcript": "",
                    "segments": []
                }
            
            # 合并所有转录文本
            full_transcript = ""
            segments = []
            
            for result in results:
                # 🔧 关键修复：检查transcription_url而不是transcription字段
                transcription_url = result.get('transcription_url')
                if not transcription_url:
                    logger.warning(f"⚠️ 未找到transcription_url: {result}")
                    continue
                
                # 🔧 从transcription_url下载实际的转录结果
                logger.info(f"📥 正在下载转录结果: {transcription_url}")
                transcription_data = self._download_transcription_result(transcription_url)
                
                if not transcription_data:
                    logger.warning("⚠️ 下载转录结果失败")
                    continue
                
                # 🔧 解析下载的转录数据 - 修复版本
                # DashScope实际返回格式: transcripts数组
                transcripts = transcription_data.get('transcripts', [])
                
                for transcript in transcripts:
                    # 提取完整文本
                    transcript_text = transcript.get('text', '')
                    full_transcript += transcript_text
                    
                    # 🎯 根据fine_grained参数选择时间戳粒度
                    if fine_grained:
                        # 精细化模式：优先使用词级时间戳
                        words = transcript.get('words', [])
                        if words:
                            self._create_fine_grained_segments(words, segments)
                        else:
                            # 降级为句子级时间戳
                            sentences = transcript.get('sentences', [])
                            self._create_sentence_segments(sentences, segments)
                    else:
                        # 标准模式：使用句子级时间戳
                        sentences = transcript.get('sentences', [])
                        if sentences:
                            self._create_sentence_segments(sentences, segments)
                        else:
                            # 降级为词级时间戳
                            words = transcript.get('words', [])
                            self._create_fine_grained_segments(words, segments)
            
            # 清理转录文本
            full_transcript = full_transcript.strip()
            
            logger.info(f"✅ 转录解析完成: 文本长度={len(full_transcript)}, 片段数={len(segments)}")
            
            return {
                "success": True,
                "transcript": full_transcript,
                "segments": segments,
                "raw_output": output
            }
            
        except Exception as e:
            logger.error(f"❌ 解析转录结果失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"解析转录结果失败: {str(e)}",
                "transcript": "",
                "segments": []
            }
    
    def _download_transcription_result(self, transcription_url: str) -> Optional[Dict[str, Any]]:
        """
        从transcription_url下载实际的转录结果
        
        Args:
            transcription_url: DashScope返回的转录结果URL
            
        Returns:
            转录结果字典，失败时返回None
        """
        try:
            import requests
            import json
            
            # 下载转录结果
            response = requests.get(transcription_url, timeout=30)
            response.raise_for_status()
            
            # 解析JSON
            transcription_data = response.json()
            logger.info(f"✅ 转录结果下载成功，数据大小: {len(response.text)} 字符")
            
            return transcription_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 下载转录结果网络错误: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ 转录结果JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 下载转录结果失败: {e}")
            return None
    
    def _create_sentence_segments(self, sentences: List[Dict], segments: List[Dict]):
        """创建句子级时间戳片段"""
        for sentence in sentences:
            sentence_text = sentence.get('text', '').strip()
            if sentence_text:
                segments.append({
                    'text': sentence_text,
                    'start': sentence.get('begin_time', 0) / 1000,  # 转换为秒
                    'end': sentence.get('end_time', 0) / 1000,
                    'confidence': sentence.get('confidence', 1.0)
                })

    def _create_fine_grained_segments(self, words: List[Dict], segments: List[Dict]):
        """创建词级精细化时间戳片段"""
        current_segment = {'words': [], 'start': None, 'end': None}
        
        for word in words:
            word_text = word.get('text', '')
            word_start = word.get('begin_time', 0) / 1000
            word_end = word.get('end_time', 0) / 1000
            
            if current_segment['start'] is None:
                current_segment['start'] = word_start
            
            current_segment['words'].append(word_text)
            current_segment['end'] = word_end
            
            # 🎯 精细化分割策略：3个词或遇到标点符号创建一个片段
            if (len(current_segment['words']) >= 3 or 
                word_text.endswith(('。', '！', '？', '，', '；', '、', '：'))):
                segment_text = ''.join(current_segment['words']).strip()
                if segment_text:
                    segments.append({
                        'text': segment_text,
                        'start': current_segment['start'],
                        'end': current_segment['end'],
                        'confidence': 1.0
                    })
                current_segment = {'words': [], 'start': None, 'end': None}
        
        # 处理最后一个片段
        if current_segment['words']:
            segment_text = ''.join(current_segment['words']).strip()
            if segment_text:
                segments.append({
                    'text': segment_text,
                    'start': current_segment['start'],
                    'end': current_segment['end'],
                    'confidence': 1.0
                })

    def _format_timestamp(self, milliseconds) -> str:
        """
        将毫秒转换为格式化的时间戳
        
        Args:
            milliseconds: 毫秒数（int或float）
            
        Returns:
            格式化的时间戳
        """
        # 确保输入是数字类型并转换为整数
        ms = int(float(milliseconds)) if milliseconds else 0
        
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        seconds = seconds % 60
        ms_remainder = ms % 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms_remainder:03d}" 