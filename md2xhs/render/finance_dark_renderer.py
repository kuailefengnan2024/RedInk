# 【功能描述】方向B 财经深色主题渲染器（Pillow 代码排版）
# 【输入】Slide 列表；输出目录
# 【输出】01.png … 0N.png 路径列表

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from md2xhs.domain.models import Slide

W, H = 1242, 1660
MARGIN = 96
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_REG = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD_FALLBACKS = [
    FONT_BOLD,
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]
FONT_REG_FALLBACKS = [
    FONT_REG,
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]
BG, SURFACE, BORDER = "#0f1117", "#191d26", "#303746"
TEXT, MUTED = "#f2f4f7", "#aab3bf"
ACCENT, ACCENT_DIM, GRID = "#10b981", "#0d9668", "#171d27"


def _ft(path: str, size: int):
    candidates = FONT_BOLD_FALLBACKS if path == FONT_BOLD else FONT_REG_FALLBACKS
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _sub_pairs(slide: Slide) -> list[tuple[str, str]]:
    return [(s.tag, s.text) for s in slide.sub_items]


class FinanceDarkRenderer:
    def render_all(self, slides: list[Slide], output_dir: str) -> list[str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for stale in out.glob("[0-9][0-9].png"):
            stale.unlink()
        paths: list[str] = []
        renderers = {
            "cover": self._cover,
            "body": self._body,
            "hero": self._hero,
            "estimate": self._estimate,
            "roadmap": self._roadmap,
            "flow": self._flow,
            "cta": self._cta,
        }
        for i, slide in enumerate(slides, 1):
            fn = renderers.get(slide.type, self._body)
            path = out / f"{i:02d}.png"
            fn(slide).save(path, "PNG", optimize=True)
            paths.append(str(path))
        return paths

    def _grid(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        step = 48
        for x in range(0, W, step):
            draw.line([(x, 0), (x, H)], fill=GRID, width=1)
        for y in range(0, H, step):
            draw.line([(0, y), (W, y)], fill=GRID, width=1)
        draw.rectangle((0, 0, W, 3), fill=ACCENT_DIM)
        draw.rectangle((0, H - 3, W, H), fill=ACCENT_DIM)

    def _wrap(self, draw, x, y, text, fnt, color, max_w, gap=12):
        lines = self._wrap_lines(draw, text, fnt, max_w)
        return self._draw_lines(draw, x, y, lines, fnt, color, gap)

    def _wrap_lines(self, draw, text, fnt, max_w):
        lines, cur = [], ""
        for ch in text:
            t = cur + ch
            if draw.textlength(t, font=fnt) <= max_w:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
        return lines

    def _line_h(self, draw, fnt):
        bb = draw.textbbox((0, 0), "国", font=fnt)
        return bb[3] - bb[1]

    def _draw_lines(self, draw, x, y, lines, fnt, color, gap=12):
        line_h = self._line_h(draw, fnt)
        for line in lines:
            draw.text((x, y), line, font=fnt, fill=color)
            y += line_h + gap
        return y

    def _icon_label(self, draw, slide: Slide):
        draw.rounded_rectangle(
            (MARGIN, 88, MARGIN + 56, 88 + 56), 10, fill=SURFACE, outline=ACCENT_DIM, width=2
        )
        fi, fl = _ft(FONT_BOLD, 34), _ft(FONT_REG, 24)
        iw = draw.textlength(slide.icon, font=fi)
        draw.text((MARGIN + 28 - iw / 2, 98), slide.icon, font=fi, fill=ACCENT)
        draw.text((MARGIN + 72, 104), slide.label, font=fl, fill=MUTED)

    def _title_font_size(self, slide: Slide, line: str, *, large=True):
        scale = slide.layout.get("title_scale") or (
            "poster" if slide.type == "cover" else "xlarge" if large else "large"
        )
        n = len(line)
        if scale == "poster":
            return 156 if n <= 7 else 138 if n <= 11 else 120
        if scale == "xlarge":
            return 136 if n <= 7 else 122 if n <= 12 else 108
        return 120 if n <= 7 else 110 if n <= 12 else 98

    def _title(self, draw, y, slide: Slide, *, accent_last=False, large=True):
        for i, line in enumerate(slide.title):
            last = i == len(slide.title) - 1
            color = ACCENT if accent_last and last else TEXT
            sz = self._title_font_size(slide, line, large=large)
            y = self._wrap(draw, MARGIN, y, line, _ft(FONT_BOLD, sz), color, W - MARGIN * 2, 4)
        return y + 28

    def _sub_card(self, draw, y, pairs: list[tuple[str, str]], *, density: str = "rich"):
        if not pairs:
            return y
        f_tag = _ft(FONT_BOLD, 32)
        f_body = _ft(FONT_REG, 38 if density == "rich" else 34)
        pad, gap, tag_w = 36, 24, 156
        tx = MARGIN + 34
        body_w = W - MARGIN - tx - tag_w - 34
        measured = []
        for tag, body in pairs:
            lines = self._wrap_lines(draw, body, f_body, body_w)
            line_h = self._line_h(draw, f_body)
            item_h = max(self._line_h(draw, f_tag), len(lines) * line_h + max(0, len(lines) - 1) * 8)
            measured.append((tag, lines, item_h))
        card_h = pad * 2 + sum(h for _, _, h in measured) + gap * (len(measured) - 1)
        draw.rounded_rectangle((MARGIN, y, W - MARGIN, y + card_h), 18, fill=SURFACE, outline=BORDER, width=2)
        inner_y = y + pad
        for tag, lines, item_h in measured:
            draw.text((tx, inner_y + 3), tag, font=f_tag, fill=ACCENT)
            self._draw_lines(draw, tx + tag_w, inner_y, lines, f_body, MUTED, 8)
            inner_y += item_h
            inner_y += gap
        return y + card_h

    def _canvas(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (W, H), BG)
        self._grid(img)
        return img, ImageDraw.Draw(img)

    def _cover(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 190, slide, accent_last=True)
        self._sub_card(draw, y + 18, _sub_pairs(slide), density=slide.layout.get("body_density", "rich"))
        fq = _ft(FONT_BOLD, 280)
        qw = draw.textlength("?", font=fq)
        draw.text(((W - qw) / 2, H - 520), "?", font=fq, fill=ACCENT_DIM)
        return img

    def _body(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide, accent_last=True)
        self._sub_card(draw, y + 12, _sub_pairs(slide), density=slide.layout.get("body_density", "rich"))
        return img

    def _hero(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide)
        y = self._sub_card(draw, y + 12, _sub_pairs(slide), density=slide.layout.get("body_density", "rich"))
        return img

    def _estimate(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide, accent_last=True)
        y = self._sub_card(draw, y + 8, _sub_pairs(slide), density=slide.layout.get("body_density", "rich"))
        y += 28
        if slide.highlight:
            draw.rounded_rectangle((MARGIN, y, W - MARGIN, y + 208), 18, fill=SURFACE, outline=ACCENT, width=2)
            fh, fs = _ft(FONT_BOLD, 72), _ft(FONT_REG, 34)
            tw = draw.textlength(slide.highlight, font=fh)
            draw.text(((W - tw) / 2, y + 34), slide.highlight, font=fh, fill=ACCENT)
            if slide.highlight_sub:
                tw2 = draw.textlength(slide.highlight_sub, font=fs)
                draw.text(((W - tw2) / 2, y + 124), slide.highlight_sub, font=fs, fill=MUTED)
            y += 228
        if slide.footnote:
            draw.text((MARGIN, y), slide.footnote, font=_ft(FONT_REG, 30), fill=ACCENT_DIM)
        return img

    def _roadmap(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide, accent_last=True)
        if slide.sub_items:
            y = self._sub_card(draw, y + 8, _sub_pairs(slide), density=slide.layout.get("body_density", "rich"))
        y += 32
        fp, fd = _ft(FONT_BOLD, 38), _ft(FONT_REG, 34)
        for i, (phase, desc) in enumerate(slide.phases):
            last = i == len(slide.phases) - 1
            desc_lines = self._wrap_lines(draw, desc, fd, W - MARGIN * 2 - 48)
            h = 52 + len(desc_lines) * self._line_h(draw, fd) + max(0, len(desc_lines) - 1) * 8 + 28
            draw.rounded_rectangle(
                (MARGIN, y, W - MARGIN, y + h), 12, fill=SURFACE, outline=ACCENT if last else BORDER, width=2
            )
            draw.text((MARGIN + 24, y + 14), phase, font=fp, fill=ACCENT)
            self._draw_lines(draw, MARGIN + 24, y + 58, desc_lines, fd, MUTED if not last else TEXT, 8)
            y += h + (28 if not last else 8)
        return img

    def _flow(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide)
        if slide.sub_items:
            y = self._sub_card(draw, y + 8, _sub_pairs(slide), density=slide.layout.get("body_density", "rich"))
        y += 36
        fs = _ft(FONT_BOLD, 44)
        for i, step in enumerate(slide.steps):
            last = i == len(slide.steps) - 1
            lines = self._wrap_lines(draw, step, fs, W - MARGIN * 2 - 56)
            line_h = self._line_h(draw, fs)
            h = max(92, 44 + len(lines) * line_h + max(0, len(lines) - 1) * 8)
            draw.rounded_rectangle(
                (MARGIN, y, W - MARGIN, y + h), 12,
                fill=ACCENT if last else SURFACE, outline=ACCENT if last else BORDER, width=2,
            )
            self._draw_lines(draw, MARGIN + 28, y + 22, lines, fs, BG if last else TEXT, 8)
            y += h + 14
        return img

    def _cta(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide, accent_last=True)
        self._sub_card(draw, y + 12, _sub_pairs(slide), density=slide.layout.get("body_density", "rich"))
        by = H - 260
        draw.rounded_rectangle((MARGIN, by, W - MARGIN, by + 96), 14, fill=ACCENT)
        fb = _ft(FONT_BOLD, 48)
        btn = "我支持 · 继续算账"
        tw = draw.textlength(btn, font=fb)
        draw.text(((W - tw) / 2, by + 24), btn, font=fb, fill=BG)
        return img
