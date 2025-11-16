#!/usr/bin/env python3
"""
标记分析失败的切片文件
在文件名前加上❌标记
"""

import os
import json
import glob
from pathlib import Path

def find_failed_analysis_files():
    """找到所有分析失败的JSON文件"""
    failed_files = []
    
    # 搜索所有切片目录中的JSON文件
    # 支持灵活的文件夹结构：既支持slices子目录，也支持直接在目录下
    slice_dirs = []
    for item in glob.glob("🎬Slice/*/"):
        if os.path.isdir(item):
            # 方法1: 检查slices子目录
            slices_path = os.path.join(item, "slices")
            if os.path.exists(slices_path):
                slice_dirs.append(slices_path + "/")
            # 方法2: 检查直接在目录下是否有JSON文件
            elif glob.glob(os.path.join(item, "*_analysis.json")):
                slice_dirs.append(item)
    
    for slice_dir in slice_dirs:
        json_files = glob.glob(os.path.join(slice_dir, "*_analysis.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('object') == '分析失败':
                        failed_files.append(json_file)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"⚠️ 无法读取文件 {json_file}: {e}")
    
    return failed_files

def mark_failed_slice_files(failed_json_files):
    """标记对应的切片文件"""
    marked_count = 0
    
    for json_file in failed_json_files:
        # 获取目录和文件信息
        json_path = Path(json_file)
        slice_dir = json_path.parent
        
        # 从JSON文件名推导切片文件名
        # 例: video_semantic_seg_1_镜头1_analysis.json -> video_semantic_seg_1_镜头1.mp4
        json_basename = json_path.stem  # 移除.json扩展名
        slice_basename = json_basename.replace('_analysis', '')
        
        # 查找对应的切片文件（可能是.mp4, .mov等格式）
        slice_patterns = [
            os.path.join(slice_dir, f"{slice_basename}.mp4"),
            os.path.join(slice_dir, f"{slice_basename}.mov"),
            os.path.join(slice_dir, f"{slice_basename}.avi"),
            os.path.join(slice_dir, f"{slice_basename}.mkv")
        ]
        
        for slice_pattern in slice_patterns:
            if os.path.exists(slice_pattern):
                slice_file = slice_pattern
                slice_path = Path(slice_file)
                
                # 检查是否已经标记过
                if slice_path.name.startswith('❌'):
                    print(f"⏭️ 已标记: {slice_path.name}")
                    continue
                
                # 创建新文件名
                new_name = f"❌{slice_path.name}"
                new_path = slice_path.parent / new_name
                
                try:
                    # 重命名文件
                    slice_path.rename(new_path)
                    print(f"✅ 标记完成: {slice_path.name} -> {new_name}")
                    marked_count += 1
                except OSError as e:
                    print(f"❌ 重命名失败: {slice_file} - {e}")
                
                break
        else:
            print(f"⚠️ 未找到对应的切片文件: {slice_basename}")
    
    return marked_count

def main():
    print("🔍 正在搜索分析失败的切片...")
    
    # 找到所有分析失败的JSON文件
    failed_json_files = find_failed_analysis_files()
    
    if not failed_json_files:
        print("🎉 没有找到分析失败的切片文件！")
        return
    
    print(f"\n📋 找到 {len(failed_json_files)} 个分析失败的文件：")
    for i, json_file in enumerate(failed_json_files, 1):
        # 提取视频名和片段信息
        path_parts = json_file.split('/')
        video_name = path_parts[-3] if len(path_parts) >= 3 else "未知视频"
        file_name = Path(json_file).stem
        segment_info = file_name.split('_')[-2:]  # 获取最后两部分，如 "seg_1", "镜头1"
        
        print(f"  {i}. {video_name} - {' '.join(segment_info)}")
    
    print(f"\n🏷️ 开始标记对应的切片文件...")
    marked_count = mark_failed_slice_files(failed_json_files)
    
    print(f"\n📊 处理结果：")
    print(f"  🔍 发现分析失败: {len(failed_json_files)} 个")
    print(f"  ✅ 成功标记: {marked_count} 个")
    print(f"  ⚠️ 未找到切片: {len(failed_json_files) - marked_count} 个")

if __name__ == "__main__":
    main() 