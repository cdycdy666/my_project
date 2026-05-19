from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


W, H = 1080, 1920
BG = (7, 9, 15)
PANEL = (16, 23, 34)
PAPER = (239, 226, 199)
AMBER = (231, 169, 61)
RUST = (199, 100, 59)
MUTED = (111, 143, 168)
FONT_UI = "/System/Library/Fonts/PingFang.ttc"
FONT_SERIF = "/System/Library/Fonts/Supplemental/Songti.ttc"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))


def tracked(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, size: int, fill, gap: int):
    f = font(FONT_UI, size)
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += int(draw.textlength(ch, font=f)) + gap


def rounded(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_background(img: Image.Image):
    pix = img.load()
    for y in range(H):
        ty = y / H
        left = blend((28, 19, 9), BG, min(1, ty * 1.25))
        right = blend((5, 12, 20), (5, 7, 11), ty)
        for x in range(W):
            pix[x, y] = blend(left, right, x / W)

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-240, -180, 520, 720), fill=(*AMBER, 92))
    gd.ellipse((660, 1040, 1340, 1840), fill=(*RUST, 42))
    gd.ellipse((580, 700, 1260, 1500), fill=(*MUTED, 30))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(92)))

    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, W, 72):
        d.line((x, 0, x, H), fill=(*PAPER, 3), width=1)
    for y in range(0, H, 72):
        d.line((0, y, W, y), fill=(*PAPER, 2), width=1)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, f: ImageFont.FreeTypeFont) -> list[str]:
    lines: list[str] = []
    current = ""
    for ch in text:
        trial = current + ch
        if draw.textlength(trial, font=f) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--episode", required=True)
    parser.add_argument("--kicker", required=True)
    parser.add_argument("--title-line", action="append", required=True)
    parser.add_argument("--badge", required=True)
    parser.add_argument("--big-line", action="append", required=True)
    parser.add_argument("--quote", required=True)
    parser.add_argument("--footer", required=True)
    args = parser.parse_args()

    img = Image.new("RGBA", (W, H), (*BG, 255))
    draw_background(img)
    d = ImageDraw.Draw(img, "RGBA")
    ui = lambda size: font(FONT_UI, size)
    serif = lambda size: font(FONT_SERIF, size)

    d.line((72, 138, 1008, 138), fill=(*PAPER, 80), width=1)
    d.line((72, 138, 330, 138), fill=(*AMBER, 180), width=3)
    tracked(d, 72, 82, "NAVAL ALMANACK", 23, (*PAPER, 198), 9)
    tracked(d, 600, 82, args.episode, 21, (*PAPER, 170), 7)

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    rounded(sd, (76, 250, 1004, 1460), 60, (0, 0, 0, 125))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(26)))

    rounded(d, (78, 250, 1002, 1460), 58, (*PANEL, 226), (*PAPER, 30), 2)
    rounded(d, (112, 288, 968, 1422), 40, (0, 0, 0, 0), (*AMBER, 86), 2)

    tracked(d, 136, 352, args.kicker, 28, (*AMBER, 238), 9)
    y = 420
    title_size = 108 if max(len(line) for line in args.title_line) >= 7 else 120
    for line in args.title_line:
        d.text((136, y), line, font=serif(title_size), fill=(*PAPER, 255))
        y += title_size + 20

    rounded(d, (136, y + 18, 740, y + 108), 45, (*AMBER, 238), (*AMBER, 255), 2)
    tracked(d, 174, y + 46, args.badge, 30, (44, 30, 13, 255), 3)

    y += 226
    for i, line in enumerate(args.big_line):
        d.text((136, y), line, font=serif(96), fill=(*(AMBER if i == 0 else PAPER), 255))
        y += 118

    d.line((136, 1190, 868, 1190), fill=(*PAPER, 46), width=1)
    quote_font = serif(32)
    qy = 1240
    for line in wrap_text(d, args.quote, 560, quote_font):
        d.text((136, qy), line, font=quote_font, fill=(*PAPER, 245))
        qy += 50

    d.arc((762, 1218, 920, 1376), 210, 520, fill=(*AMBER, 120), width=7)
    d.arc((790, 1248, 892, 1350), 220, 525, fill=(*AMBER, 100), width=5)
    d.line((802, 1320, 878, 1390), fill=(*RUST, 150), width=6)
    d.line((878, 1320, 802, 1390), fill=(*RUST, 150), width=6)

    rounded(d, (72, 1608, 1008, 1900), 34, (5, 7, 11, 218), (*PAPER, 24), 1)
    d.line((104, 1650, 976, 1650), fill=(*PAPER, 58), width=1)
    d.line((104, 1650, 438, 1650), fill=(*AMBER, 168), width=3)
    tracked(d, 104, 1692, "THE NAVAL PRINCIPLE SERIES", 21, (*PAPER, 148), 6)
    d.text((104, 1748), args.footer, font=serif(36), fill=(*PAPER, 224))
    rounded(d, (104, 1818, 976, 1882), 26, (0, 0, 0, 118), (*PAPER, 34), 1)
    d.text((144, 1831), "3 分钟内，讲清一个反直觉原则", font=serif(30), fill=(*PAPER, 240))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, quality=96)
    print(out)


if __name__ == "__main__":
    main()
