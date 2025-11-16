#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块

负责加载和管理项目配置，支持从文件和环境变量加载配置。
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .converter_config import ConversionConfig


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 自定义配置文件路径
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = self._load_default_config()
        
        # 加载配置文件
        if config_path:
            self._load_config_file(config_path)
        else:
            # 尝试加载默认配置文件
            default_config_path = Path("config/env_config.txt")
            if default_config_path.exists():
                self._load_config_file(str(default_config_path))
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "conversion": {
                "quality": "medium",
                "resolution": None,
                "bitrate": None,
                "fps": None,
                "video_codec": "libx264",
                "audio_codec": "aac",
                "threads": 0,
                "extra_args": []
            },
            "processing": {
                "workers": 2,
                "max_workers": 8,
                "skip_existing": True,
                "preserve_structure": True,
                "buffer_size": 64,
                "large_file_threshold": 1024
            },
            "files": {
                "supported_formats": [
                    "avi", "mov", "mkv", "wmv", "flv", "webm", "m4v", 
                    "3gp", "ts", "mpg", "mpeg", "mts", "m2ts"
                ],
                "output_extension": "mp4",
                "temp_prefix": "temp_convert_"
            },
            "logging": {
                "level": "INFO",
                "enable_file_logging": True,
                "retention_days": 30
            },
            "hardware": {
                "use_acceleration": False,
                "acceleration_type": "auto"
            }
        }
    
    def _load_config_file(self, config_path: str):
        """从文件加载配置"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            self.logger.warning(f"配置文件不存在: {config_path}")
            return
        
        try:
            # 使用 python-dotenv 加载配置
            load_dotenv(config_file)
            
            # 更新转换配置
            self._update_conversion_config()
            self._update_processing_config()
            self._update_file_config()
            self._update_logging_config()
            self._update_hardware_config()
            
            self.logger.info(f"已加载配置文件: {config_path}")
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败 {config_path}: {e}")
    
    def _update_conversion_config(self):
        """更新转换配置"""
        conversion = self.config["conversion"]
        
        # 基础设置
        if os.getenv("DEFAULT_QUALITY"):
            conversion["quality"] = os.getenv("DEFAULT_QUALITY")
        
        if os.getenv("DEFAULT_RESOLUTION"):
            conversion["resolution"] = os.getenv("DEFAULT_RESOLUTION")
        
        if os.getenv("DEFAULT_BITRATE"):
            conversion["bitrate"] = os.getenv("DEFAULT_BITRATE")
        
        if os.getenv("DEFAULT_FPS"):
            try:
                conversion["fps"] = int(os.getenv("DEFAULT_FPS"))
            except ValueError:
                pass
        
        if os.getenv("VIDEO_CODEC"):
            conversion["video_codec"] = os.getenv("VIDEO_CODEC")
        
        if os.getenv("AUDIO_CODEC"):
            conversion["audio_codec"] = os.getenv("AUDIO_CODEC")
        
        if os.getenv("FFMPEG_THREADS"):
            try:
                conversion["threads"] = int(os.getenv("FFMPEG_THREADS"))
            except ValueError:
                pass
        
        if os.getenv("FFMPEG_EXTRA_ARGS"):
            extra_args = os.getenv("FFMPEG_EXTRA_ARGS").strip()
            if extra_args:
                conversion["extra_args"] = extra_args.split()
    
    def _update_processing_config(self):
        """更新处理配置"""
        processing = self.config["processing"]
        
        if os.getenv("DEFAULT_WORKERS"):
            try:
                processing["workers"] = int(os.getenv("DEFAULT_WORKERS"))
            except ValueError:
                pass
        
        if os.getenv("MAX_WORKERS"):
            try:
                processing["max_workers"] = int(os.getenv("MAX_WORKERS"))
            except ValueError:
                pass
        
        if os.getenv("SKIP_EXISTING"):
            processing["skip_existing"] = os.getenv("SKIP_EXISTING").lower() == "true"
        
        if os.getenv("PRESERVE_STRUCTURE"):
            processing["preserve_structure"] = os.getenv("PRESERVE_STRUCTURE").lower() == "true"
        
        if os.getenv("BUFFER_SIZE"):
            try:
                processing["buffer_size"] = int(os.getenv("BUFFER_SIZE"))
            except ValueError:
                pass
        
        if os.getenv("LARGE_FILE_THRESHOLD"):
            try:
                processing["large_file_threshold"] = int(os.getenv("LARGE_FILE_THRESHOLD"))
            except ValueError:
                pass
    
    def _update_file_config(self):
        """更新文件配置"""
        files = self.config["files"]
        
        if os.getenv("SUPPORTED_FORMATS"):
            formats = os.getenv("SUPPORTED_FORMATS").split(",")
            files["supported_formats"] = [fmt.strip() for fmt in formats]
        
        if os.getenv("OUTPUT_EXTENSION"):
            files["output_extension"] = os.getenv("OUTPUT_EXTENSION")
        
        if os.getenv("TEMP_PREFIX"):
            files["temp_prefix"] = os.getenv("TEMP_PREFIX")
    
    def _update_logging_config(self):
        """更新日志配置"""
        logging_config = self.config["logging"]
        
        if os.getenv("LOG_LEVEL"):
            logging_config["level"] = os.getenv("LOG_LEVEL")
        
        if os.getenv("ENABLE_FILE_LOGGING"):
            logging_config["enable_file_logging"] = os.getenv("ENABLE_FILE_LOGGING").lower() == "true"
        
        if os.getenv("LOG_RETENTION_DAYS"):
            try:
                logging_config["retention_days"] = int(os.getenv("LOG_RETENTION_DAYS"))
            except ValueError:
                pass
    
    def _update_hardware_config(self):
        """更新硬件配置"""
        hardware = self.config["hardware"]
        
        if os.getenv("USE_HARDWARE_ACCELERATION"):
            hardware["use_acceleration"] = os.getenv("USE_HARDWARE_ACCELERATION").lower() == "true"
        
        if os.getenv("HARDWARE_ACCELERATION_TYPE"):
            hardware["acceleration_type"] = os.getenv("HARDWARE_ACCELERATION_TYPE")
    
    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self.config.copy()
    
    def get_conversion_config(self, quality: Optional[str] = None) -> Dict[str, Any]:
        """获取转换配置，并应用质量预设"""
        conversion_config = self.config["conversion"].copy()
        
        # 应用质量预设
        quality = quality or conversion_config.get("quality", "medium")
        quality_preset = ConversionConfig.get_quality_preset(quality)
        
        # 合并配置，命令行/配置文件设置优先
        for key, value in quality_preset.items():
            if not conversion_config.get(key):
                conversion_config[key] = value
        
        return conversion_config
    
    def get_processing_config(self) -> Dict[str, Any]:
        """获取处理配置"""
        return self.config["processing"].copy()
    
    def get_file_config(self) -> Dict[str, Any]:
        """获取文件配置"""
        return self.config["files"].copy()
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.config["logging"].copy()
    
    def get_hardware_config(self) -> Dict[str, Any]:
        """获取硬件配置"""
        return self.config["hardware"].copy()
    
    def update_config(self, section: str, key: str, value: Any):
        """动态更新配置"""
        if section in self.config and isinstance(self.config[section], dict):
            self.config[section][key] = value
            self.logger.debug(f"更新配置: {section}.{key} = {value}")
        else:
            self.logger.warning(f"无效的配置节: {section}")
    
    def validate_config(self) -> bool:
        """验证配置有效性"""
        errors = []
        
        # 验证处理配置
        processing = self.config["processing"]
        if processing["workers"] <= 0:
            errors.append("workers 必须大于 0")
        
        if processing["workers"] > processing["max_workers"]:
            errors.append("workers 不能超过 max_workers")
        
        # 验证转换配置
        conversion = self.config["conversion"]
        if conversion["quality"] not in ["low", "medium", "high", "ultra"]:
            errors.append("quality 必须是 low, medium, high, ultra 中的一个")
        
        # 验证文件配置
        files = self.config["files"]
        if not files["supported_formats"]:
            errors.append("supported_formats 不能为空")
        
        if errors:
            for error in errors:
                self.logger.error(f"配置验证错误: {error}")
            return False
        
        return True
    
    def print_config_summary(self):
        """打印配置摘要"""
        self.logger.info("当前配置摘要:")
        self.logger.info(f"  转换质量: {self.config['conversion']['quality']}")
        self.logger.info(f"  并行线程: {self.config['processing']['workers']}")
        self.logger.info(f"  支持格式: {', '.join(self.config['files']['supported_formats'])}")
        self.logger.info(f"  跳过已存在: {self.config['processing']['skip_existing']}")
        self.logger.info(f"  保持结构: {self.config['processing']['preserve_structure']}")
        
        if self.config["conversion"]["resolution"]:
            self.logger.info(f"  输出分辨率: {self.config['conversion']['resolution']}")
        
        if self.config["hardware"]["use_acceleration"]:
            self.logger.info(f"  硬件加速: {self.config['hardware']['acceleration_type']}") 