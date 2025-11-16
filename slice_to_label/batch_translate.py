#!/usr/bin/env python3
"""
批量JSON翻译工具 - 翻译指定目录下的所有JSON分析文件
"""

import sys
import os
from pathlib import Path
import glob

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

def main():
    if len(sys.argv) < 2:
        print("用法: python batch_translate.py <目录路径>")
        print("示例: python batch_translate.py '../🎬Slice/video_1/slices/'")
        return
    
    target_dir = sys.argv[1]
    
    if not os.path.exists(target_dir):
        print(f"❌ 目录不存在: {target_dir}")
        return
    
    # 查找所有analysis.json文件
    json_files = glob.glob(os.path.join(target_dir, "*_analysis.json"))
    
    if not json_files:
        print(f"❌ 在目录 {target_dir} 中未找到*_analysis.json文件")
        return
    
    print(f"🎯 发现 {len(json_files)} 个JSON文件需要翻译")
    
    # 导入翻译函数
    from src.ai_analyzers import translate_json_file_with_deepseek
    
    success_count = 0
    fail_count = 0
    
    for i, json_file in enumerate(json_files, 1):
        file_name = os.path.basename(json_file)
        print(f"\n📋 [{i}/{len(json_files)}] 处理: {file_name}")
        
        result = translate_json_file_with_deepseek(json_file)
        
        if result:
            success_count += 1
            print(f"✅ 翻译成功")
        else:
            fail_count += 1
            print(f"❌ 翻译失败")
    
    print(f"\n🎉 批量翻译完成！")
    print(f"✅ 成功: {success_count} 个文件")
    print(f"❌ 失败: {fail_count} 个文件")

if __name__ == "__main__":
    main() 