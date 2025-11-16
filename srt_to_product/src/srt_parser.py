#!/usr/bin/env python3
"""
SRT解析器 - SRT转产品介绍视频
解析SRT字幕文件，提取时间戳和文本内容
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SRTSegment:
    """SRT字幕片段数据结构"""
    index: int
    start_time: float  # 开始时间(秒)
    end_time: float    # 结束时间(秒)
    text: str          # 文本内容
    duration: float    # 持续时间(秒)

class SRTParser:
    """SRT字幕解析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_srt_file(self, srt_path: Path) -> List[SRTSegment]:
        """
        解析SRT文件
        
        Args:
            srt_path: SRT文件路径
            
        Returns:
            SRT片段列表
        """
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            segments = self._parse_srt_content(content)
            
            self.logger.info(f"成功解析SRT文件: {srt_path.name}, 共{len(segments)}个片段")
            return segments
            
        except Exception as e:
            self.logger.error(f"解析SRT文件失败 {srt_path}: {e}")
            return []
    
    def _parse_srt_content(self, content: str) -> List[SRTSegment]:
        """解析SRT内容"""
        segments = []
        
        # 按空行分割片段
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            if not block.strip():
                continue
                
            segment = self._parse_srt_block(block)
            if segment:
                segments.append(segment)
        
        return segments
    
    def _parse_srt_block(self, block: str) -> Optional[SRTSegment]:
        """解析单个SRT片段"""
        lines = block.strip().split('\n')
        
        if len(lines) < 3:
            return None
        
        try:
            # 第一行：序号
            index = int(lines[0])
            
            # 第二行：时间戳
            time_line = lines[1]
            start_time, end_time = self._parse_time_line(time_line)
            
            # 第三行及以后：文本内容
            text = '\n'.join(lines[2:]).strip()
            
            # 计算持续时间
            duration = end_time - start_time
            
            return SRTSegment(
                index=index,
                start_time=start_time,
                end_time=end_time,
                text=text,
                duration=duration
            )
            
        except Exception as e:
            self.logger.warning(f"解析SRT片段失败: {e}")
            return None
    
    def _parse_time_line(self, time_line: str) -> Tuple[float, float]:
        """
        解析时间戳行
        格式: 00:00:00,000 --> 00:00:05,000
        """
        # 匹配时间戳格式
        pattern = r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})'
        match = re.match(pattern, time_line)
        
        if not match:
            raise ValueError(f"无效的时间戳格式: {time_line}")
        
        # 解析开始时间
        start_h, start_m, start_s, start_ms = map(int, match.groups()[:4])
        start_time = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
        
        # 解析结束时间
        end_h, end_m, end_s, end_ms = map(int, match.groups()[4:])
        end_time = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000
        
        return start_time, end_time
    
    def get_full_content(self, segments: List[SRTSegment]) -> str:
        """获取完整的文本内容"""
        return '\n'.join([segment.text for segment in segments])
    
    def get_content_with_timestamps(self, segments: List[SRTSegment]) -> str:
        """获取带时间戳的内容"""
        result = []
        for segment in segments:
            timestamp = self._format_timestamp(segment.start_time)
            result.append(f"[{timestamp}] {segment.text}")
        return '\n'.join(result)
    
    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为可读格式"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def filter_segments_by_duration(self, segments: List[SRTSegment], 
                                   min_duration: float = 2.0,
                                   max_duration: float = 30.0) -> List[SRTSegment]:
        """根据持续时间过滤片段"""
        filtered = [
            segment for segment in segments 
            if min_duration <= segment.duration <= max_duration
        ]
        
        self.logger.info(f"时长过滤: {len(segments)} -> {len(filtered)} 个片段")
        return filtered
    
    def filter_segments_by_keywords(self, segments: List[SRTSegment], 
                                   keywords: List[str]) -> List[SRTSegment]:
        """根据关键词过滤片段"""
        filtered = []
        
        for segment in segments:
            for keyword in keywords:
                if keyword in segment.text:
                    filtered.append(segment)
                    break
        
        self.logger.info(f"关键词过滤: {len(segments)} -> {len(filtered)} 个片段")
        return filtered
    
    def get_statistics(self, segments: List[SRTSegment]) -> Dict:
        """获取统计信息"""
        if not segments:
            return {}
        
        durations = [seg.duration for seg in segments]
        total_text = self.get_full_content(segments)
        
        return {
            'total_segments': len(segments),
            'total_duration': sum(durations),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'total_text_length': len(total_text),
            'total_characters': len(total_text.replace(' ', ''))
        } 