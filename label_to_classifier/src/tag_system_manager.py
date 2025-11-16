#!/usr/bin/env python3
"""
🏷️ 标签体系管理器 - Tag System Manager
从feishu_pool迁移而来，统一管理所有标签相关的业务逻辑

职责：
- 标签体系定义和管理
- 标签验证和标准化
- 子标签关联性检查
- 标签格式化处理
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TagValidationResult:
    """标签验证结果"""
    valid: bool
    valid_tags: List[str]
    invalid_tags: List[str]
    available_tags: List[str]
    error: Optional[str] = None
    note: Optional[str] = None

class TagSystemManager:
    """标签体系管理器 - 统一管理所有标签相关的业务逻辑"""
    
    def __init__(self):
        """初始化标签体系管理器"""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # 初始化标签体系
        self.tag_system = self._init_tag_system()
        
        # 标签标准化映射表
        self.main_tag_mappings = self._init_main_tag_mappings()
        
        self.logger.info("✅ 标签体系管理器初始化完成")
        self.logger.info(f"📋 支持主标签: {list(self.tag_system['main_categories'])}")
    
    def _init_tag_system(self) -> Dict:
        """初始化标签体系 - 从feishu_pool迁移而来"""
        return {
            "main_categories": [
                "🌟 使用效果",
                "🍼 产品介绍", 
                "🎁 促销机制",
                "🪝 钩子"
            ],
            "sub_tags": {
                "🌟 使用效果": [
                    "宝宝活泼蹦跳画面",
                    "家长竖起大拇指夸赞",
                    "喝奶前后对比镜头",
                    "真实用户出镜分享",
                    "专家点头认可画面"
                ],
                "🍼 产品介绍": [
                    "产品包装展示",
                    "权威认证标识展示",
                    "冲泡演示过程",
                    "成分结构动画展示",
                    "品牌方出镜讲述",
                    "图表展示"
                ],
                "🎁 促销机制": [
                    "亲子互动画面",
                    "宝宝开心喝奶",
                    "家长轻松育儿",
                    "全家和谐场景",
                    "宝宝成长记录",
                    "温馨家庭生活",
                    "愉快喂养时光",
                    "宝宝活泼展示",
                    "幸福氛围营造"
                ],
                "🪝 钩子": [
                    "宝宝哭闹不安",
                    "医生出镜讲解",
                    "产品对比展示",
                    "宝宝拒绝喝奶",
                    "家长焦虑表情",
                    "喂奶疲惫场景",
                    "专家科普讲解",
                    "宝宝不满足表现"
                ]
            }
        }
    
    def _init_main_tag_mappings(self) -> Dict[str, str]:
        """初始化主标签标准化映射表"""
        return {
            # 使用效果相关
            "使用效果": "🌟 使用效果",
            "🌟使用效果": "🌟 使用效果", 
            "🌟 使用效果": "🌟 使用效果",
            "效果": "🌟 使用效果",
            "效果展示": "🌟 使用效果",
            
            # 产品介绍相关
            "产品介绍": "🍼 产品介绍",
            "🍼产品介绍": "🍼 产品介绍",
            "🍼 产品介绍": "🍼 产品介绍",
            "产品": "🍼 产品介绍",
            "产品展示": "🍼 产品介绍",
            
            # 促销机制相关
            "促销机制": "🎁 促销机制",
            "🎁促销机制": "🎁 促销机制",
            "🎁 促销机制": "🎁 促销机制",
            "促销": "🎁 促销机制",
            "营销": "🎁 促销机制",
            
            # 钩子相关
            "钩子": "🪝 钩子",
            "🪝钩子": "🪝 钩子",
            "🪝 钩子": "🪝 钩子",
            "引入": "🪝 钩子",
            "开场": "🪝 钩子"
        }
    
    def get_main_categories(self) -> List[str]:
        """获取所有主标签类别"""
        return self.tag_system["main_categories"].copy()
    
    def get_sub_tags_for_main_category(self, main_category: str) -> List[str]:
        """根据主标签获取对应的子标签列表"""
        return self.tag_system["sub_tags"].get(main_category, [])
    
    def normalize_main_tag(self, main_tag: str) -> str:
        """标准化主标签格式"""
        if not main_tag:
            return ""
        
        # 定义标准主标签映射
        standard_tags = {
            "使用效果": "🌟 使用效果",
            "🌟使用效果": "🌟 使用效果", 
            "🌟 使用效果": "🌟 使用效果",
            
            "产品介绍": "🍼 产品介绍",
            "🍼产品介绍": "🍼 产品介绍",
            "🍼 产品介绍": "🍼 产品介绍",
            
            "促销机制": "🎁 促销机制",
            "🎁促销机制": "🎁 促销机制",
            "🎁 促销机制": "🎁 促销机制",
            
            "钩子": "🪝 钩子",
            "🪝钩子": "🪝 钩子",
            "🪝 钩子": "🪝 钩子"
        }
        
        # 清理输入：去除首尾空格
        cleaned_tag = main_tag.strip()
        
        # 直接匹配
        if cleaned_tag in standard_tags:
            return standard_tags[cleaned_tag]
        
        # 模糊匹配：去除所有空格后匹配
        cleaned_no_space = cleaned_tag.replace(" ", "")
        for key, value in standard_tags.items():
            if cleaned_no_space == key.replace(" ", ""):
                return value
        
        # 如果没有匹配到，返回原值（可能是新的标签类型）
        return cleaned_tag
    
    def normalize_sub_tags(self, sub_tags: List[str]) -> List[str]:
        """标准化子标签格式"""
        if not sub_tags:
            return []
        
        normalized = []
        for tag in sub_tags:
            if not tag:
                continue
            
            # 清理标签：去除首尾空格，统一格式
            cleaned_tag = tag.strip()
            
            # 标准化常见的子标签格式
            if ":" in cleaned_tag or "：" in cleaned_tag:
                # 统一使用中文冒号，并确保冒号后有空格
                if ":" in cleaned_tag:
                    parts = cleaned_tag.split(":", 1)
                    cleaned_tag = f"{parts[0].strip()}: {parts[1].strip()}"
                elif "：" in cleaned_tag:
                    parts = cleaned_tag.split("：", 1)
                    cleaned_tag = f"{parts[0].strip()}: {parts[1].strip()}"
            
            normalized.append(cleaned_tag)
        
        return normalized
    
    def validate_sub_tags(self, main_category: str, sub_tags: List[str]) -> Dict:
        """验证子标签是否属于指定的主标签类别"""
        # 特殊处理：产品介绍切片允许AI生成的灵活子标签
        if main_category == "🍼产品介绍" or main_category == "🍼 产品介绍":
            return {
                "valid": True,
                "valid_tags": sub_tags,
                "invalid_tags": [],
                "available_tags": ["AI生成的品牌标签", "AI生成的产品标签"],
                "note": "产品介绍切片允许AI生成的灵活子标签"
            }
        
        valid_sub_tags = self.get_sub_tags_for_main_category(main_category)
        
        if not valid_sub_tags:
            return {
                "valid": False,
                "error": f"未找到主标签 '{main_category}' 对应的子标签"
            }
        
        invalid_tags = []
        valid_tags = []
        
        for tag in sub_tags:
            if tag in valid_sub_tags:
                valid_tags.append(tag)
            else:
                invalid_tags.append(tag)
        
        return {
            "valid": len(invalid_tags) == 0,
            "valid_tags": valid_tags,
            "invalid_tags": invalid_tags,
            "available_tags": valid_sub_tags
        }
    
    def format_sub_tags_text(self, sub_tags: List[str]) -> str:
        """将子标签列表格式化为文本"""
        return ", ".join(sub_tags) if sub_tags else ""
    
    def parse_sub_tags_text(self, sub_tags_text: str) -> List[str]:
        """解析子标签文本为列表"""
        if not sub_tags_text:
            return []
        # 按逗号或顿号分割
        tags = [tag.strip() for tag in sub_tags_text.replace('，', ',').split(',')]
        return [tag for tag in tags if tag]
    
    def is_valid_main_category(self, main_category: str) -> bool:
        """
        检查是否为有效的主标签类别
        
        Args:
            main_category: 主标签
            
        Returns:
            bool: 是否有效
        """
        normalized = self.normalize_main_tag(main_category)
        return normalized in self.tag_system["main_categories"]
    
    def get_tag_statistics(self) -> Dict:
        """
        获取标签体系统计信息
        
        Returns:
            Dict: 统计信息
        """
        total_sub_tags = sum(len(tags) for tags in self.tag_system["sub_tags"].values())
        
        return {
            "main_categories_count": len(self.tag_system["main_categories"]),
            "total_sub_tags": total_sub_tags,
            "tag_mappings_count": len(self.main_tag_mappings),
            "main_categories": self.tag_system["main_categories"],
            "sub_tags_distribution": {
                category: len(tags) 
                for category, tags in self.tag_system["sub_tags"].items()
            }
        }
    
    def add_custom_main_tag(self, category: str, sub_tags: List[str] = None) -> bool:
        """
        添加自定义主标签类别
        
        Args:
            category: 新的主标签类别
            sub_tags: 对应的子标签列表
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if category not in self.tag_system["main_categories"]:
                self.tag_system["main_categories"].append(category)
                self.tag_system["sub_tags"][category] = sub_tags or []
                self.logger.info(f"✅ 添加自定义主标签: {category}")
                return True
            else:
                self.logger.warning(f"⚠️ 主标签已存在: {category}")
                return False
        except Exception as e:
            self.logger.error(f"❌ 添加自定义主标签失败: {e}")
            return False
    
    def export_tag_system(self) -> Dict:
        """导出完整的标签体系"""
        return {
            "tag_system": self.tag_system,
            "main_tag_mappings": self.main_tag_mappings,
            "statistics": self.get_tag_statistics()
        }


# 全局标签管理器实例
_tag_manager = None

def get_tag_system_manager() -> TagSystemManager:
    """获取全局标签管理器实例"""
    global _tag_manager
    if _tag_manager is None:
        _tag_manager = TagSystemManager()
    return _tag_manager 