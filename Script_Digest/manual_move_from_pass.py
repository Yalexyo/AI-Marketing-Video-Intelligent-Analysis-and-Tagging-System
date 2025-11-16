#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动移动脚本
根据各段落目录下的pass.json文件，将通过AI匹配的视频从【参考】文件夹移动到段落根目录
"""

import json
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('manual_move.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class ManualMover:
    """手动移动器，基于pass.json执行文件移动"""
    
    def __init__(self, output_dir: str = "data/output"):
        """
        初始化手动移动器
        
        Args:
            output_dir (str): 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.moved_count = 0
        self.error_count = 0
        self.operation_log = []
        
    def process_all_segments(self) -> None:
        """处理所有段落目录中的pass.json文件"""
        if not self.output_dir.exists():
            logger.error(f"❌ 输出目录不存在: {self.output_dir}")
            return
            
        segment_dirs = [d for d in self.output_dir.iterdir() if d.is_dir() and d.name.startswith('【')]
        
        if not segment_dirs:
            logger.warning("⚠️ 未找到任何段落目录")
            return
            
        logger.info(f"🔍 发现 {len(segment_dirs)} 个段落目录")
        
        for segment_dir in sorted(segment_dirs):
            self.process_segment(segment_dir)
            
        # 显示最终结果
        self.show_summary()
    
    def process_segment(self, segment_dir: Path) -> None:
        """
        处理单个段落目录
        
        Args:
            segment_dir (Path): 段落目录路径
        """
        pass_json_path = segment_dir / "pass.json"
        reference_dir = segment_dir / "【参考】"
        
        logger.info(f"\n--- 处理段落: {segment_dir.name} ---")
        
        # 检查pass.json是否存在
        if not pass_json_path.exists():
            logger.warning(f"⚠️ 未找到pass.json文件: {pass_json_path}")
            return
            
        # 检查【参考】目录是否存在
        if not reference_dir.exists():
            logger.warning(f"⚠️ 未找到【参考】目录: {reference_dir}")
            return
            
        try:
            # 读取pass.json文件
            with open(pass_json_path, 'r', encoding='utf-8') as f:
                pass_data = json.load(f)
                
            passed_videos = pass_data.get('passed_videos', [])
            
            if not passed_videos:
                logger.info(f"📭 {segment_dir.name}: 没有通过匹配的视频")
                return
                
            logger.info(f"📋 找到 {len(passed_videos)} 个通过匹配的视频")
            
            # 移动每个通过匹配的视频
            for video_info in passed_videos:
                self.move_single_video(segment_dir, reference_dir, video_info)
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ pass.json格式错误: {e}")
            self.error_count += 1
        except Exception as e:
            logger.error(f"❌ 处理段落时出错: {e}")
            self.error_count += 1
    
    def move_single_video(self, segment_dir: Path, reference_dir: Path, video_info: Dict[str, Any]) -> None:
        """
        移动单个视频文件
        
        Args:
            segment_dir (Path): 段落目录
            reference_dir (Path): 参考目录
            video_info (Dict[str, Any]): 视频信息
        """
        video_filename = video_info.get('video_file_name', '')
        match_score = video_info.get('match_score', 0)
        match_reason = video_info.get('match_reason', '')
        
        if not video_filename:
            logger.warning("⚠️ 视频文件名为空，跳过")
            return
            
        source_path = reference_dir / video_filename
        destination_path = segment_dir / video_filename
        
        try:
            if not source_path.exists():
                logger.warning(f"⚠️ 【参考】中未找到文件: {video_filename}")
                self.operation_log.append(f"未找到: {video_filename}")
                return
                
            if destination_path.exists():
                # 目标文件已存在，删除【参考】中的重复文件
                source_path.unlink()
                logger.debug(f"🗑️ 删除【参考】中的重复文件: {video_filename}")
                self.operation_log.append(f"删除重复: {video_filename}")
            else:
                # 移动文件到段落根目录
                shutil.move(str(source_path), str(destination_path))
                logger.info(f"⭐ 移动成功: {video_filename} (分数: {match_score:.2f})")
                self.operation_log.append(f"移动成功: {video_filename} (分数: {match_score:.2f})")
                self.moved_count += 1
                
                # 显示匹配原因（如果有的话）
                if match_reason:
                    logger.debug(f"   📝 匹配原因: {match_reason[:50]}...")
                    
        except Exception as e:
            logger.error(f"❌ 移动文件失败 {video_filename}: {e}")
            self.operation_log.append(f"移动失败: {video_filename} - {e}")
            self.error_count += 1
    
    def show_summary(self) -> None:
        """显示移动操作的总结"""
        logger.info(f"\n" + "="*60)
        logger.info(f"📊 移动操作总结")
        logger.info(f"="*60)
        logger.info(f"✅ 成功移动: {self.moved_count} 个视频")
        logger.info(f"❌ 操作失败: {self.error_count} 个")
        logger.info(f"📝 总操作数: {len(self.operation_log)}")
        
        if self.operation_log:
            logger.info(f"\n📋 详细操作记录:")
            for i, operation in enumerate(self.operation_log[:10], 1):  # 只显示前10个
                logger.info(f"  {i}. {operation}")
            if len(self.operation_log) > 10:
                logger.info(f"  ... 还有 {len(self.operation_log) - 10} 个操作")
        
        logger.info(f"="*60)

def main():
    """主函数"""
    print("🔧 手动移动脚本 - 基于pass.json执行文件移动")
    print("="*60)
    
    # 获取输出目录
    output_dir = input("请输入输出目录路径 (默认: data/output): ").strip()
    if not output_dir:
        output_dir = "data/output"
    
    # 确认操作
    print(f"\n📁 目标目录: {output_dir}")
    confirm = input("确认开始移动操作？(y/N): ").strip().lower()
    
    if confirm != 'y':
        print("👋 操作已取消")
        return
    
    # 执行移动操作
    mover = ManualMover(output_dir)
    mover.process_all_segments()
    
    print(f"\n🎉 移动操作完成！详细日志已保存到 manual_move.log")

if __name__ == "__main__":
    main() 