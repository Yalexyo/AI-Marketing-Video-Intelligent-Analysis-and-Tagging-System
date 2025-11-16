#!/usr/bin/env python3
"""
🚀 快速运行脚本 - 主标签处理器
提供简化的接口快速执行主标签分类任务和动态聚类
新增: 🚀 增强聚类管理器 - 端到端处理架构优化
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

# 添加当前目录到路径
sys.path.append(str(Path(__file__).parent))

# 导入统一处理器
from src.unified_processing_manager import UnifiedProcessingManager
from src.slice_file_manager import SliceFileManager

def _should_filter_file_for_clustering(json_file: Path, json_data: Dict[str, Any]) -> bool:
    """
    判断文件是否需要过滤（用于聚类分析）
    
    Args:
        json_file: JSON文件路径
        json_data: JSON数据内容
        
    Returns:
        bool: 是否需要过滤
    """
    # 🎯 用户反馈：多镜头视频也应该被分析，只过滤真正失败的文件
    # 只过滤❌前缀的文件（分析失败），♻️文件允许正常分析
    if json_file.stem.startswith("❌"):
        return True
    
    # 检查quality_status是否为failed
    if json_data.get("quality_status") == "failed":
        return True
    
    # 检查success字段是否为false
    if json_data.get("success") == False:
        return True
    
    # 检查文件路径是否包含❌标记（♻️标记允许通过）
    file_path = json_data.get("file_path", "")
    if isinstance(file_path, str) and "❌" in file_path:
        return True
    
    return False

def run_ai_clustering_analysis_only():
    """🤖 双层AI智能聚类 - 仅分析模式（不复制文件）"""
    print("🤖 启动双层AI智能聚类分析器 - 仅分析模式...")
    print("🧠 双层AI架构：主标签AI + 子类别AI")
    print("📊 只增强JSON文件，不复制文件")
    try:
        from src.secondary_ai_classifier import SecondaryAIClassifier
        from src.slice_file_manager import SliceFileManager  # 🔧 导入SliceFileManager
        
        classifier = SecondaryAIClassifier()
        file_manager = SliceFileManager()  # 🔧 创建文件管理器实例
        
        # 从🎬Slice目录加载已分类的数据
        slice_files = []
        slice_dir = Path("../🎬Slice")
        
        for video_dir in slice_dir.iterdir():
            if video_dir.is_dir() and video_dir.name not in [".", "..", "🎬Slice"] and not video_dir.name.startswith("."):
                # 支持灵活的文件夹结构：既支持slices子目录，也支持直接在目录下
                json_files_found = []
                
                # 方法1: 检查slices子目录
                slices_dir = video_dir / "slices"
                if slices_dir.exists():
                    json_files_found.extend(list(slices_dir.glob("*_analysis.json")))
                
                # 方法2: 检查直接在目录下
                if not json_files_found:
                    json_files_found.extend(list(video_dir.glob("*_analysis.json")))
                
                slice_files.extend(json_files_found)
        
        if not slice_files:
            print("❌ 未找到已分析的JSON文件")
            return None
        
        print(f"📋 发现 {len(slice_files)} 个已分析的JSON文件")
        
        # 按主标签分组处理
        import json
        main_tag_groups = {}
        filtered_count = 0  # 🆕 新增：过滤文件计数
        
        for json_file in slice_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 🚨 新增：质量过滤逻辑
                if _should_filter_file_for_clustering(json_file, data):
                    filtered_count += 1
                    print(f"🚫 过滤文件: {json_file.name} (质量问题)")
                    continue
                
                main_tag = data.get("main_tag", "")
                if main_tag and "其他" not in main_tag:
                    if main_tag not in main_tag_groups:
                        main_tag_groups[main_tag] = []
                    
                    # 🔧 修复：使用智能路径解析方法
                    resolved_file_path = file_manager._resolve_valid_video_file_path(json_file, data)
                    
                    # 构建slice_data格式
                    slice_data = {
                        "slice_name": json_file.stem.replace("_analysis", ""),
                        "labels": f"object: {data.get('object', '')}, scene: {data.get('scene', '')}, emotion: {data.get('emotion', '')}, brand_elements: {data.get('brand_elements', '')}",
                        "file_path": resolved_file_path,
                        "analysis_file": str(json_file),
                        "confidence": data.get("confidence", 0.0)
                    }
                    main_tag_groups[main_tag].append(slice_data)
            except Exception as e:
                print(f"⚠️ 读取文件失败 {json_file}: {e}")
                continue
        
        if filtered_count > 0:
            print(f"🚫 已过滤 {filtered_count} 个质量问题文件")
        
        # 对每个主标签组进行二级AI分析
        total_processed = 0
        total_enhanced = 0
        
        for main_tag, slice_list in main_tag_groups.items():
            print(f"\n🎯 处理主标签: {main_tag} ({len(slice_list)} 个文件)")
            
            # 执行二级AI分类
            enriched_results = classifier.batch_classify_secondary(
                slice_list, main_tag, min_confidence=0.5
            )
            
            # 将结果写回原JSON文件
            for enriched_slice in enriched_results:
                analysis_file = enriched_slice.get("analysis_file")
                if analysis_file and Path(analysis_file).exists():
                    try:
                        # 读取原JSON
                        with open(analysis_file, 'r', encoding='utf-8') as f:
                            original_data = json.load(f)
                        
                        # 添加二级分析字段
                        if "secondary_category" in enriched_slice:
                            original_data.update({
                                "secondary_category": enriched_slice["secondary_category"],
                                "secondary_confidence": enriched_slice["secondary_confidence"],
                                "secondary_reasoning": enriched_slice.get("secondary_reasoning", ""),
                                "secondary_features": enriched_slice.get("secondary_features", []),
                                "secondary_processed_at": enriched_slice.get("secondary_processed_at", "")
                            })
                            
                            # 写回文件
                            with open(analysis_file, 'w', encoding='utf-8') as f:
                                json.dump(original_data, f, ensure_ascii=False, indent=2)
                            
                            total_enhanced += 1
                        
                        total_processed += 1
                        
                    except Exception as e:
                        print(f"⚠️ 更新文件失败 {analysis_file}: {e}")
        
        print(f"\n✅ 二级AI分析完成!")
        print(f"📊 处理 {total_processed} 个文件，成功增强 {total_enhanced} 个JSON文件")
        print(f"🎯 已添加 secondary_category, secondary_confidence 等字段")
        
        return {
            "total_processed": total_processed,
            "total_enhanced": total_enhanced,
            "main_tag_groups": list(main_tag_groups.keys())
        }
        
    except Exception as e:
        print(f"❌ 二级AI分析失败: {e}")
        return None

def run_overview():
    """运行处理概览 - 使用统一管理器"""
    print("📊 获取处理概览...")
    try:
        # 使用文件管理器获取概览信息
        file_manager = SliceFileManager()
        classified_data, unclassified_data = file_manager.collect_all_slice_data()
        
        # 获取处理统计信息
        stats = file_manager.get_processing_statistics()
        total_stats = stats.get("TOTAL", {})
        
        overview = {
            "total_videos": total_stats.get("total_videos", 0),
            "total_files": total_stats.get("total_files", 0),
            "classified_files": len(classified_data),
            "unclassified_files": len(unclassified_data),
            "processing_complete": True
        }
        
        print(f"📊 概览统计:")
        print(f"   🎬 总视频数: {overview['total_videos']}")
        print(f"   📋 总文件数: {overview['total_files']}")
        print(f"   🎯 已分类: {overview['classified_files']}")
        print(f"   🧫 未分类: {overview['unclassified_files']}")
        
        return overview
    except Exception as e:
        print(f"❌ 获取概览失败: {e}")
        return None

def run_single_video(video_name: str, force_reprocess: bool = False, no_backup: bool = False):
    """处理单个视频 - 使用统一管理器"""
    print(f"🎬 处理视频: {video_name}")
    print("⚠️ 建议使用统一智能分类模式 (run.py enhanced-cluster)")
    try:
        # 使用统一处理管理器进行单视频处理
        manager = UnifiedProcessingManager()
        
        # 构建输出目录
        from pathlib import Path
        from datetime import datetime
        output_dir = Path("../📁生成结果") / f"单视频处理_{video_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 执行统一智能分类
        result = manager.perform_unified_classification_and_clustering(
            force_reprocess=force_reprocess,
            output_base_dir=output_dir
        )
        
        if result:
            print(f"✅ 视频 {video_name} 处理完成")
            print(f"📁 生成 {len(result.main_modules)} 个主模块")
            print(f"📊 AI分析统计: {result.ai_analysis_stats}")
            return {"success": True, "video_name": video_name, "result": result}
        else:
            return {"success": False, "video_name": video_name}
            
    except Exception as e:
        print(f"❌ 处理视频失败: {e}")
        return {"success": False, "error": str(e)}

def run_all_videos(force_reprocess: bool = False, no_backup: bool = False):
    """处理所有视频 - 使用统一管理器"""
    print("🎬 批量处理所有视频...")
    print("⚠️ 建议使用统一智能分类模式 (run.py enhanced-cluster)")
    try:
        # 使用统一处理管理器
        manager = UnifiedProcessingManager()
        
        # 执行统一智能分类
        result = manager.perform_unified_classification_and_clustering(
            force_reprocess=force_reprocess
        )
        
        if result:
            print(f"✅ 批量处理完成")
            print(f"📁 生成 {len(result.main_modules)} 个主模块")
            print(f"📊 处理统计: {result.processing_stats}")
            print(f"🤖 AI分析统计: {result.ai_analysis_stats}")
            return {"success": True, "result": result}
        else:
            return {"success": False}
            
    except Exception as e:
        print(f"❌ 批量处理失败: {e}")
        return {"success": False, "error": str(e)}

def run_clustering(output_base_dir: Optional[str] = None):
    """执行动态聚类 - 使用增强聚类管理器"""
    print("🎯 执行动态聚类...")
    try:
        # 直接使用统一智能分类管理器
        return run_intelligent_classification(output_base_dir)
    except Exception as e:
        print(f"❌ 聚类失败: {e}")
        return None

def run_intelligent_classification(output_base_dir: Optional[str] = None, force_reprocess: bool = False):
    """🎯 统一智能分类模式 - 内存流式处理（架构优化版v4.0）"""
    print("🎯 启动统一智能分类管理器v4.0（架构优化版）...")
    print("🧠 双层AI架构：主标签AI + 子类别AI")
    print("⚡ 架构优化：内存流式处理，减少文件读写")
    try:
        from src.unified_processing_manager import UnifiedProcessingManager
        manager = UnifiedProcessingManager()
        
        # 设置输出目录
        if output_base_dir:
            output_dir = Path(output_base_dir)
        else:
            output_dir = None
        
        # 执行统一智能分类和聚类（内存流式处理）
        result = manager.perform_unified_classification_and_clustering(
            force_reprocess=force_reprocess,
            output_base_dir=output_dir
        )
        
        print("✅ 统一智能分类完成!")
        print(f"📁 生成 {len(result.main_modules)} 个主模块")
        print(f"🎯 处理 {sum(len(clusters) for clusters in result.main_modules.values())} 个聚类")
        print(f"📊 总计 {sum(c.slice_count for clusters in result.main_modules.values() for c in clusters)} 个切片")
        print(f"🤖 AI分析统计: {result.ai_analysis_stats}")
        print(f"📊 处理统计: {result.processing_stats}")
        
        # 显示详细的AI分析结果
        for main_tag, clusters in result.main_modules.items():
            print(f"   🎯 {main_tag}: {len(clusters)} 个AI智能子类别")
            for cluster in clusters:
                if hasattr(cluster, 'avg_secondary_confidence'):
                    print(f"      └─ {cluster.cluster_name}: {cluster.slice_count} 个切片 (AI置信度: {cluster.avg_secondary_confidence:.2f})")
                else:
                    print(f"      └─ {cluster.cluster_name}: {cluster.slice_count} 个切片")
        
        return result
    except Exception as e:
        print(f"❌ 统一智能分类失败: {e}")
        return None

def run_process_and_cluster(force_reprocess: bool = False, no_backup: bool = False, 
                           enable_clustering: bool = True, output_base_dir: Optional[str] = None):
    """一键处理：分类 + 聚类"""
    print("🚀 一键处理：主标签分类 + 动态聚类...")
    try:
        # 第一步：主标签分类
        print("📝 第一步：执行主标签分类...")
        classification_result = run_all_videos(force_reprocess, no_backup)
        
        if not classification_result or not classification_result.get("success"):
            print("❌ 分类步骤失败")
            return None
        
        print(f"✅ 分类完成: {classification_result['total_stats']}")
        
        # 第二步：聚类（如果启用）
        clustering_result = None
        if enable_clustering:
            print("🚀 第二步：执行动态聚类...")
            clustering_result = run_clustering(output_base_dir)
        
        return {
            "classification": classification_result,
            "clustering": clustering_result
        }
    except Exception as e:
        print(f"❌ 一键处理失败: {e}")
        return None

def run_enhanced_process_and_cluster(force_reprocess: bool = False, no_backup: bool = False, 
                                   output_base_dir: Optional[str] = None):
    """🚀 增强一键处理：分类 + 增强端到端聚类（架构优化版）"""
    print("🚀 增强一键处理：主标签分类 + 增强端到端聚类...")
    try:
        # 第一步：分类处理
        print("📝 第一步：执行主标签分类...")
        classification_result = run_all_videos(force_reprocess, no_backup)
        
        if not classification_result or not classification_result.get("success"):
            print("❌ 分类步骤失败")
            return None
        
        print(f"✅ 分类完成: {classification_result['total_stats']}")
        
        # 第二步：智能聚类
        print("🚀 第二步：执行统一智能分类...")
        clustering_result = run_intelligent_classification(output_base_dir, force_reprocess)
        
        if not clustering_result:
            print("❌ 聚类步骤失败")
            return None
        
        print("🎉 增强一键处理完成!")
        return {
            "classification": classification_result,
            "clustering": clustering_result
        }
        
    except Exception as e:
        print(f"❌ 增强一键处理失败: {e}")
        return None

def interactive_mode():
    """交互模式"""
    print("🎯 主标签处理器 - 交互模式")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 📊 查看处理概览")
        print("2. 🎬 处理单个视频")
        print("3. 🎬 处理所有视频")
        print("4. 🔄 强制重新处理单个视频")
        print("5. 🔄 强制重新处理所有视频")
        print("6. 🎯 执行动态聚类")
        print("7. 🚀 一键处理（分类+聚类）")
        print("8. 🔄 强制一键处理（分类+聚类）")
        print("9. 🎯 执行统一智能分类（架构优化版）")
        print("10. 🚀 增强一键处理（分类+智能聚类）")
        print("11. 📊 仅分析模式（增强JSON，不复制文件）")
        print("0. 🚪 退出")
        
        choice = input("\n请输入选择 (0-11): ").strip()
        
        if choice == "0":
            print("👋 再见!")
            break
        elif choice == "1":
            run_overview()
        elif choice == "2":
            video_name = input("请输入视频名称 (如: 这是楠楠纯净版): ").strip()
            if video_name:
                run_single_video(video_name)
            else:
                print("❌ 视频名称不能为空")
        elif choice == "3":
            run_all_videos()
        elif choice == "4":
            video_name = input("请输入视频名称 (如: 这是楠楠纯净版): ").strip()
            if video_name:
                run_single_video(video_name, force_reprocess=True)
            else:
                print("❌ 视频名称不能为空")
        elif choice == "5":
            confirm = input("⚠️ 确认强制重新处理所有视频? (y/N): ").strip().lower()
            if confirm == "y":
                run_all_videos(force_reprocess=True)
            else:
                print("❌ 操作已取消")
        elif choice == "6":
            output_dir = input("请输入输出目录 (留空使用默认): ").strip()
            run_clustering(output_dir if output_dir else None)
        elif choice == "7":
            output_dir = input("请输入输出目录 (留空使用默认): ").strip()
            run_process_and_cluster(output_base_dir=output_dir if output_dir else None)
        elif choice == "8":
            confirm = input("⚠️ 确认强制重新处理并聚类? (y/N): ").strip().lower()
            if confirm == "y":
                output_dir = input("请输入输出目录 (留空使用默认): ").strip()
                run_process_and_cluster(
                    force_reprocess=True,
                    output_base_dir=output_dir if output_dir else None
                )
            else:
                print("❌ 操作已取消")
        elif choice == "9":
            output_dir = input("请输入输出目录 (留空使用默认): ").strip()
            force = input("是否强制重新处理? (y/N): ").strip().lower() == "y"
            run_intelligent_classification(output_dir if output_dir else None, force)
        elif choice == "10":
            confirm = input("🚀 确认执行增强一键处理? (Y/n): ").strip().lower()
            if confirm != "n":
                output_dir = input("请输入输出目录 (留空使用默认): ").strip()
                force = input("是否强制重新处理? (y/N): ").strip().lower() == "y"
                run_enhanced_process_and_cluster(
                    force_reprocess=force,
                    output_base_dir=output_dir if output_dir else None
                )
            else:
                print("❌ 操作已取消")
        elif choice == "11":
            run_ai_clustering_analysis_only()
        else:
            print("❌ 无效选择，请重新输入")

def main():
    """主函数"""
    print("🎯 主标签处理器 + 动态聚类")
    print("=" * 50)
    
    # 检查环境
    if not Path("../🎬Slice").exists():
        print("❌ 错误: 未找到 🎬Slice 目录")
        print("请确保在正确的项目目录下运行此脚本")
        return
    
    # 如果有命令行参数，直接执行
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        # 解析参数
        force = False
        no_backup = False
        no_clustering = False
        output_dir = None
        
        for arg in sys.argv[2:]:
            if arg.lower() == "force":
                force = True
            elif arg.lower() == "no-backup":
                no_backup = True
            elif arg.lower() == "no-clustering":
                no_clustering = True
            elif arg.startswith("output="):
                output_dir = arg.split("=", 1)[1]
        
        if action == "overview":
            run_overview()
        elif action == "all":
            run_all_videos(force_reprocess=force, no_backup=no_backup)
        elif action == "cluster":
            run_clustering(output_dir)
        elif action == "enhanced-cluster" or action == "intelligent-classification":
            run_intelligent_classification(output_dir, force)
        elif action == "ai-cluster" or action == "ai-clustering":
            # 🎯 统一智能分类模式 - 内存流式处理（架构优化版v4.0）
            print("🎯 启动统一智能分类管理器v4.0（架构优化版）...")
            print("🧠 双层AI架构：主标签AI + 子类别AI")
            run_intelligent_classification(output_dir, force)
        elif action == "ai-cluster-analysis-only":
            # 🤖 双层AI智能聚类 - 仅分析模式（不复制文件）
            run_ai_clustering_analysis_only()
        elif action == "all-cluster":
            run_process_and_cluster(
                force_reprocess=force, 
                no_backup=no_backup,
                enable_clustering=not no_clustering,
                output_base_dir=output_dir
            )
        elif action == "enhanced-all-cluster":
            run_enhanced_process_and_cluster(
                force_reprocess=force,
                no_backup=no_backup,
                output_base_dir=output_dir
            )
        else:
            # 检查是否为有效的视频目录名
            slice_dir = Path("../🎬Slice")
            potential_video_dir = slice_dir / action
            
            if potential_video_dir.exists() and potential_video_dir.is_dir() and (potential_video_dir / "slices").exists():
                # 这是一个有效的视频目录
                video_name = action
                run_single_video(video_name, force_reprocess=force, no_backup=no_backup)
            else:
                print("❌ 无效参数")
                print("用法:")
                print("  python run.py overview                         # 查看概览")
                print("  python run.py all [force] [no-backup]          # 处理所有视频")
                print("  python run.py cluster [output=路径]             # 执行聚类")
                print("  python run.py enhanced-cluster [output=路径]    # 🎯 统一智能分类（架构优化）")
                print("  python run.py ai-cluster [output=路径]          # 🎯 统一智能分类（同上）")
                print("  python run.py ai-cluster-analysis-only        # 🤖 双层AI仅分析模式（不复制文件）")
                print("  python run.py all-cluster [force] [no-backup] [no-clustering] [output=路径]  # 一键处理")
                print("  python run.py enhanced-all-cluster [force] [no-backup] [output=路径]        # 🚀 增强一键处理")
                print("  python run.py <视频目录名> [force] [no-backup]      # 处理单个视频")
                print("")
                print("🎯 架构优化功能:")
                print("  enhanced-cluster:       统一智能分类，整合文件处理")
                print("  enhanced-all-cluster:   分类 + 智能聚类一键完成")
                print("  ai-cluster:             🎯 统一智能分类，主标签AI + 子类别AI")
                print("  📁 动态聚类: 基于主标签分类结果生成4大模块文件夹")
                print("  🍼 产品介绍: 整合营养科学，新增A2标签识别")
                print("  🎯 架构简化: 减少文件数量，直接端到端处理")
                print("  🤖 AI智能化: 完全摆脱硬编码关键词匹配，全AI驱动")
    else:
        # 进入交互模式
        interactive_mode()

if __name__ == "__main__":
    main() 