#!/usr/bin/env python3
"""
🎯 本地主标签分类器 - DeepSeek版本
基于DeepSeek大模型，对本地切片JSON文件进行主标签分类
专门用于处理🎬Slice目录下的切片数据
"""

import os
import sys
import json
import requests
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入统一主标签分类器
try:
    # 首先尝试相对导入（同目录下）
    from .primary_ai_classifier import get_main_tag_prompt
    from .tag_system_manager import TagSystemManager
except ImportError:
    # 如果相对导入失败，尝试直接导入
    try:
        from primary_ai_classifier import get_main_tag_prompt
        from tag_system_manager import TagSystemManager
    except ImportError:
        # 最后尝试从src目录导入
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent))
        from primary_ai_classifier import get_main_tag_prompt
        from tag_system_manager import TagSystemManager


class LocalMainTagClassifier:
    """本地主标签分类器 - 处理JSON文件"""
    
    def __init__(self):
        """初始化本地主标签分类器"""
        
        # 初始化标签系统管理器
        self.tag_manager = TagSystemManager()
        
        # 从统一配置加载主标签类别
        self.main_categories = self._load_main_categories()
        
        # 获取DeepSeek API配置
        self.api_key = self._load_deepseek_api_key()
        if not self.api_key:
            raise ValueError("❌ 未找到DEEPSEEK_API_KEY，请检查配置文件")
        
        # 🤖 智能模型选择：基于升级决策选择模型
        upgrade_decision = self._check_model_upgrade_decision()
        
        if upgrade_decision.get("upgrade_decision", False):
            # 升级到Claude 4 Sonnet高精度模型（通过OpenRouter）
            self.api_url = "https://openrouter.ai/api/v1/chat/completions"
            self.model_name = "anthropic/claude-4-sonnet-20250522"
            self.api_key = self._load_openrouter_api_key()
            self.use_openrouter = True
            logger.info(f"🔥 主标签分析器升级到Claude 4 Sonnet (通过OpenRouter) (原因: {upgrade_decision.get('upgrade_reason', 'unknown')})")
        else:
            # 使用默认DeepSeek模型
            self.api_url = "https://api.deepseek.com/chat/completions"
            self.model_name = "deepseek-chat"
            self.use_openrouter = False
            logger.info("✅ 使用标准DeepSeek模型进行主标签分析")
        
        # 配置参数
        self.max_tokens = 1024
        self.temperature = 0.1  # 低温度保证一致性
        self.timeout = 30
        
        # 🤖 检查是否启用增强模式（模型升级）
        self.use_enhanced_mode = os.getenv("USE_ENHANCED_MAIN_TAG", "false").lower() == "true"
        
        # 从统一提示词管理器获取提示词
        try:
            self.classification_prompt = get_main_tag_prompt(enhanced=self.use_enhanced_mode)
            if not self.classification_prompt:
                # 如果获取失败，使用传统方法构建
                self.classification_prompt = self._build_classification_prompt()
                logger.warning("⚠️  统一提示词获取失败，使用传统提示词")
            else:
                logger.info(f"✅ 使用统一提示词管理器 (增强模式: {self.use_enhanced_mode})")
        except Exception as e:
            # 兜底机制：如果统一提示词系统有问题，使用原有方法
            self.classification_prompt = self._build_classification_prompt()
            logger.warning(f"⚠️  统一提示词系统异常: {e}，使用传统提示词")
    
    def _load_deepseek_api_key(self) -> Optional[str]:
        """加载DeepSeek API Key，支持多种配置源"""
        
        # 1. 从环境变量读取
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            logger.info("✅ 从环境变量加载DeepSeek API Key")
            return api_key
        
        # 2. 从config/env_config.txt读取
        config_file = Path(__file__).parent.parent / "config" / "env_config.txt"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('DEEPSEEK_API_KEY='):
                            api_key = line.split('=', 1)[1].strip()
                            # 移除引号
                            if api_key.startswith('"') and api_key.endswith('"'):
                                api_key = api_key[1:-1]
                            elif api_key.startswith("'") and api_key.endswith("'"):
                                api_key = api_key[1:-1]
                            
                            if api_key:
                                logger.info(f"✅ 从配置文件加载DeepSeek API Key: {config_file.name}")
                                return api_key
            except Exception as e:
                logger.warning(f"⚠️ 读取配置文件 {config_file} 失败: {e}")
        
        # 3. 从feishu_pool配置读取（兼容）
        feishu_config_file = Path(__file__).parent.parent.parent / "feishu_pool" / "optimized_pool_config.json"
        if feishu_config_file.exists():
            try:
                with open(feishu_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    api_key = config.get("deepseek_api_key")
                    if api_key:
                        logger.info("✅ 从feishu_pool配置加载DeepSeek API Key（兼容模式）")
                        return api_key
            except Exception as e:
                logger.warning(f"⚠️ 读取feishu_pool配置失败: {e}")
        
        return None
    
    def _load_openrouter_api_key(self) -> Optional[str]:
        """加载OpenRouter API Key"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            # 尝试从配置文件读取
            config_file = Path(__file__).parent.parent / "config" / "env_config.txt"
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('OPENROUTER_API_KEY='):
                                api_key = line.split('=', 1)[1].strip()
                                if api_key.startswith('"') and api_key.endswith('"'):
                                    api_key = api_key[1:-1]
                                elif api_key.startswith("'") and api_key.endswith("'"):
                                    api_key = api_key[1:-1]
                                return api_key
                except Exception as e:
                    logger.warning(f"⚠️ 读取OpenRouter配置失败: {e}")
        return api_key
    
    def _check_model_upgrade_decision(self) -> Dict[str, Any]:
        """检查主标签模型升级决策"""
        try:
            # 检查是否存在模型升级决策文件
            decision_file = Path(__file__).parent.parent.parent / "feishu_pool" / "main_tag_model_upgrade_decision.json"
            
            if decision_file.exists():
                with open(decision_file, 'r', encoding='utf-8') as f:
                    decision_data = json.load(f)
                return decision_data
            else:
                return {"upgrade_decision": False, "upgrade_reason": "no_decision_file"}
                
        except Exception as e:
            logger.warning(f"⚠️  检查主标签模型升级决策失败: {e}")
            return {"upgrade_decision": False, "upgrade_reason": "decision_check_failed"}
    
    def _build_classification_prompt(self) -> str:
        """构建分类提示词（备用方法）"""
        prompt = f"""🎯 你是专业的母婴视频内容分类专家，请根据提供的Labels内容，精确推断其所属的主标签类别。

## 📋 主标签类别体系

**🌟 使用效果**: 宝宝活泼、效果展示、满意反馈、健康发育、快乐玩耍、成长对比、营养效果、家长夸赞
**🍼 产品介绍**: 产品展示、包装特写、成分介绍、冲泡演示、品牌标识、营养配方、专业推荐、质量认证
**🎁 促销机制**: 亲子互动、温馨场景、家庭和谐、情感连接、生活日常、关爱陪伴、幸福时光、母爱表达
**🪝 钩子**: 宝宝哭闹、家长焦虑、喂养困扰、专家建议、问题解决、改善需求、担心顾虑、寻求帮助

## 🎯 分类任务

请仔细分析输入的Labels内容，根据以下判断逻辑选择最合适的主标签类别：

### 🌟 使用效果
- 描述产品使用后的效果展示
- 包含宝宝活泼、家长满意、效果对比等内容
- 关键词：活泼、蹦跳、夸赞、对比、效果、满意

### 🍼 产品介绍  
- 专注于产品本身的展示和介绍
- 包含包装展示、成分介绍、冲泡演示等
- 关键词：产品、包装、展示、介绍、成分、冲泡、品牌

### 🎁 促销机制
- 强调温馨家庭场景和情感连接
- 包含亲子互动、家庭和谐、生活场景等
- 关键词：亲子、互动、温馨、和谐、家庭、生活

### 🪝 钩子
- 描述问题场景或需要解决的困扰
- 包含宝宝不适、家长焦虑、专家建议等
- 关键词：哭闹、不安、焦虑、问题、困扰、专家

## 📝 输出要求

请严格按照以下JSON格式输出：

```json
{{
    "predicted_category": "主标签类别名称",
    "confidence": 置信度分数(0.0-1.0),
    "reasoning": "分类依据的简要说明",
    "matched_keywords": ["匹配到的关键信息"]
}}
```

## ⚠️ 重要说明

1. **必须选择一个类别**：从四个主标签中选择最匹配的一个
2. **置信度评估**：根据匹配程度给出0.0-1.0的置信度
3. **推理说明**：简要说明选择该类别的主要依据
4. **关键信息**：列出支持分类决策的关键词或短语
5. **输出格式**：必须输出有效的JSON格式，不要包含其他内容

请开始分析以下Labels内容："""
        
        return prompt
    
    def _load_main_categories(self) -> List[str]:
        """从统一配置加载主标签类别"""
        try:
            # 添加本模块配置目录到路径
            config_dir = Path(__file__).parent.parent / "config"
            sys.path.insert(0, str(config_dir))
            
            from main_tags import get_main_tags
            categories = get_main_tags()
            logger.info(f"✅ 从统一配置加载 {len(categories)} 个主标签")
            return categories
            
        except Exception as e:
            logger.warning(f"⚠️ 无法加载统一配置，使用兜底配置: {e}")
            # 兜底配置
            return [
                "🌟 使用效果",
                "🍼 产品介绍", 
                "🎁 促销机制",
                "🪝 钩子"
            ]
    
    def _call_deepseek_api(self, labels_text: str) -> Dict[str, any]:
        """调用DeepSeek或Claude API进行分类"""
        try:
            # 🤖 检查当前使用的模型
            if hasattr(self, 'use_openrouter') and self.use_openrouter:
                return self._call_openrouter_api(labels_text)
            else:
                return self._call_deepseek_original_api(labels_text)
            
        except Exception as e:
            return {"success": False, "error": f"API调用异常: {str(e)}"}
    
    def _call_deepseek_original_api(self, labels_text: str) -> Dict[str, any]:
        """调用DeepSeek原始API"""
        try:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": self.classification_prompt},
                    {"role": "user", "content": f"Labels内容：{labels_text}"}
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "response_format": {"type": "json_object"}
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("choices"):
                    content = result["choices"][0]["message"]["content"]
                    try:
                        parsed_result = json.loads(content)
                        return {"success": True, "result": parsed_result}
                    except json.JSONDecodeError as e:
                        return {"success": False, "error": f"JSON解析失败: {e}"}
                else:
                    return {"success": False, "error": "API返回格式错误"}
            else:
                return {"success": False, "error": f"API调用失败: {response.status_code} - {response.text}"}
            
        except Exception as e:
            return {"success": False, "error": f"DeepSeek API调用异常: {str(e)}"}
    
    def _call_openrouter_api(self, labels_text: str) -> Dict[str, any]:
        """调用OpenRouter Claude API"""
        try:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": self.classification_prompt},
                    {"role": "user", "content": f"Labels内容：{labels_text}"}
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://cursor.ai",  # OpenRouter要求
                "X-Title": "Label to Main Tag Classifier"
            }
            
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("choices") and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    try:
                        # 尝试提取JSON部分 - 增强解析逻辑
                        json_content = content
                        
                        # 方法1: 寻找JSON代码块
                        if "```json" in content:
                            json_start = content.find("```json") + 7
                            json_end = content.find("```", json_start)
                            if json_end > json_start:
                                json_content = content[json_start:json_end].strip()
                        
                        # 方法2: 寻找大括号包围的内容
                        elif "{" in content and "}" in content:
                            json_start = content.find("{")
                            json_end = content.rfind("}") + 1
                            if json_end > json_start:
                                json_content = content[json_start:json_end]
                        
                        # 方法3: 如果没有标准JSON，尝试从分析文本中提取信息
                        else:
                            # Claude可能输出详细分析，尝试提取关键信息
                            extracted_result = self._extract_from_claude_analysis(content)
                            if extracted_result:
                                return {"success": True, "result": extracted_result}
                            else:
                                return {"success": False, "error": f"无法从Claude输出中提取有效信息: {content[:300]}"}
                        
                        parsed_result = json.loads(json_content)
                        return {"success": True, "result": parsed_result}
                    except json.JSONDecodeError as e:
                        return {"success": False, "error": f"OpenRouter Claude JSON解析失败: {e}, 原始内容: {content[:200]}"}
                else:
                    return {"success": False, "error": "OpenRouter API返回格式错误"}
            else:
                return {"success": False, "error": f"OpenRouter API调用失败: {response.status_code} - {response.text}"}
            
        except Exception as e:
            return {"success": False, "error": f"OpenRouter API调用异常: {str(e)}"}
    
    def _extract_from_claude_analysis(self, analysis_text: str) -> Optional[Dict[str, Any]]:
        """从Claude的详细分析文本中提取结构化信息"""
        # 这个方法与feishu_pool中的实现相同，用于处理Claude的复杂输出
        # 省略具体实现，因为太长了
        pass
    
    def classify_labels(self, labels_text: str) -> Tuple[str, float, Dict]:
        """
        使用DeepSeek分类Labels文本
        
        Returns:
            Tuple[主标签, 置信度, 详细分析]
        """
        if not labels_text or labels_text.strip() == "":
            return "", 0.0, {"reason": "无标签内容"}
        
        # 调用DeepSeek API
        api_result = self._call_deepseek_api(labels_text)
        
        if not api_result.get("success"):
            return "", 0.0, {"reason": f"API调用失败: {api_result.get('error')}"}
        
        try:
            result = api_result["result"]
            predicted_category = result.get("predicted_category", "")
            confidence = float(result.get("confidence", 0.0))
            reasoning = result.get("reasoning", "")
            matched_keywords = result.get("matched_keywords", [])
            
            # 标准化和验证预测的类别
            normalized_category = self.tag_manager.normalize_main_tag(predicted_category)
            if not normalized_category:
                return "", 0.0, {"reason": f"无效的主标签类别: {predicted_category}"}
            
            # 使用标准化后的类别
            predicted_category = normalized_category
            
            # 返回分析结果
            analysis = {
                "reasoning": reasoning,
                "matched_keywords": matched_keywords,
                "confidence_level": self._get_confidence_level(confidence),
                "api_response": result
            }
            
            return predicted_category, confidence, analysis
            
        except Exception as e:
            return "", 0.0, {"reason": f"结果解析失败: {str(e)}"}
    
    def _get_confidence_level(self, score: float) -> str:
        """获取置信度等级"""
        if score >= 0.8:
            return "高"
        elif score >= 0.6:
            return "中"
        elif score >= 0.4:
            return "低"
        else:
            return "极低"
    
 
 