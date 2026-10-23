#!/usr/bin/env python3
"""Recreate assets/source/bhavna-portrait-cutout.png from the original photo.

Only the plain white studio background is removed: rembg's `u2net_human_seg` model gives the
silhouette, then the hair/edge pixels are un-mixed from the known white background so no
white halo remains on a dark banner. Interior pixels (face, body) are copied unchanged.

    pip install "rembg[cpu]" scipy pillow numpy
    python3 scripts/cutout_refine.py
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "source" / "bhavna-portrait-original.png"
DST = ROOT / "assets" / "source" / "bhavna-portrait-cutout.png"
W = 255.0


def main():
    from rembg import new_session, remove

    photo = Image.open(SRC).convert("RGB")
    orig = np.asarray(photo).astype(np.float32)
    a0 = np.asarray(remove(photo, session=new_session("u2net_human_seg")))[..., 3].astype(np.float32) / 255

    m = a0 > 0.5
    inner = ndi.binary_erosion(m, iterations=5)
    outer = ndi.binary_dilation(m, iterations=5)
    band = outer & ~inner
    # local foreground colour: normalized convolution of interior colours
    sig = 7
    wgt = ndi.gaussian_filter(inner.astype(np.float32), sig)
    F = np.stack([ndi.gaussian_filter(orig[..., c] * inner, sig) for c in range(3)], -1)
    F /= np.maximum(wgt, 1e-4)[..., None]
    WF, WC = W - F, W - orig
    den = (WF ** 2).sum(-1)
    a_un = np.clip((WC * WF).sum(-1) / np.maximum(den, 1), 0, 1)
    contrast = np.clip((np.sqrt(den) - 60) / 80, 0, 1)  # dark hair: trust un-mixing; cream shirt: trust model
    a = np.where(inner, 1.0, np.where(band, contrast * a_un + (1 - contrast) * a0, 0.0))
    aa = np.clip(a, 1e-3, 1)[..., None]
    Fu = np.clip((orig - (1 - aa) * W) / aa, 0, 255)
    col = np.where(inner[..., None], orig, np.where(aa > 0.35, Fu, F))
    Image.fromarray(np.dstack([col, a * 255]).round().astype(np.uint8), "RGBA").save(DST)
    print("wrote", DST)


if __name__ == "__main__":
    main()
