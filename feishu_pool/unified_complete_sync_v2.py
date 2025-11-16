#!/usr/bin/env python3
"""
统一AI视频数据同步器 v2
包含主表(视频基础池)和子表(切片标签池)的完整同步功能
主标签分类功能已移至label_to_classifier模块
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from optimized_data_pool import OptimizedDataPoolManager, VideoBaseRecord, SliceTagRecord

class UnifiedVideoSyncer:
    """统一视频数据同步器"""
    
    def __init__(self):
        self.data_pool = OptimizedDataPoolManager()
        self.project_root = Path('/Users/sshlijy/Desktop/demo')
        self.results = {
            "sync_time": datetime.now().isoformat(),
            "video_base": {},
            "slice_tags": {},
            "tag_classification": {},
            "summary": {
                "total_videos": 0,
                "successful_video_base": 0,
                "failed_video_base": 0,
                "total_slices": 0,
                "successful_slices": 0,
                "failed_slices": 0,
                "total_classifications": 0,
                "successful_classifications": 0,
                "failed_classifications": 0
            }
        }
    
    def get_srt_duration(self, srt_path):
        """从SRT文件获取视频时长"""
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            for line in reversed(lines):
                if '-->' in line:
                    end_time = line.split('-->')[1].strip()
                    time_parts = end_time.replace(',', '.').split(':')
                    if len(time_parts) == 3:
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        seconds = float(time_parts[2])
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        return int(total_seconds)
                    break
        except Exception as e:
            print(f"  ⚠️ 解析SRT时长失败: {e}")
        return 0
    
    def read_srt_content(self, srt_file):
        """读取字幕文件完整内容"""
        try:
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"  📄 字幕内容读取: {len(content)} 字符")
            return content
        except Exception as e:
            print(f"  ❌ 字幕内容读取失败: {e}")
            return ""

    def extract_source_channel(self, srt_content):
        """根据字幕内容推测来源渠道 - 保持为空"""
        # 不进行推断，保持为空，待人工填写
        return ""

    def prepare_video_upload_data(self, video_name):
        """准备视频上传数据（新方法）"""
        print(f"\n🎬 准备上传数据: {video_name}")
        
        # 原始视频文件
        video_file = self.project_root / "🍭Origin" / f"{video_name}.mp4"
        
        # 完整字幕文件  
        srt_file = self.project_root / "📄SRT" / video_name / f"{video_name}_full.srt"
        
        print(f"  📁 视频文件: {video_file.name} ({'存在' if video_file.exists() else '不存在'})")
        print(f"  📄 字幕文件: {srt_file.name} ({'存在' if srt_file.exists() else '不存在'})")
        
        # 获取文件大小和时长
        if video_file.exists():
            file_size_mb = round(video_file.stat().st_size / (1024 * 1024), 1)
            print(f"  📊 文件大小: {file_size_mb}MB")
        else:
            file_size_mb = 0
            print(f"  ❌ 视频文件不存在")
        
        # 从SRT获取时长
        duration = self.get_srt_duration(srt_file) if srt_file.exists() else 0
        print(f"  📊 时长(从SRT): {duration}秒")
        
        # 读取字幕内容
        srt_content = self.read_srt_content(srt_file) if srt_file.exists() else ""
        
        # 设置主题和渠道（保持为空）
        themes = []  # 保持为空，待人工填写
        source_channel = self.extract_source_channel(srt_content)
        
        # 生成视频名称
        if "启赋蕴醇" in srt_content or "蕴醇" in srt_content:
            video_display_name = f"启赋蕴醇产品介绍 - {video_name}"
        elif "妮妮" in srt_content:
            video_display_name = f"启赋奶粉使用效果分享 - {video_name}"
        else:
            video_display_name = f"启赋产品视频 - {video_name}"
        
        print(f"  🏷️ 视频名称: {video_display_name}")
        print(f"  📱 来源渠道: {source_channel if source_channel else '(待填写)'}")
        print(f"  🏷️ 内容主题: {'无' if not themes else ', '.join(themes)}")
        
        return {
            "video_id": video_name,
            "video_name": video_display_name,
            "video_file_path": str(video_file) if video_file.exists() else None,
            "srt_file_path": str(srt_file) if srt_file.exists() else None,
            "srt_content": srt_content,
            "file_size_mb": file_size_mb,
            "duration_seconds": duration,
            "resolution": "1920x1080",
            "source_channel": source_channel,
            "content_themes": themes
        }
    
    def sync_video_base(self, video_names):
        """同步视频基础池主表（使用文件上传功能）"""
        print(f"\n📄 第一阶段：同步视频基础池主表")
        print("=" * 50)
        
        success_count = 0
        
        for video_name in video_names:
            try:
                # 准备上传数据
                upload_data = self.prepare_video_upload_data(video_name)
                
                # 同步到飞书（使用现有7个字段）
                print(f"\n🔄 同步主表到飞书: {video_name}")
                record_id = self.data_pool.add_video_base_record_with_content(
                    video_id=upload_data["video_id"],
                    video_name=upload_data["video_name"],
                    video_file_path=upload_data["video_file_path"],
                    srt_content=upload_data["srt_content"],
                    file_size_mb=upload_data["file_size_mb"],
                    duration_seconds=upload_data["duration_seconds"],
                    resolution=upload_data["resolution"]
                )
                
                if record_id:
                    success_count += 1
                    self.results["video_base"][video_name] = {
                        "status": "success",
                        "record_id": record_id,
                        "file_size_mb": upload_data["file_size_mb"],
                        "duration_seconds": upload_data["duration_seconds"]
                    }
                    print(f"  ✅ 主表同步成功 → {record_id}")
                    print(f"  📁 视频文件: {'已上传' if upload_data['video_file_path'] else '无'}")
                    print(f"  📝 字幕内容: {'已存储' if upload_data['srt_content'] else '无'}")
                else:
                    self.results["video_base"][video_name] = {"status": "failed", "error": "飞书API失败"}
                    print(f"  ❌ 主表同步失败")
                    
            except Exception as e:
                self.results["video_base"][video_name] = {"status": "failed", "error": str(e)}
                print(f"  ❌ 主表异常: {e}")
        
        self.results["summary"]["successful_video_base"] = success_count
        self.results["summary"]["failed_video_base"] = len(video_names) - success_count
        
        print(f"\n📊 主表同步完成:")
        print(f"  ✅ 成功: {success_count}/{len(video_names)}")
        print(f"  ❌ 失败: {len(video_names) - success_count}")
        
        return self.results["video_base"]

    def get_slice_data(self, video_name):
        """获取切片数据和AI分析结果"""
        slice_dir = self.project_root / "🎬Slice" / video_name
        
        segments = None
        
        # 优先尝试语义合并报告
        merge_reports = list(slice_dir.glob("semantic_merge_report_*.json"))
        if merge_reports:
            report_file = merge_reports[0]
            print(f"  📄 使用语义合并报告: {report_file.name}")
        
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            segments = data.get('segments', [])
        except Exception as e:
            print(f"  ❌ 读取语义合并报告失败: {e}")
            segments = None
        
        # 如果没有语义合并报告或读取失败，使用备用数据源
        if segments is None:
            # 使用video_slices.json作为备用数据源
            slices_file = slice_dir / f"{video_name}_slices.json"
            if not slices_file.exists():
                print(f"  ❌ 未找到切片数据文件: {slice_dir}")
                return None, {}
            
            print(f"  📄 使用切片数据文件: {slices_file.name}")
            
            try:
                with open(slices_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                segments = data.get('slices', [])
            except Exception as e:
                print(f"  ❌ 读取切片数据失败: {e}")
                return None, {}
        
        # 获取AI分析结果
        analysis_dir = slice_dir / 'slices'
        analysis_files = list(analysis_dir.glob('*_analysis.json'))
        ai_results = {}
        
        for analysis_file in analysis_files:
            try:
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)
                filename = analysis_file.name.replace('_analysis.json', '.mp4')
                ai_results[filename] = analysis_data
            except Exception as e:
                print(f"  ⚠️ 读取AI分析失败: {analysis_file.name} - {e}")
        
        print(f"  📊 发现 {len(segments)} 个切片段, {len(ai_results)} 个AI分析")
        return segments, ai_results
    
    def extract_subtitle_for_timespan(self, video_name, start_time, end_time):
        """从SRT文件中提取指定时间段的字幕文本"""
        try:
            srt_file = self.project_root / "📄SRT" / video_name / f"{video_name}_full.srt"
            if not srt_file.exists():
                return ""
            
            with open(srt_file, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # 解析SRT文件
            subtitle_blocks = []
            current_block = {}
            lines = srt_content.strip().split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                
                # 序号行
                if line.isdigit():
                    current_block = {'index': int(line)}
                    i += 1
                    continue
                
                # 时间戳行
                if '-->' in line:
                    time_parts = line.split(' --> ')
                    if len(time_parts) == 2:
                        start_ts = self.parse_srt_timestamp(time_parts[0])
                        end_ts = self.parse_srt_timestamp(time_parts[1])
                        current_block['start'] = start_ts
                        current_block['end'] = end_ts
                    i += 1
                    continue
                
                # 字幕文本行
                text_lines = []
                while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                    text_lines.append(lines[i].strip())
                    i += 1
                
                if text_lines:
                    current_block['text'] = ' '.join(text_lines)
                    subtitle_blocks.append(current_block)
                    current_block = {}
            
            # 查找与时间段重叠的字幕
            matching_texts = []
            for block in subtitle_blocks:
                if 'start' in block and 'end' in block and 'text' in block:
                    # 检查时间段是否有重叠
                    if (block['start'] <= end_time and block['end'] >= start_time):
                        matching_texts.append(block['text'])
            
            return ' '.join(matching_texts)
        
        except Exception as e:
            print(f"  ⚠️ 提取字幕失败: {e}")
            return ""
    
    def parse_srt_timestamp(self, timestamp_str):
        """解析SRT时间戳为秒数"""
        try:
            # 格式: 00:00:12,098
            time_part, ms_part = timestamp_str.split(',')
            h, m, s = map(int, time_part.split(':'))
            ms = int(ms_part)
            return h * 3600 + m * 60 + s + ms / 1000.0
        except:
            return 0.0
    
    def _check_slice_quality(self, ai_result):
        """检测切片质量，返回无效原因或None"""
        try:
            # 检查AI分析结果中的object字段
            object_text = ai_result.get('object', '')
            if not object_text:
                return None  # 没有object字段，允许通过
            
            object_lower = object_text.lower()
            
            # 检测没有人物的切片
            if "无人物-无效切片" in object_text:
                return "无人物"
            
            # 检测多场景切片  
            if "多场景-无效切片" in object_text:
                return "多场景"
            
            # 补充检测：如果object中明确只提到物体而没有人物动作
            no_person_indicators = ["物体", "食物", "水果", "静物", "产品特写", "仅有产品", "只有物品", "没有人物", "无人出现", "仅有", "只有产品"]
            person_indicators = ["宝宝", "妈妈", "爸爸", "医生", "护士", "人", "婴儿", "孩子", "女人", "男人", "专家"]
            
            has_person = any(indicator in object_lower for indicator in person_indicators)
            has_only_objects = any(indicator in object_lower for indicator in no_person_indicators)
            
            # 增强检测：包含"没有人"或"无人"等明确表述
            no_person_phrases = ["没有人", "无人", "没有人物", "无人物", "人物出现"]
            has_no_person_phrase = any(phrase in object_lower for phrase in no_person_phrases)
            
            if has_only_objects and not has_person:
                return "仅物体无人物"
            
            if has_no_person_phrase:
                return "明确无人物"
            
            # 检测场景切换关键词
            scene_switch_indicators = ["场景切换", "画面跳转", "突兀", "不连贯", "多个场景", "场景变化"]
            if any(indicator in object_lower for indicator in scene_switch_indicators):
                return "场景切换突兀"
            
            # 检查quality_status字段（如果存在）
            quality_status = ai_result.get('quality_status', '')
            if quality_status == '无效':
                invalid_reason = ai_result.get('invalid_reason', '未知原因')
                return invalid_reason
            
            return None  # 通过质量检测
            
        except Exception as e:
            print(f"  ⚠️ 质量检测异常: {e}")
            return None  # 异常时允许通过
    
    def build_slice_record(self, video_name, segment, ai_result):
        """构建切片标签记录（含质量控制检测）"""
        filename = Path(segment['file_path']).name
        
        # 🚨 质量控制检测
        is_invalid_slice = self._check_slice_quality(ai_result)
        
        if is_invalid_slice:
            # 跳过无效切片，返回None表示不处理
            print(f"  🚨 跳过无效切片: {filename} - {is_invalid_slice}")
            return None
        
        # 提取AI标签
        sub_tags = []
        if 'object' in ai_result:
            sub_tags.append(f"对象: {ai_result['object']}")
        if 'scene' in ai_result:
            sub_tags.append(f"场景: {ai_result['scene']}")
        if 'emotion' in ai_result:
            sub_tags.append(f"情绪: {ai_result['emotion']}")
        if 'brand_elements' in ai_result:
            sub_tags.append(f"品牌: {ai_result['brand_elements']}")
        
        # 提取对应时间段的字幕文本
        subtitle_text = self.extract_subtitle_for_timespan(
            video_name, 
            segment['start_time'], 
            segment['end_time']
        )
        
        return SliceTagRecord(
            slice_id=f"{video_name}_{filename}",
            video_id=video_name,
            slice_name=filename,
            start_time=segment['start_time'],
            end_time=segment['end_time'],
            duration_seconds=segment['duration'],
            main_category="",  # 保持空白，待人工标注
            sub_tags=sub_tags,
            subtitle_text=subtitle_text,  # 现在包含对应时间段的字幕
            confidence_score=ai_result.get('confidence_score', 0.8),
            annotation_status="待标注",
            review_status="待审核"
        )
    
    def sync_slice_tags(self, video_name):
        """同步单个视频的切片标签"""
        print(f"\n✂️ 同步切片标签: {video_name}")
        print("-" * 40)
        
        # 获取切片数据
        segments, ai_results = self.get_slice_data(video_name)
        if not segments:
            return {"success": 0, "failed": 0, "error": "无切片数据"}
        
        success_count = 0
        failed_count = 0
        slice_results = {}
        skipped_count = 0  # 添加跳过计数
        
        # 🔧 修复：直接使用用户友好的video_name作为关联ID
        # 不再查询主视频记录ID，直接使用video_name进行关联
        print(f"  🔗 使用用户友好ID进行关联: {video_name}")

        # 开始处理切片
        for i, segment in enumerate(segments, 1):
            filename = Path(segment['file_path']).name
            
            if i <= 3:  # 只显示前3个的详细信息
                print(f"\n🔄 [{i:2d}/{len(segments)}] {filename}")
            
            try:
                # 获取AI分析结果
                ai_result = ai_results.get(filename, {})
                
                # 🔍 调试输出
                if i <= 3:
                    print(f"  🔍 文件名: '{filename}'")
                    print(f"     AI分析结果存在: {filename in ai_results}")
                    print(f"     AI结果内容: {ai_result}")
                
                # 创建切片记录（包含质量控制检测）
                slice_record = self.build_slice_record(video_name, segment, ai_result)
                
                # 🚨 如果返回None，说明是无效切片，跳过处理
                if slice_record is None:
                    skipped_count += 1
                    slice_results[filename] = {"status": "skipped", "reason": "无效切片"}
                    continue
                
                # 🔧 修复：保持用户友好的video_name作为关联ID
                slice_record.video_id = video_name
                
                if i <= 3:
                    print(f"  📊 时间: {segment['start_time']:.1f} - {segment['end_time']:.1f}秒")
                    print(f"  🏷️ AI标签: {len(slice_record.sub_tags)} 个")
                    print(f"  🏷️ 子标签列表: {slice_record.sub_tags}")
                    file_size_mb = segment.get('file_size', 0) / (1024 * 1024)
                    print(f"  📦 文件大小: {file_size_mb:.1f}MB")
                
                # 同步到飞书（带切片文件上传）
                slice_file_path = segment['file_path']  # 从segment获取切片文件路径
                record_id = self.data_pool.add_slice_tag_record(slice_data=slice_record, slice_file_path=slice_file_path)
                
                if record_id:
                    success_count += 1
                    slice_results[filename] = {
                        "status": "success", 
                        "record_id": record_id,
                        "ai_tags": len(slice_record.sub_tags)
                    }
                    if i <= 3:
                        print(f"  ✅ 子表同步成功 → {record_id}")
                else:
                    failed_count += 1
                    slice_results[filename] = {"status": "failed", "error": "飞书API失败"}
                    if i <= 3:
                        print(f"  ❌ 子表同步失败")
                        
            except Exception as e:
                failed_count += 1
                slice_results[filename] = {"status": "failed", "error": str(e)}
                if i <= 3:
                    print(f"  ❌ 子表异常: {e}")
        
        if len(segments) > 3:
            print(f"\n⏩ 继续同步其余 {len(segments)-3} 个切片...")
        
        # 计算处理后的有效切片数量
        valid_segments = len(segments) - skipped_count
        success_rate = (success_count / valid_segments * 100) if valid_segments > 0 else 0
        
        print(f"\n📊 {video_name} 子表同步完成:")
        print(f"  📊 原始切片: {len(segments)} 个")
        print(f"  🚨 跳过无效: {skipped_count} 个")
        print(f"  📝 有效处理: {valid_segments} 个")
        print(f"  ✅ 成功上传: {success_count}")
        print(f"  ❌ 失败: {failed_count}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return {
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "total": len(segments),
            "valid_total": valid_segments,
            "success_rate": success_rate,
            "results": slice_results
        }
    
    def sync_all_slice_tags(self, video_names):
        """同步所有视频的切片标签（包含AI标签切片 + 产品介绍切片）"""
        print(f"\n✂️ 第二阶段：同步切片标签池子表")
        print("=" * 50)
        
        total_success = 0
        total_failed = 0
        total_slices = 0
        total_product_success = 0
        total_product_failed = 0
        total_product_slices = 0
        
        for video_name in video_names:
            # 检查该视频是否有切片数据
            slice_dir = self.project_root / "🎬Slice" / video_name
            if not slice_dir.exists():
                print(f"⚠️ 跳过 {video_name}：无切片数据目录")
                continue
                
            # 第一部分：AI标签切片（常规切片）
            result = self.sync_slice_tags(video_name)
            if "slice_tags" not in self.results:
                self.results["slice_tags"] = {}
            self.results["slice_tags"][video_name] = result
            
            total_slices += result.get("total", 0)
            total_success += result.get("success", 0)
            total_failed += result.get("failed", 0)
        
            # 第二部分：产品介绍切片
            product_result = self.sync_product_slices(video_name)
            if "product_slices" not in self.results:
                self.results["product_slices"] = {}
            self.results["product_slices"][video_name] = product_result
            
            total_product_slices += product_result.get("total", 0)
            total_product_success += product_result.get("success", 0)
            total_product_failed += product_result.get("failed", 0)
        
        # 更新汇总统计
        self.results["summary"]["total_slices"] = total_slices
        self.results["summary"]["successful_slices"] = total_success
        self.results["summary"]["failed_slices"] = total_failed
        self.results["summary"]["total_product_slices"] = total_product_slices
        self.results["summary"]["successful_product_slices"] = total_product_success
        self.results["summary"]["failed_product_slices"] = total_product_failed
        
        # 总计
        grand_total = total_slices + total_product_slices
        grand_success = total_success + total_product_success
        grand_failed = total_failed + total_product_failed
        
        print(f"\n📊 所有子表同步完成:")
        print(f"  🎯 AI标签切片: {total_slices} 总数, ✅ {total_success} 成功, ❌ {total_failed} 失败")
        print(f"  🍼 产品介绍切片: {total_product_slices} 总数, ✅ {total_product_success} 成功, ❌ {total_product_failed} 失败")
        print(f"  📈 总计: {grand_total} 总数, ✅ {grand_success} 成功, ❌ {grand_failed} 失败")
        
        if grand_total > 0:
            overall_rate = (grand_success / grand_total) * 100
            print(f"  📊 总体成功率: {overall_rate:.1f}%")
        
        return {
            "slice_tags": self.results["slice_tags"],
            "product_slices": self.results["product_slices"]
        }
    
    def sync_product_slices(self, video_name):
        """同步产品介绍切片（含专用字幕）"""
        print(f"\n🍼 同步产品介绍切片: {video_name}")
        print("-" * 40)
        
        # 检查产品介绍目录
        product_dir = self.project_root / "🎬Slice" / video_name / "product"
        if not product_dir.exists():
            print(f"  📁 无产品介绍目录: {product_dir}")
            return {"success": 0, "failed": 0, "error": "无产品介绍目录"}
        
        # 获取所有产品介绍文件
        product_files = {}
        for mp4_file in product_dir.glob("*.mp4"):
            base_name = mp4_file.stem  # 文件名不含扩展名
            json_file = product_dir / f"{base_name}.json"
            srt_file = product_dir / f"{base_name}.srt"
            
            if json_file.exists():
                product_files[base_name] = {
                    "mp4": mp4_file,
                    "json": json_file,
                    "srt": srt_file if srt_file.exists() else None
                }
        
        if not product_files:
            print(f"  📁 无产品介绍文件: {product_dir}")
            return {"success": 0, "failed": 0, "error": "无产品介绍文件"}
        
        print(f"  📊 发现 {len(product_files)} 个产品介绍切片")
        
        success_count = 0
        failed_count = 0
        product_results = {}
        
        for i, (base_name, files) in enumerate(product_files.items(), 1):
            print(f"\n🔄 [{i:2d}/{len(product_files)}] {base_name}")
            
            try:
                # 读取JSON分析结果
                with open(files["json"], 'r', encoding='utf-8') as f:
                    product_data = json.load(f)
                
                # 提取时间信息
                timing_info = product_data.get('timing_info', {})
                duration = timing_info.get('duration_seconds', 0)
                
                # 解析时间戳格式（如 "00:34.825" -> 34.825秒）
                start_time_str = timing_info.get('start_time', '00:00.000')
                end_time_str = timing_info.get('end_time', '00:00.000')
                
                def parse_time_str(time_str):
                    """解析 '00:34.825' 格式的时间为秒数"""
                    try:
                        parts = time_str.split(':')
                        if len(parts) == 2:
                            minutes = int(parts[0])
                            seconds = float(parts[1])
                            return minutes * 60 + seconds
                        return 0
                    except:
                        return 0
                
                start_time = parse_time_str(start_time_str)
                end_time = parse_time_str(end_time_str)
                
                # 读取产品字幕内容
                product_subtitle_content = ""
                if files["srt"]:
                    try:
                        with open(files["srt"], 'r', encoding='utf-8') as f:
                            raw_content = f.read()
                        
                        # 清理字幕内容：去掉注释部分，只保留SRT格式内容
                        product_subtitle_content = self._clean_srt_content(raw_content)
                        print(f"  📝 加载产品字幕: {len(product_subtitle_content)} 字符 (已清理)")
                    except Exception as e:
                        print(f"  ⚠️ 读取字幕失败: {e}")
                
                # 提取品牌分析
                product_analysis = product_data.get('product_analysis', {})
                brand_name = product_analysis.get('product_brand_type', '')
                confidence = product_analysis.get('confidence_score', 0.9)
                
                # 构建AI子标签
                ai_sub_tags = [f"品牌: {brand_name}"] if brand_name else []
                
                # 获取文件大小
                file_size = files["mp4"].stat().st_size / (1024 * 1024)  # MB
                
                print(f"  📊 时间: {start_time:.1f} - {end_time:.1f}秒 ({duration:.1f}秒)")
                print(f"  🏷️ 品牌: {brand_name or '未识别'}")
                print(f"  📦 文件大小: {file_size:.1f}MB")
                
                # 使用新的参数格式添加记录
                record_id = self.data_pool.add_slice_tag_record(
                    video_id=video_name,
                    slice_name=f"{base_name}.mp4",
                    slice_file_path=str(files["mp4"]),
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration,
                    file_size_mb=file_size,
                    main_tag="🍼 产品介绍",  # 使用标准化格式（注意空格）
                    ai_sub_tags=ai_sub_tags,
                    confidence=confidence,
                    slice_type="product",
                    product_subtitle_content=product_subtitle_content  # 产品字幕内容
                )
                
                if record_id:
                    success_count += 1
                    product_results[base_name] = {
                        "status": "success",
                        "record_id": record_id,
                        "brand": brand_name,
                        "has_subtitle": bool(product_subtitle_content)
                    }
                    print(f"  ✅ 产品切片同步成功 → {record_id}")
                else:
                    failed_count += 1
                    product_results[base_name] = {"status": "failed", "error": "飞书API失败"}
                    print(f"  ❌ 产品切片同步失败")
                    
            except Exception as e:
                failed_count += 1
                product_results[base_name] = {"status": "failed", "error": str(e)}
                print(f"  ❌ 产品切片异常: {e}")
        
        success_rate = (success_count / len(product_files) * 100) if product_files else 0
        
        print(f"\n📊 {video_name} 产品介绍同步完成:")
        print(f"  ✅ 成功: {success_count}")
        print(f"  ❌ 失败: {failed_count}")
        print(f"  成功率: {success_rate:.1f}%")
        
        return {
            "success": success_count,
            "failed": failed_count,
            "total": len(product_files),
            "success_rate": success_rate,
            "results": product_results
        }
    
    def _clean_srt_content(self, raw_content: str) -> str:
        """清理SRT内容，去掉注释部分，只保留纯净的SRT格式内容"""
        lines = raw_content.split('\n')
        cleaned_lines = []
        found_srt_start = False
        
        for line in lines:
            line = line.strip()
            
            # 跳过注释行（以 # 开头）
            if line.startswith('#'):
                continue
            
            # 跳过空行，直到找到SRT开始（数字行）
            if not found_srt_start:
                if line and line.isdigit():
                    found_srt_start = True
                    cleaned_lines.append(line)
                elif line and not line.startswith('#'):
                    # 如果遇到非注释、非空行，也开始收集
                    found_srt_start = True
                    cleaned_lines.append(line)
            else:
                # 已经开始收集SRT内容
                cleaned_lines.append(line)
        
        # 移除开头和结尾的空行
        while cleaned_lines and not cleaned_lines[0]:
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)
    
    def run_intelligent_tag_classification(self):
        """第三阶段：智能标签分类（调用label_to_classifier模块）"""
        print(f"\n🤖 第三阶段：智能标签分类")
        print("=" * 50)
        print(f"ℹ️  主标签分类功能已移至独立的 label_to_classifier 模块")
        print(f"🔧 请手动运行: cd ../label_to_classifier && python run.py")
        print(f"📋 此功能专注于本地JSON文件的主标签标注")
        
        # 模拟一个简单的统计
        classification_results = {
            "status": "skipped",
            "message": "主标签分类功能已移至label_to_classifier模块",
            "recommendation": "请使用 label_to_classifier/run.py 进行主标签分类"
        }
        
        # 更新结果统计
        self.results["tag_classification"] = classification_results
        self.results["summary"]["total_classifications"] = 0
        self.results["summary"]["successful_classifications"] = 0  
        self.results["summary"]["failed_classifications"] = 0
        
        print(f"\n📊 智能标签分类状态:")
        print(f"  📋 状态: 已跳过（功能独立）")
        print(f"  🎯 建议: 运行 label_to_classifier 模块进行主标签分类")
        print(f"  📍 位置: ../label_to_classifier/run.py")
        
        return classification_results
    
    def verify_sync_results(self):
        """验证同步结果"""
        print(f"\n🔍 第四阶段：验证同步结果")
        print("=" * 50)
        
        try:
            # 验证主表
            video_records = self.data_pool.query_records('video_base')
            print(f"📄 主表总记录数: {len(video_records)}")
            
            video_count = 0
            for record in video_records:
                fields = record.get('fields', {})
                video_id = fields.get('video_ID', 'N/A')
                if video_id.startswith('video_'):
                    video_count += 1
                    size = fields.get('文件大小MB', 0)
                    duration = fields.get('视频时长秒', 0)
                    print(f"  ✅ {video_id}: {size}MB, {duration}秒")
            
            # 验证子表
            slice_records = self.data_pool.query_records('slice_tag')
            print(f"\n✂️ 子表总记录数: {len(slice_records)}")
            
            slice_count = 0
            for record in slice_records:
                fields = record.get('fields', {})
                video_id = fields.get('关联video_ID', 'N/A')
                if video_id.startswith('video_'):
                    slice_count += 1
            
            print(f"  ✅ 有效切片记录: {slice_count}条")
            
            print(f"\n🎯 关联一致性:")
            print(f"  📄 主表视频: {video_count}")
            print(f"  ✂️ 子表切片: {slice_count}")
            print(f"  🔗 关联状态: {'✅ 一致' if slice_count > 0 else '⚠️ 需检查'}")
            
        except Exception as e:
            print(f"❌ 验证失败: {e}")

    def run_complete_sync(self):
        """运行完整的统一同步"""
        print("🚀 统一AI视频数据同步器 v2")
        print("=" * 60)
        print("📋 功能: 主表(视频基础池) + 子表(切片标签池)")
        print("🎯 策略: 原始视频+完整字幕 + 切片数据+AI分析")
        print("=" * 60)
        
        # 测试连接
        print("🔧 测试飞书连接...")
        if not self.data_pool.test_connection():
            print("❌ 飞书连接失败")
            return None
        print("✅ 飞书连接正常")
        
        # 确定要同步的视频
        video_names = ["video_1"]
        self.results["summary"]["total_videos"] = len(video_names)
        
        print(f"\n📁 要同步的视频: {video_names}")
        
        try:
            # 第一阶段：同步主表
            self.sync_video_base(video_names)
            
            # 第二阶段：同步子表
            self.sync_all_slice_tags(video_names)
            
            # 第三阶段：智能标签分类（已移至label_to_classifier模块）
            self.run_intelligent_tag_classification()
            
            # 第四阶段：验证结果
            self.verify_sync_results()
            
            # 保存结果
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_file = f"unified_complete_sync_result_{timestamp}.json"
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
            print(f"\n📄 统一同步结果已保存: {result_file}")
            print(f"🔗 飞书数据池访问: https://feishu.cn/base/OPrUb7H2vanihWsLtuhcEqCunbd")
            
            # 最终总结
            print(f"\n🎉 统一同步完成!")
            print("=" * 60)
            summary = self.results["summary"]
            print(f"📊 总体统计:")
            print(f"  🎬 视频总数: {summary['total_videos']}")
            print(f"  📄 主表成功: {summary['successful_video_base']}")
            print(f"  ✂️ 切片总数: {summary['total_slices']}")
            print(f"  ✂️ 子表成功: {summary['successful_slices']}")
            print(f"  🤖 智能分类总数: {summary['total_classifications']}")
            print(f"  🤖 分类成功: {summary['successful_classifications']}")
            
            if summary['total_slices'] > 0:
                overall_rate = (summary['successful_slices'] / summary['total_slices']) * 100
                print(f"  📈 数据同步成功率: {overall_rate:.1f}%")
            
            if summary['total_classifications'] > 0:
                classification_rate = (summary['successful_classifications'] / summary['total_classifications']) * 100
                print(f"  🧠 智能分类成功率: {classification_rate:.1f}%")
            
            print(f"\n📱 后续操作建议:")
            print(f"  1. 访问飞书表格验证数据完整性")
            print(f"  2. 检查AI智能分类的主标签类别结果") 
            print(f"  3. 人工审核和优化需要的分类结果")
            print(f"  4. 根据业务需求调整分类策略")
            
            return self.results
            
        except Exception as e:
            print(f"❌ 统一同步异常: {e}")
            return None

def main():
    """主函数"""
    syncer = UnifiedVideoSyncer()
    return syncer.run_complete_sync()

if __name__ == "__main__":
    main()