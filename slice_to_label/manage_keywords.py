#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键词配置管理工具
支持动态管理关键词、调整权重、查看统计等功能
"""

import sys
import json
from pathlib import Path
from typing import List, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from config.keyword_extraction_config import get_keyword_config, reload_keyword_config

class KeywordManager:
    """关键词管理器"""
    
    def __init__(self):
        """初始化管理器"""
        self.config = get_keyword_config()
        self.config_file = Path(__file__).parent / "config" / "keyword_extraction.json"
        
    def show_current_config(self):
        """显示当前配置概览"""
        print("\n🔍 当前关键词配置概览")
        print("=" * 50)
        
        # 提取设置
        settings = self.config.get_extraction_settings()
        print(f"📋 提取设置:")
        print(f"   最小句子长度: {settings['min_sentence_length']}")
        print(f"   最大句子数: {settings['max_sentences']}")
        print(f"   启用正则模式: {settings['enable_regex_patterns']}")
        print(f"   大小写敏感: {settings['case_sensitive']}")
        
        # 关键词类别统计
        print(f"\n🏷️ 关键词类别统计:")
        for category, config in self.config.keywords_config["keyword_categories"].items():
            total_keywords = sum(len(keywords) for keywords in config["keywords"].values())
            weight = config["weight"]
            print(f"   {category}: {total_keywords}个词汇, 权重{weight}")
        
        # 正则模式
        patterns = self.config.get_regex_patterns()
        print(f"\n🎯 正则模式: {len(patterns)}个")
        for pattern in patterns:
            print(f"   {pattern['name']}: 权重{pattern['weight']}")
        
        # 业务场景
        scenarios = self.config.keywords_config["business_scenarios"]
        print(f"\n🎬 业务场景: {len(scenarios)}个")
        for scenario_name in scenarios:
            print(f"   {scenario_name}")
    
    def list_keywords(self, category: Optional[str] = None, language: Optional[str] = None):
        """列出关键词"""
        print(f"\n📝 关键词列表")
        print("=" * 50)
        
        categories = self.config.keywords_config["keyword_categories"]
        
        for cat_name, cat_config in categories.items():
            if category and cat_name != category:
                continue
                
            print(f"\n🏷️ {cat_name} (权重: {cat_config['weight']})")
            for lang, keywords in cat_config["keywords"].items():
                if language and lang != language:
                    continue
                print(f"   {lang}: {', '.join(keywords)}")
    
    def add_keywords(self, category: str, language: str, new_keywords: List[str]):
        """添加新关键词"""
        try:
            self.config.update_keywords(category, language, new_keywords)
            self.save_config()
            print(f"✅ 已添加 {len(new_keywords)} 个关键词到 {category}-{language}")
            print(f"   新增词汇: {', '.join(new_keywords)}")
        except Exception as e:
            print(f"❌ 添加关键词失败: {e}")
    
    def remove_keywords(self, category: str, language: str, keywords_to_remove: List[str]):
        """删除关键词"""
        try:
            if category in self.config.keywords_config["keyword_categories"]:
                if language in self.config.keywords_config["keyword_categories"][category]["keywords"]:
                    keyword_list = self.config.keywords_config["keyword_categories"][category]["keywords"][language]
                    
                    removed = []
                    for keyword in keywords_to_remove:
                        if keyword in keyword_list:
                            keyword_list.remove(keyword)
                            removed.append(keyword)
                    
                    if removed:
                        self.save_config()
                        print(f"✅ 已删除 {len(removed)} 个关键词")
                        print(f"   删除词汇: {', '.join(removed)}")
                    else:
                        print(f"⚠️ 未找到要删除的关键词")
                else:
                    print(f"❌ 语言 {language} 不存在")
            else:
                print(f"❌ 类别 {category} 不存在")
        except Exception as e:
            print(f"❌ 删除关键词失败: {e}")
    
    def adjust_weight(self, category: str, new_weight: float):
        """调整类别权重"""
        try:
            if category in self.config.keywords_config["keyword_categories"]:
                old_weight = self.config.keywords_config["keyword_categories"][category]["weight"]
                self.config.keywords_config["keyword_categories"][category]["weight"] = new_weight
                self.save_config()
                print(f"✅ 已调整 {category} 权重: {old_weight} → {new_weight}")
            else:
                print(f"❌ 类别 {category} 不存在")
        except Exception as e:
            print(f"❌ 调整权重失败: {e}")
    

    
    def save_config(self):
        """保存配置"""
        try:
            self.config.save_config()
            print(f"💾 配置已保存到: {self.config_file}")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def backup_config(self, backup_name: Optional[str] = None):
        """备份配置"""
        try:
            from datetime import datetime
            if not backup_name:
                backup_name = f"keyword_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            backup_path = self.config_file.parent / backup_name
            
            import shutil
            shutil.copy2(self.config_file, backup_path)
            print(f"💾 配置已备份到: {backup_path}")
            
        except Exception as e:
            print(f"❌ 备份失败: {e}")

def main():
    """主函数 - 命令行界面"""
    import argparse
    
    parser = argparse.ArgumentParser(description="关键词配置管理工具")
    parser.add_argument("--show", action="store_true", help="显示当前配置")
    parser.add_argument("--list", nargs="*", help="列出关键词 [类别] [语言]")
    parser.add_argument("--add", nargs="+", help="添加关键词: 类别 语言 词汇1 词汇2 ...")
    parser.add_argument("--remove", nargs="+", help="删除关键词: 类别 语言 词汇1 词汇2 ...")
    parser.add_argument("--weight", nargs=2, help="调整权重: 类别 新权重")

    parser.add_argument("--backup", nargs="?", const="", help="备份配置 [备份名称]")
    
    args = parser.parse_args()
    manager = KeywordManager()
    
    if args.show:
        manager.show_current_config()
    
    elif args.list is not None:
        category = args.list[0] if len(args.list) > 0 else None
        language = args.list[1] if len(args.list) > 1 else None
        manager.list_keywords(category, language)
    
    elif args.add:
        if len(args.add) < 3:
            print("❌ 添加关键词需要至少3个参数: 类别 语言 词汇...")
        else:
            category, language = args.add[0], args.add[1]
            keywords = args.add[2:]
            manager.add_keywords(category, language, keywords)
    
    elif args.remove:
        if len(args.remove) < 3:
            print("❌ 删除关键词需要至少3个参数: 类别 语言 词汇...")
        else:
            category, language = args.remove[0], args.remove[1]
            keywords = args.remove[2:]
            manager.remove_keywords(category, language, keywords)
    
    elif args.weight:
        category, weight = args.weight[0], float(args.weight[1])
        manager.adjust_weight(category, weight)
    

    
    elif args.backup is not None:
        backup_name = args.backup if args.backup else None
        manager.backup_config(backup_name)
    
    else:
        # 交互式模式
        print("\n🎯 关键词配置管理工具")
        print("使用 --help 查看所有选项")
        manager.show_current_config()

if __name__ == "__main__":
    main() 