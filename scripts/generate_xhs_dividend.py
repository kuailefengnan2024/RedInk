# 【功能描述】调用 RedInk ImageService 批量生成「AI 全民红利」小红书轮播图（方向B·财经深度报）
# 【输入】内置 9 页大纲；image_providers.yaml + .env 中的 api-core 配置
# 【输出】history/<task_id>/ 下 PNG；并复制到 DyVault 项目 xhs/output_redink/

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from backend.services.image import ImageService  # noqa: E402

TASK_ID = "20260611_ai_dividend_b"
OUT_COPY = Path(r"D:\DyVault\career\work\research\items\20260611_ai_dividend_for_all\xhs\output_redink")

STYLE_B = """
【全系列视觉锁定 · 方向B「财经深度报」——9页必须严格统一】
背景：深炭黑 #0F1117，叠加极淡网格/数据线（透明度约5%，全系列同一纹理）
配色：冷白大标题 + 浅灰小字说明 + 墨绿 #10B981 仅用于 icon / 高亮线 / CTA，禁止其他强调色
排版：左上锚定；大标题左对齐、超大粗体；小字说明紧挨其下、左对齐，字号约为大标题40%
Icon：每页左上角 1 个小实心 icon（栏目标记），同一套风格，高级克制，可吸引视线但不卡通
构图：左文右简图 或 上文下简图；大量留白；禁止霓虹赛博、复杂插画、emoji、卡通人物
气质：严肃公共议题、高级克制、像 Bloomberg/财新封面，但标题文字有号召力
禁止：小红书 logo、每页不同配色、过度光效、装饰堆砌
"""

USER_TOPIC = (
    "AI 全民红利公约 · 小红书首发轮播。"
    + STYLE_B
    + "双线安全：打工人视角、技术红利共享。不是反AI，不是加税倡议。"
    "目标：吸引支持、评论区打「支持」、留下会实操落地的钩子。"
)

VISUAL = """版式：左上大标题+小字说明，右侧极简线条信息图
背景：深炭黑+极淡网格（与封面完全一致）
Icon：栏目标记icon（左上角小实心，墨绿色）"""

FULL_OUTLINE = f"""
[封面]
大标题：AI 年赚千亿，你得到了什么？
小字说明：当 AI 创造财富，普通人也该有一份
{STYLE_B}
Icon：问号或数据柱状（栏目标记）
视觉：系列基准封面，定义全系列视觉规范

<page>
[内容]
大标题：AI 正在接手这些工作
小字说明：客服 · 设计 · 翻译 · 编程，效率提升了，岗位却在变少
Icon：公文包/岗位
{VISUAL}

<page>
[内容]
大标题：AI 的钱流向了极少数人
小字说明：风险与代价，却由全民承担
Icon：向上箭头/财富集中
{VISUAL}

<page>
[内容]
大标题：挪威：石油收益 → 全民分红
小字说明：已运行数十年，自然资源能共享，AI 收益为什么不能？
Icon：油滴/分红
{VISUAL}

<page>
[内容]
大标题：海外已在讨论全民共享
小字说明：韩国 · 科技领袖 · 共识正在形成，缺中文语境的发声
Icon：地球/讨论
{VISUAL}

<page>
[内容]
大标题：AI 全民红利
小字说明：超额收益纳入公共池，专款专用 · 账目公开 · 反哺全民
Icon：公共池/盾牌
{VISUAL}
备注：系列核心页，标题最醒目，但仍保持同一视觉系统

<page>
[内容]
大标题：分配优先级
小字说明：被 AI 影响的人 → 基层保障 → 教育医疗 → 成熟后现金分红
Icon：阶梯/流程
{VISUAL}

<page>
[内容]
大标题：不是反 AI
小字说明：是让 AI 真正惠及每个人，支持发展，反对红利只流向顶部
Icon：对勾/平衡
{VISUAL}

<page>
[总结]
大标题：认同就评论「支持」
小字说明：人数和留言都会公开记录 · 我会继续推动落地 · 链接在主页置顶
Icon：评论/手势
{VISUAL}
备注：唯一可略加强 CTA 墨绿元素，但整体仍属同一系列
"""

