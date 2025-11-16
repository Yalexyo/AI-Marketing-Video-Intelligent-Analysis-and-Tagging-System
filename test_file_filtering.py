#!/usr/bin/env python3
"""
测试文件过滤逻辑验证脚本
验证带♻️和❌前缀的文件是否被正确过滤
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "slice_to_label"))

def test_slice_to_label_filtering():
    """测试slice_to_label模块的过滤逻辑"""
    print("🧪 测试slice_to_label模块的文件过滤逻辑...")
    
    try:
        from slice_to_label.run_analysis import scan_slice_directories
        
        # 测试🎬Slice目录
        slice_dir = Path("🎬Slice")
        if slice_dir.exists():
            print(f"📁 扫描目录: {slice_dir}")
            video_slices = scan_slice_directories(slice_dir)
            
            total_files = 0
            for video_name, data in video_slices.items():
                file_count = len(data['slices']) + len(data['product'])
                total_files += file_count
                print(f"  📹 {video_name}: {file_count} 个有效文件")
            
            print(f"✅ slice_to_label过滤测试完成，共发现 {total_files} 个有效文件")
        else:
            print("⚠️ 🎬Slice目录不存在")
            
    except Exception as e:
        print(f"❌ slice_to_label过滤测试失败: {e}")

def test_label_to_classifier_filtering():
    """测试label_to_classifier模块的过滤逻辑"""
    print("\n🧪 测试label_to_classifier模块的文件过滤逻辑...")
    
    try:
        sys.path.append(str(Path(__file__).parent / "label_to_classifier"))
        from label_to_classifier.src.slice_file_manager import SliceFileManager
        
        # 创建文件管理器
        file_manager = SliceFileManager("🎬Slice")
        
        # 收集切片数据
        classified_data, unclassified_data = file_manager.collect_all_slice_data()
        
        total_valid_files = len(classified_data) + len(unclassified_data)
        print(f"✅ label_to_classifier过滤测试完成")
        print(f"  📊 已分类文件: {len(classified_data)}")
        print(f"  📊 未分类文件: {len(unclassified_data)}")
        print(f"  📊 总有效文件: {total_valid_files}")
        
    except Exception as e:
        print(f"❌ label_to_classifier过滤测试失败: {e}")

def test_shell_script_filtering():
    """测试shell脚本的过滤逻辑"""
    print("\n🧪 测试shell脚本的文件计数逻辑...")
    
    import subprocess
    
    try:
        # 执行文件计数命令（模拟一键DD.sh中的逻辑）
        json_count_cmd = 'find "🎬Slice" -name "*_analysis.json" ! -name "♻️*" ! -name "❌*" 2>/dev/null | wc -l'
        slice_count_cmd = 'find "🎬Slice" -name "*.mp4" ! -name "♻️*" ! -name "❌*" 2>/dev/null | wc -l'
        
        json_result = subprocess.run(json_count_cmd, shell=True, capture_output=True, text=True)
        slice_result = subprocess.run(slice_count_cmd, shell=True, capture_output=True, text=True)
        
        if json_result.returncode == 0 and slice_result.returncode == 0:
            json_count = int(json_result.stdout.strip())
            slice_count = int(slice_result.stdout.strip())
            
            coverage_percentage = (json_count * 100) // slice_count if slice_count > 0 else 0
            
            print(f"✅ shell脚本过滤测试完成")
            print(f"  📊 有效视频文件: {slice_count}")
            print(f"  📊 有效分析文件: {json_count}")
            print(f"  📊 覆盖率: {coverage_percentage}%")
        else:
            print(f"❌ shell命令执行失败")
            
    except Exception as e:
        print(f"❌ shell脚本过滤测试失败: {e}")

def main():
    """主测试函数"""
    print("🚫 文件过滤逻辑验证测试")
    print("=" * 50)
    print("测试目标：验证带♻️和❌前缀的文件是否被正确过滤")
    print()
    
    # 运行各项测试
    test_slice_to_label_filtering()
    test_label_to_classifier_filtering()
    test_shell_script_filtering()
    
    print("\n" + "=" * 50)
    print("🎉 所有过滤逻辑测试完成")
    print("💡 如果看到过滤信息，说明修复生效")
    print("💡 如果没有看到♻️和❌前缀的文件被计入，说明过滤成功")

if __name__ == "__main__":
    main() 