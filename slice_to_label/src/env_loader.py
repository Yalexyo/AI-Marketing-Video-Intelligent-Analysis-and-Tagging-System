#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量加载器
自动从 .env 文件加载环境变量
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class EnvLoader:
    """环境变量加载器"""
    
    def __init__(self, env_file: str = ".env"):
        """
        初始化环境变量加载器
        
        Args:
            env_file: .env文件路径
        """
        self.env_file = env_file
        self.loaded_vars = {}
        
    def load_env_file(self, project_root: Optional[str] = None) -> Dict[str, str]:
        """
        加载 .env 文件中的环境变量
        
        Args:
            project_root: 项目根目录，如果为None则自动检测
            
        Returns:
            加载的环境变量字典
        """
        if project_root is None:
            # 自动检测项目根目录
            current_file = Path(__file__).resolve()
            project_root = str(current_file.parent.parent)
        
        env_path = Path(project_root) / self.env_file
        
        if not env_path.exists():
            logger.warning(f"⚠️ 未找到 .env 文件: {env_path}")
            return {}
        
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            loaded_count = 0
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue
                
                # 解析 KEY=VALUE 格式
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 移除值两端的引号
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # 设置环境变量
                    os.environ[key] = value
                    self.loaded_vars[key] = value
                    loaded_count += 1
                    
                    logger.debug(f"✅ 加载环境变量: {key}")
            
            logger.info(f"✅ 成功加载 {loaded_count} 个环境变量")
            return self.loaded_vars
            
        except Exception as e:
            logger.error(f"❌ 加载 .env 文件失败: {str(e)}")
            return {}
    
    def get_api_keys(self) -> Dict[str, str]:
        """获取AI API密钥，并映射到标准名称"""
        api_keys = {}
        
        # DashScope API密钥 (Qwen模型使用)
        dashscope_key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('QWEN_API_KEY')
        if dashscope_key:
            api_keys['qwen'] = dashscope_key  # 映射到qwen名称
            api_keys['DASHSCOPE_API_KEY'] = dashscope_key  # 保持原名称
            logger.info("✅ DashScope/Qwen API密钥: 已设置")
        else:
            logger.warning("⚠️ DASHSCOPE_API_KEY/QWEN_API_KEY: 未设置")
        
        # Gemini API密钥
        gemini_key = os.getenv('GOOGLE_AI_API_KEY') or os.getenv('GEMINI_API_KEY')
        if gemini_key:
            api_keys['gemini'] = gemini_key  # 映射到gemini名称
            api_keys['GOOGLE_AI_API_KEY'] = gemini_key  # 保持原名称
            logger.info("✅ Gemini API密钥: 已设置")
        else:
            logger.warning("⚠️ GOOGLE_AI_API_KEY/GEMINI_API_KEY: 未设置")
        
        # DeepSeek API密钥 (翻译功能使用)
        deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        if deepseek_key:
            api_keys['deepseek'] = deepseek_key  # 映射到deepseek名称
            api_keys['DEEPSEEK_API_KEY'] = deepseek_key  # 保持原名称
            logger.info("✅ DeepSeek API密钥: 已设置")
        else:
            logger.warning("⚠️ DEEPSEEK_API_KEY: 未设置")
        
        return api_keys
    
    def get_oss_config(self) -> Dict[str, Any]:
        """获取OSS配置"""
        oss_config = {}
        
        oss_keys = [
            'OSS_ACCESS_KEY_ID',
            'OSS_ACCESS_KEY_SECRET', 
            'OSS_BUCKET_NAME',
            'OSS_ENDPOINT',
            'OSS_UPLOAD_DIR',
            'ENABLE_OSS'
        ]
        
        for key in oss_keys:
            value = os.getenv(key)
            if value:
                # 处理布尔值
                if key == 'ENABLE_OSS':
                    oss_config[key] = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    oss_config[key] = value
        
        return oss_config
    
    def get_video_config(self) -> Dict[str, Any]:
        """获取视频处理配置"""
        video_config = {}
        
        video_keys = {
            'VIDEO_MAX_SIZE_MB': int,
            'VIDEO_SPEECH_RECOGNITION_ENGINE': str,
            'VIDEO_PROCESSING_THREADS': int,
            'MAX_FILES_PER_BATCH': int,
            'MAX_VIDEO_DURATION_SECONDS': int,
            'MIN_VIDEO_DURATION_SECONDS': int,
            'DUAL_STAGE_ENABLED': bool,
            'BRAND_DETECTION_THRESHOLD': float,
            'VISUAL_ANALYSIS_CONFIDENCE': float
        }
        
        for key, type_func in video_keys.items():
            value = os.getenv(key)
            if value:
                try:
                    if type_func == bool:
                        video_config[key] = value.lower() in ('true', '1', 'yes', 'on')
                    elif type_func == int:
                        video_config[key] = int(value)
                    elif type_func == float:
                        video_config[key] = float(value)
                    else:
                        video_config[key] = value
                except ValueError as e:
                    logger.warning(f"⚠️ 配置 {key} 值格式错误: {value}")
        
        return video_config
    
    def validate_config(self) -> bool:
        """验证配置完整性"""
        api_keys = self.get_api_keys()
        
        # 检查必需的API密钥（至少需要一个分析模型API）
        has_analysis_api = 'qwen' in api_keys or 'gemini' in api_keys
        
        if not has_analysis_api:
            logger.error("❌ 缺少必需的分析API密钥，至少需要配置以下之一:")
            logger.error("   - DASHSCOPE_API_KEY (用于Qwen模型)")
            logger.error("   - GOOGLE_AI_API_KEY 或 GEMINI_API_KEY (用于Gemini模型)")
            return False
        
        logger.info("✅ 配置验证通过")
        return True
    
    def print_config_summary(self):
        """打印配置摘要"""
        print("\n📋 环境配置摘要:")
        print("=" * 50)
        
        # API密钥状态
        api_keys = self.get_api_keys()
        print(f"🔑 API密钥:")
        
        # DashScope/Qwen API
        qwen_status = "✅ 已设置" if 'qwen' in api_keys else "❌ 未设置"
        print(f"   DashScope/Qwen API: {qwen_status}")
        
        # Gemini API
        gemini_status = "✅ 已设置" if 'gemini' in api_keys else "❌ 未设置"
        print(f"   Gemini API: {gemini_status}")
        
        # DeepSeek API
        deepseek_status = "✅ 已设置" if 'deepseek' in api_keys else "❌ 未设置"
        print(f"   DeepSeek API: {deepseek_status}")
        
        # OSS配置状态
        oss_config = self.get_oss_config()
        print(f"\n☁️ OSS配置:")
        print(f"   启用状态: {'✅ 已启用' if oss_config.get('ENABLE_OSS') else '❌ 未启用'}")
        if oss_config.get('ENABLE_OSS'):
            print(f"   存储桶: {oss_config.get('OSS_BUCKET_NAME', '未设置')}")
            print(f"   端点: {oss_config.get('OSS_ENDPOINT', '未设置')}")
        
        # 视频处理配置
        video_config = self.get_video_config()
        print(f"\n🎬 视频处理配置:")
        print(f"   最大文件大小: {video_config.get('VIDEO_MAX_SIZE_MB', 500)}MB")
        print(f"   处理线程数: {video_config.get('VIDEO_PROCESSING_THREADS', 4)}")
        print(f"   双层识别: {'✅ 启用' if video_config.get('DUAL_STAGE_ENABLED', True) else '❌ 禁用'}")
        
        print("=" * 50)

def load_environment(env_file: str = ".env") -> EnvLoader:
    """
    便捷函数：加载环境变量
    
    Args:
        env_file: .env文件路径
        
    Returns:
        EnvLoader实例
    """
    env_loader = EnvLoader(env_file)
    env_loader.load_env_file()
    return env_loader

if __name__ == "__main__":
    # 测试环境变量加载
    print("🚀 测试环境变量加载器...")
    
    env_loader = load_environment()
    env_loader.print_config_summary()
    
    if env_loader.validate_config():
        print("\n✅ 环境配置就绪，可以运行AI分析！")
    else:
        print("\n❌ 环境配置不完整，请检查API密钥设置")
        sys.exit(1) 