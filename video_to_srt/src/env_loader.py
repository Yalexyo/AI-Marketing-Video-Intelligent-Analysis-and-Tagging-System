#!/usr/bin/env python3
"""
环境变量加载模块
自动加载项目根目录下的 .env 文件
"""

import os
from pathlib import Path
from typing import Optional

# 尝试导入 python-dotenv
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

def load_env_config() -> dict:
    """
    加载环境配置文件
    
    Returns:
        dict: 配置字典
    """
    env_vars = {}
    
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent
    
    # 查找配置文件
    config_paths = [
        current_dir / "config" / "env_config.txt",  # src/config/
        current_dir.parent / "config" / "env_config.txt",  # video_to_srt/config/
        current_dir.parent.parent / ".env",  # 项目根目录/.env
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # 跳过空行和注释
                        if not line or line.startswith('#'):
                            continue
                        
                        # 解析 KEY=VALUE 格式
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # 移除引号
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            
                            env_vars[key] = value
                            
                            # 同时设置到环境变量（不覆盖已存在的）
                            if key not in os.environ:
                                os.environ[key] = value
                                
                print(f"✅ 已加载环境配置: {config_path}")
                break
                        
            except Exception as e:
                print(f"⚠️ 加载配置文件失败 {config_path}: {e}")
                continue
    
    return env_vars

def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    获取环境变量
    
    Args:
        key: 环境变量名
        default: 默认值
        
    Returns:
        环境变量值或默认值
    """
    # 先尝试加载配置文件
    load_env_config()
    
    return os.environ.get(key, default)

def get_dashscope_api_key() -> Optional[str]:
    """
    获取 DashScope API 密钥
    
    Returns:
        API密钥或None
    """
    return get_env_var("DASHSCOPE_API_KEY")

def get_default_vocab_id() -> Optional[str]:
    """
    获取默认词汇表ID
    
    Returns:
        词汇表ID或None
    """
    return get_env_var("DEFAULT_VOCAB_ID")

def get_default_language() -> str:
    """
    获取默认语言
    
    Returns:
        默认语言，默认为 'zh'
    """
    return get_env_var("DEFAULT_LANGUAGE", "zh")

def get_default_quality() -> str:
    """
    获取默认音频质量
    
    Returns:
        默认音频质量，默认为 'auto'
    """
    return get_env_var("DEFAULT_QUALITY", "auto")

def get_deepseek_api_key() -> Optional[str]:
    """
    获取DeepSeek API密钥
    
    Returns:
        API密钥或None
    """
    key = get_env_var("DEEPSEEK_API_KEY")
    if key == 'your_deepseek_api_key_here':
        return None
    return key

def get_openrouter_api_key() -> Optional[str]:
    """
    获取OpenRouter API密钥
    
    Returns:
        API密钥或None
    """
    key = get_env_var("OPENROUTER_API_KEY")
    if key == 'your_openrouter_api_key_here':
        return None
    return key

# 自动加载环境变量
load_env_config() 