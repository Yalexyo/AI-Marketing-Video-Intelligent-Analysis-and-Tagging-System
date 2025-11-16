#!/usr/bin/env python3
"""
DeepSeek AI分析器 - SRT转产品介绍视频
使用DeepSeek API分析SRT内容，识别产品介绍相关片段
"""

import json
import logging
import time
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from .srt_parser import SRTSegment
    from .env_loader import (
        get_deepseek_api_key, get_deepseek_base_url, get_deepseek_model,
        get_max_tokens, get_temperature, get_product_keywords, get_brand_keywords,
        get_min_segment_duration, get_max_segment_duration
    )
except ImportError:
    from srt_parser import SRTSegment
    from env_loader import (
        get_deepseek_api_key, get_deepseek_base_url, get_deepseek_model,
        get_max_tokens, get_temperature, get_product_keywords, get_brand_keywords,
        get_min_segment_duration, get_max_segment_duration
    )

logger = logging.getLogger(__name__)

class ProductSegment:
    """代表一个产品介绍片段"""
    def __init__(self, topic: str, sequence_ids: List[int], summary: str,
                 keywords: List[str], logic_pattern: str, confidence: float,
                 start_time: float = 0.0, end_time: float = 0.0,
                 scene_type: str = "未分类"):
        self.topic = topic
        self.sequence_ids = sequence_ids
        self.summary = summary
        self.keywords = keywords
        self.logic_pattern = logic_pattern
        self.confidence = confidence
        self.start_time = start_time
        self.end_time = end_time
        self.duration = end_time - start_time if end_time > start_time else 0
        self.scene_type = scene_type # 可选的旧字段

