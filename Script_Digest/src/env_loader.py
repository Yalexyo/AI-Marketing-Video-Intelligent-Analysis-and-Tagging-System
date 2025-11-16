#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量加载器 - 复用现有项目的API配置
智能查找和复用slice_to_label等项目的环境配置
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class ScriptDigestEnvLoader:
    """Script Digest 环境变量加载器 - 智能复用现有配置"""
    
    def __init__(self):
        """初始化环境变量加载器"""
        self.project_root = self._find_project_root()
        self.config_sources = self._find_config_sources()
        self.loaded_vars = {}
        
    def _find_project_root(self) -> Path:
        """查找项目根目录"""
        current_path = Path(__file__).resolve()
        
        # 从Script_Digest向上查找，直到找到包含其他项目目录的根目录
        for parent in [current_path.parent.parent.parent, current_path.parent.parent]:
            if (parent / "slice_to_label").exists():
                logger.info(f"✅ 找到项目根目录: {parent}")
                return parent
        
        # 默认返回上上级目录
        default_root = current_path.parent.parent.parent
        logger.warning(f"⚠️ 使用默认根目录: {default_root}")
        return default_root
    
    def _find_config_sources(self) -> List[Path]:
        """查找可用的配置文件源"""
        sources = []
        
        # 1. slice_to_label的配置文件（优先级最高）
        slice_config = self.project_root / "slice_to_label" / "config" / "env_config.txt"
        if slice_config.exists():
            sources.append(slice_config)
            logger.info(f"✅ 发现配置源: {slice_config}")
        
        # 2. 根目录的.env文件
        root_env = self.project_root / ".env"
        if root_env.exists():
            sources.append(root_env)
            logger.info(f"✅ 发现配置源: {root_env}")
        
        # 3. 其他可能的配置文件
        other_configs = [
            self.project_root / "video_to_srt" / "config" / "env_config.txt",
            self.project_root / "srt_to_product" / "config" / "env_config.txt",
        ]
        
        for config_path in other_configs:
            if config_path.exists():
                sources.append(config_path)
                logger.info(f"✅ 发现额外配置源: {config_path}")
        
        if not sources:
            logger.warning("⚠️ 未找到任何配置文件源")
        
        return sources
    
    def load_env_variables(self) -> Dict[str, str]:
        """加载环境变量"""
        env_vars = {}
        
        # 首先从系统环境变量读取
        system_vars = self._load_from_system()
        env_vars.update(system_vars)
        
        # 然后从各个配置文件读取（按优先级覆盖）
        for config_source in self.config_sources:
            try:
                file_vars = self._load_from_file(config_source)
                env_vars.update(file_vars)
                logger.info(f"✅ 从 {config_source.name} 加载了 {len(file_vars)} 个变量")
            except Exception as e:
                logger.warning(f"⚠️ 读取 {config_source} 失败: {e}")
        
        self.loaded_vars = env_vars
        logger.info(f"✅ 总共加载了 {len(env_vars)} 个环境变量")
        return env_vars
    
    def _load_from_system(self) -> Dict[str, str]:
        """从系统环境变量加载"""
        system_vars = {}
        
        required_keys = [
            "DEEPSEEK_API_KEY",
            "DASHSCOPE_API_KEY", 
            "GOOGLE_AI_API_KEY",
            "OPENROUTER_API_KEY"
        ]
        
        for key in required_keys:
            value = os.getenv(key)
            if value:
                system_vars[key] = value
        
        return system_vars
    
    def _load_from_file(self, file_path: Path) -> Dict[str, str]:
        """从指定文件加载环境变量"""
        file_vars = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                
                # 解析键值对
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 移除引号
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    # 跳过占位符值
                    placeholder_values = [
                        "your_deepseek_api_key_here",
                        "your_dashscope_api_key_here", 
                        "your_google_ai_api_key_here",
                        "your_openrouter_api_key_here"
                    ]
                    
                    if value and value not in placeholder_values:
                        file_vars[key] = value
        
        return file_vars
    
    def get_api_keys(self) -> Dict[str, str]:
        """获取API密钥配置"""
        if not self.loaded_vars:
            self.load_env_variables()
        
        api_keys = {
            "deepseek": self.loaded_vars.get("DEEPSEEK_API_KEY", ""),
            "dashscope": self.loaded_vars.get("DASHSCOPE_API_KEY", ""),
            "qwen": self.loaded_vars.get("DASHSCOPE_API_KEY", ""),  # Qwen使用DashScope
            "google": self.loaded_vars.get("GOOGLE_AI_API_KEY", ""),
            "openrouter": self.loaded_vars.get("OPENROUTER_API_KEY", "")
        }
        
        # 过滤空值
        api_keys = {k: v for k, v in api_keys.items() if v}
        
        logger.info(f"✅ 加载了 {len(api_keys)} 个有效API密钥: {list(api_keys.keys())}")
        return api_keys
    
    def get_config_value(self, key: str, default: str = "") -> str:
        """
        获取配置值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        if not self.loaded_vars:
            self.load_env_variables()
        
        return self.loaded_vars.get(key, default)

# 全局实例
_env_loader = ScriptDigestEnvLoader()

def load_environment() -> ScriptDigestEnvLoader:
    """获取环境加载器实例"""
    return _env_loader

def get_api_keys() -> Dict[str, str]:
    """获取API密钥（快捷函数）"""
    return _env_loader.get_api_keys()

if __name__ == "__main__":
    # 测试环境变量加载
    print("🧪 测试环境变量加载...")
    
    env_loader = load_environment()
    env_vars = env_loader.load_env_variables()
    api_keys = env_loader.get_api_keys()
    
    print(f"📁 项目根目录: {env_loader.project_root}")
    print(f"📄 配置源数量: {len(env_loader.config_sources)}")
    print(f"🔧 加载的环境变量数量: {len(env_vars)}")
    print(f"🔑 有效API密钥: {list(api_keys.keys())}")
    
    for service, key in api_keys.items():
        masked_key = f"{key[:10]}..." if len(key) > 10 else "***"
        print(f"  - {service}: {masked_key}")
