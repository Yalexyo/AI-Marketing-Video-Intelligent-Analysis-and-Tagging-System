#!/usr/bin/env python3
"""
CLIP模型下载脚本
下载并缓存CLIP模型到本地，用于离线使用
"""

import os
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_clip_model():
    """下载CLIP模型到本地缓存"""
    try:
        from transformers import CLIPProcessor, CLIPModel
        import torch
        
        print("🔄 开始下载CLIP模型...")
        
        model_name = "openai/clip-vit-base-patch32"
        cache_dir = Path("./cache/clip").resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 缓存目录: {cache_dir}")
        
        # 下载模型
        print("📦 下载CLIP模型...")
        model = CLIPModel.from_pretrained(
            model_name,
            cache_dir=str(cache_dir),
            force_download=False  # 如果已存在则不重复下载
        )
        
        print("📦 下载CLIP处理器...")
        processor = CLIPProcessor.from_pretrained(
            model_name,
            cache_dir=str(cache_dir),
            force_download=False
        )
        
        # 测试模型是否正常工作
        print("🧪 测试模型...")
        model.eval()
        
        # 检查GPU可用性
        if torch.cuda.is_available():
            print("🎮 检测到GPU，测试GPU模式...")
            model = model.to('cuda')
            print("✅ GPU模式正常")
        else:
            print("💻 使用CPU模式")
        
        print("✅ CLIP模型下载并测试成功!")
        print(f"📂 模型已保存到: {cache_dir}")
        
        # 显示缓存目录内容
        print("\n📋 缓存文件:")
        for item in cache_dir.rglob("*"):
            if item.is_file():
                size_mb = item.stat().st_size / (1024 * 1024)
                print(f"  {item.relative_to(cache_dir)} ({size_mb:.1f} MB)")
        
        return True
        
    except ImportError as e:
        print(f"❌ 依赖缺失: {e}")
        print("请先安装: uv add torch transformers pillow")
        return False
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False

def check_offline_model():
    """检查离线模型是否可用"""
    try:
        from transformers import CLIPProcessor, CLIPModel
        
        model_name = "openai/clip-vit-base-patch32"
        cache_dir = Path("./cache/clip").resolve()
        
        if not cache_dir.exists():
            print("❌ 缓存目录不存在")
            return False
        
        print("🔍 检查离线模型...")
        
        # 尝试从本地加载
        model = CLIPModel.from_pretrained(
            model_name,
            cache_dir=str(cache_dir),
            local_files_only=True  # 只使用本地文件
        )
        
        processor = CLIPProcessor.from_pretrained(
            model_name,
            cache_dir=str(cache_dir),
            local_files_only=True
        )
        
        print("✅ 离线模型加载成功!")
        return True
        
    except Exception as e:
        print(f"❌ 离线模型检查失败: {e}")
        return False

def main():
    """主函数"""
    print("🎬 AI Video Master 5.0 - CLIP模型管理工具")
    print("=" * 50)
    
    # 检查是否已有离线模型
    if check_offline_model():
        print("\n✅ 离线模型已存在且可用!")
        choice = input("是否重新下载? [y/N]: ").strip().lower()
        if choice not in ['y', 'yes']:
            print("👍 使用现有离线模型")
            return
    
    # 下载模型
    print("\n🚀 开始下载流程...")
    success = download_clip_model()
    
    if success:
        print("\n🎉 模型准备完成!")
        print("现在可以使用离线模式运行程序了")
    else:
        print("\n❌ 模型准备失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 