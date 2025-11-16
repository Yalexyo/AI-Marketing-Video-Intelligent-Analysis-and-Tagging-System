#!/usr/bin/env python3
"""
🤖 基础AI分类器抽象类 - Base AI Classifier Abstract Class
为所有AI分类器提供统一的基础框架和共同功能
减少代码重复，提高维护性

设计原则:
- 单一职责：专注于AI分类的通用逻辑
- 开放封闭：对扩展开放，对修改封闭
- 模板方法：定义分类流程的骨架
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# 统一AI客户端集成
try:
    from .unified_ai_client import UnifiedAIClient
    from .unified_ai_config_manager import TaskType
except ImportError:
    from unified_ai_client import UnifiedAIClient
    from unified_ai_config_manager import TaskType

logger = logging.getLogger(__name__)

class BaseAIClassifier(ABC):
    """基础AI分类器抽象类 - 提供通用分类框架"""
    
    def __init__(self, task_type: TaskType):
        """
        初始化基础AI分类器
        
        Args:
            task_type: 任务类型，用于配置统一AI客户端
        """
        self.task_type = task_type
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # 初始化统一AI客户端
        self.ai_client = UnifiedAIClient(task_type)
        
        # 子类必须实现的提示词模板
        self.classification_prompts = self._build_classification_prompts()
        
        self.logger.info(f"✅ {self.__class__.__name__} 初始化完成")
        self.logger.info(f"🤖 可用API: {', '.join(self.ai_client.get_available_models())}")
        self.logger.info(f"🎯 任务类型: {task_type.value}")
    
    @abstractmethod
    def _build_classification_prompts(self) -> Dict[str, str]:
        """
        构建分类提示词模板 - 子类必须实现
        
        Returns:
            Dict[str, str]: 提示词模板字典
        """
        pass
    
    def _call_ai_api(self, user_message: str, prompt_key: str = "default") -> Optional[Dict[str, Any]]:
        """
        调用AI API进行分类 - 通用方法
        
        Args:
            user_message: 用户输入的待分类内容
            prompt_key: 提示词模板键名
            
        Returns:
            Optional[Dict[str, Any]]: AI分析结果
        """
        try:
            # 获取提示词
            if prompt_key not in self.classification_prompts:
                self.logger.error(f"未找到提示词模板: {prompt_key}")
                return None

            system_prompt = self.classification_prompts[prompt_key]
            
            # 构建完整的用户消息
            full_prompt = f"{system_prompt}\n\n{user_message}"
            
            # 调用统一AI客户端
            result = self.ai_client.call_ai(
                prompt="你是专业的内容分析专家，严格按照JSON格式输出分析结果。",
                user_message=full_prompt
            )
            
            if not result or not result.success:
                self.logger.error(f"AI API调用失败: {result.error if result else 'API调用返回空'}")
                return None
            
            # 解析JSON响应
            import json
            try:
                content = result.data if result and result.data else ""
                if not content:
                    self.logger.error("AI响应内容为空")
                    return None
                
                # 尝试提取JSON部分
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    ai_response = json.loads(json_str)
                    self.logger.info(f"✅ AI分析成功")
                    return ai_response
                else:
                    self.logger.error("AI响应中未找到有效JSON格式")
                    return None
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"AI响应JSON解析失败: {e}")
                self.logger.debug(f"AI原始响应: {result.data if result and result.data else ''}")
                return None
                
        except Exception as e:
            self.logger.error(f"AI API调用异常: {e}")
            return None
    
    def _get_confidence_level(self, score: float) -> str:
        """
        获取置信度等级描述 - 通用方法
        
        Args:
            score: 置信度分数 (0.0-1.0)
            
        Returns:
            str: 置信度等级描述
        """
        if score >= 0.9:
            return "极高"
        elif score >= 0.7:
            return "高"
        elif score >= 0.5:
            return "中等"
        elif score >= 0.3:
            return "较低"
        else:
            return "低"
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳 - 通用方法"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _normalize_confidence(self, confidence: Any) -> float:
        """
        标准化置信度值 - 通用方法
        
        Args:
            confidence: 原始置信度值
            
        Returns:
            float: 标准化后的置信度 (0.0-1.0)
        """
        try:
            conf_float = float(confidence)
            return max(0.0, min(1.0, conf_float))
        except (ValueError, TypeError):
            self.logger.warning(f"无效的置信度值: {confidence}")
            return 0.0
    
    def _extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """
        从内容中提取关键词 - 通用方法
        
        Args:
            content: 待分析内容
            max_keywords: 最大关键词数量
            
        Returns:
            List[str]: 提取的关键词列表
        """
        # 简单的关键词提取（可以后续优化为更智能的方法）
        import re
        
        # 移除标点符号，分割单词
        words = re.findall(r'\b\w+\b', content.lower())
        
        # 过滤停用词（简化版）
        stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', '等', '了', '着', '过'}
        keywords = [word for word in words if word not in stop_words and len(word) > 1]
        
        # 去重并返回前N个
        unique_keywords = list(dict.fromkeys(keywords))
        return unique_keywords[:max_keywords]
    
    def classify(self, content: str, enhanced: bool = False) -> Optional[Dict[str, Any]]:
        """
        通用分类方法 - 模板方法，子类可重写
        
        Args:
            content: 待分类的内容
            enhanced: 是否使用增强模式
            
        Returns:
            Optional[Dict[str, Any]]: 分类结果
        """
        try:
            # 选择提示词模板
            prompt_key = "enhanced" if enhanced else "standard"
            if prompt_key not in self.classification_prompts:
                prompt_key = list(self.classification_prompts.keys())[0]  # 使用第一个可用的
            
            # 调用AI API
            result = self._call_ai_api(content, prompt_key)
            
            if result:
                # 添加通用的元数据
                result.update({
                    "processed_at": self._get_timestamp(),
                    "confidence_level": self._get_confidence_level(result.get("confidence", 0.0)),
                    "enhanced_mode": enhanced,
                    "classifier": self.__class__.__name__
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"分类异常: {e}")
            return {"error": str(e)}
    
    def batch_classify(self, items: List[Dict], min_confidence: float = 0.5) -> List[Dict]:
        """
        批量分类 - 模板方法，子类可重写
        
        Args:
            items: 待分类的项目列表，每个项目应包含 'text' 和 'id' 字段
            min_confidence: 最小置信度阈值
            
        Returns:
            List[Dict]: 分类结果列表
        """
        results = []
        
        for item in items:
            try:
                text = item.get("text", "")
                item_id = item.get("id", f"item_{len(results)}")
                
                # 调用分类方法
                result = self.classify(text)
                
                if result and "error" not in result:
                    confidence = result.get("confidence", 0.0)
                    category = result.get("predicted_category") or result.get("secondary_category", "")
                    
                    # 构建结果
                    batch_result = {
                        "id": item_id,
                        "category": category,
                        "confidence": confidence,
                        "reasoning": result.get("reasoning", ""),
                        "matched_features": result.get("matched_features", []),
                        "success": confidence >= min_confidence
                    }
                else:
                    # 分类失败
                    batch_result = {
                        "id": item_id,
                        "category": "",
                        "confidence": 0.0,
                        "reasoning": result.get("error", "分类失败") if result else "API调用失败",
                        "matched_features": [],
                        "success": False
                    }
                
                results.append(batch_result)
                
            except Exception as e:
                self.logger.error(f"批量分类中单项处理失败: {e}")
                # 添加失败结果
                results.append({
                    "id": item.get("id", f"error_{len(results)}"),
                    "category": "",
                    "confidence": 0.0,
                    "reasoning": f"处理异常: {str(e)}",
                    "matched_features": [],
                    "success": False
                })
        
        return results
    
    def get_classification_stats(self) -> Dict[str, Any]:
        """
        获取分类统计信息 - 通用方法
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "classifier_type": self.__class__.__name__,
            "task_type": self.task_type.value,
            "available_models": self.ai_client.get_available_models(),
            "prompt_templates": list(self.classification_prompts.keys()),
            "initialization_time": self._get_timestamp()
        } 