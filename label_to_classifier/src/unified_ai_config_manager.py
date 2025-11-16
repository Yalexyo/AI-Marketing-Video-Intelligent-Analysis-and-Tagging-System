#!/usr/bin/env python3
"""
🤖 统一AI配置管理器
统一管理一级分类和二级分类的AI模型配置、密钥加载和模型选择逻辑
提高代码可维护性和一致性
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ModelType(Enum):
    """AI模型类型枚举 - 专注于文本分类模型"""
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"

class TaskType(Enum):
    """任务类型枚举 - 专注于文本分类任务"""
    MAIN_TAG_CLASSIFICATION = "main_tag_classification"
    SECONDARY_TAG_CLASSIFICATION = "secondary_tag_classification"

@dataclass
class ModelConfig:
    """AI模型配置数据类"""
    model_type: ModelType
    model_name: str
    api_url: str
    api_key: str
    max_tokens: int = 1024
    temperature: float = 0.1
    timeout: int = 30
    priority: int = 1  # 优先级，数字越小优先级越高

@dataclass
class ModelSelectionStrategy:
    """模型选择策略"""
    primary_models: List[ModelType]  # 主要模型列表，按优先级排序
    fallback_enabled: bool = False   # 是否启用回退机制
    strict_mode: bool = True         # 严格模式：所有模型都失败才报错
    max_retries: int = 2             # 每个模型的最大重试次数

class UnifiedAIConfigManager:
    """统一AI配置管理器"""
    
    def __init__(self):
        """初始化统一配置管理器"""
        self.logger = logging.getLogger(__name__)
        
        # 加载所有API密钥
        self.api_keys = self._load_all_api_keys()
        
        # 初始化模型配置
        self.model_configs = self._initialize_model_configs()
        
        # 初始化任务策略
        self.task_strategies = self._initialize_task_strategies()
        
        # 加载升级决策
        self.upgrade_decisions = self._load_upgrade_decisions()
        
        self.logger.info("✅ 统一AI配置管理器初始化完成")
        self._log_available_configs()
    
    def _load_all_api_keys(self) -> Dict[str, str]:
        """统一加载所有API密钥"""
        api_keys = {}
        
        # 定义密钥映射 - 仅文本分类相关模型
        key_mappings = {
            "DEEPSEEK_API_KEY": "deepseek",
            "OPENROUTER_API_KEY": "openrouter"
        }
        
        for env_key, config_key in key_mappings.items():
            api_key = self._load_single_api_key(env_key)
            if api_key:
                api_keys[config_key] = api_key
                self.logger.info(f"✅ {config_key} API密钥加载成功")
            else:
                self.logger.warning(f"⚠️ {config_key} API密钥未找到")
        
        return api_keys
    
    def _load_single_api_key(self, key_name: str) -> Optional[str]:
        """加载单个API密钥，支持多种配置源"""
        try:
            # 方法1: 环境变量
            api_key = os.getenv(key_name)
            if api_key:
                return api_key.strip()
            
            # 方法2: 根目录.env文件
            root_env_file = Path(__file__).parent.parent.parent / ".env"
            if root_env_file.exists():
                with open(root_env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(f"{key_name}="):
                            api_key = line.split("=", 1)[1].strip()
                            if api_key:
                                return api_key
            
            # 方法3: 模块配置文件
            config_file = Path(__file__).parent.parent / "config" / "env_config.txt"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(f"{key_name}="):
                            api_key = line.split("=", 1)[1].strip()
                            # 移除引号
                            if api_key.startswith('"') and api_key.endswith('"'):
                                api_key = api_key[1:-1]
                            elif api_key.startswith("'") and api_key.endswith("'"):
                                api_key = api_key[1:-1]
                            if api_key:
                                return api_key
            
            # 方法4: feishu_pool配置（兼容模式）
            feishu_config_file = Path(__file__).parent.parent.parent / "feishu_pool" / "optimized_pool_config.json"
            if feishu_config_file.exists():
                with open(feishu_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    api_key = config.get(key_name.lower())
                    if api_key:
                        return api_key
            
            return None
            
        except Exception as e:
            self.logger.warning(f"⚠️ 加载API密钥 {key_name} 失败: {e}")
            return None
    
    def _initialize_model_configs(self) -> Dict[ModelType, ModelConfig]:
        """初始化所有模型配置"""
        configs = {}
        
        # DeepSeek配置
        if "deepseek" in self.api_keys:
            configs[ModelType.DEEPSEEK] = ModelConfig(
                model_type=ModelType.DEEPSEEK,
                model_name="deepseek-chat",
                api_url="https://api.deepseek.com/chat/completions",
                api_key=self.api_keys["deepseek"],
                max_tokens=1024,
                temperature=0.1,
                timeout=30,
                priority=1
            )
        
        # Claude配置（通过OpenRouter）
        if "openrouter" in self.api_keys:
            configs[ModelType.CLAUDE] = ModelConfig(
                model_type=ModelType.CLAUDE,
                model_name="anthropic/claude-4-sonnet-20250522",
                api_url="https://openrouter.ai/api/v1/chat/completions",
                api_key=self.api_keys["openrouter"],
                max_tokens=1024,
                temperature=0.1,
                timeout=30,
                priority=2
            )
        

        
        return configs
    
    def _initialize_task_strategies(self) -> Dict[TaskType, ModelSelectionStrategy]:
        """初始化任务策略配置 - 专注于文本分类任务，严格模式+4次重试"""
        return {
            # 主标签分类策略：严格模式，支持升级决策，3次重试
            TaskType.MAIN_TAG_CLASSIFICATION: ModelSelectionStrategy(
                primary_models=[ModelType.DEEPSEEK, ModelType.CLAUDE],
                fallback_enabled=True,
                strict_mode=True,   # 🔥 改为严格模式：所有模型都尝试
                max_retries=3       # 🔄 调整为3次重试
            ),
            
            # 二级标签分类策略：DeepSeek优先，严格模式，3次重试
            TaskType.SECONDARY_TAG_CLASSIFICATION: ModelSelectionStrategy(
                primary_models=[ModelType.DEEPSEEK, ModelType.CLAUDE],  # DeepSeek优先
                fallback_enabled=True,   # 启用回退机制：DeepSeek失败→Claude
                strict_mode=True,        # 严格模式：两个都失败才报错
                max_retries=3            # 🔄 调整为3次重试
            )
        }
    
    def _load_upgrade_decisions(self) -> Dict[TaskType, Dict[str, Any]]:
        """加载升级决策配置 - 仅支持文本分类任务"""
        decisions = {}
        
        # 主标签分类升级决策
        main_tag_decision_file = Path(__file__).parent.parent.parent / "feishu_pool" / "main_tag_model_upgrade_decision.json"
        if main_tag_decision_file.exists():
            try:
                with open(main_tag_decision_file, 'r', encoding='utf-8') as f:
                    decisions[TaskType.MAIN_TAG_CLASSIFICATION] = json.load(f)
                    self.logger.info("✅ 主标签升级决策加载成功")
            except Exception as e:
                self.logger.warning(f"⚠️ 加载主标签升级决策失败: {e}")
        
        # 二级标签分类升级决策（未来扩展）
        secondary_tag_decision_file = Path(__file__).parent.parent.parent / "feishu_pool" / "secondary_tag_model_upgrade_decision.json"
        if secondary_tag_decision_file.exists():
            try:
                with open(secondary_tag_decision_file, 'r', encoding='utf-8') as f:
                    decisions[TaskType.SECONDARY_TAG_CLASSIFICATION] = json.load(f)
                    self.logger.info("✅ 二级标签升级决策加载成功")
            except Exception as e:
                self.logger.warning(f"⚠️ 加载二级标签升级决策失败: {e}")
        
        return decisions
    
    def get_model_selection_for_task(self, task_type: TaskType) -> Tuple[List[ModelConfig], ModelSelectionStrategy]:
        """获取指定任务的模型选择和策略"""
        strategy = self.task_strategies.get(task_type)
        if not strategy:
            raise ValueError(f"❌ 未找到任务类型 {task_type.value} 的策略配置")
        
        # 检查是否有升级决策
        upgrade_decision = self.upgrade_decisions.get(task_type, {})
        should_upgrade = upgrade_decision.get("upgrade_decision", False)
        
        # 根据升级决策调整模型顺序
        if should_upgrade and task_type == TaskType.MAIN_TAG_CLASSIFICATION:
            # 主标签分类升级：优先使用Claude
            if ModelType.CLAUDE in strategy.primary_models:
                ordered_models = [ModelType.CLAUDE] + [m for m in strategy.primary_models if m != ModelType.CLAUDE]
                strategy.primary_models = ordered_models
                self.logger.info(f"🔥 {task_type.value} 升级到Claude优先模式 (原因: {upgrade_decision.get('upgrade_reason', 'unknown')})")
        
        # 获取可用的模型配置
        available_configs = []
        for model_type in strategy.primary_models:
            if model_type in self.model_configs:
                available_configs.append(self.model_configs[model_type])
            else:
                self.logger.warning(f"⚠️ 模型 {model_type.value} 配置不可用（缺少API密钥）")
        
        if not available_configs:
            raise ValueError(f"❌ 任务 {task_type.value} 没有可用的模型配置")
        
        return available_configs, strategy
    
    def get_single_model_config(self, task_type: TaskType, model_type: Optional[ModelType] = None) -> ModelConfig:
        """获取单个模型配置（兼容旧接口）"""
        available_configs, strategy = self.get_model_selection_for_task(task_type)
        
        if model_type:
            # 指定模型类型
            for config in available_configs:
                if config.model_type == model_type:
                    return config
            raise ValueError(f"❌ 指定的模型 {model_type.value} 在任务 {task_type.value} 中不可用")
        else:
            # 返回第一个可用的模型
            return available_configs[0]
    
    def _log_available_configs(self):
        """记录可用配置信息"""
        self.logger.info(f"🤖 可用模型: {', '.join([model.value for model in self.model_configs.keys()])}")
        
        for task_type, strategy in self.task_strategies.items():
            available_models = [model.value for model in strategy.primary_models if model in self.model_configs]
            self.logger.info(f"📋 {task_type.value}: {', '.join(available_models)} (严格模式: {strategy.strict_mode})")
    
    def validate_configuration(self) -> Dict[str, Any]:
        """验证配置完整性"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "summary": {}
        }
        
        # 检查每个任务类型的配置
        for task_type in TaskType:
            try:
                available_configs, strategy = self.get_model_selection_for_task(task_type)
                validation_result["summary"][task_type.value] = {
                    "available_models": len(available_configs),
                    "model_names": [config.model_type.value for config in available_configs],
                    "strategy": {
                        "strict_mode": strategy.strict_mode,
                        "fallback_enabled": strategy.fallback_enabled,
                        "max_retries": strategy.max_retries
                    }
                }
            except Exception as e:
                validation_result["valid"] = False
                validation_result["errors"].append(f"任务 {task_type.value} 配置错误: {str(e)}")
        
        return validation_result

