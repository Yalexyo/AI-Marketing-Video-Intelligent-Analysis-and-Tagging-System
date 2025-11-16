#!/usr/bin/env python3
"""
🎯 主标签AI智能分类器 - Primary AI Intelligent Classifier
统一架构设计：继承BaseAIClassifier，专注主标签分类

v3.0 功能:
- 继承统一的BaseAIClassifier架构
- 专注主标签分类业务逻辑
- 内置主标签分类提示词模板
- 智能置信度评估
- 向后兼容的公共函数接口
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# 继承BaseAIClassifier
try:
    from .base_ai_classifier import BaseAIClassifier
    from .unified_ai_config_manager import TaskType
except ImportError:
    # 支持直接运行测试
    from base_ai_classifier import BaseAIClassifier
    from unified_ai_config_manager import TaskType

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PrimaryAIClassifier(BaseAIClassifier):
    """主标签AI智能分类器 v3.0 - 继承统一分类器架构"""
    
    def __init__(self):
        """初始化主标签AI分类器 - 继承BaseAIClassifier"""
        
        # 初始化基类
        super().__init__(TaskType.MAIN_TAG_CLASSIFICATION)
        
        # 主标签分类特定配置 - 支持品牌感知的产品介绍分类
        self.main_categories = [
            "🌟 使用效果",
            "🍼 产品介绍_蕴淳",
            "🍼 产品介绍_水奶", 
            "🍼 产品介绍_蓝钻",
            "🎁 促销机制",
            "🪝 钩子"
        ]
        
        # 品牌关键词配置 - 从现有配置中提取
        self.brand_keywords = {
            "蕴淳": ["蕴淳", "蕴醇", "启赋蕴淳", "启赋蕴醇", "核心配方", "HMO", "母乳低聚糖", "OPN", "α-乳清蛋白"],
            "水奶": ["水奶", "便携装", "即饮", "小瓶装", "液体奶", "A2奶源", "携带方便", "新鲜", "即开即饮"],
            "蓝钻": ["蓝钻", "高端", "升级配方", "顶级", "旗舰", "premium", "钻石"]
        }
        
        logger.info(f"✅ 主标签AI智能分类器初始化完成")
        logger.info(f"🎯 支持分类: {', '.join(self.main_categories)}")

    def _normalize_main_tag(self, tag: str) -> str:
        """
        标准化主标签 - 将AI返回的文本标签映射到标准emoji标签
        
        Args:
            tag: AI返回的原始标签
            
        Returns:
            str: 标准化后的emoji标签，如果无法映射则返回"未知"
        """
        if not tag or not isinstance(tag, str):
            return "未知"
        
        # 移除多余空格并转小写用于匹配
        tag_clean = tag.strip().lower()
        
        # 标签映射表 - 支持多种可能的AI返回格式
        tag_mapping = {
            # 使用效果相关
            "使用效果": "🌟 使用效果",
            "🌟 使用效果": "🌟 使用效果",
            "效果": "🌟 使用效果",
            "效果展示": "🌟 使用效果",
            "使用体验": "🌟 使用效果",
            "产品效果": "🌟 使用效果",
            
            # 产品介绍相关 - 支持品牌感知映射
            "产品介绍": "🍼 产品介绍_蕴淳",  # 默认映射到蕴淳
            "🍼 产品介绍": "🍼 产品介绍_蕴淳",  # 兼容旧格式
            "产品": "🍼 产品介绍_蕴淳",
            "产品展示": "🍼 产品介绍_蕴淳",
            "产品说明": "🍼 产品介绍_蕴淳",
            "品牌介绍": "🍼 产品介绍_蕴淳",
            "成分介绍": "🍼 产品介绍_蕴淳",
            
            # 品牌化产品介绍标签
            "🍼 产品介绍_蕴淳": "🍼 产品介绍_蕴淳",
            "🍼 产品介绍_水奶": "🍼 产品介绍_水奶", 
            "🍼 产品介绍_蓝钻": "🍼 产品介绍_蓝钻",
            "产品介绍_蕴淳": "🍼 产品介绍_蕴淳",
            "产品介绍_水奶": "🍼 产品介绍_水奶",
            "产品介绍_蓝钻": "🍼 产品介绍_蓝钻",
            
            # 品牌特定关键词映射
            "蕴淳": "🍼 产品介绍_蕴淳",
            "蕴醇": "🍼 产品介绍_蕴淳",
            "水奶": "🍼 产品介绍_水奶",
            "便携装": "🍼 产品介绍_水奶",
            "蓝钻": "🍼 产品介绍_蓝钻",
            "高端": "🍼 产品介绍_蓝钻",
            
            # 促销机制相关
            "促销机制": "🎁 促销机制",
            "🎁 促销机制": "🎁 促销机制",
            "促销": "🎁 促销机制",
            "营销": "🎁 促销机制",
            "推广": "🎁 促销机制",
            "家庭场景": "🎁 促销机制",
            "情感连接": "🎁 促销机制",
            "温馨": "🎁 促销机制",
            
            # 钩子相关
            "钩子": "🪝 钩子",
            "🪝 钩子": "🪝 钩子",
            "问题": "🪝 钩子",
            "困扰": "🪝 钩子",
            "痛点": "🪝 钩子",
            "焦虑": "🪝 钩子",
            "担心": "🪝 钩子"
        }
        
        # 直接匹配
        if tag_clean in tag_mapping:
            return tag_mapping[tag_clean]
        
        # 包含匹配 - 检查原始标签是否包含关键词
        for key, standard_tag in tag_mapping.items():
            if key in tag_clean or tag_clean in key:
                return standard_tag
        
        # 模糊匹配 - 检查是否已经是标准格式但大小写不同
        tag_original = tag.strip()
        for standard_tag in self.main_categories:
            if tag_original == standard_tag:
                return standard_tag
            # 去掉emoji比较
            standard_text = standard_tag.split(' ', 1)[-1] if ' ' in standard_tag else standard_tag
            if tag_clean == standard_text.lower():
                return standard_tag
        
        logger.debug(f"🔍 无法标准化标签: '{tag}' -> 未知")
        return "未知"
    
    def _build_classification_prompts(self) -> Dict[str, str]:
        """构建主标签分类提示词模板"""
        return {
            "standard": """🎯 你是专业的母婴视频内容分类专家，请根据提供的Labels内容，精确推断其所属的主标签类别。

