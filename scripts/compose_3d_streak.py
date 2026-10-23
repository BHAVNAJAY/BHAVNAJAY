#!/usr/bin/env python3
"""Put the streak card inside the 3D contribution calendar, replacing its radar chart.

Run after both images have been generated (the workflow does this):
    python3 scripts/compose_3d_streak.py
Reads  profile-3d-contrib/profile-3d-bhavna.svg  and  profile/streak.svg,
rewrites the 3D file in place. Does nothing if the radar is already gone or an input is missing.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "profile-3d-contrib" / "profile-3d-bhavna.svg"
STREAK = ROOT / "profile" / "streak.svg"
CARD_W, CARD_H = 495, 195
RIGHT_MARGIN, TOP = 34, 175  # card sits where the radar chart was (top-right)


def radar_span(svg: str) -> tuple[int, int] | None:
    """Start/end offsets of the top-level <g> that contains the radar polygon."""
    marker = svg.find('class="radar"')
    if marker < 0:
        return None
    depth, top_start = 0, None
    for m in re.finditer(r"<g\b[^>]*?(?<!/)>|</g>", svg):
        if m.group(0) == "</g>":
            depth -= 1
            if depth == 0 and top_start is not None and top_start < marker < m.end():
                return top_start, m.end()
        else:
            if depth == 0:
                top_start = m.start()
            depth += 1
    return None


def freeze(streak: str) -> str:
    """Bake in the animations' end state; animations don't run inside a nested <image>."""
    streak = re.sub(r"opacity:\s*0;\s*animation:\s*fadein[^;'\"]*", "opacity: 1", streak)
    streak = re.sub(r"animation:\s*currstreak[^;'\"]*", "font-size: 28px; opacity: 1", streak)
    return streak


def main() -> None:
    if not CAL.exists() or not STREAK.exists():
        print("missing input, nothing to do")
        return
    svg = CAL.read_text(encoding="utf-8")
    span = radar_span(svg)
    if span is None:
        print("radar not found (already composed?), nothing to do")
        return
    w = int(re.search(r'<svg[^>]*\bwidth="(\d+)', svg).group(1))
    data = base64.b64encode(freeze(STREAK.read_text(encoding="utf-8")).encode()).decode()
    x = w - RIGHT_MARGIN - CARD_W
    card = (f'<image x="{x}" y="{TOP}" width="{CARD_W}" height="{CARD_H}" '
            f'href="data:image/svg+xml;base64,{data}"/>')
    CAL.write_text(svg[:span[0]] + card + svg[span[1]:], encoding="utf-8")
    print("streak card placed in the 3D calendar")


if __name__ == "__main__":
    main()
