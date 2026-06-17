import sys
from pathlib import Path

# 确保 md2xhs 包能被导入
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from md2xhs.utils.text_wrapper import wrap_semantic

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python wrap_tool.py <待折行文本> [每行最大字数, 默认20]")
        print("例如: python wrap_tool.py \"芯片、云和模型订阅变成了巨头收入。但被 AI 影响和替代的裁员岗位，由公众承担。\" 20")
        sys.exit(1)
        
    text = sys.argv[1]
    max_chars = 20
    if len(sys.argv) >= 3:
        try:
            max_chars = int(sys.argv[2])
        except ValueError:
            pass
        
    wrapped = wrap_semantic(text, max_chars)
    print("================ 折行结果 ================")
    print(wrapped)
    print("==========================================")
