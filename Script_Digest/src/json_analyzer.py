#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频切片JSON分析器
负责扫描目录，读取并解析所有 ..._analysis.json 文件，提取关键信息。
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class JsonAnalyzer:
    """
    分析和管理视频切片JSON文件的类。
    """

    def __init__(self, json_directory: str):
        """
        初始化JSON分析器。

        Args:
            json_directory (str): 存放 ..._analysis.json 文件的目录路径。
        """
        self.json_dir = Path(json_directory)
        if not self.json_dir.is_dir():
            logger.error(f"❌ 指定的JSON目录不存在或不是一个目录: {json_directory}")
            raise FileNotFoundError(f"JSON directory not found: {json_directory}")
        
        self.video_slice_data: List[Dict[str, Any]] = []
        logger.info(f"✅ JSON分析器初始化完成，目标目录: {self.json_dir}")

    def scan_and_parse_all(self) -> int:
        """
        扫描目录下的所有 `..._analysis.json` 文件并解析它们。

        Returns:
            int: 成功解析的文件数量。
        """
        logger.info(f"🚀 开始扫描目录: {self.json_dir}")
        json_files = list(self.json_dir.glob("*_analysis.json"))

        if not json_files:
            logger.warning(f"⚠️ 在目录 {self.json_dir} 中未找到 `..._analysis.json` 文件。")
            return 0

        logger.info(f"🔍 发现了 {len(json_files)} 个JSON文件，开始解析...")
        
        parsed_count = 0
        for file_path in json_files:
            parsed_data = self._parse_single_json(file_path)
            if parsed_data:
                self.video_slice_data.append(parsed_data)
                parsed_count += 1
        
        logger.info(f"✅ 完成解析，成功处理了 {parsed_count}/{len(json_files)} 个文件。")
        self.video_slice_data.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return parsed_count

    def _parse_single_json(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        解析单个JSON文件，并提取关键信息。

        Args:
            file_path (Path): JSON文件的路径。

        Returns:
            Optional[Dict[str, Any]]: 包含关键信息的字典，如果解析失败则返回None。
        """
        try:
            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f)

            if not data.get("success", False):
                logger.warning(f"⏭️ 跳过文件 {file_path.name}，因为 'success' 标记为 false。")
                return None
            
            # 提取我们关心的字段，提供默认值以避免KeyError
            extracted = {
                "file_path": data.get("file_path", ""),
                "file_name": data.get("file_name", ""),
                "object": data.get("object", "未知"),
                "scene": data.get("scene", "未知"),
                "emotion": data.get("emotion", "未知"),
                "main_tag": data.get("analysis", {}).get("predicted_category", "未知"),
                "secondary_category": data.get("secondary_category", "未知"),
                "reasoning": data.get("analysis", {}).get("reasoning", ""),
                "matched_keywords": data.get("analysis", {}).get("matched_keywords", []),
                "confidence": data.get("confidence", 0.0),
                "source_json_path": str(file_path.resolve()) # 保存原始json文件路径
            }
            return extracted
        except json.JSONDecodeError:
            logger.error(f"❌ 解析JSON文件失败 (格式错误): {file_path.name}")
        except Exception as e:
            logger.error(f"❌ 处理文件 {file_path.name} 时发生未知错误: {e}", exc_info=True)
        
        return None

    def get_all_slices(self) -> List[Dict[str, Any]]:
        """
        获取所有已解析的视频切片数据。

        Returns:
            List[Dict[str, Any]]: 视频切片数据列表。
        """
        return self.video_slice_data

    def get_slice_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        根据视频文件名查找对应的切片数据。

        Args:
            filename (str): 视频文件名 (例如 "video_01.mp4")。

        Returns:
            Optional[Dict[str, Any]]: 找到的视频切片数据，否则为None。
        """
        for slice_data in self.video_slice_data:
            if slice_data['file_name'] == filename:
                return slice_data
        return None

if __name__ == "__main__":
    # --- 测试JSON分析器 ---
    print("🧪 测试视频切片JSON分析器...")

    # 假设项目根目录是 "Script_Digest" 的上两级目录
    project_root = Path(__file__).parent.parent.resolve()
    # 使用用户提供的示例JSON文件所在的目录
    test_json_dir = project_root / "🍭Origin"
    
    print(f"📁 测试目标目录: {test_json_dir}")

    if not test_json_dir.exists():
        print(f"❌ 测试目录不存在，测试中止。")
        # 创建一个假的json文件用于测试
        print("💡 正在创建一个临时的测试JSON文件...")
        test_json_dir.mkdir(parents=True, exist_ok=True)
        temp_file = test_json_dir / "temp_test_analysis.json"
        temp_data = {
          "object": "宝宝趴在地上", "scene": "室内", "emotion": "平静", "brand_elements": "无",
          "success": True, "file_path": "/path/to/video.mp4", "file_name": "video.mp4",
          "confidence": 0.8, "analysis": {"predicted_category": "宝宝状态", "reasoning": "宝宝很可爱", "matched_keywords": ["宝宝", "趴"]}
        }
        with temp_file.open('w', encoding='utf-8') as f:
            json.dump(temp_data, f)
    else:
        print("✅ 测试目录已找到。")

    # 1. 初始化分析器
    try:
        analyzer = JsonAnalyzer(str(test_json_dir))
        print("✅ 分析器初始化成功。")

        # 2. 扫描并解析
        num_parsed = analyzer.scan_and_parse_all()

        # 3. 打印结果
        if num_parsed > 0:
            print(f"\n🎉 成功解析了 {num_parsed} 个JSON文件。")
            all_slices = analyzer.get_all_slices()
            
            print("\n--- 解析数据示例 (第一个) ---")
            # 使用json.dumps美化输出
            print(json.dumps(all_slices[0], indent=2, ensure_ascii=False))

            print(f"\n--- 摘要信息 ---")
            print(f"  - 文件名: {all_slices[0]['file_name']}")
            print(f"  - 置信度: {all_slices[0]['confidence']}")
            print(f"  - 主要对象: {all_slices[0]['object']}")
            print(f"  - 主要标签: {all_slices[0]['main_tag']}")

        else:
            print("\n❌ 未能解析任何JSON文件。请检查目录和文件内容。")

    except FileNotFoundError as e:
        print(f"\n❌ 初始化失败: {e}")

    # 清理临时文件
    if 'temp_file' in locals() and temp_file.exists():
        temp_file.unlink()
        print("\n🗑️ 已清理临时测试文件。")

