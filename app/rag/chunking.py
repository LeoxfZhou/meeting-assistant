import re


def chunks(text: str, source_type: str, size: int = 380) -> list[dict]:
    """Markdown 优先段落边界，会议优先句界；保留字符位置，会议有限重叠。"""
    result = []
    start = 0
    overlap = 60 if source_type == 'meeting' else 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            pattern = r'[。！？\n]' if source_type == 'meeting' else r'\n\s*\n|\n(?=#)'
            boundaries = list(re.finditer(pattern, text[start+size//2:end]))
            if boundaries:
                end = start + size//2 + boundaries[-1].end()
        content = text[start:end]
        if content.strip():
            result.append({'content':content,'char_start':start,'char_end':end,'chunk_index':len(result)})
        if end == len(text):
            break
        start = end-overlap
    return result
