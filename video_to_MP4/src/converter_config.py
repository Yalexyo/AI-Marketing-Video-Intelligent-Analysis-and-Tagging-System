#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转换器配置模块

定义视频转换的各种预设配置和质量参数。
"""

from typing import Dict, Any, List


class ConversionPresets:
    """转换预设配置类"""
    
    # 质量预设
    QUALITY_PRESETS = {
        "low": {
            "video_bitrate": "500k",
            "audio_bitrate": "64k", 
            "resolution": "720x480",
            "fps": 24,
            "crf": 28,
            "preset": "fast"
        },
        "medium": {
            "video_bitrate": "2M",
            "audio_bitrate": "128k",
            "resolution": "original", 
            "fps": 30,
            "crf": 25,
            "preset": "fast"
        },
        "high": {
            "video_bitrate": "2M",
            "audio_bitrate": "192k",
            "resolution": "1920x1080",
            "fps": 30,
            "crf": 20,
            "preset": "slow"
        },
        "ultra": {
            "video_bitrate": "5M", 
            "audio_bitrate": "256k",
            "resolution": "1920x1080",
            "fps": 60,
            "crf": 18,
            "preset": "slower"
        }
    }
    
    # 分辨率预设
    RESOLUTION_PRESETS = {
        "480p": "720x480",
        "720p": "1280x720", 
        "1080p": "1920x1080",
        "1440p": "2560x1440",
        "4k": "3840x2160"
    }
    
    # 帧率预设
    FPS_PRESETS = {
        "cinema": 24,
        "standard": 30,
        "smooth": 60
    }
    
    # 编码器预设
    ENCODER_PRESETS = {
        "h264": {
            "video_codec": "libx264",
            "audio_codec": "aac",
            "container": "mp4"
        },
        "h265": {
            "video_codec": "libx265", 
            "audio_codec": "aac",
            "container": "mp4"
        }
    }
    
    # 硬件加速预设
    HARDWARE_ACCELERATION = {
        "nvidia": {
            "encoder": "h264_nvenc",
            "decoder": "h264_cuvid"
        },
        "intel": {
            "encoder": "h264_qsv", 
            "decoder": "h264_qsv"
        },
        "apple": {
            "encoder": "h264_videotoolbox",
            "decoder": "h264"
        }
    }


class FormatSupport:
    """格式支持配置类"""
    
    # 支持的输入格式
    SUPPORTED_INPUT_FORMATS = [
        "avi", "mov", "mkv", "wmv", "flv", "webm", "m4v", 
        "3gp", "ts", "mpg", "mpeg", "mts", "m2ts", "asf",
        "f4v", "rm", "rmvb", "vob", "ogv", "dv", "mxf"
    ]
    
    # 格式特定的处理配置
    FORMAT_SPECIFIC_CONFIG = {
        "avi": {
            "common_issues": ["audio_sync"],
            "recommended_preset": "medium"
        },
        "mov": {
            "common_issues": ["codec_compatibility"],
            "recommended_preset": "high"
        },
        "mkv": {
            "common_issues": ["subtitle_handling"],
            "recommended_preset": "high"
        },
        "wmv": {
            "common_issues": ["drm_protection"],
            "recommended_preset": "medium"
        },
        "flv": {
            "common_issues": ["metadata_loss"],
            "recommended_preset": "medium"
        }
    }


class ConversionConfig:
    """转换配置管理类"""
    
    @staticmethod
    def get_quality_preset(quality: str) -> Dict[str, Any]:
        """获取质量预设配置"""
        return ConversionPresets.QUALITY_PRESETS.get(
            quality, ConversionPresets.QUALITY_PRESETS["medium"]
        )
    
    @staticmethod
    def get_resolution_preset(resolution: str) -> str:
        """获取分辨率预设"""
        return ConversionPresets.RESOLUTION_PRESETS.get(resolution, resolution)
    
    @staticmethod
    def get_fps_preset(fps: str) -> int:
        """获取帧率预设"""
        if isinstance(fps, int):
            return fps
        return ConversionPresets.FPS_PRESETS.get(fps, 30)
    
    @staticmethod
    def get_encoder_preset(encoder: str) -> Dict[str, str]:
        """获取编码器预设"""
        return ConversionPresets.ENCODER_PRESETS.get(
            encoder, ConversionPresets.ENCODER_PRESETS["h264"]
        )
    
    @staticmethod
    def is_format_supported(format_name: str) -> bool:
        """检查格式是否支持"""
        return format_name.lower() in FormatSupport.SUPPORTED_INPUT_FORMATS
    
    @staticmethod
    def get_format_config(format_name: str) -> Dict[str, Any]:
        """获取格式特定配置"""
        return FormatSupport.FORMAT_SPECIFIC_CONFIG.get(
            format_name.lower(), {}
        )
    
    @staticmethod
    def build_ffmpeg_args(config: Dict[str, Any]) -> List[str]:
        """构建 FFmpeg 参数"""
        args = []
        
        # 输入参数
        if config.get("hardware_acceleration"):
            hw_config = ConversionPresets.HARDWARE_ACCELERATION.get(
                config.get("hardware_type", "nvidia"), {}
            )
            if hw_config.get("decoder"):
                args.extend(["-c:v", hw_config["decoder"]])
        
        # 视频编码参数
        args.extend(["-c:v", config.get("video_codec", "libx264")])
        
        if config.get("video_bitrate"):
            args.extend(["-b:v", config["video_bitrate"]])
        
        if config.get("crf"):
            args.extend(["-crf", str(config["crf"])])
        
        if config.get("preset"):
            args.extend(["-preset", config["preset"]])
        
        # 音频编码参数
        args.extend(["-c:a", config.get("audio_codec", "aac")])
        
        if config.get("audio_bitrate"):
            args.extend(["-b:a", config["audio_bitrate"]])
        
        # 视频参数
        if config.get("resolution") and config["resolution"] != "original":
            args.extend(["-s", config["resolution"]])
        
        if config.get("fps"):
            args.extend(["-r", str(config["fps"])])
        
        # 其他参数
        if config.get("threads"):
            args.extend(["-threads", str(config["threads"])])
        
        # 额外参数
        if config.get("extra_args"):
            if isinstance(config["extra_args"], str):
                args.extend(config["extra_args"].split())
            elif isinstance(config["extra_args"], list):
                args.extend(config["extra_args"])
        
        return args 