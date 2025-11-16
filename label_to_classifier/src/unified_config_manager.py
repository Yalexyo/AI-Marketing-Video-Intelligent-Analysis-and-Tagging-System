#!/usr/bin/env python3
"""
⚙️ 统一配置管理器
整合所有模块的配置管理，提供统一的配置接口
架构优化版：减少配置文件冗余，统一环境变量管理
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class AIModelConfig:
    """AI模型配置"""
    primary_model: str
    secondary_model: str
    api_key: str
    base_url: Optional[str] = None
    timeout: int = 30
    max_retries: int = 2


@dataclass
class ProcessingConfig:
    """处理配置"""
    slice_base_dir: str = "../🎬Slice"
    output_base_dir: str = "../📁生成结果"
    backup_enabled: bool = True
    min_confidence_threshold: float = 0.4
    batch_size: int = 10
    concurrent_workers: int = 3


@dataclass
class UnifiedConfig:
    """统一配置"""
    processing: ProcessingConfig
    deepseek: AIModelConfig
    claude: AIModelConfig
    gemini: AIModelConfig
    debug_mode: bool = False
    log_level: str = "INFO"


class UnifiedConfigManager:
    """⚙️ 统一配置管理器 - 整合所有模块配置"""
    
    def __init__(self, config_file: Optional[str] = None):
        """初始化统一配置管理器"""
        self.config_file = config_file or "config/unified_config.json"
        self.config_dir = Path("config")
        self.config_dir.mkdir(exist_ok=True)
        
        # 加载配置
        self.config = self._load_unified_config()
        
        # 设置日志级别
        logging.getLogger().setLevel(getattr(logging, self.config.log_level))
        
        logger.info("✅ 统一配置管理器初始化完成")
        logger.info(f"📁 配置文件: {self.config_file}")
        logger.info(f"🔧 调试模式: {'开启' if self.config.debug_mode else '关闭'}")
    
    def _load_unified_config(self) -> UnifiedConfig:
        """加载统一配置"""
        try:
            # 优先从环境变量加载
            config = self._load_from_environment()
            
            # 如果配置文件存在，合并配置文件的设置
            config_path = Path(self.config_file)
            if config_path.exists():
                file_config = self._load_from_file(config_path)
                config = self._merge_configs(config, file_config)
            
            # 验证配置
            self._validate_config(config)
            
            return config
            
        except Exception as e:
            logger.error(f"❌ 配置加载失败: {e}")
            return self._get_default_config()
    
    def _load_from_environment(self) -> UnifiedConfig:
        """从环境变量加载配置"""
        # 处理配置
        processing_config = ProcessingConfig(
            slice_base_dir=os.getenv("SLICE_BASE_DIR", "../🎬Slice"),
            output_base_dir=os.getenv("OUTPUT_BASE_DIR", "../📁生成结果"),
            backup_enabled=os.getenv("BACKUP_ENABLED", "true").lower() == "true",
            min_confidence_threshold=float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.4")),
            batch_size=int(os.getenv("BATCH_SIZE", "10")),
            concurrent_workers=int(os.getenv("CONCURRENT_WORKERS", "3"))
        )
        
        # DeepSeek配置
        deepseek_config = AIModelConfig(
            primary_model=os.getenv("DEEPSEEK_PRIMARY_MODEL", "deepseek-chat"),
            secondary_model=os.getenv("DEEPSEEK_SECONDARY_MODEL", "deepseek-chat"),
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "30")),
            max_retries=int(os.getenv("DEEPSEEK_MAX_RETRIES", "2"))
        )
        
        # Claude配置
        claude_config = AIModelConfig(
            primary_model=os.getenv("CLAUDE_PRIMARY_MODEL", "anthropic/claude-4-sonnet-20250522"),
            secondary_model=os.getenv("CLAUDE_SECONDARY_MODEL", "anthropic/claude-4-sonnet-20250522"),
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            timeout=int(os.getenv("CLAUDE_TIMEOUT", "30")),
            max_retries=int(os.getenv("CLAUDE_MAX_RETRIES", "2"))
        )
        
        # Gemini配置
        gemini_config = AIModelConfig(
            primary_model=os.getenv("GEMINI_PRIMARY_MODEL", "gemini-2.5-pro"),
            secondary_model=os.getenv("GEMINI_SECONDARY_MODEL", "gemini-2.5-pro"),
            api_key=os.getenv("GEMINI_API_KEY", ""),
            base_url=os.getenv("GEMINI_BASE_URL"),
            timeout=int(os.getenv("GEMINI_TIMEOUT", "30")),
            max_retries=int(os.getenv("GEMINI_MAX_RETRIES", "2"))
        )
        
        return UnifiedConfig(
            processing=processing_config,
            deepseek=deepseek_config,
            claude=claude_config,
            gemini=gemini_config,
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
    
    def _load_from_file(self, config_path: Path) -> Dict[str, Any]:
        """从配置文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ 配置文件加载失败: {e}")
            return {}
    
    def _merge_configs(self, env_config: UnifiedConfig, file_config: Dict[str, Any]) -> UnifiedConfig:
        """合并环境变量配置和文件配置"""
        # 这里可以实现更复杂的配置合并逻辑
        # 目前优先使用环境变量配置
        return env_config
    
    def _validate_config(self, config: UnifiedConfig):
        """验证配置有效性"""
        # 验证API密钥
        if not config.deepseek.api_key:
            logger.warning("⚠️ DeepSeek API密钥未配置")
        
        if not config.claude.api_key:
            logger.warning("⚠️ Claude API密钥未配置")
        
        if not config.gemini.api_key:
            logger.warning("⚠️ Gemini API密钥未配置")
        
        # 验证路径
        slice_dir = Path(config.processing.slice_base_dir)
        if not slice_dir.exists():
            logger.warning(f"⚠️ 切片目录不存在: {slice_dir}")
        
        # 验证数值范围
        if config.processing.min_confidence_threshold < 0 or config.processing.min_confidence_threshold > 1:
            logger.warning(f"⚠️ 置信度阈值超出范围: {config.processing.min_confidence_threshold}")
    
    def _get_default_config(self) -> UnifiedConfig:
        """获取默认配置"""
        logger.info("🔧 使用默认配置")
        
        return UnifiedConfig(
            processing=ProcessingConfig(),
            deepseek=AIModelConfig(
                primary_model="deepseek-chat",
                secondary_model="deepseek-chat",
                api_key=""
            ),
            claude=AIModelConfig(
                primary_model="anthropic/claude-4-sonnet-20250522",
                secondary_model="anthropic/claude-4-sonnet-20250522",
                api_key=""
            ),
            gemini=AIModelConfig(
                primary_model="gemini-2.5-pro",
                secondary_model="gemini-2.5-pro",
                api_key=""
            )
        )
    
    def get_config(self) -> UnifiedConfig:
        """获取统一配置"""
        return self.config
    
    def get_ai_config(self, model_type: str) -> AIModelConfig:
        """获取指定AI模型配置"""
        if model_type.lower() == "deepseek":
            return self.config.deepseek
        elif model_type.lower() == "claude":
            return self.config.claude
        elif model_type.lower() == "gemini":
            return self.config.gemini
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
    
    def get_processing_config(self) -> ProcessingConfig:
        """获取处理配置"""
        return self.config.processing
    
    def update_config(self, updates: Dict[str, Any]):
        """更新配置"""
        try:
            # 这里可以实现配置的动态更新
            logger.info("🔧 配置更新请求")
            # 实际实现会更复杂，需要根据更新内容修改对应的配置对象
            pass
        except Exception as e:
            logger.error(f"❌ 配置更新失败: {e}")
    
    def save_config_to_file(self, file_path: Optional[str] = None):
        """保存配置到文件"""
        try:
            output_path = Path(file_path or self.config_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            config_dict = {
                "processing": {
                    "slice_base_dir": self.config.processing.slice_base_dir,
                    "output_base_dir": self.config.processing.output_base_dir,
                    "backup_enabled": self.config.processing.backup_enabled,
                    "min_confidence_threshold": self.config.processing.min_confidence_threshold,
                    "batch_size": self.config.processing.batch_size,
                    "concurrent_workers": self.config.processing.concurrent_workers
                },
                "deepseek": {
                    "primary_model": self.config.deepseek.primary_model,
                    "secondary_model": self.config.deepseek.secondary_model,
                    "base_url": self.config.deepseek.base_url,
                    "timeout": self.config.deepseek.timeout,
                    "max_retries": self.config.deepseek.max_retries
                },
                "claude": {
                    "primary_model": self.config.claude.primary_model,
                    "secondary_model": self.config.claude.secondary_model,
                    "base_url": self.config.claude.base_url,
                    "timeout": self.config.claude.timeout,
                    "max_retries": self.config.claude.max_retries
                },
                "gemini": {
                    "primary_model": self.config.gemini.primary_model,
                    "secondary_model": self.config.gemini.secondary_model,
                    "base_url": self.config.gemini.base_url,
                    "timeout": self.config.gemini.timeout,
                    "max_retries": self.config.gemini.max_retries
                },
                "debug_mode": self.config.debug_mode,
                "log_level": self.config.log_level,
                "note": "API密钥通过环境变量配置，不保存到文件中"
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 配置已保存到: {output_path}")
            
        except Exception as e:
            logger.error(f"❌ 配置保存失败: {e}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "processing": {
                "slice_base_dir": self.config.processing.slice_base_dir,
                "output_base_dir": self.config.processing.output_base_dir,
                "backup_enabled": self.config.processing.backup_enabled,
                "min_confidence_threshold": self.config.processing.min_confidence_threshold,
                "batch_size": self.config.processing.batch_size,
                "concurrent_workers": self.config.processing.concurrent_workers
            },
            "ai_models": {
                "deepseek": {
                    "primary_model": self.config.deepseek.primary_model,
                    "api_key_configured": bool(self.config.deepseek.api_key)
                },
                "claude": {
                    "primary_model": self.config.claude.primary_model,
                    "api_key_configured": bool(self.config.claude.api_key)
                },
                "gemini": {
                    "primary_model": self.config.gemini.primary_model,
                    "api_key_configured": bool(self.config.gemini.api_key)
                }
            },
            "debug_mode": self.config.debug_mode,
            "log_level": self.config.log_level
        }
    
    def print_config_status(self):
        """打印配置状态"""
        print("⚙️ 统一配置状态:")
        print("=" * 50)
        
        summary = self.get_config_summary()
        
        print("📁 处理配置:")
        for key, value in summary["processing"].items():
            print(f"   {key}: {value}")
        
        print("\n🤖 AI模型配置:")
        for model, config in summary["ai_models"].items():
            api_status = "✅ 已配置" if config["api_key_configured"] else "❌ 未配置"
            print(f"   {model}: {config['primary_model']} ({api_status})")
        
        print(f"\n🔧 系统配置:")
        print(f"   调试模式: {'开启' if summary['debug_mode'] else '关闭'}")
        print(f"   日志级别: {summary['log_level']}")


# 全局配置管理器实例
_global_config_manager: Optional[UnifiedConfigManager] = None


def get_unified_config_manager() -> UnifiedConfigManager:
    """获取全局统一配置管理器实例"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = UnifiedConfigManager()
    return _global_config_manager


def get_ai_config(model_type: str) -> AIModelConfig:
    """获取AI模型配置的便捷函数"""
    return get_unified_config_manager().get_ai_config(model_type)


def get_processing_config() -> ProcessingConfig:
    """获取处理配置的便捷函数"""
    return get_unified_config_manager().get_processing_config() 