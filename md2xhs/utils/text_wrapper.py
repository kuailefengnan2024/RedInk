import re

def wrap_semantic(text: str, max_chars: int) -> str:
    """
    语义化自动折行工具：
    按照最大字数限制折行，并尽量保证语义完整。
    """
    if not text:
        return ""
    
    # 如果已经是 HTML 格式（比如已经带了 br 或标签），直接返回
    if "<br" in text or "</" in text:
        return text

    # 清洗文本，移除首尾空白
    text = text.strip()
    if len(text) <= max_chars:
        return text

    # 定义自然的语义分割符号级别
    # 第一级：标点符号和空格
    punctuations = r"[，。！？；、：\s\(\)（）]"
    # 第二级：常见的连词、介词、助词（在其前面折行通常是语义连贯的）
    semantic_particles = r"(?=但|却|和|并|与|且|但|因|而|被|让|把|因为|所以|如果|但是|然而|通过|为了|由于|从而)"
    
    # 尝试寻找最佳折行点
    # 我们需要在 [1, max_chars] 范围内寻找一个最合适的折行点
    split_idx = -1
    
    # 1. 查找标点符号或括号
    for m in re.finditer(punctuations, text):
        idx = m.end() # 标点符号后面折行
        if idx <= max_chars:
            split_idx = idx
        else:
            break
            
    # 2. 如果没找到标点符号，查找连词/助词
    if split_idx == -1:
        for m in re.finditer(semantic_particles, text):
            idx = m.start() # 连词前面折行
            if 0 < idx <= max_chars:
                split_idx = idx
            elif idx > max_chars:
                break
                
    # 3. 如果还是没找到，强行在 max_chars 处切分
    if split_idx == -1 or split_idx == 0:
        split_idx = max_chars

    left = text[:split_idx].strip()
    right = text[split_idx:].strip()
    
    # 递归处理剩余部分
    wrapped_right = wrap_semantic(right, max_chars)
    if wrapped_right:
        return f"{left}<br>{wrapped_right}"
    return left
