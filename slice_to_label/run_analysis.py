#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频片段标签分析脚本 - 🍭Origin驱动架构
从🎬Slice目录读取切片文件进行AI分析

使用示例:
python run_analysis.py                      # 分析所有视频的切片
python run_analysis.py --video video_1     # 分析特定视频的切片
python run_analysis.py --help              # 查看帮助
"""

import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# 自动加载环境变量
try:
    from dotenv import load_dotenv  # type: ignore
    # 尝试从多个位置加载.env文件
    env_paths = [
        Path(__file__).parent / '.env',  # 当前目录
        Path(__file__).parent / 'config' / '.env',  # config目录
        Path(__file__).parent.parent / '.env',  # 父目录
    ]
    
    env_loaded = False
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ 已加载环境变量: {env_path}")
            env_loaded = True
            break
    
    if not env_loaded:
        print("⚠️ 未找到.env文件，将使用系统环境变量")
        
except ImportError:
    print("⚠️ python-dotenv未安装，将使用系统环境变量")

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入AI分析器
from src.ai_analyzers import DualStageAnalyzer

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

def _has_existing_analysis_json(video_file: str) -> bool:
    """检查视频文件是否已有对应的JSON分析文件"""
    video_path = Path(video_file)
    
    # 生成对应的JSON文件名
    video_stem = video_path.stem
    # 清理文件名中的♻️符号
    clean_stem = video_stem.replace("♻️", "")
    
    # 构建JSON文件路径
    json_file_path = video_path.parent / f"{clean_stem}_analysis.json"
    
    # 检查JSON文件是否存在
    return json_file_path.exists()

def scan_slice_directories(slice_dir: Path) -> Dict[str, Dict[str, List[str]]]:
    """扫描🎬Slice目录中的视频切片文件，并过滤无效文件"""
    video_slices = {}
    
    if not slice_dir.exists():
        print(f"⚠️  🎬Slice目录不存在: {slice_dir}")
        return video_slices
    
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.m4v']
    
    def _should_filter_video_file(file_path: Path) -> bool:
        """判断视频文件是否应该被过滤"""
        # 🎯 用户反馈：多镜头视频也应该被分析，只过滤真正失败的文件
        # 只过滤❌前缀的文件（分析失败），♻️文件允许正常分析
        if file_path.stem.startswith("❌"):
            return True
        return False
    
    filtered_count = 0  # 过滤文件计数
    
    for video_dir in slice_dir.iterdir():
        if video_dir.is_dir():
            video_name = video_dir.name
            video_slices[video_name] = {
                'slices': [],
                'product': []
            }
            
            # 扫描slices目录
            slices_dir = video_dir / "slices"
            if slices_dir.exists():
                for slice_file in slices_dir.iterdir():
                    if slice_file.is_file() and slice_file.suffix.lower() in video_extensions:
                        # 🚨 新增：过滤逻辑
                        if _should_filter_video_file(slice_file):
                            filtered_count += 1
                            print(f"🚫 过滤视频文件: {slice_file.name} (质量问题)")
                            continue
                        video_slices[video_name]['slices'].append(str(slice_file))
            
            # 扫描product目录
            product_dir = video_dir / "product"
            if product_dir.exists():
                for product_file in product_dir.iterdir():
                    if product_file.is_file() and product_file.suffix.lower() in video_extensions:
                        # 🚨 新增：过滤逻辑
                        if _should_filter_video_file(product_file):
                            filtered_count += 1
                            print(f"🚫 过滤视频文件: {product_file.name} (质量问题)")
                            continue
                        video_slices[video_name]['product'].append(str(product_file))
            
            total_files = len(video_slices[video_name]['slices']) + len(video_slices[video_name]['product'])
            if total_files > 0:
                print(f"🎬 发现视频: {video_name} ({len(video_slices[video_name]['slices'])} 切片, {len(video_slices[video_name]['product'])} 产品)")
    
    if filtered_count > 0:
        print(f"🚫 在视觉分析阶段已过滤 {filtered_count} 个失败的视频文件（仅❌前缀）")
        print(f"🎬 多镜头视频（♻️前缀）已允许正常分析，不再自动跳过")
    
    return video_slices

def save_individual_analysis_result(slice_dir: Path, video_name: str, slice_type: str, file_path: str, result: Dict[str, Any], is_failed: bool = False):
    """为每个切片保存独立的分析结果文件"""
    try:
        # 将文件路径转换为Path对象
        file_info = Path(file_path)
        
        # 🔧 修复：确保文件存在性检查在重命名前进行
        if not file_info.exists():
            # 如果文件不存在，尝试查找带♻️前缀的文件
            potential_multi_scene_file = file_info.parent / f"♻️{file_info.name}"
            if potential_multi_scene_file.exists():
                file_info = potential_multi_scene_file
                file_path = str(file_info)
                logger.info(f"🔍 找到多场景文件: {file_info.name}")
            else:
                logger.error(f"❌ 文件不存在: {file_path}")
                # 如果文件确实不存在，标记为失败
                result["error"] = f"[Errno 2] No such file or directory: '{file_path}'"
                is_failed = True
        
        # 确定保存目录
        if slice_type == "slices":
            output_dir = slice_dir / video_name / "slices"
        elif slice_type == "direct":
            # 🆕 支持直接目录结构
            output_dir = slice_dir / video_name
        else:  # product
            output_dir = slice_dir / video_name / "product"
        
        # 确保目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 🆕 多场景检测标记（仅在文件存在且分析成功时进行）
        # 🎯 用户反馈：多镜头视频也应该被分析，不应该直接跳过
        # 因此注释掉自动重命名逻辑，让多镜头视频正常进行后续分析
        should_rename_mp4 = False
        original_file_info = file_info

        # 🚫 注释掉自动重命名逻辑 - 让多镜头视频正常分析
        # if not is_failed and file_info.exists() and result.get("is_multi_scene", False):
        #     # 检查MP4文件是否已经有♻️前缀
        #     if not file_info.name.startswith("♻️"):
        #         should_rename_mp4 = True
        #         logger.info(f"♻️ 检测到多场景视频，标记为重命名: {file_info.name}")

        # 🎯 新逻辑：多镜头视频保持原文件名，正常进行后续分析
        if not is_failed and file_info.exists() and result.get("is_multi_scene", False):
            logger.info(f"🎬 检测到多场景视频，保持原文件名继续分析: {file_info.name}")
            logger.info(f"📊 场景数量: {result.get('scene_count', 1)}")
            logger.info(f"�� 多场景描述: {result.get('object', '未知')}")
        
        # 生成与切片文件名一致的分析文件名（JSON文件保持正常命名）
        slice_name = file_info.stem  # 去掉扩展名
        
        # 🆕 清理文件名中的♻️符号用于JSON文件命名
        clean_slice_name = slice_name.replace("♻️", "")
        
        # 🆕 文件名前缀逻辑（只针对失败的JSON文件）
        if is_failed:
            analysis_filename = f"❌{clean_slice_name}_analysis.json"
        else:
            analysis_filename = f"{clean_slice_name}_analysis.json"
        
        analysis_file_path = output_dir / analysis_filename
        
        # 🆕 延迟执行MP4重命名（在JSON保存前，只有在文件存在时）
        final_file_path = file_path
        final_file_name = file_info.name
        if should_rename_mp4 and file_info.exists():
            try:
                # 构建新的MP4文件名
                new_mp4_name = f"♻️{original_file_info.name}"
                new_mp4_path = original_file_info.parent / new_mp4_name
                
                # 检查新文件名是否已存在
                if not new_mp4_path.exists():
                    # 重命名MP4文件
                    original_file_info.rename(new_mp4_path)
                    logger.info(f"♻️ 多场景MP4已重命名: {original_file_info.name} → {new_mp4_name}")
                    
                    # 更新最终的文件路径和名称
                    final_file_path = str(new_mp4_path)
                    final_file_name = new_mp4_name
                else:
                    logger.info(f"♻️ 多场景文件已存在，跳过重命名: {new_mp4_name}")
                    # 使用已存在的多场景文件
                    final_file_path = str(new_mp4_path)
                    final_file_name = new_mp4_name
                
            except Exception as rename_error:
                logger.warning(f"⚠️ MP4文件重命名失败: {rename_error}")
                # 重命名失败时使用原始路径
                final_file_path = file_path
                final_file_name = file_info.name

        # 构建分析结果
        analysis_result = {
            "object": result.get("object", "未知"),
            "scene": result.get("scene", "未知"),
            "emotion": result.get("emotion", "未知"),
            "brand_elements": result.get("brand_elements", "无"),
            "success": result.get("success", False),
            "file_path": final_file_path,  # 🆕 使用最终的文件路径（可能包含♻️）
            "file_name": final_file_name,  # 🆕 使用最终的文件名（可能包含♻️）
            "video_name": video_name,
            "slice_type": slice_type,
            "file_size_mb": round(Path(final_file_path).stat().st_size / (1024 * 1024), 2) if Path(final_file_path).exists() else 0.0,
            "confidence": result.get("confidence", 0.0),
            "processed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "analysis_method": result.get("analysis_method", "unknown"),
            # 🆕 新增质量控制字段
            "quality_status": result.get("quality_status", "failed" if is_failed else "valid"),
            "invalid_reason": result.get("invalid_reason", None),
            # 🆕 重试相关信息
            "retry_count": result.get("retry_count", 0),
            "final_error": result.get("error", None) if is_failed else None,
            # 🆕 多场景相关信息
            "is_multi_scene": result.get("is_multi_scene", False),
            "scene_count": result.get("scene_count", 1)
        }
        
        # 如果有错误信息，添加到结果中
        if "stage2_error" in result:
            analysis_result["stage2_error"] = result["stage2_error"]
        
        # 保存分析结果
        with open(analysis_file_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        # 🆕 区分不同类型的打印信息
        if is_failed:
            print(f"📁 ❌{analysis_filename}")
        elif result.get("is_multi_scene", False):
            scene_count = result.get("scene_count", 1)
            print(f"📁 {analysis_filename} (🎬多镜头:{scene_count}个场景)")
        else:
            print(f"📁 {analysis_filename}")
        return str(analysis_file_path)
        
    except Exception as e:
        logger.error(f"保存分析结果失败 {file_path}: {str(e)}")
        return None

def analyze_with_retry(analyzer, video_file: str, analysis_type: str, max_retries: int = 2) -> Dict[str, Any]:
    """带重试机制的视频分析功能 - 优化版本"""
    retry_count = 0
    last_error = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 第 {attempt + 1}/{max_retries} 次尝试分析: {Path(video_file).name}")
            
            # 执行分析（现在Qwen内部已有5次重试机制）
            result = analyzer.analyze_video_slice(video_file, analysis_type)
            
            if result.get("success"):
                # 成功则记录重试次数并返回
                result["retry_count"] = retry_count
                logger.info(f"✅ 分析成功 (尝试次数: {attempt + 1})")
                return result
            else:
                # 分析失败，记录错误并准备重试
                error_msg = result.get("error", "未知错误")
                logger.warning(f"⚠️ 第 {attempt + 1} 次尝试失败: {error_msg}")
                last_error = error_msg
                retry_count += 1
                
                # 🔧 优化：减少上层重试，让内部重试机制发挥主要作用
                # 只有系统级错误（如文件不存在、权限问题）才需要上层重试
                if "API超时" in error_msg or "网络" in error_msg:
                    logger.info("🎯 检测到网络问题，Qwen内部重试机制已处理，跳过上层重试")
                    break
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3  # 增加等待时间: 3s, 6s
                    logger.info(f"⏳ 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                
        except Exception as e:
            error_msg = f"分析异常: {str(e)}"
            logger.error(f"❌ 第 {attempt + 1} 次尝试异常: {error_msg}")
            last_error = error_msg
            retry_count += 1
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                logger.info(f"⏳ 异常后等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
    
    # 所有重试都失败了
    logger.error(f"❌ 所有 {max_retries} 次重试都失败")
    return {
        "success": False,
        "error": last_error or "所有重试都失败",
        "retry_count": retry_count,
        "object": "analysis failed",
        "scene": "unknown scene",
        "emotion": "unknown emotion",
        "brand_elements": "none",
        "confidence": 0.0,
        "analysis_method": "failed_after_retries"
    }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="视频片段标签分析 - 🍭Origin驱动架构",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🍭Origin驱动架构说明:
  输入: 🎬Slice/{视频名}/slices/ + 🎬Slice/{视频名}/product/
  输出: 🎬Slice/{视频名}/slices/{切片名}_analysis.json
       🎬Slice/{视频名}/product/{产品名}_analysis.json

使用示例:
  python run_analysis.py                      # 分析所有视频的语义切片 (默认)
  python run_analysis.py --video video_1     # 分析特定视频的语义切片
  python run_analysis.py --slice-type all    # 分析语义切片+产品切片
  python run_analysis.py --slice-type product # 仅分析产品切片
  python run_analysis.py --max-files 20      # 限制最大文件数
  python run_analysis.py --analysis-type enhanced # 使用增强分析（视觉+音频）

分析类型:
  - dual: 双层视觉识别 (默认，推荐)
  - enhanced: 双层视觉 + 音频增强分析

分析范围:
  - 语义切片 (slices/): 通用内容分析 (默认)
  - 产品切片 (product/): 品牌专用分析
  - 全部切片 (all): 语义切片 + 产品切片
        """
    )
    
    parser.add_argument(
        "--slice-dir", "-s",
        default="../🎬Slice",
        help="🎬Slice切片目录 (默认: ../🎬Slice)"
    )
    
    parser.add_argument(
        "--video", "-v",
        help="指定分析特定视频 (例如: video_1)"
    )
    
    parser.add_argument(
        "--slice-type", "-t",
        choices=["slices", "product", "all"],
        default="slices",
        help="切片类型 (默认: slices)"
    )
    
    parser.add_argument(
        "--analysis-type", "-a",
        choices=["dual", "enhanced"],
        default="dual",
        help="分析类型: dual=双层视觉, enhanced=视觉+音频 (默认: dual)"
    )
    
    parser.add_argument(
        "--max-files",
        type=int,
        help="最大处理文件数"
    )
    
    args = parser.parse_args()
    
    try:
        print("🎯 视频片段标签分析 - 🍭Origin驱动架构")
        print("=" * 60)
        
        # 初始化AI分析器
        print("🤖 初始化AI分析器...")
        analyzer = DualStageAnalyzer()
        
        # 设置路径
        current_dir = Path(__file__).parent
        slice_dir = Path(args.slice_dir)
        if not slice_dir.is_absolute():
            slice_dir = current_dir / slice_dir
        
        print(f"🎬 切片目录: {slice_dir}")
        
        # 扫描切片文件
        print("🔍 扫描切片文件...")
        video_slices = scan_slice_directories(slice_dir)
        
        if not video_slices:
            print("❌ 未在🎬Slice中找到切片文件")
            return 1
        
        # 过滤指定视频
        if args.video:
            if args.video in video_slices:
                video_slices = {args.video: video_slices[args.video]}
                print(f"🎯 分析指定视频: {args.video}")
            else:
                print(f"❌ 未找到指定视频: {args.video}")
                print(f"可用视频: {', '.join(video_slices.keys())}")
                return 1
        
        # 收集所有要分析的文件
        all_files = []
        for video_name, slice_data in video_slices.items():
            if args.slice_type in ["slices", "all"]:
                for slice_file in slice_data['slices']:
                    all_files.append((slice_file, "slices", video_name))
            if args.slice_type in ["product", "all"]:
                for product_file in slice_data['product']:
                    all_files.append((product_file, "product", video_name))
        
        if not all_files:
            print("❌ 未找到匹配的切片文件")
            return 1
        
        # 限制文件数量
        if args.max_files:
            all_files = all_files[:args.max_files]
        
        print(f"📋 总计发现 {len(all_files)} 个切片文件")
        print(f"📊 切片类型: {args.slice_type}")
        print(f"🤖 分析类型: {args.analysis_type}")
        print(f"📁 输出模式: 独立文件保存 (每个切片一个分析文件)")
        print("=" * 60)
        
        # 处理文件
        successful_files = []
        failed_files = []
        skipped_files = []  # 新增：跳过的文件统计
        
        for i, (video_file, slice_type, video_name) in enumerate(all_files, 1):
            file_name = Path(video_file).name
            print(f"🎬 处理进度: {i}/{len(all_files)} - {file_name}")
            
            # 🆕 检查是否已有JSON分析文件
            if _has_existing_analysis_json(video_file):
                print(f"⏭️  跳过已分析文件: {file_name}")
                skipped_files.append({
                    "file_name": file_name,
                    "video_name": video_name,
                    "slice_type": slice_type,
                    "reason": "已有JSON分析文件"
                })
                continue
            
            try:
                # 🆕 使用带重试机制的分析器进行分析
                result = analyze_with_retry(analyzer, video_file, args.analysis_type, max_retries=2)
                
                if result.get("success"):
                    # 保存成功的分析结果文件
                    analysis_file = save_individual_analysis_result(
                        slice_dir, video_name, slice_type, video_file, result, is_failed=False
                    )
                    
                    if analysis_file:
                        successful_files.append({
                            "video_name": video_name,
                            "slice_type": slice_type,
                            "file_name": file_name,
                            "analysis_file": analysis_file,
                            "confidence": result.get("confidence", 0),
                            "object": result.get("object", ""),
                            "scene": result.get("scene", ""),
                            "emotion": result.get("emotion", ""),
                            "brand_elements": result.get("brand_elements", "无"),
                            "success": True,
                            "file_path": str(video_file),
                            "file_size_mb": round(Path(video_file).stat().st_size / (1024 * 1024), 2),
                            "processed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                            "analysis_method": result.get("analysis_method", "unknown"),
                            "retry_count": result.get("retry_count", 0)
                        })
                        logger.info(f"✅ 已分析: {video_name}/{slice_type}/{file_name} (重试: {result.get('retry_count', 0)} 次)")
                    else:
                        failed_files.append({
                            "file_name": file_name,
                            "error": "保存分析结果失败"
                        })
                else:
                    # 🆕 所有重试都失败，保存失败标记的文件
                    analysis_file = save_individual_analysis_result(
                        slice_dir, video_name, slice_type, video_file, result, is_failed=True
                    )
                    
                    failed_files.append({
                        "file_name": file_name,
                        "error": result.get("error", "AI分析失败"),
                        "retry_count": result.get("retry_count", 0),
                        "analysis_file": analysis_file
                    })
                    logger.error(f"❌ 最终分析失败: {file_name} - {result.get('error', '未知错误')} (重试: {result.get('retry_count', 0)} 次)")
                    
            except Exception as e:
                # 🆕 异常情况也保存失败文件
                error_result = {
                    "success": False,
                    "error": str(e),
                    "retry_count": 0,
                    "object": "analysis failed",
                    "scene": "unknown scene", 
                    "emotion": "unknown emotion",
                    "brand_elements": "none",
                    "confidence": 0.0,
                    "analysis_method": "exception_occurred"
                }
                
                analysis_file = save_individual_analysis_result(
                    slice_dir, video_name, slice_type, video_file, error_result, is_failed=True
                )
                
                failed_files.append({
                    "file_name": file_name,
                    "error": str(e),
                    "retry_count": 0,
                    "analysis_file": analysis_file
                })
                logger.error(f"❌ 处理异常: {file_name} - {str(e)}")
        
        # 生成统计信息
        video_stats = {}
        slice_type_stats = {"slices": 0, "product": 0}
        
        for result in successful_files:
            video_name = result["video_name"]
            slice_type = result["slice_type"]
            
            if video_name not in video_stats:
                video_stats[video_name] = {"slices": 0, "product": 0}
            
            video_stats[video_name][slice_type] += 1
            if slice_type in slice_type_stats:
                slice_type_stats[slice_type] += 1
        
        # 显示总结
        print("\n" + "=" * 60)
        print("📊 分析完成统计:")
        print(f"📋 总文件数: {len(all_files)}")
        print(f"✅ 成功文件: {len(successful_files)}")
        print(f"❌ 失败文件: {len(failed_files)}")
        print(f"⏭️  跳过文件: {len(skipped_files)}")
        total_processed = len(successful_files) + len(failed_files)
        print(f"📈 成功率: {len(successful_files)/total_processed*100:.1f}%" if total_processed > 0 else "0%")
        
        if skipped_files:
            print(f"\n⏭️  跳过文件统计:")
            print(f"📋 跳过文件数: {len(skipped_files)}")
            print("🎯 跳过原因: 已有JSON分析文件")
            print("💡 跳过的文件列表:")
            for skipped in skipped_files[:10]:  # 显示前10个
                print(f"  ✓ {skipped['file_name']}")
            if len(skipped_files) > 10:
                print(f"  ... 还有 {len(skipped_files) - 10} 个已跳过文件")
        
        print(f"\n📊 按视频统计:")
        for video_name, stats in video_stats.items():
            total = stats["slices"] + stats["product"]
            print(f"  🎬 {video_name}: {total} 个 (切片:{stats['slices']}, 产品:{stats['product']})")
        
        print(f"\n📊 按类型统计:")
        print(f"  🎬 语义切片: {slice_type_stats['slices']} 个")
        print(f"  🎯 产品切片: {slice_type_stats['product']} 个")
        
        if failed_files:
            print(f"\n❌ 失败文件列表:")
            for failed in failed_files[:5]:  # 只显示前5个
                retry_info = f" (重试: {failed.get('retry_count', 0)} 次)" if 'retry_count' in failed else ""
                print(f"  - {failed['file_name']}: {failed['error']}{retry_info}")
            if len(failed_files) > 5:
                print(f"  ... 还有 {len(failed_files) - 5} 个失败文件")
        
        print(f"\n📁 每个切片的分析结果已保存为独立文件")
        print(f"📄 成功文件命名格式: {{切片名}}_analysis.json")
        print(f"📄 失败文件命名格式: ❌{{切片名}}_analysis.json")
        print(f"🔄 重试机制: 最多3次重试，递增等待时间 (2s, 4s, 6s)")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"💥 程序异常: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 