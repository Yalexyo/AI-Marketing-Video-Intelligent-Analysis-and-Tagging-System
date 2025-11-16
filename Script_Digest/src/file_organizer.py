#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件组织器
根据匹配结果，创建文件夹并复制/链接匹配的视频文件。
"""

import os
import shutil
import logging
import re
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class FileOrganizer:
    """
    负责根据匹配结果整理文件的类。
    """

    def __init__(self, output_base_dir: str, copy_mode: str = 'copy', enable_reference_move: bool = True):
        """
        初始化文件组织器。

        Args:
            output_base_dir (str): 所有输出文件夹的根目录。
            copy_mode (str): 文件操作模式, 'copy' 或 'symlink'。
            enable_reference_move (bool): 是否启用从【参考】文件夹移动最佳匹配文件。
        """
        self.output_base_dir = Path(output_base_dir)
        self.copy_mode = copy_mode
        self.enable_reference_move = enable_reference_move
        self.operation_log: List[str] = []

        if self.copy_mode not in ['copy', 'symlink']:
            raise ValueError("copy_mode 必须是 'copy' 或 'symlink'")

        # 确保根输出目录存在
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ 文件组织器初始化完成，输出目录: {self.output_base_dir}, 操作模式: {self.copy_mode}")
        if enable_reference_move:
            logger.info(f"📁 已启用从【参考】文件夹移动最佳匹配功能")

    def organize_files(self, match_results: List[Dict[str, Any]]) -> List[str]:
        """
        根据匹配结果组织文件。

        Args:
            match_results (List[Dict[str, Any]]): 来自 VideoMatcher 的匹配结果列表。

        Returns:
            List[str]: 操作日志列表。
        """
        if not match_results:
            logger.warning("⚠️ 没有匹配结果，无需组织文件。")
            return []

        logger.info(f"🚀 开始根据 {len(match_results)} 条匹配结果组织文件...")
        self.operation_log = []

        for result in match_results:
            segment_id = result['segment_id']
            segment_content = result['segment_content']
            best_matches = result['best_matches']

            # 1. 修正文件夹命名逻辑
            folder_name = self._generate_folder_name(segment_id, segment_content)
            segment_dir = self.output_base_dir / folder_name
            segment_dir.mkdir(exist_ok=True)
            self.log_operation(f"创建目录: {segment_dir}")

            # 🎯 新逻辑：如果启用了reference_move，则跳过文件处理，因为VideoMatcher已经完成了
            if self.enable_reference_move:
                logger.info(f"✅ 段落 {segment_id} 的文件已由VideoMatcher处理完成，跳过重复组织")
                continue

            # 2. 处理每个匹配的视频（仅在未启用reference_move时执行）
            for match in best_matches:
                video_path_str = match['video_file_path']
                video_filename = match.get('video_file_name', '')
                
                try:
                    # 如果【参考】文件夹中没有，则按原逻辑查找和复制
                    video_path = Path(video_path_str)
                    if not video_path.exists():
                        # 视频文件应该在 data/input/ 目录下，与JSON文件同目录
                        video_filename_clean = video_path_str.replace('.mp4', '').split('/')[-1] + '.mp4'
                        input_dir = self.output_base_dir.parent / 'input'  # data/input/
                        alt_video_path = input_dir / video_filename_clean
                        
                        if alt_video_path.exists():
                            video_path = alt_video_path
                        else:
                            # 如果还是找不到，尝试在🎬Slice目录查找（兼容旧路径）
                            project_root = self.output_base_dir.parent.parent
                            legacy_video_path = project_root / '🎬Slice' / video_path.name
                            if legacy_video_path.exists():
                                video_path = legacy_video_path
                            else:
                                self.log_operation(f"错误: 源文件未找到: {video_path_str}")
                                logger.warning(f"源文件未找到: {video_path_str} (已尝试路径: {alt_video_path}, {legacy_video_path})")
                                continue

                    destination_path = segment_dir / video_path.name
                    self._process_file(video_path, destination_path)

                except Exception as e:
                    self.log_operation(f"错误处理文件 '{video_path_str}': {e}")
                    logger.error(f"处理文件 '{video_path_str}' 时出错: {e}", exc_info=True)

        logger.info(f"✅ 文件组织完成，共执行 {len(self.operation_log)} 项操作。")
        return self.operation_log

    def _move_file_from_reference(self, source_path: Path, destination_path: Path) -> None:
        """
        从【参考】文件夹移动文件到段落根目录。
        
        Args:
            source_path (Path): 【参考】文件夹中的源文件路径
            destination_path (Path): 目标文件路径（段落根目录）
        """
        try:
            if destination_path.exists():
                # 如果目标文件已存在，删除【参考】中的重复文件
                source_path.unlink()
                self.log_operation(f"删除【参考】中的重复文件: {source_path.name}")
                logger.debug(f"🗑️ 删除【参考】重复文件: {source_path.name}")
            else:
                # 移动文件到段落根目录
                shutil.move(str(source_path), str(destination_path))
                self.log_operation(f"从【参考】移动最佳匹配: {source_path.name} → {destination_path.name}")
                logger.info(f"⭐ 从【参考】移动最佳匹配: {source_path.name}")
                
        except Exception as e:
            logger.error(f"❌ 从【参考】移动文件失败 {source_path} → {destination_path}: {e}")
            self.log_operation(f"错误: 移动失败 {source_path} → {destination_path}: {e}")

    def _generate_folder_name(self, segment_id: str, content: str) -> str:
        """
        根据用户要求生成文件夹名称，例如：【1狗都不...】
        """
        # 提取ID中的数字 - 使用字符串替换方法处理各种数字格式
        id_number = ""
        temp_id = segment_id
        
        # 处理emoji数字 (完整替换)
        emoji_mappings = {
            "1️⃣": "1", "2️⃣": "2", "3️⃣": "3", "4️⃣": "4", "5️⃣": "5",
            "6️⃣": "6", "7️⃣": "7", "8️⃣": "8", "9️⃣": "9", "🔟": "10"
        }
        for emoji, num in emoji_mappings.items():
            if emoji in temp_id:
                id_number += num
                temp_id = temp_id.replace(emoji, "")
                break  # 只取第一个匹配的emoji数字
        
        # 处理圆圈数字
        circle_mappings = {
            "①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5",
            "⑥": "6", "⑦": "7", "⑧": "8", "⑨": "9", "⑩": "10"
        }
        for circle, num in circle_mappings.items():
            if circle in temp_id:
                id_number += num
                temp_id = temp_id.replace(circle, "")
                break  # 只取第一个匹配的圆圈数字
        
        # 处理普通数字 (如果还没找到数字)
        if not id_number:
            id_number = ''.join(filter(str.isdigit, temp_id))
        
        # 如果仍然没有找到数字，使用默认值
        if not id_number:
            id_number = "S"

        # 获取内容前5个字
        prefix_content = content[:5]
        
        # 拼接成最终格式
        folder_name = f"【{id_number}{prefix_content}...】"
        
        # 清理文件名中的非法字符，但保留中括号和...
        sanitized_name = re.sub(r'[\\/*?:"<>|]', "", folder_name)
        return sanitized_name


    def _process_file(self, source: Path, destination: Path):
        """根据模式处理单个文件（复制或链接）。"""
        if self.copy_mode == 'copy':
            try:
                shutil.copy2(source, destination)
                self.log_operation(f"复制: '{source.name}' 到 '{destination.parent.name}'")
            except Exception as e:
                self.log_operation(f"错误复制 '{source.name}': {e}")
                logger.error(f"复制文件时出错: {e}")
        
        elif self.copy_mode == 'symlink':
            try:
                if destination.exists() or destination.is_symlink():
                    destination.unlink()
                destination.symlink_to(source)
                self.log_operation(f"链接: '{source.name}' 到 '{destination.parent.name}'")
            except Exception as e:
                self.log_operation(f"错误创建链接 '{source.name}': {e}")
                logger.error(f"创建符号链接时出错: {e}")

    def log_operation(self, message: str):
        """记录一个操作到日志。"""
        self.operation_log.append(message)
        logger.debug(message)

if __name__ == "__main__":
    # --- 测试文件组织器 (修正版) ---
    print("🧪 测试文件组织器 (修正文件夹命名逻辑)...")

    temp_output_dir = Path("temp_test_output")
    temp_source_dir = Path("temp_test_source")
    temp_output_dir.mkdir(exist_ok=True)
    temp_source_dir.mkdir(exist_ok=True)

    (temp_source_dir / "video1.mp4").touch()
    (temp_source_dir / "video2.mp4").touch()

    print(f"✅ 创建了临时目录: {temp_output_dir} 和 {temp_source_dir}")

    mock_results = [
        {
            "segment_id": "1️⃣", # 使用您示例中的ID
            "segment_content": "狗都不，生！",
            "best_matches": [
                {"video_file_name": "video1.mp4", "video_file_path": str(temp_source_dir / "video1.mp4")}
            ]
        },
        {
            "segment_id": "2️⃣",
            "segment_content": "能自己喂肯定是更好的",
            "best_matches": [
                {"video_file_name": "video2.mp4", "video_file_path": str(temp_source_dir / "video2.mp4")}
            ]
        }
    ]
    
    try:
        organizer = FileOrganizer(str(temp_output_dir))
        organizer.organize_files(mock_results)

        print("\n--- 验证文件系统 ---")
        # 验证新命名规则 (修正期望的文件夹名称)
        expected_dir1 = temp_output_dir / "【1狗都不，生...】"
        expected_dir2 = temp_output_dir / "【2能自己喂肯...】"
        
        correct = True
        if not expected_dir1.is_dir() or not (expected_dir1 / "video1.mp4").exists():
            print(f"❌ 目录 '{expected_dir1}' 或其下文件创建不正确！")
            correct = False
        else:
            print(f"✅ 目录 '{expected_dir1}' 创建正确。")

        if not expected_dir2.is_dir() or not (expected_dir2 / "video2.mp4").exists():
            print(f"❌ 目录 '{expected_dir2}' 或其下文件创建不正确！")
            correct = False
        else:
            print(f"✅ 目录 '{expected_dir2}' 创建正确。")
        
        if correct:
            print("\n🎉 文件组织器文件夹命名逻辑修正成功！")
        else:
            print("\n❌ 文件夹命名逻辑测试失败！")

    finally:
        shutil.rmtree(temp_output_dir)
        shutil.rmtree(temp_source_dir)
        print("\n🗑️ 已清理临时测试目录。")
