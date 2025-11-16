#!/usr/bin/env python3
"""
词级语义分割器 - 智能SRT语义分析与精确切分

功能特性:
1. 提取词级时间戳 (精确到每个词汇)
2. DeepSeek/Claude语义分析 (钩子、产品介绍、使用效果、促销机制)
3. 模型效果对比分析
4. 输出精确的模块化SRT

使用场景:
- 解决长片段模块划分不清晰问题
- 提供词级精度的时间戳
- 语义驱动的智能切分
"""

import json
import logging
import tempfile
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import os
import sys

# 添加当前路径到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from env_loader import load_env_config

logger = logging.getLogger(__name__)

@dataclass
class WordTimestamp:
    """词级时间戳数据结构"""
    text: str
    start_time: float
    end_time: float
    confidence: float

@dataclass
class SemanticSegment:
    """语义片段数据结构"""
    id: int
    start_time: float
    end_time: float
    text: str
    semantic_label: str  # 🪝钩子, 🍼产品介绍, 🌟使用效果, 🎁促销机制
    confidence: float
    words: List[WordTimestamp]

class WordLevelSemanticSplitter:
    """词级语义分割器"""
    
    def __init__(self, deepseek_api_key: str = None, claude_api_key: str = None, domain_config: Dict[str, Any] = None):
        """
        初始化词级语义分割器
        
        Args:
            deepseek_api_key: DeepSeek API密钥
            claude_api_key: Claude API密钥  
            domain_config: 领域配置，包含类别定义、关键词等
        """
        # 加载环境配置
        load_env_config()
        
        # API密钥配置
        self.deepseek_api_key = deepseek_api_key or os.getenv('DEEPSEEK_API_KEY')
        self.claude_api_key = claude_api_key or os.getenv('OPENROUTER_API_KEY')
        
        # 领域配置 - 支持自定义或使用默认母婴配置
        self.domain_config = domain_config or self._get_default_baby_formula_config()
        
        logger.info("✅ 词级语义分割器初始化完成")
        logger.info(f"🎯 领域: {self.domain_config.get('domain_name', '未知')}")
        logger.info(f"📋 支持类别: {list(self.domain_config.get('categories', {}).keys())}")
        
        # 动态关键词学习缓存
        self.dynamic_keywords = {
            "🪝 钩子": set(),
            "🍼 产品介绍": set(), 
            "🌟 使用效果": set(),
            "🎁 促销机制": set()
        }
    
    def _update_dynamic_keywords(self, segments: List[Dict[str, Any]]):
        """基于分析结果动态更新关键词库"""
        for segment in segments:
            category = segment.get('category', '')
            text = segment.get('text', '')
            confidence = segment.get('confidence', 0)
            
            # 只从高置信度片段学习新关键词
            if confidence > 0.85 and category in self.dynamic_keywords:
                # 提取新词汇（简单实现）
                words = text.split()
                for word in words:
                    # 过滤掉常见词汇，只保留潜在的专业词汇
                    if len(word) > 1 and word not in ['的', '是', '有', '在', '和', '或', '但', '都', '就', '也', '还', '又', '了', '着', '过']:
                        self.dynamic_keywords[category].add(word)
    
    def _get_enhanced_keywords(self, category: str) -> List[str]:
        """获取增强的关键词列表（静态+动态）"""
        static_keywords = self.domain_config.get("categories", {}).get(category, {}).get("keywords", [])
        dynamic_keywords = list(self.dynamic_keywords.get(category, set()))
        return static_keywords + dynamic_keywords
    
    def _calculate_category_confidence(self, text: str, category: str) -> float:
        """计算文本属于特定类别的置信度"""
        keywords = self._get_enhanced_keywords(category)
        matches = sum(1 for keyword in keywords if keyword in text)
        
        if not keywords:
            return 0.5  # 默认置信度
            
        # 基于关键词匹配率和权重计算置信度
        base_confidence = min(matches / len(keywords) * 2, 1.0)  # 最大1.0
        weight_multiplier = self.domain_config.get("categories", {}).get(category, {}).get("weight_multiplier", 1.0)
        
        return min(base_confidence * weight_multiplier, 0.95)  # 最大0.95
    
    def _evaluate_generalization(self, analysis_result: Dict[str, Any], full_text: str) -> float:
        """评估系统对新内容的泛化能力"""
        if not analysis_result or not analysis_result.get('semantic_segments'):
            return 0.0
        
        segments = analysis_result['semantic_segments']
        total_score = 0.0
        
        # 1. 置信度评估 (40%)
        avg_confidence = sum(seg.get('confidence', 0) for seg in segments) / len(segments)
        confidence_score = avg_confidence * 0.4
        
        # 2. 覆盖率评估 (30%) - 检查是否有遗漏的重要内容
        total_chars = len(full_text)
        covered_chars = sum(len(seg.get('text', '')) for seg in segments)
        coverage_score = min(covered_chars / total_chars, 1.0) * 0.3
        
        # 3. 类别分布合理性 (20%) - 检查类别分布是否合理
        category_counts = {}
        for seg in segments:
            category = seg.get('category', '')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # 理想的启赋广告应该有钩子、产品介绍、使用效果
        expected_categories = {"🪝 钩子", "🍼 产品介绍", "🌟 使用效果"}
        found_categories = set(category_counts.keys())
        category_completeness = len(expected_categories & found_categories) / len(expected_categories)
        distribution_score = category_completeness * 0.2
        
        # 4. 新词汇识别能力 (10%) - 检查是否识别出新的专业词汇
        static_keywords = set()
        for category_config in self.domain_config.get("categories", {}).values():
            static_keywords.update(category_config.get("keywords", []))
        
        text_words = set(full_text.split())
        new_words = text_words - static_keywords
        
        # 如果识别出新的专业词汇，给予奖励
        professional_new_words = 0
        for word in new_words:
            if len(word) > 2 and any(char.isalpha() for char in word):
                professional_new_words += 1
        
        novelty_score = min(professional_new_words / max(len(text_words), 1), 0.1) * 0.1
        
        total_score = confidence_score + coverage_score + distribution_score + novelty_score
        
        return min(total_score, 1.0)
    
    def export_enhanced_config(self, output_path: str = "enhanced_domain_config.json"):
        """导出增强后的领域配置（包含学习到的新关键词）"""
        enhanced_config = self.domain_config.copy()
        
        # 合并动态学习的关键词
        for category, static_config in enhanced_config.get("categories", {}).items():
            if category in self.dynamic_keywords:
                dynamic_words = list(self.dynamic_keywords[category])
                if dynamic_words:
                    static_keywords = static_config.get("keywords", [])
                    enhanced_keywords = static_keywords + dynamic_words
                    static_config["keywords"] = list(set(enhanced_keywords))  # 去重
                    static_config["dynamic_learned_count"] = len(dynamic_words)
        
        # 添加泛化能力统计
        enhanced_config["generalization_stats"] = {
            "total_dynamic_keywords": sum(len(words) for words in self.dynamic_keywords.values()),
            "categories_enhanced": [cat for cat, words in self.dynamic_keywords.items() if words],
            "enhancement_timestamp": str(logger.handlers[0].formatter.formatTime(logger.handlers[0], logger.makeRecord("", 0, "", 0, "", (), None)) if logger.handlers else "unknown")
        }
        
        try:
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(enhanced_config, f, ensure_ascii=False, indent=2)
            logger.info(f"📄 增强配置已导出: {output_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 配置导出失败: {e}")
            return False
    
    def load_enhanced_config(self, config_path: str):
        """加载增强后的领域配置"""
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                self.domain_config = json.load(f)
            logger.info(f"📄 增强配置已加载: {config_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 配置加载失败: {e}")
            return False
    
    def _analyze_with_retry(self, analyze_func, text: str, model_name: str, max_retries: int = 2) -> Optional[Dict[str, Any]]:
        """带重试机制的AI分析方法"""
        import time
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"🔄 {model_name} 第{attempt + 1}次尝试...")
                result = analyze_func(text)
                if result:
                    logger.info(f"✅ {model_name} 第{attempt + 1}次尝试成功")
                    return result
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"⚠️ {model_name} 第{attempt + 1}次网络超时: {e}")
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 2  # 2, 4, 6秒等待
                    logger.info(f"⏳ 等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise TimeoutError(f"{model_name} API连续{max_retries + 1}次超时")
            except Exception as e:
                logger.error(f"❌ {model_name} 第{attempt + 1}次分析错误: {e}")
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 1  # 1, 2, 3秒等待
                    logger.info(f"⏳ 等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise
        
        return None
    
    def _get_proxy_config(self) -> Optional[Dict[str, str]]:
        """获取代理配置"""
        # 从环境变量读取代理配置
        http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
        
        if http_proxy or https_proxy:
            proxies = {}
            if http_proxy:
                proxies['http'] = http_proxy
            if https_proxy:
                proxies['https'] = https_proxy
            logger.info(f"🌐 使用代理配置: {proxies}")
            return proxies
        
        return None
    
    def _get_default_baby_formula_config(self) -> Dict[str, Any]:
        """获取默认的母婴奶粉领域配置（增强泛化版）"""
        return {
            "domain_name": "母婴奶粉营销",
            "categories": {
                "🪝 钩子": {
                    "description": "宝宝哭闹、家长焦虑、喂养困扰、专家建议、问题解决、改善需求、担心顾虑、寻求帮助、科学发现、研究结果",
                    "keywords": ["哭闹", "夜醒", "睡不好", "不安", "困扰", "担心", "焦虑", "问题", "薄弱期", "消耗光", "妈妈不知道", "90%", "你家宝宝", "频繁", "原来", "研究发现", "专家说", "科学证明"],
                    "weight_multiplier": 1.0
                },
                "🍼 产品介绍": {
                    "description": "产品展示、包装特写、成分介绍、冲泡演示、品牌标识、营养配方、专业推荐、质量认证、科技创新",
                    "keywords": ["惠氏", "启赋", "蕴醇", "蕴淳", "水奶", "有机", "奶粉", "配方", "营养", "成分", "母乳", "低聚糖", "蛋白", "A2", "奶源", "HMO", "OPN", "2'-FL", "α-乳清蛋白", "DHA", "ARA", "益生菌", "核苷酸", "叶黄素", "胆碱", "牛磺酸", "铁", "锌", "钙", "维生素", "亲和", "天然", "纯净", "原装进口", "瑞士", "爱尔兰"],
                    "weight_multiplier": 1.2
                },
                "🌟 使用效果": {
                    "description": "宝宝活泼、效果展示、满意反馈、健康发育、快乐玩耍、成长对比、营养效果、家长夸赞、智力发展、体格发育",
                    "keywords": ["自愈力", "开挂", "平稳", "度过", "更好", "吸收", "健康", "活泼", "效果", "改善", "直接", "能让", "好吸收", "平稳度过", "保护力", "抵抗力", "免疫力", "聪明", "智力", "发育", "成长", "强壮", "消化好", "不上火", "不便秘", "睡得香", "长得快", "聪明伶俐"],
                    "weight_multiplier": 1.1
                },
                "🎁 促销机制": {
                    "description": "优惠活动、限时折扣、礼品赠送、试用装、会员福利、购买渠道、客服咨询、售后保障",
                    "keywords": ["限时", "专享", "试喝", "大促", "囤", "优惠", "活动", "福利", "折扣", "满减", "买赠", "礼盒", "试用装", "新客", "会员", "积分", "返现", "包邮", "客服", "咨询", "保障", "正品", "授权", "官方"],
                    "weight_multiplier": 1.0
                }
            },
            "semantic_boundaries": [
                # 钩子 → 产品介绍
                {
                    "pattern": r"(困扰|问题|薄弱期|焦虑|担心|研究|专家).{0,20}(惠氏|启赋|配方|奶粉|选好|蕴醇|水奶|有机)",
                    "from_category": "🪝 钩子",
                    "to_category": "🍼 产品介绍",
                    "description": "钩子转向产品介绍"
                },
                # 产品介绍 → 使用效果
                {
                    "pattern": r"(配方|成分|营养|母乳|低聚糖|蛋白|奶源|HMO|OPN|DHA|维生素).{0,20}(自愈力|开挂|效果|改善|平稳|度过|吸收|健康|发育|成长|聪明|强壮)",
                    "from_category": "🍼 产品介绍", 
                    "to_category": "🌟 使用效果",
                    "description": "产品介绍转向使用效果"
                },
                # 使用效果 → 产品介绍
                {
                    "pattern": r"(自愈力|开挂|效果|改善|平稳|度过|健康|聪明|发育).{0,20}(再加上|奶源|营养|成分|A2|配方|惠氏|启赋|蕴醇|水奶)",
                    "from_category": "🌟 使用效果",
                    "to_category": "🍼 产品介绍",
                    "description": "使用效果转回产品介绍"
                },
                # 使用效果 → 促销机制
                {
                    "pattern": r"(效果|改善|健康|营养|发育|成长|聪明).{0,20}(限时|专享|试喝|大促|囤|现在|优惠|活动|折扣|新客)",
                    "from_category": "🌟 使用效果",
                    "to_category": "🎁 促销机制",
                    "description": "使用效果转向促销机制"
                },
                # 产品介绍 → 促销机制
                {
                    "pattern": r"(奶源|营养|吸收|配方|成分|惠氏|启赋).{0,20}(限时|专享|试喝|大促|囤|现在|优惠|活动|折扣|新客|价格|购买)",
                    "from_category": "🍼 产品介绍",
                    "to_category": "🎁 促销机制",
                    "description": "产品介绍转向促销机制"
                },
                # 钩子 → 使用效果（直接）
                {
                    "pattern": r"(问题|困扰|薄弱期|不安).{0,20}(自愈力|开挂|效果|改善|平稳|度过|健康|发育)",
                    "from_category": "🪝 钩子",
                    "to_category": "🌟 使用效果",
                    "description": "钩子直接转向使用效果"
                }
            ]
        }

    def analyze_srt_with_word_timestamps(self, srt_path: str, transcription_result: Dict[str, Any] = None) -> List[SemanticSegment]:
        """
        分析SRT文件，提取词级时间戳并进行语义分割
        
        Args:
            srt_path: SRT文件路径
            transcription_result: 转录结果（包含词级时间戳）
            
        Returns:
            List[SemanticSegment]: 语义分割后的片段列表
        """
        try:
            # 1. 提取词级时间戳
            word_timestamps = self._extract_word_timestamps(transcription_result)
            if not word_timestamps:
                raise ValueError("❌ 未找到词级时间戳，无法进行语义分析")
            
            logger.info(f"📊 提取到 {len(word_timestamps)} 个词级时间戳")
            
            # 2. 合并完整文本
            full_text = ''.join([word.text for word in word_timestamps])
            
            # 3. AI语义分析（严格模式：失败即报错）
            analysis_result = None
            
            # 尝试DeepSeek分析（带重试）
            try:
                analysis_result = self._analyze_with_retry(self._analyze_with_deepseek, full_text, "DeepSeek")
                logger.info("✅ 使用DeepSeek分析结果")
            except Exception as e:
                logger.warning(f"⚠️ DeepSeek分析失败: {e}")
                
                # 如果DeepSeek失败，尝试Claude（如果可用）
                if self.claude_api_key:
                    try:
                        analysis_result = self._analyze_with_retry(self._analyze_with_claude, full_text, "Claude")
                        logger.info("✅ 使用Claude分析结果")
                    except Exception as claude_e:
                        logger.error(f"❌ Claude分析也失败: {claude_e}")
                        raise RuntimeError(f"所有AI分析方法都失败。DeepSeek: {e}, Claude: {claude_e}")
                else:
                    raise RuntimeError(f"DeepSeek分析失败且未配置Claude: {e}")
            
            if not analysis_result:
                raise RuntimeError("❌ 未获得有效的AI分析结果")
            
            # 4. 基于语义分析结果进行词级切分
            semantic_segments = self._create_semantic_segments(word_timestamps, analysis_result)
            
            # 5. 动态学习新关键词（提高泛化能力）
            if analysis_result and analysis_result.get('semantic_segments'):
                self._update_dynamic_keywords(analysis_result['semantic_segments'])
                logger.info(f"🧠 动态学习完成，更新关键词库")
            
            # 6. 评估泛化能力
            generalization_score = self._evaluate_generalization(analysis_result, full_text)
            logger.info(f"📊 泛化能力评分: {generalization_score:.2f}/1.0")
            
            logger.info(f"✅ 语义分割完成，生成 {len(semantic_segments)} 个语义片段")
            
            return semantic_segments
            
        except Exception as e:
            logger.error(f"❌ 词级语义分析失败: {e}")
            return []
    
    def _extract_word_timestamps(self, transcription_result: Dict[str, Any]) -> List[WordTimestamp]:
        """从转录结果中提取词级时间戳"""
        word_timestamps = []
        
        try:
            logger.info("🔍 开始提取词级时间戳...")
            
            # 检查是否有原始转录数据
            raw_output = transcription_result.get('raw_output', {})
            if not raw_output:
                logger.warning("⚠️ 转录结果中没有raw_output数据")
                return self._extract_from_segments(transcription_result)
            
            # 方法1: 从results中的transcription_url获取
            results = raw_output.get('results', [])
            for result in results:
                transcription_url = result.get('transcription_url')
                if transcription_url:
                    logger.info(f"📥 下载词级转录详情: {transcription_url}")
                    detailed_result = self._download_transcription_details(transcription_url)
                    if detailed_result:
                        words = self._parse_word_timestamps_from_result(detailed_result)
                        word_timestamps.extend(words)
                        
            if word_timestamps:
                logger.info(f"✅ 方法1成功: 提取到 {len(word_timestamps)} 个词级时间戳")
                return word_timestamps
            
            # 方法2: 从segments中提取（备用方案）
            logger.info("🔄 尝试从segments提取词级信息...")
            segments = transcription_result.get('segments', [])
            
            for segment in segments:
                text = segment.get('text', '')
                start_time = segment.get('start_time', 0)
                end_time = segment.get('end_time', 0)
                
                # 估算每个字符的时间戳
                if text and end_time > start_time:
                    duration = end_time - start_time
                    char_duration = duration / len(text)
                    
                    for i, char in enumerate(text):
                        char_start = start_time + i * char_duration
                        char_end = char_start + char_duration
                        
                        word_timestamps.append(WordTimestamp(
                            text=char,
                            start_time=char_start,
                            end_time=char_end,
                            confidence=0.8  # 估算置信度
                        ))
            
            if word_timestamps:
                logger.info(f"✅ 方法2成功: 生成 {len(word_timestamps)} 个字符级时间戳")
                return word_timestamps
            
            logger.warning("⚠️ 无法提取词级时间戳")
            return []
            
        except Exception as e:
            logger.error(f"❌ 提取词级时间戳失败: {e}")
            return []
    
    def _extract_from_segments(self, transcription_result: Dict[str, Any]) -> List[WordTimestamp]:
        """从segments中提取词级时间戳（备用方案）"""
        word_timestamps = []
        
        try:
            segments = transcription_result.get('segments', [])
            logger.info(f"📊 处理 {len(segments)} 个段落...")
            
            for segment in segments:
                text = segment.get('text', '')
                start_time = segment.get('start_time', 0)
                end_time = segment.get('end_time', 0)
                
                if not text or end_time <= start_time:
                    continue
                
                # 按词汇分割（简单的中文分词）
                words = self._simple_word_split(text)
                if not words:
                    continue
                
                # 计算每个词的时间戳
                duration = end_time - start_time
                word_duration = duration / len(words)
                
                for i, word in enumerate(words):
                    word_start = start_time + i * word_duration
                    word_end = word_start + word_duration
                    
                    word_timestamps.append(WordTimestamp(
                        text=word,
                        start_time=word_start,
                        end_time=word_end,
                        confidence=0.7
                    ))
            
            return word_timestamps
            
        except Exception as e:
            logger.error(f"❌ 从segments提取失败: {e}")
            return []
    
    def _simple_word_split(self, text: str) -> List[str]:
        """简单的中文分词"""
        import re
        
        # 按标点符号和空格分割
        words = re.findall(r'[^，。！？；：、\s]+', text)
        
        # 进一步分割长词
        result = []
        for word in words:
            if len(word) > 4:
                # 长词按2-3字符分割
                for i in range(0, len(word), 2):
                    result.append(word[i:i+2])
            else:
                result.append(word)
        
        return result
    
    def _download_transcription_details(self, transcription_url: str) -> Optional[Dict[str, Any]]:
        """下载详细的转录结果"""
        try:
            response = requests.get(transcription_url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ 下载转录详情失败: {e}")
            return None
    
    def _parse_word_timestamps_from_result(self, transcription_data: Dict[str, Any]) -> List[WordTimestamp]:
        """从转录数据中解析词级时间戳"""
        word_timestamps = []
        
        try:
            logger.info("📊 开始解析词级时间戳数据...")
            logger.info(f"🔍 转录数据键: {list(transcription_data.keys())}")
            
            # 方法1: 查找transcripts -> sentences -> words结构 (DashScope标准格式)
            transcripts = transcription_data.get('transcripts', [])
            if transcripts:
                logger.info(f"📝 找到 {len(transcripts)} 个转录，解析词级信息...")
                for transcript in transcripts:
                    # 获取句子级数据
                    sentences = transcript.get('sentences', [])
                    if sentences:
                        logger.info(f"📝 转录中包含 {len(sentences)} 个句子")
                        for sentence in sentences:
                            words = sentence.get('words', [])
                            logger.info(f"📝 句子包含 {len(words)} 个词")
                            for word_data in words:
                                word_timestamps.append(WordTimestamp(
                                    text=word_data.get('text', ''),
                                    start_time=word_data.get('begin_time', 0) / 1000,  # 转换为秒
                                    end_time=word_data.get('end_time', 0) / 1000,
                                    confidence=word_data.get('confidence', 1.0)
                                ))
                    
                    # 如果sentences为空，尝试直接从transcript获取words
                    if not sentences:
                        words = transcript.get('words', [])
                        if words:
                            logger.info(f"📝 转录直接包含 {len(words)} 个词")
                            for word_data in words:
                                word_timestamps.append(WordTimestamp(
                                    text=word_data.get('text', ''),
                                    start_time=word_data.get('begin_time', 0) / 1000,
                                    end_time=word_data.get('end_time', 0) / 1000,
                                    confidence=word_data.get('confidence', 1.0)
                                ))
                
                if word_timestamps:
                    logger.info(f"✅ transcripts方法成功: 提取到 {len(word_timestamps)} 个词")
                    return word_timestamps
            
            # 方法2: 查找sentences -> words结构
            sentences = transcription_data.get('sentences', [])
            if sentences:
                logger.info(f"📝 找到 {len(sentences)} 个句子，解析词级信息...")
                for sentence in sentences:
                    words = sentence.get('words', [])
                    for word_data in words:
                        word_timestamps.append(WordTimestamp(
                            text=word_data.get('text', ''),
                            start_time=word_data.get('begin_time', 0) / 1000,  # 转换为秒
                            end_time=word_data.get('end_time', 0) / 1000,
                            confidence=word_data.get('confidence', 1.0)
                        ))
                if word_timestamps:
                    logger.info(f"✅ sentences方法成功: 提取到 {len(word_timestamps)} 个词")
                    return word_timestamps
            
            # 方法3: 直接查找words数组
            words = transcription_data.get('words', [])
            if words:
                logger.info(f"📝 找到直接words数组，包含 {len(words)} 个词...")
                for word_data in words:
                    word_timestamps.append(WordTimestamp(
                        text=word_data.get('text', ''),
                        start_time=word_data.get('begin_time', 0) / 1000,
                        end_time=word_data.get('end_time', 0) / 1000,
                        confidence=word_data.get('confidence', 1.0)
                    ))
                if word_timestamps:
                    logger.info(f"✅ 直接words方法成功: 提取到 {len(word_timestamps)} 个词")
                    return word_timestamps
            
            # 如果都失败了，打印调试信息
            logger.warning("⚠️ 未找到标准的词级时间戳结构")
            logger.info(f"🔍 转录数据样本: {str(transcription_data)[:500]}...")
            
            return []
            
        except Exception as e:
            logger.error(f"❌ 解析词级时间戳失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _analyze_with_deepseek(self, text: str) -> Optional[Dict[str, Any]]:
        """使用DeepSeek进行语义分析"""
        if not self.deepseek_api_key or self.deepseek_api_key in ['your_deepseek_api_key_here', 'placeholder']:
            raise ValueError("❌ DeepSeek API密钥未配置，无法进行语义分析")
        
        try:
            # 🎯 使用领域配置生成提示词
            prompt = self._generate_domain_analysis_prompt(text)
            
            # DeepSeek API调用 - 修复URL
            headers = {
                'Authorization': f'Bearer {self.deepseek_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': f'你是专业的{self.domain_config["domain_name"]}内容语义分析专家。请严格按照JSON格式返回分析结果。'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.1,
                'max_tokens': 2000
            }
            
            logger.info("🚀 调用DeepSeek API进行语义分析...")
            
            # 处理代理配置
            proxies = self._get_proxy_config()
            
            response = requests.post(
                'https://api.deepseek.com/chat/completions',
                headers=headers,
                json=payload,
                timeout=60,  # 增加到60秒
                proxies=proxies
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # 解析JSON结果 - 支持markdown代码块
                try:
                    analysis_result = json.loads(content)
                    analysis_result['model'] = 'deepseek-chat'
                    analysis_result['raw_response'] = content
                    logger.info("✅ DeepSeek分析成功")
                    return analysis_result
                except json.JSONDecodeError as e:
                    logger.error(f"❌ DeepSeek返回内容不是有效JSON: {e}")
                    logger.error(f"📄 原始响应: {content}")
                    
                    # 🧠 尝试智能提取markdown代码块中的JSON
                    try:
                        analysis_result = self._extract_analysis_from_text(content, 'DeepSeek')
                        logger.info("✅ DeepSeek智能提取成功")
                        return analysis_result
                    except Exception as extract_e:
                        logger.error(f"❌ DeepSeek智能提取也失败: {extract_e}")
                        raise ValueError(f"DeepSeek API返回格式错误: {e}")
            else:
                logger.error(f"❌ DeepSeek API调用失败: {response.status_code} - {response.text}")
                raise RuntimeError(f"DeepSeek API调用失败: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error("❌ DeepSeek API请求超时")
            raise TimeoutError("DeepSeek API请求超时")
        except Exception as e:
            logger.error(f"❌ DeepSeek语义分析失败: {e}")
            raise
    
    def _analyze_with_claude(self, text: str) -> Optional[Dict[str, Any]]:
        """使用Claude进行语义分析"""
        if not self.claude_api_key or self.claude_api_key in ['your_openrouter_api_key_here', 'placeholder']:
            raise ValueError("❌ Claude API密钥未配置，无法进行语义分析")
        
        try:
            # 🎯 使用领域配置生成提示词
            prompt = self._generate_domain_analysis_prompt(text)
            
            # Claude API调用 (通过OpenRouter)
            headers = {
                'Authorization': f'Bearer {self.claude_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'anthropic/claude-4-sonnet-20250522',
                'messages': [
                    {'role': 'system', 'content': f'你是专业的{self.domain_config["domain_name"]}内容语义分析专家。请严格按照JSON格式返回分析结果。'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.1,
                'max_tokens': 2000
            }
            
            logger.info("🚀 调用Claude API进行语义分析...")
            
            # 处理代理配置
            proxies = self._get_proxy_config()
            
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=60,  # 增加到60秒
                proxies=proxies
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # 解析JSON结果 - 支持markdown代码块
                try:
                    analysis_result = json.loads(content)
                    analysis_result['model'] = 'claude-4-sonnet'
                    analysis_result['raw_response'] = content
                    logger.info("✅ Claude分析成功")
                    return analysis_result
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Claude返回内容不是有效JSON: {e}")
                    logger.error(f"📄 原始响应: {content}")
                    
                    # 🧠 尝试智能提取markdown代码块中的JSON
                    try:
                        analysis_result = self._extract_analysis_from_text(content, 'Claude')
                        logger.info("✅ Claude智能提取成功")
                        return analysis_result
                    except Exception as extract_e:
                        logger.error(f"❌ Claude智能提取也失败: {extract_e}")
                        raise ValueError(f"Claude API返回格式错误: {e}")
            else:
                logger.error(f"❌ Claude API调用失败: {response.status_code} - {response.text}")
                raise RuntimeError(f"Claude API调用失败: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error("❌ Claude API请求超时")
            raise TimeoutError("Claude API请求超时")
        except Exception as e:
            logger.error(f"❌ Claude语义分析失败: {e}")
            raise
    
    def _generate_domain_analysis_prompt(self, text: str) -> str:
        """基于领域配置生成分析提示词"""
        domain_name = self.domain_config["domain_name"]
        categories = self.domain_config["categories"]
        
        # 构建类别说明
        category_descriptions = []
        for category, config in categories.items():
            desc = config["description"]
            keywords = ", ".join(config["keywords"][:8])  # 只显示前8个关键词
            category_descriptions.append(f"**{category}**: {desc}\n   关键词示例: {keywords}")
        
        categories_text = "\n".join(category_descriptions)
        
        # 构建类别分布示例
        category_names = list(categories.keys())
        category_dist_example = ', '.join([f'"{cat}": 数字' for cat in category_names])
        
        return f"""🎯 请对以下{domain_name}字幕文本进行**超精细语义分割分析**（适配所有启赋产品线）。

## 📋 {domain_name}类别体系

{categories_text}

## 🎯 核心分析要求（泛化版）

1. **句子内部语义切换检测**: 
   - 仔细分析每个句子内部是否包含多个语义模块
   - 识别语义转换点，如"产品介绍→使用效果"、"使用效果→产品介绍"等
   - 不要简单按句子分割，要按语义内容分割
   - **适应性分析**: 即使遇到新的词汇表达，也要基于语义逻辑进行分类

2. **关键转换信号识别**（通用模式）:
   - 🍼→🌟: "产品/成分/营养/配方" + "效果/发育/健康/能力提升"
   - 🌟→🍼: "效果/发育/健康" + "成分/营养/产品特点"  
   - 🪝→🍼: "问题/困扰/需求" + "品牌/产品/解决方案"
   - 🌟→🎁: "效果/满意" + "优惠/活动/购买"
   - 🍼→🎁: "产品介绍" + "价格/优惠/购买"

3. **精细边界定位**: 
   - 每个片段应该语义纯净，属于单一类别
   - 如果一句话包含多个语义，必须拆分成多个片段
   - 提供精确的词索引边界
   - **新内容适应**: 对于未知词汇，基于上下文语义进行分类

4. **启赋产品线自适应**:
   - 启赋蕴醇: 重点关注HMO、OPN、α-乳清蛋白等高端成分
   - 启赋水奶: 重点关注便携、新鲜、即开即饮等特点
   - 启赋有机: 重点关注有机认证、天然纯净等特点
   - 通用特征: 惠氏品牌、科学配方、营养全面等

## 📝 分析示例

对于文本："惠氏启赋蕴醇营养丰富含HMO，宝宝自愈力直接开挂，再加上瑞士A2奶源更好吸收，现在限时优惠"
应该分析为：
- 片段1: "惠氏启赋蕴醇营养丰富含HMO" → 🍼 产品介绍
- 片段2: "宝宝自愈力直接开挂" → 🌟 使用效果  
- 片段3: "再加上瑞士A2奶源更好吸收" → 🍼 产品介绍
- 片段4: "现在限时优惠" → 🎁 促销机制

## 📝 输出格式

请严格按照以下JSON格式输出，不要添加任何解释文字：

```json
{{
    "semantic_segments": [
        {{
            "text": "语义片段文本",
            "category": "类别标签",
            "confidence": 0.85,
            "start_word_index": 0,
            "end_word_index": 15,
            "reasoning": "分类依据和转换点分析（如有新词汇请说明推理过程）"
        }}
    ],
    "analysis_summary": {{
        "total_segments": 数字,
        "category_distribution": {{{category_dist_example}}},
        "overall_confidence": 0.85
    }}
}}
```

## 📝 待分析文本：

{text}

**请进行超精细分割，适应各种启赋产品内容，识别所有语义转换点：**"""

    def _classify_sentence_by_keywords(self, sentence: str) -> str:
        """基于关键词分类句子（增强泛化版）"""
        
        # 🪝 钩子关键词（扩展版）
        hook_keywords = ["哭闹", "夜醒", "睡不好", "不安", "困扰", "担心", "焦虑", "问题", "薄弱期", "消耗光", "妈妈不知道", "90%", "你家宝宝", "频繁", "原来", "研究发现", "专家说", "科学证明", "发现", "调查", "统计", "数据"]
        
        # 🍼 产品介绍关键词（扩展版）
        product_keywords = ["惠氏", "启赋", "蕴醇", "蕴淳", "水奶", "有机", "奶粉", "配方", "营养", "成分", "母乳", "低聚糖", "蛋白", "A2", "奶源", "HMO", "OPN", "2'-FL", "α-乳清蛋白", "DHA", "ARA", "益生菌", "核苷酸", "叶黄素", "胆碱", "牛磺酸", "铁", "锌", "钙", "维生素", "亲和", "天然", "纯净", "原装进口", "瑞士", "爱尔兰", "品牌", "科技", "创新", "专利"]
        
        # 🌟 使用效果关键词（扩展版）
        effect_keywords = ["自愈力", "开挂", "平稳", "度过", "更好", "吸收", "健康", "活泼", "效果", "改善", "直接", "能让", "好吸收", "平稳度过", "保护力", "抵抗力", "免疫力", "聪明", "智力", "发育", "成长", "强壮", "消化好", "不上火", "不便秘", "睡得香", "长得快", "聪明伶俐", "反应快", "记忆力", "学习能力"]
        
        # 🎁 促销机制关键词（扩展版）
        promotion_keywords = ["限时", "专享", "试喝", "大促", "囤", "优惠", "活动", "福利", "折扣", "满减", "买赠", "礼盒", "试用装", "新客", "会员", "积分", "返现", "包邮", "客服", "咨询", "保障", "正品", "授权", "官方", "购买", "下单", "立即", "马上", "现在", "价格"]
        
        sentence_lower = sentence.lower()
        
        # 统计各类关键词出现次数
        hook_count = sum(1 for kw in hook_keywords if kw in sentence)
        product_count = sum(1 for kw in product_keywords if kw in sentence)
        effect_count = sum(1 for kw in effect_keywords if kw in sentence)
        promotion_count = sum(1 for kw in promotion_keywords if kw in sentence)
        
        # 选择得分最高的类别
        scores = {
            "🪝 钩子": hook_count,
            "🍼 产品介绍": product_count,
            "🌟 使用效果": effect_count,
            "🎁 促销机制": promotion_count
        }
        
        max_category = max(scores, key=scores.get)
        
        # 如果没有明显关键词，根据位置推断
        if scores[max_category] == 0:
            if "90%" in sentence or "妈妈不知道" in sentence:
                return "🪝 钩子"
            elif "惠氏" in sentence or "奶粉" in sentence:
                return "🍼 产品介绍"
            elif "限时" in sentence or "试喝" in sentence:
                return "🎁 促销机制"
            else:
                return "🍼 产品介绍"  # 默认
        
        return max_category
    
    def _split_by_semantic_keywords(self, text: str) -> List[Dict[str, Any]]:
        """基于领域配置的语义关键词智能分割文本"""
        segments = []
        
        # 🎯 从领域配置获取语义边界
        semantic_boundaries = self.domain_config.get("semantic_boundaries", [])
        categories = self.domain_config.get("categories", {})
        
        import re
        
        # 查找所有语义边界点
        boundary_points = []
        for boundary in semantic_boundaries:
            matches = re.finditer(boundary['pattern'], text, re.IGNORECASE)
            for match in matches:
                boundary_points.append({
                    'position': match.start(),
                    'match_text': match.group(),
                    'from_category': boundary['from_category'],
                    'to_category': boundary['to_category'],
                    'description': boundary.get('description', '')
                })
        
        # 按位置排序边界点
        boundary_points.sort(key=lambda x: x['position'])
        
        # 基于边界点分割文本
        current_pos = 0
        # 默认开始类别为第一个定义的类别
        current_category = list(categories.keys())[0] if categories else '未分类'
        
        for i, boundary in enumerate(boundary_points):
            # 添加边界前的片段
            if boundary['position'] > current_pos:
                segment_text = text[current_pos:boundary['position']].strip()
                if segment_text:
                    segments.append({
                        'text': segment_text,
                        'category': current_category,
                        'confidence': 0.88,
                        'start_word_index': self._text_to_word_index(text, current_pos),
                        'end_word_index': self._text_to_word_index(text, boundary['position']),
                        'reasoning': f'基于语义边界识别为{current_category}: {boundary.get("description", "")}'
                    })
            
            # 更新当前类别
            current_category = boundary['to_category']
            current_pos = boundary['position']
        
        # 添加最后一个片段
        if current_pos < len(text):
            segment_text = text[current_pos:].strip()
            if segment_text:
                segments.append({
                    'text': segment_text,
                    'category': current_category,
                    'confidence': 0.86,
                    'start_word_index': self._text_to_word_index(text, current_pos),
                    'end_word_index': self._text_to_word_index(text, len(text)),
                    'reasoning': f'最终片段识别为{current_category}'
                })
        
        # 如果没有找到明确的边界，使用关键词密度分析
        if not segments:
            segments = self._analyze_by_keyword_density(text)
        
        logger.info(f"🎯 基于{self.domain_config['domain_name']}配置的语义分割完成：{len(segments)}个片段")
        return segments
    
    def _analyze_by_keyword_density(self, text: str) -> List[Dict[str, Any]]:
        """基于领域配置的关键词密度分析进行分割"""
        categories = self.domain_config.get("categories", {})
        
        # 计算每个类别的总权重
        category_scores = {}
        for category, config in categories.items():
            score = 0
            keywords = config.get("keywords", [])
            weight_multiplier = config.get("weight_multiplier", 1.0)
            
            for keyword in keywords:
                count = text.count(keyword)
                score += count * weight_multiplier
            
            category_scores[category] = score
        
        # 选择得分最高的类别
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            best_score = category_scores[best_category]
        else:
            best_category = "未分类"
            best_score = 0
        
        # 创建单个片段
        return [{
            'text': text,
            'category': best_category,
            'confidence': 0.82,
            'start_word_index': 0,
            'end_word_index': len(text),
            'reasoning': f'基于{self.domain_config["domain_name"]}关键词密度分析识别为{best_category}（得分: {best_score}）'
        }]
    
    def _text_to_word_index(self, full_text: str, char_pos: int) -> int:
        """将字符位置转换为词索引（简化版）"""
        # 简单地假设每2个字符为一个词
        return max(0, char_pos // 2)
    
    def _count_categories(self, segments: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计各类别的片段数量"""
        counts = {}
        for segment in segments:
            category = segment.get('category', '🍼 产品介绍')
            counts[category] = counts.get(category, 0) + 1
        return counts
    

    
    def _extract_analysis_from_text(self, content: str, model: str) -> Dict[str, Any]:
        """从文本中智能提取分析结果（增强版备用方案）"""
        logger.info(f"🧠 使用智能提取模式解析{model}响应...")
        
        # 输出完整响应内容用于调试
        logger.info(f"📄 {model}完整响应内容:")
        logger.info(f"   {content}")
        
        # 尝试多种JSON提取方法
        analysis_result = None
        
        # 方法1: 寻找JSON代码块
        import re
        json_pattern = r'```json\s*(.*?)\s*```'
        json_match = re.search(json_pattern, content, re.DOTALL)
        if json_match:
            try:
                analysis_result = json.loads(json_match.group(1))
                logger.info("✅ 方法1成功：从```json```代码块提取")
            except json.JSONDecodeError:
                logger.warning("⚠️ 方法1失败：JSON代码块格式错误")
        
        # 方法2: 寻找大括号包围的内容
        if not analysis_result:
            bracket_pattern = r'\{.*\}'
            bracket_match = re.search(bracket_pattern, content, re.DOTALL)
            if bracket_match:
                try:
                    analysis_result = json.loads(bracket_match.group(0))
                    logger.info("✅ 方法2成功：从大括号内容提取")
                except json.JSONDecodeError:
                    logger.warning("⚠️ 方法2失败：大括号内容不是有效JSON")
        
        # 方法3: 关键信息提取（基于文本分析）
        if not analysis_result:
            logger.info("🎯 方法3：基于关键词智能分析响应内容")
            analysis_result = self._intelligent_text_analysis(content, model)
        
        # 如果所有方法都失败，直接抛出错误
        if not analysis_result or not analysis_result.get('semantic_segments'):
            raise ValueError(f"❌ {model}响应解析失败：无法提取有效的语义分析结果")
        
        # 补充模型信息
        analysis_result['model'] = model
        analysis_result['raw_response'] = content
        analysis_result['extraction_method'] = 'intelligent_extraction'
        
        logger.info(f"✅ {model}智能提取成功，获得{len(analysis_result.get('semantic_segments', []))}个片段")
        return analysis_result
    
    def _intelligent_text_analysis(self, content: str, model: str) -> Dict[str, Any]:
        """基于AI响应内容进行智能分析"""
        # 查找类别相关的关键词
        category_indicators = {
            '🪝 钩子': ['钩子', '困扰', '问题', '薄弱期', '夜醒', '哭闹', '不安'],
            '🍼 产品介绍': ['产品', '介绍', '惠氏', '启赋', '配方', '成分', '营养', '母乳', '低聚糖'],
            '🌟 使用效果': ['效果', '自愈力', '开挂', '平稳', '度过', '改善', '健康', '吸收'],
            '🎁 促销机制': ['促销', '限时', '专享', '试喝', '大促', '囤', '优惠', '活动']
        }
        
        # 分析响应中提到的类别
        detected_segments = []
        segment_id = 0
        
        # 按段落分析
        paragraphs = content.split('\n')
        current_text = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 检查是否包含类别指示器
            detected_category = None
            max_score = 0
            
            for category, keywords in category_indicators.items():
                score = sum(1 for keyword in keywords if keyword in paragraph)
                if score > max_score:
                    max_score = score
                    detected_category = category
            
            # 如果检测到类别或积累了足够的文本，创建片段
            if detected_category or len(current_text) > 50:
                if current_text.strip():
                    final_category = detected_category or '🍼 产品介绍'
                    detected_segments.append({
                        'text': current_text.strip(),
                        'category': final_category,
                        'confidence': 0.78,
                        'start_word_index': segment_id * 30,
                        'end_word_index': (segment_id + 1) * 30,
                        'reasoning': f'AI{model}智能分析识别为{final_category}'
                    })
                    segment_id += 1
                
                current_text = paragraph if detected_category else ""
            else:
                current_text += paragraph + " "
        
        # 处理最后一个片段
        if current_text.strip():
            detected_segments.append({
                'text': current_text.strip(),
                'category': '🍼 产品介绍',
                'confidence': 0.75,
                'start_word_index': segment_id * 30,
                'end_word_index': (segment_id + 1) * 30,
                'reasoning': f'AI{model}智能分析最终片段'
            })
        
        # 如果没有检测到有意义的片段，返回空结果
        if not detected_segments:
            return {}
        
        # 构建分析结果
        category_distribution = {}
        for segment in detected_segments:
            category = segment['category']
            category_distribution[category] = category_distribution.get(category, 0) + 1
        
        return {
            'semantic_segments': detected_segments,
            'analysis_summary': {
                'total_segments': len(detected_segments),
                'category_distribution': category_distribution,
                'overall_confidence': 0.77
            }
        }
    

    

    
    def _create_semantic_segments(self, word_timestamps: List[WordTimestamp], analysis: Dict[str, Any]) -> List[SemanticSegment]:
        """基于语义分析结果创建语义片段（修复时间戳重叠问题）"""
        semantic_segments = []
        
        try:
            if not analysis or not analysis.get('semantic_segments'):
                raise ValueError("❌ AI语义分析结果为空，无法创建语义片段")
            
            segment_id = 1
            last_end_time = 0.0  # 追踪上一个片段的结束时间，避免重叠
            
            for segment_data in analysis['semantic_segments']:
                start_idx = segment_data.get('start_word_index', 0)
                end_idx = segment_data.get('end_word_index', len(word_timestamps) - 1)
                
                # 确保索引有效
                start_idx = max(0, min(start_idx, len(word_timestamps) - 1))
                end_idx = max(start_idx, min(end_idx, len(word_timestamps) - 1))
                
                segment_words = word_timestamps[start_idx:end_idx + 1]
                if not segment_words:
                    continue
                
                # 🔧 修复时间戳重叠问题
                start_time = segment_words[0].start_time
                end_time = segment_words[-1].end_time
                
                # 确保不与前一个片段重叠
                if start_time < last_end_time:
                    start_time = last_end_time  # 调整开始时间到前一个片段结束时间
                
                # 确保片段至少有0.1秒的最小长度
                if end_time <= start_time:
                    end_time = start_time + 0.1
                
                semantic_segments.append(SemanticSegment(
                    id=segment_id,
                    start_time=start_time,
                    end_time=end_time,
                    text=segment_data.get('text', ''),
                    semantic_label=segment_data.get('category', '未分类'),
                    confidence=segment_data.get('confidence', 0.5),
                    words=segment_words
                ))
                
                last_end_time = end_time  # 更新最后结束时间
                segment_id += 1
            
            # 🔧 后处理：进一步优化时间戳边界
            semantic_segments = self._optimize_segment_boundaries(semantic_segments)
            
            return semantic_segments
            
        except Exception as e:
            logger.error(f"❌ 创建语义片段失败: {e}")
            raise
    
    def _optimize_segment_boundaries(self, segments: List[SemanticSegment]) -> List[SemanticSegment]:
        """优化语义片段边界，消除重叠和缝隙"""
        if len(segments) <= 1:
            return segments
        
        optimized_segments = []
        
        for i, segment in enumerate(segments):
            # 复制当前片段
            new_segment = SemanticSegment(
                id=segment.id,
                start_time=segment.start_time,
                end_time=segment.end_time,
                text=segment.text,
                semantic_label=segment.semantic_label,
                confidence=segment.confidence,
                words=segment.words
            )
            
            # 如果不是第一个片段，确保与前一个片段无缝连接
            if i > 0:
                prev_segment = optimized_segments[-1]
                
                # 消除重叠：当前片段开始时间不能早于前一个片段结束时间
                if new_segment.start_time < prev_segment.end_time:
                    new_segment.start_time = prev_segment.end_time
                
                # 消除过大缝隙：如果间隔大于0.5秒，调整边界
                gap = new_segment.start_time - prev_segment.end_time
                if gap > 0.5:
                    # 将缝隙平均分配给两个片段
                    middle_time = prev_segment.end_time + gap / 2
                    prev_segment.end_time = middle_time
                    new_segment.start_time = middle_time
                    # 更新已添加的前一个片段
                    optimized_segments[-1] = prev_segment
            
            # 确保片段最小长度
            if new_segment.end_time <= new_segment.start_time:
                new_segment.end_time = new_segment.start_time + 0.1
            
            optimized_segments.append(new_segment)
        
        logger.info(f"🔧 边界优化完成：{len(optimized_segments)}个片段无重叠")
        return optimized_segments
    
    def _create_default_segments(self, word_timestamps: List[WordTimestamp]) -> List[SemanticSegment]:
        """创建默认的语义片段（备用方案）"""
        # 简单的基于时间长度的分割
        segments = []
        segment_duration = 5.0  # 5秒一个片段
        
        current_words = []
        current_start = 0
        segment_id = 1
        
        for word in word_timestamps:
            if not current_words:
                current_start = word.start_time
            
            current_words.append(word)
            
            # 检查是否需要分割
            if word.end_time - current_start >= segment_duration:
                text = ''.join([w.text for w in current_words])
                segments.append(SemanticSegment(
                    id=segment_id,
                    start_time=current_start,
                    end_time=word.end_time,
                    text=text,
                    semantic_label='🍼 产品介绍',  # 默认标签
                    confidence=0.5,
                    words=current_words.copy()
                ))
                
                current_words = []
                segment_id += 1
        
        # 处理最后一个片段
        if current_words:
            text = ''.join([w.text for w in current_words])
            segments.append(SemanticSegment(
                id=segment_id,
                start_time=current_start,
                end_time=current_words[-1].end_time,
                text=text,
                semantic_label='🍼 产品介绍',
                confidence=0.5,
                words=current_words
            ))
        
        return segments
    

    
    def export_to_srt(self, semantic_segments: List[SemanticSegment], output_path: str) -> bool:
        """导出语义片段为SRT文件"""
        try:
            srt_lines = []
            
            for segment in semantic_segments:
                # SRT格式：编号
                srt_lines.append(str(segment.id))
                
                # SRT格式：时间戳
                start_time = self._seconds_to_srt_time(segment.start_time)
                end_time = self._seconds_to_srt_time(segment.end_time)
                srt_lines.append(f"{start_time} --> {end_time}")
                
                # SRT格式：文本内容（包含语义标签）
                labeled_text = f"[{segment.semantic_label}] {segment.text}"
                srt_lines.append(labeled_text)
                
                # SRT格式：空行分隔符
                srt_lines.append("")
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(srt_lines))
            
            logger.info(f"✅ 语义SRT文件导出成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导出SRT文件失败: {e}")
            return False
    
    def export_to_srt_dual_versions(self, semantic_segments: List[SemanticSegment], output_path: str) -> bool:
        """导出语义片段为双版本SRT文件：带标注版本和干净版本"""
        try:
            from pathlib import Path
            
            output_path_obj = Path(output_path)
            
            # 生成两个文件路径
            labeled_path = output_path  # 带标注版本使用原路径
            clean_path = output_path_obj.parent / f"{output_path_obj.stem}_clean{output_path_obj.suffix}"
            
            # --- 生成带标注版本 ---
            labeled_srt_lines = []
            for segment in semantic_segments:
                # SRT格式：编号
                labeled_srt_lines.append(str(segment.id))
                
                # SRT格式：时间戳
                start_time = self._seconds_to_srt_time(segment.start_time)
                end_time = self._seconds_to_srt_time(segment.end_time)
                labeled_srt_lines.append(f"{start_time} --> {end_time}")
                
                # SRT格式：文本内容（包含语义标签）
                labeled_text = f"[{segment.semantic_label}] {segment.text}"
                labeled_srt_lines.append(labeled_text)
                
                # SRT格式：空行分隔符
                labeled_srt_lines.append("")
            
            # --- 生成干净版本 ---
            clean_srt_lines = []
            for segment in semantic_segments:
                # SRT格式：编号
                clean_srt_lines.append(str(segment.id))
                
                # SRT格式：时间戳
                start_time = self._seconds_to_srt_time(segment.start_time)
                end_time = self._seconds_to_srt_time(segment.end_time)
                clean_srt_lines.append(f"{start_time} --> {end_time}")
                
                # SRT格式：文本内容（不包含语义标签）
                clean_text = segment.text
                clean_srt_lines.append(clean_text)
                
                # SRT格式：空行分隔符
                clean_srt_lines.append("")
            
            # --- 写入带标注版本文件 ---
            with open(labeled_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(labeled_srt_lines))
            
            # --- 写入干净版本文件 ---
            with open(clean_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(clean_srt_lines))
            
            logger.info(f"✅ 带标注版本SRT文件导出成功: {labeled_path}")
            logger.info(f"✅ 干净版本SRT文件导出成功: {clean_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导出双版本SRT文件失败: {e}")
            return False
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """将秒数转换为SRT时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="词级语义分割器")
    parser.add_argument("srt_file", help="输入SRT文件路径")
    parser.add_argument("-o", "--output", help="输出SRT文件路径")
    parser.add_argument("--deepseek-key", help="DeepSeek API密钥")
    parser.add_argument("--claude-key", help="Claude API密钥")
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    splitter = WordLevelSemanticSplitter(
        deepseek_api_key=args.deepseek_key,
        claude_api_key=args.claude_key
    )
    
    # 分析SRT文件
    segments = splitter.analyze_srt_with_word_timestamps(args.srt_file)
    
    if segments:
        output_path = args.output or args.srt_file.replace('.srt', '_semantic.srt')
        success = splitter.export_to_srt(segments, output_path)
        
        if success:
            print(f"✅ 语义分割完成！输出文件: {output_path}")
        else:
            print("❌ 导出失败！")
            return 1
    else:
        print("❌ 语义分析失败！")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main()) 