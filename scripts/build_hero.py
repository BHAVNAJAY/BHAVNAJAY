#!/usr/bin/env python3
"""Build the animated hero banner (looping GIF) and its static fallback (PNG).

Inputs : assets/source/model-frames/m000.png ...  sway turntable of assets/hero/womanfinal.glb,
         rendered by scripts/model (see scripts/model/README.md)
Outputs: assets/hero/hero.gif         - loops: model sways, portfolio bubble pulses
         assets/hero/hero-static.png  - first frame, used for reduced-motion / fallback

Requires: Python 3.10+, Pillow, numpy.
Run from the repository root:  python3 scripts/build_hero.py
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "scripts" / "fonts"
MODEL_DIR = ROOT / "assets" / "source" / "model-frames"
OUT = ROOT / "assets" / "hero"

# ---------------------------------------------------------------- content
NAME_1 = "BHAVNA"
NAME_2 = "JAYAKUMAR"
BUTTON = "VIEW PORTFOLIO"
BTN_TRACKING = 2.4
BTN_X, BTN_Y = 72, 430
MODEL_X, MODEL_Y = 830, 80  # top-left of the 380x560 model render, centred in the arch
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
FPS = 16


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


def button_geometry():
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    f = F_SANS_SB(16)
    tw = sum(d.textlength(ch, font=f) for ch in BUTTON) + BTN_TRACKING * (len(BUTTON) - 1)
    return int(tw + 22 + 68), 58


def build_static_text():
    """Everything that never moves: kicker + name. The portfolio button is drawn per frame."""
    X, y = 72, 104
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((X, y), KICKER, font=F_MONO(15), fill=VIOLET + (255,))
    name_size = 124
    y_n1 = y + 18
    d.text((X - 4, y_n1), NAME_1, font=F_SERIF(name_size), fill=TEXT + (255,))
    gradient_text(layer, (X - 2, y_n1 + 104), NAME_2, F_SERIF_I(name_size))
    return layer


def draw_button(k: float):
    """Animated portfolio bubble for loop position k in [0, 1). Returns (RGBA tile, (x, y))."""
    bw, bh = button_geometry()
    pad = 70
    ox, oy = BTN_X - pad, BTN_Y - pad
    tw_, th_ = bw + 2 * pad + 230, bh + 2 * pad
    tile = Image.new("RGBA", (tw_, th_), (0, 0, 0, 0))
    bx, by = pad, pad
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * k)
    # breathing glow
    glow = Image.new("RGBA", tile.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle([bx + 6, by + 10, bx + bw - 6, by + bh + 6], radius=bh // 2,
                                            fill=VIOLET + (int(90 + 90 * pulse),))
    tile.alpha_composite(glow.filter(ImageFilter.GaussianBlur(16)))
    # expanding ripple ring
    e = 30 * k
    ring = Image.new("RGBA", tile.size, (0, 0, 0, 0))
    ImageDraw.Draw(ring).rounded_rectangle([bx - e, by - e, bx + bw + e, by + bh + e], radius=int(bh // 2 + e),
                                            outline=PINK + (int(170 * (1 - k) ** 1.5),), width=2)
    tile.alpha_composite(ring)
    # button body
    body = Image.new("RGBA", tile.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    bd.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=TEXT + (255,))
    f = F_SANS_SB(16)
    cx, ty = bx + 34, by + bh / 2
    for ch in BUTTON:
        bd.text((cx, ty), ch, font=f, fill=(14, 12, 20, 255), anchor="lm")
        cx += bd.textlength(ch, font=f) + BTN_TRACKING
    bd.text((cx + 8 + 3 * math.sin(2 * math.pi * k), ty), "↗", font=F_SANS_SB(19),
            fill=(120, 92, 220, 255), anchor="lm")
    # shimmer sweep, clipped to the bubble
    s = (k - 0.25) / 0.5
    if 0 <= s <= 1:
        sh = Image.new("RGBA", tile.size, (0, 0, 0, 0))
        sx = bx - 60 + s * (bw + 120)
        ImageDraw.Draw(sh).polygon([(sx, by), (sx + 34, by), (sx + 14, by + bh), (sx - 20, by + bh)],
                                   fill=(167, 139, 250, 120))
        clip = Image.new("L", tile.size, 0)
        ImageDraw.Draw(clip).rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=255)
        sh.putalpha(ImageChops.multiply(sh.getchannel("A"), clip))
        body.alpha_composite(sh)
    tile.alpha_composite(body)
    ImageDraw.Draw(tile).text((bx + bw + 24, by + bh / 2), URL_LABEL, font=F_MONO(13),
                              fill=MUTED + (255,), anchor="lm")
    return tile, (ox, oy)


# ---------------------------------------------------------------- compose
def load_model_frames():
    files = sorted(MODEL_DIR.glob("m*.png"))
    if not files:
        raise SystemExit(f"No model frames in {MODEL_DIR}. Render them first (see scripts/model/README.md).")
    return [Image.open(f).convert("RGBA") for f in files]


def frame(i, n, base, model_frames) -> Image.Image:
    im = base.copy()
    m = model_frames[i % len(model_frames)]
    im.alpha_composite(m, (MODEL_X, MODEL_Y))
    tile, pos = draw_button(i / n)
    im.alpha_composite(tile, pos)
    return im.convert("RGB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = build_background()
    base.alpha_composite(build_arch())
    base.alpha_composite(build_static_text())
    models = load_model_frames()
    n = len(models)
    frames = [frame(i, n, base, models) for i in range(n)]
    frames[0].save(OUT / "hero-static.png", optimize=True)
    # one shared palette keeps the GIF small; Pillow stores only the changed rectangle per frame
    pal = frames[n // 4].quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(OUT / "hero.gif", save_all=True, append_images=q[1:], duration=round(1000 / FPS),
              loop=0, optimize=True)
    for f in ("hero.gif", "hero-static.png"):
        print(f, round((OUT / f).stat().st_size / 1024), "KB")


if __name__ == "__main__":
    main()