## 📋 主标签类别体系

**🌟 使用效果**: 宝宝活泼、效果展示、满意反馈、健康发育、快乐玩耍、成长对比、营养效果、家长夸赞
**🍼 产品介绍_蕴淳**: 启赋蕴淳产品展示、HMO母乳低聚糖、OPN活性蛋白、α-乳清蛋白、核心配方介绍、营养科学、惠氏背景
**🍼 产品介绍_水奶**: 启赋水奶展示、便携装特性、A2奶源、即饮方便、小瓶装、新鲜品质、携带便利
**🍼 产品介绍_蓝钻**: 启赋蓝钻高端系列、升级配方、顶级品质、旗舰产品、premium特性（如出现）
**🎁 促销机制**: 亲子互动、温馨场景、家庭和谐、情感连接、生活日常、关爱陪伴、幸福时光、母爱表达
**🪝 钩子**: 宝宝哭闹、家长焦虑、喂养困扰、专家建议、问题解决、改善需求、担心顾虑、寻求帮助

⚠️ **重要**: predicted_category字段必须使用完整的emoji标签格式，例如"🌟 使用效果"而不是"使用效果"

## 🎯 分类判断逻辑

### 🌟 使用效果识别要点
- **核心特征**: 描述产品使用后的积极变化和效果展示
- **关键行为**: 宝宝活泼蹦跳、主动进食、快乐玩耍、健康成长
- **情绪状态**: 满意、开心、愉悦、自信、活力
- **对比元素**: 使用前后对比、效果明显、改善显著

### 🍼 产品介绍_蕴淳识别要点  
- **核心特征**: 启赋蕴淳产品展示，强调高端配方和营养科学
- **关键词汇**: 蕴淳、蕴醇、HMO、母乳低聚糖、OPN、α-乳清蛋白、核心配方、营养科学、惠氏背景
- **内容重点**: 营养配方介绍、科研实力、品牌背景、成分优势
- **展示方式**: 产品包装、配方说明、科学依据、品牌权威性