class DeepSeekAnalyzer:
    """DeepSeek AI分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化DeepSeek分析器
        
        Args:
            api_key: DeepSeek API密钥，如果为None则从环境变量获取
        """
        self.api_key = api_key or get_deepseek_api_key()
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未设置")
        
        # 初始化OpenAI客户端 (DeepSeek兼容OpenAI接口)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=get_deepseek_base_url(),
            timeout=30.0  # 添加30秒超时
        )
        
        self.model = get_deepseek_model()
        self.max_tokens = get_max_tokens()
        self.temperature = get_temperature()
        self.product_keywords = get_product_keywords()
        self.brand_keywords = get_brand_keywords()
        self.min_duration = get_min_segment_duration()
        self.max_duration = get_max_segment_duration()
        
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"DeepSeek分析器初始化完成")
        self.logger.info(f"模型: {self.model}, 最大tokens: {self.max_tokens}")
        self.logger.info(f"产品关键词: {len(self.product_keywords)}个")
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=3))
    def analyze_srt_content(self, segments: List[SRTSegment], 
                           filename: str = "unknown") -> List[ProductSegment]:
        """
        分析SRT内容，识别产品介绍片段
        
        Args:
            segments: SRT片段列表
            filename: 文件名（用于上下文）
            
        Returns:
            产品介绍片段列表
        """
        if not segments:
            self.logger.warning("SRT片段为空，无法分析")
            return []
        
        try:
            # 准备分析内容
            content_with_timestamps = self._prepare_content(segments)
            
            # 优先使用精简版prompt提高速度
            prompt = self._build_analysis_prompt_optimized(content_with_timestamps, filename)
            
            # 调用DeepSeek API
            response = self._call_deepseek_api(prompt)
            
            # 解析AI响应
            product_segments = self._parse_ai_response(response, segments)
            
            self.logger.info(f"AI分析完成，识别到{len(product_segments)}个产品介绍片段")
            return product_segments
            
        except Exception as e:
            self.logger.error(f"DeepSeek分析失败: {e}")
            # 🚫 禁用备用分析，避免产生低质量的额外主题
            self.logger.warning("为确保质量，不使用备用分析方案")
            return []
    
    def _prepare_content(self, segments: List[SRTSegment]) -> str:
        """准备分析内容 - 使用序列号格式与prompt保持一致"""
        content_parts = []
        
        for segment in segments:
            # 使用序列号格式 [1], [2] 而不是时间戳格式 [00:34]
            content_parts.append(f"[{segment.index}] {segment.text}")
        
        return '\n'.join(content_parts)
    
    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _build_analysis_prompt_optimized(self, content: str, filename: str) -> str:
        """构建AI分析提示（Token优化版）- 专注三大产品品类"""
        
        prompt = f"""你是产品介绍分析师，从字幕中识别**启赋奶粉产品介绍**内容。

## 🎯 核心任务
只识别以下三大产品品类的产品介绍内容：
1. **启赋蕴淳** - 核心奶粉产品
2. **启赋水奶** - 便携装产品  
3. **启赋蓝钻** - 高端系列产品

## 📋 产品介绍识别标准

### 必须包含的产品介绍要素
- **成分配方**：母乳低聚糖HMO、A2奶源、活性蛋白、OPN、DHA等
- **核心卖点**：营养成分、配方优势、品牌背景、科研实力
- **产品方案**：具体产品名称、使用场景、产品特性

### 排除的非产品介绍内容
❌ 育儿痛点/困惑（转奶问题、育儿焦虑等）
❌ 育儿成果/体验（宝宝表现、体质基础等）  
❌ 生活日常（早餐、家长会、玩耍等）
❌ 纯科普内容（不涉及具体产品的营养知识）

### 产品关键词识别
- **启赋蕴淳**：启赋蕴淇/蕴醇、特色配方、HMO、核心成分、惠氏背景
- **启赋水奶**：水奶、便携、A2奶源、小瓶装、携带方便
- **启赋蓝钻**：蓝钻、高端、升级配方（如出现）

### ⚠️ 段落内产品切换检测
如果一个段落内包含多个产品的介绍，需要：
1. **识别切换点**：找到从一个产品转向另一个产品的具体位置
2. **精确时间标注**：使用 `time_offset_seconds` 标注切换时间点
3. **分别归类**：将同一段落的不同部分归类到不同产品

### 时间偏移示例
```json
{{
  "topic": "启赋水奶 - 便携产品介绍",
  "sequence_ids": [14],
  "time_offset_seconds": 5.0,
  "summary": "从句子中间开始的水奶便携性介绍",
  "keywords": ["水奶", "便携", "小瓶装"]
}}
```

## 示例输出
```json
{{
  "product_mentions": [
    {{
      "topic": "启赋蕴淳 - 核心配方介绍",
      "sequence_ids": [8, 9, 10, 11, 12],
      "summary": "特色配方科普→HMO核心成分→品牌选择→惠氏科研实力，完整产品介绍",
      "keywords": ["特色配方", "HMO", "启赋蕴淳", "惠氏", "科研实力"],
      "logic_pattern": "产品介绍型",
      "confidence": 0.95
    }},
    {{
      "topic": "启赋水奶 - 便携产品介绍", 
      "sequence_ids": [14],
      "time_offset_seconds": 5.0,
      "summary": "水奶便携性→使用场景，产品特性说明（从段落中间开始）",
      "keywords": ["水奶", "便携", "小瓶装"],
      "logic_pattern": "产品介绍型",
      "confidence": 0.90
    }}
  ]
}}
```

## 分析内容
**文件**: {filename}
**字幕**: 
{content}

**输出JSON**:
```json
```"""
        return prompt
    
    def _build_analysis_prompt(self, content: str, filename: str) -> str:
        """构建AI分析prompt - 专注三大产品品类"""
        prompt = f"""你是产品介绍分析师，从字幕中识别**启赋奶粉产品介绍**内容。

## 🎯 核心任务
只识别以下三大产品品类的产品介绍内容：
1. **启赋蕴淳** - 核心奶粉产品  
2. **启赋水奶** - 便携装产品
3. **启赋蓝钻** - 高端系列产品

## 📋 产品介绍识别标准

### 必须包含的产品介绍要素
- **成分配方**：母乳低聚糖HMO、A2奶源、活性蛋白、OPN、DHA等核心成分介绍
- **核心卖点**：营养优势、配方特色、品牌背景、科研实力、安全保障
- **产品方案**：具体产品名称、使用场景、产品特性、功能说明

### 严格排除的非产品介绍内容
❌ **育儿痛点/困惑**：转奶问题、育儿焦虑、喂养困扰等
❌ **育儿成果/体验**：宝宝表现、体质基础、成长效果等
❌ **生活日常场景**：早餐制作、家长会、户外玩耍等
❌ **纯科普教育**：不涉及具体产品的营养知识普及

### 产品关键词精准识别
- **启赋蕴淳相关**：启赋蕴淇/蕴醇、特色配方、HMO、核心成分、惠氏背景、科研实力
- **启赋水奶相关**：水奶、便携装、A2奶源、小瓶装、携带方便、同品牌
- **启赋蓝钻相关**：蓝钻、高端系列、升级配方（如出现）

### 序列号选择原则
- **时长控制**：10-40秒理想范围，确保产品介绍完整
- **边界识别**：从产品提及开始，到产品介绍逻辑结束
- **逻辑完整**：包含完整的产品介绍要素链条

## 📘 精准识别示例

**文件名**: video_1_full.srt
**产品介绍片段识别**:
```
[8] 其实关键就是特色配方...选奶就看核心成分就行。   ← 产品介绍开始
[9] 而母乳低聚糖hm...能帮宝宝延续天然营养...     ← HMO核心成分
[10] 选hm奶粉，我也认真对比不少品牌，发现启赋蕴醇更适合妮妮。← 产品选择
[11] 奶粉是宝宝入口的东西...我会比较关心品牌背景。  ← 品牌重要性
[12] 启赋背靠惠氏制药公司...更有科研实力。        ← 品牌背景介绍
[14] 我和爸爸都肠胃不太好...水奶，小小一瓶，携带很方便...← 水奶产品介绍
```

**应该识别**:
- **启赋蕴淳产品介绍**: [8,9,10,11,12] - 完整产品介绍逻辑链
- **启赋水奶产品介绍**: [14] - 水奶产品特性介绍

**应该排除**:
- **育儿体验**: [3] "妮妮被养的很好" - 非产品介绍
- **育儿困惑**: [4,5] "转奶生病+专家建议" - 非产品介绍  
- **生活场景**: [16,17,18] "幼儿园+喝奶场景" - 非产品介绍

**AI应该输出**:
```json
{{
  "product_mentions": [
    {{
      "topic": "启赋蕴淳 - 核心配方介绍",
      "sequence_ids": [8, 9, 10, 11, 12],
      "summary": "特色配方科普→HMO核心成分→品牌对比选择→安全重要性→惠氏科研背景，完整产品介绍逻辑",
      "keywords": ["特色配方", "HMO", "启赋蕴淳", "惠氏", "科研实力"],
      "logic_pattern": "产品介绍型",
      "confidence": 0.95
    }},
    {{
      "topic": "启赋水奶 - 便携产品介绍",
      "sequence_ids": [14],
      "summary": "A2奶源特性→水奶便携性→使用场景，产品特色说明",
      "keywords": ["A2奶源", "水奶", "便携", "小瓶装"],
      "logic_pattern": "产品介绍型",
      "confidence": 0.90
    }}
  ]
}}
```

## 🎯 你的任务
分析以下字幕内容，**严格按照产品介绍标准**，只识别三大产品品类的纯产品介绍内容。

**文件名**: {filename}
**字幕内容**:
{content}

**输出JSON**:
```json
```"""
        return prompt
    
    def _call_deepseek_api(self, prompt: str) -> str:
        """调用DeepSeek API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"DeepSeek API调用失败: {e}")
            raise
    
    def _parse_ai_response(self, response: str, segments: List[SRTSegment]) -> List[ProductSegment]:
        """解析AI响应"""
        try:
            # 清理响应内容，只保留JSON部分
            response = response.strip()
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                response = response.split('```')[1].split('```')[0]
            
            data = json.loads(response)
            product_mentions = []
            
            for item in data.get('product_mentions', []):
                topic = item.get('topic', '未定义主题')
                sequence_ids = item.get('sequence_ids', [])
                summary = item.get('summary', '')
                keywords = item.get('keywords', [])
                logic_pattern = item.get('logic_pattern', '其他')
                confidence = float(item.get('confidence', 0.0))
                time_offset_seconds = float(item.get('time_offset_seconds', 0.0))
                
                if not sequence_ids:
                    self.logger.warning(f"跳过无效数据（缺少sequence_ids）: {item}")
                    continue
                
                # 从序号计算精确时间，支持时间偏移
                start_time, end_time = self._get_time_from_sequence(sequence_ids, segments, time_offset_seconds)
                
                product_mention = ProductSegment(
                    topic=topic,
                    sequence_ids=sequence_ids,
                    summary=summary,
                    keywords=keywords,
                    logic_pattern=logic_pattern,
                    confidence=confidence,
                    start_time=start_time,
                    end_time=end_time
                )
                product_mentions.append(product_mention)
                
                if time_offset_seconds > 0:
                    self.logger.debug(f"成功解析主题: '{topic}'，序号: {sequence_ids}，时间偏移: {time_offset_seconds}s")
                else:
                    self.logger.debug(f"成功解析主题: '{topic}'，序号: {sequence_ids}")

            # 按置信度排序
            product_mentions.sort(key=lambda x: x.confidence, reverse=True)
            
            return product_mentions
            
        except json.JSONDecodeError as e:
            self.logger.error(f"AI响应JSON解析失败: {e}")
            self.logger.debug(f"原始响应: {response}")
            return []
        except Exception as e:
            self.logger.error(f"AI响应解析失败: {e}")
            return []
    
    def _get_time_from_sequence(self, ids: List[int], segments: List[SRTSegment], time_offset_seconds: float = 0.0) -> tuple:
        """根据字幕序号列表获取起止时间，支持时间偏移"""
        if not ids:
            return 0.0, 0.0
        
        # 将序号转换为从0开始的索引
        indices = [i - 1 for i in ids]
        
        # 验证索引范围
        valid_indices = [i for i in indices if 0 <= i < len(segments)]
        if not valid_indices:
            return 0.0, 0.0
            
        start_time = segments[min(valid_indices)].start_time
        end_time = segments[max(valid_indices)].end_time
        
        # 应用时间偏移
        if time_offset_seconds > 0:
            # 如果有时间偏移，调整开始时间
            adjusted_start = start_time + time_offset_seconds
            # 确保调整后的开始时间不超过结束时间
            if adjusted_start < end_time:
                start_time = adjusted_start
                self.logger.debug(f"应用时间偏移 {time_offset_seconds}s: {start_time:.1f}s -> {end_time:.1f}s")
            else:
                self.logger.warning(f"时间偏移 {time_offset_seconds}s 过大，跳过调整")
        
        return start_time, end_time
    
    def _map_to_precise_timestamps(self, ai_start: float, ai_end: float, 
                                 segments: List[SRTSegment]) -> tuple:
        """将AI返回的时间戳映射到精确的SRT时间戳"""
        # 找到最接近AI时间戳的SRT片段
        start_segment = None
        end_segment = None
        
        # 找到开始时间对应的片段
        for segment in segments:
            if segment.start_time <= ai_start <= segment.end_time:
                start_segment = segment
                break
        
        # 如果没找到精确匹配，找最接近的
        if start_segment is None:
            min_diff = float('inf')
            for segment in segments:
                diff = abs(segment.start_time - ai_start)
                if diff < min_diff:
                    min_diff = diff
                    start_segment = segment
        
        # 找到结束时间对应的片段
        for segment in segments:
            if segment.start_time <= ai_end <= segment.end_time:
                end_segment = segment
                break
        
        # 如果没找到精确匹配，找最接近的
        if end_segment is None:
            min_diff = float('inf')
            for segment in segments:
                diff = abs(segment.end_time - ai_end)
                if diff < min_diff:
                    min_diff = diff
                    end_segment = segment
        
        # 返回精确的SRT时间戳
        precise_start = start_segment.start_time if start_segment else ai_start
        precise_end = end_segment.end_time if end_segment else ai_end
        
        return precise_start, precise_end
    
    def _validate_time_range(self, start_time: float, end_time: float, 
                           segments: List[SRTSegment]) -> bool:
        """验证时间范围是否有效"""
        if start_time >= end_time:
            return False
        
        duration = end_time - start_time
        if duration < self.min_duration or duration > self.max_duration:
            return False
        
        # 检查时间范围是否在SRT片段范围内
        total_duration = max(seg.end_time for seg in segments)
        if start_time < 0 or end_time > total_duration:
            return False
        
        return True
    
    def _fallback_keyword_analysis(self, segments: List[SRTSegment]) -> List[ProductSegment]:
        """关键词备用分析方案"""
        self.logger.info("使用关键词备用分析方案")
        
        product_segments = []
        current_segment_start = None
        current_keywords = []
        
        for i, segment in enumerate(segments):
            # 检查是否包含产品关键词
            matched_keywords = []
            for keyword in self.product_keywords + self.brand_keywords:
                if keyword in segment.text:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                if current_segment_start is None:
                    current_segment_start = segment.start_time
                current_keywords.extend(matched_keywords)
                
                # 检查是否应该结束当前片段
                if (i == len(segments) - 1 or  # 最后一个片段
                    segment.end_time - current_segment_start >= self.max_duration):
                    
                    duration = segment.end_time - current_segment_start
                    if duration >= self.min_duration:
                        confidence = min(len(set(current_keywords)) * 0.2, 1.0)
                        
                        product_segment = ProductSegment(
                            topic="关键词匹配",
                            sequence_ids=[],
                            summary="关键词匹配",
                            keywords=list(set(current_keywords)),
                            logic_pattern="关键词匹配",
                            confidence=confidence,
                            start_time=current_segment_start,
                            end_time=segment.end_time
                        )
                        product_segments.append(product_segment)
                    
                    current_segment_start = None
                    current_keywords = []
            else:
                # 如果当前片段没有关键词，结束当前产品片段
                if current_segment_start is not None:
                    duration = segments[i-1].end_time - current_segment_start
                    if duration >= self.min_duration:
                        confidence = min(len(set(current_keywords)) * 0.2, 1.0)
                        
                        product_segment = ProductSegment(
                            topic="关键词匹配",
                            sequence_ids=[],
                            summary="关键词匹配",
                            keywords=list(set(current_keywords)),
                            logic_pattern="关键词匹配",
                            confidence=confidence,
                            start_time=current_segment_start,
                            end_time=segments[i-1].end_time
                        )
                        product_segments.append(product_segment)
                    
                    current_segment_start = None
                    current_keywords = []
        
        # 按置信度排序
        product_segments.sort(key=lambda x: x.confidence, reverse=True)
        
        self.logger.info(f"关键词分析完成，找到{len(product_segments)}个产品片段")
        return product_segments
    
    def get_best_segment(self, product_segments: List[ProductSegment]) -> Optional[ProductSegment]:
        """
        从分析出的产品片段列表中选择最佳的一个。
        在新模式下，这通常是置信度最高的片段。
        """
        if not product_segments:
            return None
        
        # 列表在解析时已按置信度排序，所以第一个就是最佳的
        return product_segments[0]
    
    def get_analysis_summary(self, product_segments: List[ProductSegment]) -> Dict:
        """获取AI分析的摘要统计"""
        if not product_segments:
            return {'total_segments': 0}
        
        # 统计逻辑模式分布
        logic_patterns = {}
        for seg in product_segments:
            pattern = seg.logic_pattern
            logic_patterns[pattern] = logic_patterns.get(pattern, 0) + 1
        
        # 统计完整性分布
        high_completeness = [seg for seg in product_segments if seg.confidence >= 0.8]
        medium_completeness = [seg for seg in product_segments if 0.5 <= seg.confidence < 0.8]
        low_completeness = [seg for seg in product_segments if seg.confidence < 0.5]
        
        return {
            'total_segments': len(product_segments),
            'best_confidence': product_segments[0].confidence,
            'best_completeness': product_segments[0].confidence, # 在新模式下，completeness由confidence体现
            'avg_confidence': sum(seg.confidence for seg in product_segments) / len(product_segments),
            'avg_completeness': sum(seg.confidence for seg in product_segments) / len(product_segments),
            'total_duration': sum(seg.duration for seg in product_segments),
            'avg_duration': sum(seg.duration for seg in product_segments) / len(product_segments),
            'unique_keywords': len(set(kw for seg in product_segments for kw in seg.keywords)),
            'logic_patterns': logic_patterns,
            'completeness_distribution': {
                'high_completeness': len(high_completeness),
                'medium_completeness': len(medium_completeness),
                'low_completeness': len(low_completeness)
            },
            'best_segment_info': {
                'topic': product_segments[0].topic,
                'logic_pattern': product_segments[0].logic_pattern,
                'scene_type': product_segments[0].scene_type,
                'duration': product_segments[0].duration,
                'keywords_count': len(product_segments[0].keywords),
                'sequence_ids': product_segments[0].sequence_ids
            }
        }
    
    def _build_keyword_screening_prompt(self, content: str, filename: str) -> str:
        """为关键词筛选构建prompt"""
        
        prompt = f"""
