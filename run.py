import sys
from pathlib import Path

# =====================================================================
#  参数配置区：可以直接在此修改参数，免去在命令行中输入繁琐的后缀参数
# =====================================================================
# 1. 输入 JSON 路径 (可以填 02_carousel.json 从 LLM 重新跑，或 04_render_design.json 直接渲染)
INPUT_PATH = "md2xhs/examples/output_ai_dividend_v8_31/04_render_design.json"

# 2. 图像和 HTML 的输出目录
OUTPUT_DIR = "md2xhs/examples/output_ai_dividend_v8_31"

# 3. 渲染器类型 ("html" 为 Chrome Headless 截图渲染，"pillow" 为内置 Pillow 绘图)
RENDERER = "html" 
# =====================================================================

# 确保 md2xhs 包能被正确导入
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from md2xhs.cli import main

if __name__ == "__main__":
    # 构建模拟命令行参数
    argv = ["render", INPUT_PATH, "-o", OUTPUT_DIR, "--renderer", RENDERER]
    
    print(f"==================================================")
    print(f"【参数前置检查】")
    print(f"  输入路径: {INPUT_PATH}")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"  渲染器:   {RENDERER}")
    print(f"==================================================")
    
    sys.exit(main(argv))
