#!/usr/bin/env python3
"""
📁生成结果整合脚本 - 改进版
使用多维度去重逻辑：文件名 + 文件大小 + 时长
"""

import os
import shutil
from pathlib import Path
import json
from collections import defaultdict
import datetime
import hashlib
try:
    from moviepy.editor import VideoFileClip  # type: ignore
except ImportError as e:
    print(f"❌ 缺少依赖包: {e}")
    print("💡 请运行: uv add moviepy")
    VideoFileClip = None

class ImprovedClassificationIntegrator:
    def __init__(self, source_dir="📁生成结果", target_dir="📁生成结果/【总归类】"):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.video_files = defaultdict(list)
        self.duplicate_files = []
        self.duplicate_groups = []  # 重复文件组
        
    def get_video_fingerprint(self, video_path):
        """获取视频指纹：文件大小 + 时长"""
        try:
            # 获取文件大小
            file_size = video_path.stat().st_size
            
            # 获取视频时长（更准确的判断依据）
            if VideoFileClip is not None:
                with VideoFileClip(str(video_path)) as clip:
                    duration = round(clip.duration, 2)
            else:
                print(f"  ⚠️ MoviePy未安装，无法获取视频时长: {video_path.name}")
                duration = 0
            
            # 生成指纹
            fingerprint = f"{file_size}_{duration}"
            
            return {
                'size': file_size,
                'duration': duration,
                'fingerprint': fingerprint
            }
        except Exception as e:
            print(f"  ⚠️ 获取视频信息失败: {video_path.name} - {str(e)}")
            # fallback：仅使用文件大小
            return {
                'size': video_path.stat().st_size,
                'duration': 0,
                'fingerprint': f"{video_path.stat().st_size}_0"
            }
    
    def is_duplicate_video(self, new_file_info, existing_files):
        """判断是否为重复视频"""
        new_fingerprint = new_file_info['fingerprint']
        
        for existing in existing_files:
            # 1. 文件名完全相同
            if new_file_info['name'] == existing['name']:
                return True, existing, "文件名相同"
            
            # 2. 指纹相同（文件大小 + 时长）
            if new_fingerprint == existing['fingerprint']:
                return True, existing, "文件大小和时长相同"
            
            # 3. 文件名相似且大小接近（可能是同一视频的不同版本）
            if self.is_similar_filename(new_file_info['name'], existing['name']):
                size_diff = abs(new_file_info['size'] - existing['size'])
                if size_diff < 100 * 1024:  # 小于100KB差异
                    return True, existing, "文件名相似且大小接近"
        
        return False, None, ""
    
    def is_similar_filename(self, name1, name2):
        """判断文件名是否相似"""
        # 移除扩展名
        stem1 = Path(name1).stem
        stem2 = Path(name2).stem
        
        # 移除常见的后缀（如 _1, _2, _copy等）
        clean_stem1 = stem1.split('_')[0]
        clean_stem2 = stem2.split('_')[0]
        
        return clean_stem1 == clean_stem2
    
    def scan_classification_results(self):
        """扫描所有分类结果文件夹"""
        print("🔍 扫描分类结果文件夹...")
        
        timestamp_folders = [d for d in self.source_dir.iterdir() 
                           if d.is_dir() and not d.name.startswith("【")]
        
        print(f"📁 发现 {len(timestamp_folders)} 个分类结果文件夹")
        
        primary_tags = {
            "🍼_产品介绍_蕴淳": "🍼_产品介绍_蕴淳",
            "🍼_产品介绍_水奶": "🍼_产品介绍_水奶", 
            "🍼_产品介绍_蓝钻": "🍼_产品介绍_蓝钻",
            "🌟_使用效果": "🌟_使用效果",
            "🎁_促销机制": "🎁_促销机制",
            "🪝_钩子": "🪝_钩子"
        }
        
        # 扫描每个时间戳文件夹
        for folder in sorted(timestamp_folders, key=lambda x: x.name):
            print(f"  📂 扫描: {folder.name}")
            
            for tag_folder in folder.iterdir():
                if tag_folder.is_dir() and tag_folder.name in primary_tags:
                    tag_name = primary_tags[tag_folder.name]
                    
                    for file in tag_folder.iterdir():
                        if file.suffix.lower() == '.mp4':
                            print(f"    🎬 分析视频: {file.name}")
                            
                            # 获取视频指纹
                            video_info = self.get_video_fingerprint(file)
                            
                            file_info = {
                                'name': file.name,
                                'path': file,
                                'folder': folder.name,
                                'tag': tag_name,
                                'size': video_info['size'],
                                'duration': video_info['duration'],
                                'fingerprint': video_info['fingerprint']
                            }
                            
                            # 检查是否重复
                            is_dup, existing_file, reason = self.is_duplicate_video(
                                file_info, self.video_files[tag_name]
                            )
                            
                            if is_dup and existing_file is not None:
                                self.duplicate_files.append({
                                    'name': file.name,
                                    'tag': tag_name,
                                    'folder': folder.name,
                                    'existing_folder': existing_file['folder'],
                                    'reason': reason,
                                    'new_size': file_info['size'],
                                    'new_duration': file_info['duration'],
                                    'existing_size': existing_file['size'],
                                    'existing_duration': existing_file['duration']
                                })
                                print(f"    🔄 重复文件: {reason}")
                            else:
                                self.video_files[tag_name].append(file_info)
                                print(f"    ✅ 新文件: {file.name}")
        
        # 统计信息
        print(f"\n📊 扫描完成统计:")
        total_files = sum(len(files) for files in self.video_files.values())
        print(f"  ✅ 唯一视频文件: {total_files} 个")
        print(f"  🔄 重复文件: {len(self.duplicate_files)} 个")
        
        for tag, files in self.video_files.items():
            print(f"  📋 {tag}: {len(files)} 个文件")
    
    def create_integrated_folder(self):
        """创建【总归类】文件夹"""
        print(f"\n📁 创建【总归类】文件夹: {self.target_dir}")
        
        if self.target_dir.exists():
            shutil.rmtree(self.target_dir)
        
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
        for tag in self.video_files.keys():
            tag_folder = self.target_dir / tag
            tag_folder.mkdir(exist_ok=True)
            print(f"  📂 创建分类文件夹: {tag}")
    
    def copy_files_with_analysis(self):
        """复制视频文件和分析文件"""
        print(f"\n📋 复制文件到【总归类】文件夹...")
        
        copied_files = 0
        failed_files = 0
        
        for tag, files in self.video_files.items():
            tag_folder = self.target_dir / tag
            
            for file_info in files:
                try:
                    # 复制视频文件
                    source_video = file_info['path']
                    target_video = tag_folder / file_info['name']
                    
                    shutil.copy2(source_video, target_video)
                    
                    # 复制对应的JSON分析文件
                    json_name = file_info['name'].replace('.mp4', '_analysis.json')
                    source_json = source_video.parent / json_name
                    target_json = tag_folder / json_name
                    
                    if source_json.exists():
                        shutil.copy2(source_json, target_json)
                    
                    copied_files += 1
                    print(f"  ✅ 复制: {file_info['name']} → {tag}")
                    
                except Exception as e:
                    failed_files += 1
                    print(f"  ❌ 复制失败: {file_info['name']} - {str(e)}")
        
        print(f"\n📊 复制完成:")
        print(f"  ✅ 成功复制: {copied_files} 个文件")
        print(f"  ❌ 复制失败: {failed_files} 个文件")
    
    def generate_detailed_report(self):
        """生成详细报告"""
        print(f"\n📄 生成详细报告...")
        
        report = {
            "integration_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_unique_files": sum(len(files) for files in self.video_files.values()),
            "duplicate_files": len(self.duplicate_files),
            "classifications": {},
            "duplicate_analysis": {}
        }
        
        # 分类统计
        for tag, files in self.video_files.items():
            report["classifications"][tag] = {
                "count": len(files),
                "files": [
                    {
                        "name": f['name'],
                        "size_mb": round(f['size'] / 1024 / 1024, 2),
                        "duration": f['duration'],
                        "source_folder": f['folder']
                    }
                    for f in files
                ]
            }
        
        # 重复文件分析
        duplicate_reasons = defaultdict(int)
        for dup in self.duplicate_files:
            duplicate_reasons[dup['reason']] += 1
        
        report["duplicate_analysis"] = {
            "by_reason": dict(duplicate_reasons),
            "details": self.duplicate_files
        }
        
        # 保存报告
        report_path = self.target_dir / "📊_详细整合报告.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ 详细报告已保存: {report_path}")
        
        # 生成人类可读的汇总
        summary_path = self.target_dir / "📋_去重分析汇总.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("📁生成结果 - 智能去重分析汇总\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"整合时间: {report['integration_time']}\n")
            f.write(f"唯一视频文件: {report['total_unique_files']} 个\n")
            f.write(f"重复文件: {report['duplicate_files']} 个\n\n")
            
            f.write("📊 分类统计:\n")
            for tag, info in report["classifications"].items():
                f.write(f"  {tag}: {info['count']} 个文件\n")
                total_size = sum(f['size_mb'] for f in info['files'])
                total_duration = sum(f['duration'] for f in info['files'])
                f.write(f"    总大小: {total_size:.1f} MB\n")
                f.write(f"    总时长: {total_duration:.1f} 秒\n\n")
            
            f.write("🔄 重复文件分析:\n")
            for reason, count in duplicate_reasons.items():
                f.write(f"  {reason}: {count} 个\n")
            f.write("\n")
            
            f.write("📋 重复文件详情:\n")
            for i, dup in enumerate(self.duplicate_files, 1):
                f.write(f"{i}. {dup['name']} ({dup['tag']})\n")
                f.write(f"   原因: {dup['reason']}\n")
                f.write(f"   保留版本: {dup['existing_folder']} ({dup['existing_size']/1024/1024:.1f}MB, {dup['existing_duration']:.1f}s)\n")
                f.write(f"   跳过版本: {dup['folder']} ({dup['new_size']/1024/1024:.1f}MB, {dup['new_duration']:.1f}s)\n\n")
        
        print(f"  ✅ 去重分析汇总已保存: {summary_path}")
    
    def run(self):
        """执行整合流程"""
        print("🚀 开始智能去重整合📁生成结果...")
        print("=" * 60)
        
        try:
            # 1. 扫描分类结果
            self.scan_classification_results()
            
            # 2. 创建总归类文件夹
            self.create_integrated_folder()
            
            # 3. 复制文件
            self.copy_files_with_analysis()
            
            # 4. 生成详细报告
            self.generate_detailed_report()
            
            print("\n" + "=" * 60)
            print("🎉 智能去重整合完成！")
            print(f"📁 总归类文件夹: {self.target_dir}")
            print(f"📊 唯一视频文件: {sum(len(files) for files in self.video_files.values())}")
            print(f"🔄 重复文件: {len(self.duplicate_files)}")
            
        except Exception as e:
            print(f"❌ 整合失败: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    integrator = ImprovedClassificationIntegrator()
    integrator.run() 