### 🍼 产品介绍_水奶识别要点
- **核心特征**: 启赋水奶产品展示，强调便携性和新鲜品质
- **关键词汇**: 水奶、便携装、A2奶源、即饮、小瓶装、新鲜、携带方便、液体奶
- **内容重点**: 便携特性、A2奶源优势、使用便利性、品质保证
- **展示方式**: 便携包装、使用场景、A2奶源介绍、便利性演示

### 🍼 产品介绍_蓝钻识别要点
- **核心特征**: 启赋蓝钻高端系列展示，强调顶级品质和升级配方
- **关键词汇**: 蓝钻、高端、升级配方、顶级、旗舰、premium、钻石系列
- **内容重点**: 高端定位、升级配方、顶级品质、旗舰特性
- **展示方式**: 高端包装、升级特性、品质升级、旗舰产品介绍

### 🎁 促销机制识别要点
- **核心特征**: 强调温馨家庭场景和亲情价值传递
- **关键行为**: 亲子互动、家庭聚餐、日常生活、情感表达
- **情感元素**: 温馨、和谐、关爱、陪伴、幸福、满足
- **场景设置**: 家庭环境、生活日常、节日庆祝、亲情时刻

### 🪝 钩子识别要点
- **核心特征**: 描述问题场景和需要解决的困扰痛点
- **关键行为**: 宝宝哭闹、拒食、不安、家长焦虑、寻求帮助
- **问题类型**: 喂养困难、营养担忧、发育问题、适应困扰
- **解决导向**: 专家建议、改善方案、产品推荐、问题解答

## 📝 输出格式要求

请严格按照以下JSON格式输出，确保格式正确：

```json
{
    "predicted_category": "🌟 使用效果",
    "confidence": 0.85,
    "reasoning": "分类依据的详细说明",
    "matched_keywords": ["匹配到的关键信息"],
    "category_analysis": {
        "primary_indicators": ["主要判断指标"],
        "emotional_tone": "情感基调",
        "content_focus": "内容焦点"
    }
}
```

注意：predicted_category必须是完整的emoji格式："🌟 使用效果"、"🍼 产品介绍_蕴淳"、"🍼 产品介绍_水奶"、"🍼 产品介绍_蓝钻"、"🎁 促销机制"或"🪝 钩子"

请开始分析以下Labels内容：""",

            "enhanced": """🎯 你是资深的母婴内容分析专家，请对以下Labels内容进行深度语义分析和精确分类。

## 📋 增强分类标准

### 🌟 使用效果 - 深度识别标准
**核心语义特征**:
- 效果展示词汇: "活泼"、"蹦跳"、"开心"、"健康"、"成长"、"进步"
- 满意表达: "满意"、"喜欢"、"很棒"、"不错"、"好"、"棒"
- 对比描述: "现在"、"以前"、"改善"、"变化"、"效果"
- 积极行为: "主动"、"愿意"、"爱喝"、"接受"、"适应"

### 🍼 产品介绍_蕴淳 - 深度识别标准  
**核心语义特征**:
- 品牌词汇: "蕴淳"、"蕴醇"、"启赋蕴淳"、"启赋蕴醇"、"惠氏"
- 核心成分: "HMO"、"母乳低聚糖"、"OPN"、"α-乳清蛋白"、"核心配方"
- 科学背景: "营养科学"、"科研实力"、"品牌背景"、"权威认证"
- 展示方式: "配方介绍"、"成分解析"、"科学依据"、"专业推荐"

### 🍼 产品介绍_水奶 - 深度识别标准
**核心语义特征**:
- 产品词汇: "水奶"、"便携装"、"液体奶"、"即饮"、"小瓶装"
- 奶源特点: "A2奶源"、"A2蛋白质"、"新鲜"、"即开即饮"
- 便利特性: "携带方便"、"便携"、"随身"、"方便"、"即时"
- 使用场景: "外出"、"旅行"、"便利性"、"即饮体验"

### 🍼 产品介绍_蓝钻 - 深度识别标准
**核心语义特征**:
- 品牌词汇: "蓝钻"、"钻石系列"、"高端"、"顶级"、"旗舰"
- 品质定位: "premium"、"升级配方"、"顶级品质"、"高端系列"
- 配方特点: "升级"、"进阶"、"优化"、"增强"、"高端配方"
- 市场定位: "旗舰产品"、"精选"、"臻选"、"卓越"

