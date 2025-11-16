"""
视频切片AI分析器模块
专门分析已有视频切片，提取标签并分类到业务模块

核心功能：
- Qwen视觉分析：物体、场景、情绪、品牌识别
- DashScope音频转录：高精度语音识别  
- DeepSeek语义分析：转录内容理解和业务分类
"""

import os
import sys
import json
import logging
import tempfile
import requests
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path
import time
try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except ImportError as e:
    print(f"❌ 缺少依赖包: {e}")
    print("💡 请运行: uv add opencv-python numpy")
import re

# 添加主项目路径，以便导入主程序的分析器
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir / "streamlit_app"))

from config.slice_config import (
    get_api_keys, get_models_config, get_core_brands, 
    get_brand_trigger_keywords, get_analysis_prompts, get_quality_control, get_output_config,
    get_default_model_selection
)

# 导入统一提示词管理
from config.prompt_templates import get_unified_prompt, get_prompt_manager

logger = logging.getLogger(__name__)

class QwenVideoAnalyzer:
    """Qwen视觉分析器 - 独立实现"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model_config = get_models_config()["qwen"]
        
    def analyze_video_frames(self, video_path: str, prompt: str) -> Dict[str, Any]:
        """分析视频帧，输出原始格式，不进行即时翻译"""
        try:
            # 使用优化的帧提取策略
            frames = self._extract_frames_optimized(video_path)
            if not frames:
                return {"success": False, "error": "无法提取视频帧"}
            
            # 编码帧为base64
            encoded_frames = []
            for frame in frames:  # 使用所有提取的帧
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                encoded_frame = base64.b64encode(buffer).decode('utf-8')
                encoded_frames.append(encoded_frame)
            
            logger.info(f"📸 提取了 {len(encoded_frames)} 帧用于分析")
            
            # 调用Qwen API
            response = self._call_qwen_api(encoded_frames, prompt)
            
            if response.get("success"):
                raw_output = response["content"]
                
                # 🔥 关键修复：处理Qwen API返回的列表格式
                logger.info("📋 Qwen分析完成，保留原始格式（翻译将在后处理阶段统一进行）")
                logger.info(f"📋 Qwen原始输出: {str(raw_output)[:200]}...")
                
                # 提取文本内容
                extracted_text = self._extract_qwen_text_content(raw_output)
                
                # 只做基本格式清理，不翻译
                cleaned_output = self._clean_qwen_output(extracted_text)
                
                logger.info(f"📋 格式清理后输出: {cleaned_output[:200]}...")
                
                return {
                    "success": True,
                    "analysis_result": cleaned_output,  # 返回清理后但未翻译的结果
                    "raw_output": raw_output,           # 保留原始输出用于调试
                    "confidence": 0.85,
                    "model_used": "qwen-vl-max-latest",
                    "method_used": "multi_frame_raw_output"
                }
            else:
                return {"success": False, "error": response.get("error", "API调用失败")}
                
        except Exception as e:
            logger.error(f"Qwen视频分析失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _extract_qwen_text_content(self, raw_output) -> str:
        """提取Qwen API返回的文本内容"""
        try:
            # 如果是列表格式
            if isinstance(raw_output, list):
                if len(raw_output) > 0 and isinstance(raw_output[0], dict):
                    # 提取text字段
                    if 'text' in raw_output[0]:
                        return raw_output[0]['text']
                    elif 'content' in raw_output[0]:
                        return raw_output[0]['content']
                # 如果列表中是字符串
                elif len(raw_output) > 0 and isinstance(raw_output[0], str):
                    return raw_output[0]
            
            # 如果是字典格式
            elif isinstance(raw_output, dict):
                if 'text' in raw_output:
                    return raw_output['text']
                elif 'content' in raw_output:
                    return raw_output['content']
            
            # 如果已经是字符串
            elif isinstance(raw_output, str):
                return raw_output
            
            # 默认情况：转换为字符串
            logger.warning(f"⚠️ 未知的Qwen输出格式，转换为字符串: {type(raw_output)}")
            return str(raw_output)
                
        except Exception as e:
            logger.error(f"❌ 提取Qwen文本内容失败: {e}")
            return str(raw_output)
    
    def _clean_qwen_output(self, text: str) -> str:
        """清理Qwen输出格式，移除方括号和多余符号"""
        if not text:
            return text
        
        # 使用正则表达式进行格式清理
        import re
        
        try:
            # 先尝试解析JSON格式
            import json
            if text.strip().startswith('{') and text.strip().endswith('}'):
                try:
                    data = json.loads(text)
                    # 清理所有字段格式
                    for key, value in data.items():
                        if isinstance(value, str):
                            # 去除方括号和多余符号
                            value = re.sub(r'^\[([^\]]+)\]$', r'\1', value.strip())
                            value = value.strip().strip('"').strip("'").strip()
                            data[key] = value
                    
                    # 返回格式化的JSON
                    return json.dumps(data, ensure_ascii=False, separators=(',', ': '))
                except json.JSONDecodeError:
                    pass
        except:
            pass
        
        # 如果不是JSON，按行处理
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # 移除方括号和引号
                value = value.replace('[', '').replace(']', '')
                value = value.replace('"', '').replace("'", '')
                
                # 清理逗号
                if value.startswith(','):
                    value = value[1:]
                if value.endswith(','):
                    value = value[:-1]
                
                # 清理空格
                value = ' '.join(value.split())
                
                # 特殊处理
                if value.lower().strip() in ['无', 'none', 'null', '']:
                    value = '无'
                
                cleaned_lines.append(f"{key}: {value}")
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _get_deepseek_api_key(self) -> str:
        """获取DeepSeek API密钥"""
        try:
            import os
            # 首先尝试环境变量
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if api_key:
                return api_key
            
            # 然后尝试从配置文件读取
            config_path = Path(__file__).parent.parent / "config" / "env_config.txt"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("DEEPSEEK_API_KEY="):
                            return line.split("=", 1)[1].strip()
            
            logger.error("❌ 未找到DeepSeek API密钥")
            return ""
            
        except Exception as e:
            logger.error(f"❌ 获取DeepSeek API密钥失败: {e}")
            return ""
    
    def _extract_frames_optimized(self, video_path: str) -> List:
        """优化的视频帧提取策略 - 针对短视频片段优化"""
        try:
            cap = cv2.VideoCapture(video_path)
            frames = []
            
            # 获取视频基本信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"📹 视频信息: {total_frames}帧, {fps:.1f}fps, {duration:.1f}秒")
            
            if total_frames == 0:
                cap.release()
                return frames
            
            # 根据视频长度动态选择帧数和策略
            if duration <= 3:  # 极短视频 (≤3秒)
                frames = self._extract_short_video_frames(cap, total_frames, fps)
            elif duration <= 10:  # 短视频 (3-10秒)
                frames = self._extract_medium_video_frames(cap, total_frames, fps)
            else:  # 较长视频 (>10秒)
                frames = self._extract_long_video_frames(cap, total_frames, fps)
            
            cap.release()
            
            # 帧质量评估和过滤
            frames = self._filter_quality_frames(frames)
            
            logger.info(f"✅ 最终提取 {len(frames)} 个高质量帧")
            return frames
            
        except Exception as e:
            logger.error(f"优化帧提取失败: {str(e)}")
            return []
    
    def _extract_short_video_frames(self, cap, total_frames: int, fps: float) -> List:
        """提取极短视频的帧 (≤3秒) - 密集采样"""
        frames = []
        
        # 对于极短视频，每隔几帧就采样一次，确保捕捉到所有重要变化
        step = max(1, int(total_frames / 8))  # 最多8帧
        
        for i in range(0, total_frames, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret and frame is not None:
                frames.append(frame)
        
        # 确保包含首尾帧
        if total_frames > 1:
            cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
            ret, frame = cap.read()
            if ret and frame is not None:
                frames.append(frame)
        
        return frames[:6]  # 最多6帧
    
    def _extract_medium_video_frames(self, cap, total_frames: int, fps: float) -> List:
        """提取短视频的帧 (3-10秒) - 关键时刻采样"""
        frames = []
        
        # 关键时刻点：开始、1/4、1/2、3/4、结束
        key_positions = [0, 0.25, 0.5, 0.75, 1.0]
        
        for pos in key_positions:
            frame_idx = int(pos * (total_frames - 1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret and frame is not None:
                frames.append(frame)
        
        return frames
    
    def _extract_long_video_frames(self, cap, total_frames: int, fps: float) -> List:
        """提取较长视频的帧 (>10秒) - 均匀采样"""
        frames = []
        
        # 均匀选择4个关键帧
        indices = [int(i * total_frames / 4) for i in range(4)]
        
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret and frame is not None:
                frames.append(frame)
        
        return frames
    
    def _filter_quality_frames(self, frames: List) -> List:
        """过滤和评估帧质量"""
        if not frames:
            return frames
        
        quality_frames = []
        
        for frame in frames:
            # 检查帧是否有效
            if frame is None or frame.size == 0:
                continue
            
            # 计算帧的质量指标
            quality_score = self._calculate_frame_quality(frame)
            
            # 只保留质量足够的帧
            if quality_score > 0.3:  # 质量阈值
                quality_frames.append(frame)
        
        # 如果所有帧都被过滤掉了，保留原始的第一帧
        if not quality_frames and frames:
            quality_frames = [frames[0]]
        
        # 限制最大帧数（避免API调用过大）
        return quality_frames[:5]
    
    def _calculate_frame_quality(self, frame) -> float:
        """计算帧的质量分数"""
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 计算拉普拉斯方差（清晰度指标）
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 计算亮度分布（避免过暗或过亮）
            brightness = gray.mean()
            brightness_score = 1.0 - abs(brightness - 128) / 128
            
            # 计算对比度
            contrast = gray.std()
            contrast_score = min(contrast / 64, 1.0)
            
            # 综合质量分数
            quality = (
                min(laplacian_var / 1000, 1.0) * 0.5 +  # 清晰度权重50%
                brightness_score * 0.3 +                 # 亮度权重30%
                contrast_score * 0.2                     # 对比度权重20%
            )
            
            return quality
            
        except Exception as e:
            logger.warning(f"帧质量计算失败: {e}")
            return 0.5  # 默认中等质量
    
    def _call_qwen_api(self, encoded_frames: List[str], prompt: str) -> Dict[str, Any]:
        """调用Qwen API - 支持重试机制"""
        import time
        
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        
        # 从配置获取参数
        max_retries = self.model_config.get("max_retries", 5)
        timeout = self.model_config.get("timeout", 90)
        retry_delay = self.model_config.get("retry_delay", 2)
        
        # 构建消息内容
        content = [{"text": prompt}]
        for frame in encoded_frames:
            content.append({
                "image": f"data:image/jpeg;base64,{frame}"
            })
        
        payload = {
            "model": self.model_config["model_name"],
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            },
            "parameters": {
                "max_tokens": 2000
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 实现重试机制
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Qwen API调用尝试 {attempt + 1}/{max_retries} (超时: {timeout}s)")
                
                response = requests.post(url, json=payload, headers=headers, timeout=timeout)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("output", {}).get("choices"):
                        content = result["output"]["choices"][0]["message"]["content"]
                        logger.info(f"✅ Qwen API调用成功 (尝试次数: {attempt + 1})")
                        return {"success": True, "content": content}
                    else:
                        logger.warning(f"⚠️ Qwen API返回格式错误 (尝试 {attempt + 1})")
                        if attempt < max_retries - 1:
                            logger.info(f"⏳ 等待 {retry_delay} 秒后重试...")
                            time.sleep(retry_delay)
                            continue
                        return {"success": False, "error": "API返回格式错误"}
                else:
                    logger.warning(f"⚠️ Qwen API调用失败: {response.status_code} (尝试 {attempt + 1})")
                    if attempt < max_retries - 1:
                        logger.info(f"⏳ 等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        continue
                    return {"success": False, "error": f"API调用失败: {response.status_code}"}
                    
            except requests.exceptions.Timeout:
                logger.error(f"❌ Qwen API超时 (尝试 {attempt + 1}/{max_retries}, 超时: {timeout}s)")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ 网络超时，等待 {retry_delay * (attempt + 1)} 秒后重试...")
                    time.sleep(retry_delay * (attempt + 1))  # 递增等待时间
                    continue
                return {"success": False, "error": f"API超时 (已重试{max_retries}次)"}
                
            except Exception as e:
                logger.error(f"❌ Qwen API异常: {str(e)} (尝试 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ 异常后等待 {retry_delay * (attempt + 1)} 秒后重试...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": f"所有 {max_retries} 次重试都失败"}
    
class GeminiVideoAnalyzer:
    """Google Gemini 2.5 Pro视觉分析器 - 通过OpenRouter API调用"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model_config = get_models_config()["gemini"]
        self.gemini_model = self.model_config["model_name"]  # 设置gemini_model属性
        
        # 🆕 添加 OpenRouter API 配置
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_api_key:
            logger.warning("⚠️ OPENROUTER_API_KEY 未配置，将回退到原有 Google API")
            self.use_openrouter = False
        else:
            self.use_openrouter = True
            logger.info("✅ 使用 OpenRouter API 调用 Gemini 2.5 Pro")
        
        # 🚀 新增：智能帧提取器配置
        self.use_smart_extractor = self.model_config.get("use_smart_extractor", False)
        if self.use_smart_extractor:
            try:
                from smart_frame_extractor import SmartFrameExtractor
                self.smart_extractor = SmartFrameExtractor()
                logger.info("✅ 智能帧提取器已启用（内容变化检测）")
            except ImportError:
                logger.warning("⚠️ 智能帧提取器模块未找到，使用标准提取方式")
                self.use_smart_extractor = False
                self.smart_extractor = None
        else:
            self.smart_extractor = None
            logger.info("📊 使用标准帧提取方式（已优化）")
    
    def analyze_video_frames(self, video_path: str, prompt: str) -> Dict[str, Any]:
        """使用Gemini分析视频，优先使用OpenRouter API"""
        
        try:
            # 🔧 **关键修正**：使用传入的统一prompt，不再硬编码
            logger.info(f"🎯 Gemini收到prompt，长度: {len(prompt)}字符")
            logger.info(f"📋 Gemini接收的prompt开头: {prompt[:300]}...")
            
            # 🔍 **调试**：检查是否为专用prompt
            if "Gemini增强指导" in prompt:
                logger.info("✅ 确认收到Gemini专用prompt（包含增强指导）")
            elif "行为/交互" in prompt:
                logger.info("⚠️ 收到通用prompt（通用版本）")
            else:
                logger.warning("❓ 收到未知格式的prompt")
            
            logger.info(f"📹 Gemini开始分析视频: {video_path}")
            
            # 🆕 优先使用 OpenRouter API
            if self.use_openrouter:
                response = self._call_gemini_openrouter_api(video_path, prompt)
            else:
                # 回退到原有的 Google API（需要导入库）
                response = self._call_gemini_google_api_fallback(video_path, prompt)
            
            if response.get("success"):
                raw_output = response["content"]
                
                # 🔥 简化处理：直接返回原始输出，不做复杂解析
                logger.info("📋 Gemini分析完成，保留原始格式（翻译将在后处理阶段统一进行）")
                logger.info(f"📋 Gemini原始输出: {raw_output[:200]}...")
                
                # 只做基本格式清理，保持原始内容
                cleaned_output = raw_output.strip()
                
                return {
                    "success": True,
                    "analysis_result": cleaned_output,  # 直接返回清理后的结果
                    "raw_output": raw_output,           # 保留原始输出用于调试
                    "confidence": 0.90,
                    "model_used": "gemini-2.5-pro",
                    "method_used": "openrouter_api" if self.use_openrouter else "google_api_fallback",
                    "prompt_type": "gemini_specialized" if "Gemini增强指导" in prompt else "universal"
                }
            else:
                # 直接报错，不使用回退方法
                error_msg = response.get("error", "Gemini API调用失败")
                logger.error(f"❌ Gemini API失败: {error_msg}")
                raise Exception(f"Gemini API失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"❌ Gemini视频分析失败: {str(e)}")
            raise e
    


    def _call_gemini_openrouter_api(self, video_path: str, prompt: str) -> Dict[str, Any]:
        """🆕 使用 OpenRouter API 调用 Gemini 2.5 Pro"""
        try:
            import requests
            import json
            import base64
            
            logger.info("🚀 使用 OpenRouter API 调用 Gemini 2.5 Pro")
            
            # 🎯 根据配置选择帧提取方式
            if self.use_smart_extractor and self.smart_extractor:
                logger.info("🧠 使用智能帧提取器（内容变化检测）")
                key_frames_data = self.smart_extractor.extract_key_frames(video_path)
                if key_frames_data:
                    frames = [frame_data["frame"] for frame_data in key_frames_data]
                    logger.info(f"🎯 智能提取了 {len(frames)} 个关键帧（基于内容变化）")
                else:
                    logger.warning("⚠️ 智能帧提取失败，回退到标准方式")
                    frames = self._extract_frames_optimized(video_path)
            else:
                # 使用优化的标准提取方式
                frames = self._extract_frames_optimized(video_path)
                
            if not frames:
                return {"success": False, "error": "无法从视频中提取帧"}
            
            # 将帧转换为 base64 编码
            encoded_frames = []
            for i, frame in enumerate(frames):
                try:
                    import cv2  # type: ignore
                    # 将帧编码为 JPEG
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    encoded_frames.append(frame_base64)
                    logger.info(f"✅ 帧 {i+1} 编码完成")
                except Exception as e:
                    logger.warning(f"⚠️ 帧 {i+1} 编码失败: {e}")
                    continue
            
            if not encoded_frames:
                return {"success": False, "error": "帧编码失败"}
            
            # 构建 OpenRouter API 请求
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://ai-video-master.com",  # Optional site URL
                "X-Title": "AI Video Master",  # Optional site title
            }
            
            # 构建消息内容：prompt + 图像
            content = [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
            
            # 添加图像帧
            for i, frame_base64 in enumerate(encoded_frames):
                image_content = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{frame_base64}"
                    }
                }
                content.append(image_content)  # type: ignore
                logger.info(f"📸 添加帧 {i+1} 到请求")
            
            payload = {
                "model": "google/gemini-2.5-pro",
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            }
            
            logger.info(f"📤 发送 OpenRouter API 请求，包含 {len(encoded_frames)} 个帧")
            
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("choices") and result["choices"][0].get("message", {}).get("content"):
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"✅ OpenRouter API 调用成功，响应长度: {len(content)}字符")
                    return {"success": True, "content": content}
                else:
                    return {"success": False, "error": "OpenRouter API返回格式错误"}
            else:
                error_msg = f"OpenRouter API调用失败: {response.status_code}"
                if response.text:
                    error_msg += f", 响应: {response.text[:200]}"
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"❌ OpenRouter API调用异常: {str(e)}")
            return {"success": False, "error": str(e)}

    def _call_gemini_google_api_fallback(self, video_path: str, prompt: str) -> Dict[str, Any]:
        """🆕 真正的Google原生API调用"""
        try:
            logger.info("🇬 使用Google原生API调用Gemini 2.5 Pro")
            
            # 方法1：尝试新版Google Gen AI SDK
            try:
                import google.generativeai as genai  # type: ignore
                
                # 配置API密钥
                genai.configure(api_key=self.api_key)
                
                # 创建模型
                model = genai.GenerativeModel("gemini-2.5-pro")
                
                # 提取视频帧并转换为PIL Image
                frames = self._extract_frames_optimized(video_path)
                if not frames:
                    return {"success": False, "error": "无法提取视频帧"}
                
                # 转换帧为PIL Image格式
                pil_images = []
                for frame in frames:
                    import cv2  # type: ignore
                    from PIL import Image  # type: ignore
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    pil_images.append(pil_image)
                
                logger.info(f"📸 Google API准备分析 {len(pil_images)} 个帧")
                
                # 构建内容：prompt + 图像
                content = [prompt]
                content.extend(pil_images)
                
                # 生成配置
                generation_config = {
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 2000,
                }
                
                # 安全设置
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                
                # 调用Google API
                response = model.generate_content(
                    content,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                if response.text:
                    logger.info(f"✅ Google原生API调用成功，响应长度: {len(response.text)}字符")
                    return {"success": True, "content": response.text}
                else:
                    return {"success": False, "error": "Google API返回空内容"}
                    
            except ImportError:
                logger.warning("⚠️ Google GenerativeAI SDK未安装，回退到帧分析")
                return self._call_gemini_frame_fallback(video_path, prompt)
            except Exception as e:
                logger.warning(f"⚠️ Google原生API调用失败: {str(e)}")
                logger.info("🔄 回退到帧分析方法")
                return self._call_gemini_frame_fallback(video_path, prompt)
                
        except Exception as e:
            logger.error(f"❌ Google API整体调用失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _extract_frames_optimized(self, video_path: str) -> List:
        """优化的视频帧提取策略 - 专为Gemini优化，提供更全面的视频分析"""
        try:
            import cv2  # type: ignore
            cap = cv2.VideoCapture(video_path)
            frames = []
            
            # 获取视频基本信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"📹 Gemini视频信息: {total_frames}帧, {fps:.1f}fps, {duration:.1f}秒")
            
            if total_frames == 0:
                cap.release()
                return frames
            
            # 🚀 优化后的Gemini帧提取策略：更全面的覆盖
            if duration <= 2:  # 极短视频：密集采样
                # 每0.3秒采样一次，确保捕捉所有变化
                frame_interval = max(1, int(fps * 0.3))
                for i in range(0, total_frames, frame_interval):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        frames.append(frame)
                # 确保包含最后一帧
                if total_frames > 1:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        frames.append(frame)
                frames = frames[:6]  # 极短视频最多6帧
                
            elif duration <= 8:  # 短视频：关键时刻采样
                # 更密集的关键时刻点
                key_positions = [0, 0.15, 0.35, 0.55, 0.75, 0.95]
                for pos in key_positions:
                    frame_idx = int(pos * (total_frames - 1))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        frames.append(frame)
                        
            elif duration <= 20:  # 中等视频：混合策略
                # 关键时刻 + 内容变化检测
                key_positions = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
                for pos in key_positions:
                    frame_idx = int(pos * (total_frames - 1))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        frames.append(frame)
                        
                # 额外采样中间变化点
                mid_points = [0.1, 0.3, 0.5, 0.7, 0.9]
                for pos in mid_points:
                    frame_idx = int(pos * (total_frames - 1))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        frames.append(frame)
                        
            else:  # 长视频：智能采样
                # 分段策略：将视频分成8段，每段取代表帧
                segments = 8
                for i in range(segments):
                    # 每段取开始、中间、结束三个点
                    segment_start = i / segments
                    segment_mid = (i + 0.5) / segments
                    segment_end = (i + 1) / segments
                    
                    for pos in [segment_start, segment_mid, segment_end]:
                        if pos <= 1.0:
                            frame_idx = int(pos * (total_frames - 1))
                            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                frames.append(frame)
            
            cap.release()
            
            # 🔧 优化质量过滤：更智能的帧选择
            frames = self._filter_frames_for_gemini_enhanced(frames)
            
            logger.info(f"✅ Gemini优化后提取 {len(frames)} 个高质量帧")
            return frames
            
        except Exception as e:
            logger.error(f"Gemini帧提取失败: {str(e)}")
            return []
    
    def _filter_frames_for_gemini_enhanced(self, frames: List) -> List:
        """增强版Gemini帧过滤 - 智能选择最有代表性的帧"""
        if not frames:
            return frames
        
        # 🎯 第一步：质量评估
        frame_scores = []
        for i, frame in enumerate(frames):
            if frame is None or frame.size == 0:
                continue
            
            quality_score = self._calculate_gemini_frame_quality(frame)
            if quality_score > 0.3:  # 降低质量阈值，保留更多帧
                frame_scores.append((i, frame, quality_score))
        
        if not frame_scores:
            return [frames[0]] if frames else []
        
        # 🎯 第二步：多样性选择 - 避免选择过于相似的帧
        selected_frames = []
        frame_scores.sort(key=lambda x: x[2], reverse=True)  # 按质量排序
        
        for i, frame, score in frame_scores:
            if len(selected_frames) >= 8:  # 🚀 增加到最多8帧
                break
                
            # 检查与已选择帧的相似度
            is_similar = False
            for selected_frame in selected_frames:
                similarity = self._calculate_frame_similarity(frame, selected_frame)
                if similarity > 0.85:  # 如果太相似就跳过
                    is_similar = True
                    break
            
            if not is_similar:
                selected_frames.append(frame)
        
        # 🎯 第三步：确保时间分布均匀
        if len(selected_frames) < 3 and len(frame_scores) >= 3:
            # 强制选择首、中、尾三帧确保时间覆盖
            indices = [0, len(frame_scores)//2, len(frame_scores)-1]
            for idx in indices:
                frame = frame_scores[idx][1]
                if frame not in selected_frames:
                    selected_frames.append(frame)
        
        logger.info(f"📊 Gemini帧过滤：{len(frames)}帧 → {len(selected_frames)}帧（多样性选择）")
        return selected_frames[:8]  # 最终限制为8帧
    
    def _calculate_frame_similarity(self, frame1, frame2) -> float:
        """计算两帧之间的相似度"""
        try:
            import cv2  # type: ignore
            
            # 转换为灰度图并调整大小以加速计算
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            
            # 调整到相同尺寸
            h, w = 64, 64
            gray1 = cv2.resize(gray1, (w, h))
            gray2 = cv2.resize(gray2, (w, h))
            
            # 计算直方图相关性
            hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
            
            correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return correlation
            
        except Exception as e:
            logger.warning(f"帧相似度计算失败: {e}")
            return 0.5
    
    def _calculate_gemini_frame_quality(self, frame) -> float:
        """计算适合Gemini的帧质量分数"""
        try:
            import cv2  # type: ignore
            # 转换为灰度图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 清晰度检测（拉普拉斯算子）
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness = min(laplacian_var / 1500, 1.0)  # 更高的清晰度要求
            
            # 信息密度检测（边缘检测）
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.count_nonzero(edges) / edges.size
            
            # 亮度均衡
            brightness = gray.mean()
            brightness_score = 1.0 - abs(brightness - 128) / 128
            
            # Gemini偏好的综合评分
            quality = (
                sharpness * 0.4 +           # 清晰度权重40%
                edge_density * 0.4 +        # 信息密度权重40%
                brightness_score * 0.2      # 亮度权重20%
            )
            
            return quality
            
        except Exception as e:
            logger.warning(f"Gemini帧质量计算失败: {e}")
            return 0.5

    def _call_gemini_frame_fallback(self, video_path: str, prompt: str) -> Dict[str, Any]:
        """回退方法：使用帧分析（保持原有逻辑作为备用）"""
        try:
            logger.warning("🔄 Gemini视频API失败，回退到帧分析方法")
            
            # 使用原有的帧提取方法
            frames = self._extract_frames_optimized(video_path)
            if not frames:
                return {"success": False, "error": "无法提取视频帧"}
            
            # 转换帧为PIL Image格式
            pil_images = []
            for frame in frames:
                import cv2  # type: ignore
                from PIL import Image  # type: ignore
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                pil_images.append(pil_image)
            
            # 使用旧版图片分析API
            return self._call_gemini_api_fallback(pil_images, prompt)
            
        except Exception as e:
            logger.error(f"Gemini帧分析回退也失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _call_gemini_api_fallback(self, pil_images: List, prompt: str) -> Dict[str, Any]:
        """回退到旧版Gemini API（图片分析）"""
        try:
            import google.generativeai as genai  # type: ignore
            
            # 配置Gemini API（旧版方式）
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-2.5-pro")
            
            # 构建消息内容
            content = [prompt]
            content.extend(pil_images)
            
            # 生成配置
            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2000,
            }
            
            # 调用旧版API
            response = model.generate_content(
                content, 
                generation_config=generation_config,
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            )
            
            if response.text:
                return {"success": True, "content": response.text}
            else:
                return {"success": False, "error": "Gemini API返回空内容"}
                
        except Exception as e:
            logger.error(f"Gemini回退API调用异常: {str(e)}")
            return {"success": False, "error": str(e)}


    
    def _clean_deepseek_output(self, text: str) -> str:
        """清理DeepSeek输出格式，移除方括号和多余符号"""
        if not text:
            return text
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # 移除方括号和引号
                value = value.replace('[', '').replace(']', '')
                value = value.replace('"', '').replace("'", '')
                
                # 清理逗号
                if value.startswith(','):
                    value = value[1:]
                if value.endswith(','):
                    value = value[:-1]
                
                # 清理空格
                value = ' '.join(value.split())
                
                # 特殊处理
                if value.lower().strip() in ['无', 'none', 'null', '']:
                    value = '无'
                
                cleaned_lines.append(f"{key}: {value}")
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _get_deepseek_api_key(self) -> str:
        """获取DeepSeek API密钥"""
        import os
        from pathlib import Path
        
        # 1. 从环境变量获取
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            return api_key
        
        # 2. 从配置文件获取
        config_paths = [
            Path(__file__).parent.parent.parent / "feishu_pool" / ".env",
            Path(__file__).parent.parent / "config" / "env_config.txt"
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip().startswith('DEEPSEEK_API_KEY='):
                                api_key = line.split('=', 1)[1].strip()
                                # 移除引号
                                if api_key.startswith('"') and api_key.endswith('"'):
                                    api_key = api_key[1:-1]
                                elif api_key.startswith("'") and api_key.endswith("'"):
                                    api_key = api_key[1:-1]
                                return api_key
                except Exception:
                    continue
        
        return ""

    def _clean_gemini_raw_output(self, raw_output: str) -> str:
        """清理Gemini原始输出格式，统一格式规范，不进行翻译"""
        try:
            # 基础清理：去除多余空白和换行
            cleaned = raw_output.strip()
            
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(0)
            
            # 🔧 使用统一的字段清理方法
            def clean_field_format(value):
                if isinstance(value, str):
                    # 移除各种方括号和引号
                    cleaned = value.replace('[', '').replace(']', '')
                    cleaned = cleaned.replace('"', '').replace("'", '')
                    if cleaned.startswith(','):
                        cleaned = cleaned[1:]
                    if cleaned.endswith(','):
                        cleaned = cleaned[:-1]
                    cleaned = ' '.join(cleaned.split())
                    if cleaned.lower().strip() in ['无', 'none', 'null', '', '没有', '未知']:
                        return '无'
                    return cleaned.strip()
                return value
            
            # 解析和重新格式化JSON
            try:
                import json
                data = json.loads(cleaned)
                
                # 清理所有字段格式
                for key, value in data.items():
                    if isinstance(value, str):
                        data[key] = clean_field_format(value)
                    elif isinstance(value, list):
                        data[key] = [clean_field_format(item) if isinstance(item, str) else item for item in value]
                
                # 返回格式化的JSON
                return json.dumps(data, ensure_ascii=False, separators=(',', ': '))
                
            except json.JSONDecodeError:
                logger.warning("⚠️ JSON解析失败，返回文本清理结果")
                # 如果JSON解析失败，进行文本级别的格式清理
                cleaned = re.sub(r':\s*\["([^"]+)"\]', r': "\1"', cleaned)  # [content] -> content
                cleaned = re.sub(r':\s*\[([^\]]+)\]', r': "\1"', cleaned)   # 去除方括号
                return cleaned
                
        except Exception as e:
            logger.warning(f"⚠️ 格式清理失败: {e}，返回原始输出")
            return raw_output



class DeepSeekAnalyzer:
    """DeepSeek分析器 - 独立实现"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model_config = get_models_config()["deepseek"]
    
    def analyze_text(self, text: str, prompt: str) -> Dict[str, Any]:
        """分析文本内容"""
        try:
            response = self._call_deepseek_api(text, prompt)
            
            if response.get("success"):
                return {
                    "success": True,
                    "analysis_result": response["content"],
                    "confidence": 0.9
                }
            else:
                return {"success": False, "error": response.get("error", "API调用失败")}
                
        except Exception as e:
            logger.error(f"DeepSeek文本分析失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _call_deepseek_api(self, text: str, prompt: str) -> Dict[str, Any]:
        """调用DeepSeek API"""
        try:
            url = "https://api.deepseek.com/chat/completions"
            
            payload = {
                "model": self.model_config["model_name"],
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                "max_tokens": self.model_config["max_tokens"],
                "temperature": self.model_config["temperature"]
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("choices"):
                    content = result["choices"][0]["message"]["content"]
                    return {"success": True, "content": content}
                else:
                    return {"success": False, "error": "API返回格式错误"}
            else:
                return {"success": False, "error": f"API调用失败: {response.status_code}"}
            
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
class DualStageAnalyzer:
    """
    双层识别机制分析器 - 独立实现版本
    
    第一层（AI-B）：通用物体/场景/情绪识别 + 主谓宾动作识别
    第二层（AI-A）：条件触发的品牌专用检测
    """
    
    def __init__(self):
        """初始化双层分析器"""
        self.api_keys = get_api_keys()
        self.models_config = get_models_config()
        self.core_brands = get_core_brands()
        self.trigger_keywords = get_brand_trigger_keywords()
        self.prompts = get_analysis_prompts()
        self.quality_control = get_quality_control()
        
        # 初始化分析器
        self._initialize_analyzers()
        
    def _initialize_analyzers(self):
        """初始化分析器"""
        try:
            # 检查API密钥
            if not self.api_keys.get("qwen"):
                logger.warning("Qwen API密钥未配置")
                self.qwen_analyzer = None
            else:
                self.qwen_analyzer = QwenVideoAnalyzer(self.api_keys["qwen"])
            
            # 初始化Gemini分析器
            if not self.api_keys.get("gemini"):
                logger.warning("Gemini API密钥未配置")
                self.gemini_analyzer = None
            else:
                self.gemini_analyzer = GeminiVideoAnalyzer(self.api_keys["gemini"])
            
            if not self.api_keys.get("deepseek"):
                logger.warning("DeepSeek API密钥未配置")
                self.deepseek_analyzer = None
            else:
                self.deepseek_analyzer = DeepSeekAnalyzer(self.api_keys["deepseek"])
            
            logger.info("✅ 分析器初始化完成")
            
        except Exception as e:
            logger.error(f"分析器初始化失败: {e}")
            self.qwen_analyzer = None
            self.gemini_analyzer = None
            self.deepseek_analyzer = None
    
    def analyze_video_slice(self, video_path: str, analysis_type: str = "dual") -> Dict[str, Any]:
        """
        分析单个视频片段（严格按照双层识别机制）
        
        Args:
            video_path: 视频片段文件路径
            analysis_type: 分析类型 ("dual", "enhanced")
            
        Returns:
            分析结果字典
        """
        try:
            logger.info(f"🎯 开始双层识别分析: {video_path}")
            logger.info(f"📊 分析类型: {analysis_type}")
            
            # 质量检查
            if not self._check_video_quality(video_path):
                return self._get_default_result("视频质量检查失败")
            
            # 检查分析器可用性
            if not self.qwen_analyzer:
                return self._get_default_result("Qwen分析器未初始化")
            
            # 根据分析类型选择处理方式
            if analysis_type == "dual":
                # 双层视觉机制（核心推荐）
                return self._perform_dual_stage_visual_analysis(video_path)
            else:  # analysis_type == "enhanced"
                # 双层机制 + 音频增强
                return self._perform_enhanced_dual_analysis(video_path)
                
        except Exception as e:
            logger.error(f"视频片段分析失败: {str(e)}")
            return self._get_default_result(f"分析异常: {str(e)}")
    
    def _perform_dual_stage_visual_analysis(self, video_path: str) -> Dict[str, Any]:
        """🆕 执行Qwen单级分析（禁用Gemini回退）"""
        try:
            logger.info("🎯 开始Qwen单级分析（已禁用Gemini回退）")
            logger.info("📋 分析顺序: 1️⃣Qwen VL Max (唯一选择)")
            
            # 🔧 获取Qwen专用prompt
            qwen_prompt = self.prompts.get("stage1_general_detection")
            
            if not qwen_prompt:
                logger.error("❌ 未能获取Qwen分析提示词模板")
                return self._get_default_result("提示词获取失败")
            
            logger.info("✅ 成功加载Qwen专用prompt")
            
            # 🥇 唯一选择：Qwen VL Max（使用通用prompt）
            if self.qwen_analyzer:
                logger.info("🤖 1️⃣ 使用 Qwen VL Max 分析（通用prompt）...")
                logger.info(f"📋 Qwen通用prompt预览: {qwen_prompt[:150]}...")
                
                qwen_result = self._try_analysis_with_language_detection(
                    self.qwen_analyzer, video_path, qwen_prompt, "qwen-vl-max"
                )
                
                if qwen_result.get("success"):
                    qwen_result["analysis_method"] = "qwen_only_mode"
                    logger.info("✅ Qwen VL Max分析成功，返回结果")
                    return qwen_result
                else:
                    logger.error(f"❌ Qwen VL Max分析失败: {qwen_result.get('error', '未知错误')}")
                    logger.info("🚫 Gemini回退已禁用，直接返回失败")
                    return self._get_default_result(f"Qwen分析失败: {qwen_result.get('error', '未知错误')}")
            else:
                logger.error("❌ Qwen分析器未初始化")
                return self._get_default_result("Qwen分析器未初始化")
                
        except Exception as e:
            logger.error(f"❌ Qwen单级分析异常: {str(e)}")
            return self._get_default_result(f"分析异常: {str(e)}")

    def _try_analysis_with_language_detection(self, analyzer, video_path: str, prompt: str, model_name: str) -> Dict[str, Any]:
        """带语言检测的分析尝试（根据模型输出语言进行相应处理）"""
        try:
            # 执行分析
            result = analyzer.analyze_video_frames(video_path, prompt)
            
            if result.get("success"):
                # 解析分析结果
                parsed_result = self._parse_result_with_language_detection(
                    result["analysis_result"], model_name
                )
                
                if parsed_result:
                    parsed_result["success"] = True
                    parsed_result["model_used"] = model_name
                    parsed_result["confidence"] = result.get("confidence", 0.85)
                    return parsed_result
                else:
                    return {"success": False, "error": "结果解析失败"}
            else:
                return {"success": False, "error": result.get("error", "分析失败")}
            
        except Exception as e:
            return {"success": False, "error": f"分析异常: {str(e)}"}
    
    def _parse_result_with_language_detection(self, analysis_text: str, model_name: str) -> Optional[Dict[str, Any]]:
        """根据模型特性和输出语言进行智能解析"""
        try:
            # 数据预处理
            if isinstance(analysis_text, dict) and 'text' in analysis_text:
                analysis_text = analysis_text.get('text', '')  # type: ignore
            elif isinstance(analysis_text, list):
                analysis_text = analysis_text[0] if analysis_text else ""
            
            analysis_text = str(analysis_text)
            
            logger.info(f"🔍 解析{model_name}分析结果: {analysis_text[:200]}...")
            
            # 🤖 Gemini模型：优先处理JSON数组格式，输出通常是英文
            if "gemini" in model_name.lower():
                return self._parse_gemini_result(analysis_text)
            
            # 🤖 Qwen模型：优先处理key:value格式，输出通常是中文
            elif "qwen" in model_name.lower():
                return self._parse_qwen_result(analysis_text)
            
            # 🤖 其他模型：通用解析
            else:
                return self._parse_generic_result(analysis_text)
                
        except Exception as e:
            logger.error(f"解析结果失败: {str(e)}")
            return None
    
    def _perform_enhanced_dual_analysis(self, video_path: str) -> Dict[str, Any]:
        """执行增强双层分析：视觉双层 + 音频增强"""
        # 暂时只返回视觉分析结果
        logger.info("🎯 增强分析暂时使用视觉分析")
        return self._perform_dual_stage_visual_analysis(video_path)

    def _check_video_quality(self, video_path: str) -> bool:
        """检查视频质量"""
        try:
            file_path = Path(video_path)
            
            # 检查文件是否存在
            if not file_path.exists():
                logger.error(f"视频文件不存在: {video_path}")
                return False
            
            # 检查文件大小
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            quality = self.quality_control
            
            if file_size_mb < quality["min_file_size_mb"]:
                logger.error(f"文件过小: {file_size_mb:.2f}MB")
                return False
            
            if file_size_mb > quality["max_file_size_mb"]:
                logger.error(f"文件过大: {file_size_mb:.2f}MB")
                return False
            
            # 检查文件格式
            if file_path.suffix.lower() not in quality["supported_formats"]:
                logger.error(f"不支持的文件格式: {file_path.suffix}")
                return False
            
            return True
                
        except Exception as e:
            logger.error(f"视频质量检查失败: {str(e)}")
            return False

    def _get_default_result(self, reason: str) -> Dict[str, Any]:
        """获取默认结果"""
        return {
            "success": False,
            "error": reason,
            "object": "analysis failed",
            "scene": "unknown scene",
            "emotion": "unknown emotion",
            "brand_elements": "none",
            "confidence": 0.0,
            "analysis_method": "failed"
        }

    def _parse_gemini_result(self, analysis_text: str) -> Optional[Dict[str, Any]]:
        """解析Gemini模型结果 - 简化版，直接解析key:value格式"""
        try:
            logger.info(f"🔍 解析gemini-2.5-pro分析结果: {analysis_text[:200]}...")
            
            # 🔧 简化解析：直接使用key:value格式解析（与Qwen相同）
            result = self._parse_key_value_format(analysis_text)
            
            if result and result.get('object'):
                # 基础验证：确保object不是通用词汇
                object_text = result.get('object', '').lower()
                if any(generic in object_text for generic in ['video', 'content', '视频', '内容']):
                    logger.warning(f"⚠️ Gemini输出包含通用词汇: {result.get('object')}")
                    # 不返回None，而是保留结果但降低置信度
                    result['confidence'] = 0.6
                else:
                    result['confidence'] = 0.9
                
                logger.info("✅ Gemini简化解析成功")
                return result
            else:
                logger.warning("⚠️ Gemini key:value解析失败，尝试智能提取")
                # 备用：智能文本提取
                result = self._extract_meaningful_content_from_text(analysis_text)
                if result and result.get("success"):
                    logger.info("✅ Gemini智能文本提取完成")
                    return result
                else:
                    logger.error("❌ Gemini所有解析方法都失败")
                    return None
            
        except Exception as e:
            logger.error(f"Gemini结果解析异常: {e}")
            return None
    
    def _parse_qwen_result(self, analysis_text: str) -> Optional[Dict[str, Any]]:
        """解析Qwen模型结果（通常是中文，key:value格式）"""
        try:
            result = {}
            
            # 🔧 优先尝试key:value格式（Qwen特色）
            parsed_kv = self._parse_key_value_format(analysis_text)
            if parsed_kv:
                result.update(parsed_kv)
                logger.info(f"✅ Qwen key:value格式解析成功")
                return self._finalize_result(result)
            
            # 🔧 备用方案：智能文本提取（中文友好）
            result = self._extract_meaningful_content_from_text(analysis_text)
            logger.info(f"✅ Qwen智能文本提取完成")
            return self._finalize_result(result)
                
        except Exception as e:
            logger.error(f"Qwen结果解析失败: {str(e)}")
            return None

    def _parse_generic_result(self, analysis_text: str) -> Optional[Dict[str, Any]]:
        """通用模型结果解析"""
        try:
            result = {}
            
            # 🔧 尝试多种解析方案
            # 1. key:value格式
            parsed_kv = self._parse_key_value_format(analysis_text)
            if parsed_kv:
                result.update(parsed_kv)
                return self._finalize_result(result)
            
            # 2. 智能文本提取
            result = self._extract_meaningful_content_from_text(analysis_text)
            return self._finalize_result(result)
                
        except Exception as e:
            logger.error(f"通用结果解析失败: {str(e)}")
            return None

    def _extract_from_gemini_json_array(self, json_data: list) -> Dict[str, Any]:
        """从Gemini的JSON数组中提取信息，保持原始语言"""
        try:
            result = {}
            
            # 合并所有label内容
            all_labels = []
            for item in json_data:
                if isinstance(item, dict) and 'label' in item:
                    label_text = item['label'].strip()
                    if label_text and len(label_text) > 5:  # 过滤掉太短的标签
                        all_labels.append(label_text)
            
            if not all_labels:
                return {}
            
            # 🔧 使用第一个有意义的标签作为主要描述
            main_description = all_labels[0]
            result['object'] = main_description
            
            # 🔧 从描述中智能推断场景和情绪
            result['scene'] = self._infer_scene_from_text(main_description)
            result['emotion'] = self._infer_emotion_from_text(main_description)
            
            logger.info(f"🎯 Gemini JSON提取: object='{result['object'][:50]}...', scene='{result['scene']}', emotion='{result['emotion']}'")
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini JSON数组提取失败: {e}")
            return {}

    def _parse_key_value_format(self, text: str) -> Dict[str, Any]:
        """解析key:value格式的文本"""
        try:
            result = {}
            lines = text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    # 🔧 统一格式清理
                    value = self._clean_field_format(value)
                    
                    if key == 'interaction' and 'object' not in result:
                        result['object'] = value
                    elif key == 'scene' and 'scene' not in result:
                        result['scene'] = value
                    elif key == 'emotion' and 'emotion' not in result:
                        result['emotion'] = value
                    elif key == 'brand_elements' and 'brand_elements' not in result:
                        result['brand_elements'] = value
            
            # 检查是否找到了足够的字段
            if len(result) >= 3:
                return result
            else:
                return {}
                
        except Exception as e:
            logger.error(f"key:value格式解析失败: {e}")
            return {}

    def _finalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """完善分析结果，添加必需字段和质量控制"""
        try:
            # 添加默认brand_elements
            if 'brand_elements' not in result:
                result['brand_elements'] = '无'
            
            # 🔧 对所有字段进行格式清理
            for key in ['object', 'scene', 'emotion', 'brand_elements']:
                if key in result:
                    result[key] = self._clean_field_format(result[key])
            
            # 🚨 质量控制检测
            if result.get('object'):
                is_invalid, invalid_reason = self._detect_invalid_slice(result['object'])
                result['quality_status'] = 'invalid' if is_invalid else 'valid'
                if is_invalid:
                    result['invalid_reason'] = invalid_reason
                    logger.warning(f"🚨 检测到无效切片: {invalid_reason}")
            else:
                result['quality_status'] = 'valid'
            
            return result
            
        except Exception as e:
            logger.error(f"结果完善失败: {e}")
            return result

    def _infer_scene_from_text(self, text: str) -> str:
        """从文本描述中推断场景（支持中英文）"""
        try:
            text_lower = text.lower()
            
            # 中文场景关键词
            chinese_scene_keywords = {
                '厨房': '家中厨房',
                '客厅': '家中客厅', 
                '餐厅': '家中餐厅',
                '卧室': '家中卧室',
                '医院': '医院环境',
                '诊所': '医疗场所',
                '户外': '户外场景',
                '教室': '室内教室',
                '办公': '办公环境'
            }
            
            # 英文场景关键词
            english_scene_keywords = {
                'kitchen': '家中厨房',
                'living room': '家中客厅',
                'bedroom': '家中卧室', 
                'hospital': '医院环境',
                'clinic': '医疗场所',
                'outdoor': '户外场景',
                'classroom': '室内教室',
                'office': '办公环境'
            }
            
            # 中文关键词匹配
            for keyword, scene in chinese_scene_keywords.items():
                if keyword in text:
                    return scene
            
            # 英文关键词匹配
            for keyword, scene in english_scene_keywords.items():
                if keyword in text_lower:
                    return scene
            
            # 根据内容推断
            if any(word in text_lower for word in ['cooking', 'preparing', 'formula', '冲泡', '准备']):
                return '家中厨房'
            elif any(word in text_lower for word in ['playing', 'dancing', '玩耍', '游戏']):
                return '家中客厅'
            
            # 默认室内场景
            return '室内场景'
            
        except Exception as e:
            logger.warning(f"场景推断失败: {e}")
            return '室内场景'

    def _infer_emotion_from_text(self, text: str) -> str:
        """从文本描述中推断情绪（支持中英文）"""
        try:
            text_lower = text.lower()
            
            # 中文情绪关键词
            chinese_emotion_keywords = {
                '哭': '不安',
                '哭闹': '不安',
                '开心': '开心',
                '高兴': '开心',
                '玩': '开心',
                '笑': '开心',
                '专注': '专注',
                '认真': '专注',
                '焦虑': '焦虑',
                '担心': '焦虑'
            }
            
            # 英文情绪关键词  
            english_emotion_keywords = {
                'crying': '不安',
                'happy': '开心',
                'smiling': '开心',
                'playing': '开心',
                'focused': '专注',
                'worried': '焦虑',
                'calm': '平静'
            }
            
            # 中文关键词匹配
            for keyword, emotion in chinese_emotion_keywords.items():
                if keyword in text:
                    return emotion
            
            # 英文关键词匹配
            for keyword, emotion in english_emotion_keywords.items():
                if keyword in text_lower:
                    return emotion
            
            # 默认平静情绪
            return '平静'
            
        except Exception as e:
            logger.warning(f"情绪推断失败: {e}")
            return '平静'

    def _extract_concise_object_from_multi_frame_analysis(self, text: str) -> tuple[str, bool]:
        """从多图片分析文本中提取详细且结构化的多场景描述
        
        Returns:
            tuple: (详细描述文本, 是否为多场景)
        """
        try:
            # 检测是否为多图片分析格式
            if "### 第一张图片分析" in text or "### 图片一" in text or "### 第一组" in text:
                logger.info("🔍 检测到多图片分析格式，进行多场景标记和结构化分析")
                
                # 提取所有interaction内容
                interactions = []
                scenes = []
                emotions = []
                import re
                
                # 匹配所有字段
                interaction_pattern = r'\*\*interaction\*\*:\s*([^*\n]+)'
                scene_pattern = r'\*\*scene\*\*:\s*([^*\n]+)'
                emotion_pattern = r'\*\*emotion\*\*:\s*([^*\n]+)'
                
                interaction_matches = re.findall(interaction_pattern, text)
                scene_matches = re.findall(scene_pattern, text)
                emotion_matches = re.findall(emotion_pattern, text)
                
                # 清理和收集数据
                for match in interaction_matches:
                    interaction = match.strip()
                    if interaction and len(interaction) > 2:
                        interactions.append(interaction)
                
                for match in scene_matches:
                    scene = match.strip()
                    if scene and len(scene) > 2:
                        scenes.append(scene)
                
                for match in emotion_matches:
                    emotion = match.strip()
                    if emotion and len(emotion) > 1:
                        emotions.append(emotion)
                
                if interactions:
                    scene_count = len(interactions)
                    logger.info(f"📊 发现 {scene_count} 个场景：{len(set(interactions))} 个不同动作")
                    
                    # 🎯 策略1: 单场景情况（不标记为多场景）
                    if scene_count == 1:
                        return interactions[0], False
                    
                    # 🎯 策略2: 多场景情况 - 生成详细结构化描述并标记
                    is_multi_scene = True
                    structured_description = self._create_structured_multi_scene_description(interactions, scenes, emotions)
                    
                    # 🆕 添加场景总结信息，便于后续分类
                    scene_summary = self._generate_scene_summary_for_classification(interactions, scenes, emotions)
                    
                    # 🎯 组合详细描述和分类总结
                    full_description = f"{structured_description} | 总结: {scene_summary}"
                    
                    logger.info(f"📝 多场景结构化描述: {full_description}")
                    return full_description, is_multi_scene
                
                # 如果没有找到interaction，尝试提取其他有用信息
                logger.warning("⚠️ 多图片分析中未找到interaction字段")
                
            # 🎯 策略3: 非多图片格式的处理（不是多场景）
            simple_desc = self._extract_simple_action_description(text)
            return simple_desc, False
            
        except Exception as e:
            logger.error(f"❌ 多场景分析失败: {e}")
            # 返回前50个字符作为备选，不标记为多场景
            fallback = text[:50] + "..." if len(text) > 50 else text
            return fallback, False

    def _create_structured_multi_scene_description(self, interactions: list, scenes: list, emotions: list) -> str:
        """创建结构化的多场景描述，详细覆盖所有场景，便于后续分类"""
        try:
            scene_count = len(interactions)
            
            # 🎯 新逻辑：生成详细的结构化描述
            if scene_count <= 1:
                return interactions[0] if interactions else "单场景内容"
            
            # 📋 分析场景模式和主题
            scene_analysis = self._analyze_scene_patterns(interactions, scenes)
            
            # 🔍 识别主要参与者和行为类型
            main_subjects = scene_analysis.get('unique_subjects', [])
            main_actions = scene_analysis.get('unique_actions', [])
            main_subject = main_subjects[0] if main_subjects else '主体'
            
            # 📊 生成详细的场景描述
            detailed_scenes = []
            for i, interaction in enumerate(interactions[:5]):  # 最多显示5个场景
                # 提取每个场景的关键信息
                scene_info = self._extract_scene_key_info(interaction, scenes[i] if i < len(scenes) else "")
                detailed_scenes.append(f"场景{i+1}: {scene_info}")
            
            # 🎯 创建结构化描述
            if scene_count == 2:
                return f"双场景序列 - {detailed_scenes[0]}; {detailed_scenes[1]}"
            elif scene_count == 3:
                return f"三场景序列 - {detailed_scenes[0]}; {detailed_scenes[1]}; {detailed_scenes[2]}"
            elif scene_count <= 5:
                scenes_desc = "; ".join(detailed_scenes)
                return f"多场景序列({scene_count}个) - {scenes_desc}"
            else:
                # 超过5个场景，显示前3个和后2个
                first_scenes = "; ".join(detailed_scenes[:3])
                last_scenes = "; ".join(detailed_scenes[-2:])
                return f"复杂多场景({scene_count}个) - {first_scenes}; ...; {last_scenes}"
                
        except Exception as e:
            logger.error(f"❌ 结构化描述创建失败: {e}")
            # 回退到简单的场景列表
            return self._create_simple_scene_list(interactions)

    def _extract_scene_key_info(self, interaction: str, scene: str) -> str:
        """提取单个场景的关键信息"""
        try:
            # 🔍 提取主要元素
            subject = "主体"
            action = "行为"
            object_item = "对象"
            
            # 识别主体
            if '妈妈' in interaction or '女人' in interaction or '母亲' in interaction:
                subject = "妈妈"
            elif '宝宝' in interaction or '婴儿' in interaction or '孩子' in interaction:
                subject = "宝宝"
            elif '医生' in interaction or '专家' in interaction or '护士' in interaction:
                subject = "医生"
            elif '工作人员' in interaction or '教练' in interaction:
                subject = "工作人员"
            elif '产品' in interaction or '奶粉' in interaction or '奶瓶' in interaction:
                subject = "产品"
            
            # 识别动作
            action_keywords = {
                '喂养': ['喂', '喝奶', '饮用', '吃'],
                '护理': ['护理', '抚摸', '轻拍', '照顾', '换尿布'],
                '互动': ['逗', '互动', '交谈', '玩耍', '拍照'],
                '展示': ['展示', '显示', '拿着', '手持', '呈现'],
                '准备': ['冲泡', '准备', '调制', '搅拌'],
                '情绪': ['哭闹', '哭泣', '笑', '开心', '不安'],
                '教育': ['教导', '指导', '解释', '演示'],
                '检查': ['检查', '观察', '查看', '测试']
            }
            
            for action_type, keywords in action_keywords.items():
                if any(keyword in interaction for keyword in keywords):
                    action = action_type
                    break
            
            # 识别对象
            if '奶粉' in interaction or '配方奶' in interaction:
                object_item = "奶粉"
            elif '奶瓶' in interaction:
                object_item = "奶瓶"
            elif '产品' in interaction or '包装' in interaction:
                object_item = "产品"
            elif '营养' in interaction or '标签' in interaction:
                object_item = "营养信息"
            
            # 添加场景信息
            scene_info = ""
            if scene and scene.strip():
                scene_clean = scene.strip()
                if '厨房' in scene_clean:
                    scene_info = "在厨房"
                elif '客厅' in scene_clean:
                    scene_info = "在客厅"
                elif '医院' in scene_clean:
                    scene_info = "在医院"
                elif '户外' in scene_clean:
                    scene_info = "在户外"
                elif '卧室' in scene_clean:
                    scene_info = "在卧室"
            
            # 组合成简洁描述
            return f"{subject}{action}{object_item}{scene_info}"
            
        except Exception as e:
            logger.error(f"❌ 场景关键信息提取失败: {e}")
            return interaction[:15] + "..." if len(interaction) > 15 else interaction

    def _create_simple_scene_list(self, interactions: list) -> str:
        """创建简单的场景列表（备用方案）"""
        try:
            if not interactions:
                return "无场景信息"
            
            # 限制每个场景描述长度
            simplified_scenes = []
            for i, interaction in enumerate(interactions[:5]):
                short_desc = interaction[:12] + "..." if len(interaction) > 12 else interaction
                simplified_scenes.append(f"第{i+1}段:{short_desc}")
            
            if len(interactions) > 5:
                return f"多场景内容({len(interactions)}个) - {'; '.join(simplified_scenes)}等"
            else:
                return f"多场景内容({len(interactions)}个) - {'; '.join(simplified_scenes)}"
                
        except Exception as e:
            logger.error(f"❌ 简单场景列表创建失败: {e}")
            return f"多场景内容({len(interactions)}个场景)"

    def _extract_action_keywords(self, interaction: str) -> str:
        """从interaction中提取关键动作词"""
        try:
            # 动作关键词映射
            action_mapping = {
                '展示': ['展示', '显示', '拿着', '手持'],
                '逗': ['逗', '玩', '互动'],
                '喂养': ['喝奶', '喂', '喂养'],
                '护理': ['抚摸', '轻拍', '护理', '照顾'],
                '自拍': ['自拍', '拍照'],
                '交谈': ['交谈', '交流', '对话'],
                '游泳': ['游泳', '水中', '支撑'],
                '准备': ['准备', '冲泡', '调制']
            }
            
            for action, keywords in action_mapping.items():
                if any(keyword in interaction for keyword in keywords):
                    return action
            
            # 如果没找到映射，提取主要动词
            import re
            # 提取中文动词模式
            verb_pattern = r'([\u4e00-\u9fa5]{1,2}(?:着|了|过|在|给)*[\u4e00-\u9fa5]{0,2})'
            matches = re.findall(verb_pattern, interaction)
            if matches:
                return matches[0][:4]  # 取前4个字符
            
            # 最后回退
            return interaction[:6] + "..." if len(interaction) > 6 else interaction
            
        except Exception as e:
            logger.error(f"❌ 动作关键词提取失败: {e}")
            return interaction[:8]

    def _actions_are_similar(self, action1: str, action2: str) -> bool:
        """判断两个动作是否相似"""
        try:
            # 提取关键词进行比较
            key1 = self._extract_action_keywords(action1)
            key2 = self._extract_action_keywords(action2)
            
            # 如果关键词相同，认为相似
            if key1 == key2:
                return True
            
            # 检查是否包含相同的主体和动词
            similar_pairs = [
                ['喝奶', '喂养'], ['展示', '显示'], ['逗', '互动'], 
                ['抚摸', '轻拍'], ['交谈', '交流'], ['自拍', '拍照']
            ]
            
            for pair in similar_pairs:
                if (pair[0] in action1 and pair[1] in action2) or (pair[1] in action1 and pair[0] in action2):
                    return True
            
            return False
        
        except Exception as e:
            logger.error(f"❌ 动作相似性判断失败: {e}")
            return False

    def _analyze_scene_patterns(self, interactions: list, scenes: list) -> dict:
        """分析场景模式"""
        try:
            # 🔍 主体分析
            subjects = []
            for interaction in interactions:
                if '妈妈' in interaction or '女人' in interaction or '女性' in interaction:
                    subjects.append('妈妈')
                elif '宝宝' in interaction or '婴儿' in interaction:
                    subjects.append('宝宝')
                elif '工作人员' in interaction or '教练' in interaction:
                    subjects.append('工作人员')
                elif '奶粉' in interaction or '产品' in interaction or '包装' in interaction:
                    subjects.append('产品')
                else:
                    subjects.append('其他')
            
            # 🔍 动作类型分析
            action_types = []
            action_mapping = {
                '护理': ['护理', '抚摸', '轻拍', '换尿布', '照顾'],
                '互动': ['逗', '互动', '交谈', '拍照', '自拍', '玩'],
                '喂养': ['喝奶', '喂养', '准备奶', '冲泡', '喝'],
                '展示': ['展示', '显示', '拿着', '手持'],
                '运动': ['游泳', '水中', '运动', '锻炼']
            }
            
            for interaction in interactions:
                categorized = False
                for action_type, keywords in action_mapping.items():
                    if any(keyword in interaction for keyword in keywords):
                        action_types.append(action_type)
                        categorized = True
                        break
                if not categorized:
                    action_types.append('其他')
            
            # 🔍 场景环境分析
            environments = []
            if scenes:
                for scene in scenes:
                    if '游泳' in scene or '水中' in scene:
                        environments.append('游泳馆')
                    elif '厨房' in scene:
                        environments.append('厨房')
                    elif '婴儿房' in scene or '卧室' in scene:
                        environments.append('婴儿房')
                    elif '客厅' in scene:
                        environments.append('客厅')
                    else:
                        environments.append('室内')
            
            # 🎯 模式判断
            unique_subjects = list(set(subjects))
            unique_actions = list(set(action_types))
            unique_environments = list(set(environments))
            
            is_progressive = len(unique_actions) > 1 and len(unique_subjects) >= 1
            is_parallel = len(unique_subjects) > 1 and len(set(action_types[:2])) == 1  # 前两个动作相同
            is_repetitive = len(set(interactions)) < len(interactions) * 0.6  # 60%相似度阈值
            
            return {
                'subjects': subjects,
                'unique_subjects': unique_subjects,
                'action_types': action_types,
                'unique_actions': unique_actions,
                'environments': environments,
                'unique_environments': unique_environments,
                'is_progressive': is_progressive,
                'is_parallel': is_parallel,
                'is_repetitive': is_repetitive,
                'total_scenes': len(interactions)
            }
            
        except Exception as e:
            logger.error(f"❌ 场景模式分析失败: {e}")
            return {
                'subjects': [], 'unique_subjects': [], 'action_types': [], 'unique_actions': [],
                'environments': [], 'unique_environments': [],
                'is_progressive': False, 'is_parallel': False, 'is_repetitive': False,
                'total_scenes': len(interactions)
            }

    def _extract_simple_action_description(self, text: str) -> str:
        """提取简单动作描述（非多图片格式）"""
        try:
            # 如果包含明显的行为描述，直接提取
            simple_patterns = [
                r'(妈妈|女人|女性|宝宝|工作人员)[^。，]+?(?:展示|逗|抚摸|轻拍|换|喂|喝|准备|交谈|自拍|拍照)[^。，]*',
                r'(展示|显示)[^。，]*?(产品|奶瓶|奶粉|营养标签)[^。，]*',
                r'(手持|拿着)[^。，]*?(展示|显示)[^。，]*'
            ]
            
            for pattern in simple_patterns:
                match = re.search(pattern, text)
                if match:
                    result = match.group(0).strip()
                    if len(result) <= 25:  # 稍微放宽长度限制
                        return result
            
            # 如果都没找到，返回前25个字符
            cleaned_text = re.sub(r'[#*]+', '', text).strip()
            if len(cleaned_text) > 25:
                return cleaned_text[:25] + "..."
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"❌ 简单动作描述提取失败: {e}")
            return text[:20] + "..." if len(text) > 20 else text

    def _extract_meaningful_content_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取有意义的内容，确保具体性"""
        try:
            # 🔧 基础清理和预处理
            text = re.sub(r'[{}[\]"]', '', text).strip()
            
            # 🆕 专门处理多图片分析格式，提取简洁的object描述
            concise_object, is_multi_scene = self._extract_concise_object_from_multi_frame_analysis(text)
            
            # 🎯 如果成功提取到描述，使用它作为主要结果
            if concise_object and len(concise_object) <= 100:  # 🆕 适度放宽长度限制以容纳详细多场景描述
                extraction_type = "多场景结构化" if is_multi_scene else "简洁"
                logger.info(f"✅ 成功提取{extraction_type}描述: {concise_object}")
                
                # 📊 构建结果
                result = {
                    "object": self._clean_field_format(concise_object),
                    "scene": self._infer_scene_from_text(text),  # 从完整文本推断场景
                    "emotion": self._infer_emotion_from_text(text),  # 从完整文本推断情感
                    "brand_elements": "无",
                    "confidence": 0.92 if is_multi_scene else 0.88,  # 🆕 多场景分析有更高置信度
                    "success": True,
                    "is_multi_scene": is_multi_scene,  # 🆕 添加多场景标记
                    "scene_count": text.count("### ") if is_multi_scene else 1  # 🆕 场景数量
                }
                
                logger.info(f"🎯 {extraction_type}提取结果: object='{result['object']}', scene='{result['scene']}', emotion='{result['emotion']}', multi_scene={is_multi_scene}")
                return result
            
            # 🔄 如果简洁提取失败，回退到原有的关键句子提取逻辑
            logger.info("🔄 简洁提取未成功，回退到关键句子提取")
            sentences = self._extract_key_sentences_from_text(text)
            
            if not sentences:
                return self._get_default_result("无法提取关键句子")
            
            # 🎯 使用第一个最具体的句子作为主描述
            main_sentence = sentences[0]
            
            # 🔧 修复：大幅降低具体性阈值，避免误判
            specificity_score = self._calculate_specificity_score(main_sentence)
            if specificity_score < 0.2:  # 🚀 降低阈值从0.6到0.2，只过滤真正无意义的内容
                logger.warning(f"⚠️ 内容可能过于通用 (具体性得分: {specificity_score:.2f}): {main_sentence}")
                # 尝试使用下一个更具体的句子
                for sentence in sentences[1:]:
                    alt_score = self._calculate_specificity_score(sentence)
                    if alt_score >= 0.2:  # 🚀 降低备选阈值
                        main_sentence = sentence
                        specificity_score = alt_score
                        logger.info(f"✅ 使用更具体的描述 (得分: {alt_score:.2f}): {sentence}")
                        break
                else:
                    # 🔧 关键修复：即使所有句子得分都低，也不返回失败，而是使用原句子
                    logger.warning(f"⚠️ 所有描述得分偏低，但仍保留分析结果: {main_sentence}")
                    specificity_score = 0.5  # 给予默认置信度
            
            # 📊 构建结果
            result = {
                "object": self._clean_field_format(main_sentence),
                "scene": self._infer_scene_from_text(main_sentence),
                "emotion": self._infer_emotion_from_text(main_sentence),
                "brand_elements": "无",
                "confidence": max(0.7, specificity_score),  # 基于具体性调整置信度
                "success": True
            }
            
            logger.info(f"🎯 智能提取 (具体性: {specificity_score:.2f}): object='{result['object'][:50]}...', scene='{result['scene']}', emotion='{result['emotion']}'")
            
            return result
            
        except Exception as e:
            logger.error(f"智能内容提取失败: {e}")
            return self._get_default_result("内容提取异常")

    def _calculate_specificity_score(self, text: str) -> float:
        """计算文本的具体性得分 - 优化版，更宽松合理"""
        try:
            text_lower = text.lower()
            score = 0.3  # 🚀 基础分数从0改为0.3，更宽松
            
            # 🎯 具体物体词汇 (+0.2，降低权重)
            specific_objects = [
                'baby', 'child', 'girl', 'boy', 'mother', 'father', 'toddler',
                '宝宝', '孩子', '女孩', '男孩', '妈妈', '爸爸', '幼儿', '女人', '人',
                'bottle', 'milk', 'formula', 'toy', 'book', 'food', 'package', 'product',
                '奶瓶', '牛奶', '奶粉', '玩具', '书', '食物', '餐具', '包装', '产品', '罐'
            ]
            for obj in specific_objects:
                if obj in text_lower:
                    score += 0.2
                    break
            
            # 🎯 具体动作词汇 (+0.3，保持权重)
            specific_actions = [
                'drinking', 'eating', 'playing', 'crying', 'smiling', 'walking', 'sitting',
                'holding', 'showing', 'displaying', 'preparing',
                '喝', '吃', '玩', '哭', '笑', '走', '坐', '拿', '放', '看', '听', '展示', 
                '显示', '摆放', '突出', '冲泡', '准备', '递给', '抱着'
            ]
            for action in specific_actions:
                if action in text_lower:
                    score += 0.3
                    break
            
            # 🎯 具体场景词汇 (+0.1，降低权重)
            specific_places = [
                'table', 'chair', 'bed', 'sofa', 'kitchen', 'living room', 'hospital',
                '桌子', '椅子', '床', '沙发', '厨房', '客厅', '医院', '餐桌', '室内', '桌面'
            ]
            for place in specific_places:
                if place in text_lower:
                    score += 0.1
                    break
            
            # 🔧 修复：大幅减少通用词汇惩罚 (-0.2，从-0.5减少)
            very_generic_terms = [
                'video content analysis', 'general content', 'unknown content',
                '视频内容分析', '通用内容', '未知内容'  # 只惩罚真正通用的词汇
            ]
            for generic in very_generic_terms:
                if generic in text_lower:
                    score -= 0.2  # 🚀 减少惩罚力度
                    break
            
            # 🔧 移除过短描述惩罚，因为简洁也可能很有效
            
            # 🎯 新增：包含品牌或产品信息的加分
            product_terms = [
                '营养标签', '品牌标识', '奶粉罐', '包装', '标签', '成分', 'logo', 'brand'
            ]
            for term in product_terms:
                if term in text_lower:
                    score += 0.2
                    break
            
            return max(0.1, min(1.0, score))  # 🚀 最低分从0改为0.1，避免完全为0
            
        except Exception as e:
            logger.warning(f"具体性评分失败: {e}")
            return 0.5  # 默认中等得分

    def _extract_key_sentences_from_text(self, text: str, scenario: str = "母婴产品") -> list:
        """从文本中提取关键句子 - 使用配置化的关键词管理"""
        try:
            import re
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent))
            from config.keyword_extraction_config import get_keyword_config
            
            # 获取关键词配置
            keyword_config = get_keyword_config()
            extraction_settings = keyword_config.get_extraction_settings()
            keywords = keyword_config.get_keywords_for_extraction(scenario)
            regex_patterns = keyword_config.get_regex_patterns()
            
            # 分割句子
            sentences = re.split(r'[.!?。！？]+', text)
            key_sentences = []
            
            logger.info(f"🔍 使用 {len(keywords)} 个关键词和 {len(regex_patterns)} 个正则模式进行提取")
            
            for sentence in sentences:
                sentence = sentence.strip()
                
                # 基础过滤
                min_length = extraction_settings.get("min_sentence_length", 8)
                if len(sentence) < min_length:
                    continue
                
                sentence_score = 0
                match_details = []
                
                # 🎯 方法1: 关键词匹配（基础方法）
                sentence_lower = sentence.lower() if not extraction_settings.get("case_sensitive", False) else sentence
                for keyword in keywords:
                    keyword_check = keyword.lower() if not extraction_settings.get("case_sensitive", False) else keyword
                    if keyword_check in sentence_lower:
                        sentence_score += 1
                        match_details.append(f"关键词:{keyword}")
                
                # 🎯 方法2: 正则表达式模式匹配（高级方法）
                for pattern_config in regex_patterns:
                    pattern = pattern_config["pattern"]
                    weight = pattern_config["weight"]
                    
                    if pattern.search(sentence):
                        sentence_score += weight
                        match_details.append(f"模式:{pattern_config['name']}")
                
                # 🎯 方法3: 语义结构分析（智能方法）
                if self._has_subject_verb_object_structure(sentence):
                    sentence_score += 1.5
                    match_details.append("主谓宾结构")
                
                # 决定是否保留句子
                if sentence_score >= 1.0:  # 至少匹配一个条件
                    key_sentences.append({
                        "sentence": sentence,
                        "score": sentence_score,
                        "matches": match_details
                    })
                    logger.debug(f"✅ 保留句子 (得分:{sentence_score:.1f}): {sentence[:50]}...")
            
            # 按得分排序并返回最佳句子
            key_sentences.sort(key=lambda x: x["score"], reverse=True)
            max_sentences = extraction_settings.get("max_sentences", 3)
            
            best_sentences = [item["sentence"] for item in key_sentences[:max_sentences]]
            
            if best_sentences:
                logger.info(f"🎯 提取到 {len(best_sentences)} 个关键句子，最高得分: {key_sentences[0]['score']:.1f}")
            else:
                logger.warning("⚠️ 未提取到任何关键句子，可能需要调整配置")
            
            return best_sentences
            
        except Exception as e:
            logger.error(f"❌ 配置化关键句子提取失败: {e}")
            # 回退到简单方法
            return self._extract_key_sentences_fallback(text)
    
    def _has_subject_verb_object_structure(self, sentence: str) -> bool:
        """检测句子是否具有主谓宾结构"""
        try:
            # 简单的中文主谓宾结构检测
            chinese_verbs = ["展示", "拿着", "喝", "吃", "玩", "坐", "看", "抱", "喂", "哭", "笑", "制作", "准备"]
            chinese_subjects = ["宝宝", "妈妈", "爸爸", "孩子", "婴儿", "产品", "奶粉罐", "包装"]
            chinese_objects = ["奶瓶", "奶粉", "玩具", "食品", "标签", "营养成分"]
            
            has_subject = any(subj in sentence for subj in chinese_subjects)
            has_verb = any(verb in sentence for verb in chinese_verbs)
            has_object = any(obj in sentence for obj in chinese_objects)
            
            return has_subject and has_verb
            
        except Exception:
            return False
    
    def _extract_key_sentences_fallback(self, text: str) -> list:
        """回退的简单关键句子提取方法 - 也使用配置化关键词"""
        try:
            import re
            sentences = re.split(r'[.!?。！？]+', text)
            
            # 🔧 移除硬编码：使用配置化的基础关键词
            try:
                import sys
                from pathlib import Path
                sys.path.append(str(Path(__file__).parent.parent))
                from config.keyword_extraction_config import get_keyword_config
                
                # 使用高权重类别的关键词作为基础回退
                keyword_config = get_keyword_config()
                all_keywords = []
                for category, config in keyword_config.keywords_config["keyword_categories"].items():
                    if config.get("weight", 1.0) >= 1.0:  # 只使用权重>=1.0的类别
                        for keywords in config["keywords"].values():
                            all_keywords.extend(keywords[:5])  # 每类最多5个词
                
                basic_keywords = list(set(all_keywords))  # 去重
                logger.info(f"🔄 回退方法使用 {len(basic_keywords)} 个配置化关键词")
                
            except Exception as config_error:
                logger.warning(f"⚠️ 配置加载失败，使用最小硬编码集: {config_error}")
                # 🚨 最后的硬编码保障：只保留最核心的词汇
                basic_keywords = ["宝宝", "妈妈", "baby", "mother"]
            
            key_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if (len(sentence) >= 8 and 
                    any(word in sentence.lower() for word in basic_keywords)):
                    key_sentences.append(sentence)
            
            return key_sentences[:3]
            
        except Exception as e:
            logger.warning(f"回退提取方法失败: {e}")
            return []

    def _clean_field_format(self, text: str) -> str:
        """统一清理字段格式，移除方括号和多余符号"""
        if not text:
            return text
        
        try:
            # 移除各种方括号和引号
            cleaned = text
            
            # 移除方括号 [ ]
            cleaned = cleaned.replace('[', '').replace(']', '')
            
            # 移除多余的引号
            cleaned = cleaned.replace('"', '').replace("'", '')
            
            # 移除多余的逗号分隔（但保留内容中的逗号）
            if cleaned.startswith(','):
                cleaned = cleaned[1:]
            if cleaned.endswith(','):
                cleaned = cleaned[:-1]
            
            # 清理多余的空格
            cleaned = ' '.join(cleaned.split())
            
            # 🔧 统一处理空值
            if cleaned.lower().strip() in ['无', 'none', 'null', '', '没有', '未知']:
                return '无'
            
            return cleaned.strip()
            
        except Exception as e:
            logger.warning(f"字段格式清理失败: {e}")
            return text

    def _detect_invalid_slice(self, interaction_text: str) -> tuple[bool, str]:
        """检测无效切片 - 仅检测彻底无内容的情况，不再基于人物存在判断"""
        try:
            if not interaction_text:
                return True, "empty content"
                
            text_lower = interaction_text.lower()
            
            # 🎯 新策略：任何切片都有分析价值，不再因为无人物而标记为无效
            # 无人物的切片也可能包含产品信息、品牌元素、环境信息等有价值内容
            
            # 1. 检测分析彻底失败的情况 - 🔧 更严格的检测，避免误判
            true_failure_phrases = [
                "analysis completely failed", "处理彻底失败", "无法解析视频", "视频损坏",
                "fatal error", "严重错误", "complete failure", "total failure"
            ]
            # 🚀 移除"analysis failed"的检测，因为这可能是正常的分析结果描述
            for phrase in true_failure_phrases:
                if phrase in text_lower:
                    return True, "analysis failed completely"
            
            # 2. 检测完全空白或无意义的内容
            very_short = len(interaction_text.strip()) < 3
            completely_empty = interaction_text.strip() in ["", "无", "none", "null", "N/A", "未知", "unknown"]
            
            if very_short or completely_empty:
                return True, "empty or meaningless content"
            
            # 3. 检测视频文件损坏或无法解析的情况
            corrupted_indicators = [
                "corrupted", "损坏", "无法播放", "文件错误", "format error",
                "cannot decode", "解码失败", "视频损坏"
            ]
            if any(phrase in text_lower for phrase in corrupted_indicators):
                return True, "corrupted or unreadable video file"
            
            # 🔧 重要改变：移除所有基于人物存在的无效判断
            # 包含以下内容的切片现在都被认为是有效的：
            # - 纯产品展示（无人物但有产品信息）
            # - 品牌标识特写（无人物但有品牌价值）
            # - 环境场景（无人物但有场景信息）
            # - 文字说明（无人物但有文字内容）
            
            # 🔧 更宽松的有效性判断：只要有任何可识别内容就认为有效
            return False, ""
            
        except Exception as e:
            logger.warning(f"⚠️ 无效切片检测异常: {e}")
            return False, ""

    def _generate_scene_summary_for_classification(self, interactions: list, scenes: list, emotions: list) -> str:
        """生成场景总结信息，专门用于后续的1级2级标签分类"""
        try:
            # 🔍 分析主要元素
            summary_parts = []
            
            # 1. 主体分析
            subjects = set()
            for interaction in interactions:
                if '妈妈' in interaction or '女人' in interaction or '母亲' in interaction:
                    subjects.add('妈妈')
                if '宝宝' in interaction or '婴儿' in interaction or '孩子' in interaction:
                    subjects.add('宝宝')
                if '医生' in interaction or '专家' in interaction or '护士' in interaction:
                    subjects.add('医生')
                if '产品' in interaction or '奶粉' in interaction or '奶瓶' in interaction:
                    subjects.add('产品')
            
            if subjects:
                summary_parts.append(f"主体: {', '.join(sorted(subjects))}")
            
            # 2. 行为类型分析
            behavior_types = set()
            behavior_mapping = {
                '喂养行为': ['喂', '喝奶', '饮用', '吃', '哺乳'],
                '护理行为': ['护理', '抚摸', '轻拍', '照顾', '换尿布', '清洁'],
                '互动行为': ['逗', '互动', '交谈', '玩耍', '拍照', '自拍'],
                '展示行为': ['展示', '显示', '拿着', '手持', '呈现', '推荐'],
                '准备行为': ['冲泡', '准备', '调制', '搅拌'],
                '情绪表达': ['哭闹', '哭泣', '笑', '开心', '不安', '拒绝'],
                '教育行为': ['教导', '指导', '解释', '演示', '说明'],
                '检查行为': ['检查', '观察', '查看', '测试', '确认']
            }
            
            for behavior_type, keywords in behavior_mapping.items():
                if any(keyword in interaction for interaction in interactions for keyword in keywords):
                    behavior_types.add(behavior_type)
            
            if behavior_types:
                summary_parts.append(f"行为: {', '.join(sorted(behavior_types))}")
            
            # 3. 产品相关性分析
            product_relevance = []
            if any('奶粉' in interaction for interaction in interactions):
                product_relevance.append('奶粉相关')
            if any('奶瓶' in interaction for interaction in interactions):
                product_relevance.append('奶瓶相关')
            if any('营养' in interaction or '标签' in interaction for interaction in interactions):
                product_relevance.append('营养信息')
            if any('品牌' in interaction or '产品' in interaction for interaction in interactions):
                product_relevance.append('产品展示')
            
            if product_relevance:
                summary_parts.append(f"产品: {', '.join(product_relevance)}")
            
            # 4. 场景环境分析
            scene_types = set()
            for scene in scenes:
                if '厨房' in scene:
                    scene_types.add('厨房环境')
                elif '客厅' in scene:
                    scene_types.add('客厅环境')
                elif '医院' in scene or '诊所' in scene:
                    scene_types.add('医疗环境')
                elif '户外' in scene:
                    scene_types.add('户外环境')
                elif '卧室' in scene:
                    scene_types.add('卧室环境')
            
            if scene_types:
                summary_parts.append(f"场景: {', '.join(sorted(scene_types))}")
            
            # 5. 情绪倾向分析
            emotion_analysis = self._analyze_emotion_trend(emotions)
            if emotion_analysis:
                summary_parts.append(f"情绪: {emotion_analysis}")
            
            # 6. 视频类型建议（用于分类参考）
            video_type_hints = self._suggest_video_type_for_classification(interactions, subjects, behavior_types)
            if video_type_hints:
                summary_parts.append(f"类型建议: {video_type_hints}")
            
            # 组合总结
            return "; ".join(summary_parts) if summary_parts else "多场景内容"
            
        except Exception as e:
            logger.error(f"❌ 场景总结生成失败: {e}")
            return f"多场景内容({len(interactions)}个场景)"

    def _analyze_emotion_trend(self, emotions: list) -> str:
        """分析情绪趋势"""
        try:
            if not emotions:
                return ""
            
            positive_emotions = ['开心', '温馨', '愉悦', '满意', '开心', '快乐']
            negative_emotions = ['哭闹', '不安', '焦虑', '痛苦', '担心', '拒绝']
            neutral_emotions = ['平静', '专注', '中性', '观察', '思考']
            
            pos_count = sum(1 for emotion in emotions if any(pos in emotion for pos in positive_emotions))
            neg_count = sum(1 for emotion in emotions if any(neg in emotion for neg in negative_emotions))
            neu_count = sum(1 for emotion in emotions if any(neu in emotion for neu in neutral_emotions))
            
            if pos_count > neg_count and pos_count > neu_count:
                return "积极倾向"
            elif neg_count > pos_count and neg_count > neu_count:
                return "消极倾向"
            elif neu_count > pos_count and neu_count > neg_count:
                return "中性倾向"
            else:
                return "情绪混合"
                
        except Exception as e:
            logger.error(f"❌ 情绪趋势分析失败: {e}")
            return "情绪未知"

    def _suggest_video_type_for_classification(self, interactions: list, subjects: set, behavior_types: set) -> str:
        """基于场景内容建议视频类型，用于后续分类参考"""
        try:
            suggestions = []
            
            # 产品介绍类型判断
            if '产品' in subjects and '展示行为' in behavior_types:
                suggestions.append('产品介绍')
            
            # 使用效果类型判断
            if '宝宝' in subjects and ('喂养行为' in behavior_types or '情绪表达' in behavior_types):
                suggestions.append('使用效果')
            
            # 钩子类型判断
            if '情绪表达' in behavior_types and any('哭' in interaction or '不安' in interaction for interaction in interactions):
                suggestions.append('钩子')
            
            # 促销机制类型判断
            if '医生' in subjects and ('展示行为' in behavior_types or '教育行为' in behavior_types):
                suggestions.append('促销机制')
            
            return ', '.join(suggestions) if suggestions else "待分类"
            
        except Exception as e:
            logger.error(f"❌ 视频类型建议失败: {e}")
            return "待分类"


class BatchSliceAnalyzer:
    """
    批量切片分析器
    """
    
    def __init__(self):
        """初始化批量分析器"""
        self.dual_analyzer = DualStageAnalyzer()
        self.quality_control = get_quality_control()
        
    def analyze_batch(
        self, 
        video_files: List[str], 
        progress_callback: Optional[callable] = None  # type: ignore
    ) -> Dict[str, Any]:
        """
        批量分析视频文件
        """
        logger.info(f"🎯 开始批量双层识别分析，共 {len(video_files)} 个文件")
        
        batch_result = {
            "total_files": len(video_files),
            "success_count": 0,
            "failed_count": 0,
            "results": [],
            "statistics": {},
            "start_time": time.time()
        }
        
        for i, video_file in enumerate(video_files):
            try:
                if progress_callback:
                    progress_callback(f"分析 {i+1}/{len(video_files)}: {Path(video_file).name}")
                
                # 分析单个文件
                result = self.dual_analyzer.analyze_video_slice(video_file)
                
                if result["success"]:
                    batch_result["success_count"] += 1
                else:
                    batch_result["failed_count"] += 1
                
                batch_result["results"].append(result)
                
                # API限流
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"批量分析文件 {video_file} 失败: {e}")
                batch_result["failed_count"] += 1
                batch_result["results"].append({
                    "file_path": video_file,
                    "success": False,
                    "error": str(e)
                })
        
        # 生成统计信息
        batch_result["statistics"] = self._generate_batch_statistics(batch_result["results"])
        batch_result["end_time"] = time.time()
        batch_result["duration"] = batch_result["end_time"] - batch_result["start_time"]
        
        logger.info(f"✅ 批量分析完成: 成功 {batch_result['success_count']}, 失败 {batch_result['failed_count']}")
        
        return batch_result
    
    def _generate_batch_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成批量分析统计信息"""
        statistics = {
            "tag_frequency": {},
            "brand_frequency": {},
            "interaction_frequency": {},
            "scene_frequency": {},
            "emotion_frequency": {},
            "average_confidence": 0.0,
            "stage2_trigger_rate": 0.0
        }
        
        successful_results = [r for r in results if r.get("success", False)]
        if not successful_results:
            return statistics
        
        total_confidence = 0
        stage2_triggered = 0
        
        for result in successful_results:
            final_tags = result.get("final_tags", {})
            
            # 统计标签频次
            all_tags = final_tags.get("all_tags", [])
            for tag in all_tags:
                statistics["tag_frequency"][tag] = statistics["tag_frequency"].get(tag, 0) + 1
            
            # 统计各类别频次
            interaction = final_tags.get("interaction", "")
            if interaction:
                statistics["interaction_frequency"][interaction] = statistics["interaction_frequency"].get(interaction, 0) + 1
            
            scene = final_tags.get("scene", "")
            if scene:
                statistics["scene_frequency"][scene] = statistics["scene_frequency"].get(scene, 0) + 1
            
            emotion = final_tags.get("emotion", "")
            if emotion:
                statistics["emotion_frequency"][emotion] = statistics["emotion_frequency"].get(emotion, 0) + 1
            
            brand_elements = final_tags.get("brand_elements", "")
            if brand_elements:
                brands = [b.strip() for b in brand_elements.split(',') if b.strip()]
                for brand in brands:
                    statistics["brand_frequency"][brand] = statistics["brand_frequency"].get(brand, 0) + 1
            
            # 累计置信度
            total_confidence += final_tags.get("confidence", 0.0)
            
            # 统计第二阶段触发率
            stage2_result = result.get("stage2_result", {})
            if stage2_result.get("triggered", False):
                stage2_triggered += 1
        
        # 计算平均值
        statistics["average_confidence"] = total_confidence / len(successful_results)
        statistics["stage2_trigger_rate"] = stage2_triggered / len(successful_results) * 100
        
        return statistics 

def translate_json_file_with_deepseek(json_file_path: str) -> bool:
    """直接对JSON文件进行DeepSeek翻译，翻译英文字段为中文"""
    try:
        import json
        import requests
        import os
        from pathlib import Path
        
        # 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 需要翻译的字段
        translate_fields = ['object', 'scene', 'emotion']
        
        # 检查是否需要翻译或智能推断
        needs_translation = False
        
        for field in translate_fields:
            if field in data and isinstance(data[field], str):
                # 检查是否包含英文需要翻译
                if any(c.isalpha() and ord(c) < 256 for c in data[field]):
                    needs_translation = True
                    break
        
        # 特别检查emotion字段是否需要智能推断
        if ('emotion' in data and 
            data['emotion'].strip() in ['', '无', '[无]', '[enthusiastically]', '[无情绪]']):
            needs_translation = True
            print("🧠 检测到emotion字段需要智能推断")
        
        if not needs_translation:
            print("✅ JSON文件已经是中文且emotion完整，无需处理")
            return True
        
        print(f"🔄 开始翻译JSON文件: {json_file_path}")
        
        # 获取DeepSeek API密钥
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            # 从配置文件获取
            config_paths = [
                Path(__file__).parent.parent.parent / "feishu_pool" / ".env",
                Path(__file__).parent.parent / "config" / "env_config.txt"
            ]
            
            for config_path in config_paths:
                if config_path.exists():
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip().startswith('DEEPSEEK_API_KEY='):
                                    api_key = line.split('=', 1)[1].strip()
                                    if api_key.startswith('"') and api_key.endswith('"'):
                                        api_key = api_key[1:-1]
                                    elif api_key.startswith("'") and api_key.endswith("'"):
                                        api_key = api_key[1:-1]
                                    break
                        if api_key:
                            break
                    except Exception:
                        continue
        
        if not api_key:
            print("❌ 未找到DeepSeek API密钥")
            return False
        
        # 构造翻译请求
        translation_content = []
        for field in translate_fields:
            if field in data:
                translation_content.append(f"{field}: {data[field]}")
        
        content_to_translate = "\n".join(translation_content)
        
        # DeepSeek翻译提示词
        translate_prompt = f"""请将以下视频分析结果翻译为中文标准格式：

{content_to_translate}

要求：
1. object字段：翻译为"主语+动词+宾语"的中文格式，去除方括号
2. scene字段：翻译为简洁的中文场景描述，去除方括号
3. emotion字段：翻译为单个中文情绪词，去除方括号
4. 保持原有的分析含义不变

🧠 **智能emotion推断**：
如果emotion字段为空、"无"或"[无]"，请根据object和scene的内容智能推断合适的情绪：
- 拍手、笑容、玩耍 → 开心、兴奋、快乐
- 哭泣、拒绝、不安 → 伤心、不安、焦虑  
- 喝奶、吃饭、睡觉 → 满足、安静、舒适
- 教室、学习环境 → 专注、好奇、积极
- 家庭环境、亲子互动 → 温馨、安全、愉悦

输出格式（严格遵循，不要使用方括号）：
object: 中文主语+动词+宾语
scene: 中文场景描述
emotion: 中文情绪词

直接输出翻译结果，不要额外解释，不要使用方括号："""

        # 调用DeepSeek API
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": translate_prompt}],
            "max_tokens": 200,
            "temperature": 0.1
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        print("🚀 调用DeepSeek API进行翻译...")
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            json=payload,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("choices"):
                translated_text = result["choices"][0]["message"]["content"].strip()
                print(f"✅ DeepSeek翻译结果: {translated_text}")
                
                # 解析翻译结果并应用格式清理
                for line in translated_text.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        field, value = line.split(':', 1)
                        field = field.strip()
                        value = value.strip()
                        
                        # 🔧 格式清理：移除方括号和多余符号
                        value = value.replace('[', '').replace(']', '')
                        value = value.replace('"', '').replace("'", '')
                        
                        # 清理逗号
                        if value.startswith(','):
                            value = value[1:]
                        if value.endswith(','):
                            value = value[:-1]
                        
                        # 清理空格
                        value = ' '.join(value.split())
                        
                        # 特殊处理
                        if value.lower().strip() in ['无', 'none', 'null', '']:
                            value = '无'
                        
                        if field in translate_fields and field in data:
                            data[field] = value
                            print(f"✅ 更新字段 {field}: {value}")
                
                # 保存翻译后的JSON
                with open(json_file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ JSON文件翻译完成: {json_file_path}")
                return True
            else:
                print("❌ DeepSeek API响应中没有choices字段")
                return False
        else:
            print(f"❌ DeepSeek API调用失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ JSON翻译失败: {e}")
        return False


"""
# 🔄 原始 Google API 实现代码（已注释，保留作为参考）
# 原来的 _call_gemini_video_api_new 方法实现

def _call_gemini_video_api_new(self, client, video_path: str, prompt: str) -> Dict[str, Any]:
    # 使用新的Google Gen AI SDK调用Gemini视频API（原实现）
    try:
        from google.genai import types
        
        logger.info(f"📤 开始上传视频文件: {video_path}")
        
        # 🔧 **修复文件上传问题**：根据官方文档使用正确的API调用方式
        try:
            # 方法1: 使用官方文档推荐的方式 - 直接传递file参数
            uploaded_file = client.files.upload(file=video_path)
            logger.info(f"✅ 文件上传成功，URI: {uploaded_file.uri}")
            
        except Exception as e1:
            logger.warning(f"⚠️ 方法1失败: {e1}")
            try:
                # 方法2: 使用文件对象上传，明确指定MIME类型
                with open(video_path, 'rb') as video_file:
                    uploaded_file = client.files.upload(
                        file=video_file,
                        mime_type="video/mp4"
                    )
                logger.info(f"✅ 方法2成功：文件上传完成，URI: {uploaded_file.uri}")
                
            except Exception as e2:
                logger.warning(f"⚠️ 方法2失败: {e2}")
                try:
                    # 方法3: 使用display_name和MIME类型的完整配置
                    with open(video_path, 'rb') as video_file:
                        uploaded_file = client.files.upload(
                            file=video_file,
                            mime_type="video/mp4",
                            display_name=f"video_analysis_{os.path.basename(video_path)}"
                        )
                    logger.info(f"✅ 方法3成功：文件上传完成，URI: {uploaded_file.uri}")
                    
                except Exception as e3:
                    logger.warning(f"⚠️ 方法3失败: {e3}")
                    raise Exception(f"所有上传方法均失败: 方法1={e1}, 方法2={e2}, 方法3={e3}")
        
        # 🔧 **新增：等待文件处理完成**
        import time
        max_wait_time = 60  # 最大等待60秒
        wait_interval = 2   # 每2秒检查一次
        elapsed_time = 0
        
        logger.info("⏳ 等待文件处理完成...")
        
        while elapsed_time < max_wait_time:
            try:
                # 检查文件状态
                file_info = client.files.get(name=uploaded_file.name)
                file_state = getattr(file_info, 'state', 'UNKNOWN')
                
                logger.info(f"📊 文件状态检查: {file_state} (等待时间: {elapsed_time}s)")
                
                if file_state == 'ACTIVE':
                    logger.info("✅ 文件处理完成，状态为ACTIVE")
                    break
                elif file_state == 'FAILED':
                    raise Exception("文件处理失败")
                else:
                    # 继续等待
                    time.sleep(wait_interval)
                    elapsed_time += wait_interval
                    
            except Exception as status_error:
                logger.warning(f"⚠️ 状态检查失败: {status_error}")
                time.sleep(wait_interval)
                elapsed_time += wait_interval
        
        if elapsed_time >= max_wait_time:
            logger.warning(f"⚠️ 文件处理超时（{max_wait_time}s），尝试继续分析")
        
        logger.info(f"🎬 开始视频分析，模型: {self.gemini_model}")
        
        # 调用视频分析API
        response = client.models.generate_content(
            model=self.gemini_model,
            contents=[prompt, uploaded_file]
        )
        
        if not response or not response.text:
            raise Exception("Gemini API返回空响应")
        
        logger.info(f"📊 Gemini分析完成，响应长度: {len(response.text)}字符")
        logger.info(f"📝 Gemini原始响应开头: {response.text[:200]}...")
        
        # 清理上传的文件
        try:
            client.files.delete(name=uploaded_file.name)
            logger.info("🗑️ 临时文件已清理")
        except Exception as cleanup_error:
            logger.warning(f"⚠️ 清理临时文件失败: {cleanup_error}")
        
        # 🔧 **新方案**：保持原始输出完整性，不强制解析
        logger.info("📋 保持Gemini原始输出格式，交由后续统一处理")
        
        return {
            'success': True,
            'content': response.text,  # 直接返回原始文本
            'model': 'gemini'
        }
            
    except Exception as e:
        logger.error(f"❌ Gemini API调用异常: {e}")
        return {
            'success': False,
            'error': str(e),
            'model': 'gemini'
        }
"""