分析字幕，快速识别产品介绍相关片段序号。

产品关键词: {', '.join(self.product_keywords[:10])}
品牌关键词: {', '.join(self.brand_keywords[:5])}

字幕内容:
{content}

输出包含产品介绍的片段序号(如: 8,9,10,11,12):
"""
        return prompt
    
    def analyze_srt_content_layered(self, segments: List[SRTSegment], 
                                   filename: str = "unknown") -> List[ProductSegment]:
        """
        分层分析SRT内容（Token优化版）
        第一层：关键词快速筛选 (~200 tokens)
        第二层：详细AI分析筛选结果 (~800 tokens)
        总计可节省40-60% token使用
        """
        if not segments:
            self.logger.warning("SRT片段为空，无法分析")
            return []
        
        try:
            # 第一层：关键词预筛选
            self.logger.info("第一层分析：关键词预筛选...")
            
            # 创建简化的内容用于预筛选
            screening_content = self._prepare_screening_content(segments)
            screening_prompt = self._build_keyword_screening_prompt(screening_content, filename)
            
            # 调用API进行预筛选
            screening_response = self._call_deepseek_api(screening_prompt)
            
            # 解析预筛选结果
            candidate_indices = self._parse_screening_response(screening_response)
            
            if not candidate_indices:
                self.logger.warning("预筛选未找到候选片段，使用全量分析")
                return self.analyze_srt_content(segments, filename)
            
            # 第二层：详细分析候选片段
            self.logger.info(f"第二层分析：详细分析{len(candidate_indices)}个候选片段...")
            
            candidate_segments = [segments[i-1] for i in candidate_indices if 1 <= i <= len(segments)]
            
            if not candidate_segments:
                return []
            
            # 对候选片段进行详细分析
            candidate_content = self._prepare_content(candidate_segments)
            detailed_prompt = self._build_analysis_prompt_optimized(candidate_content, filename)
            
            # 调用API进行详细分析
            detailed_response = self._call_deepseek_api(detailed_prompt)
            
            # 解析详细分析结果
            product_segments = self._parse_ai_response(detailed_response, segments)
            
            self.logger.info(f"分层分析完成，识别到{len(product_segments)}个产品介绍片段")
            return product_segments
            
        except Exception as e:
            self.logger.error(f"分层分析失败: {e}")
            # 如果分层分析失败，回退到标准分析
            return self.analyze_srt_content(segments, filename)
    
    def _prepare_screening_content(self, segments: List[SRTSegment]) -> str:
        """准备预筛选内容（极简版）"""
        content_parts = []
        
        for i, segment in enumerate(segments, 1):
            # 只保留序号和文本，去除详细时间戳
            content_parts.append(f"{i}. {segment.text}")
        
        return '\n'.join(content_parts)
    
    def _parse_screening_response(self, response: str) -> List[int]:
        """解析预筛选响应，提取片段序号"""
        try:
            # 提取数字序号
            import re
            numbers = re.findall(r'\d+', response)
            return [int(n) for n in numbers if int(n) > 0]
        except Exception as e:
            self.logger.warning(f"预筛选响应解析失败: {e}")
            return [] 