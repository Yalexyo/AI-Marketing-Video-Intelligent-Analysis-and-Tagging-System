"""
Google Cloud Video Intelligence API 分析器 - 独立版本

专门处理Google Cloud视频分析功能的模块，已移除对项目其他模块的依赖
"""

import os
import time
import logging
import json
import uuid
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class GoogleVideoAnalyzer:
    """Google Cloud Video Intelligence API 分析器"""

    def __init__(self, credentials_path: Optional[str] = None):
        """
        初始化Google Cloud分析器

        Args:
            credentials_path: Google Cloud凭据文件路径
        """
        # 凭据文件路径优先级
        if credentials_path:
            self.credentials_path = credentials_path
        elif os.path.exists("google_credentials.json"):
            self.credentials_path = "google_credentials.json"
        else:
            self.credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        
        self.client = None
        self.storage_client = None
        self.project_id = None

        # 设置环境变量
        if self.credentials_path and os.path.exists(self.credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(os.path.abspath(self.credentials_path))
            logger.info(f"使用Google Cloud凭据: {self.credentials_path}")

            # 获取项目ID
            try:
                with open(self.credentials_path, 'r', encoding='utf-8') as f:
                    cred_data = json.load(f)
                    self.project_id = cred_data.get('project_id')
                    logger.info(f"项目ID: {self.project_id}")
            except Exception as e:
                logger.warning(f"无法读取项目ID: {e}")
        else:
            logger.warning(f"Google Cloud凭据文件不存在: {self.credentials_path}")

        self._initialize_clients()

    def _initialize_clients(self):
        """初始化Google Cloud客户端"""
        try:
            from google.cloud import videointelligence_v1 as vi
            from google.cloud import storage

            self.client = vi.VideoIntelligenceServiceClient()
            self.storage_client = storage.Client()
            logger.info("Google Cloud客户端初始化成功")
        except Exception as e:
            logger.error(f"Google Cloud客户端初始化失败: {str(e)}")
            self.client = None
            self.storage_client = None

    def check_credentials(self) -> Tuple[bool, Optional[str]]:
        """检查Google Cloud凭据是否有效"""
        if self.credentials_path and os.path.exists(self.credentials_path):
            try:
                # 验证JSON文件格式
                import json
                with open(self.credentials_path, 'r', encoding='utf-8') as f:
                    cred_data = json.load(f)

                # 检查必要字段
                required_fields = ['type', 'project_id', 'private_key', 'client_email']
                if all(field in cred_data for field in required_fields):
                    logger.info(f"Google Cloud凭据有效，项目ID: {cred_data.get('project_id', 'Unknown')}")
                    return True, self.credentials_path
                else:
                    logger.error("Google Cloud凭据文件缺少必要字段")
                    return False, None
            except Exception as e:
                logger.error(f"Google Cloud凭据文件验证失败: {str(e)}")
                return False, None
        else:
            logger.warning(f"Google Cloud凭据文件不存在: {self.credentials_path}")
            return False, None

    def analyze_video(
        self,
        video_path: Optional[str] = None,
        video_uri: Optional[str] = None,
        features: List[str] = None,
        progress_callback: Optional[callable] = None,
        auto_cleanup_storage: bool = False,
        bucket_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析视频内容

        Args:
            video_path: 本地视频文件路径
            video_uri: 云端视频URI（如gs://bucket/video.mp4）
            features: 要分析的功能列表
            progress_callback: 进度回调函数
            auto_cleanup_storage: 是否在分析完成后自动删除上传的文件
            bucket_name: Cloud Storage桶名（如果不提供会使用默认的video-slice-bucket）

        Returns:
            分析结果字典
        """
        if not self.client:
            raise Exception("Google Cloud客户端未初始化")

        # 检查网络连接
        if progress_callback:
            progress_callback(5, "检查网络连接和服务可用性...")

        try:
            import requests
            # 检查基本网络连接
            requests.get("https://www.google.com", timeout=5)

            # 快速检查Google Cloud服务可用性
            response = requests.get("https://videointelligence.googleapis.com", timeout=10)
            logger.info("Google Cloud Video Intelligence服务连接正常")
        except Exception as e:
            error_msg = f"无法连接到Google Cloud服务，请检查网络连接: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        uploaded_blob_name = None  # 记录上传的文件名，用于后续删除
        bucket = None

        try:
            from google.cloud import videointelligence_v1 as vi

            # 默认功能 - 只使用镜头检测以提升性能
            if not features:
                features = ["shot_detection"]

            # 转换功能名称为API枚举
            feature_map = {
                "shot_detection": vi.Feature.SHOT_CHANGE_DETECTION,
                "label_detection": vi.Feature.LABEL_DETECTION,
                "text_detection": vi.Feature.TEXT_DETECTION,
                "face_detection": vi.Feature.FACE_DETECTION,
                "object_tracking": vi.Feature.OBJECT_TRACKING
            }

            api_features = [feature_map[f] for f in features if f in feature_map]

            # 构建请求
            if video_path and os.path.exists(video_path):
                # 检查文件大小
                file_size = os.path.getsize(video_path)
                file_size_mb = file_size / (1024 * 1024)

                if progress_callback:
                    progress_callback(15, f"准备处理视频文件 ({file_size_mb:.1f}MB)...")

                # 大文件警告
                if file_size_mb > 200:
                    logger.warning(f"视频文件较大 ({file_size_mb:.1f}MB)，分析可能需要较长时间")
                    if progress_callback:
                        progress_callback(20, f"视频文件较大 ({file_size_mb:.1f}MB)，预计需要5-15分钟...")
                elif file_size_mb > 50:
                    if progress_callback:
                        progress_callback(20, f"视频文件大小适中 ({file_size_mb:.1f}MB)，预计需要2-5分钟...")
                else:
                    if progress_callback:
                        progress_callback(20, f"视频文件较小 ({file_size_mb:.1f}MB)，预计1-2分钟完成...")

                # 如果需要自动清理，或者文件较大，则上传到Cloud Storage
                if auto_cleanup_storage or file_size_mb > 50:
                    if progress_callback:
                        progress_callback(22, "上传视频到Cloud Storage...")
                    
                    # 准备Cloud Storage桶
                    if not bucket_name:
                        bucket_name = "video-slice-bucket"
                    
                    bucket = self._ensure_bucket_exists(bucket_name)
                    if not bucket:
                        raise Exception(f"无法创建或访问存储桶: {bucket_name}")
                    
                    # 生成唯一的云端文件名
                    import time
                    timestamp = int(time.time())
                    file_name = f"slice_analysis_{timestamp}_{uuid.uuid4().hex[:8]}_{Path(video_path).name}"
                    uploaded_blob_name = f"video-analysis/{file_name}"
                    
                    # 上传文件到Cloud Storage
                    gs_uri = self._upload_to_cloud_storage(bucket, video_path, uploaded_blob_name)
                    if not gs_uri:
                        raise Exception("上传视频到Cloud Storage失败")
                    
                    logger.info(f"视频已上传到Cloud Storage: {gs_uri}")
                    request = {"features": api_features, "input_uri": gs_uri}
                    
                    if progress_callback:
                        progress_callback(25, f"视频已上传到云端，开始分析...")
                else:
                    # 小文件直接通过内容上传
                    with open(video_path, "rb") as f:
                        input_content = f.read()
                    request = {"features": api_features, "input_content": input_content}
                    
            elif video_uri:
                # 云端文件
                request = {"features": api_features, "input_uri": video_uri}
            else:
                raise ValueError("必须提供video_path或video_uri")

            # 执行分析
            if progress_callback:
                progress_callback(30, "正在提交分析请求到Google Cloud...")

            # 添加重试机制
            max_retries = 3
            retry_count = 0
            operation = None

            while retry_count < max_retries:
                try:
                    operation = self.client.annotate_video(request=request)
                    break  # 成功就退出循环
                except Exception as e:
                    retry_count += 1
                    error_str = str(e)

                    if "503" in error_str or "failed to connect" in error_str:
                        if retry_count < max_retries:
                            if progress_callback:
                                progress_callback(30, f"网络连接失败，正在重试... ({retry_count}/{max_retries})")
                            time.sleep(5)  # 等待5秒后重试
                            continue
                        else:
                            raise Exception(f"网络连接失败，已重试{max_retries}次: {error_str}")
                    else:
                        raise e

            if not operation:
                raise Exception("无法提交分析请求到Google Cloud")

            if progress_callback:
                progress_callback(35, f"分析请求已提交，操作ID: {operation.operation.name}")

            # 等待完成
            start_time = time.time()
            timeout = 1200  # 20分钟超时
            check_interval = 10  # 每10秒检查一次

            if progress_callback:
                progress_callback(40, "分析任务已提交到Google Cloud，正在处理...")

            while not operation.done():
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    error_msg = f"分析超时（{timeout}秒），视频可能太大或网络较慢"
                    logger.error(error_msg)
                    raise TimeoutError(error_msg)

                if progress_callback:
                    # 非线性进度计算，前期慢后期快
                    progress_ratio = min(elapsed / timeout, 0.8)
                    progress = 40 + int(progress_ratio * 50)  # 40-90%

                    # 估算剩余时间
                    if elapsed > 30:  # 30秒后开始估算
                        estimated_total = elapsed / progress_ratio if progress_ratio > 0 else timeout
                        remaining = max(0, estimated_total - elapsed)
                        progress_callback(
                            progress,
                            f"分析进行中... 已用时 {elapsed:.0f}秒，预计还需 {remaining:.0f}秒"
                        )
                    else:
                        progress_callback(progress, f"分析进行中... 已用时 {elapsed:.0f}秒")

                time.sleep(check_interval)

            result = operation.result()

            if progress_callback:
                progress_callback(95, "分析完成，正在处理结果...")

            # 分析完成后清理Cloud Storage文件（如果需要）
            if auto_cleanup_storage and uploaded_blob_name and bucket:
                try:
                    if progress_callback:
                        progress_callback(97, "清理临时云端文件...")
                    
                    blob = bucket.blob(uploaded_blob_name)
                    blob.delete()
                    logger.info(f"已删除Cloud Storage文件: {uploaded_blob_name}")
                    
                except Exception as e:
                    logger.warning(f"删除Cloud Storage文件失败 {uploaded_blob_name}: {str(e)}")

            if progress_callback:
                progress_callback(100, "分析完成！")

            return {
                "success": True,
                "result": result,
                "features": features,
                "video_path": video_path,
                "video_uri": video_uri,
                "cleanup_performed": auto_cleanup_storage and uploaded_blob_name is not None
            }

        except Exception as e:
            logger.error(f"Google Cloud视频分析失败: {str(e)}")
            
            # 出错时也尝试清理上传的文件
            if auto_cleanup_storage and uploaded_blob_name and bucket:
                try:
                    blob = bucket.blob(uploaded_blob_name)
                    blob.delete()
                    logger.info(f"分析失败，已清理Cloud Storage文件: {uploaded_blob_name}")
                except Exception as cleanup_e:
                    logger.warning(f"清理失败的上传文件时出错: {str(cleanup_e)}")
            
            return {
                "success": False,
                "error": str(e),
                "features": features
            }

    def extract_shots(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从分析结果中提取镜头信息"""
        shots = []

        if not analysis_result.get("success") or not analysis_result.get("result"):
            return shots

        result = analysis_result["result"]
        if not result.annotation_results:
            return shots

        annotation = result.annotation_results[0]

        if hasattr(annotation, 'shot_annotations') and annotation.shot_annotations:
            for i, shot in enumerate(annotation.shot_annotations):
                try:
                    start_time = self._get_time_seconds(shot.start_time_offset)
                    end_time = self._get_time_seconds(shot.end_time_offset)

                    shots.append({
                        'index': i + 1,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'type': f"镜头{i+1}",
                        'confidence': 1.0
                    })
                except Exception as e:
                    logger.warning(f"处理镜头 {i+1} 时出错: {e}")

        return shots

    def extract_labels(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从分析结果中提取标签信息"""
        labels = []

        if not analysis_result.get("success") or not analysis_result.get("result"):
            return labels

        result = analysis_result["result"]
        if not result.annotation_results:
            return labels

        annotation = result.annotation_results[0]

        if hasattr(annotation, 'segment_label_annotations') and annotation.segment_label_annotations:
            for label in annotation.segment_label_annotations:
                label_name = label.entity.description

                for segment in label.segments:
                    try:
                        start_time = self._get_time_seconds(segment.segment.start_time_offset)
                        end_time = self._get_time_seconds(segment.segment.end_time_offset)
                        confidence = segment.confidence

                        labels.append({
                            'label': label_name,
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': end_time - start_time,
                            'confidence': confidence,
                            'type': f"标签_{label_name}"
                        })
                    except Exception as e:
                        logger.warning(f"处理标签 {label_name} 时出错: {e}")

        return labels

    def _get_time_seconds(self, time_offset) -> float:
        """安全地获取时间偏移的秒数"""
        try:
            if hasattr(time_offset, 'total_seconds'):
                return time_offset.total_seconds()
            elif hasattr(time_offset, 'seconds'):
                # 处理 protobuf Duration 对象
                return time_offset.seconds + time_offset.nanos / 1e9
            else:
                # 如果是数字，直接返回
                return float(time_offset)
        except Exception as e:
            logger.warning(f"时间解析错误: {e}")
            return 0.0

    def _ensure_bucket_exists(self, bucket_name: str):
        """确保Cloud Storage桶存在"""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(bucket_name)
                logger.info(f"创建了新的存储桶: {bucket_name}")
            else:
                logger.info(f"使用现有存储桶: {bucket_name}")
            return bucket
        except Exception as e:
            logger.error(f"无法创建或访问存储桶 {bucket_name}: {str(e)}")
            return None

    def _upload_to_cloud_storage(self, bucket, local_path: str, blob_name: str) -> Optional[str]:
        """上传文件到Cloud Storage"""
        try:
            from google.cloud.storage import transfer_manager
            import google.cloud.storage as storage
            
            blob = bucket.blob(blob_name)
            
            # 检查文件大小，为大文件设置更长的超时
            file_size = os.path.getsize(local_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # 根据文件大小设置超时时间 (每MB给予2秒，最少5分钟，最多30分钟)
            timeout_seconds = max(300, min(1800, int(file_size_mb * 2)))
            logger.info(f"上传文件 ({file_size_mb:.1f}MB)，超时设置: {timeout_seconds}秒")
            
            # 设置分块上传参数
            if file_size_mb > 50:
                # 大文件使用分块上传
                logger.info("使用分块上传方式")
                blob.chunk_size = 1024 * 1024 * 5  # 5MB 分块
            
            # 上传文件
            blob.upload_from_filename(local_path, timeout=timeout_seconds)
            
            gs_uri = f"gs://{bucket.name}/{blob_name}"
            logger.info(f"文件上传成功: {gs_uri}")
            return gs_uri
        except Exception as e:
            logger.error(f"上传文件到Cloud Storage失败: {str(e)}")
            return None 