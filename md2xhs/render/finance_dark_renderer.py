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
BG, SURFACE, BORDER = "#0f1117", "#1a1d27", "#2a2f3d"
TEXT, MUTED = "#e8eaed", "#9aa3ad"
ACCENT, ACCENT_DIM, GRID = "#10b981", "#0d9668", "#1e2430"


def _ft(path: str, size: int):
    return ImageFont.truetype(path, size)


def _sub_pairs(slide: Slide) -> list[tuple[str, str]]:
    return [(s.tag, s.text) for s in slide.sub_items]


class FinanceDarkRenderer:
    def render_all(self, slides: list[Slide], output_dir: str) -> list[str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
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
        for line in lines:
            draw.text((x, y), line, font=fnt, fill=color)
            bb = draw.textbbox((0, 0), line, font=fnt)
            y += bb[3] - bb[1] + gap
        return y

    def _icon_label(self, draw, slide: Slide):
        draw.rounded_rectangle(
            (MARGIN, 88, MARGIN + 56, 88 + 56), 10, fill=SURFACE, outline=ACCENT_DIM, width=2
        )
        fi, fl = _ft(FONT_BOLD, 34), _ft(FONT_REG, 24)
        iw = draw.textlength(slide.icon, font=fi)
        draw.text((MARGIN + 28 - iw / 2, 98), slide.icon, font=fi, fill=ACCENT)
        draw.text((MARGIN + 72, 104), slide.label, font=fl, fill=MUTED)

    def _title(self, draw, y, slide: Slide, *, accent_last=False, large=True):
        for i, line in enumerate(slide.title):
            last = i == len(slide.title) - 1
            color = ACCENT if accent_last and last else TEXT
            sz = (92 if len(line) > 11 else 104) if large else (88 if len(line) > 11 else 98)
            y = self._wrap(draw, MARGIN, y, line, _ft(FONT_BOLD, sz), color, W - MARGIN * 2, 6)
        return y + 24

    def _sub_card(self, draw, y, pairs: list[tuple[str, str]]):
        f_tag, f_body = _ft(FONT_BOLD, 30), _ft(FONT_REG, 32)
        pad, gap, tag_w = 32, 22, 88
        card_h = pad * 2 + len(pairs) * (38 + gap) - gap + 16
        draw.rounded_rectangle((MARGIN, y, W - MARGIN, y + card_h), 16, fill=SURFACE, outline=BORDER, width=2)
        inner_y = y + pad
        tx = MARGIN + 28
        for tag, body in pairs:
            draw.text((tx, inner_y + 2), tag, font=f_tag, fill=ACCENT)
            inner_y = self._wrap(
                draw, tx + tag_w, inner_y, body, f_body, MUTED, W - MARGIN - tx - tag_w - 28, 10
            )
            inner_y += gap
        return y + card_h

    def _canvas(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGB", (W, H), BG)
        self._grid(img)
        return img, ImageDraw.Draw(img)

    def _cover(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide, accent_last=True)
        self._sub_card(draw, y + 12, _sub_pairs(slide))
        fq = _ft(FONT_BOLD, 300)
        qw = draw.textlength("?", font=fq)
        draw.text(((W - qw) / 2, H - 560), "?", font=fq, fill=ACCENT_DIM)
        return img

    def _body(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide, accent_last=True)
        self._sub_card(draw, y + 12, _sub_pairs(slide))
        return img

    def _hero(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide)
        y = self._sub_card(draw, y + 12, _sub_pairs(slide))
        return img

    def _estimate(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide, accent_last=True)
        y = self._sub_card(draw, y + 8, _sub_pairs(slide))
        y += 28
        if slide.highlight:
            draw.rounded_rectangle((MARGIN, y, W - MARGIN, y + 168), 16, fill=SURFACE, outline=ACCENT, width=2)
            fh, fs = _ft(FONT_BOLD, 44), _ft(FONT_REG, 28)
            tw = draw.textlength(slide.highlight, font=fh)
            draw.text(((W - tw) / 2, y + 28), slide.highlight, font=fh, fill=ACCENT)
            if slide.highlight_sub:
                tw2 = draw.textlength(slide.highlight_sub, font=fs)
                draw.text(((W - tw2) / 2, y + 88), slide.highlight_sub, font=fs, fill=MUTED)
            y += 188
        if slide.footnote:
            draw.text((MARGIN, y), slide.footnote, font=_ft(FONT_REG, 24), fill=ACCENT_DIM)
        return img

    def _roadmap(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide, accent_last=True)
        if slide.sub_items:
            y = self._sub_card(draw, y + 8, _sub_pairs(slide))
        y += 32
        fp, fd = _ft(FONT_BOLD, 32), _ft(FONT_REG, 30)
        for i, (phase, desc) in enumerate(slide.phases):
            last = i == len(slide.phases) - 1
            h = 96
            draw.rounded_rectangle(
                (MARGIN, y, W - MARGIN, y + h), 12, fill=SURFACE, outline=ACCENT if last else BORDER, width=2
            )
            draw.text((MARGIN + 24, y + 14), phase, font=fp, fill=ACCENT)
            self._wrap(draw, MARGIN + 24, y + 50, desc, fd, MUTED if not last else TEXT, W - MARGIN * 2 - 48, 8)
            y += h + (28 if not last else 8)
        return img

    def _flow(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide)
        if slide.sub_items:
            y = self._sub_card(draw, y + 8, _sub_pairs(slide))
        y += 36
        fs = _ft(FONT_BOLD, 38)
        for i, step in enumerate(slide.steps):
            last = i == len(slide.steps) - 1
            h = 84
            draw.rounded_rectangle(
                (MARGIN, y, W - MARGIN, y + h), 12,
                fill=ACCENT if last else SURFACE, outline=ACCENT if last else BORDER, width=2,
            )
            draw.text((MARGIN + 28, y + 22), step, font=fs, fill=BG if last else TEXT)
            y += h + 14
        return img

    def _cta(self, slide: Slide) -> Image.Image:
        img, draw = self._canvas()
        self._icon_label(draw, slide)
        y = self._title(draw, 200, slide, accent_last=True)
        self._sub_card(draw, y + 12, _sub_pairs(slide))
        by = H - 260
        draw.rounded_rectangle((MARGIN, by, W - MARGIN, by + 96), 14, fill=ACCENT)
        fb = _ft(FONT_BOLD, 48)
        btn = "我支持 · 反哺全民"
        tw = draw.textlength(btn, font=fb)
        draw.text(((W - tw) / 2, by + 24), btn, font=fb, fill=BG)
        return img
