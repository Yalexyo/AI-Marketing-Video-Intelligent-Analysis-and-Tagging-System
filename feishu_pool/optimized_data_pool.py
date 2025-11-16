#!/usr/bin/env python3
"""
🎬 AI-启赋优化数据池管理器
单一多维表格架构：视频基础池 + 切片标签池

架构优势：
1. 数据关联更简单 - 只需要一个app_token
2. 权限管理统一 - 一个应用统一管理权限
3. 操作更便捷 - 在同一个界面查看所有数据
4. 性能更好 - 减少跨应用查询
5. 维护成本低 - 只需要维护一个多维表格
"""

import os
import json
import requests
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

# 导入标签系统管理器（用于处理标签业务逻辑）
try:
    # 尝试导入label_to_classifier的TagSystemManager
    import sys
    sys.path.append(str(Path(__file__).parent.parent / "label_to_classifier" / "src"))
    from tag_system_manager import TagSystemManager
    TAG_SYSTEM_AVAILABLE = True
except ImportError:
    print("⚠️ 未找到TagSystemManager，标签相关功能将受限")
    TAG_SYSTEM_AVAILABLE = False


@dataclass
class VideoBaseRecord:
    """视频基础池记录结构"""
    video_id: str
    video_name: str
    original_video_path: str
    original_srt_path: str
    file_size_mb: float
    duration_seconds: int
    resolution: str
    upload_time: str
    source_channel: str
    content_themes: List[str]
    process_status: str = "未处理"  # 未处理/切片中/已完成


@dataclass
class SliceTagRecord:
    """切片标签池记录结构"""
    slice_id: str
    video_id: str  # 关联到视频基础池
    slice_name: str
    start_time: float
    end_time: float
    duration_seconds: float
    main_category: str  # 主标签
    sub_tags: List[str]  # 子标签
    subtitle_text: str  # 对应的字幕文本
    confidence_score: float
    annotation_status: str = "待标注"
    review_status: str = "待审核"
    product_subtitle: str = ""  # 产品介绍专用字幕（用于产品介绍切片）
    modification_reason: str = ""  # 修改原因，用于MCP反馈优化


