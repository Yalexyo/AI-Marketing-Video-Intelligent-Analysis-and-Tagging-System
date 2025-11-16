#!/usr/bin/env python3
"""
标记包含"无效切片"的切片文件
在文件名前加上❌标记
"""

import os
import json
import glob
from pathlib import Path

def find_invalid_slice_files():
    """找到所有包含"无效切片"的JSON文件"""
    invalid_files = []
    
    # 搜索所有切片目录中的JSON文件
    slice_dirs = glob.glob("🎬Slice/*/slices/")
    
    for slice_dir in slice_dirs:
        json_files = glob.glob(os.path.join(slice_dir, "*_analysis.json"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    object_value = data.get('object', '')
                    if '无效切片' in object_value:
                        invalid_files.append({
                            'json_file': json_file,
                            'object_value': object_value
                        })
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"⚠️ 无法读取文件 {json_file}: {e}")
    
    return invalid_files

def mark_invalid_slice_files(invalid_json_files):
    """标记对应的切片文件"""
    marked_count = 0
    already_marked = 0
    not_found = 0
    
    for item in invalid_json_files:
        json_file = item['json_file']
        object_value = item['object_value']
        
        # 获取目录和文件信息
        json_path = Path(json_file)
        slice_dir = json_path.parent
        
        # 从JSON文件名推导切片文件名
        json_basename = json_path.stem  # 移除.json扩展名
        slice_basename = json_basename.replace('_analysis', '')
        
        # 查找对应的切片文件（可能是.mp4, .mov等格式）
        slice_patterns = [
            os.path.join(slice_dir, f"{slice_basename}.mp4"),
            os.path.join(slice_dir, f"{slice_basename}.mov"),
            os.path.join(slice_dir, f"{slice_basename}.avi"),
            os.path.join(slice_dir, f"{slice_basename}.mkv")
        ]
        
        found = False
        for slice_pattern in slice_patterns:
            if os.path.exists(slice_pattern):
                slice_file = slice_pattern
                slice_path = Path(slice_file)
                
                # 检查是否已经标记过
                if slice_path.name.startswith('❌'):
                    print(f"⏭️ 已标记: {slice_path.name} (object: {object_value})")
                    already_marked += 1
                    found = True
                    break
                
                # 创建新文件名
                new_name = f"❌{slice_path.name}"
                new_path = slice_path.parent / new_name
                
                try:
                    # 重命名文件
                    slice_path.rename(new_path)
                    print(f"✅ 标记完成: {slice_path.name} -> {new_name}")
                    print(f"   📝 object内容: {object_value}")
                    marked_count += 1
                    found = True
                except OSError as e:
                    print(f"❌ 重命名失败: {slice_file} - {e}")
                
                break
        
        if not found:
            # 检查是否在已标记的目录中
            parent_dir_name = slice_dir.parent.name
            if parent_dir_name.startswith('❌'):
                print(f"📁 目录已标记: {parent_dir_name}/{slice_basename}")
                already_marked += 1
            else:
                print(f"⚠️ 未找到对应的切片文件: {slice_basename}")
                print(f"   📝 object内容: {object_value}")
                not_found += 1
    
    return marked_count, already_marked, not_found

def main():
    print("🔍 正在搜索包含'无效切片'的文件...")
    
    # 找到所有包含"无效切片"的JSON文件
    invalid_json_files = find_invalid_slice_files()
    
    if not invalid_json_files:
        print("🎉 没有找到包含'无效切片'的文件！")
        return
    
    print(f"\n📋 找到 {len(invalid_json_files)} 个包含'无效切片'的文件：")
    
    # 按视频分组显示
    video_groups = {}
    for item in invalid_json_files:
        json_file = item['json_file']
        object_value = item['object_value']
        
        # 提取视频名
        path_parts = json_file.split('/')
        video_name = path_parts[-3] if len(path_parts) >= 3 else "未知视频"
        
        if video_name not in video_groups:
            video_groups[video_name] = []
        
        file_name = Path(json_file).stem
        segment_info = file_name.split('_')[-2:]  # 获取最后两部分
        video_groups[video_name].append({
            'segment': ' '.join(segment_info),
            'object': object_value
        })
    
    for i, (video_name, segments) in enumerate(video_groups.items(), 1):
        print(f"  {i}. {video_name} ({len(segments)}个切片)")
        for seg in segments:
            print(f"     - {seg['segment']}: {seg['object']}")
    
    print(f"\n🏷️ 开始标记对应的切片文件...")
    marked_count, already_marked, not_found = mark_invalid_slice_files(invalid_json_files)
    
    print(f"\n📊 处理结果：")
    print(f"  🔍 发现无效切片: {len(invalid_json_files)} 个")
    print(f"  ✅ 新标记切片: {marked_count} 个")
    print(f"  ⏭️ 已标记切片: {already_marked} 个")
    print(f"  ⚠️ 未找到文件: {not_found} 个")
    print(f"  📁 总标记数量: {marked_count + already_marked} 个")

if __name__ == "__main__":
    main() 