### 🎁 促销机制 - 深度识别标准
**核心语义特征**:
- 情感词汇: "温馨"、"和谐"、"幸福"、"甜蜜"、"关爱"、"陪伴"
- 互动行为: "亲子"、"一起"、"陪伴"、"游戏"、"聊天"、"拥抱"
- 生活场景: "家庭"、"日常"、"生活"、"时光"、"时刻"、"瞬间"
- 价值传递: "爱"、"关怀"、"呵护"、"守护"、"珍惜"

### 🪝 钩子 - 深度识别标准
**核心语义特征**:
- 问题词汇: "哭闹"、"不安"、"拒绝"、"困扰"、"担心"、"焦虑"
- 负面状态: "不舒服"、"不适应"、"不喜欢"、"难受"、"问题"
- 寻求帮助: "怎么办"、"如何"、"专家"、"建议"、"解决"、"改善"
- 迫切需求: "急需"、"希望"、"想要"、"需要"、"渴望"

## 🔍 语义分析流程

1. **词汇分析**: 识别核心关键词的语义归属
2. **情感分析**: 判断整体情感倾向和基调
3. **行为分析**: 分析描述的主要行为和动作
4. **场景分析**: 理解内容所处的具体场景环境
5. **意图分析**: 推断内容传达的主要意图和目的

## 📊 置信度评估标准

- **0.9-1.0**: 关键词匹配度极高，语义指向明确
- **0.7-0.8**: 关键词匹配度较高，语义指向清晰
- **0.5-0.6**: 关键词匹配度一般，需要推理判断
- **0.3-0.4**: 关键词匹配度较低，存在模糊性
- **0.0-0.2**: 关键词匹配度很低，分类困难

⚠️ **格式要求**: predicted_category字段必须使用完整的emoji格式，如"🌟 使用效果"、"🍼 产品介绍_蕴淳"、"🍼 产品介绍_水奶"、"🍼 产品介绍_蓝钻"、"🎁 促销机制"、"🪝 钩子"

