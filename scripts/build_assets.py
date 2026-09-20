#!/usr/bin/env python3
"""Deterministic asset builder for the MostimaBridges GitHub profile README.

Every visual in the profile is generated from this one script so the identity
stays consistent and reproducible: change PALETTE or the geometry constants
below, re-run, and every asset (hero, project cards, dividers, portrait,
monogram) is rebuilt from scratch.

Usage
-----
    python scripts/build_assets.py                 # build everything
    python scripts/build_assets.py --only hero     # build one target

Source material is READ-ONLY and lives outside this repository; nothing is ever
written back to it.

Outputs (all committed and self-hosted, so the README never depends on a
third-party image service):

    assets/hero/hero-{dark,light}.webp
    assets/projects/tessera-{dark,light}.webp
    assets/projects/aurora-{dark,light}.webp
    assets/ornaments/divider-{dark,light}.webp
    assets/misc/strand-portrait.webp
    assets/icons/monogram.svg

Requires: Pillow >= 10 with WebP and FreeType support.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "assets"

# Set to the read-only directory holding cafen.png and the OC portrait before
# running. This path is deliberately not committed with a value — your Windows
# username must not appear in the public commit log.
DEFAULT_SOURCE_ROOT: Path | None = None
BANNER_SOURCE = "cafen.png"        # hero artwork (preferred over 0227_.png)
PORTRAIT_SOURCE = "斯特兰德.png"    # OC illustration — same character as the avatar

FONT_DIR = Path(r"C:\Windows\Fonts")

# ─────────────────────────────────────────────────────────────────────────────
# PALETTE — sampled programmatically from the hero artwork
#   void #0D0812 · surface #372D43 · crimson #C3134D · rose #D8AAB8
# Budget: 1 primary (crimson) + 1 secondary (violet) + 2 accents (ember, rose).
# ─────────────────────────────────────────────────────────────────────────────

DARK = {
    "name": "dark",
    "void": "#08050E",
    "panel": "#0E0817",
    "surface": "#170E23",
    "line": "#39244E",
    "crimson": "#E11D5C",
    "ember": "#FF4D7E",
    "rose": "#F0A8C0",
    "violet": "#8B5CF6",
    "text": "#F3EDF9",
    "muted": "#9C87B3",
    "art_blend": 0.14,
    "art_lift": 1.0,
    "vignette_keep": 0.74,
    "scan_alpha": 12,
    "grid_alpha": 30,
}

LIGHT = {
    "name": "light",
    "void": "#FBF9FD",
    "panel": "#F4EFFA",
    "surface": "#FFFFFF",
    "line": "#DCCFEC",
    "crimson": "#C2185B",
    "ember": "#E11D5C",
    "rose": "#A8406A",
    "violet": "#6D3FD1",
    "text": "#1B1028",
    "muted": "#6E5C82",
    "art_blend": 0.06,
    "art_lift": 1.05,
    "vignette_keep": 0.90,
    "scan_alpha": 5,
    "grid_alpha": 40,
}


def rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgba(h: str, a: int) -> tuple[int, int, int, int]:
    r, g, b = rgb(h)
    return (r, g, b, a)


# ─────────────────────────────────────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────────────────────────────────────

_DISPLAY = ["bahnschrift.ttf", "segoeuib.ttf", "ARIALNB.TTF", "arialbd.ttf"]
_MONO = ["CascadiaMono.ttf", "consola.ttf", "CascadiaCode.ttf", "consolab.ttf", "arial.ttf"]
_MONO_BOLD = ["CascadiaCode.ttf", "consolab.ttf", "consola.ttf", "arialbd.ttf"]


def load_font(candidates: list[str], size: int, variation: str | None = None):
    for name in candidates:
        path = FONT_DIR / name
        if not path.exists():
            continue
        try:
            font = ImageFont.truetype(str(path), size)
        except OSError:
            continue
        if variation:
            try:
                font.set_variation_by_name(variation)
            except (OSError, ValueError, AttributeError):
                pass
        return font
    return ImageFont.load_default(size)


def display(size: int):
    """Condensed DIN-like display face used for the name and card titles."""
    return load_font(_DISPLAY, size, variation="Bold SemiCondensed")


def mono(size: int, bold: bool = False):
    return load_font(_MONO_BOLD if bold else _MONO, size)


# Chinese UI face. Noto Sans SC is a variable font, so the weight is selectable;
# it also carries Latin glyphs, which keeps mixed strings like "本地 + 云端"
# on one consistent face instead of falling back to a generic sans.
_CJK = ["NotoSansSC-VF.ttf", "msyhbd.ttc", "msyh.ttc", "simhei.ttf"]


def sans(size: int, weight: str = "Medium"):
    for name in _CJK:
        path = FONT_DIR / name
        if not path.exists():
            continue
        try:
            font = ImageFont.truetype(str(path), size)
        except OSError:
            continue
        if "-VF" in name:
            try:
                font.set_variation_by_name(weight)
            except (OSError, ValueError):
                pass
        return font
    return load_font(_MONO, size)


# ─────────────────────────────────────────────────────────────────────────────
# DRAWING PRIMITIVES
# ─────────────────────────────────────────────────────────────────────────────


def measure(draw: ImageDraw.ImageDraw, text: str, font, tracking: float = 0.0) -> float:
    if not text:
        return 0.0
    return sum(draw.textlength(ch, font=font) for ch in text) + tracking * (len(text) - 1)


def text_mask(size, xy, text: str, font, tracking: float = 0.0) -> Image.Image:
    """Render tracked text into an 8-bit mask (Pillow has no letter-spacing)."""
    mask = Image.new("L", size, 0)
    md = ImageDraw.Draw(mask)
    x, y = xy
    for ch in text:
        md.text((x, y), ch, font=font, fill=255)
        x += md.textlength(ch, font=font) + tracking
    return mask


def draw_tracked(base: Image.Image, xy, text: str, font, fill, tracking: float = 0.0) -> None:
    mask = text_mask(base.size, xy, text, font, tracking)
    base.paste(Image.new("RGB", base.size, fill), (0, 0), mask)


def draw_tracked_gradient(base: Image.Image, xy, text: str, font, c1: str, c2: str, tracking: float = 0.0) -> None:
    """Tracked text filled with a horizontal gradient — used for the name lockup."""
    mask = text_mask(base.size, xy, text, font, tracking)
    w, h = base.size
    a, b = rgb(c1), rgb(c2)
    strip = Image.new("RGB", (w, 1))
    strip.putdata([tuple(int(a[i] + (b[i] - a[i]) * (x / max(1, w - 1))) for i in range(3)) for x in range(w)])
    base.paste(strip.resize((w, h)), (0, 0), mask)


def linear_gradient(size, c1: str, c2: str, alpha_from: int = 255, alpha_to: int = 0,
                    vertical: bool = False) -> Image.Image:
    """RGBA gradient, used for seam blends and edge fades."""
    w, h = size
    n = h if vertical else w
    a, b = rgb(c1), rgb(c2)
    data = [
        (
            int(a[0] + (b[0] - a[0]) * (i / max(1, n - 1))),
            int(a[1] + (b[1] - a[1]) * (i / max(1, n - 1))),
            int(a[2] + (b[2] - a[2]) * (i / max(1, n - 1))),
            int(alpha_from + (alpha_to - alpha_from) * (i / max(1, n - 1))),
        )
        for i in range(n)
    ]
    strip = Image.new("RGBA", (1, n) if vertical else (n, 1))
    strip.putdata(data)
    return strip.resize((w, h), Image.BILINEAR)


def grid_overlay(size, color: str, alpha: int, step: int = 32) -> Image.Image:
    ov = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    w, h = size
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=rgba(color, alpha))
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=rgba(color, alpha))
    return ov


def scanlines(size, alpha: int = 10, step: int = 4) -> Image.Image:
    ov = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(0, size[1], step):
        d.line([(0, y), (size[0], y)], fill=(0, 0, 0, alpha))
    return ov


def vignette_mask(size, keep: float = 0.72, feather: float = 0.10) -> Image.Image:
    """L mask: 255 in the centre (keep the art), 0 at the edges (replace with void)."""
    w, h = size
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    px, py = int(w * (1 - keep) / 2), int(h * (1 - keep) / 2)
    d.rectangle([px, py, w - px, h - py], fill=255)
    return mask.filter(ImageFilter.GaussianBlur(max(w, h) * feather))


def hairline(d, x0, y0, x1, y1, color: str, alpha: int = 255, width: int = 1) -> None:
    d.line([(x0, y0), (x1, y1)], fill=rgba(color, alpha), width=width)


def corner_brackets(d, box, color: str, length: int = 18, width: int = 2, alpha: int = 190) -> None:
    x0, y0, x1, y1 = box
    for cx, cy, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(cx, cy), (cx + dx * length, cy)], fill=rgba(color, alpha), width=width)
        d.line([(cx, cy), (cx, cy + dy * length)], fill=rgba(color, alpha), width=width)


def diamond(d, cx, cy, r, color: str, width: int = 2, alpha: int = 255, fill=None) -> None:
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
              outline=rgba(color, alpha), fill=fill, width=width)


def marker_triangle(d, x, y, size: int, color: str, alpha: int = 255) -> None:
    d.polygon([(x, y - size), (x + size, y), (x, y + size)], fill=rgba(color, alpha))


def fit_font(draw, text: str, factory, max_width: float, start: int, tracking: float = 0.0, floor: int = 12):
    """Largest size at which `text` fits `max_width`."""
    size = start
    while size > floor:
        font = factory(size)
        if measure(draw, text, font, tracking) <= max_width:
            return font
        size -= 2
    return factory(floor)


# ─────────────────────────────────────────────────────────────────────────────
# HERO — 1692x656 title screen
#   left  620px : designed HUD panel (identity + focus areas)
#   right 1072px: cinematic crop of the banner artwork
#
# SCALE: the GitHub profile README article measures 846 CSS px wide at viewport
# widths >= 1280 (verified with a headless browser on real profiles). Every
# canvas here is therefore 1692 px = exactly 2x of 846, and all type is sized in
# display pixels then doubled, so it survives both the downscale and a retina
# screen without going soft.
# ─────────────────────────────────────────────────────────────────────────────

HERO_W, HERO_H = 1692, 656
PANEL_W = 620
ART_W = HERO_W - PANEL_W
PAD = 56
SEAM_FADE = 120


def build_art(pal: dict, source_root: Path) -> Image.Image:
    """Crop the banner to the art panel's aspect ratio with minimal loss."""
    src = Image.open(source_root / BANNER_SOURCE).convert("RGB")
    sw, sh = src.size
    crop_w = min(sw, int(round(sh * (ART_W / HERO_H))))
    art = src.crop((0, 0, crop_w, sh)).resize((ART_W, HERO_H), Image.LANCZOS)

    if pal["art_lift"] != 1.0:
        art = art.point(lambda v: min(255, int(v * pal["art_lift"])))
    art = Image.blend(art, Image.new("RGB", art.size, rgb(pal["void"])), pal["art_blend"])
    art = Image.composite(art, Image.new("RGB", art.size, rgb(pal["void"])),
                          vignette_mask(art.size, keep=pal["vignette_keep"]))
    return art


