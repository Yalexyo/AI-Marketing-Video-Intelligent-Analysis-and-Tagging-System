#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek AI API 客户端
负责与DeepSeek API进行通信，获取视频与脚本的匹配分析结果
"""

import os
import json
import logging
import requests
import time
from typing import Dict, Any, Optional

# 确保可以从src目录导入env_loader
try:
    from env_loader import get_api_keys
except ImportError:
    # 如果直接运行此文件，需要将父目录添加到sys.path
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.env_loader import get_api_keys

logger = logging.getLogger(__name__)

class DeepSeekClient:
    """与DeepSeek API交互的客户端"""

    def __init__(self, timeout: int = 60, max_retries: int = 3, request_delay: float = 1.5):
        """
        初始化DeepSeek客户端
        
        Args:
            timeout (int): API请求的超时时间（秒）
            max_retries (int): 最大重试次数
            request_delay (float): 请求之间的延迟时间（秒）
        """
        self.api_keys = get_api_keys()
        self.api_key = self.api_keys.get("deepseek")
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self.timeout = timeout
        self.max_retries = max_retries
        self.request_delay = request_delay

        if not self.api_key:
            logger.error("❌ DeepSeek API 密钥未找到！请检查您的环境配置。")
            raise ValueError("DeepSeek API key is missing.")
        
        logger.info(f"🔧 DeepSeek客户端初始化 - 超时:{timeout}s, 重试:{max_retries}次, 延迟:{request_delay}s")

    def get_match_analysis(
        self,
        prompt: str,
        model: str = "deepseek-chat",
        max_tokens: int = 500,
        temperature: float = 0.2,
    ) -> Optional[Dict[str, Any]]:
        """
        调用DeepSeek API获取匹配分析结果（带重试机制）
        
        Args:
            prompt (str): 发送给模型的完整提示
            model (str): 使用的模型名称
            max_tokens (int): 生成结果的最大token数
            temperature (float): 生成的随机性，越低越确定
            
        Returns:
            Optional[Dict[str, Any]]: AI返回的JSON分析结果，如果失败则返回None
        """
        if not self.api_key:
            logger.error("无法进行API调用，因为DeepSeek API密钥缺失。")
            return None

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a professional video content matching analyst."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "response_format": {"type": "json_object"},
        }

        # 重试机制
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = self.request_delay * (2 ** (attempt - 1))  # 指数退避
                    logger.info(f"🔄 第 {attempt + 1} 次尝试，等待 {wait_time:.1f} 秒...")
                    time.sleep(wait_time)
                
                logger.info(f"🚀 向DeepSeek API发送请求 (model: {model})...")
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=body,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                response_json = response.json()
                ai_content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")

                if not ai_content:
                    logger.warning("⚠️ DeepSeek API返回的内容为空。")
                    if attempt < self.max_retries:
                        continue
                    return None

                # 解析AI返回的JSON字符串
                analysis_result = json.loads(ai_content)
                logger.info("✅ 成功从DeepSeek获取并解析了匹配分析。")
                
                # 添加请求间隔（成功后也要等待）
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
                
                return analysis_result

            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    ConnectionResetError) as e:
                logger.warning(f"⚠️ 网络连接问题 (尝试 {attempt + 1}/{self.max_retries + 1}): {type(e).__name__}")
                if attempt == self.max_retries:
                    logger.error(f"❌ 达到最大重试次数 ({self.max_retries + 1})，网络请求失败。")
                continue
                
            except requests.exceptions.HTTPError as http_err:
                if hasattr(response, 'text'):
                    logger.error(f"❌ DeepSeek API请求返回HTTP错误: {http_err} - {response.text}")
                else:
                    logger.error(f"❌ DeepSeek API请求返回HTTP错误: {http_err}")
                break
                
            except json.JSONDecodeError as json_err:
                logger.error(f"❌ 无法解析DeepSeek API返回的JSON内容: {ai_content}")
                logger.debug(f"JSON解析错误详情: {json_err}")
                break
                
            except Exception as e:
                logger.error(f"❌ 调用DeepSeek API时发生未知错误: {type(e).__name__}: {e}")
                if attempt == self.max_retries:
                    logger.error(f"❌ 达到最大重试次数 ({self.max_retries + 1})，请求失败。", exc_info=True)
                continue
        
        return None

if __name__ == "__main__":
    # --- 测试DeepSeek客户端 ---
    print("🧪 测试 DeepSeek API 客户端...")

    # 1. 准备一个模拟的prompt
    # 这个prompt模仿了dynamic_match_config.py中的模板
    mock_prompt = """
你是一个专业的视频内容匹配分析师。请根据以下信息进行匹配分析：

## 脚本段落信息：
- 内容：妈妈拿着奶瓶无奈摇头，宝宝饿得一直哭闹
- 类型：动作描述
- 关键词：['拿着', '无奈', '哭', '哭闹', '摇头']
- 预期情绪：['哭闹', '无奈']

## 视频切片JSON信息：
- 对象描述：妈妈拿着一个空奶瓶，对镜头摇头叹气
- 场景描述：室内，客厅沙发
- 情绪状态：无奈
- 主标签：家庭日常
- 关键词：['妈妈', '奶瓶', '摇头']
- 分析推理：该片段表现了母亲因奶粉问题而无奈的情绪。

## 匹配任务：
请分析视频切片是否适合该脚本段落，并以JSON格式回答：
{{
    "match_score": 0.0-1.0,
    "match_reason": "匹配理由",
    "mismatch_issues": ["问题1", "问题2"]
}}
"""
    try:
        # 2. 初始化客户端（带重试机制）
        client = DeepSeekClient(max_retries=3, request_delay=2.0)
        print("✅ 客户端初始化成功。")

        # 3. 发送请求
        print("⏳ 正在向DeepSeek发送测试请求...")
        analysis = client.get_match_analysis(mock_prompt)

        # 4. 打印结果
        if analysis:
            print("\n🎉 成功从DeepSeek获取到分析结果：")
            print(json.dumps(analysis, indent=2, ensure_ascii=False))
            # 简单验证结果格式
            if "match_score" in analysis and "match_reason" in analysis:
                print("\n✅ 返回结果格式正确！")
            else:
                print("\n❌ 返回结果格式不正确！")
        else:
            print("\n❌ 未能从DeepSeek获取到分析结果。请检查错误日志。")

    except ValueError as e:
        print(f"\n初始化失败: {e}")
    except Exception as e:
        print(f"\n测试过程中发生意外错误: {e}")
