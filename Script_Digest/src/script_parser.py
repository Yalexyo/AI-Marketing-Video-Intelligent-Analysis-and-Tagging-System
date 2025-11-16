#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能脚本解析器
负责接收和解析用户输入的脚本，并利用动态配置系统进行结构化分析。
"""

import os
import logging
from typing import Dict, List, Any, Optional

# 确保可以从src目录导入其他模块
try:
    from config.dynamic_match_config import DynamicMatchConfig
except ImportError:
    # 如果直接运行此文件，需要将项目根目录添加到sys.path
    import sys
    # 'Script_Digest/src' -> 'Script_Digest' -> ''
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    from config.dynamic_match_config import DynamicMatchConfig

logger = logging.getLogger(__name__)

class ScriptParser:
    """
    脚本解析器，用于处理和分析用户提供的脚本内容。
    """

    def __init__(self):
        """
        初始化脚本解析器。
        """
        self.config = DynamicMatchConfig()
        logger.info("✅ 脚本解析器初始化完成，已加载动态匹配配置。")

    def parse_script(self, script_segments: Dict[str, str]) -> Optional[List[Dict[str, Any]]]:
        """
        解析用户提供的脚本段落。

        Args:
            script_segments (Dict[str, str]): 一个字典，键是段落ID，值是段落内容。

        Returns:
            Optional[List[Dict[str, Any]]]: 一个包含每个段落分析结果的列表，
                                           如果输入无效则返回None。
        """
        if not script_segments or not isinstance(script_segments, dict):
            logger.error("❌ 输入的脚本格式无效，必须是一个非空字典。")
            return None

        logger.info(f"🚀 开始解析 {len(script_segments)} 个脚本段落...")
        
        try:
            self.config.load_user_script(script_segments)
            analyzed_data = self.config.analyzed_segments
            
            logger.info("✅ 脚本解析和结构化分析成功。")
            return analyzed_data
        except Exception as e:
            logger.error(f"❌ 解析脚本时发生错误: {e}", exc_info=True)
            return None

    def get_analyzed_segment(self, segment_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单个已分析的段落信息。

        Args:
            segment_id (str): 要查找的段落ID。

        Returns:
            Optional[Dict[str, Any]]: 包含该段落分析信息的字典，如果未找到则返回None。
        """
        for segment in self.config.analyzed_segments:
            if segment['id'] == segment_id:
                return segment
        
        logger.warning(f"⚠️ 未找到ID为 '{segment_id}' 的已分析段落。")
        return None

if __name__ == "__main__":
    # --- 测试脚本解析器 ---
    print("🧪 测试智能脚本解析器...")

    # 1. 模拟用户输入的脚本数据
    user_script_input = {
        "S01_Brand": "能自己喂肯定是更好的，但凡你决定了奶粉喂养，就一定要选有百年科研实力，专业渠道也认可的品牌。",
        "S02_Action": "妈妈拿着奶瓶无奈摇头，宝宝饿得一直哭闹",
        "S03_Emotion": "选奶关键的就是不试错，你不冲我可要冲了！",
        "S04_Hook": "狗都不，生！"
    }

    # 2. 初始化解析器
    parser = ScriptParser()
    print("✅ 解析器初始化成功。")

    # 3. 解析脚本
    analyzed_script = parser.parse_script(user_script_input)

    # 4. 打印结果
    if analyzed_script:
        print(f"\n🎉 成功解析了 {len(analyzed_script)} 个脚本段落：")
        
        for i, segment in enumerate(analyzed_script, 1):
            print(f"\n--- 段落 {i} ---")
            print(f"  - ID: {segment['id']}")
            print(f"  - 内容: '{segment['content'][:35]}...'")
            print(f"  - 识别类型: {segment['type']}")
            print(f"  - 关键词: {segment['keywords']}")
            print(f"  - 预期情绪: {segment['expected_emotions']}")

        # 5. 测试获取单个段落
        print("\n--- 测试获取单个段落 ---")
        single_segment = parser.get_analyzed_segment("S02_Action")
        if single_segment:
            print("✅ 成功获取ID为 'S02_Action' 的段落：")
            print(f"   内容: {single_segment['content']}")
        else:
            print("❌ 获取单个段落失败。")

    else:
        print("\n❌ 脚本解析失败，请检查错误日志。")