def build_hero(pal: dict, source_root: Path) -> Image.Image:
    canvas = Image.new("RGBA", (HERO_W, HERO_H), rgb(pal["panel"]) + (255,))
    canvas.paste(build_art(pal, source_root), (PANEL_W, 0))
    canvas.alpha_composite(scanlines((ART_W, HERO_H), alpha=pal["scan_alpha"]), (PANEL_W, 0))
    # left edge of the artwork fades into the panel so the seam reads as a light leak
    canvas.alpha_composite(
        linear_gradient((SEAM_FADE, HERO_H), pal["panel"], pal["panel"],
                        alpha_from=235 if pal["name"] == "dark" else 200, alpha_to=0),
        (PANEL_W, 0),
    )
    # bottom fade so the strip never fights the README background
    canvas.alpha_composite(
        linear_gradient((HERO_W, 86), pal["void"], pal["void"], alpha_from=0, alpha_to=190, vertical=True),
        (0, HERO_H - 86),
    )

    # ── HUD panel ──────────────────────────────────────────────────────────
    panel = Image.new("RGBA", (PANEL_W, HERO_H), rgb(pal["panel"]) + (255,))
    panel.alpha_composite(grid_overlay((PANEL_W, HERO_H), pal["line"], pal["grid_alpha"], 64))
    hairline(ImageDraw.Draw(panel), 0, 0, 0, HERO_H, pal["crimson"], 90, 5)
    canvas.alpha_composite(panel, (0, 0))

    # seam hairline, brightest at the vertical centre
    seam = Image.new("RGBA", (5, HERO_H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(seam)
    for y in range(HERO_H):
        t = 1.0 - abs(y / (HERO_H / 2) - 1.0)
        sd.line([(1, y), (4, y)], fill=rgba(pal["crimson"], int(40 + 200 * t ** 1.6)), width=3)
    canvas.alpha_composite(seam, (PANEL_W - 2, 0))

    d = ImageDraw.Draw(canvas)

    # ── monogram + profile label ───────────────────────────────────────────
    mr, mx, my = 19, PAD + 19, 66
    diamond(d, mx, my, mr, pal["crimson"], width=3)
    diamond(d, mx, my, mr - 8, pal["crimson"], width=2, alpha=140)
    draw_tracked(canvas, (PAD + 54, 52), "// GITHUB PROFILE", mono(24), rgb(pal["muted"]), tracking=3.0)

    # ── name lockup ────────────────────────────────────────────────────────
    avail = PANEL_W - 2 * PAD
    font = fit_font(d, "MOSTIMA", display, avail, start=124)
    pitch = int(font.size * 0.90)
    draw_tracked(canvas, (PAD, 126), "MOSTIMA", font, rgb(pal["text"]), tracking=font.size * 0.02)
    draw_tracked_gradient(canvas, (PAD, 126 + pitch), "BRIDGES", display(font.size),
                          pal["crimson"], pal["ember"], tracking=font.size * 0.02)

    # ── rule ───────────────────────────────────────────────────────────────
    ry = 404
    hairline(d, PAD, ry, PANEL_W - PAD, ry, pal["line"], 255, 2)
    hairline(d, PAD, ry, PAD + 130, ry, pal["crimson"], 255, 5)
    d.ellipse([PAD + 124, ry - 5, PAD + 136, ry + 7], fill=rgba(pal["ember"], 255))

    # ── focus readout: the who / what / which-direction payload ────────────
    y = 440
    for label, value in (("方向", "AI · LLM 系统"),
                         ("推理", "本地 + 云端"),
                         ("交付", "全栈服务")):
        draw_tracked(canvas, (PAD, y + 5), label, sans(24, "Bold"), rgb(pal["crimson"]), tracking=3.0)
        draw_tracked(canvas, (PAD + 96, y - 4), value, sans(31), rgb(pal["text"]), tracking=1.0)
        y += 50

    # ── bottom strip ───────────────────────────────────────────────────────
    by = HERO_H - 70
    hairline(d, PAD, by, PANEL_W - PAD, by, pal["line"], 200, 2)
    draw_tracked(canvas, (PAD, by + 23), "状态", sans(22, "Bold"), rgb(pal["muted"]), tracking=3.0)
    d.ellipse([PAD + 66, by + 31, PAD + 80, by + 45], fill=rgba(pal["ember"], 255))
    draw_tracked(canvas, (PAD + 94, by + 23), "持续更新", sans(22, "Bold"), rgb(pal["ember"]), tracking=3.0)
    draw_tracked(canvas, (PANEL_W - PAD - 40, by + 23), "01", mono(22, bold=True),
                 rgb(pal["muted"]), tracking=2.6)

    return canvas.convert("RGB")


# ─────────────────────────────────────────────────────────────────────────────
# PROJECT CARDS — 1600x500
#   left  column: title, category, verifiable highlights
#   right column: architecture sketch built from the real component names
# ─────────────────────────────────────────────────────────────────────────────

CARD_W, CARD_H = 1692, 680
DIAGRAM_X0 = 856        # left edge of the architecture panel
PANEL_LEFT = DIAGRAM_X0 - 30
BULLET_X = 44
# Bullet text starts at BULLET_X + 30 and must stop before PANEL_LEFT.
BULLET_W = PANEL_LEFT - (BULLET_X + 30) - 12
BULLET_SIZE = 26        # -> 13 display px
DIAGRAM_TOP, BOX_H, ROW_PITCH = 150, 84, 118


def card_shell(pal: dict, index: str, chip: str) -> Image.Image:
    canvas = Image.new("RGBA", (CARD_W, CARD_H), rgb(pal["panel"]) + (255,))
    canvas.alpha_composite(grid_overlay((CARD_W, CARD_H), pal["line"], pal["grid_alpha"] - 8, 64))
    d = ImageDraw.Draw(canvas)

    d.rectangle([0, 0, CARD_W, 62], fill=rgb(pal["surface"]) + (255,))
    hairline(d, 0, 62, CARD_W, 62, pal["crimson"], 170, 3)
    draw_tracked(canvas, (44, 16), index, mono(28, bold=True), rgb(pal["crimson"]), tracking=1.4)
    draw_tracked(canvas, (100, 20), "// 项目", sans(23, "Bold"), rgb(pal["muted"]), tracking=3.0)

    cw = measure(d, chip, sans(23), 2.6)
    bx1, bx0 = CARD_W - 44, CARD_W - 44 - cw - 44
    d.rounded_rectangle([bx0, 11, bx1, 51], radius=6, outline=rgba(pal["crimson"], 200), width=2)
    draw_tracked(canvas, (bx0 + 22, 20), chip, sans(23, "Bold"), rgb(pal["crimson"]), tracking=2.6)

    corner_brackets(d, (20, 84, CARD_W - 20, CARD_H - 20), pal["crimson"], length=26, width=3, alpha=120)
    return canvas


def card_bullets(canvas: Image.Image, pal: dict, bullets: list[str], x: int, y: int, width: int) -> None:
    d = ImageDraw.Draw(canvas)
    font = sans(BULLET_SIZE)
    for line in bullets:
        marker_triangle(d, x + 6, y + 13, 7, pal["crimson"])
        cur = ""
        for word in line.split():
            probe = f"{cur} {word}".strip()
            if measure(d, probe, font) > width and cur:
                draw_tracked(canvas, (x + 30, y), cur, font, rgb(pal["text"]), tracking=0.5)
                y += 40
                cur = word
            else:
                cur = probe
        if cur:
            draw_tracked(canvas, (x + 30, y), cur, font, rgb(pal["text"]), tracking=0.5)
        y += 52


def card_header(canvas: Image.Image, pal: dict, title: str, subtitle: str) -> int:
    d = ImageDraw.Draw(canvas)
    font = fit_font(d, title, display, 840, start=78)
    draw_tracked_gradient(canvas, (44, 92), title, font, pal["text"], pal["crimson"], tracking=font.size * 0.03)
    y = 92 + int(font.size * 1.05)
    draw_tracked(canvas, (44, y), subtitle, sans(30), rgb(pal["rose"]), tracking=1.4)
    y += 52
    hairline(d, 44, y, 820, y, pal["line"], 255, 2)
    hairline(d, 44, y, 116, y, pal["crimson"], 255, 5)
    return y + 26


_BOX_RECTS: list[tuple[tuple[int, int, int, int], str]] = []


def diagram_box(d, pal, box, label, sub=None, accent=False) -> None:
    """Draw a labelled node. Label and sub-label auto-shrink to stay inside."""
    x0, y0, x1, y1 = box
    _BOX_RECTS.append((box, label))
    d.rounded_rectangle(box, radius=8, fill=rgba(pal["surface"], 190),
                        outline=rgba(pal["crimson"] if accent else pal["line"], 235), width=3 if accent else 2)
    cx = (x0 + x1) / 2
    ink = rgb(pal["crimson"] if accent else pal["text"])
    wide = (x1 - x0) - 20

    f = fit_font(d, label, lambda s: sans(s, "Bold" if accent else "Medium"), wide,
                 start=27, tracking=1.4, floor=17)
    if f.size < 23:
        print(f"    WARN diagram label shrunk to {f.size}px: {label!r}", file=sys.stderr)
    if sub:
        d.text((cx - measure(d, label, f, 1.4) / 2, y0 + 13), label, font=f, fill=ink)
        fs = fit_font(d, sub, sans, wide - 4, start=23, tracking=1.0, floor=18)
        if fs.size < 21:
            print(f"    WARN diagram sub shrunk to {fs.size}px: {sub!r}", file=sys.stderr)
        d.text((cx - measure(d, sub, fs, 1.0) / 2, y0 + 48), sub, font=fs, fill=rgb(pal["muted"]))
    else:
        d.text((cx - measure(d, label, f, 1.4) / 2, y0 + BOX_H / 2 - 16), label, font=f, fill=ink)


def check_geometry(where: str) -> None:
    """Boxes must sit inside the diagram panel and must not overlap each other."""
    left, right, top, bottom = PANEL_LEFT, CARD_W - 44, 84, CARD_H - 44
    ok = True
    for (x0, y0, x1, y1), label in _BOX_RECTS:
        if x0 < left or x1 > right or y0 < top or y1 > bottom:
            print(f"    FAIL [{where}] {label!r} escapes the panel: {(x0, y0, x1, y1)}", file=sys.stderr)
            ok = False
    for i, (a, la) in enumerate(_BOX_RECTS):
        for b_, lb in _BOX_RECTS[i + 1:]:
            if a[0] < b_[2] and b_[0] < a[2] and a[1] < b_[3] and b_[1] < a[3]:
                print(f"    FAIL [{where}] {la!r} overlaps {lb!r}", file=sys.stderr)
                ok = False
    if ok:
        print(f"    geometry ok: {len(_BOX_RECTS)} boxes inside the panel, no overlaps")
    _BOX_RECTS.clear()


def arrow(d, pal, p0, p1, color=None) -> None:
    color = color or pal["muted"]
    d.line([p0, p1], fill=rgba(color, 200), width=3)
    (x0, y0), (x1, y1) = p0, p1
    if abs(x1 - x0) >= abs(y1 - y0):
        s = 1 if x1 > x0 else -1
        d.polygon([(x1, y1), (x1 - 14 * s, y1 - 8), (x1 - 14 * s, y1 + 8)], fill=rgba(color, 215))
    else:
        s = 1 if y1 > y0 else -1
        d.polygon([(x1, y1), (x1 - 8, y1 - 14 * s), (x1 + 8, y1 - 14 * s)], fill=rgba(color, 215))


def diagram_panel(canvas: Image.Image, pal: dict, caption: str, tech: str) -> int:
    X0 = DIAGRAM_X0
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([PANEL_LEFT, 84, CARD_W - 44, CARD_H - 44], radius=10,
                        outline=rgba(pal["line"], 150), width=2, fill=rgba(pal["void"], 90))
    avail = (CARD_W - 44) - X0 - 8
    for text, y, factory, start, track in ((caption, 104, lambda s: sans(s, "Bold"), 23, 3.0),
                                           (tech, CARD_H - 74, mono, 22, 0.6)):
        f = fit_font(d, text, factory, avail, start=start, tracking=track, floor=18)
        if f.size < 21:
            print(f"    WARN panel text shrunk to {f.size}px: {text!r}", file=sys.stderr)
        draw_tracked(canvas, (X0, y), text, f, rgb(pal["muted"]), tracking=track)
    return X0


def build_card_tessera(pal: dict) -> Image.Image:
    canvas = card_shell(pal, "01", "私有仓库")
    y = card_header(canvas, pal, "TESSERA", "多服务 AI 平台")
    card_bullets(canvas, pal, [
        "云端和本地 GGUF 走同一套 provider 接口",
        "熔断、排队、每日额度，按账本管",
        "流式输出里夹带的元数据，边收边剥离",
        "角色设定：编译 → 发布 → 泄漏检查",
        "运维面：迁移、保留期清理、运行时设置",
    ], 44, y, BULLET_W)

    X0 = diagram_panel(canvas, pal, "一次请求的路径",
                       "asyncio · httpx · FastAPI · SQLAlchemy · Postgres")
    d = ImageDraw.Draw(canvas)
    r1, r2, r3, r4 = (DIAGRAM_TOP + i * ROW_PITCH for i in range(4))
    b = lambda x, y, w: (X0 + x, y, X0 + x + w, y + BOX_H)  # noqa: E731

    diagram_box(d, pal, b(0, r1, 348), "客户端", "网页对话 · 个人 API")
    diagram_box(d, pal, b(388, r1, 404), "网关", "准入 · 配额 · 预算", accent=True)
    arrow(d, pal, (X0 + 348, r1 + BOX_H / 2), (X0 + 388, r1 + BOX_H / 2))

    diagram_box(d, pal, b(388, r2, 404), "注册表", "按请求取 provider 快照")
    arrow(d, pal, (X0 + 590, r1 + BOX_H), (X0 + 590, r2))

    diagram_box(d, pal, b(40, r3, 330), "本地节点", "llama.cpp · GGUF")
    diagram_box(d, pal, b(410, r3, 330), "云端", "OpenAI 兼容")
    arrow(d, pal, (X0 + 480, r2 + BOX_H), (X0 + 205, r3))
    arrow(d, pal, (X0 + 700, r2 + BOX_H), (X0 + 575, r3))
    arrow(d, pal, (X0 + 370, r3 + BOX_H / 2), (X0 + 410, r3 + BOX_H / 2))

    diagram_box(d, pal, b(40, r4, 330), "熔断器", "忙不算故障")
    diagram_box(d, pal, b(410, r4, 330), "回退链", "有序 · 带遥测")
    arrow(d, pal, (X0 + 205, r3 + BOX_H), (X0 + 205, r4))
    arrow(d, pal, (X0 + 575, r3 + BOX_H), (X0 + 575, r4))
    check_geometry("tessera")
    return canvas.convert("RGB")


def build_card_aurora(pal: dict) -> Image.Image:
    canvas = card_shell(pal, "02", "私有仓库")
    y = card_header(canvas, pal, "AURORA", "电路识别与拓扑还原")
    card_bullets(canvas, pal, [
        "规则引擎说不准就不猜，宁可少连一根",
        "导线用并查集聚类，环路用 Prim MST 收尾",
        "每条边都记着为什么存在，错了能回溯",
        "串并联看主轴方向，另外带一道短路校验",
        "浏览器里跑 YOLO，WebGPU 不行就退 WASM",
    ], 44, y, BULLET_W)

    X0 = diagram_panel(canvas, pal, "照片 → 结构化电路",
                       "ultralytics · torch · onnxruntime · tensorrt · ort-web")
    d = ImageDraw.Draw(canvas)
    r1, r2, r3, r4 = (DIAGRAM_TOP + i * ROW_PITCH for i in range(4))
    b = lambda x, y, w: (X0 + x, y, X0 + x + w, y + BOX_H)  # noqa: E731

    diagram_box(d, pal, b(0, r1, 268), "照片", "课堂实验")
    diagram_box(d, pal, b(308, r1, 442), "检测器", "PT / ONNX / TensorRT", accent=True)
    arrow(d, pal, (X0 + 268, r1 + BOX_H / 2), (X0 + 308, r1 + BOX_H / 2))

    diagram_box(d, pal, b(40, r2, 330), "规则引擎", "确定性 · 可解释")
    diagram_box(d, pal, b(410, r2, 330), "LLM 层", "云端 + 本地 GGUF")
    arrow(d, pal, (X0 + 420, r1 + BOX_H), (X0 + 205, r2))
    arrow(d, pal, (X0 + 590, r1 + BOX_H), (X0 + 575, r2))

    diagram_box(d, pal, b(160, r3, 428), "nodes + edges", "同一份 JSON 契约", accent=True)
    arrow(d, pal, (X0 + 205, r2 + BOX_H), (X0 + 300, r3))
    arrow(d, pal, (X0 + 575, r2 + BOX_H), (X0 + 448, r3))

    for bx, label, sub in ((40, "画布", "可编辑"),
                           (292, "导出", "PNG · JSON"),
                           (544, "解释", "决策路径")):
        diagram_box(d, pal, b(bx, r4, 236), label, sub)
    for cx in (X0 + 158, X0 + 410, X0 + 662):
        arrow(d, pal, (X0 + 374, r3 + BOX_H), (cx, r4))
    check_geometry("aurora")
    return canvas.convert("RGB")


# ─────────────────────────────────────────────────────────────────────────────
# DIVIDER — hairline rule with a centre diamond (transparent, works on any bg)
# ─────────────────────────────────────────────────────────────────────────────

DIV_W, DIV_H = 1692, 64


def build_divider(pal: dict) -> Image.Image:
    img = Image.new("RGBA", (DIV_W, DIV_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cy = DIV_H // 2
    for x in range(DIV_W):
        t = 1.0 - abs(x / (DIV_W / 2) - 1.0)
        d.line([(x, cy), (x, cy)], fill=rgba(pal["line"], 120))
        d.line([(x, cy), (x, cy)], fill=rgba(pal["crimson"], int(28 + 175 * t ** 2.2)))
    cx = DIV_W // 2
    d.rectangle([cx - 40, cy - 6, cx + 40, cy + 6], fill=(0, 0, 0, 0))
    diamond(d, cx, cy, 13, pal["crimson"], width=2)
    d.polygon([(cx, cy - 5), (cx + 5, cy), (cx, cy + 5), (cx - 5, cy)], fill=rgba(pal["ember"], 255))
    for sx in (cx - 170, cx + 170):
        diamond(d, sx, cy, 5, pal["crimson"], width=2, alpha=170)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# PORTRAIT — the OC, clipped into the avatar's diamond
# ─────────────────────────────────────────────────────────────────────────────

PORT_W, PORT_H = 340, 510
# Measured from the source art, not guessed: the head sits at x = 0.545 W, is
# about 0.63 W wide, and lands ~17.5% down a full-height crop.
PORT_HEAD_X = 0.545
# A sharp rhombus is only ~35% wide at that height, so it cannot hold a head
# that is 63% wide. The exponent walks the outline from diamond (1.0) toward
# ellipse (2.0); 1.30 keeps the diamond reading while clearing the head.
PORT_SHAPE_P = 1.30
# Nudges the artwork down into the wider part of the shape, which also brings
# the character's halo fully into frame.
PORT_OFFSET_Y = 30


def superellipse_mask(size, p, ss=3) -> Image.Image:
    """|u|^p + |v|^p <= 1. Build one quadrant, mirror it, then mirror the bottom half up."""
    w, h = size
    nw, nh = w * ss, h * ss
    cx, cy = nw // 2, nh // 2
    qw, qh = cx + 1, cy + 1

    q = Image.new("L", (qw, qh), 0)
    px = q.load()
    inv = 1.0 / p
    for y in range(qh):
        v = y / (nh / 2.0)
        vp = v ** p
        if vp >= 1.0:
            break
        xmax = min(int(((1.0 - vp) ** inv) * (nw / 2.0)), qw - 1)
        for x in range(xmax + 1):
            px[x, y] = 255

    full = Image.new("L", (nw, nh), 0)
    full.paste(q, (cx, cy))
    full.paste(q.transpose(Image.FLIP_LEFT_RIGHT), (cx - qw + 1, cy))
    bottom = full.crop((0, cy, nw, nh))
    full.paste(bottom.transpose(Image.FLIP_TOP_BOTTOM), (0, 0))
    return full.resize(size, Image.LANCZOS)


def build_portrait(source_root: Path) -> Image.Image:
    src = Image.open(source_root / PORTRAIT_SOURCE).convert("RGB")
    sw, sh = src.size

    # full-height crop whose horizontal centre lands on the head
    crop_w = min(int(sh * PORT_W / PORT_H), sw)
    x0 = max(0, min(sw - crop_w, int(PORT_HEAD_X * sw - crop_w / 2)))
    art = src.crop((x0, 0, x0 + crop_w, sh)).resize((PORT_W, PORT_H), Image.LANCZOS)
    if PORT_OFFSET_Y:
        shifted = Image.new("RGB", (PORT_W, PORT_H), (0, 0, 0))
        shifted.paste(art, (0, PORT_OFFSET_Y))
        art = shifted

    out = Image.new("RGBA", (PORT_W, PORT_H), (0, 0, 0, 0))
    out.paste(art, (0, 0), superellipse_mask((PORT_W, PORT_H), PORT_SHAPE_P))

    # crimson edge, traced along the same superellipse so the two agree
    rim = Image.new("RGBA", (PORT_W, PORT_H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    for inset, col in ((0, (225, 29, 92, 255)), (2, (255, 77, 126, 140)), (4, (139, 92, 246, 80))):
        pts = []
        for i in range(241):
            t = i / 240 * 2 * math.pi
            ca, sa = math.cos(t), math.sin(t)
            rad = (abs(ca) ** PORT_SHAPE_P + abs(sa) ** PORT_SHAPE_P) ** (-1.0 / PORT_SHAPE_P)
            pts.append((PORT_W / 2 + ca * rad * (PORT_W / 2 - inset),
                        PORT_H / 2 + sa * rad * (PORT_H / 2 - inset)))
        rd.line(pts, fill=col, width=2)
    return Image.alpha_composite(out, rim)


# ─────────────────────────────────────────────────────────────────────────────
# AI TOOLCHAIN ROW — the third row of // 常用技术
#
# skillicons has no id for any of these (every candidate id returns its 256-byte
# placeholder), so the row is assembled here on skillicons' own geometry: one
# 256x256 rounded tile (rx=60) per icon, 44px gutters, rendered 48px tall.
# Tiles follow the same rule skillicons uses — a brand-coloured tile keeps its
# colour in both themes, otherwise the tile tracks the theme (#242938 / #F4F2ED)
# and the mark inverts with it.
#
# Mark provenance (paths copied verbatim, fills re-applied per theme):
#   GitHub Copilot  simple-icons (CC0)                        24x24
#   Codex           simple-icons v15 (CC0) — the OpenAI mark  24x24
#                   (OpenAI's entry was dropped from newer releases)
#   DSH             deepseek-harness  apps/web/public/favicon.svg   50x50
#   AstrBot         AstrBot  dashboard/public/favicon.svg          512x512
# ─────────────────────────────────────────────────────────────────────────────

AI_TILE, AI_TILE_RX, AI_GUTTER = 256, 60, 44
AI_MARK_BOX = 158          # the mark is drawn inside a 158px box, centred in the tile
AI_RENDER_H = 48           # rendered tile height, matching the skillicons rows

AI_TOOLS = [
    {
        "name": "GitHub Copilot",
        "tile": ("#242938", "#F4F2ED"),
        "mark": ("#FFFFFF", "#161614"),
        "viewBox": "0 0 24 24",
        "paths": (
            "M23.922 16.997C23.061 18.492 18.063 22.02 12 22.02 5.937 22.02.939 18.492.078 16.997A.641.641 0 0 1 0 16.741v-2.869a.883.883 0 0 1 .053-.22c.372-.935 1.347-2.292 2.605-2.656.167-.429.414-1.055.644-1.517a10.098 10.098 0 0 1-.052-1.086c0-1.331.282-2.499 1.132-3.368.397-.406.89-.717 1.474-.952C7.255 2.937 9.248 1.98 11.978 1.98c2.731 0 4.767.957 6.166 2.093.584.235 1.077.546 1.474.952.85.869 1.132 2.037 1.132 3.368 0 .368-.014.733-.052 1.086.23.462.477 1.088.644 1.517 1.258.364 2.233 1.721 2.605 2.656a.841.841 0 0 1 .053.22v2.869a.641.641 0 0 1-.078.256Zm-11.75-5.992h-.344a4.359 4.359 0 0 1-.355.508c-.77.947-1.918 1.492-3.508 1.492-1.725 0-2.989-.359-3.782-1.259a2.137 2.137 0 0 1-.085-.104L4 11.746v6.585c1.435.779 4.514 2.179 8 2.179 3.486 0 6.565-1.4 8-2.179v-6.585l-.098-.104s-.033.045-.085.104c-.793.9-2.057 1.259-3.782 1.259-1.59 0-2.738-.545-3.508-1.492a4.359 4.359 0 0 1-.355-.508Zm2.328 3.25c.549 0 1 .451 1 1v2c0 .549-.451 1-1 1-.549 0-1-.451-1-1v-2c0-.549.451-1 1-1Zm-5 0c.549 0 1 .451 1 1v2c0 .549-.451 1-1 1-.549 0-1-.451-1-1v-2c0-.549.451-1 1-1Zm3.313-6.185c.136 1.057.403 1.913.878 2.497.442.544 1.134.938 2.344.938 1.573 0 2.292-.337 2.657-.751.384-.435.558-1.15.558-2.361 0-1.14-.243-1.847-.705-2.319-.477-.488-1.319-.862-2.824-1.025-1.487-.161-2.192.138-2.533.529-.269.307-.437.808-.438 1.578v.021c0 .265.021.562.063.893Zm-1.626 0c.042-.331.063-.628.063-.894v-.02c-.001-.77-.169-1.271-.438-1.578-.341-.391-1.046-.69-2.533-.529-1.505.163-2.347.537-2.824 1.025-.462.472-.705 1.179-.705 2.319 0 1.211.175 1.926.558 2.361.365.414 1.084.751 2.657.751 1.21 0 1.902-.394 2.344-.938.475-.584.742-1.44.878-2.497Z",
        ),
    },
    {
        "name": "Codex",
        "tile": ("#242938", "#F4F2ED"),
        "mark": ("#FFFFFF", "#161614"),
        "viewBox": "0 0 24 24",
        "paths": (
            "M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z",
        ),
    },
    {
        "name": "DSH",
        "tile": ("#4D6BFE", "#4D6BFE"),
        "mark": ("#FFFFFF", "#FFFFFF"),
        "viewBox": "0 0 50 50",
        "paths": (
            "M48.8354 10.0479C48.3232 9.79199 48.1025 10.2798 47.8032 10.5278C47.7007 10.6079 47.6143 10.7119 47.5273 10.8076C46.7793 11.624 45.9048 12.1597 44.7622 12.0957C43.0923 12 41.666 12.5356 40.4058 13.8398C40.1377 12.2319 39.2476 11.272 37.8926 10.6558C37.1836 10.3359 36.4668 10.0156 35.9702 9.31982C35.6235 8.82373 35.5293 8.27197 35.356 7.72754C35.2456 7.3999 35.1353 7.06396 34.7651 7.00781C34.3633 6.94385 34.2056 7.2876 34.0479 7.57568C33.418 8.75195 33.1733 10.0479 33.1973 11.3599C33.2524 14.312 34.4736 16.6641 36.8999 18.3359C37.1758 18.5278 37.2466 18.7197 37.1597 19C36.9946 19.5757 36.7974 20.1357 36.624 20.7119C36.5137 21.0801 36.3486 21.1597 35.9624 21C34.6309 20.4321 33.481 19.5918 32.4644 18.5757C30.7393 16.8721 29.1792 14.9917 27.2334 13.52C26.7764 13.1758 26.3193 12.856 25.8467 12.5518C23.8618 10.584 26.1069 8.96777 26.627 8.77588C27.1704 8.57568 26.8159 7.8877 25.0591 7.896C23.3022 7.90381 21.6953 8.50391 19.647 9.30371C19.3477 9.42383 19.0322 9.51172 18.7095 9.58398C16.8501 9.22363 14.9199 9.14355 12.9033 9.37598C9.10596 9.80762 6.07275 11.6396 3.84326 14.7681C1.16455 18.5278 0.53418 22.7998 1.30664 27.2559C2.11768 31.9521 4.46582 35.8398 8.07373 38.8799C11.8159 42.0322 16.1255 43.5762 21.041 43.2803C24.0269 43.104 27.3516 42.6963 31.1016 39.4561C32.0469 39.936 33.0396 40.1279 34.686 40.272C35.9546 40.3921 37.1758 40.208 38.1211 40.0078C39.6021 39.688 39.4995 38.2881 38.9639 38.0322C34.623 35.9678 35.5762 36.8081 34.71 36.1279C36.9155 33.4639 40.2402 30.6958 41.54 21.728C41.6426 21.0161 41.5557 20.5679 41.54 19.9917C41.5322 19.6396 41.6108 19.5039 42.0049 19.4639C43.0923 19.3359 44.1479 19.0317 45.1167 18.4878C47.9292 16.9199 49.064 14.3438 49.3315 11.2559C49.3711 10.7837 49.3237 10.2959 48.8354 10.0479ZM24.3262 37.8398C20.1196 34.4639 18.0791 33.3521 17.2358 33.3999C16.4482 33.4482 16.5898 34.3682 16.7632 34.9678C16.9443 35.5601 17.1812 35.9683 17.5117 36.4878C17.7402 36.832 17.8979 37.3442 17.2832 37.728C15.9282 38.584 13.5728 37.4399 13.4624 37.3838C10.7207 35.7358 8.42822 33.5601 6.81348 30.584C5.25342 27.7197 4.34766 24.6479 4.19775 21.3677C4.1582 20.5757 4.38672 20.2959 5.15869 20.1519C6.17529 19.96 7.22314 19.9199 8.23926 20.0718C12.5327 20.7119 16.1885 22.6719 19.2529 25.7759C21.002 27.5439 22.3252 29.6558 23.6885 31.7202C25.1377 33.9121 26.6978 36 28.6831 37.7119C29.3843 38.312 29.9434 38.7681 30.479 39.104C28.8643 39.2881 26.1699 39.3281 24.3262 37.8398ZM26.3433 24.6001C26.3433 24.248 26.6191 23.9678 26.9658 23.9678C27.0444 23.9678 27.1152 23.9839 27.1782 24.0078C27.2651 24.04 27.3438 24.0879 27.4067 24.1602C27.5171 24.272 27.5801 24.4321 27.5801 24.6001C27.5801 24.9521 27.3042 25.2319 26.9575 25.2319C26.6108 25.2319 26.3433 24.9521 26.3433 24.6001ZM32.6064 27.8799C32.2046 28.0479 31.8027 28.1919 31.4165 28.208C30.8179 28.2397 30.1641 27.9922 29.8096 27.688C29.2583 27.2158 28.8643 26.9521 28.6987 26.1279C28.6279 25.7759 28.6675 25.2319 28.7305 24.9199C28.8721 24.248 28.7144 23.8159 28.2495 23.4238C27.8716 23.104 27.3911 23.0161 26.8633 23.0161C26.666 23.0161 26.4849 22.9277 26.3511 22.856C26.1304 22.7441 25.9492 22.4639 26.1226 22.1201C26.1777 22.0078 26.4458 21.7358 26.5088 21.688C27.2256 21.272 28.0527 21.4077 28.8169 21.7197C29.5259 22.0161 30.0615 22.5601 30.834 23.3281C31.6216 24.2559 31.7632 24.5117 32.2124 25.208C32.5669 25.752 32.8901 26.312 33.1104 26.9521C33.2446 27.3521 33.0713 27.6802 32.6064 27.8799Z",
        ),
    },
    {
        "name": "AstrBot",
        # The mark is AstrBot's own blue, so it stays that blue in both themes;
        # the tile is neutral, so it tracks the theme like Copilot's and Codex's.
        "tile": ("#242938", "#F4F2ED"),
        "mark": ("#2f86bd", "#2f86bd"),
        "viewBox": "0 0 512 512",
        "paths": (
            "m246.3 328.1-17.8 41.2c-6.4 14.8-26.9 14.8-33.3 0l-17.8-41.2c-14.9-34.2-41.8-61.4-75.3-76.3l-48.8-21.6c-14.7-6.5-14.7-27.9 0-34.4l47.2-21c34.4-15.3 61.7-43.5 76.4-78.8l18-43.7c6.3-15.2 27.3-15.2 33.6 0l18 43.7c14.7 35.3 42 63.6 76.4 78.8l47.2 21c14.7 6.5 14.7 27.9 0 34.4l-48.8 21.6c-33.5 14.8-60.4 42.1-75.3 76.2z",
            "m402.2 449.3-5.3 12.2c-3.5 7.9-14.4 7.9-17.9 0l-5.3-12.2c-8.4-19.3-23.6-34.6-42.4-43l-15.4-6.9c-7.9-3.5-7.9-14.9 0-18.4l14.5-6.5c19.4-8.6 34.8-24.5 43.1-44.5l5.4-13.1c3.4-8.1 14.6-8.1 18 0l5.4 13.1c8.3 19.9 23.7 35.8 43.1 44.5l14.5 6.5c7.9 3.5 7.9 14.9 0 18.4l-15.4 6.9c-19 8.3-34.1 23.7-42.5 43z",
        ),
    },
]


def build_ai_tools_svg(theme: str = "dark") -> str:
    """Assemble the four tiles into one row, sized like a skillicons row."""
    ti = 0 if theme == "dark" else 1
    n = len(AI_TOOLS)
    row_w = n * AI_TILE + (n - 1) * AI_GUTTER
    label = "、".join(t["name"] for t in AI_TOOLS)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {row_w} {AI_TILE}" '
        f'width="{row_w * AI_RENDER_H / AI_TILE:.2f}" height="{AI_RENDER_H}" '
        f'role="img" aria-label="{label}">'
    ]
    for i, tool in enumerate(AI_TOOLS):
        x = i * (AI_TILE + AI_GUTTER)
        vw = float(tool["viewBox"].split()[2])
        k = AI_MARK_BOX / vw
        off = (AI_TILE - AI_MARK_BOX) / 2
        out.append(f'<g transform="translate({x} 0)">')
        out.append(f'<rect width="{AI_TILE}" height="{AI_TILE}" '
        f'rx="{AI_TILE_RX}" fill="{tool["tile"][ti]}"/>')
        out.append(f'<g transform="translate({off:g} {off:g}) scale({k:.6f})" '
        f'fill="{tool["mark"][ti]}">')
        for d in tool["paths"]:
            out.append(f'<path d="{d}"/>')
        out.append("</g></g>")
    out.append("</svg>")
    return "".join(out)

# ─────────────────────────────────────────────────────────────────────────────
# MONOGRAM (SVG — pure geometry, crisp at any size, echoes the avatar mark)
# ─────────────────────────────────────────────────────────────────────────────

MONOGRAM_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64"
     role="img" aria-label="A crimson and violet diamond monogram">
  <defs>
    <linearGradient id="mb" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FF4D7E"/>
      <stop offset="1" stop-color="#8B5CF6"/>
    </linearGradient>
  </defs>
  <path d="M32 3 L61 32 L32 61 L3 32 Z" fill="none" stroke="url(#mb)" stroke-width="4"/>
  <path d="M32 15 L49 32 L32 49 L15 32 Z" fill="none" stroke="#E11D5C" stroke-width="2" opacity="0.75"/>
  <path d="M32 25 L39 32 L32 39 L25 32 Z" fill="#FF4D7E"/>
</svg>
"""


# ─────────────────────────────────────────────────────────────────────────────
# DRIVER
# ─────────────────────────────────────────────────────────────────────────────


def save(img: Image.Image, path: Path, lossless: bool = False, budget_kb: float = 420) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="WEBP", quality=92, method=6, lossless=lossless)
    if not lossless and path.stat().st_size / 1024 > budget_kb:
        img.save(path, format="WEBP", quality=82, method=6)
    size_kb = path.stat().st_size / 1024
    flag = "  <-- OVER BUDGET" if size_kb > budget_kb else ""
    print(f"  {path.relative_to(REPO).as_posix():<44} {img.size[0]}x{img.size[1]}  {size_kb:7.1f} KB{flag}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build MostimaBridges profile assets.")
    ap.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT,
                    help="read-only directory holding the source artwork (required)")
    ap.add_argument("--only", default="all",
                    choices=["all", "hero", "cards", "divider", "portrait", "icons", "monogram"])
    args = ap.parse_args()

    root = args.source_root
    if root is None:
        ap.print_usage()
        print("ERROR: --source-root is required.  Point it at the read-only directory\n"
              "       holding the hero artwork and the OC portrait, e.g.\n"
              "       python scripts/build_assets.py --source-root /path/to/artwork",
              file=sys.stderr)
        return 1

    if args.only in ("all", "hero", "cards") and not (root / BANNER_SOURCE).exists():
        print(f"ERROR: source artwork not found: {root / BANNER_SOURCE}", file=sys.stderr)
        return 1

    print(f"source: {root}")

    if args.only in ("all", "hero"):
        print("hero:")
        for pal in (DARK, LIGHT):
            save(build_hero(pal, root), ASSETS / "hero" / f"hero-{pal['name']}.webp")

    if args.only in ("all", "cards"):
        print("project cards:")
        for pal in (DARK, LIGHT):
            save(build_card_tessera(pal), ASSETS / "projects" / f"tessera-{pal['name']}.webp")
            save(build_card_aurora(pal), ASSETS / "projects" / f"aurora-{pal['name']}.webp")

    if args.only in ("all", "divider"):
        print("dividers:")
        for pal in (DARK, LIGHT):
            save(build_divider(pal), ASSETS / "ornaments" / f"divider-{pal['name']}.webp", lossless=True)

    if args.only in ("all", "portrait"):
        print("portrait:")
        if (root / PORTRAIT_SOURCE).exists():
            save(build_portrait(root), ASSETS / "misc" / "strand-portrait.webp")
        else:
            print(f"  skipped (missing {PORTRAIT_SOURCE})", file=sys.stderr)

    if args.only in ("all", "icons", "monogram"):
        print("icons:")
        for name, svg in (
            ("monogram.svg", MONOGRAM_SVG),
            ("ai-tools-dark.svg", build_ai_tools_svg("dark")),
            ("ai-tools-light.svg", build_ai_tools_svg("light")),
        ):
            out = ASSETS / "icons" / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(svg, encoding="utf-8")
            print(f"  {out.relative_to(REPO).as_posix():<44} {out.stat().st_size} B")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
