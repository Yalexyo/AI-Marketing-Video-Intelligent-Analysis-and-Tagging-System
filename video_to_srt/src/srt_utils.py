import datetime

def to_srt(segments: list) -> str:
    """
    将包含时间戳的文本片段列表转换为SRT格式的字符串。

    Args:
        segments (list): 一个字典列表，每个字典包含 'start', 'end', 和 'text'。
                         例如: [{'start': 0.0, 'end': 2.5, 'text': '你好'}]

    Returns:
        str: 标准SRT格式的字幕内容。
    """
    srt_content = []
    for i, segment in enumerate(segments):
        start_time = segment['start']
        end_time = segment['end']
        text = segment['text']

        # 格式化时间戳 (时:分:秒,毫秒)
        start_srt_time = _format_srt_time(start_time)
        end_srt_time = _format_srt_time(end_time)

        srt_content.append(str(i + 1))
        srt_content.append(f"{start_srt_time} --> {end_srt_time}")
        srt_content.append(text)
        srt_content.append("")  # 每个条目后的空行

    return "\n".join(srt_content)

def _format_srt_time(seconds: float) -> str:
    """将秒数转换为SRT时间戳格式"""
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    milliseconds = int(td.microseconds / 1000)
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}" 