# 全局配置管理器实例
_global_ai_config_manager = None

def get_ai_config_manager() -> UnifiedAIConfigManager:
    """获取全局AI配置管理器实例"""
    global _global_ai_config_manager
    if _global_ai_config_manager is None:
        _global_ai_config_manager = UnifiedAIConfigManager()
    return _global_ai_config_manager

def get_model_config_for_task(task_type: TaskType, model_type: Optional[ModelType] = None) -> ModelConfig:
    """便捷函数：获取指定任务的模型配置"""
    manager = get_ai_config_manager()
    return manager.get_single_model_config(task_type, model_type)

def get_model_selection_for_task(task_type: TaskType) -> Tuple[List[ModelConfig], ModelSelectionStrategy]:
    """便捷函数：获取指定任务的模型选择和策略"""
    manager = get_ai_config_manager()
    return manager.get_model_selection_for_task(task_type)

def validate_ai_configuration() -> Dict[str, Any]:
    """便捷函数：验证AI配置"""
    manager = get_ai_config_manager()
    return manager.validate_configuration()

if __name__ == "__main__":
    # 测试配置管理器
    print("🧪 测试统一AI配置管理器")
    print("=" * 60)
    
    try:
        manager = UnifiedAIConfigManager()
        
        # 验证配置
        validation = manager.validate_configuration()
        print(f"✅ 配置验证: {'通过' if validation['valid'] else '失败'}")
        
        if validation["errors"]:
            for error in validation["errors"]:
                print(f"❌ {error}")
        
        # 显示配置摘要
        print(f"\n📊 配置摘要:")
        for task, summary in validation["summary"].items():
            print(f"  {task}: {summary['available_models']} 个可用模型")
            print(f"    模型: {', '.join(summary['model_names'])}")
            print(f"    策略: 严格模式={summary['strategy']['strict_mode']}, 回退={summary['strategy']['fallback_enabled']}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}") 