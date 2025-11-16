#!/usr/bin/env python3
"""
JSON翻译工具 - 直接翻译JSON文件中的英文字段
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

def main():
    if len(sys.argv) < 2:
        print("用法: python translate_json.py <json文件路径>")
        print("示例: python translate_json.py '../🎬Slice/video_1/slices/video_1_semantic_seg_15_镜头15_analysis.json'")
        return
    
    json_file = sys.argv[1]
    
    if not os.path.exists(json_file):
        print(f"❌ 文件不存在: {json_file}")
        return
    
    print(f"🎯 准备翻译JSON文件: {json_file}")
    
    # 导入翻译函数
    from src.ai_analyzers import translate_json_file_with_deepseek
    
    # 执行翻译
    result = translate_json_file_with_deepseek(json_file)
    
    if result:
        print("🎉 翻译完成！")
        
        # 显示翻译后的内容
        import json
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("\n📋 翻译后的内容:")
        for field in ['object', 'scene', 'emotion']:
            if field in data:
                print(f"  {field}: {data[field]}")
    else:
        print("❌ 翻译失败")

if __name__ == "__main__":
    main() 