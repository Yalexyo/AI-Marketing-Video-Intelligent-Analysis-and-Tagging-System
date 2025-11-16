#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频匹配器
负责将脚本段落与视频切片进行智能匹配，集成AI分析和预筛选优化。
"""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

# 确保可以从src目录导入其他模块
try:
    from config.dynamic_match_config import DynamicMatchConfig
    from deepseek_client import DeepSeekClient
except ImportError:
    # 如果直接运行此文件，需要将项目根目录添加到sys.path
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    from config.dynamic_match_config import DynamicMatchConfig
    from src.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)

class VideoMatcher:
    """
    视频匹配器，负责将脚本段落与视频切片进行智能匹配。
    """

    def __init__(self, 
                 enable_pre_filter: bool = True, 
                 keyword_threshold: float = 0.15,
                 output_dir: Optional[str] = None,
                 enable_reference_copy: bool = True):
        """
        初始化视频匹配器。

        Args:
            enable_pre_filter (bool): 是否启用关键词预筛选优化
            keyword_threshold (float): 关键词重叠阈值，低于此值的视频将被过滤
            output_dir (Optional[str]): 输出目录路径，用于预筛选文件复制
            enable_reference_copy (bool): 是否启用预筛选文件复制到【参考】文件夹
                """
        self.config = DynamicMatchConfig()
        self.ai_client = DeepSeekClient()
        self.match_results: List[Dict[str, Any]] = []
        
        # 预筛选配置
        self.enable_pre_filter = enable_pre_filter
        self.keyword_threshold = keyword_threshold
        
        # 文件复制配置
        self.output_dir = Path(output_dir) if output_dir else None
        self.enable_reference_copy = enable_reference_copy
        
        logger.info(f"✅ 视频匹配器初始化完成")
        if enable_pre_filter:
            logger.info(f"🔍 已启用关键词预筛选 (阈值: {keyword_threshold:.2f})")
        if enable_reference_copy and output_dir:
            logger.info(f"📁 已启用预筛选文件复制到【参考】文件夹")

    def match_script_to_videos(
        self,
        analyzed_script: List[Dict[str, Any]],
        video_slices: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        将脚本段落与视频切片进行匹配。

        Args:
            analyzed_script (List[Dict[str, Any]]): 已分析的脚本段落列表
            video_slices (List[Dict[str, Any]]): 视频切片数据列表

        Returns:
            List[Dict[str, Any]]: 匹配结果列表
        """
        if not self.ai_client:
            logger.error("❌ DeepSeek客户端未初始化，无法进行匹配。")
            return []
            
        if not analyzed_script or not video_slices:
            logger.warning("⚠️ 脚本或视频数据为空，无法进行匹配。")
            return []

        logger.info(f"🚀 开始为 {len(analyzed_script)} 个脚本段落匹配 {len(video_slices)} 个视频切片...")
        if self.enable_pre_filter:
            logger.info(f"🔍 预筛选模式：将先进行关键词匹配过滤")
        
        self.match_results = []
        total_ai_calls = 0
        total_filtered = 0

        for i, segment in enumerate(analyzed_script, 1):
            logger.info(f"--- 正在处理第 {i}/{len(analyzed_script)} 个脚本段落: ID={segment['id']} ---")
            
            # 预筛选步骤
            if self.enable_pre_filter:
                filtered_videos = self._pre_filter_videos(segment, video_slices)
                filtered_count = len(video_slices) - len(filtered_videos)
                total_filtered += filtered_count
                logger.info(f"🔍 预筛选：{len(video_slices)} → {len(filtered_videos)} 个视频 (过滤掉 {filtered_count} 个)")
                
                # 复制预筛选通过的视频到【参考】文件夹
                self._copy_prefiltered_videos_to_reference(segment, filtered_videos)
                
                videos_to_process = filtered_videos
            else:
                videos_to_process = video_slices
            
            best_matches_for_segment = self._find_best_matches_for_segment(segment, videos_to_process)
            total_ai_calls += len(videos_to_process)
            
            # 保存通过AI匹配的视频信息到pass.json
            self._save_passed_videos_to_json(segment, best_matches_for_segment)
            
            if best_matches_for_segment:
                self.match_results.append({
                    "segment_id": segment['id'],
                    "segment_content": segment['content'],
                    "best_matches": best_matches_for_segment
                })
        
        if self.enable_pre_filter:
            efficiency_gain = (total_filtered / (len(analyzed_script) * len(video_slices))) * 100
            logger.info(f"🎯 预筛选效果：总共过滤掉 {total_filtered} 次AI调用，效率提升 {efficiency_gain:.1f}%")
            logger.info(f"📊 实际AI调用次数: {total_ai_calls} (vs 原本 {len(analyzed_script) * len(video_slices)})")
        
        logger.info(f"✅ 完成所有匹配，共为 {len(self.match_results)} 个段落找到了匹配。")
        return self.match_results

    def _pre_filter_videos(
        self, 
        segment: Dict[str, Any], 
        video_slices: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        基于关键词重叠度预筛选视频，过滤掉明显不相关的视频。

        Args:
            segment (Dict[str, Any]): 脚本段落数据
            video_slices (List[Dict[str, Any]]): 所有视频切片

        Returns:
            List[Dict[str, Any]]: 通过预筛选的视频列表
        """
        segment_keywords = set(segment.get('keywords', []))
        if not segment_keywords:
            logger.warning(f"⚠️ 段落 {segment['id']} 没有关键词，跳过预筛选")
            return video_slices
        
        # 🎯 动态调整阈值：促销逼单内容使用更低的阈值
        promotion_keywords = {'选奶', '试错', '冲了', '促销', '逼单', '关键', '不试错'}
        current_threshold = self.keyword_threshold
        
        if segment_keywords & promotion_keywords:
            current_threshold = max(0.05, self.keyword_threshold - 0.1)  # 降低阈值但不低于0.05
            logger.info(f"🎁 检测到促销逼单内容，调整预筛选阈值: {self.keyword_threshold:.2f} → {current_threshold:.2f}")
        
        # 语义相似词映射
        semantic_mapping = {
            '喂养': ['喂奶', '奶瓶', '哺乳', '母乳喂养', '喂食', '吃奶', '喝奶', '喂宝宝', '温柔喂', '爸爸温柔喂'],
            '宝宝': ['婴儿', '小孩', '孩子', '小朋友', '娃娃', '宝宝喝奶', '宝宝喝', '宝宝吃'],
            '妈妈': ['母亲', '妈咪', '女人', '女性', '爸爸', '父亲'],  # 添加父亲相关
            '奶粉': ['配方奶', '婴幼儿奶粉', '牛奶粉', '启赋', '惠氏', '蕴淳'],
            '启赋': ['启赋奶粉', '惠氏启赋', '启赋蕴淳'],
            '惠氏': ['惠氏奶粉', '惠氏品牌', '惠氏启赋'],
            '生！': ['生', '出生', '新生', '诞生'],  # 为特殊关键词添加映射
            '狗都不': ['狗都', '都不', '否定', '拒绝'],  # 为特殊关键词添加映射
            
            # 🎯 新增：促销机制和逼单脚本相关关键词映射
            '选奶': ['选择', '奶粉', '产品展示', '推荐', '建议', '选择奶粉', '挑选'],
            '试错': ['尝试', '错误', '选择', '决定', '测试'],
            '冲了': ['冲', '行动', '决定', '购买', '选择', '马上', '立即', '赶紧'],
            '促销': ['促销', '优惠', '活动', '限时', '特价', '折扣', '购买'],
            '逼单': ['推荐', '建议', '选择', '决定', '马上', '立即', '不要错过'],
            '关键': ['重要', '关键', '核心', '主要', '必须', '一定要'],
            '不试错': ['正确选择', '一次选对', '准确', '可靠', '值得信赖'],
            
            # 🎁 促销机制标签相关映射
            '温馨': ['温馨', '家庭', '亲子', '互动', '和谐', '幸福'],
            '展示': ['展示', '介绍', '推荐', '说明', '演示'],
            '欢乐': ['开心', '快乐', '愉快', '喜悦', '欢乐', '高兴'],
            '信息': ['信息', '内容', '介绍', '说明', '展示']
        }
        
        filtered_videos = []
        
        for video in video_slices:
            # 从视频JSON中提取关键词和文本内容
            video_keywords = set()
            video_text = ""
            
            # 从不同字段提取关键词
            if 'matched_keywords' in video:
                video_keywords.update(video['matched_keywords'])
            
            if 'object' in video:
                video_keywords.add(video['object'])
                video_text += " " + str(video['object'])
            
            if 'emotion' in video:
                video_keywords.add(video['emotion'])
                
            if 'main_tag' in video:
                video_keywords.add(video['main_tag'])
                
            if 'reasoning' in video:
                video_text += " " + str(video['reasoning'])
            
            # 计算关键词重叠度（直接匹配）
            direct_overlap = len(segment_keywords & video_keywords)
            
            # 计算语义相似匹配
            semantic_overlap = 0
            for seg_keyword in segment_keywords:
                if seg_keyword in semantic_mapping:
                    similar_words = semantic_mapping[seg_keyword]
                    # 检查视频关键词或文本中是否包含相似词
                    for similar_word in similar_words:
                        if similar_word in video_keywords or similar_word in video_text:
                            semantic_overlap += 1
                            break
            
            # 总重叠度 = 直接匹配 + 语义匹配
            total_overlap = direct_overlap + semantic_overlap
            overlap_ratio = total_overlap / len(segment_keywords)
            
            # 特殊关键词加权 (品牌名、专业术语等)
            important_keywords = {'启赋', '惠氏', 'HMO', '奶粉', '宝宝', '妈妈', '喂养'}
            important_overlap = len(segment_keywords & video_keywords & important_keywords)
            if important_overlap > 0:
                overlap_ratio += important_overlap * 0.2  # 重要关键词加权
            
            # 🎯 新增：促销机制特殊匹配规则
            promotion_keywords = {'选奶', '试错', '冲了', '促销', '逼单', '关键', '不试错'}
            segment_has_promotion = bool(segment_keywords & promotion_keywords)
            video_is_promotion = '🎁 促销机制' in video_text or '促销机制' in str(video.get('main_tag', ''))
            
            # 如果脚本是促销逼单类型，且视频是促销机制，给予特殊加权
            if segment_has_promotion and video_is_promotion:
                overlap_ratio += 0.3  # 促销匹配加权
                logger.debug(f"  🎁 促销机制特殊匹配: {video.get('file_name', 'Unknown')} (+0.3)")
            
            # 🎁 促销机制视频的额外语义匹配
            if video_is_promotion:
                promotion_semantic_words = ['展示', '推荐', '介绍', '温馨', '家庭', '欢乐', '选择', '决定']
                for word in promotion_semantic_words:
                    if word in video_text:
                        overlap_ratio += 0.1  # 每个促销语义词+0.1
                        break
            
            # 通过阈值检查
            if overlap_ratio >= current_threshold:
                filtered_videos.append(video)
                logger.debug(f"  ✅ 通过预筛选: {video.get('file_name', 'Unknown')} (重叠度: {overlap_ratio:.2f})")
            else:
                logger.debug(f"  ❌ 被过滤: {video.get('file_name', 'Unknown')} (重叠度: {overlap_ratio:.2f})")
        
        return filtered_videos

    def _copy_prefiltered_videos_to_reference(
        self, 
        segment: Dict[str, Any], 
        filtered_videos: List[Dict[str, Any]]
    ) -> None:
        """
        将预筛选通过的视频复制到对应段落的【参考】文件夹中。
        
        Args:
            segment (Dict[str, Any]): 脚本段落数据
            filtered_videos (List[Dict[str, Any]]): 预筛选通过的视频列表
        """
        if not self.enable_reference_copy or not self.output_dir or not filtered_videos:
            return
            
        try:
            # 生成文件夹名称
            segment_id = segment.get('id', 'unknown')
            segment_content = segment.get('content', '')
            folder_name = self._generate_folder_name(segment_id, segment_content)
            
            # 创建段落目录和参考子目录
            segment_dir = self.output_dir / folder_name
            reference_dir = segment_dir / "【参考】"
            
            segment_dir.mkdir(parents=True, exist_ok=True)
            reference_dir.mkdir(exist_ok=True)
            
            # 复制预筛选视频到参考文件夹
            copied_count = 0
            for video in filtered_videos:
                try:
                    # 获取源JSON文件路径，从中推断实际视频文件
                    source_json_path = video.get('source_json_path', '')
                    if not source_json_path:
                        logger.debug(f"⚠️ 预筛选复制跳过: 无源JSON路径")
                        continue
                    
                    # 从JSON文件路径推断对应的实际视频文件
                    json_path = Path(source_json_path)
                    actual_video_name = json_path.name.replace('_analysis.json', '.mp4')
                    source_video_path = json_path.parent / actual_video_name
                    
                    if not source_video_path.exists():
                        logger.debug(f"⚠️ 预筛选复制跳过: 找不到视频文件 {actual_video_name}")
                        continue
                    
                    # 复制到参考文件夹
                    dest_path = reference_dir / actual_video_name
                    if not dest_path.exists():  # 避免重复复制
                        shutil.copy2(source_video_path, dest_path)
                        copied_count += 1
                        logger.debug(f"📁 复制到参考: {actual_video_name}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 复制视频文件失败 {video.get('file_name', 'unknown')}: {e}")
                    continue
            
            if copied_count > 0:
                logger.info(f"📁 已复制 {copied_count} 个预筛选视频到 {folder_name}/【参考】/")
            
        except Exception as e:
            logger.error(f"❌ 创建参考文件夹失败: {e}")

    def _find_video_file(self, video_filename: str) -> Optional[Path]:
        """
        查找视频文件的实际路径。
        
        Args:
            video_filename (str): 视频文件名
            
        Returns:
            Optional[Path]: 视频文件路径，如果找不到则返回None
        """
        if not video_filename:
            return None
            
        if not self.output_dir:
            return None
            
        input_dir = self.output_dir.parent / 'input'
        
        # 方法1: 直接匹配文件名
        video_path = input_dir / video_filename
        if video_path.exists():
            return video_path
        
        # 方法2: 由于JSON中的file_name与实际文件名不匹配，
        # 我们需要通过JSON文件找到对应的实际视频文件
        # 查找同名的JSON文件，然后获取对应的实际视频文件名
        json_filename = video_filename.replace('.mp4', '_analysis.json')
        json_path = input_dir / json_filename
        
        if json_path.exists():
            try:
                import json
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 从JSON文件名推断实际视频文件名
                # JSON文件名格式：温馨日常_宝宝喝奶瓶中的奶_analysis.json
                # 对应视频文件名：温馨日常_宝宝喝奶瓶中的奶.mp4
                actual_video_name = json_path.name.replace('_analysis.json', '.mp4')
                actual_video_path = input_dir / actual_video_name
                
                if actual_video_path.exists():
                    return actual_video_path
                    
            except Exception as e:
                logger.debug(f"读取JSON文件失败 {json_path}: {e}")
        
        # 方法3: 兼容旧路径：在🎬Slice目录查找
        project_root = self.output_dir.parent.parent
        legacy_path = project_root / '🎬Slice' / video_filename
        if legacy_path.exists():
            return legacy_path
                
        return None

    def _generate_folder_name(self, segment_id: str, content: str) -> str:
        """
        生成文件夹名称（与file_organizer.py中的逻辑保持一致）。
        
        Args:
            segment_id (str): 段落ID
            content (str): 段落内容
            
        Returns:
            str: 文件夹名称
        """
        # 提取数字ID
        numeric_id = self._extract_numeric_id(segment_id)
        
        # 截取内容前缀（最多5个字符，避免文件夹名过长）
        content_prefix = content[:5] if content else "未知内容"
        
        return f"【{numeric_id}{content_prefix}...】"

    def _extract_numeric_id(self, segment_id: str) -> str:
        """
        从段落ID中提取数字（与file_organizer.py中的逻辑保持一致）。
        
        Args:
            segment_id (str): 段落ID（如 "1️⃣", "2", "③" 等）
            
        Returns:
            str: 提取的数字字符串
        """
        import re
        
        # 处理emoji数字 (1️⃣ → 1)
        emoji_to_digit = {
            '1️⃣': '1', '2️⃣': '2', '3️⃣': '3', '4️⃣': '4', '5️⃣': '5',
            '6️⃣': '6', '7️⃣': '7', '8️⃣': '8', '9️⃣': '9', '🔟': '10'
        }
        
        if segment_id in emoji_to_digit:
            return emoji_to_digit[segment_id]
        
        # 提取任何数字字符
        numbers = re.findall(r'\d+', segment_id)
        return numbers[0] if numbers else segment_id

    def _get_actual_video_name(self, video_slice: Dict[str, Any]) -> str:
        """
        从视频切片数据中获取实际的视频文件名。
        
        Args:
            video_slice (Dict[str, Any]): 视频切片数据
            
        Returns:
            str: 实际的视频文件名
        """
        try:
            source_json_path = video_slice.get('source_json_path', '')
            if source_json_path:
                json_path = Path(source_json_path)
                actual_video_name = json_path.name.replace('_analysis.json', '.mp4')
                return actual_video_name
        except Exception as e:
            logger.debug(f"获取实际视频文件名失败: {e}")
        
        # 如果失败，返回原始文件名作为备用
        return video_slice.get('file_name', 'unknown.mp4')

    def _find_best_matches_for_segment(
        self,
        segment: Dict[str, Any],
        video_slices: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """为单个脚本段落找到最佳的视频匹配。"""
        
        current_segment_matches = []
        for j, video_slice in enumerate(video_slices, 1):
            logger.debug(f"  - 正在匹配视频 {j}/{len(video_slices)}: {video_slice['file_name']}")
            
            # 1. 构造Prompt
            prompt = self._construct_prompt(segment, video_slice)
            
            # 2. 调用AI获取分析
            ai_analysis = self.ai_client.get_match_analysis(prompt)
            
            if ai_analysis and "match_score" in ai_analysis:
                match_score = ai_analysis.get("match_score", 0.0)
                
                # 3. 判断是否满足最低匹配阈值
                min_threshold = self.config.QUALITY_STANDARDS['min_acceptable_threshold']
                if match_score >= min_threshold:
                    # 获取实际的视频文件名（从source_json_path推断）
                    actual_video_name = self._get_actual_video_name(video_slice)
                    
                    current_segment_matches.append({
                        "video_file_name": actual_video_name,  # 使用实际的视频文件名
                        "video_file_path": video_slice['file_path'],
                        "match_score": match_score,
                        "match_reason": ai_analysis.get("match_reason", ""),
                        "mismatch_issues": ai_analysis.get("mismatch_issues", [])
                    })
                    logger.info(f"    🌟 找到一个有效匹配: {video_slice['file_name']} (分数: {match_score:.2f})")
        
        # 4. 排序并筛选出最佳匹配
        sorted_matches = sorted(current_segment_matches, key=lambda x: x['match_score'], reverse=True)
        max_matches = self.config.QUALITY_STANDARDS['max_matches_per_segment']
        
        return sorted_matches[:max_matches]

    def _construct_prompt(self, segment: Dict[str, Any], video_slice: Dict[str, Any]) -> str:
        """构造发送给DeepSeek的匹配分析提示。"""
        
        # 从视频JSON中提取关键信息
        video_object = video_slice.get('object', '未知')
        video_scene = video_slice.get('scene', '未知')
        video_emotion = video_slice.get('emotion', '未知')
        video_main_tag = video_slice.get('main_tag', '未知')
        video_keywords = video_slice.get('matched_keywords', [])
        video_reasoning = video_slice.get('analysis', {}).get('reasoning', '未提供')
        
        # 使用配置中的提示模板
        prompt = self.config.DEEPSEEK_PROMPT.format(
            script_content=segment['content'],
            script_type=segment['type'],
            script_keywords=segment['keywords'],
            expected_emotions=segment['expected_emotions'],
            object=video_object,
            scene=video_scene,
            emotion=video_emotion,
            main_tag=video_main_tag,
            matched_keywords=video_keywords,
            reasoning=video_reasoning
        )
        
        return prompt

    def _save_passed_videos_to_json(self, segment: Dict[str, Any], best_matches: List[Dict[str, Any]]) -> None:
        """
        将通过AI匹配的视频信息分级保存到pass.json文件中。
        
        Args:
            segment (Dict[str, Any]): 脚本段落信息
            best_matches (List[Dict[str, Any]]): 通过匹配的视频列表
        """
        if not self.output_dir or not best_matches:
            return
            
        try:
            # 生成段落文件夹名称
            folder_name = self._generate_folder_name(segment['id'], segment['content'])
            segment_dir = self.output_dir / folder_name
            
            # 确保段落目录存在
            segment_dir.mkdir(parents=True, exist_ok=True)
            
            # 分级收录
            high_quality = []
            medium_quality = []
            acceptable = []
            hq = self.config.QUALITY_STANDARDS['high_quality_threshold']
            mq = self.config.QUALITY_STANDARDS['medium_quality_threshold']
            minq = self.config.QUALITY_STANDARDS['min_acceptable_threshold']
            for match in best_matches:
                score = match.get('match_score', 0)
                if score >= hq:
                    high_quality.append(match)
                elif score >= mq:
                    medium_quality.append(match)
                elif score >= minq:
                    acceptable.append(match)
            
            pass_data = {
                "segment_info": {
                    "id": segment['id'],
                    "content": segment['content'],
                    "type": segment.get('type', ''),
                    "keywords": segment.get('keywords', [])
                },
                "processing_time": self._get_current_timestamp(),
                "total_matches": len(best_matches),
                "min_score": min(match['match_score'] for match in best_matches) if best_matches else 0,
                "max_score": max(match['match_score'] for match in best_matches) if best_matches else 0,
                "high_quality": high_quality,
                "medium_quality": medium_quality,
                "acceptable": acceptable
            }
            
            # 保存到pass.json文件
            pass_json_path = segment_dir / "pass.json"
            with open(pass_json_path, 'w', encoding='utf-8') as f:
                json.dump(pass_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 已分级保存 {len(best_matches)} 个匹配结果到 {folder_name}/pass.json")
            
            # 🎯 新增：完成json保存后立即移动文件并添加分数前缀
            self._move_best_matches_with_scores(segment, best_matches)
            
        except Exception as e:
            logger.error(f"❌ 保存pass.json失败: {e}")

    def _move_best_matches_with_scores(self, segment: Dict[str, Any], best_matches: List[Dict[str, Any]]) -> None:
        """
        完成AI匹配后立即复制视频文件到段落根目录，并在文件名前加上分数。
        从【参考】文件夹中删除已选中的文件，保留其他未被选中的候选视频。
        
        Args:
            segment (Dict[str, Any]): 脚本段落信息
            best_matches (List[Dict[str, Any]]): 通过匹配的视频列表
        """
        if not self.output_dir or not best_matches:
            return
            
        try:
            # 生成段落文件夹名称
            folder_name = self._generate_folder_name(segment['id'], segment['content'])
            segment_dir = self.output_dir / folder_name
            reference_dir = segment_dir / "【参考】"
            
            copied_count = 0
            removed_from_reference = 0
            
            for match in best_matches:
                try:
                    video_file_name = match.get('video_file_name', '')
                    match_score = match.get('match_score', 0.0)
                    
                    if not video_file_name:
                        continue
                    
                    # 检查【参考】文件夹中是否有该文件
                    reference_video_path = reference_dir / video_file_name
                    
                    if reference_video_path.exists():
                        # 生成带分数的新文件名：0.85_原文件名.mp4
                        score_prefix = f"{match_score:.2f}_"
                        new_filename = score_prefix + video_file_name
                        
                        # 复制到段落根目录并重命名
                        destination_path = segment_dir / new_filename
                        
                        if not destination_path.exists():  # 避免重复复制
                            shutil.copy2(str(reference_video_path), str(destination_path))
                            copied_count += 1
                            logger.info(f"⭐ 已复制并重命名: {video_file_name} → {new_filename}")
                            
                            # 🎯 关键修改：从【参考】文件夹中删除已选中的文件
                            reference_video_path.unlink()
                            removed_from_reference += 1
                            logger.debug(f"🗑️ 从【参考】删除已选中文件: {video_file_name}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 处理文件失败 {video_file_name}: {e}")
                    continue
            
            if copied_count > 0:
                logger.info(f"📁 完成段落 {segment['id']} 的文件处理:")
                logger.info(f"   ✅ 复制 {copied_count} 个最佳匹配到段落根目录（带分数前缀）")
                logger.info(f"   🗑️ 从【参考】删除 {removed_from_reference} 个已选中文件")
                
                # 统计剩余的候选视频数量
                if reference_dir.exists():
                    remaining_count = len(list(reference_dir.iterdir()))
                    if remaining_count > 0:
                        logger.info(f"   📂 【参考】文件夹保留 {remaining_count} 个其他候选视频供手动选择")
                    else:
                        # 如果没有剩余文件，删除空文件夹
                        reference_dir.rmdir()
                        logger.info(f"   🗑️ 【参考】文件夹已清空并删除")
            
        except Exception as e:
            logger.error(f"❌ 处理匹配文件失败: {e}")

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    # --- 测试视频匹配器 ---
    print("🧪 测试视频匹配器...")

    # 模拟测试数据
    mock_script = [
        {
            "id": "1️⃣",
            "content": "狗都不，生！生的就是纯奶粉喂养八斤八两的大胖娃！",
            "type": "情绪表达",
            "keywords": ["奶粉", "喂养", "娃"],
            "expected_emotions": ["激动"]
        }
    ]
    
    mock_videos = [
        {
            "file_name": "test_video1.mp4",
            "file_path": "/test/path/video1.mp4",
            "object": "爸爸温柔喂宝宝喝奶",
            "scene": "室内",
            "emotion": "温馨",
            "main_tag": "促销机制",
            "matched_keywords": ["喂养", "宝宝", "温馨"],
            "analysis": {"reasoning": "温馨的喂养场景"}
        },
        {
            "file_name": "test_video2.mp4", 
            "file_path": "/test/path/video2.mp4",
            "object": "女人展示珍珠项链",
            "scene": "室内",
            "emotion": "时尚",
            "main_tag": "时尚展示",
            "matched_keywords": ["项链", "时尚"],
            "analysis": {"reasoning": "时尚配饰展示"}
        }
    ]
    
    try:
        # 测试预筛选功能
        matcher = VideoMatcher(enable_pre_filter=True, keyword_threshold=0.2)
        
        print("🔍 测试预筛选功能...")
        filtered = matcher._pre_filter_videos(mock_script[0], mock_videos)
        print(f"预筛选结果: {len(mock_videos)} → {len(filtered)} 个视频")
        
        for video in filtered:
            print(f"  ✅ 通过: {video['file_name']}")
        
        print("\n✅ 预筛选测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
