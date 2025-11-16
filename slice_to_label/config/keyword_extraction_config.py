#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键词提取配置文件
支持灵活的关键词管理、场景分类、权重设置和正则表达式匹配
"""

import re
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

class KeywordExtractionConfig:
    """关键词提取配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器"""
        self.config_path = config_path or "config/keyword_extraction.json"
        self.keywords_config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载关键词配置，支持文件配置和默认配置"""
        try:
            config_file = Path(__file__).parent / "keyword_extraction.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"✅ 从文件加载关键词配置: {config_file}")
                return config
        except Exception as e:
            logger.warning(f"⚠️ 配置文件加载失败，使用默认配置: {e}")
        
        # 默认配置
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认关键词配置"""
        return {
            "extraction_settings": {
                "min_sentence_length": 8,
                "max_sentences": 3,
                "enable_regex_patterns": True,
                "case_sensitive": False
            },
            "keyword_categories": {
                "人物相关": {
                    "weight": 1.0,
                    "keywords": {
                        "中文": ["女性", "儿童", "宝宝", "家庭", "人物", "妈妈", "爸爸", "孩子", "婴儿", "幼儿"],
                        "英文": ["woman", "child", "baby", "family", "person", "mother", "mom", "dad", "father", "infant"]
                    }
                },
                "动作行为": {
                    "weight": 1.2,
                    "keywords": {
                        "中文": ["展示", "拿着", "玩", "坐", "制作", "准备", "喝", "喂", "哭", "笑", "吃", "抱", "看"],
                        "英文": ["shows", "showing", "holding", "playing", "sitting", "making", "preparing", "drinking", "feeding", "crying", "smiling", "laughing", "eating"]
                    }
                },
                "产品物品": {
                    "weight": 1.1,
                    "keywords": {
                        "中文": ["奶瓶", "牛奶", "奶粉", "产品", "包装", "容器", "玩具", "罐", "瓶子", "食品"],
                        "英文": ["bottle", "milk", "formula", "product", "package", "container", "toy", "can", "food", "nutrition"]
                    }
                },
                "环境场景": {
                    "weight": 0.9,
                    "keywords": {
                        "中文": ["房间", "厨房", "家", "室内", "户外", "医院", "场景", "卧室", "客厅"],
                        "英文": ["room", "kitchen", "home", "indoor", "outdoor", "hospital", "bedroom", "living"]
                    }
                },
                "品牌标识": {
                    "weight": 1.3,
                    "keywords": {
                        "中文": ["标签", "品牌", "营养", "成分", "标识", "商标", "logo"],
                        "英文": ["label", "brand", "nutrition", "ingredient", "logo", "trademark", "branding"]
                    }
                },
                "分析描述": {
                    "weight": 0.7,
                    "keywords": {
                        "中文": ["视频", "图片", "画面", "分析", "内容", "镜头", "帧"],
                        "英文": ["video", "image", "frame", "analysis", "content", "scene", "shot"]
                    }
                }
            },
            "regex_patterns": {
                "交互模式": {
                    "pattern": r"([\u4e00-\u9fff]+)\s*([\u4e00-\u9fff]*?[展示|拿着|喝|吃|玩|坐|看|抱|喂][\u4e00-\u9fff]*?)\s*([\u4e00-\u9fff]+)",
                    "weight": 1.5,
                    "description": "匹配主谓宾结构的中文交互描述"
                },
                "产品描述": {
                    "pattern": r"(奶粉|产品|包装|标签).{0,10}(展示|显示|呈现|标明)",
                    "weight": 1.4,
                    "description": "匹配产品相关的描述"
                },
                "情绪动作": {
                    "pattern": r"(宝宝|婴儿|孩子).{0,5}(哭|笑|开心|不安|满意|拒绝)",
                    "weight": 1.3,
                    "description": "匹配情绪相关的描述"
                }
            },
            "business_scenarios": {
                "母婴产品": {
                    "enhanced_categories": ["产品物品", "品牌标识", "动作行为"],
                    "reduced_categories": ["分析描述"],
                    "description": "母婴产品分析场景，强化产品和品牌识别"
                },
                "家庭生活": {
                    "enhanced_categories": ["人物相关", "动作行为", "环境场景"],
                    "reduced_categories": ["品牌标识"],
                    "description": "家庭生活场景，强化人物互动"
                }
            }
        }
    
    def get_keywords_for_extraction(self, scenario: str = "母婴产品") -> List[str]:
        """获取用于关键句子提取的关键词列表"""
        all_keywords = []
        scenario_config = self.keywords_config.get("business_scenarios", {}).get(scenario, {})
        
        # 根据场景调整权重
        enhanced_categories = scenario_config.get("enhanced_categories", [])
        reduced_categories = scenario_config.get("reduced_categories", [])
        
        for category_name, category_config in self.keywords_config["keyword_categories"].items():
            base_weight = category_config.get("weight", 1.0)
            
            # 场景权重调整
            if category_name in enhanced_categories:
                weight = base_weight * 1.5
            elif category_name in reduced_categories:
                weight = base_weight * 0.5
            else:
                weight = base_weight
            
            # 根据权重决定是否包含该类别的关键词
            if weight >= 0.8:  # 只包含权重较高的类别
                for lang_keywords in category_config["keywords"].values():
                    all_keywords.extend(lang_keywords)
        
        return list(set(all_keywords))  # 去重
    
    def get_regex_patterns(self) -> List[Dict[str, Any]]:
        """获取正则表达式模式"""
        if not self.keywords_config["extraction_settings"]["enable_regex_patterns"]:
            return []
        
        return [
            {
                "name": name,
                "pattern": re.compile(config["pattern"]),
                "weight": config["weight"],
                "description": config["description"]
            }
            for name, config in self.keywords_config["regex_patterns"].items()
        ]
    
    def get_extraction_settings(self) -> Dict[str, Any]:
        """获取提取设置"""
        return self.keywords_config["extraction_settings"]
    
    def update_keywords(self, category: str, language: str, new_keywords: List[str]):
        """动态更新关键词"""
        if category in self.keywords_config["keyword_categories"]:
            if language in self.keywords_config["keyword_categories"][category]["keywords"]:
                self.keywords_config["keyword_categories"][category]["keywords"][language].extend(new_keywords)
                logger.info(f"✅ 已更新 {category}-{language} 关键词: {new_keywords}")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            config_file = Path(__file__).parent / "keyword_extraction.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.keywords_config, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 配置已保存到: {config_file}")
        except Exception as e:
            logger.error(f"❌ 保存配置失败: {e}")

# 全局配置实例
_keyword_config = None

def get_keyword_config() -> KeywordExtractionConfig:
    """获取全局关键词配置实例"""
    global _keyword_config
    if _keyword_config is None:
        _keyword_config = KeywordExtractionConfig()
    return _keyword_config

def reload_keyword_config():
    """重新加载关键词配置（支持热更新）"""
    global _keyword_config
    _keyword_config = None
    return get_keyword_config() 