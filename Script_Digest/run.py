#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Digest - 视频脚本智能匹配系统
主入口程序：提供用户友好的脚本输入界面和完整的匹配流程
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent / 'src'))

from src.env_loader import get_api_keys
from src.script_parser import ScriptParser
from src.json_analyzer import JsonAnalyzer
from src.video_matcher import VideoMatcher
from src.file_organizer import FileOrganizer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/script_digest.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ScriptDigestMain:
    """Script Digest 主程序类"""
    
    def __init__(self):
        """初始化主程序"""
        self.ensure_directories()
        self.script_parser = ScriptParser()
        # json_analyzer 和 video_matcher 将在需要时创建
        self.json_analyzer = None
        self.video_matcher = None
        
        logger.info("🚀 Script Digest 系统初始化完成")
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        dirs = ['logs', 'data/input', 'data/output', 'cache']
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def get_default_script(self) -> Dict[str, str]:
        """获取默认脚本段落"""
        # 尝试从配置文件加载脚本
        config_file = Path(__file__).parent / 'config' / 'my_script.json'
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    script_data = json.load(f)
                logger.info(f"✅ 从配置文件加载脚本: {config_file}")
                return script_data
            except Exception as e:
                logger.warning(f"⚠️ 读取脚本配置文件失败: {e}，使用内置默认脚本")
        
        # 如果配置文件不存在或读取失败，使用内置默认脚本
        logger.info("📝 使用内置默认脚本")
        return {
            "1️⃣": "狗都不，生！生的就是纯奶粉喂养八斤八两的大胖娃！",
            "2️⃣": "能自己喂肯定是更好的，但凡你决定了奶粉喂养，就一定要选有百年科研实力，专业渠道也认可的品牌。",
            "3️⃣": "怕你走弯路，我必须再多嘴两句，配方你肯定是越看越花眼 越做功课越不会选，其实！你只要关注有没有 HMO，以及 HMO 的科研背景就够了！",
            "4️⃣": "毕竟是宝宝进嘴的东西，启赋背靠惠氏制药背景，做起奶粉降维打击，对 HMO 的研究比我岁数都长！",
            "5️⃣": "你就问问身边吃奶启赋的妈妈们吧，个个养成小肉宝，娃是越来越好带了，妈也越来越美了。",
            "6️⃣": "选奶关键的就是不试错，你不冲我可要冲了！"
        }

    def save_script_to_config(self, script_data: Dict[str, str]) -> bool:
        """保存脚本内容到配置文件"""
        config_file = Path(__file__).parent / 'config' / 'my_script.json'
        
        try:
            # 确保config目录存在
            config_file.parent.mkdir(exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(script_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 脚本已保存到配置文件: {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存脚本配置文件失败: {e}")
            return False

    def get_user_script_input(self) -> Optional[Dict[str, str]]:
        """获取用户脚本输入"""
        print("\n" + "="*60)
        print("🎬 Script Digest - 视频脚本智能匹配系统")
        print("="*60)
        
        # 显示默认脚本选项
        default_script = self.get_default_script()
        print("\n📝 脚本输入选择：")
        print("1. 使用默认脚本（推荐）")
        print("2. 自定义输入脚本")
        print("\n🎯 默认脚本预览：")
        for segment_id, content in default_script.items():
            preview = content if len(content) <= 30 else content[:30] + "..."
            print(f"   {segment_id}: {preview}")
        
        # 获取用户选择
        while True:
            try:
                choice = input("\n请选择 (1-默认脚本 / 2-自定义输入): ").strip()
                
                if choice == "1":
                    print("✅ 使用默认脚本")
                    return default_script
                
                elif choice == "2":
                    print("✅ 选择自定义输入")
                    break
                
                else:
                    print("❌ 无效选择，请输入 1 或 2")
                    continue
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户取消选择")
                return None
            except Exception as e:
                print(f"❌ 输入错误：{e}")
                continue
        
        # 自定义输入流程
        print("\n📝 自定义脚本输入")
        print("💡 格式说明：")
        print("   - 每行一个段落")
        print("   - 格式：段落ID:段落内容") 
        print("   - 示例：1️⃣:狗都不，生！")
        print("   - 输入空行结束输入")
        print("\n🎯 要获得文件夹【1狗都不...】【2能自己...】格式，")
        print("   请使用 1️⃣、2️⃣ 等作为段落ID")
        print("\n开始输入：")
        
        script_segments = {}
        line_count = 0
        
        while True:
            try:
                line_count += 1
                user_input = input(f"{line_count:2d}> ").strip()
                
                if not user_input:  # 空行表示结束输入
                    break
                
                if ':' not in user_input:
                    print("⚠️  格式错误！请使用'段落ID:段落内容'格式")
                    line_count -= 1
                    continue
                
                # 分割ID和内容
                parts = user_input.split(':', 1)
                segment_id = parts[0].strip()
                content = parts[1].strip()
                
                if not segment_id or not content:
                    print("⚠️  段落ID和内容都不能为空")
                    line_count -= 1
                    continue
                
                script_segments[segment_id] = content
                print(f"✅ 已添加：{segment_id} -> {content}")
                
            except KeyboardInterrupt:
                print("\n\n👋 用户取消输入")
                return None
            except Exception as e:
                print(f"❌ 输入错误：{e}")
                line_count -= 1
                continue
        
        if not script_segments:
            print("⚠️  没有输入任何脚本段落")
            return None

        # 询问是否保存为默认脚本
        print(f"\n✅ 已输入 {len(script_segments)} 个脚本段落")
        try:
            save_choice = input("💾 是否将此脚本保存为新的默认脚本？(y/N): ").strip().lower()
            if save_choice in ['y', 'yes', '是']:
                if self.save_script_to_config(script_segments):
                    print("✅ 脚本已保存！下次运行时将自动使用这个脚本作为默认选项。")
                else:
                    print("❌ 脚本保存失败，但不影响当前运行。")
        except KeyboardInterrupt:
            print("\n跳过保存...")
        
        return script_segments
    
    def get_video_slices_directory(self) -> Optional[str]:
        """获取视频切片目录"""
        print("\n📁 请输入视频切片目录路径：")
        print("💡 该目录应包含大量的 *_analysis.json 文件")
        
        # 提供一些默认选项
        default_options = [
            "🎬Slice",
            "../🎬Slice", 
            "data/input",
        ]
        
        print("🔍 常用选项：")
        for i, option in enumerate(default_options, 1):
            if Path(option).exists():
                json_count = len(list(Path(option).glob("**/*_analysis.json")))
                print(f"  {i}. {option} (发现 {json_count} 个JSON文件)")
            else:
                print(f"  {i}. {option} (目录不存在)")
        
        print("  0. 手动输入路径")
        
        while True:
            try:
                choice = input("\n请选择 (0-{max_choice}): ".format(max_choice=len(default_options))).strip()
                
                if choice == "0":
                    custom_path = input("请输入自定义路径: ").strip()
                    if custom_path and Path(custom_path).exists():
                        return custom_path
                    else:
                        print("❌ 路径不存在，请重新输入")
                        continue
                
                elif choice.isdigit() and 1 <= int(choice) <= len(default_options):
                    selected_path = default_options[int(choice) - 1]
                    if Path(selected_path).exists():
                        return selected_path
                    else:
                        print("❌ 所选路径不存在，请重新选择")
                        continue
                else:
                    print("❌ 无效选择，请重新输入")
                    continue
                    
            except KeyboardInterrupt:
                print("\n👋 用户取消选择")
                return None
            except Exception as e:
                print(f"❌ 输入错误：{e}")
                continue
    
    def get_output_directory(self) -> str:
        """获取输出目录"""
        default_output = "data/output"
        
        user_input = input(f"\n📤 输出目录 (默认: {default_output}): ").strip()
        return user_input if user_input else default_output
    
    def run_full_pipeline(self):
        """运行完整的匹配流程"""
        try:
            # 1. 获取用户脚本输入
            script_segments = self.get_user_script_input()
            if not script_segments:
                print("❌ 没有有效的脚本输入，程序退出")
                return
            
            print(f"\n✅ 成功输入 {len(script_segments)} 个脚本段落")
            
            # 2. 获取视频切片目录
            video_dir = self.get_video_slices_directory()
            if not video_dir:
                print("❌ 没有选择视频切片目录，程序退出")
                return
            
            # 3. 获取输出目录
            output_dir = self.get_output_directory()
            
            # 4. 开始处理
            print("\n" + "="*60)
            print("🚀 开始处理流程...")
            print("="*60)
            
            # 5. 解析脚本
            print("\n📝 第1步：解析脚本段落...")
            analyzed_script = self.script_parser.parse_script(script_segments)
            if not analyzed_script:
                print("❌ 脚本解析失败")
                return
            print(f"✅ 脚本解析完成，共 {len(analyzed_script)} 个段落")
            
            # 6. 分析视频JSON文件
            print(f"\n🎬 第2步：扫描视频切片目录 {video_dir}...")
            self.json_analyzer = JsonAnalyzer(video_dir)
            parsed_count = self.json_analyzer.scan_and_parse_all()
            if parsed_count == 0:
                print("❌ 未找到有效的视频切片JSON文件")
                return
            video_slices = self.json_analyzer.get_all_slices()
            print(f"✅ 找到 {len(video_slices)} 个视频切片")
            
            # 7. 执行匹配
            print(f"\n🎯 第3步：执行AI语义匹配...")
            self.video_matcher = VideoMatcher(
                enable_pre_filter=True,
                keyword_threshold=0.15,
                output_dir=output_dir,
                enable_reference_copy=True
            )
            match_results = self.video_matcher.match_script_to_videos(analyzed_script, video_slices)
            if not match_results:
                print("❌ 匹配过程失败")
                return
            
            # 统计匹配结果
            total_matches = sum(len(result['best_matches']) for result in match_results)
            print(f"✅ 匹配完成，共找到 {total_matches} 个匹配的视频片段")
            
            # 8. 组织文件
            print(f"\n📁 第4步：组织匹配的视频文件到 {output_dir}...")
            organizer = FileOrganizer(
                output_base_dir=output_dir,
                copy_mode='copy',
                enable_reference_move=True
            )
            operation_log = organizer.organize_files(match_results)
            
            print(f"✅ 文件组织完成，执行了 {len(operation_log)} 项操作")
            
            # 9. 显示最终结果
            self.show_final_results(match_results, output_dir)
            
        except Exception as e:
            logger.error(f"❌ 处理过程中发生错误: {e}", exc_info=True)
            print(f"❌ 处理失败: {e}")
    
    def show_final_results(self, match_results: List[Dict[str, Any]], output_dir: str):
        """显示最终结果"""
        print("\n" + "="*60)
        print("🎉 处理完成！结果摘要：")
        print("="*60)
        
        for result in match_results:
            segment_id = result['segment_id']
            segment_content = result['segment_content']
            best_matches = result['best_matches']
            
            print(f"\n📂 段落 {segment_id}: {segment_content[:20]}...")
            print(f"   匹配到 {len(best_matches)} 个视频片段")
            
            if best_matches:
                # 显示最高分的匹配
                top_match = max(best_matches, key=lambda x: x['match_score'])
                print(f"   最佳匹配: {top_match['video_file_name']} (得分: {top_match['match_score']:.2f})")
        
        print(f"\n📁 所有匹配的视频已组织到: {output_dir}")
        print("🎯 您可以查看相应文件夹中的视频文件")

def main():
    """主函数"""
    try:
        # 检查API配置
        api_keys = get_api_keys()
        if not api_keys.get('deepseek'):
            print("❌ 未配置DeepSeek API密钥！")
            print("💡 请在slice_to_label/config/env_config.txt中配置DEEPSEEK_API_KEY")
            return
        
        # 启动主程序
        app = ScriptDigestMain()
        app.run_full_pipeline()
        
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序运行错误: {e}")
        logger.error(f"主程序错误: {e}", exc_info=True)

if __name__ == "__main__":
    main() 