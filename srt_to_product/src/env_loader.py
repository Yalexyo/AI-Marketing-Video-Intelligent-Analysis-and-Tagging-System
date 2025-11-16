#!/usr/bin/env python3
"""
环境变量加载器 - SRT转产品介绍视频
统一管理API密钥和配置参数的加载
"""

import os
from dotenv import load_dotenv
from typing import Optional

# 加载 .env 文件
load_dotenv()

def get_deepseek_api_key() -> Optional[str]:
    """获取DeepSeek API密钥"""
    return os.getenv('DEEPSEEK_API_KEY')

def get_deepseek_base_url() -> str:
    """获取DeepSeek API基础URL"""
    return os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

def get_deepseek_model() -> str:
    """获取DeepSeek模型名称"""
    return os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

def get_max_tokens() -> int:
    """获取最大token数"""
    return int(os.getenv('MAX_TOKENS', '4000'))

def get_temperature() -> float:
    """获取创意度参数"""
    return float(os.getenv('TEMPERATURE', '0.3'))

def get_min_segment_duration() -> int:
    """获取产品介绍片段最小时长"""
    return int(os.getenv('MIN_SEGMENT_DURATION', '10'))

def get_max_segment_duration() -> int:
    """获取产品介绍片段最大时长"""
    return int(os.getenv('MAX_SEGMENT_DURATION', '30'))

def get_video_quality() -> str:
    """获取视频质量设置"""
    return os.getenv('VIDEO_QUALITY', 'medium')

def get_product_keywords() -> list:
    """获取产品关键词列表"""
    keywords_str = os.getenv('PRODUCT_KEYWORDS', 
                            '启赋,蕴淳,蓝钻,HMO,A2奶源,OPN,母乳低聚糖,自愈力,水奶,转奶,断奶')
    return [keyword.strip() for keyword in keywords_str.split(',')]

def get_brand_keywords() -> list:
    """获取品牌关键词列表"""
    keywords_str = os.getenv('BRAND_KEYWORDS', 
                            '惠氏,启赋,蕴淳,蓝钻')
    return [keyword.strip() for keyword in keywords_str.split(',')]

def validate_config() -> bool:
    """验证必需的配置是否完整"""
    api_key = get_deepseek_api_key()
    if not api_key:
        return False
    return True

def get_config_summary() -> dict:
    """获取配置摘要"""
    return {
        'api_configured': bool(get_deepseek_api_key()),
        'model': get_deepseek_model(),
        'max_tokens': get_max_tokens(),
        'temperature': get_temperature(),
        'min_duration': get_min_segment_duration(),
        'max_duration': get_max_segment_duration(),
        'video_quality': get_video_quality(),
        'product_keywords_count': len(get_product_keywords()),
        'brand_keywords_count': len(get_brand_keywords())
    } 