class OptimizedDataPoolManager:
    """🎬 AI-启赋优化数据池管理器"""
    
    def __init__(self, config_path: str = "optimized_pool_config.json"):
        """初始化数据池管理器"""
        self.config = self._load_config(config_path)
        if not self.config:
            # 如果没有优化配置，尝试基础配置
            self.config = self._load_config("feishu_config.json")
            
        self.access_token = None
        self.base_url = "https://open.feishu.cn/open-apis"
        
        # 尝试从配置文件加载app_config
        # 支持两种配置格式
        if "feishu_api" in self.config:
            app_token = self.config["feishu_api"].get("app_token")
        else:
            app_token = self.config.get("app_token")
            
        if app_token and 'tables' in self.config:
            # 使用完整配置
            self.app_config = {
                "app_name": self.config.get("app_name", "🎬 AI-启赋智能数据池"),
                "app_token": app_token,
                "tables": self.config.get("tables", {})
            }
        else:
            # 默认配置
            self.app_config = {
                "app_name": "🎬 AI-启赋智能数据池",
                "app_token": app_token,
                "tables": {
                    "video_base": {
                        "name": "📄 视频基础池",
                        "table_id": None
                    },
                    "slice_tag": {
                        "name": "✂️ 切片标签池", 
                        "table_id": None
                    }
                }
            }
        
        # 初始化标签系统管理器（用于处理业务逻辑）
        if TAG_SYSTEM_AVAILABLE:
            self.tag_manager = TagSystemManager()
        else:
            self.tag_manager = None
            print("⚠️ 标签系统管理器不可用，将使用简化的标签处理")

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            return {}

    # 注意：标签体系管理功能已迁移到 label_to_classifier/TagSystemManager
    # 此类现在专注于数据存储和飞书API操作

    def _get_access_token(self) -> str:
        """获取访问令牌"""
        try:
            url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
            headers = {"Content-Type": "application/json; charset=utf-8"}
            # 支持两种配置格式
            if "feishu_api" in self.config:
                # 嵌套格式
                app_id = self.config["feishu_api"]["app_id"]
                app_secret = self.config["feishu_api"]["app_secret"]
            else:
                # 平铺格式
                app_id = self.config["app_id"]
                app_secret = self.config["app_secret"]
                
            data = {
                "app_id": app_id,
                "app_secret": app_secret
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            result = response.json()
            
            if result.get("code") == 0:
                self.access_token = result["tenant_access_token"]
                return self.access_token
            else:
                print(f"❌ 获取访问令牌失败: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 获取访问令牌异常: {e}")
            return None

    def create_optimized_data_pool(self) -> bool:
        """创建优化的数据池（单一多维表格 + 两个表）"""
        try:
            print("🚀 创建AI-启赋优化数据池...")
            
            # 1. 创建多维表格应用
            if not self._create_app():
                return False
            
            # 2. 获取默认表并重命名为视频基础池
            if not self._setup_video_base_table():
                return False
            
            # 3. 创建切片标签池表
            if not self._create_slice_tag_table():
                return False
            
            print(f"\n🎉 优化数据池创建完成！")
            print(f"📱 访问链接: https://feishu.cn/base/{self.app_config['app_token']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建数据池异常: {e}")
            return False

    def _create_app(self) -> bool:
        """创建多维表格应用"""
        try:
            access_token = self._get_access_token()
            if not access_token:
                return False
                
            url = f"{self.base_url}/bitable/v1/apps"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            data = {"name": self.app_config["app_name"]}
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                self.app_config["app_token"] = result["data"]["app"]["app_token"]
                print(f"✅ 多维表格应用创建成功: {self.app_config['app_token']}")
                return True
            else:
                print(f"❌ 多维表格应用创建失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 多维表格应用创建异常: {e}")
            return False

    def _setup_video_base_table(self) -> bool:
        """设置视频基础池表（获取默认表并添加字段）"""
        try:
            access_token = self._get_access_token()
            app_token = self.app_config["app_token"]
            
            # 获取默认表格ID
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            response = requests.get(url, headers=headers, timeout=10)
            result = response.json()
            
            if result.get("code") == 0 and result["data"]["items"]:
                table_id = result["data"]["items"][0]["table_id"]
                self.app_config["tables"]["video_base"]["table_id"] = table_id
                
                # 注意：跳过重命名功能，因为API不支持
                print(f"  ℹ️ 使用默认表格作为视频基础池: {table_id}")
                
                # 创建视频基础池字段
                fields_data = [
                    {"field_name": "video_id", "type": 1},  # 单行文本
                    {"field_name": "视频名称", "type": 1},
                    {"field_name": "原视频文件", "type": 17},  # 附件 - 支持直接上传视频文件
                    {"field_name": "原视频字幕文件", "type": 17},  # 附件 - 支持直接上传SRT文件
                    {"field_name": "完整字幕内容", "type": 1},  # 单行文本 - 存储字幕的完整文本内容
                    {"field_name": "文件大小MB", "type": 2},  # 数字
                    {"field_name": "视频时长秒", "type": 2},
                    {"field_name": "分辨率", "type": 1},
                    {"field_name": "上传时间", "type": 5},  # 日期时间
                    {"field_name": "来源渠道", "type": 1},
                    {"field_name": "内容主题", "type": 3},  # 多选
                    {"field_name": "处理状态", "type": 3, "property": {"options": [
                        {"name": "未处理"},
                        {"name": "切片中"},
                        {"name": "已完成"}
                    ]}}
                ]
                
                for field_data in fields_data:
                    self._create_field(app_token, table_id, field_data)
                
                print(f"✅ 视频基础池表设置完成")
                return True
                
        except Exception as e:
            print(f"❌ 视频基础池表设置异常: {e}")
            return False

    def _create_slice_tag_table(self) -> bool:
        """创建切片标签池表"""
        try:
            access_token = self._get_access_token()
            app_token = self.app_config["app_token"]
            
            # 创建新表
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 使用正确的飞书API格式
            data = {"table": {"name": "✂️ 切片标签池"}}
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                # 修复：直接从data中获取table_id
                table_id = result["data"]["table_id"]
                self.app_config["tables"]["slice_tag"]["table_id"] = table_id
                
                # 创建切片标签池字段
                fields_data = [
                    {"field_name": "slice_id", "type": 1},
                    {"field_name": "关联video_id", "type": 1},  # 关联到视频基础池
                    {"field_name": "切片名称", "type": 1},
                    {"field_name": "开始时间", "type": 2},
                    {"field_name": "结束时间", "type": 2},
                    {"field_name": "时长秒", "type": 2},
                    {"field_name": "Labels", "type": 1},  # AI分析的完整标签信息
                    {"field_name": "主标签类别", "type": 3, "property": {"options": [
                        {"name": "🌟 使用效果"},
                        {"name": "🍼 产品介绍"},
                        {"name": "🎁 促销机制"},
                        {"name": "🪝 钩子"}
                    ]}},
                    {"field_name": "子标签", "type": 1},  # 文本输入
                    {"field_name": "对应字幕文本", "type": 1},
                    {"field_name": "置信度分数", "type": 2},
                    {"field_name": "标注状态", "type": 3, "property": {"options": [
                        {"name": "待标注"},
                        {"name": "已标注"},
                        {"name": "需修正"}
                    ]}},
                    {"field_name": "审核状态", "type": 3, "property": {"options": [
                        {"name": "待审核"},
                        {"name": "已通过"},
                        {"name": "需修改"}
                    ]}},
                    {"field_name": "修改原因", "type": 1}  # 文本输入字段，用于MCP反馈优化
                ]
                
                for field_data in fields_data:
                    self._create_field(app_token, table_id, field_data)
                
                print(f"✅ 切片标签池表创建完成")
                return True
            else:
                print(f"❌ 切片标签池表创建失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 切片标签池表创建异常: {e}")
            return False

    def _rename_table(self, app_token: str, table_id: str, new_name: str) -> bool:
        """重命名表格 - 该功能暂不可用"""
        print(f"  ℹ️ 表格重命名功能暂不可用，跳过: {new_name}")
        return True

    def _create_field(self, app_token: str, table_id: str, field_data: Dict) -> bool:
        """创建表格字段"""
        try:
            access_token = self._get_access_token()
            
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            response = requests.post(url, headers=headers, json=field_data, timeout=10)
            result = response.json()
            
            if result.get("code") == 0:
                print(f"    ✅ 字段创建成功: {field_data['field_name']}")
                return True
            else:
                print(f"    ❌ 字段创建失败: {field_data['field_name']} - {result}")
                return False
                
        except Exception as e:
            print(f"    ❌ 字段创建异常: {field_data['field_name']} - {e}")
            return False

    def upload_file_to_feishu(self, file_path: str, file_type: str = "stream") -> Optional[str]:
        """
        上传文件到飞书，获取file_token
        
        Args:
            file_path: 本地文件路径
            file_type: 文件类型，默认为stream
        
        Returns:
            str: file_token 或 None
        """
        try:
            access_token = self._get_access_token()
            if not access_token:
                return None
            
            url = f"{self.base_url}/im/v1/files"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            file_name = Path(file_path).name
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_name, f, 'application/octet-stream')
                }
                data = {
                    'file_type': file_type,
                    'file_name': file_name
                }
                
                response = requests.post(url, headers=headers, files=files, data=data, timeout=180)
                result = response.json()
                
                if result.get("code") == 0:
                    file_key = result["data"]["file_key"]
                    print(f"✅ 文件上传成功: {file_name} -> {file_key}")
                    return file_key
                else:
                    print(f"❌ 文件上传失败: {result}")
                    return None
                    
        except Exception as e:
            print(f"❌ 文件上传异常: {e}")
            return None

    def validate_video_file(self, file_path: str) -> dict:
        """
        验证视频文件是否包含视频流
        
        Args:
            file_path: 视频文件路径
        
        Returns:
            dict: 验证结果 {is_valid: bool, has_video: bool, has_audio: bool, reason: str}
        """
        try:
            import subprocess
            import json
            
            # 使用ffprobe检查文件流信息
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {
                    "is_valid": False,
                    "has_video": False,
                    "has_audio": False,
                    "reason": "无法读取文件信息"
                }
            
            # 解析流信息
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            
            has_video = any(stream.get('codec_type') == 'video' for stream in streams)
            has_audio = any(stream.get('codec_type') == 'audio' for stream in streams)
            
            if not has_video and has_audio:
                return {
                    "is_valid": False,
                    "has_video": False,
                    "has_audio": True,
                    "reason": "仅包含音频流，无视频内容"
                }
            elif has_video:
                return {
                    "is_valid": True,
                    "has_video": True,
                    "has_audio": has_audio,
                    "reason": "正常视频文件"
                }
            else:
                return {
                    "is_valid": False,
                    "has_video": False,
                    "has_audio": False,
                    "reason": "无有效音视频流"
                }
        except Exception as e:
            return {
                "is_valid": False,
                "has_video": False,
                "has_audio": False,
                "reason": f"验证过程出错: {str(e)}"
            }

    def upload_media_to_drive(self, file_path: str, parent_type: str = "bitable_record", parent_node: str = "", file_name: str = None) -> Optional[str]:
        """
        通过云文档素材上传API上传文件，绕过机器人权限限制
        
        Args:
            file_path: 本地文件路径
            parent_type: 云文档节点类型，如果为空则使用默认容器文档
            parent_node: 云文档节点ID，如果为空则使用默认容器文档
            file_name: 文件名，如果为空则使用本地文件名
        
        Returns:
            str: file_token 或 None
        """
        try:
            access_token = self._get_access_token()
            if not access_token:
                print("❌ 无法获取访问令牌")
                return None
            
            # 如果没有指定parent_node，尝试创建或获取默认容器文档
            if not parent_node:
                parent_node = self._get_or_create_media_container()
                if not parent_node:
                    print("❌ 无法获取素材容器文档")
                    return None
            
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"❌ 文件不存在: {file_path}")
                return None
            
            file_size = file_path.stat().st_size
            file_name = file_name or file_path.name
            
            # 检查文件大小限制（50MB）
            if file_size > 50 * 1024 * 1024:
                print(f"❌ 文件过大: {file_name} ({file_size / 1024 / 1024:.1f}MB)，超过50MB限制")
                return None
            
            url = f"{self.base_url}/drive/v1/medias/upload_all"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_name, f, 'application/octet-stream')
                }
                data = {
                    'file_name': file_name,
                    'parent_type': 'bitable_record',
                    'parent_node': parent_node,
                    'size': str(file_size)
                }
                
                print(f"🌐 开始上传到云文档: {file_name} ({file_size / 1024 / 1024:.1f}MB)")
                response = requests.post(url, headers=headers, files=files, data=data, timeout=180)
                result = response.json()
                
                if result.get("code") == 0:
                    file_token = result["data"]["file_token"]
                    print(f"✅ 云文档素材上传成功: {file_name} -> {file_token}")
                    return file_token
                else:
                    print(f"❌ 云文档素材上传失败: {result}")
                    return None
                    
        except Exception as e:
            print(f"❌ 云文档素材上传异常: {e}")
            return None

    def _get_or_create_media_container(self) -> Optional[str]:
        """
        获取或创建素材容器文档
        
        Returns:
            str: 容器文档的node_id 或 None
        """
        try:
            # 从配置中获取容器文档ID
            container_node = self.config.get("media_container_node")
            if container_node:
                print(f"📁 使用配置的素材容器: {container_node}")
                return container_node
            
            # 使用当前数据池的app_token作为容器
            app_token = self.app_config.get("app_token")
            if app_token:
                print(f"📁 使用数据池作为素材容器: {app_token}")
                return app_token
            
            print("❌ 无法找到合适的素材容器")
            return None
            
        except Exception as e:
            print(f"❌ 获取素材容器异常: {e}")
            return None

    def set_media_container(self, parent_node: str) -> bool:
        """
        设置素材容器文档ID
        
        Args:
            parent_node: 云文档节点ID
        
        Returns:
            bool: 设置是否成功
        """
        try:
            self.config["media_container_node"] = parent_node
            print(f"✅ 素材容器已设置: {parent_node}")
            return True
        except Exception as e:
            print(f"❌ 设置素材容器失败: {e}")
            return False

    def read_srt_content(self, srt_file_path: str) -> str:
        """
        读取SRT字幕文件的完整内容
        
        Args:
            srt_file_path: SRT文件路径
        
        Returns:
            str: 字幕文件的完整文本内容
        """
        try:
            with open(srt_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"✅ 字幕内容读取成功: {len(content)} 字符")
                return content
        except Exception as e:
            print(f"❌ 字幕内容读取失败: {e}")
            return ""

    def add_video_base_record_with_content(self,
                                         video_id: str,
                                         video_name: str,
                                         video_file_path: str = None,
                                         srt_content: str = None,
                                         file_size_mb: float = 0,
                                         duration_seconds: int = 0,
                                         resolution: str = "") -> Optional[str]:
        """
        添加视频基础记录（仅使用现有7个字段）
        
        Args:
            video_id: 视频ID
            video_name: 视频名称
            video_file_path: 本地视频文件路径（可选）
            srt_content: 字幕文本内容（可选）
            file_size_mb: 文件大小
            duration_seconds: 视频时长
            resolution: 分辨率
        
        Returns:
            str: 记录ID 或 None
        """
        try:
            app_token = self.app_config["app_token"]
            table_id = self.app_config["tables"]["video_base"]["table_id"]
            
            if not app_token or not table_id:
                print("❌ 数据池未初始化，请先创建数据池")
                return None
            
            # 准备记录数据 - 只使用现有的7个字段
            record_fields = {
                "video_ID": video_id,  # 注意字段名是 video_ID
                "视频名称": video_name,
                "文件大小MB": file_size_mb,
                "视频时长秒": duration_seconds,
                "分辨率": resolution
            }
            
            # 跳过完整视频文件上传（主表只存基本信息）
            print("ℹ️ 主表跳过完整视频文件上传，只存储基本信息")
            
            # 处理字幕内容（作为文本存储在"原视频字幕"字段）
            if srt_content:
                print("📄 使用提供的字幕内容")
                record_fields["原视频字幕"] = srt_content
            
            # 创建记录
            access_token = self._get_access_token()
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            record_data = {"fields": record_fields}
            
            response = requests.post(url, headers=headers, json=record_data, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                record_id = result["data"]["record"]["record_id"]
                print(f"✅ 视频基础记录添加成功: {video_id}")
                return record_id
            else:
                print(f"❌ 视频基础记录添加失败: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 视频基础记录添加异常: {e}")
            return None

    def add_video_base_record(self, video_data: Union[VideoBaseRecord, Dict]) -> Optional[str]:
        """添加视频基础记录（兼容旧接口）"""
        try:
            if isinstance(video_data, dict):
                return self.add_video_base_record_with_content(
                    video_id=video_data.get("video_id", ""),
                    video_name=video_data.get("video_name", ""),
                    video_file_path=video_data.get("original_video_path"),
                    srt_file_path=video_data.get("original_srt_path"),
                    srt_content=video_data.get("srt_content"),  # 支持直接传入字幕内容
                    file_size_mb=video_data.get("file_size_mb", 0),
                    duration_seconds=video_data.get("duration_seconds", 0),
                    resolution=video_data.get("resolution", ""),
                    source_channel=video_data.get("source_channel", ""),
                    content_themes=video_data.get("content_themes", [])
                )
            else:
                return self.add_video_base_record_with_content(
                    video_id=video_data.video_id,
                    video_name=video_data.video_name,
                    video_file_path=video_data.original_video_path,
                    srt_file_path=video_data.original_srt_path,
                    file_size_mb=video_data.file_size_mb,
                    duration_seconds=video_data.duration_seconds,
                    resolution=video_data.resolution,
                    source_channel=video_data.source_channel,
                    content_themes=video_data.content_themes
                )
                
        except Exception as e:
            print(f"❌ 视频基础记录添加异常: {e}")
            return None

    def add_slice_tag_record(self, 
                           video_id: str = None,
                           slice_name: str = None, 
                           slice_file_path: str = None,
                           start_time: float = 0,
                           end_time: float = 0,
                           duration: float = 0,
                           file_size_mb: float = 0,
                           main_tag: str = "",
                           ai_sub_tags: list = None,
                           confidence: float = 0.0,
                           slice_type: str = "",
                           product_subtitle_content: str = "",
                           slice_data: Union[SliceTagRecord, Dict] = None) -> Optional[str]:
        """添加切片标签记录（带主子标签关联验证）"""
        try:
            # 处理新的参数格式或传统的slice_data格式
            if slice_data is not None:
                if isinstance(slice_data, dict):
                    slice_data = SliceTagRecord(**slice_data)
                elif isinstance(slice_data, SliceTagRecord):
                    # 直接使用已有的 SliceTagRecord 对象
                    pass
                else:
                    print(f"⚠️ 未知的slice_data类型: {type(slice_data)}")
                    return None
            else:
                # 使用新的参数格式创建slice_data
                slice_data = SliceTagRecord(
                    slice_id=slice_name or "",
                    video_id=video_id or "",
                    slice_name=slice_name or "",
                    start_time=start_time,
                    end_time=end_time, 
                    duration_seconds=duration,
                    main_category=main_tag,
                    sub_tags=ai_sub_tags or [],
                    subtitle_text="",  # 通用字幕（AI切片使用）
                    confidence_score=confidence,
                    product_subtitle=product_subtitle_content  # 产品字幕（会被优先使用到"对应字幕文本"字段）
                )
                
            # 验证主标签和子标签的关联性（仅当主标签不为空时）
            if slice_data.main_category and slice_data.main_category.strip():
                validation_result = self.validate_sub_tags(slice_data.main_category, slice_data.sub_tags)
                
                if not validation_result["valid"]:
                    print(f"❌ 子标签验证失败:")
                    print(f"   主标签: {slice_data.main_category}")
                    print(f"   无效子标签: {validation_result.get('invalid_tags', [])}")
                    print(f"   可用子标签: {validation_result.get('available_tags', [])}")
                    return None
            else:
                # 主标签为空时，跳过验证，允许任意子标签（AI识别结果）
                if slice_data.main_category:
                    print(f"ℹ️ 主标签: {slice_data.main_category}")
                else:
                    print(f"ℹ️ 主标签为空，跳过子标签验证")
            
            app_token = self.app_config["app_token"]
            table_id = self.app_config["tables"]["slice_tag"]["table_id"]
            
            if not app_token or not table_id:
                print("❌ 数据池未初始化，请先创建数据池")
                return None
                
            access_token = self._get_access_token()
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 🔧 标准化标签格式
            normalized_main_tag = self.normalize_main_tag(slice_data.main_category)
            normalized_sub_tags = self.normalize_sub_tags(slice_data.sub_tags)
            
            # 将子标签列表格式化为文本
            sub_tags_text = self.format_sub_tags_text(normalized_sub_tags)
            
            # 🔍 调试输出
            print(f"  🔍 标签标准化:")
            print(f"     原始主标签: '{slice_data.main_category}' → 标准化: '{normalized_main_tag}'")
            print(f"     原始子标签: {slice_data.sub_tags}")
            print(f"     标准化子标签: {normalized_sub_tags}")
            print(f"     格式化子标签: '{sub_tags_text}'")
            
            # 构建完整的AI标签信息
            labels_info = []
            if normalized_sub_tags:
                labels_info.extend(normalized_sub_tags)
            if hasattr(slice_data, 'confidence_score') and slice_data.confidence_score:
                labels_info.append(f"置信度: {slice_data.confidence_score}")
            labels_text = " | ".join(labels_info) if labels_info else ""
            
            # 准备记录数据
            # 智能字幕内容选择：产品介绍切片优先使用产品字幕，否则使用通用字幕
            subtitle_content = slice_data.subtitle_text
            if hasattr(slice_data, 'product_subtitle') and slice_data.product_subtitle:
                subtitle_content = slice_data.product_subtitle
            
            record_fields = {
                "关联video_ID": slice_data.video_id,  # 修复：使用大写ID匹配表字段定义
                "切片名称": slice_data.slice_name,
                "开始时间": slice_data.start_time,
                "结束时间": slice_data.end_time,
                "时长秒": slice_data.duration_seconds,
                "Labels": labels_text,  # AI分析的完整标签信息
                "对应字幕文本": subtitle_content,  # 智能字幕：产品介绍切片使用完整SRT，AI切片使用片段字幕
                "主标签类别": normalized_main_tag,  # 使用标准化的主标签
                "子标签": sub_tags_text,  # 使用标准化的子标签
                "置信度分数": slice_data.confidence_score,
                "审核状态": "待审核",
                "修改原因": ""  # 新增：严格对应飞书表字段，默认为空
            }
            
            # 处理切片文件上传（产品介绍类型跳过上传）
            if slice_file_path and Path(slice_file_path).exists():
                file_size_mb = Path(slice_file_path).stat().st_size / (1024 * 1024)
                print(f"  📹 切片文件: {Path(slice_file_path).name} ({file_size_mb:.1f}MB)")
                
                # 检查是否为产品介绍切片（跳过上传）
                if normalized_main_tag == "🍼 产品介绍":
                    print(f"  ℹ️ 产品介绍视频跳过上传，仅记录本地路径")
                    # 在Labels字段中记录本地路径信息
                    local_path_info = f"本地路径: {slice_file_path}"
                    if record_fields["Labels"]:
                        record_fields["Labels"] += f" | {local_path_info}"
                    else:
                        record_fields["Labels"] = local_path_info
                else:
                    # 验证视频文件是否包含视频流
                    validation = self.validate_video_file(slice_file_path)
                if not validation["is_valid"]:
                    print(f"  ⚠️ 跳过文件上传: {validation['reason']}")
                    # 在Labels字段中标注这是音频片段
                    if record_fields["Labels"]:
                        record_fields["Labels"] += f" | [音频片段: {validation['reason']}]"
                    else:
                        record_fields["Labels"] = f"[音频片段: {validation['reason']}]"
                else:
                        # 使用云文档素材上传（仅非产品介绍类型）
                    file_token = self.upload_media_to_drive(slice_file_path)
                    if file_token:
                        # 构造附件格式并存储到"切片"字段
                        attachment_data = [{
                            "file_token": file_token,
                            "name": Path(slice_file_path).name,
                            "size": Path(slice_file_path).stat().st_size,
                            "tmp_url": ""  # 由飞书自动处理
                        }]
                        record_fields["切片"] = attachment_data
                        print(f"  ✅ 切片文件上传成功并关联到记录")
                    else:
                        print(f"  ❌ 切片文件上传失败，跳过附件关联")
            
            record_data = {"fields": record_fields}
            
            response = requests.post(url, headers=headers, json=record_data, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                record_id = result["data"]["record"]["record_id"]
                print(f"✅ 切片标签记录添加成功: {slice_data.slice_id}")
                print(f"   主标签: {slice_data.main_category}")
                print(f"   子标签: {sub_tags_text}")
                return record_id
            else:
                print(f"❌ 切片标签记录添加失败: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 切片标签记录添加异常: {e}")
            return None

    def save_config(self, config_file: str = "optimized_pool_config.json") -> bool:
        """保存优化数据池配置"""
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.app_config, f, ensure_ascii=False, indent=2)
            print(f"✅ 优化数据池配置已保存到: {config_file}")
            return True
        except Exception as e:
            print(f"❌ 配置保存失败: {e}")
            return False

    def get_access_info(self) -> Dict:
        """获取访问信息"""
        if not self.app_config["app_token"]:
            return {"error": "数据池未创建"}
            
        return {
            "app_name": self.app_config["app_name"],
            "app_token": self.app_config["app_token"],
            "access_url": f"https://feishu.cn/base/{self.app_config['app_token']}",
            "tables": {
                "video_base": {
                    "name": self.app_config["tables"]["video_base"]["name"],
                    "url": f"https://feishu.cn/base/{self.app_config['app_token']}?table={self.app_config['tables']['video_base']['table_id']}"
                },
                "slice_tag": {
                    "name": self.app_config["tables"]["slice_tag"]["name"],
                    "url": f"https://feishu.cn/base/{self.app_config['app_token']}?table={self.app_config['tables']['slice_tag']['table_id']}"
                }
            }
        }

    def test_connection(self) -> bool:
        """测试连接"""
        token = self._get_access_token()
        return token is not None

    def get_sub_tags_for_main_category(self, main_category: str) -> List[str]:
        """根据主标签获取对应的子标签列表"""
        return self.tag_manager.get_sub_tags_for_main_category(main_category) if self.tag_manager else []
    
    def validate_sub_tags(self, main_category: str, sub_tags: List[str]) -> Dict:
        """验证子标签是否属于指定的主标签类别"""
        return self.tag_manager.validate_sub_tags(main_category, sub_tags) if self.tag_manager else {}
    
    def format_sub_tags_text(self, sub_tags: List[str]) -> str:
        """将子标签列表格式化为文本"""
        return self.tag_manager.format_sub_tags_text(sub_tags) if self.tag_manager else ", ".join(sub_tags)
    
    def parse_sub_tags_text(self, sub_tags_text: str) -> List[str]:
        """解析子标签文本为列表"""
        return self.tag_manager.parse_sub_tags_text(sub_tags_text) if self.tag_manager else [tag.strip() for tag in sub_tags_text.replace('，', ',').split(',')]
    
    def normalize_main_tag(self, main_tag: str) -> str:
        """标准化主标签格式"""
        return self.tag_manager.normalize_main_tag(main_tag) if self.tag_manager else main_tag
    
    def normalize_sub_tags(self, sub_tags: List[str]) -> List[str]:
        """标准化子标签格式"""
        return self.tag_manager.normalize_sub_tags(sub_tags) if self.tag_manager else [tag.strip() for tag in sub_tags]

    # ========== 新增功能：数据同步和CRUD操作 ==========
    
    def sync_from_bitable(self, table_type: str = "both") -> Dict:
        """
        同步获取多维表格上的更新状态
        
        Args:
            table_type: "video_base", "slice_tag", "both"
        
        Returns:
            Dict: 同步结果
        """
        try:
            print(f"🔄 开始同步多维表格数据...")
            
            app_token = self.app_config["app_token"]
            if not app_token:
                print("❌ 数据池未初始化")
                return {"error": "数据池未初始化"}
            
            access_token = self._get_access_token()
            if not access_token:
                return {"error": "无法获取访问令牌"}
            
            sync_result = {"video_base": [], "slice_tag": []}
            
            # 同步视频基础池
            if table_type in ["video_base", "both"]:
                video_records = self._fetch_table_records(app_token, "video_base", access_token)
                if video_records:
                    sync_result["video_base"] = video_records
                    print(f"✅ 视频基础池同步完成: {len(video_records)} 条记录")
                
            # 同步切片标签池
            if table_type in ["slice_tag", "both"]:
                slice_records = self._fetch_table_records(app_token, "slice_tag", access_token)
                if slice_records:
                    sync_result["slice_tag"] = slice_records
                    print(f"✅ 切片标签池同步完成: {len(slice_records)} 条记录")
            
            return sync_result
            
        except Exception as e:
            print(f"❌ 同步异常: {e}")
            return {"error": str(e)}

    def _fetch_table_records(self, app_token: str, table_type: str, access_token: str) -> List[Dict]:
        """获取表格所有记录"""
        try:
            table_id = self.app_config["tables"][table_type]["table_id"]
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            all_records = []
            page_token = None
            
            while True:
                params = {"page_size": 100}
                if page_token:
                    params["page_token"] = page_token
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                result = response.json()
                
                if result.get("code") == 0:
                    records = result.get("data", {}).get("items", [])
                    all_records.extend(records)
                    
                    page_token = result.get("data", {}).get("page_token")
                    if not page_token:
                        break
                else:
                    print(f"❌ 获取{table_type}记录失败: {result}")
                    break
            
            return all_records
            
        except Exception as e:
            print(f"❌ 获取{table_type}记录异常: {e}")
            return []

    def update_record_fields(self, table_type: str, record_id: str, field_updates: Dict) -> bool:
        """
        根据用户输入更新字段
        
        Args:
            table_type: "video_base" 或 "slice_tag"
            record_id: 记录ID
            field_updates: 要更新的字段字典 {"字段名": "新值"}
        
        Returns:
            bool: 更新是否成功
        """
        try:
            app_token = self.app_config["app_token"]
            table_id = self.app_config["tables"][table_type]["table_id"]
            
            if not app_token or not table_id:
                print("❌ 数据池未初始化")
                return False
            
            access_token = self._get_access_token()
            if not access_token:
                return False
            
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 构建更新数据
            update_data = {"fields": field_updates}
            
            response = requests.put(url, headers=headers, json=update_data, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                print(f"✅ 记录更新成功: {record_id}")
                print(f"📝 更新字段: {list(field_updates.keys())}")
                return True
            else:
                print(f"❌ 记录更新失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 记录更新异常: {e}")
            return False

    def query_records(self, table_type: str, filter_conditions: Dict = None, fields: List[str] = None) -> List[Dict]:
        """
        查询记录 (Read操作)
        
        Args:
            table_type: "video_base" 或 "slice_tag"
            filter_conditions: 过滤条件 (暂时简单实现，后续可扩展)
            fields: 要返回的字段列表
        
        Returns:
            List[Dict]: 查询结果
        """
        try:
            app_token = self.app_config["app_token"]
            table_id = self.app_config["tables"][table_type]["table_id"]
            
            if not app_token or not table_id:
                print("❌ 数据池未初始化")
                return []
            
            access_token = self._get_access_token()
            if not access_token:
                return []
            
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            params = {"page_size": 100}
            if fields:
                params["field_names"] = ",".join(fields)
            
            all_records = []
            page_token = None
            
            while True:
                if page_token:
                    params["page_token"] = page_token
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                result = response.json()
                
                if result.get("code") == 0:
                    records = result.get("data", {}).get("items", [])
                    
                    # 应用过滤条件 (简单实现)
                    if filter_conditions:
                        filtered_records = []
                        for record in records:
                            match = True
                            for field, value in filter_conditions.items():
                                if record.get("fields", {}).get(field) != value:
                                    match = False
                                    break
                            if match:
                                filtered_records.append(record)
                        records = filtered_records
                    
                    all_records.extend(records)
                    
                    page_token = result.get("data", {}).get("page_token")
                    if not page_token:
                        break
                else:
                    print(f"❌ 查询记录失败: {result}")
                    break
            
            print(f"✅ 查询完成: 找到 {len(all_records)} 条记录")
            return all_records
            
        except Exception as e:
            print(f"❌ 查询记录异常: {e}")
            return []

    def delete_record(self, table_type: str, record_id: str) -> bool:
        """
        删除记录 (Delete操作)
        
        Args:
            table_type: "video_base" 或 "slice_tag"
            record_id: 记录ID
        
        Returns:
            bool: 删除是否成功
        """
        try:
            app_token = self.app_config["app_token"]
            table_id = self.app_config["tables"][table_type]["table_id"]
            
            if not app_token or not table_id:
                print("❌ 数据池未初始化")
                return False
            
            access_token = self._get_access_token()
            if not access_token:
                return False
            
            url = f"{self.base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            response = requests.delete(url, headers=headers, timeout=30)
            result = response.json()
            
            if result.get("code") == 0:
                print(f"✅ 记录删除成功: {record_id}")
                return True
            else:
                print(f"❌ 记录删除失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 记录删除异常: {e}")
            return False

    def batch_operations(self, operations: List[Dict]) -> Dict:
        """
        批量操作
        
        Args:
            operations: 操作列表，每个操作包含 {"action": "create/update/delete", "table_type": "...", "data": {...}}
        
        Returns:
            Dict: 批量操作结果
        """
        try:
            results = {"success": [], "failed": []}
            
            for i, operation in enumerate(operations):
                action = operation.get("action")
                table_type = operation.get("table_type")
                data = operation.get("data", {})
                
                print(f"🔄 执行操作 {i+1}/{len(operations)}: {action} - {table_type}")
                
                if action == "create":
                    if table_type == "video_base":
                        result = self.add_video_base_record(data)
                    elif table_type == "slice_tag":
                        result = self.add_slice_tag_record(data)
                    else:
                        result = None
                    
                    if result:
                        results["success"].append({"operation": i+1, "action": action, "result": result})
                    else:
                        results["failed"].append({"operation": i+1, "action": action, "error": "创建失败"})
                
                elif action == "update":
                    record_id = data.get("record_id")
                    field_updates = data.get("field_updates", {})
                    
                    if record_id and field_updates:
                        success = self.update_record_fields(table_type, record_id, field_updates)
                        if success:
                            results["success"].append({"operation": i+1, "action": action, "record_id": record_id})
                        else:
                            results["failed"].append({"operation": i+1, "action": action, "error": "更新失败"})
                    else:
                        results["failed"].append({"operation": i+1, "action": action, "error": "缺少必要参数"})
                
                elif action == "delete":
                    record_id = data.get("record_id")
                    
                    if record_id:
                        success = self.delete_record(table_type, record_id)
                        if success:
                            results["success"].append({"operation": i+1, "action": action, "record_id": record_id})
                        else:
                            results["failed"].append({"operation": i+1, "action": action, "error": "删除失败"})
                    else:
                        results["failed"].append({"operation": i+1, "action": action, "error": "缺少记录ID"})
                
                else:
                    results["failed"].append({"operation": i+1, "action": action, "error": "不支持的操作"})
            
            print(f"\n📊 批量操作完成:")
            print(f"✅ 成功: {len(results['success'])} 个操作")
            print(f"❌ 失败: {len(results['failed'])} 个操作")
            
            return results
            
        except Exception as e:
            print(f"❌ 批量操作异常: {e}")
            return {"error": str(e)}

    def interactive_mode(self):
        """交互式操作模式"""
        print("\n🎯 进入交互式操作模式")
        print("=" * 50)
        
        while True:
            print("\n📋 可用操作:")
            print("1. 同步数据 (sync)")
            print("2. 查询记录 (query)")
            print("3. 更新记录 (update)")
            print("4. 删除记录 (delete)")
            print("5. 添加记录 (add)")
            print("6. 退出 (quit)")
            
            choice = input("\n请选择操作 (1-6): ").strip()
            
            if choice == "1" or choice.lower() == "sync":
                table_type = input("同步哪个表? (video_base/slice_tag/both): ").strip()
                if table_type in ["video_base", "slice_tag", "both"]:
                    result = self.sync_from_bitable(table_type)
                    if "error" not in result:
                        print(f"📊 同步结果: {len(result.get('video_base', []))} 个视频, {len(result.get('slice_tag', []))} 个切片")
                else:
                    print("❌ 无效的表类型")
            
            elif choice == "2" or choice.lower() == "query":
                table_type = input("查询哪个表? (video_base/slice_tag): ").strip()
                if table_type in ["video_base", "slice_tag"]:
                    records = self.query_records(table_type)
                    print(f"📋 查询结果: {len(records)} 条记录")
                    
                    if records and len(records) <= 5:
                        for i, record in enumerate(records):
                            print(f"  {i+1}. {record.get('record_id', 'N/A')}: {list(record.get('fields', {}).keys())}")
                else:
                    print("❌ 无效的表类型")
            
            elif choice == "3" or choice.lower() == "update":
                table_type = input("更新哪个表? (video_base/slice_tag): ").strip()
                record_id = input("记录ID: ").strip()
                field_name = input("字段名: ").strip()
                field_value = input("新值: ").strip()
                
                if table_type in ["video_base", "slice_tag"] and record_id and field_name:
                    success = self.update_record_fields(table_type, record_id, {field_name: field_value})
                    if not success:
                        print("❌ 更新失败")
                else:
                    print("❌ 参数不完整")
            
            elif choice == "4" or choice.lower() == "delete":
                table_type = input("删除哪个表的记录? (video_base/slice_tag): ").strip()
                record_id = input("记录ID: ").strip()
                
                if table_type in ["video_base", "slice_tag"] and record_id:
                    confirm = input(f"确认删除记录 {record_id}? (y/n): ").strip().lower()
                    if confirm == "y":
                        success = self.delete_record(table_type, record_id)
                        if not success:
                            print("❌ 删除失败")
                    else:
                        print("取消删除")
                else:
                    print("❌ 参数不完整")
            
            elif choice == "5" or choice.lower() == "add":
                table_type = input("添加到哪个表? (video_base/slice_tag): ").strip()
                
                if table_type == "video_base":
                    print("\n📹 添加视频基础记录")
                    video_id = input("视频ID: ").strip()
                    video_name = input("视频名称: ").strip()
                    
                    # 视频文件
                    video_file = input("视频文件路径 (可选，直接回车跳过): ").strip()
                    video_file_path = video_file if video_file and Path(video_file).exists() else None
                    
                    # 字幕处理
                    srt_choice = input("字幕输入方式: 1=文件路径, 2=直接输入内容, 其他=跳过: ").strip()
                    srt_file_path = None
                    srt_content = None
                    
                    if srt_choice == "1":
                        srt_file = input("SRT文件路径: ").strip()
                        srt_file_path = srt_file if srt_file and Path(srt_file).exists() else None
                    elif srt_choice == "2":
                        print("请输入字幕内容 (输入'END'结束):")
                        srt_lines = []
                        while True:
                            line = input()
                            if line.strip() == "END":
                                break
                            srt_lines.append(line)
                        srt_content = "\n".join(srt_lines)
                    
                    # 其他信息
                    try:
                        file_size = float(input("文件大小(MB, 可选): ").strip() or "0")
                        duration = int(input("视频时长(秒, 可选): ").strip() or "0")
                    except:
                        file_size, duration = 0, 0
                    
                    resolution = input("分辨率 (可选): ").strip()
                    source_channel = input("来源渠道 (可选): ").strip()
                    
                    if video_id and video_name:
                        record_id = self.add_video_base_record_with_content(
                            video_id=video_id,
                            video_name=video_name,
                            video_file_path=video_file_path,
                            srt_file_path=srt_file_path,
                            srt_content=srt_content,
                            file_size_mb=file_size,
                            duration_seconds=duration,
                            resolution=resolution,
                            source_channel=source_channel
                        )
                        if record_id:
                            print(f"✅ 视频记录添加成功: {record_id}")
                        else:
                            print("❌ 视频记录添加失败")
                    else:
                        print("❌ 视频ID和视频名称不能为空")
                
                elif table_type == "slice_tag":
                    print("📝 切片标签记录添加功能请使用现有的 add_slice_tag_record 方法")
                else:
                    print("❌ 无效的表类型")
            
            elif choice == "6" or choice.lower() == "quit":
                print("👋 退出交互式模式")
                break
            
            else:
                print("❌ 无效的选择，请重新输入")

    def get_main_video_record_id(self, video_name: str) -> Optional[str]:
        """根据 video_name 查询主视频记录并返回其 record_id"""
        table_id = self.app_config['tables']['video_base']['table_id']
        
        # 构建查询参数，使用正确的字段名"视频ID"
        params = {
            "filter": f'CurrentValue.[视频ID] = "{video_name}"',
            "page_size": 1
        }
        
        records = self._list_records(self.app_config['app_token'], table_id, params)
        
        if records:
            return records[0].get('record_id')
        
        return None

    def _ensure_table_and_fields(self, app_token, table_name, table_config):
        """确保表和字段存在，如果不存在则创建"""
        print(f"  - 检查表 '{table_name}'...")


if __name__ == "__main__":
    # 示例：如何使用管理器
    # manager = OptimizedDataPoolManager()
    # manager.add_main_video_record({"video_id": "video_test", "video_name": "测试视频"})
    pass 