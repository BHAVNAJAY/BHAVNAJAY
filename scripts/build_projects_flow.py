#!/usr/bin/env python3
"""Build the projects "flow": a strip of project cards that scrolls past and curves away at both edges.

Input : assets/source/backdrops/<slug>.jpg  +  PROJECTS in scripts/build_cards.py
Output: assets/projects/projects-flow.webp  (looping animated WebP)
Requires: Pillow, numpy.  Run from the repository root:  python3 scripts/build_projects_flow.py
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_cards", ROOT / "scripts" / "build_cards.py")
cards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cards)

ORDER = ["satquery-ai", "ping", "iready", "netra", "ecolearn", "notify"]
W, H = 1100, 330
CARD_W, CARD_H, GAP, RADIUS = 300, 165, 30, 14
BG = (11, 10, 15)
FPS, STEP = 14, 10           # frames per second, strip pixels moved per frame
THETA = math.radians(64)     # how far round the "cylinder" the visible window reaches
PERSPECTIVE = 2.3            # camera distance in cylinder radii (smaller = stronger edge shrink)
FONTS = ROOT / "scripts" / "fonts"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def build_strip() -> Image.Image:
    """All cards (image + title + tagline) in one long row, flat and unwarped."""
    info = {p[0]: p for p in cards.PROJECTS}
    period = len(ORDER) * (CARD_W + GAP)
    strip = Image.new("RGB", (period, H), BG)
    top = 62
    for i, slug in enumerate(ORDER):
        _, title, short, *_ = info[slug]
        x = i * (CARD_W + GAP)
        im = Image.open(ROOT / "assets" / "source" / "backdrops" / f"{slug}.jpg").convert("RGB")
        im = im.resize((CARD_W, CARD_H), Image.LANCZOS)
        mask = Image.new("L", (CARD_W * 4, CARD_H * 4), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, CARD_W * 4 - 1, CARD_H * 4 - 1], RADIUS * 4, fill=255)
        mask = mask.resize((CARD_W, CARD_H), Image.LANCZOS)
        strip.paste(im, (x, top), mask)
        d = ImageDraw.Draw(strip)
        d.text((x + 2, top + CARD_H + 16), title, font=font("Poppins-Bold.ttf", 19), fill=(244, 241, 248))
        d.text((x + 2, top + CARD_H + 44), short, font=font("Inter-Regular.otf", 13), fill=(142, 135, 156))
    return strip


def warp(strip: np.ndarray, offset: float) -> np.ndarray:
    """Wrap the strip round a cylinder seen from the front: edges curve away and shrink."""
    sh, sw, _ = strip.shape
    r = (W / 2) / math.sin(THETA)
    xs = np.arange(W) + 0.5
    theta = np.arcsin(np.clip((xs - W / 2) / r, -1, 1))
    src_x = (W / 2 + r * theta + offset) % sw                       # arc length -> strip column
    scale = PERSPECTIVE / (PERSPECTIVE + (1 - np.cos(theta)))       # farther = smaller
    cy = H / 2
    ys = np.arange(H) + 0.5
    src_y = cy + (ys[:, None] - cy) / scale[None, :]                # (H, W)
    x0 = np.floor(src_x).astype(int)
    fx = (src_x - x0)[None, :, None]
    x1 = (x0 + 1) % sw
    x0 %= sw
    y0 = np.clip(np.floor(src_y).astype(int), 0, sh - 2)
    fy = np.clip(src_y - y0, 0, 1)[..., None]
    cols = np.arange(W)[None, :]
    def px(yy, xx):
        return strip[yy, xx[None, :] if xx.ndim == 1 else xx].astype(np.float32)
    a = px(y0, x0) * (1 - fx) + px(y0, x1) * fx
    b = px(y0 + 1, x0) * (1 - fx) + px(y0 + 1, x1) * fx
    out = a * (1 - fy) + b * fy
    inside = ((src_y >= 0) & (src_y <= sh - 1))[..., None]
    bg = np.array(BG, np.float32)
    out = np.where(inside, out, bg)
    shade = (0.35 + 0.65 * np.cos(theta) ** 1.5)[None, :, None]     # darker as it turns away
    out = bg + (out - bg) * shade
    return np.clip(out, 0, 255).astype(np.uint8)


def main():
    strip = np.asarray(build_strip())
    period = strip.shape[1]
    n = period // STEP
    frames = [Image.fromarray(warp(strip, i * STEP)) for i in range(n)]
    out = ROOT / "assets" / "projects" / "projects-flow.webp"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=round(1000 / FPS),
                   loop=0, quality=60, method=4)
    frames[0].save(ROOT / "assets" / "projects" / "projects-flow-static.png", optimize=True)
    print(out.name, n, "frames", round(out.stat().st_size / 1024), "KB")


if __name__ == "__main__":
    main()
