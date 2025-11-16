#!/usr/bin/env python3
"""
端到端视频语义分割演示程序 - 🍭Origin驱动架构

本程序整合了两个核心功能：
1.  **精细化转录**: 使用DashScope将视频转录为包含词级时间戳的SRT。
2.  **AI语义分割**: 使用DeepSeek/Claude模型分析文本，按营销意图重新划分SRT片段。

程序自动生成两个版本的SRT文件：
- 带标注版本: 包含 [🪝 钩子] 等语义标注
- 干净版本: 不包含标注符号的纯字幕版本（文件名后缀_clean）

使用示例:
    uv run python demo_srt.py \\
        --video-path ../🍭Origin/ref/通用-保护薄弱期-HMO&自御力-启赋-CTA7.mp4 \\
        --output-path ./data/output/demo_semantic_output.srt
    
输出文件:
    - demo_semantic_output.srt (带标注版本)
    - demo_semantic_output_clean.srt (干净版本)
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any

# 确保src目录在Python路径中
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# 导入核心模块
from batch_video_to_srt import BatchVideoTranscriber
from word_level_semantic_splitter import WordLevelSemanticSplitter
from env_loader import load_env_config, get_dashscope_api_key, get_default_vocab_id

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_semantic_pipeline(video_path: str, output_path: str):
    """
    执行完整的语义分割流程：转录 -> AI分析 -> 生成新SRT

    Args:
        video_path (str): 输入视频文件路径
        output_path (str): 输出的语义SRT文件路径
    """
    logger.info("🚀 开始端到端语义分割流程...")
    
    # --- 步骤 1: 精细化转录 ---
    logger.info("--- 步骤 1/3: 正在进行精细化转录 ---")
    
    try:
        # 初始化转录器，必须开启fine_grained模式以获取词级数据
        transcriber = BatchVideoTranscriber(api_key=get_dashscope_api_key(), fine_grained=True)
        
        # 使用一个临时文件路径，因为我们主要需要的是原始数据
        temp_srt_path = Path(output_path).parent / f"temp_{Path(video_path).stem}.srt"
        temp_srt_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"📹 正在处理视频: {video_path}")
        # 该方法会执行转录并保存一个临时的SRT文件
        transcriber.transcribe_video_to_srt_with_details(
            video_path=video_path,
            output_srt_path=str(temp_srt_path),
            preset_vocabulary_id=get_default_vocab_id()
        )
        
        # 从转录器中获取包含词级时间戳的原始结果
        transcription_result = getattr(transcriber, 'last_transcription_result', None)

        if not transcription_result or not transcription_result.get("success"):
            logger.error("❌ 转录失败或未获得有效结果。流程终止。")
            return

        logger.info("✅ 精细化转录成功，已获取词级时间戳数据。")
        # 临时保存原始数据以供调试
        debug_json_path = temp_srt_path.with_suffix('.json')
        with open(debug_json_path, 'w', encoding='utf-8') as f:
            json.dump(transcription_result, f, ensure_ascii=False, indent=2)
        logger.info(f"🔍 调试信息：原始转录数据已保存到 {debug_json_path}")

    except Exception as e:
        logger.error(f"❌ 在转录步骤中发生严重错误: {e}", exc_info=True)
        return

    # --- 步骤 2: AI语义分割 ---
    logger.info("--- 步骤 2/3: 正在进行AI语义分割 ---")
    
    try:
        splitter = WordLevelSemanticSplitter()
        
        # 使用原始转录数据进行分析
        # 注意：这里的 srt_path 参数只是为了兼容，实际数据来自 transcription_result
        semantic_segments = splitter.analyze_srt_with_word_timestamps(
            srt_path=str(temp_srt_path), 
            transcription_result=transcription_result
        )

        if not semantic_segments:
            logger.error("❌ AI语义分割失败，未生成任何片段。流程终止。")
            return

        logger.info(f"✅ AI语义分割成功，生成 {len(semantic_segments)} 个语义化片段。")

    except Exception as e:
        logger.error(f"❌ 在AI语义分割步骤中发生严重错误: {e}", exc_info=True)
        return

    # --- 步骤 3: 导出最终的SRT文件（双版本） ---
    logger.info(f"--- 步骤 3/3: 正在导出语义化SRT文件（双版本） ---")
    
    try:
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 导出为双版本SRT文件：带标注版本 + 干净版本
        success = splitter.export_to_srt_dual_versions(semantic_segments, output_path)

        if success:
            # 生成文件路径信息
            output_path_obj = Path(output_path)
            clean_path = output_path_obj.parent / f"{output_path_obj.stem}_clean{output_path_obj.suffix}"
            
            logger.info(f"🎉 流程成功完成！已生成两个版本的SRT文件:")
            logger.info(f"📊 带标注版本: {output_path}")
            logger.info(f"🧹 干净版本: {clean_path}")
            
            # 导出增强配置（包含学习到的新关键词）
            config_path = Path(output_path).parent / f"enhanced_config_{Path(output_path).stem}.json"
            if splitter.export_enhanced_config(str(config_path)):
                logger.info(f"📚 增强配置已保存，可用于提高对新广告的泛化能力")
            
            # 可以选择删除临时文件
            # temp_srt_path.unlink(missing_ok=True)
            # debug_json_path.unlink(missing_ok=True)
        else:
            logger.error("❌ 导出SRT文件失败。")

    except Exception as e:
        logger.error(f"❌ 在导出SRT文件步骤中发生严重错误: {e}", exc_info=True)
        return


def main():
    # 加载环境变量
    load_env_config()
    
    parser = argparse.ArgumentParser(
        description="端到端视频语义分割演示程序",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  uv run python demo_srt.py \\
    --video-path ../🍭Origin/ref/通用-保护薄弱期-HMO&自御力-启赋-CTA7.mp4 \\
    --output-path ./data/output/demo_semantic_output.srt

输出文件:
  - demo_semantic_output.srt (带[🪝 钩子]等标注的版本)
  - demo_semantic_output_clean.srt (干净的纯字幕版本)
"""
    )
    parser.add_argument(
        "--video-path",
        required=True,
        help="输入视频文件的路径"
    )
    parser.add_argument(
        "--output-path",
        required=True,
        help="输出的语义化SRT文件的路径（带标注版本，同时会生成_clean版本）"
    )
    
    args = parser.parse_args()
    
    # 检查视频文件是否存在
    if not Path(args.video_path).is_file():
        logger.error(f"视频文件不存在: {args.video_path}")
        sys.exit(1)
        
    run_semantic_pipeline(args.video_path, args.output_path)


if __name__ == "__main__":
    main() 