PAGES = [
    {
        "index": 0,
        "type": "cover",
        "content": f"""[封面]
大标题：AI 年赚千亿，你得到了什么？
小字说明：当 AI 创造财富，普通人也该有一份
{STYLE_B}
Icon：数据/问号栏目标记
视觉：系列基准封面，竖版3:4""",
    },
    {
        "index": 1,
        "type": "content",
        "content": f"""[内容]
大标题：AI 正在接手这些工作
小字说明：客服 · 设计 · 翻译 · 编程，效率提升了，岗位却在变少
Icon：岗位/公文包
{VISUAL}""",
    },
    {
        "index": 2,
        "type": "content",
        "content": f"""[内容]
大标题：AI 的钱流向了极少数人
小字说明：风险与代价，却由全民承担
Icon：财富集中/箭头
{VISUAL}""",
    },
    {
        "index": 3,
        "type": "content",
        "content": f"""[内容]
大标题：挪威：石油收益 → 全民分红
小字说明：已运行数十年，自然资源能共享，AI 收益为什么不能？
Icon：油滴/分红
{VISUAL}""",
    },
    {
        "index": 4,
        "type": "content",
        "content": f"""[内容]
大标题：海外已在讨论全民共享
小字说明：韩国 · 科技领袖 · 共识正在形成，缺中文语境的发声
Icon：地球/讨论
{VISUAL}""",
    },
    {
        "index": 5,
        "type": "content",
        "content": f"""[内容]
大标题：AI 全民红利
小字说明：超额收益纳入公共池，专款专用 · 账目公开 · 反哺全民
Icon：公共池/盾牌
{VISUAL}""",
    },
    {
        "index": 6,
        "type": "content",
        "content": f"""[内容]
大标题：分配优先级
小字说明：被 AI 影响的人 → 基层保障 → 教育医疗 → 成熟后现金分红
Icon：阶梯/流程
{VISUAL}""",
    },
    {
        "index": 7,
        "type": "content",
        "content": f"""[内容]
大标题：不是反 AI
小字说明：是让 AI 真正惠及每个人，支持发展，反对红利只流向顶部
Icon：对勾/平衡
{VISUAL}""",
    },
    {
        "index": 8,
        "type": "summary",
        "content": f"""[总结]
大标题：认同就评论「支持」
小字说明：人数和留言都会公开记录 · 我会继续推动落地 · 链接在主页置顶
Icon：评论
{VISUAL}""",
    },
]


def main():
    print(f"RedInk batch · task={TASK_ID} · style=B")
    service = ImageService()
    task_dir = ROOT / "history" / TASK_ID
    task_dir.mkdir(parents=True, exist_ok=True)

    fail = 0
    for event in service.generate_images(
        PAGES,
        task_id=TASK_ID,
        full_outline=FULL_OUTLINE,
        user_topic=USER_TOPIC,
    ):
        et = event["event"]
        data = event["data"]
        if et == "progress":
            msg = data.get("message") or f"page {data.get('index', '?')}"
            print(f"  ... {msg}")
        elif et == "complete":
            print(f"  [OK] index={data['index']}")
        elif et == "error":
            fail += 1
            print(f"  [FAIL] index={data['index']}: {data.get('message', '')[:120]}")
        elif et == "finish":
            print(f"\nDone: {data['completed']}/{data['total']}, failed={data['failed']}")
            print(f"Output: {task_dir}")

    OUT_COPY.mkdir(parents=True, exist_ok=True)
    for i in range(len(PAGES)):
        src = task_dir / f"{i}.png"
        if src.exists():
            dst = OUT_COPY / f"{i + 1:02d}.png"
            shutil.copy2(src, dst)
            print(f"copy -> {dst}")

    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
