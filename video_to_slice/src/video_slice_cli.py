#!/usr/bin/env python3
"""
🎬 AI Video Master 5.0 - 命令行交互界面
提供用户友好的视频切分和语义合并操作界面
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
from datetime import datetime

# 添加颜色支持
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_colored(text: str, color: str = Colors.WHITE):
    """打印彩色文字"""
    print(f"{color}{text}{Colors.END}")

def print_header():
    """打印程序头部信息"""
    print_colored("=" * 80, Colors.CYAN)
    print_colored("🎬 AI Video Master 5.0 - 智能视频切片系统", Colors.BOLD + Colors.CYAN)
    print_colored("=" * 80, Colors.CYAN)
    print()

def print_menu():
    """打印主菜单"""
    print_colored("📋 主菜单:", Colors.BOLD + Colors.BLUE)
    print("1. 🎥 视频切分 (首次处理新视频)")
    print("2. 🧠 语义合并 (合并已切分的视频片段)")
    print("3. 📊 查看切分历史")
    print("4. ❓ 帮助信息")
    print("5. 🚪 退出程序")
    print()

def get_user_choice(prompt: str, valid_choices: List[str]) -> str:
    """获取用户选择"""
    while True:
        choice = input(f"{Colors.YELLOW}{prompt}{Colors.END}").strip()
        if choice in valid_choices:
            return choice
        print_colored(f"❌ 无效选择，请输入: {', '.join(valid_choices)}", Colors.RED)

def scan_input_videos(input_dir: str) -> List[Path]:
    """扫描输入目录中的视频文件"""
    input_path = Path(input_dir)
    if not input_path.exists():
        return []
    
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}
    video_files = []
    
    for file_path in input_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            video_files.append(file_path)
    
    return sorted(video_files)

def scan_output_folders(output_dir: str) -> List[Dict[str, Any]]:
    """扫描输出目录中已切分的视频文件夹"""
    output_path = Path(output_dir)
    if not output_path.exists():
        return []
    
    video_folders = []
    
    for folder_path in output_path.iterdir():
        if folder_path.is_dir():
            # 检查是否有切片文件
            slices_json = folder_path / f"{folder_path.name}_slices.json"
            mp4_files = list(folder_path.glob("*.mp4"))
            
            if slices_json.exists() and mp4_files:
                # 读取切片信息
                try:
                    with open(slices_json, 'r', encoding='utf-8') as f:
                        slice_data = json.load(f)
                    
                    video_folders.append({
                        'name': folder_path.name,
                        'path': str(folder_path),
                        'slice_count': len(mp4_files),
                        'total_duration': slice_data.get('quality_check', {}).get('total_duration', 0),
                        'slices_json': str(slices_json),
                        'has_semantic_merge': any('semantic_seg' in f.name for f in mp4_files)
                    })
                except Exception as e:
                    print_colored(f"⚠️ 读取切片信息失败: {folder_path.name} - {e}", Colors.YELLOW)
    
    return sorted(video_folders, key=lambda x: x['name'])

def display_video_list(videos: List[Path], title: str):
    """显示视频列表"""
    print_colored(f"\n📁 {title}:", Colors.BOLD + Colors.GREEN)
    if not videos:
        print_colored("  (暂无视频文件)", Colors.YELLOW)
        return
    
    for i, video in enumerate(videos, 1):
        file_size = video.stat().st_size / (1024 * 1024)  # MB
        print(f"  {i}. {video.name} ({file_size:.1f} MB)")

def display_folder_list(folders: List[Dict[str, Any]], title: str):
    """显示已切分视频文件夹列表"""
    print_colored(f"\n📂 {title}:", Colors.BOLD + Colors.GREEN)
    if not folders:
        print_colored("  (暂无已切分的视频)", Colors.YELLOW)
        return
    
    for i, folder in enumerate(folders, 1):
        duration_str = f"{folder['total_duration']:.1f}s" if folder['total_duration'] > 0 else "未知"
        merge_status = "✅已合并" if folder['has_semantic_merge'] else "❌未合并"
        print(f"  {i}. {folder['name']} - {folder['slice_count']}个片段 ({duration_str}) {merge_status}")

def get_similarity_threshold_suggestion():
    """获取相似度阈值建议"""
    print_colored("\n🎯 相似度阈值建议:", Colors.BOLD + Colors.BLUE)
    suggestions = [
        ("1", "0.6", "宽松合并", "更多片段会被整合，适合内容变化较大的视频"),
        ("2", "0.7", "平衡模式", "推荐设置，适合大多数场景"),
        ("3", "0.75", "标准模式", "适中的合并策略，保持较好的内容连贯性"),
        ("4", "0.8", "严格合并", "只有高度相似的片段才合并，适合精细内容"),
        ("5", "0.9", "极严格", "几乎不合并，只处理非常相似的片段"),
        ("6", "custom", "自定义", "手动输入0.1-1.0之间的数值")
    ]
    
    for choice, threshold, name, desc in suggestions:
        print(f"  {choice}. {name} (阈值: {threshold}) - {desc}")
    
    print()
    choice = get_user_choice("请选择相似度阈值 [1-6]: ", [str(i) for i in range(1, 7)])
    
    if choice == "6":
        while True:
            try:
                threshold = float(input(f"{Colors.YELLOW}请输入自定义阈值 (0.1-1.0): {Colors.END}"))
                if 0.1 <= threshold <= 1.0:
                    return threshold
                else:
                    print_colored("❌ 阈值必须在0.1-1.0之间", Colors.RED)
            except ValueError:
                print_colored("❌ 请输入有效的数字", Colors.RED)
    else:
        return float(suggestions[int(choice) - 1][1])

def get_merge_duration():
    """获取最大合并时长"""
    print_colored("\n⏱️ 最大合并时长建议:", Colors.BOLD + Colors.BLUE)
    suggestions = [
        ("1", "30", "短视频模式", "适合快节奏内容"),
        ("2", "60", "标准模式", "推荐设置，适合大多数内容"),
        ("3", "90", "长内容模式", "适合教学或演示视频"),
        ("4", "120", "完整场景", "适合保持完整的场景内容"),
        ("5", "custom", "自定义", "手动输入时长（秒）")
    ]
    
    for choice, duration, name, desc in suggestions:
        print(f"  {choice}. {name} ({duration}秒) - {desc}")
    
    print()
    choice = get_user_choice("请选择最大合并时长 [1-5]: ", [str(i) for i in range(1, 6)])
    
    if choice == "5":
        while True:
            try:
                duration = float(input(f"{Colors.YELLOW}请输入自定义时长 (10-300秒): {Colors.END}"))
                if 10 <= duration <= 300:
                    return duration
                else:
                    print_colored("❌ 时长必须在10-300秒之间", Colors.RED)
            except ValueError:
                print_colored("❌ 请输入有效的数字", Colors.RED)
    else:
        return float(suggestions[int(choice) - 1][1])

def video_slicing_mode():
    """视频切分模式"""
    print_colored("\n🎥 视频切分模式", Colors.BOLD + Colors.MAGENTA)
    print_colored("=" * 50, Colors.MAGENTA)
    
    # 扫描输入目录
    input_dir = "data/input"
    videos = scan_input_videos(input_dir)
    
    display_video_list(videos, "可切分的视频文件")
    
    if not videos:
        print_colored("\n❌ 输入目录中没有找到视频文件", Colors.RED)
        print_colored(f"请将视频文件放置到: {os.path.abspath(input_dir)}", Colors.YELLOW)
        return
    
    print_colored("\n⚠️ 注意: 首次切分将禁用Google Video AI，使用默认时间切分策略", Colors.YELLOW)
    print_colored("这样可以快速生成切片，后续可以使用语义合并功能优化", Colors.YELLOW)
    
    # 选择处理方式
    print_colored("\n🔧 处理选项:", Colors.BOLD + Colors.BLUE)
    print("1. 处理所有视频")
    print("2. 选择特定视频")
    print("3. 返回主菜单")
    
    choice = get_user_choice("请选择处理方式 [1-3]: ", ["1", "2", "3"])
    
    if choice == "3":
        return
    
    # 获取处理参数
    print_colored("\n⚙️ 切分参数设置:", Colors.BOLD + Colors.BLUE)
    
    # 默认时间间隔
    print("切分时间间隔:")
    print("  1. 5秒  (适合短视频)")
    print("  2. 10秒 (推荐设置)")
    print("  3. 15秒 (适合长视频)")
    print("  4. 自定义")
    
    interval_choice = get_user_choice("请选择切分间隔 [1-4]: ", ["1", "2", "3", "4"])
    
    intervals = {"1": 5, "2": 10, "3": 15}
    if interval_choice == "4":
        while True:
            try:
                interval = float(input(f"{Colors.YELLOW}请输入自定义间隔 (3-60秒): {Colors.END}"))
                if 3 <= interval <= 60:
                    break
                else:
                    print_colored("❌ 间隔必须在3-60秒之间", Colors.RED)
            except ValueError:
                print_colored("❌ 请输入有效的数字", Colors.RED)
    else:
        interval = intervals[interval_choice]
    
    # 并发设置
    concurrent = 2  # 降低并发数，避免资源竞争
    ffmpeg_workers = 4
    
    print_colored(f"\n🚀 开始切分处理...", Colors.GREEN)
    print_colored(f"切分间隔: {interval}秒", Colors.CYAN)
    print_colored(f"并发数: {concurrent}", Colors.CYAN)
    print_colored(f"FFmpeg线程: {ffmpeg_workers}", Colors.CYAN)
    
    # 执行切分
    try:
        from parallel_batch_processor import ParallelBatchProcessor
        
        # 创建处理器，禁用Google Video AI和语义合并
        processor = ParallelBatchProcessor(
            output_dir="data/output",
            temp_dir="data/temp",
            max_concurrent=concurrent,
            ffmpeg_workers=ffmpeg_workers,
            enable_semantic_merge=False  # 首次切分禁用语义合并
        )
        
        if choice == "1":
            # 处理所有视频
            video_paths = [str(v) for v in videos]
        else:
            # 选择特定视频
            print_colored("\n请选择要处理的视频:", Colors.BLUE)
            for i, video in enumerate(videos, 1):
                print(f"  {i}. {video.name}")
            
            selected = get_user_choice(f"请输入视频编号 [1-{len(videos)}]: ", 
                                     [str(i) for i in range(1, len(videos) + 1)])
            video_paths = [str(videos[int(selected) - 1])]
        
        # 执行处理（使用默认切分策略）
        start_time = time.time()
        
        # 这里需要修改processor来支持默认时间切分
        result = processor.process_batch_with_default_slicing(
            video_paths=video_paths,
            segment_duration=interval
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result["success"]:
            print_colored(f"\n✅ 切分完成!", Colors.GREEN)
            print_colored(f"处理时间: {duration:.1f}秒", Colors.CYAN)
            print_colored(f"成功处理: {result['stats']['processed_videos']}/{result['stats']['total_videos']} 个视频", Colors.CYAN)
            print_colored(f"生成切片: {result['stats']['total_slices']} 个", Colors.CYAN)
            print_colored("\n💡 提示: 现在可以使用语义合并功能来优化切片!", Colors.YELLOW)
        else:
            print_colored(f"\n❌ 切分失败: {result.get('error', '未知错误')}", Colors.RED)
    
    except ImportError:
        print_colored("❌ 导入处理模块失败，请检查依赖", Colors.RED)
    except Exception as e:
        print_colored(f"❌ 处理过程中发生错误: {e}", Colors.RED)

def semantic_merge_mode():
    """语义合并模式"""
    print_colored("\n🧠 语义合并模式", Colors.BOLD + Colors.MAGENTA)
    print_colored("=" * 50, Colors.MAGENTA)
    
    # 扫描输出目录
    output_dir = "data/output"
    folders = scan_output_folders(output_dir)
    
    display_folder_list(folders, "已切分的视频")
    
    if not folders:
        print_colored("\n❌ 没有找到已切分的视频", Colors.RED)
        print_colored("请先使用视频切分功能处理视频文件", Colors.YELLOW)
        return
    
    # 选择要合并的视频
    print_colored("\n📋 选择要进行语义合并的视频:", Colors.BOLD + Colors.BLUE)
    print("0. 处理所有视频")
    for i, folder in enumerate(folders, 1):
        status = "✅" if folder['has_semantic_merge'] else "❌"
        print(f"{i}. {folder['name']} {status}")
    print(f"{len(folders) + 1}. 返回主菜单")
    
    choice = get_user_choice(f"请选择 [0-{len(folders) + 1}]: ", 
                           [str(i) for i in range(0, len(folders) + 2)])
    
    if choice == str(len(folders) + 1):
        return
    
    # 获取合并参数
    similarity_threshold = get_similarity_threshold_suggestion()
    max_merge_duration = get_merge_duration()
    
    # 确认参数
    print_colored("\n📊 合并参数确认:", Colors.BOLD + Colors.BLUE)
    print_colored(f"相似度阈值: {similarity_threshold}", Colors.CYAN)
    print_colored(f"最大合并时长: {max_merge_duration}秒", Colors.CYAN)
    
    confirm = get_user_choice("确认开始合并? [y/n]: ", ["y", "n", "Y", "N"])
    if confirm.lower() == "n":
        print_colored("❌ 操作已取消", Colors.YELLOW)
        return
    
    # 执行语义合并
    print_colored(f"\n🚀 开始语义合并...", Colors.GREEN)
    
    try:
        from semantic_segment_merger import SemanticSegmentMerger
        
        # 创建语义合并器
        merger = SemanticSegmentMerger(
            similarity_threshold=similarity_threshold,
            max_merge_duration=max_merge_duration
        )
        
        if choice == "0":
            # 处理所有视频
            selected_folders = folders
        else:
            # 处理选定视频
            selected_folders = [folders[int(choice) - 1]]
        
        # 执行合并
        start_time = time.time()
        results = []
        
        for folder in selected_folders:
            print_colored(f"\n处理视频: {folder['name']}", Colors.CYAN)
            
            # 读取切片信息
            with open(folder['slices_json'], 'r', encoding='utf-8') as f:
                slice_data = json.load(f)
            
            # 执行语义合并
            merge_result = merger.merge_segments(
                segments=slice_data['slices'],
                video_name=folder['name'],
                output_dir=folder['path']
            )
            
            results.append({
                'video_name': folder['name'],
                'result': merge_result
            })
            
            if merge_result['success']:
                compression_ratio = merge_result.get('compression_ratio', 1.0)
                print_colored(f"  ✅ 合并完成 - 压缩比: {compression_ratio:.1f}x", Colors.GREEN)
            else:
                print_colored(f"  ❌ 合并失败: {merge_result.get('error', '未知错误')}", Colors.RED)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 显示总结
        successful = [r for r in results if r['result']['success']]
        failed = [r for r in results if not r['result']['success']]
        
        print_colored(f"\n🎉 语义合并完成!", Colors.GREEN)
        print_colored(f"处理时间: {duration:.1f}秒", Colors.CYAN)
        print_colored(f"成功: {len(successful)}/{len(results)} 个视频", Colors.CYAN)
        
        if successful:
            avg_compression = sum(r['result'].get('compression_ratio', 1.0) for r in successful) / len(successful)
            print_colored(f"平均压缩比: {avg_compression:.1f}x", Colors.CYAN)
        
        if failed:
            print_colored(f"失败的视频:", Colors.RED)
            for r in failed:
                print_colored(f"  - {r['video_name']}: {r['result'].get('error', '未知错误')}", Colors.RED)
    
    except ImportError:
        print_colored("❌ 导入语义合并模块失败，请检查依赖", Colors.RED)
    except Exception as e:
        print_colored(f"❌ 合并过程中发生错误: {e}", Colors.RED)

def view_history():
    """查看切分历史"""
    print_colored("\n📊 切分历史", Colors.BOLD + Colors.MAGENTA)
    print_colored("=" * 50, Colors.MAGENTA)
    
    # 读取批处理报告
    report_file = Path("data/output/parallel_batch_processing_report.json")
    
    if not report_file.exists():
        print_colored("❌ 没有找到处理历史记录", Colors.RED)
        return
    
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        print_colored(f"📅 最后处理时间: {report.get('timestamp', '未知')}", Colors.CYAN)
        print_colored(f"📁 输入目录: {report.get('input_directory', '未知')}", Colors.CYAN)
        print_colored(f"📂 输出目录: {report.get('output_directory', '未知')}", Colors.CYAN)
        
        stats = report.get('stats', {})
        print_colored(f"\n📊 处理统计:", Colors.BOLD + Colors.BLUE)
        print(f"  总视频数: {stats.get('total_videos', 0)}")
        print(f"  成功处理: {stats.get('processed_videos', 0)}")
        print(f"  失败数量: {stats.get('failed_videos', 0)}")
        print(f"  总切片数: {stats.get('total_slices', 0)}")
        
        if stats.get('compression_ratio', 1.0) > 1.0:
            print(f"  语义压缩比: {stats.get('compression_ratio', 1.0):.1f}x")
        
        parallel_info = report.get('parallel_info', {})
        print_colored(f"\n⚡ 性能信息:", Colors.BOLD + Colors.BLUE)
        print(f"  并发数: {parallel_info.get('max_concurrent_videos', 0)}")
        print(f"  FFmpeg线程: {parallel_info.get('ffmpeg_workers', 0)}")
        print(f"  实际处理时间: {parallel_info.get('actual_parallel_time', 0):.1f}秒")
        print(f"  平均每视频: {parallel_info.get('average_time_per_video', 0):.1f}秒")
        
        if parallel_info.get('time_saved_percentage', 0) > 0:
            print(f"  时间节省: {parallel_info.get('time_saved_percentage', 0):.1f}%")
        
        # 显示详细结果
        results = report.get('results', [])
        if results:
            print_colored(f"\n📋 详细结果:", Colors.BOLD + Colors.BLUE)
            for result in results[:10]:  # 只显示前10个
                status = "✅" if result.get('success', False) else "❌"
                name = result.get('video_name', '未知')
                slices = result.get('slices_count', 0)
                duration = result.get('duration', 0)
                print(f"  {status} {name} - {slices}个切片 ({duration:.1f}s)")
            
            if len(results) > 10:
                print(f"  ... 还有 {len(results) - 10} 个结果")
    
    except Exception as e:
        print_colored(f"❌ 读取历史记录失败: {e}", Colors.RED)

def show_help():
    """显示帮助信息"""
    print_colored("\n❓ 帮助信息", Colors.BOLD + Colors.MAGENTA)
    print_colored("=" * 50, Colors.MAGENTA)
    
    print_colored("🎥 视频切分功能:", Colors.BOLD + Colors.BLUE)
    print("  - 将视频文件放入 data/input/ 目录")
    print("  - 首次切分使用默认时间间隔，不依赖Google Video AI")
    print("  - 支持 MP4, MOV, AVI, MKV 等格式")
    print("  - 输出文件保存在 data/output/ 目录")
    
    print_colored("\n🧠 语义合并功能:", Colors.BOLD + Colors.BLUE)
    print("  - 基于CLIP模型分析视频内容语义相似性")
    print("  - 智能合并相关性强的视频片段")
    print("  - 可调整相似度阈值和最大合并时长")
    print("  - 生成详细的合并报告和统计信息")
    
    print_colored("\n⚙️ 相似度阈值说明:", Colors.BOLD + Colors.BLUE)
    print("  - 0.6-0.65: 宽松合并，更多整合")
    print("  - 0.7-0.75: 平衡模式，推荐使用")
    print("  - 0.8-0.85: 严格合并，精确匹配")
    print("  - 0.9+: 极严格，几乎不合并")
    
    print_colored("\n📁 目录结构:", Colors.BOLD + Colors.BLUE)
    print("  data/input/   - 放置待处理的视频文件")
    print("  data/output/  - 输出的切片文件和报告")
    print("  data/temp/    - 临时处理文件")
    
    print_colored("\n🔧 系统要求:", Colors.BOLD + Colors.BLUE)
    print("  - Python 3.10+")
    print("  - FFmpeg (用于视频处理)")
    print("  - 8GB+ 内存 (语义分析)")
    print("  - 可选: CUDA GPU (加速处理)")

def main():
    """主函数"""
    print_header()
    
    # 检查必要的目录
    required_dirs = ["data/input", "data/output", "data/temp"]
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    while True:
        print_menu()
        choice = get_user_choice("请选择功能 [1-5]: ", ["1", "2", "3", "4", "5"])
        
        if choice == "1":
            video_slicing_mode()
        elif choice == "2":
            semantic_merge_mode()
        elif choice == "3":
            view_history()
        elif choice == "4":
            show_help()
        elif choice == "5":
            print_colored("\n👋 感谢使用 AI Video Master 5.0!", Colors.GREEN)
            break
        
        # 显示分隔线
        print_colored("\n" + "─" * 80, Colors.CYAN)
        input(f"{Colors.YELLOW}按回车键继续...{Colors.END}")
        print("\n" * 2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n👋 程序已退出", Colors.YELLOW)
    except Exception as e:
        print_colored(f"\n❌ 程序发生异常: {e}", Colors.RED)
        sys.exit(1) 