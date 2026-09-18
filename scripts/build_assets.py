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
    for label, value in (("CORE", "AI / LLM SYSTEMS"),
                         ("EDGE", "LOCAL + CLOUD INFERENCE"),
                         ("SHIP", "FULL-STACK SERVICES")):
        draw_tracked(canvas, (PAD, y + 4), label, mono(24), rgb(pal["crimson"]), tracking=2.4)
        draw_tracked(canvas, (PAD + 112, y - 3), value, mono(28), rgb(pal["text"]), tracking=0.6)
        y += 50

    # ── bottom strip ───────────────────────────────────────────────────────
    by = HERO_H - 70
    hairline(d, PAD, by, PANEL_W - PAD, by, pal["line"], 200, 2)
    draw_tracked(canvas, (PAD, by + 22), "STATUS", mono(22), rgb(pal["muted"]), tracking=2.6)
    d.ellipse([PAD + 106, by + 30, PAD + 122, by + 46], fill=rgba(pal["ember"], 255))
    draw_tracked(canvas, (PAD + 136, by + 22), "BUILDING", mono(22), rgb(pal["ember"]), tracking=2.6)
    draw_tracked(canvas, (PANEL_W - PAD - 56, by + 22), "01", mono(22, bold=True),
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
    draw_tracked(canvas, (100, 21), "// SELECTED WORK", mono(22), rgb(pal["muted"]), tracking=3.0)

    cw = measure(d, chip, mono(22), 2.6)
    bx1, bx0 = CARD_W - 44, CARD_W - 44 - cw - 44
    d.rounded_rectangle([bx0, 11, bx1, 51], radius=6, outline=rgba(pal["crimson"], 200), width=2)
    draw_tracked(canvas, (bx0 + 22, 21), chip, mono(22), rgb(pal["crimson"]), tracking=2.6)

    corner_brackets(d, (20, 84, CARD_W - 20, CARD_H - 20), pal["crimson"], length=26, width=3, alpha=120)
    return canvas


def card_bullets(canvas: Image.Image, pal: dict, bullets: list[str], x: int, y: int, width: int) -> None:
    d = ImageDraw.Draw(canvas)
    font = mono(BULLET_SIZE)
    for line in bullets:
        marker_triangle(d, x + 6, y + 13, 7, pal["crimson"])
        cur = ""
        for word in line.split():
            probe = f"{cur} {word}".strip()
            if measure(d, probe, font) > width and cur:
                draw_tracked(canvas, (x + 30, y), cur, font, rgb(pal["text"]), tracking=0.3)
                y += 34
                cur = word
            else:
                cur = probe
        if cur:
            draw_tracked(canvas, (x + 30, y), cur, font, rgb(pal["text"]), tracking=0.3)
        y += 46


def card_header(canvas: Image.Image, pal: dict, title: str, subtitle: str) -> int:
    d = ImageDraw.Draw(canvas)
    font = fit_font(d, title, display, 840, start=78)
    draw_tracked_gradient(canvas, (44, 92), title, font, pal["text"], pal["crimson"], tracking=font.size * 0.03)
    y = 92 + int(font.size * 1.05)
    draw_tracked(canvas, (44, y), subtitle, mono(28), rgb(pal["rose"]), tracking=1.0)
    y += 48
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

    f = fit_font(d, label, lambda s: mono(s, bold=accent), wide, start=26, tracking=1.6, floor=15)
    if f.size < 22:
        print(f"    WARN diagram label shrunk to {f.size}px: {label!r}", file=sys.stderr)
    if sub:
        d.text((cx - measure(d, label, f, 1.6) / 2, y0 + 12), label, font=f, fill=ink)
        fs = fit_font(d, sub, mono, wide - 4, start=22, tracking=1.2, floor=20)
        if fs.size < 21:
            print(f"    WARN diagram sub shrunk to {fs.size}px: {sub!r}", file=sys.stderr)
        d.text((cx - measure(d, sub, fs, 1.2) / 2, y0 + 48), sub, font=fs, fill=rgb(pal["muted"]))
    else:
        d.text((cx - measure(d, label, f, 1.6) / 2, y0 + BOX_H / 2 - 16), label, font=f, fill=ink)


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
    for text, y, start, track in ((caption, 104, 22, 3.2), (tech, CARD_H - 74, 22, 0.6)):
        f = fit_font(d, text, mono, avail, start=start, tracking=track, floor=18)
        if f.size < 22:
            print(f"    WARN panel text shrunk to {f.size}px: {text!r}", file=sys.stderr)
        draw_tracked(canvas, (X0, y), text, f, rgb(pal["muted"]), tracking=track)
    return X0


def build_card_tessera(pal: dict) -> Image.Image:
    canvas = card_shell(pal, "01", "PRIVATE SOURCE")
    y = card_header(canvas, pal, "TESSERA", "Multi-service AI platform")
    card_bullets(canvas, pal, [
        "One provider interface over cloud APIs and local GGUF nodes",
        "Circuit breaker, capacity queues, quota reserve -> settle",
        "In-band metadata parsed out of the token stream",
        "Persona release gate with verbatim-leakage scanning",
        "Layered local-node transport attestation, 8 checkpoints",
    ], 44, y, BULLET_W)

    X0 = diagram_panel(canvas, pal, "REQUEST PATH",
                       "asyncio · httpx · FastAPI · SQLAlchemy · Postgres")
    d = ImageDraw.Draw(canvas)
    r1, r2, r3, r4 = (DIAGRAM_TOP + i * ROW_PITCH for i in range(4))
    b = lambda x, y, w: (X0 + x, y, X0 + x + w, y + BOX_H)  # noqa: E731

    diagram_box(d, pal, b(0, r1, 348), "CLIENTS", "webchat + personal api")
    diagram_box(d, pal, b(388, r1, 404), "GATEWAY", "admission · quota · budget", accent=True)
    arrow(d, pal, (X0 + 348, r1 + BOX_H / 2), (X0 + 388, r1 + BOX_H / 2))

    diagram_box(d, pal, b(388, r2, 404), "REGISTRY", "per-request snapshot")
    arrow(d, pal, (X0 + 590, r1 + BOX_H), (X0 + 590, r2))

    diagram_box(d, pal, b(40, r3, 330), "LOCAL NODE", "llama.cpp · gguf")
    diagram_box(d, pal, b(410, r3, 330), "CLOUD", "openai-compatible")
    arrow(d, pal, (X0 + 480, r2 + BOX_H), (X0 + 205, r3))
    arrow(d, pal, (X0 + 700, r2 + BOX_H), (X0 + 575, r3))
    arrow(d, pal, (X0 + 370, r3 + BOX_H / 2), (X0 + 410, r3 + BOX_H / 2))

    diagram_box(d, pal, b(40, r4, 330), "CIRCUIT BREAKER", "busy != failure")
    diagram_box(d, pal, b(410, r4, 330), "FALLBACK CHAIN", "ordered · telemetry")
    arrow(d, pal, (X0 + 205, r3 + BOX_H), (X0 + 205, r4))
    arrow(d, pal, (X0 + 575, r3 + BOX_H), (X0 + 575, r4))
    check_geometry("tessera")
    return canvas.convert("RGB")


def build_card_aurora(pal: dict) -> Image.Image:
    canvas = card_shell(pal, "02", "PRIVATE SOURCE")
    y = card_header(canvas, pal, "AURORA", "Circuit vision & topology engine")
    card_bullets(canvas, pal, [
        "Rule engine abstains rather than guessing at topology",
        "Union-find clustering plus Prim MST cycle construction",
        "Per-edge provenance ledger and full decision trace",
        "PCA axis gate for series / parallel, DSU safety check",
        "Browser YOLO: WebGPU to threaded WASM in a worker",
    ], 44, y, BULLET_W)

    X0 = diagram_panel(canvas, pal, "PHOTO -> STRUCTURED CIRCUIT",
                       "ultralytics · torch · onnxruntime · tensorrt · ort-web")
    d = ImageDraw.Draw(canvas)
    r1, r2, r3, r4 = (DIAGRAM_TOP + i * ROW_PITCH for i in range(4))
    b = lambda x, y, w: (X0 + x, y, X0 + x + w, y + BOX_H)  # noqa: E731

    diagram_box(d, pal, b(0, r1, 268), "PHOTO", "classroom photo")
    diagram_box(d, pal, b(308, r1, 442), "DETECTOR", "pt / onnx / tensorrt", accent=True)
    arrow(d, pal, (X0 + 268, r1 + BOX_H / 2), (X0 + 308, r1 + BOX_H / 2))

    diagram_box(d, pal, b(40, r2, 330), "RULE ENGINE", "deterministic")
    diagram_box(d, pal, b(410, r2, 330), "LLM LAYER", "cloud + local gguf")
    arrow(d, pal, (X0 + 420, r1 + BOX_H), (X0 + 205, r2))
    arrow(d, pal, (X0 + 590, r1 + BOX_H), (X0 + 575, r2))

    diagram_box(d, pal, b(160, r3, 428), "NODES + EDGES", "one json contract", accent=True)
    arrow(d, pal, (X0 + 205, r2 + BOX_H), (X0 + 300, r3))
    arrow(d, pal, (X0 + 575, r2 + BOX_H), (X0 + 448, r3))

    for bx, label, sub in ((40, "CANVAS", "editable"),
                           (292, "EXPORT", "png · json"),
                           (544, "EXPLAIN", "decision path")):
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


def build_portrait(source_root: Path) -> Image.Image:
    src = Image.open(source_root / PORTRAIT_SOURCE).convert("RGB")
    sw, sh = src.size
    crop_w = int(sw * 0.34)
    x0 = int(sw * 0.31)
    src = src.crop((x0, 0, x0 + crop_w, sh))

    ss = 4  # supersample the mask for clean edges
    mask = Image.new("L", (PORT_W * ss, PORT_H * ss), 0)
    w, h = PORT_W * ss, PORT_H * ss
    ImageDraw.Draw(mask).polygon([(w // 2, 0), (w, h // 2), (w // 2, h), (0, h // 2)], fill=255)
    mask = mask.resize((PORT_W, PORT_H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))

    out = Image.new("RGBA", (PORT_W, PORT_H), (0, 0, 0, 0))
    out.paste(src.resize((PORT_W, PORT_H), Image.LANCZOS), (0, 0), mask)

    rim = Image.new("RGBA", (PORT_W, PORT_H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    for inset, (r, g, b, a) in ((0, (225, 29, 92, 255)), (2, (255, 77, 126, 150)), (4, (139, 92, 246, 90))):
        rd.polygon([(PORT_W // 2, inset), (PORT_W - inset, PORT_H // 2),
                    (PORT_W // 2, PORT_H - inset), (inset, PORT_H // 2)],
                   outline=(r, g, b, a), width=2)
    return Image.alpha_composite(out, rim)


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
                    choices=["all", "hero", "cards", "divider", "portrait", "monogram"])
    args = ap.parse_args()

    root = args.source_root
    if root is None:
        ap.print_usage()
        print("ERROR: --source-root is required.  Point it at the read-only directory\n"
              "       that contains the hero artwork and the OC portrait.\n"
              "       Example: python build_assets.py --source-root C:/Users/you/稿",
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

    if args.only in ("all", "monogram"):
        print("monogram:")
        out = ASSETS / "icons" / "monogram.svg"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(MONOGRAM_SVG, encoding="utf-8")
        print(f"  {out.relative_to(REPO).as_posix():<44} {out.stat().st_size} B")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