请进行深度语义分析并分类："""
        }
    
    def classify_primary_category(self, labels_text: str, enhanced: bool = False) -> Tuple[str, float, Dict]:
        """
        对Labels内容进行主标签分类
        
        Args:
            labels_text: 待分类的Labels文本内容
            enhanced: 是否使用增强模式（用于复杂情况）
            
        Returns:
            Tuple[predicted_category, confidence, analysis_result]
        """
        try:
            logger.info(f"🎯 开始主标签分类: {'增强模式' if enhanced else '标准模式'}")
            
            # 使用基类的分类方法
            result = self.classify(labels_text, enhanced)
            
            if not result or "error" in result:
                logger.error("主标签分类失败")
                return "未知", 0.0, result or {"error": "分类失败"}
            
            # 解析结果
            predicted_category = result.get("predicted_category", "未知")
            confidence = float(result.get("confidence", 0.0))
            
            # 🔧 标准化标签 - 将AI返回的文本标签转换为标准emoji标签
            if predicted_category != "未知":
                original_category = predicted_category
                predicted_category = self._normalize_main_tag(predicted_category)
                
                if predicted_category == "未知" and original_category != "未知":
                    logger.warning(f"⚠️ 标签标准化失败: '{original_category}' -> 未知")
                    confidence = 0.0
                elif predicted_category != original_category:
                    logger.info(f"🔧 标签已标准化: '{original_category}' -> '{predicted_category}'")
            
            # 验证最终标签是否有效
            if predicted_category not in self.main_categories and predicted_category != "未知":
                logger.warning(f"❌ 无效的主标签类别: {predicted_category}")
                predicted_category = "未知"
                confidence = 0.0
            
            logger.info(f"✅ 主标签分类完成: {predicted_category} (置信度: {confidence:.2f})")
            
            return predicted_category, confidence, result
            
        except Exception as e:
            logger.error(f"主标签分类异常: {e}")
            return "未知", 0.0, {"error": str(e)}

    def classify_single_item(self, item_data: Dict) -> Dict:
        """
        对单个切片项目进行主标签分类 - 符合统一处理管理器调用接口
        
        Args:
            item_data: 包含labels和slice_name的字典
                     {"labels": "标签文本", "slice_name": "切片名称"}
        
        Returns:
            Dict: 包含success, main_tag, confidence, analysis字段的结果
        """
        try:
            labels_text = item_data.get("labels", "")
            slice_name = item_data.get("slice_name", "unknown")
            
            if not labels_text:
                return {
                    "success": False,
                    "error": "标签文本为空",
                    "slice_name": slice_name
                }
            
            # 调用主标签分类
            predicted_category, confidence, analysis = self.classify_primary_category(labels_text)
            
            # 检查分类是否成功
            if predicted_category and predicted_category != "未知" and confidence > 0:
                return {
                    "success": True,
                    "main_tag": predicted_category,
                    "confidence": confidence,
                    "analysis": analysis,
                    "slice_name": slice_name,
                    "processed_at": self._get_timestamp()
                }
            else:
                return {
                    "success": False,
                    "main_tag": predicted_category,
                    "confidence": confidence,
                    "analysis": analysis,
                    "slice_name": slice_name,
                    "error": "分类失败或置信度过低"
                }
                
        except Exception as e:
            logger.error(f"单项分类异常 {item_data.get('slice_name', 'unknown')}: {e}")
            return {
                "success": False,
                "error": str(e),
                "slice_name": item_data.get("slice_name", "unknown")
            }
    
    def batch_classify_primary(self, slice_data_list: List[Dict], 
                             min_confidence: float = 0.5) -> List[Dict]:
        """
        批量主标签分类
        
        Args:
            slice_data_list: 切片数据列表
            min_confidence: 最小置信度阈值
            
        Returns:
            更新后的切片数据列表
        """
        try:
            logger.info(f"🔄 开始批量主标签分类: {len(slice_data_list)} 个切片")
            
            processed_count = 0
            success_count = 0
            
            for slice_data in slice_data_list:
                try:
                    labels_text = slice_data.get("labels", "")
                    if not labels_text:
                        logger.warning(f"切片 {slice_data.get('segment_id', '未知')} 的labels为空")
                        continue
                    
                    # 执行主标签分类
                    predicted_category, confidence, analysis_result = self.classify_primary_category(labels_text)
                    
                    # 更新切片数据
                    slice_data["main_tag"] = predicted_category
                    slice_data["main_tag_confidence"] = confidence
                    slice_data["main_tag_analysis"] = analysis_result
                    
                    processed_count += 1
                    
                    if confidence >= min_confidence:
                        success_count += 1
                        logger.debug(f"✅ 切片 {slice_data.get('segment_id', '未知')}: {predicted_category} ({confidence:.2f})")
                    else:
                        logger.warning(f"⚠️ 切片 {slice_data.get('segment_id', '未知')} 置信度过低: {confidence:.2f}")
                        
                except Exception as e:
                    logger.error(f"处理切片失败: {e}")
                    continue
            
            logger.info(f"✅ 批量主标签分类完成: {processed_count}/{len(slice_data_list)} 处理, {success_count} 成功")
            
            return slice_data_list
            
        except Exception as e:
            logger.error(f"批量主标签分类异常: {e}")
            return slice_data_list
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    


# 全局主标签分类器实例
_primary_classifier = None

def get_primary_ai_classifier() -> PrimaryAIClassifier:
    """获取全局主标签分类器实例"""
    global _primary_classifier
    if _primary_classifier is None:
        _primary_classifier = PrimaryAIClassifier()
    return _primary_classifier

# ========================================
# 向后兼容的公共函数接口
# ========================================

def get_main_tag_prompt(enhanced: bool = False) -> str:
    """获取主标签分类提示词（向后兼容）"""
    classifier = get_primary_ai_classifier()
    template_key = "enhanced" if enhanced else "standard"
    return classifier._build_classification_prompts().get(template_key, "")

def optimize_main_tag_prompts_from_feedback(feedback_file: str, reason: str = "用户反馈优化") -> bool:
    """基于反馈文件优化主标签提示词（向后兼容）"""
    try:
        logger.info(f"📝 主标签提示词优化请求: {reason}")
        logger.warning("⚠️ 当前版本使用内置提示词模板，优化功能已简化")
        
        # 在统一架构中，提示词优化将通过更高级别的机制处理
        # 这里保持接口兼容性，实际优化逻辑可以在后续版本中实现
        
        return True
        
    except Exception as e:
        logger.error(f"主标签提示词优化失败: {e}")
        return False

if __name__ == "__main__":
    pass