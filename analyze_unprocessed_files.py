#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
未分析文件检测和处理脚本
功能：
1. 扫描🎬Slice目录中的所有视频文件
2. 检测哪些文件没有成功分析（没有有效的analysis.json文件）
3. 将未分析的文件移动到"未分析"文件夹
4. 修复多场景文件名映射问题
"""

import os
import json
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Optional
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UnprocessedFileAnalyzer:
    """未分析文件分析器"""
    
    def __init__(self, slice_dir: str = "🎬Slice"):
        self.slice_dir = Path(slice_dir)
        self.unprocessed_dir = Path("🎬Slice/未分析")
        self.video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.m4v']
        
    def analyze_all_files(self) -> Dict[str, Any]:
        """分析所有文件的处理状态"""
        logger.info("🔍 开始分析文件处理状态...")
        
        results = {
            "total_videos": 0,
            "successfully_analyzed": 0,
            "failed_analysis": 0,
            "no_analysis": 0,
            "file_name_issues": 0,
            "unprocessed_files": [],
            "failed_files": [],
            "name_mapping_issues": [],
            "summary_by_video": {}
        }
        
        # 扫描所有视频目录
        for video_dir in self.slice_dir.iterdir():
            if not video_dir.is_dir() or video_dir.name == "未分析":
                continue
                
            video_name = video_dir.name
            logger.info(f"📁 分析视频目录: {video_name}")
            
            video_stats = self._analyze_video_directory(video_dir)
            results["summary_by_video"][video_name] = video_stats
            
            # 累积统计
            results["total_videos"] += video_stats["total_files"]
            results["successfully_analyzed"] += video_stats["success_count"]
            results["failed_analysis"] += video_stats["failed_count"]
            results["no_analysis"] += video_stats["no_analysis_count"]
            results["file_name_issues"] += video_stats["name_issues_count"]
            
            # 收集问题文件
            results["unprocessed_files"].extend(video_stats["unprocessed_files"])
            results["failed_files"].extend(video_stats["failed_files"])
            results["name_mapping_issues"].extend(video_stats["name_mapping_issues"])
        
        return results
    
    def _analyze_video_directory(self, video_dir: Path) -> Dict[str, Any]:
        """分析单个视频目录"""
        stats = {
            "total_files": 0,
            "success_count": 0,
            "failed_count": 0,
            "no_analysis_count": 0,
            "name_issues_count": 0,
            "unprocessed_files": [],
            "failed_files": [],
            "name_mapping_issues": []
        }
        
        # 检查slices子目录
        slices_dir = video_dir / "slices"
        if slices_dir.exists():
            self._analyze_slices_directory(slices_dir, video_dir.name, stats)
        else:
            # 检查直接在视频目录下的文件
            self._analyze_direct_directory(video_dir, video_dir.name, stats)
        
        return stats
    
    def _analyze_slices_directory(self, slices_dir: Path, video_name: str, stats: Dict[str, Any]):
        """分析slices子目录"""
        # 收集所有视频文件
        video_files = []
        for file_path in slices_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.video_extensions:
                video_files.append(file_path)
        
        stats["total_files"] = len(video_files)
        
        # 分析每个视频文件
        for video_file in video_files:
            self._analyze_single_video_file(video_file, video_name, stats)
    
    def _analyze_direct_directory(self, video_dir: Path, video_name: str, stats: Dict[str, Any]):
        """分析直接目录结构"""
        # 收集所有视频文件
        video_files = []
        for file_path in video_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.video_extensions:
                video_files.append(file_path)
        
        stats["total_files"] = len(video_files)
        
        # 分析每个视频文件
        for video_file in video_files:
            self._analyze_single_video_file(video_file, video_name, stats)
    
    def _analyze_single_video_file(self, video_file: Path, video_name: str, stats: Dict[str, Any]):
        """分析单个视频文件"""
        file_stem = video_file.stem
        
        # 清理文件名（移除♻️符号用于JSON文件匹配）
        clean_stem = file_stem.replace("♻️", "")
        
        # 寻找对应的分析文件
        analysis_file = video_file.parent / f"{clean_stem}_analysis.json"
        failed_analysis_file = video_file.parent / f"❌{clean_stem}_analysis.json"
        
        if analysis_file.exists():
            # 检查分析文件是否有效
            if self._is_valid_analysis_file(analysis_file):
                stats["success_count"] += 1
            else:
                stats["failed_count"] += 1
                stats["failed_files"].append({
                    "video_file": str(video_file),
                    "analysis_file": str(analysis_file),
                    "video_name": video_name,
                    "issue": "分析文件无效"
                })
        elif failed_analysis_file.exists():
            # 有失败标记的分析文件
            stats["failed_count"] += 1
            stats["failed_files"].append({
                "video_file": str(video_file),
                "analysis_file": str(failed_analysis_file),
                "video_name": video_name,
                "issue": "分析失败"
            })
        else:
            # 完全没有分析文件
            stats["no_analysis_count"] += 1
            stats["unprocessed_files"].append({
                "video_file": str(video_file),
                "video_name": video_name,
                "issue": "无分析文件"
            })
        
        # 检查文件名映射问题
        if file_stem.startswith("♻️"):
            # 多场景文件，检查是否有原始名称的JSON文件
            original_stem = file_stem[1:]  # 移除♻️
            original_analysis = video_file.parent / f"{original_stem}_analysis.json"
            if original_analysis.exists():
                stats["name_issues_count"] += 1
                stats["name_mapping_issues"].append({
                    "video_file": str(video_file),
                    "expected_json": str(analysis_file),
                    "actual_json": str(original_analysis),
                    "video_name": video_name,
                    "issue": "多场景文件名映射不一致"
                })
    
    def _is_valid_analysis_file(self, analysis_file: Path) -> bool:
        """检查分析文件是否有效"""
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查必要字段
            if not data.get("success", False):
                return False
            
            # 检查是否有有意义的内容
            object_val = data.get("object", "")
            if object_val in ["analysis failed", "未知", "", "unknown"]:
                return False
            
            return True
        except Exception as e:
            logger.warning(f"⚠️ 无法读取分析文件 {analysis_file}: {e}")
            return False
    
    def move_unprocessed_files(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """移动未分析的文件到"未分析"文件夹"""
        logger.info("📦 开始移动未分析的文件...")
        
        # 创建未分析目录
        self.unprocessed_dir.mkdir(exist_ok=True)
        
        move_results = {
            "moved_files": 0,
            "failed_moves": 0,
            "moved_file_list": [],
            "move_errors": []
        }
        
        # 移动完全未分析的文件
        for unprocessed in analysis_result["unprocessed_files"]:
            try:
                src_file = Path(unprocessed["video_file"])
                dst_file = self.unprocessed_dir / src_file.name
                
                # 避免文件名冲突
                counter = 1
                original_dst = dst_file
                while dst_file.exists():
                    dst_file = original_dst.parent / f"{original_dst.stem}_{counter}{original_dst.suffix}"
                    counter += 1
                
                shutil.move(str(src_file), str(dst_file))
                move_results["moved_files"] += 1
                move_results["moved_file_list"].append({
                    "original": str(src_file),
                    "destination": str(dst_file),
                    "video_name": unprocessed["video_name"]
                })
                logger.info(f"📦 已移动: {src_file.name} → 未分析/")
                
            except Exception as e:
                move_results["failed_moves"] += 1
                move_results["move_errors"].append({
                    "file": unprocessed["video_file"],
                    "error": str(e)
                })
                logger.error(f"❌ 移动失败: {unprocessed['video_file']} - {e}")
        
        return move_results
    
    def fix_name_mapping_issues(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """修复文件名映射问题"""
        logger.info("🔧 开始修复文件名映射问题...")
        
        fix_results = {
            "fixed_count": 0,
            "failed_fixes": 0,
            "fixed_files": [],
            "fix_errors": []
        }
        
        for issue in analysis_result["name_mapping_issues"]:
            try:
                # 重命名JSON文件以匹配视频文件名
                old_json = Path(issue["actual_json"])
                new_json = Path(issue["expected_json"])
                
                if old_json.exists() and not new_json.exists():
                    shutil.move(str(old_json), str(new_json))
                    fix_results["fixed_count"] += 1
                    fix_results["fixed_files"].append({
                        "old_json": str(old_json),
                        "new_json": str(new_json),
                        "video_file": issue["video_file"]
                    })
                    logger.info(f"🔧 已修复映射: {old_json.name} → {new_json.name}")
                
            except Exception as e:
                fix_results["failed_fixes"] += 1
                fix_results["fix_errors"].append({
                    "issue": issue,
                    "error": str(e)
                })
                logger.error(f"❌ 修复失败: {issue['video_file']} - {e}")
        
        return fix_results
    
    def generate_report(self, analysis_result: Dict[str, Any], move_result: Optional[Dict[str, Any]] = None, fix_result: Optional[Dict[str, Any]] = None) -> str:
        """生成分析报告"""
        report_lines = [
            "=" * 80,
            "🔍 未分析文件检测和处理报告",
            f"⏰ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            "",
            "📊 总体统计:",
            f"  总视频文件数: {analysis_result['total_videos']}",
            f"  成功分析: {analysis_result['successfully_analyzed']} ({analysis_result['successfully_analyzed']/analysis_result['total_videos']*100:.1f}%)" if analysis_result['total_videos'] > 0 else "  成功分析: 0 (0%)",
            f"  分析失败: {analysis_result['failed_analysis']}",
            f"  完全未分析: {analysis_result['no_analysis']}",
            f"  文件名映射问题: {analysis_result['file_name_issues']}",
            "",
            "📁 按视频目录统计:",
        ]
        
        for video_name, stats in analysis_result["summary_by_video"].items():
            if stats["total_files"] > 0:
                success_rate = stats["success_count"] / stats["total_files"] * 100
                report_lines.append(f"  📹 {video_name}:")
                report_lines.append(f"    总文件: {stats['total_files']}, 成功: {stats['success_count']} ({success_rate:.1f}%)")
                report_lines.append(f"    失败: {stats['failed_count']}, 未分析: {stats['no_analysis_count']}, 名称问题: {stats['name_issues_count']}")
        
        if move_result:
            report_lines.extend([
                "",
                "📦 文件移动结果:",
                f"  成功移动: {move_result['moved_files']} 个文件",
                f"  移动失败: {move_result['failed_moves']} 个文件",
            ])
        
        if fix_result:
            report_lines.extend([
                "",
                "🔧 映射修复结果:",
                f"  成功修复: {fix_result['fixed_count']} 个问题",
                f"  修复失败: {fix_result['failed_fixes']} 个问题",
            ])
        
        report_lines.extend([
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="未分析文件检测和处理工具")
    parser.add_argument("--slice-dir", default="🎬Slice", help="切片目录路径")
    parser.add_argument("--move", action="store_true", help="移动未分析的文件到'未分析'文件夹")
    parser.add_argument("--fix-mapping", action="store_true", help="修复文件名映射问题")
    parser.add_argument("--report-file", help="保存报告到文件")
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = UnprocessedFileAnalyzer(args.slice_dir)
    
    # 分析所有文件
    logger.info("🚀 开始未分析文件检测...")
    analysis_result = analyzer.analyze_all_files()
    
    move_result = None
    fix_result = None
    
    # 修复文件名映射问题
    if args.fix_mapping:
        fix_result = analyzer.fix_name_mapping_issues(analysis_result)
    
    # 移动未分析文件
    if args.move:
        move_result = analyzer.move_unprocessed_files(analysis_result)
    
    # 生成报告
    report = analyzer.generate_report(analysis_result, move_result, fix_result)
    print(report)
    
    # 保存报告到文件
    if args.report_file:
        with open(args.report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"📄 报告已保存到: {args.report_file}")
    
    # 显示建议
    if analysis_result["no_analysis"] > 0 or analysis_result["failed_analysis"] > 0:
        print("\n💡 建议操作:")
        if analysis_result["no_analysis"] > 0:
            print(f"  1. 运行 python analyze_unprocessed_files.py --move 将 {analysis_result['no_analysis']} 个未分析文件移到'未分析'文件夹")
        if analysis_result["file_name_issues"] > 0:
            print(f"  2. 运行 python analyze_unprocessed_files.py --fix-mapping 修复 {analysis_result['file_name_issues']} 个文件名映射问题")
        if analysis_result["failed_analysis"] > 0:
            print(f"  3. 检查 {analysis_result['failed_analysis']} 个分析失败的文件，考虑重新处理")

if __name__ == "__main__":
    main() 