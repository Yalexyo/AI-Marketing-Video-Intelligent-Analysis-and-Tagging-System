#!/usr/bin/env python3
"""
🤖 统一AI客户端
提供统一的AI API调用接口，支持多模型自动切换、错误处理和重试机制
实现 DeepSeek -> Claude -> 报错 的逻辑
"""

import json
import logging
import time
import requests
from typing import Dict, List, Optional, Any, Union
try:
    from .unified_ai_config_manager import (
        UnifiedAIConfigManager, ModelConfig, ModelSelectionStrategy, 
        TaskType, ModelType, get_ai_config_manager
    )
except ImportError:
    # 支持直接运行测试
    from unified_ai_config_manager import (
        UnifiedAIConfigManager, ModelConfig, ModelSelectionStrategy, 
        TaskType, ModelType, get_ai_config_manager
    )

logger = logging.getLogger(__name__)

class AICallResult:
    """AI调用结果封装"""
    
    def __init__(self, success: bool, data: Any = None, error: str = None, 
                 model_used: str = None, attempts: int = 0):
        self.success = success
        self.data = data
        self.error = error
        self.model_used = model_used
        self.attempts = attempts
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "model_used": self.model_used,
            "attempts": self.attempts,
            "timestamp": self.timestamp
        }

class UnifiedAIClient:
    """统一AI客户端"""
    
    def __init__(self, task_type: TaskType):
        """初始化AI客户端"""
        self.task_type = task_type
        self.config_manager = get_ai_config_manager()
        self.logger = logging.getLogger(f"{__name__}.{task_type.value}")
        
        # 获取任务配置
        self.model_configs, self.strategy = self.config_manager.get_model_selection_for_task(task_type)
        
        self.logger.info(f"🤖 统一AI客户端初始化完成 - 任务: {task_type.value}")
        self.logger.info(f"📋 可用模型: {[config.model_type.value for config in self.model_configs]}")
        self.logger.info(f"🎯 策略: 严格模式={self.strategy.strict_mode}, 回退={self.strategy.fallback_enabled}")
    
    def call_ai(self, prompt: str, user_message: str, **kwargs) -> AICallResult:
        """
        统一AI调用接口
        
        Args:
            prompt: 系统提示词
            user_message: 用户消息
            **kwargs: 额外参数
        
        Returns:
            AICallResult: 调用结果
        """
        total_attempts = 0
        last_error = None
        
        # 按优先级尝试每个模型
        for model_config in self.model_configs:
            model_attempts = 0
            
            while model_attempts < self.strategy.max_retries:
                total_attempts += 1
                model_attempts += 1
                
                try:
                    self.logger.info(f"🤖 尝试调用 {model_config.model_type.value} (第{model_attempts}次)")
                    
                    result = self._call_single_model(model_config, prompt, user_message, **kwargs)
                    
                    if result.success:
                        self.logger.info(f"✅ {model_config.model_type.value} 调用成功")
                        result.attempts = total_attempts
                        return result
                    else:
                        last_error = result.error
                        self.logger.warning(f"⚠️ {model_config.model_type.value} 调用失败: {result.error}")
                        
                        # 如果不是严格模式，单个模型成功即可
                        if not self.strategy.strict_mode:
                            break
                
                except Exception as e:
                    last_error = str(e)
                    self.logger.error(f"❌ {model_config.model_type.value} 调用异常: {e}")
                
                # 重试间隔
                if model_attempts < self.strategy.max_retries:
                    time.sleep(1)
            
            self.logger.warning(f"⚠️ {model_config.model_type.value} 经过 {self.strategy.max_retries} 次尝试后失败")
        
        # 所有模型都失败了
        error_message = f"❌ 所有模型调用失败，最后错误: {last_error}"
        self.logger.error(error_message)
        
        return AICallResult(
            success=False,
            error=error_message,
            attempts=total_attempts
        )
    
    def _call_single_model(self, config: ModelConfig, prompt: str, user_message: str, **kwargs) -> AICallResult:
        """调用单个模型"""
        try:
            if config.model_type == ModelType.DEEPSEEK:
                return self._call_deepseek(config, prompt, user_message, **kwargs)
            elif config.model_type == ModelType.CLAUDE:
                return self._call_claude_via_openrouter(config, prompt, user_message, **kwargs)
            else:
                return AICallResult(
                    success=False,
                    error=f"不支持的模型类型: {config.model_type.value}",
                    model_used=config.model_type.value
                )
        
        except Exception as e:
            return AICallResult(
                success=False,
                error=f"模型调用异常: {str(e)}",
                model_used=config.model_type.value
            )
    
    def _call_deepseek(self, config: ModelConfig, prompt: str, user_message: str, **kwargs) -> AICallResult:
        """调用DeepSeek模型"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.model_name,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": kwargs.get("temperature", config.temperature),
            "max_tokens": kwargs.get("max_tokens", config.max_tokens),
            "stream": False
        }
        
        response = requests.post(
            config.api_url,
            headers=headers,
            json=payload,
            timeout=config.timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            return AICallResult(
                success=True,
                data=content,
                model_used=config.model_type.value
            )
        else:
            return AICallResult(
                success=False,
                error=f"DeepSeek API错误: {response.status_code} - {response.text}",
                model_used=config.model_type.value
            )
    
    def _call_claude_via_openrouter(self, config: ModelConfig, prompt: str, user_message: str, **kwargs) -> AICallResult:
        """通过OpenRouter调用Claude模型"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ai-video-analysis",
            "X-Title": "AI Video Analysis Tool"
        }
        
        payload = {
            "model": config.model_name,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": kwargs.get("temperature", config.temperature),
            "max_tokens": kwargs.get("max_tokens", config.max_tokens)
        }
        
        response = requests.post(
            config.api_url,
            headers=headers,
            json=payload,
            timeout=config.timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            return AICallResult(
                success=True,
                data=content,
                model_used=config.model_type.value
            )
        else:
            return AICallResult(
                success=False,
                error=f"Claude API错误: {response.status_code} - {response.text}",
                model_used=config.model_type.value
            )
    

    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [config.model_type.value for config in self.model_configs]
    
    def get_current_strategy(self) -> Dict[str, Any]:
        """获取当前策略信息"""
        return {
            "task_type": self.task_type.value,
            "available_models": self.get_available_models(),
            "strict_mode": self.strategy.strict_mode,
            "fallback_enabled": self.strategy.fallback_enabled,
            "max_retries": self.strategy.max_retries
        }

# 便捷函数
def create_ai_client(task_type: TaskType) -> UnifiedAIClient:
    """创建AI客户端的便捷函数"""
    return UnifiedAIClient(task_type)

def call_ai_for_task(task_type: TaskType, prompt: str, user_message: str, **kwargs) -> AICallResult:
    """为指定任务调用AI的便捷函数"""
    client = create_ai_client(task_type)
    return client.call_ai(prompt, user_message, **kwargs)

if __name__ == "__main__":
    # 测试统一AI客户端 - 专注于文本分类任务
    print("🧪 测试统一AI客户端（文本分类专用）")
    print("=" * 60)
    
    try:
        # 测试主标签分类
        main_tag_client = UnifiedAIClient(TaskType.MAIN_TAG_CLASSIFICATION)
        print(f"📋 主标签分类客户端配置: {main_tag_client.get_current_strategy()}")
        
        # 测试二级标签分类
        secondary_tag_client = UnifiedAIClient(TaskType.SECONDARY_TAG_CLASSIFICATION)
        print(f"📋 二级标签分类客户端配置: {secondary_tag_client.get_current_strategy()}")
        
        print(f"\n🎯 配置特点:")
        print(f"   - 主标签分类: 支持回退，单个模型成功即可")
        print(f"   - 二级标签分类: 严格模式，DeepSeek->Claude->报错")
        print(f"   - 仅支持文本分类，不包含视觉模型")
        
        # 模拟简单的AI调用测试
        test_prompt = "你是一个专业的婴幼儿奶粉视频分析专家。"
        test_message = "请对以下标签进行分类测试：营养配方、A2蛋白、便携装"
        
        print(f"\n🧪 执行AI调用测试...")
        result = main_tag_client.call_ai(test_prompt, test_message)
        
        if result.success:
            print(f"✅ 测试成功 - 使用模型: {result.model_used}")
            print(f"📄 响应内容: {result.data[:100]}...")
        else:
            print(f"❌ 测试失败: {result.error}")
        
    except Exception as e:
        print(f"❌ 测试异常: {e}") 