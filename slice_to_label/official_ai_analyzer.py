#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
官方规范AI分析器
严格按照阿里云DashScope和DeepSeek官方API规范实现
"""

import os
import sys
import json
import logging
import requests
import base64
import time
try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except ImportError as e:
    print(f"❌ 缺少依赖包: {e}")
    print("💡 请运行: uv add opencv-python numpy")
    sys.exit(1)
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入环境变量加载器和智能关键帧提取器
from src.env_loader import load_environment
from src.smart_frame_extractor import SmartFrameExtractor

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OfficialAIAnalyzer:
    """严格符合官方规范的AI分析器"""
    
    def __init__(self):
        """初始化分析器"""
        # 自动加载.env文件
        env_loader = load_environment()
        
        self.dashscope_key = os.getenv("DASHSCOPE_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        
        if not self.dashscope_key:
            raise ValueError("❌ 未找到DASHSCOPE_API_KEY环境变量")
        if not self.deepseek_key:
            raise ValueError("❌ 未找到DEEPSEEK_API_KEY环境变量")
            
        # 官方API端点
        self.dashscope_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        self.deepseek_url = "https://api.deepseek.com/chat/completions"
        
        # 配置参数
        self.qwen_model = "qwen-vl-max-latest"
        self.deepseek_model = "deepseek-chat"
        self.fps = 2.0  # 视频抽帧频率
        self.max_retries = 3
        self.timeout = 60
        
        # 初始化智能关键帧提取器
        self.frame_extractor = SmartFrameExtractor()
        
        logger.info("✅ 官方规范AI分析器初始化完成（已集成智能关键帧提取）")
    
    def analyze_video_dual_stage(self, video_path: str) -> Dict[str, Any]:
        """
        双层识别机制分析视频
        严格按照项目设计的双层架构实现
        """
        try:
            file_info = Path(video_path)
            logger.info(f"🎯 开始双层AI分析: {file_info.name}")
            
            # 提取关键帧
            frames = self._extract_key_frames(video_path)
            if not frames:
                raise ValueError("无法提取视频帧")
            
            # 第一层：AI-B通用识别（禁止品牌识别）
            stage1_result = self._stage1_general_analysis(frames[0])
            
            # 判断是否触发第二层
            trigger_brand = self._should_trigger_brand_detection(stage1_result)
            
            if trigger_brand:
                logger.info("🔍 触发第二层品牌检测")
                # 第二层：AI-A品牌专用检测
                stage2_result = self._stage2_brand_detection(frames[0])
                brand_elements = stage2_result.get("brand_elements", "无")
            else:
                logger.info("⚪ 未触发品牌检测条件")
                brand_elements = "无"
            
            # 合并结果
            final_result = {
                **stage1_result,
                "brand_elements": brand_elements,
                "analysis_method": "official_dual_stage",
                "stage1_triggered": True,
                "stage2_triggered": trigger_brand,
                "file_name": file_info.name,
                "file_size_mb": round(file_info.stat().st_size / (1024 * 1024), 2),
                "processed_at": datetime.now().isoformat(),
                "success": True
            }
            
            logger.info(f"✅ 双层分析完成: {stage1_result.get('object', '未知')}")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 双层分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "file_name": Path(video_path).name,
                "analysis_method": "official_dual_stage"
            }
    
    def _extract_key_frames(self, video_path: str) -> List[np.ndarray]:
        """使用智能关键帧提取器提取视频关键帧"""
        try:
            # 使用智能关键帧提取器
            key_frames_data = self.frame_extractor.extract_key_frames(video_path)
            
            if key_frames_data:
                # 提取帧数据
                frames = [frame_data["frame"] for frame_data in key_frames_data]
                
                logger.info(f"🖼️ 智能提取了 {len(frames)} 个关键帧")
                
                # 打印帧信息
                for i, frame_data in enumerate(key_frames_data):
                    logger.info(f"   帧{i+1}: {frame_data['timestamp']:.2f}s (方法: {frame_data['extraction_method']})")
                
                return frames
            else:
                logger.error(f"❌ 智能关键帧提取失败: 返回空结果")
                return []
            
        except Exception as e:
            logger.error(f"❌ 关键帧提取器异常: {str(e)}")
            return []
    
    def _frame_to_base64(self, frame: np.ndarray) -> str:
        """将帧转换为base64编码"""
        try:
            # 调整图片大小以符合API限制
            height, width = frame.shape[:2]
            if width > 1024 or height > 1024:
                scale = min(1024/width, 1024/height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # 编码为JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # 转换为base64
            base64_str = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{base64_str}"
            
        except Exception as e:
            logger.error(f"❌ 帧转base64失败: {str(e)}")
            return ""
    
    def _stage1_general_analysis(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        第一层：通用识别分析（严格禁止品牌识别）
        使用官方Qwen-VL API
        """
        try:
            # 转换帧为base64
            image_base64 = self._frame_to_base64(frame)
            if not image_base64:
                raise ValueError("图片转换失败")
            
            # 构建官方格式的请求
            prompt = """仔细分析画面内容，无论是否有人物都要详细描述。

1. **interaction**: 用"主语+动词+宾语"描述核心事件或物体状态
   - 有人物时：如"宝宝拒绝奶瓶", "妈妈冲泡奶粉"
   - 无人物时：如"奶粉罐展示营养标签", "产品摆放桌面"

2. **scene**: 描述场景环境 (室内/户外，具体位置)

3. **emotion**: 分析画面传达的情绪或氛围：
   - 有人物时：重点观察面部表情、肢体语言，判断真实情绪状态
   - 无人物时：分析画面营造的整体氛围（如专业、温馨、清新等）
   - 选择词汇：哭闹/痛苦/拒绝/不开心/难受(负面) | 专注/平静/中性状态(中性) | 开心/温馨/愉悦(正面)

输出格式：
interaction: [行为描述或物体状态]
scene: [场景描述]  
emotion: [单个词汇]"""
            
            # 按官方格式构建请求
            payload = {
                "model": self.qwen_model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"image": image_base64},
                                {"text": prompt}
                            ]
                        }
                    ]
                },
                "parameters": {
                    "max_tokens": 600,
                    "temperature": 0.05
                }
            }
            
            # 发送请求
            response = self._make_dashscope_request(payload)
            result_text = response.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 解析结果
            parsed_result = self._parse_stage1_result(result_text)
            
            logger.info(f"✅ 第一层分析完成: {parsed_result.get('object', '未知')}")
            return parsed_result
            
        except Exception as e:
            logger.error(f"❌ 第一层分析失败: {str(e)}")
            return {
                "object": "分析失败",
                "scene": "未知",
                "emotion": "未知",
                "confidence": 0.0,
                "stage1_error": str(e)
            }
    
    def _stage2_brand_detection(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        第二层：品牌专用检测
        使用官方Qwen-VL API进行品牌识别
        """
        try:
            # 转换帧为base64
            image_base64 = self._frame_to_base64(frame)
            if not image_base64:
                raise ValueError("图片转换失败")
            
            # 品牌检测专用prompt (精简版)
            brand_prompt = """识别画面中的奶粉品牌标识。

目标品牌：启赋, illuma, 惠氏, Wyeth, 蕴淳, A2, ATWO, HMO

要求：
- 只识别列表中的品牌
- 必须清晰可见
- 如无发现输出"无"

输出格式：品牌名称或"无\""""
            
            # 按官方格式构建请求
            payload = {
                "model": self.qwen_model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"image": image_base64},
                                {"text": brand_prompt}
                            ]
                        }
                    ]
                },
                "parameters": {
                    "max_tokens": 500,
                    "temperature": 0.05
                }
            }
            
            # 发送请求
            response = self._make_dashscope_request(payload)
            result_text = response.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 解析品牌结果 - 处理list类型的content
            if isinstance(result_text, list):
                if len(result_text) > 0 and isinstance(result_text[0], dict):
                    # 如果是字典，尝试提取text字段
                    brand_elements = result_text[0].get('text', str(result_text[0]))
                else:
                    brand_elements = str(result_text[0]) if result_text else "无"
            else:
                brand_elements = result_text
            
            brand_elements = brand_elements.strip() if brand_elements else "无"
            if not brand_elements or brand_elements.lower() in ["无", "none", "无品牌"]:
                brand_elements = "无"
            
            logger.info(f"✅ 第二层品牌检测完成: {brand_elements}")
            return {
                "brand_elements": brand_elements,
                "stage2_confidence": 0.9 if brand_elements != "无" else 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ 第二层品牌检测失败: {str(e)}")
            return {
                "brand_elements": "无",
                "stage2_error": str(e)
            }
    
    def _make_dashscope_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送DashScope API请求（官方格式）"""
        headers = {
            "Authorization": f"Bearer {self.dashscope_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"📡 发送DashScope请求 (尝试 {attempt + 1}/{self.max_retries})")
                
                response = requests.post(
                    self.dashscope_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("✅ DashScope请求成功")
                    return result
                else:
                    logger.warning(f"⚠️ DashScope请求失败: {response.status_code} - {response.text}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # 指数退避
                    
            except Exception as e:
                logger.error(f"❌ DashScope请求异常: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        
        raise Exception("DashScope API请求失败，已达到最大重试次数")
    
    def _should_trigger_brand_detection(self, stage1_result: Dict[str, Any]) -> bool:
        """判断是否触发第二层品牌检测"""
        trigger_keywords = [
            "奶粉", "奶瓶", "产品", "罐", "包装", "冲泡", "喂养", "喝奶", "配方奶"
        ]
        
        interaction = stage1_result.get("object", "").lower()
        scene = stage1_result.get("scene", "").lower()
        
        # 检查交互和场景中是否包含触发关键词
        text_to_check = f"{interaction} {scene}"
        return any(keyword in text_to_check for keyword in trigger_keywords)
    
    def _parse_stage1_result(self, result_text: Any) -> Dict[str, Any]:
        """解析第一层分析结果"""
        try:
            # 如果result_text是list，提取第一个元素
            text_content = ""
            if isinstance(result_text, list):
                if len(result_text) > 0 and isinstance(result_text[0], dict):
                    # 如果是字典，尝试提取text字段
                    dict_item = result_text[0]
                    text_content = dict_item.get('text', str(dict_item))
                else:
                    text_content = str(result_text[0]) if result_text else ""
            else:
                text_content = str(result_text) if result_text else ""
            
            lines = text_content.strip().split('\n')
            result = {
                "object": "未知交互",
                "scene": "未知场景", 
                "emotion": "未知",
                "confidence": 0.8
            }
            
            for line in lines:
                line = line.strip()
                if line.startswith("interaction:"):
                    result["object"] = line.replace("interaction:", "").strip()
                elif line.startswith("scene:"):
                    result["scene"] = line.replace("scene:", "").strip()
                elif line.startswith("emotion:"):
                    result["emotion"] = line.replace("emotion:", "").strip()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 解析第一层结果失败: {str(e)}")
            logger.error(f"   原始数据类型: {type(result_text)}")
            logger.error(f"   原始数据内容: {result_text}")
            return {
                "object": "解析失败",
                "scene": "未知",
                "emotion": "未知",
                "confidence": 0.0
            }

def _save_individual_analysis(result: Dict[str, Any], input_dir: str) -> str:
    """为每个视频保存单独的结构化分析文件"""
    try:
        # 确保输出目录存在
        output_dir = Path("data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取输入目录名称作为子目录
        input_path = Path(input_dir)
        dir_name = input_path.name
        structured_output_dir = output_dir / dir_name
        structured_output_dir.mkdir(exist_ok=True)
        
        # 生成清理后的文件名
        file_name = result.get("file_name", "unknown.mp4")
        video_name = Path(file_name).stem
        clean_name = "".join(c for c in video_name if c.isalnum() or c in ('_', '-'))
        
        # 构建结构化结果
        structured_result = {
            'file_info': {
                'filename': file_name,
                'file_path': result.get('file_path', ''),
                'file_size_mb': result.get('file_size_mb', 0),
                'directory': dir_name
            },
            'analysis_info': {
                'analysis_time': datetime.now().isoformat(),
                'analyzer_version': 'official_v1.0',
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
                'stage1_success': result.get('stage1_triggered', True),
                'stage2_success': result.get('stage2_triggered', False),
                'processing_time': result.get('processed_at', '')
            }
        }
        
        # 保存单独的JSON文件
        output_file = structured_output_dir / f"{clean_name}_analysis.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structured_result, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"💾 单独分析文件已保存: {output_file}")
        return str(output_file)
        
    except Exception as e:
        logger.error(f"保存单独分析文件失败: {e}")
        return ""

def analyze_videos_with_official_api(input_dir: str, max_files: int = 10) -> Dict[str, Any]:
    """使用官方API分析视频文件，并过滤无效文件"""
    try:
        analyzer = OfficialAIAnalyzer()
        
        # 扫描视频文件
        video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".m4v"]
        video_files = []
        filtered_count = 0  # 过滤文件计数
        
        def _should_filter_video_file(file_path: Path) -> bool:
            """判断视频文件是否应该被过滤"""
            # 🎯 用户反馈：多镜头视频也应该被分析，只过滤真正失败的文件
            # 只过滤❌前缀的文件（分析失败），♻️文件允许正常分析
            if file_path.stem.startswith("❌"):
                return True
            return False
        
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    file_path = Path(root) / file
                    # 🚨 新增：过滤逻辑
                    if _should_filter_video_file(file_path):
                        filtered_count += 1
                        logger.debug(f"🚫 过滤视频文件: {file_path.name} (质量问题)")
                        continue
                    video_files.append(os.path.join(root, file))
        
        if filtered_count > 0:
            logger.info(f"🚫 官方API分析过滤了 {filtered_count} 个质量问题视频文件")
        
        if max_files:
            video_files = video_files[:max_files]
        
        logger.info(f"📋 找到 {len(video_files)} 个视频文件，开始官方API分析")
        
        results = []
        failed_files = []
        
        for i, video_file in enumerate(video_files, 1):
            logger.info(f"🎬 处理进度: {i}/{len(video_files)} - {Path(video_file).name}")
            
            result = analyzer.analyze_video_dual_stage(video_file)
            
            if result.get("success"):
                results.append(result)
                
                # 为每个视频保存单独的结构化JSON文件
                _save_individual_analysis(result, input_dir)
            else:
                failed_files.append(result)
            
            # 添加延迟避免API限流
            if i < len(video_files):
                time.sleep(1)
        
        return {
            "total_analyzed": len(video_files),
            "successful_analyses": len(results),
            "failed_analyses": len(failed_files),
            "filtered_files": filtered_count,
            "results": results,
            "failed_files": failed_files
        }
        
    except Exception as e:
        logger.error(f"官方API分析失败: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import argparse
    
    # 自动加载.env文件
    print("🔧 正在加载环境配置...")
    env_loader = load_environment()
    
    # 验证配置
    if not env_loader.validate_config():
        print("❌ 环境配置不完整")
        print("💡 请检查项目根目录下的 .env 文件")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description="官方规范AI视频分析工具")
    parser.add_argument("--input", default="data/input", help="输入目录")
    parser.add_argument("--max-files", type=int, default=5, help="最大文件数")
    
    args = parser.parse_args()
    
    print("🚀 启动官方规范AI分析...")
    print(f"📁 输入目录: {args.input}")
    print(f"📊 最大文件数: {args.max_files}")
    print()
    
    # 分析视频
    report = analyze_videos_with_official_api(args.input, args.max_files)
    
    if "error" not in report:
        # 保存报告 - 使用结构化命名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_dir_name = Path(args.input).name if hasattr(args, 'input') else 'mixed'
        output_file = f"data/output/official_analysis_{input_dir_name}_{timestamp}.json"
        os.makedirs("data/output", exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 显示结果
        summary = report["summary"]
        print(f"\n📊 官方API分析完成:")
        print(f"📋 总文件数: {summary['total_files']}")
        print(f"✅ 成功文件: {summary['successful_files']}")
        print(f"❌ 失败文件: {summary['failed_files']}")
        print(f"📈 成功率: {summary['success_rate']}")
        print(f"🔧 API版本: {summary['api_version']}")
        print(f"📁 报告文件: {output_file}")
        
        # 显示分析结果示例
        if report["results"]:
            print(f"\n🎯 分析结果示例:")
            for i, result in enumerate(report["results"][:3], 1):
                print(f"\n{i}. {result['file_name']} ({result['file_size_mb']}MB)")
                print(f"   📋 交互行为: {result.get('object', '未知')}")
                print(f"   🏠 场景环境: {result.get('scene', '未知')}")
                print(f"   😊 情绪状态: {result.get('emotion', '未知')}")
                print(f"   🏷️ 品牌元素: {result.get('brand_elements', '无')}")
                print(f"   🔍 第一层: ✅ | 第二层: {'✅' if result.get('stage2_triggered') else '⚪'}")
    else:
        print(f"❌ 分析失败: {report['error']}")
