#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态脚本匹配配置文件
支持运行时输入脚本，并提供灵活的匹配规则和关键词映射
"""

from typing import Dict, List, Any

class DynamicMatchConfig:
    """动态匹配配置 - 支持运行时脚本输入"""

    def __init__(self):
        """初始化动态配置"""
        # 不再硬编码EXAMPLE_SCRIPT
        self.current_script_segments: Dict[str, str] = {}
        self.analyzed_segments: List[Dict[str, Any]] = []

        # JSON字段匹配权重配置
        self.MATCH_WEIGHTS: Dict[str, float] = {
            "object": 0.25,
            "emotion": 0.20,
            "scene": 0.20,
            "main_tag": 0.15,
            "matched_keywords": 0.10,
            "reasoning": 0.05,
            "secondary_category": 0.05,
        }

        # 关键词映射表
        self._initialize_keyword_mappings()

        # DeepSeek AI 匹配提示模板
        self.DEEPSEEK_PROMPT = self._get_deepseek_prompt_template()

        # 质量控制标准
        self.QUALITY_STANDARDS: Dict[str, Any] = {
            "high_quality_threshold": 0.8,
            "medium_quality_threshold": 0.5,
            "min_acceptable_threshold": 0.2,  # 降低阈值，扩大收录
            "max_matches_per_segment": 100,     # 提升最大收录数量
        }

    def load_user_script(self, script_segments: Dict[str, str]):
        """加载并解析用户提供的脚本"""
        self.current_script_segments = script_segments
        self.analyzed_segments = self._analyze_script_segments(script_segments)

    def _analyze_script_segments(self, segments: Dict[str, str]) -> List[Dict[str, Any]]:
        """智能分析脚本段落"""
        analyzed_list = []
        for segment_id, content in segments.items():
            segment_type = self._get_segment_type(content)
            keywords = self._extract_script_keywords(content)
            emotions = self._get_expected_emotions(content)
            
            analyzed_list.append({
                "id": segment_id,
                "content": content,
                "type": segment_type,
                "keywords": keywords,
                "expected_emotions": emotions,
            })
        return analyzed_list

    def _get_segment_type(self, content: str) -> str:
        """根据脚本内容动态分析段落类型"""
        # 这是一个简化的实现，未来可以用AI来增强
        type_scores = {segment_type: 0 for segment_type in self.SCRIPT_SEGMENT_KEYWORDS}
        
        for segment_type, keywords in self.SCRIPT_SEGMENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content:
                    type_scores[segment_type] += 1
        
        # 返回得分最高的类型
        if any(type_scores.values()):
            return max(type_scores, key=type_scores.get)
        
        return "通用段落"

    def _extract_script_keywords(self, content: str) -> List[str]:
        """从脚本内容中提取所有相关关键词"""
        keywords = set()
        all_mappings = [
            self.SCRIPT_SEGMENT_KEYWORDS,  # 添加脚本段落关键词映射
            self.EMOTION_MAPPING, 
            self.SCENE_MAPPING, 
            self.ACTION_MAPPING, 
            self.BRAND_MAPPING
        ]
        for mapping in all_mappings:
            for keyword_list in mapping.values():
                for keyword in keyword_list:
                    if keyword in content:
                        keywords.add(keyword)
        return list(keywords)

    def _get_expected_emotions(self, content: str) -> List[str]:
        """根据脚本内容推测预期情绪"""
        emotions = set()
        for emotion, keywords in self.EMOTION_MAPPING.items():
            for keyword in keywords:
                if keyword in content:
                    emotions.add(emotion)
        return list(emotions)

    def _initialize_keyword_mappings(self):
        """初始化所有关键词映射表"""
        self.SCRIPT_SEGMENT_KEYWORDS = {
            "情绪表达": ["狗都不", "生！", "冲了", "试错"],
            "产品背书": ["百年科研", "品牌", "专业渠道", "惠氏", "制药背景"],
            "动作描述": ["妈妈", "拿奶瓶", "摇头", "喂养", "宝宝"],
            "科研配方": ["HMO", "配方", "研究", "科研背景"],
            "宝宝状态": ["小肉宝", "好带", "互动", "可爱", "趴地上"],
            "口播推荐": ["对镜头", "口播", "推荐", "选择", "建议"],
        }
        self.EMOTION_MAPPING = {
            "开心": ["开心", "高兴", "快乐", "欢乐", "笑"], "哭闹": ["哭", "哭闹", "不安", "烦躁"],
            "无奈": ["无奈", "摇头", "叹气"], "温馨": ["温馨", "温暖", "和谐", "亲密"],
            "专业": ["专业", "权威", "科研"], "激动": ["激动", "兴奋", "热情", "冲了"],
        }
        self.SCENE_MAPPING = { "室内家庭": ["室内", "家里", "客厅", "厨房"], "产品展示": ["奶粉罐", "产品", "包装"], "口播场景": ["口播", "讲解", "对镜头"],}
        self.ACTION_MAPPING = { "拿着": ["拿着", "握着"], "看着": ["看着", "注视"], "摇头": ["摇头", "摆头"], "喂养": ["喂奶", "喂食"], "互动": ["互动", "玩耍"], }
        self.BRAND_MAPPING = { "惠氏": ["惠氏"], "启赋": ["启赋"], "HMO": ["HMO"], }

    def _get_deepseek_prompt_template(self) -> str:
        """获取DeepSeek AI的提示模板"""
        return """
你是一个专业的视频内容匹配分析师。请根据以下信息进行匹配分析：

## 脚本段落信息：
- 内容：{script_content}
- 类型：{script_type}
- 关键词：{script_keywords}
- 预期情绪：{expected_emotions}

## 视频切片JSON信息：
- 对象描述：{object}
- 场景描述：{scene}  
- 情绪状态：{emotion}
- 主标签：{main_tag}
- 关键词：{matched_keywords}
- 分析推理：{reasoning}

## 匹配任务：
请分析视频切片是否适合该脚本段落，并以JSON格式回答：
{{
    "match_score": 0.0-1.0,
    "match_reason": "匹配理由",
    "mismatch_issues": ["问题1", "问题2"]
}}
"""

if __name__ == '__main__':
    # --- 测试动态配置系统 ---
    print("🧪 测试动态匹配配置系统...")
    
    # 1. 模拟用户输入的脚本
    user_script = {
        "S01": "能自己喂肯定是更好的，但凡你决定了奶粉喂养，就一定要选有百年科研实力，专业渠道也认可的品牌。",
        "S02": "妈妈拿着奶瓶无奈摇头，宝宝饿得一直哭闹",
    }
    
    # 2. 创建并加载配置
    dynamic_config = DynamicMatchConfig()
    dynamic_config.load_user_script(user_script)
    
    # 3. 打印分析结果
    print(f"\n✅ 成功加载并解析了 {len(dynamic_config.analyzed_segments)} 个脚本段落。")
    for i, analyzed_seg in enumerate(dynamic_config.analyzed_segments, 1):
        print(f"\n--- 段落 {i} ---")
        print(f"  ID: {analyzed_seg['id']}")
        print(f"  内容: '{analyzed_seg['content'][:30]}...'")
        print(f"  -> 识别类型: {analyzed_seg['type']}")
        print(f"  -> 提取关键词: {analyzed_seg['keywords']}")
        print(f"  -> 预期情绪: {analyzed_seg['expected_emotions']}")

    print("\n🎉 动态配置系统工作正常！")
