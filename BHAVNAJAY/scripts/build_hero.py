#!/usr/bin/env python3
"""Build the animated hero banner (GIF) and its static fallback (PNG).

Inputs : assets/source/bhavna-portrait-cutout.png  (cut-out of the original photo;
         the face and body pixels are untouched — only the white background removed)
Outputs: assets/hero/hero.gif         – plays once: portrait wipe-reveal + subtle zoom, type fades in
         assets/hero/hero-static.png  – final frame, used for reduced-motion / fallback

Requires: Python 3.10+, Pillow, numpy, scipy, ffmpeg on PATH.
Run from the repository root:  python3 scripts/build_hero.py
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "scripts" / "fonts"
SRC = ROOT / "assets" / "source" / "bhavna-portrait-cutout.png"
OUT = ROOT / "assets" / "hero"

# ---------------------------------------------------------------- content
NAME_1 = "BHAVNA"
NAME_2 = "JAYAKUMAR"
TAGLINE = "Logic Runs from A to Z, Creativity Knows No Limits."
ABOUT = ("I'm a Computer Science Engineering student specialising in AI & Machine Learning. "
         "I build web applications, experiment with AI-powered solutions, and design "
         "intuitive, visually engaging interfaces.")
BUTTON = "VIEW PORTFOLIO"
URL_LABEL = "bhavna-j.vercel.app"
TOP_LEFT = "~/bhavna-jayakumar"
TOP_RIGHT = "[ ai · ml · web · design ]"
KICKER = "// hello, world — i'm"

# ---------------------------------------------------------------- look
W, H = 1280, 640
BG = np.array([11, 10, 15], np.float32)
VIOLET = (167, 139, 250)
PINK = (240, 166, 202)
TEXT = (244, 241, 248)
MUTED = (160, 154, 174)
FPS = 20
DURATION = 2.3  # seconds of motion; the GIF then rests on the last frame


def font(name: str, size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), int(round(size)))


F_SERIF = lambda s: font("InstrumentSerif-Regular.ttf", s)
F_SERIF_I = lambda s: font("InstrumentSerif-Italic.ttf", s)
F_MONO = lambda s: font("JetBrainsMono-Regular.ttf", s)
F_SANS = lambda s: font("Inter-Regular.otf", s)
F_SANS_SB = lambda s: font("Inter-SemiBold.otf", s)


def ease_out(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def phase(t: float, start: float, end: float) -> float:
    return ease_out((t - start) / (end - start))


def radial(cx, cy, r, strength):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
    return np.clip(1 - d, 0, 1) ** 2 * strength


# ---------------------------------------------------------------- background
def build_background() -> Image.Image:
    img = np.tile(BG, (H, W, 1))
    v = np.array(VIOLET, np.float32)
    p = np.array(PINK, np.float32)
    img += radial(1015, 300, 480, 0.20)[..., None] * (v - BG)
    img += radial(1230, 640, 330, 0.10)[..., None] * (p - BG)
    img += radial(40, 660, 420, 0.05)[..., None] * (p - BG)
    # vignette
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = ((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.75)) ** 2
    img *= (1 - np.clip(vig - 0.35, 0, 1) * 0.45)[..., None]
    # sparse dot grid on the text side (technical texture)
    grid = np.zeros((H, W), np.float32)
    grid[24::32, 24::32] = 1
    fade = np.clip(1 - x / 760, 0, 1) * np.clip((y - 90) / 200, 0, 1)
    img += (grid * fade * 14)[..., None]
    # film grain (fixed seed so every frame shares it -> small GIF deltas)
    rng = np.random.default_rng(7)
    img += rng.normal(0, 2.2, (H, W, 1)).astype(np.float32)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    d = ImageDraw.Draw(im)
    d.text((72, 36), TOP_LEFT, font=F_MONO(13), fill=MUTED + (255,))
    tw = d.textlength(TOP_RIGHT, font=F_MONO(13))
    d.text((W - 72 - tw, 36), TOP_RIGHT, font=F_MONO(13), fill=MUTED + (255,))
    rule = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(rule).line([(72, 68), (W - 72, 68)], fill=(255, 255, 255, 22), width=1)
    im.alpha_composite(rule)
    return im


def build_arch() -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0, x1, top = 850, 1190, 104
    r = (x1 - x0) // 2
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([x0, top, x1, H + r], radius=r, fill=255)
    grad = np.zeros((H, W, 4), np.float32)
    t = np.clip((np.arange(H) - top) / (H - top), 0, 1)[:, None]
    grad[..., 0] = VIOLET[0] * (1 - t) + PINK[0] * t
    grad[..., 1] = VIOLET[1] * (1 - t) + PINK[1] * t
    grad[..., 2] = VIOLET[2] * (1 - t) + PINK[2] * t
    grad[..., 3] = (0.16 * (1 - t) + 0.05 * t) * 255
    g = Image.fromarray(grad.astype(np.uint8), "RGBA")
    layer.paste(g, (0, 0), mask)
    outline = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(outline)
    od.rounded_rectangle([x0, top, x1, H + r], radius=r, outline=VIOLET + (90,), width=1)
    od.rounded_rectangle([x0 - 14, top - 14, x1 + 14, H + r], radius=r + 14, outline=(255, 255, 255, 16), width=1)
    layer.alpha_composite(outline)
    return layer


# ---------------------------------------------------------------- portrait
def build_portrait() -> tuple[Image.Image, Image.Image]:
    """Return (portrait RGBA, glow RGBA) at canvas scale, unpositioned."""
    cut = Image.open(SRC).convert("RGBA")
    a = np.asarray(cut)[..., 3]
    rows = np.where(a.max(axis=1) > 20)[0]
    top = int(rows[0])
    cut = cut.crop((0, max(top - 10, 0), cut.width, cut.height))
    target_h = H - 112
    s = target_h / cut.height
    cut = cut.resize((round(cut.width * s), target_h), Image.LANCZOS)
    # soften the photo's hard side/bottom crop edges so it melts into the dark
    arr = np.asarray(cut).astype(np.float32)
    h, w = arr.shape[:2]
    x = np.arange(w)[None, :]
    y = np.arange(h)[:, None]
    side = np.clip(np.minimum(x, w - 1 - x) / 70.0, 0, 1)
    side = np.where(y < h * 0.45, 1.0, side)  # only fade sides where arms meet the frame
    bottom = np.clip((h - 1 - y) / 70.0, 0, 1) * 0.55 + 0.45
    arr[..., 3] *= side * bottom
    portrait = Image.fromarray(arr.astype(np.uint8), "RGBA")
    # rim glow from the silhouette
    sil = portrait.getchannel("A").filter(ImageFilter.GaussianBlur(18))
    glow = Image.new("RGBA", portrait.size, VIOLET + (0,))
    glow.putalpha(sil.point(lambda v: int(v * 0.55)))
    return portrait, glow


# ---------------------------------------------------------------- text layers
def text_layer(draw_fn) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer), layer)
    return layer


def gradient_text(layer: Image.Image, xy, text, fnt):
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).text(xy, text, font=fnt, fill=255)
    bbox = mask.getbbox()
    g = np.zeros((H, W, 3), np.float32)
    x0, x1 = bbox[0], bbox[2]
    t = np.clip((np.arange(W) - x0) / max(x1 - x0, 1), 0, 1)[None, :]
    for c in range(3):
        g[..., c] = VIOLET[c] * (1 - t) + PINK[c] * t
    gi = Image.fromarray(g.astype(np.uint8), "RGB").convert("RGBA")
    layer.paste(gi, (0, 0), mask)


def wrap(text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    for wd in words:
        trial = (cur + " " + wd).strip()
        if d.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    return lines


def build_text_layers():
    X = 72
    y = 104
    layers = []  # (layer, start, end, slide_px)

    kicker = text_layer(lambda d, l: d.text((X, y), KICKER, font=F_MONO(15), fill=VIOLET + (255,)))
    layers.append((kicker, 0.35, 0.95, 10))

    name_size = 124
    y_n1 = y + 18
    n1 = text_layer(lambda d, l: d.text((X - 4, y_n1), NAME_1, font=F_SERIF(name_size), fill=TEXT + (255,)))
    layers.append((n1, 0.50, 1.30, 22))
    y_n2 = y_n1 + 104
    n2 = text_layer(lambda d, l: gradient_text(l, (X - 2, y_n2), NAME_2, F_SERIF_I(name_size)))
    layers.append((n2, 0.68, 1.48, 22))

    y_tag = y_n2 + 150
    tag = text_layer(lambda d, l: d.text((X, y_tag), TAGLINE, font=F_SERIF_I(29), fill=(232, 228, 240, 255)))
    layers.append((tag, 1.00, 1.70, 12))

    y_desc = y_tag + 50
    fd = F_SANS(16)
    lines = wrap(ABOUT, fd, 590)

    def draw_desc(d, l):
        for i, ln in enumerate(lines):
            d.text((X, y_desc + i * 26), ln, font=fd, fill=MUTED + (255,))
    desc = text_layer(draw_desc)
    layers.append((desc, 1.20, 1.90, 10))

    y_btn = y_desc + len(lines) * 26 + 26

    def draw_btn(d, l):
        f = F_SANS_SB(14)
        label = BUTTON
        tracking = 2.2
        tw = sum(d.textlength(ch, font=f) for ch in label) + tracking * (len(label) - 1)
        arrow_w = 22
        bw, bh = int(tw + arrow_w + 56), 50
        # soft glow under the button
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.rounded_rectangle([X + 6, y_btn + 10, X + bw - 6, y_btn + bh + 6], radius=25, fill=VIOLET + (120,))
        glow = glow.filter(ImageFilter.GaussianBlur(14))
        l.alpha_composite(glow)
        d.rounded_rectangle([X, y_btn, X + bw, y_btn + bh], radius=bh // 2, fill=TEXT + (255,))
        cx = X + 28
        ty = y_btn + bh / 2
        for ch in label:
            d.text((cx, ty), ch, font=f, fill=(14, 12, 20, 255), anchor="lm")
            cx += d.textlength(ch, font=f) + tracking
        d.text((cx + 8, ty), "↗", font=F_SANS_SB(16), fill=(120, 92, 220, 255), anchor="lm")
        d.text((X + bw + 22, ty), URL_LABEL, font=F_MONO(13), fill=MUTED + (255,), anchor="lm")
    btn = text_layer(draw_btn)
    layers.append((btn, 1.45, 2.15, 10))
    return layers


# ---------------------------------------------------------------- compose
def fade_layer(layer: Image.Image, alpha: float) -> Image.Image:
    if alpha >= 0.999:
        return layer
    a = layer.getchannel("A").point(lambda v: int(v * alpha))
    out = layer.copy()
    out.putalpha(a)
    return out


def frame(t, bg, arch, portrait, glow, layers) -> Image.Image:
    im = bg.copy()
    # arch
    im.alpha_composite(fade_layer(arch, phase(t, 0.0, 0.9)))
    # portrait: subtle zoom 1.06 -> 1.0, bottom-anchored, plus upward wipe reveal
    z = 1.05 - 0.05 * phase(t, 0.0, 1.6)
    pw, ph = portrait.size
    sw, sh = round(pw * z), round(ph * z)
    p = portrait.resize((sw, sh), Image.LANCZOS) if z != 1 else portrait
    g = glow.resize((sw, sh), Image.LANCZOS) if z != 1 else glow
    cx = 1020
    px, py = cx - sw // 2, H - sh
    reveal = phase(t, 0.0, 1.6)
    edge = H - reveal * (H + 80)  # wipe line moves from bottom to above the top
    yy = np.arange(sh)[:, None] + py
    wipe = np.clip((yy - edge) / 80.0, 0, 1)
    fade = phase(t, 0.0, 1.0)

    def masked(src):
        arr = np.asarray(src).astype(np.float32)
        arr[..., 3] *= wipe * fade
        return Image.fromarray(arr.astype(np.uint8), "RGBA")
    pl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pl.alpha_composite(masked(g), (px - 6, py), (max(0, -(px - 6)), 0))
    im.alpha_composite(pl)
    pl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    src = masked(p)
    if px < 0:
        src = src.crop((-px, 0, sw, sh))
        px = 0
    pl.alpha_composite(src, (px, py))
    im.alpha_composite(pl)
    # text
    for layer, s, e, slide in layers:
        k = phase(t, s, e)
        if k <= 0:
            continue
        lay = fade_layer(layer, k)
        dy = round((1 - k) * slide)
        if dy:
            shifted = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            shifted.alpha_composite(lay, (0, dy), (0, 0, W, H - dy))
            lay = shifted
        im.alpha_composite(lay)
    return im.convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bg = build_background()
    arch = build_arch()
    portrait, glow = build_portrait()
    layers = build_text_layers()
    n = int(DURATION * FPS)
    tmp = Path(tempfile.mkdtemp())
    for i in range(n + 1):
        t = i / FPS
        frame(t, bg, arch, portrait, glow, layers).save(tmp / f"f{i:03d}.png")
    final = frame(99, bg, arch, portrait, glow, layers)
    final.save(OUT / "hero-static.png", optimize=True)
    # GIF: shared palette, only changed rectangles re-encoded, plays once (-loop -1)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%03d.png"),
        "-vf", "split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];"
               "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle",
        "-loop", "-1", "-final_delay", "500", str(OUT / "hero.gif"),
    ], check=True)
    shutil.rmtree(tmp)
    # optional: shrink with gifsicle (≈40% smaller, quality stays close to the source)
    gifsicle = shutil.which("gifsicle")
    if gifsicle:
        subprocess.run([gifsicle, "-O3", "--lossy=30", "-b", str(OUT / "hero.gif")], check=True)
    for f in ("hero.gif", "hero-static.png"):
        print(f, round((OUT / f).stat().st_size / 1024), "KB")


if __name__ == "__main__":
    main()
