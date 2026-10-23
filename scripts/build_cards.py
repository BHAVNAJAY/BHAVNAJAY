#!/usr/bin/env python3
"""Generate the README's SVG assets: skill pills, project cards, achievement cards, contact pills.

All content lives in the DATA section below — edit it and re-run:
    python3 scripts/build_cards.py
Requires: Python 3.10+, Pillow (text measurement), fonttools + brotli (font subsetting).

Each SVG embeds a tiny subset of its fonts as a data URI, so it renders identically on
GitHub (SVGs shown through <img> cannot load external fonts or run scripts).
Brand icons: Simple Icons (CC0), vendored in scripts/icons/.
"""
from __future__ import annotations

import base64
import colorsys
import io
import re
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "scripts" / "fonts"
ICONS = ROOT / "scripts" / "icons"
ASSETS = ROOT / "assets"

# =============================================================== DATA
SKILLS = {
    "development": [
        ("Python", "python"), ("JavaScript", "javascript"), ("TypeScript", "typescript"),
        ("React.js", "react"), ("Next.js", "nextdotjs"), ("Node.js", "nodedotjs"),
        ("Express.js", "express"), ("Flask", "flask"), ("FastAPI", "fastapi"), ("SQL", None),
        ("MongoDB", "mongodb"), ("PostgreSQL", "postgresql"), ("Supabase", "supabase"),
        ("REST APIs", None), ("Git", "git"), ("GitHub", "github"),
    ],
    "ai-ml": [
        ("Generative AI", None), ("LLMs", None), ("Prompt Engineering", None), ("RAG", None),
        ("Embeddings", None), ("Agentic AI", None), ("NLP", None), ("Computer Vision", None),
        ("PyTorch", "pytorch"), ("Scikit-learn", "scikitlearn"), ("Pandas", "pandas"),
        ("NumPy", "numpy"), ("Gemini API", "googlegemini"), ("OpenAI API", None),
    ],
}

# From the portfolio projects data (title, short description, hue, stack, repo, demo)
PROJECTS = [
    ("satquery-ai", "SatQuery AI", "AI-Powered Earth Observation", 200,
     ["Python", "PyTorch", "LLMs", "Agentic AI", "RAG", "Computer Vision"],
     "https://github.com/BHAVNAJAY/SatQueryAI", None),
    ("ping", "Ping", "Intelligent Campaign Automation", 328,
     ["React", "Node.js", "Express.js", "MongoDB", "OpenAI API"],
     None, "https://ping-ecru-nu.vercel.app/"),
    ("iready", "iReady", "AI-Powered Interview Preparation", 262,
     ["React", "Flask", "Python", "Scikit-learn", "NLTK"],
     None, "https://i-ready-alpha.vercel.app/"),
    ("netra", "Netra", "Intelligent Healthcare Operations", 14,
     ["Python", "FastAPI", "Scikit-learn", "Next.js", "Supabase"],
     "https://github.com/BHAVNAJAY/Netra", None),
    ("ecolearn", "EcoLearn", "Gamified Sustainability Education", 96,
     ["React", "TypeScript", "Supabase", "Gemini API"],
     "https://github.com/BHAVNAJAY/Eco-Learn", None),
    ("notify", "Notify", "Secure Notes & Organization", 210,
     ["React", "Node.js", "Express.js", "MongoDB", "Google OAuth"],
     None, "https://notify-yh0m.onrender.com/"),
]

ACHIEVEMENTS = [
    ("sih-2025-winner", "Smart India Hackathon 2025", "WINNER",
     "Built a SaaS platform solution for the Government of Punjab addressing real-world "
     "administrative workflows."),
    ("nxtgen-runner-up", "NxtGen Hackathon", "RUNNER-UP",
     "Built Netra, an intelligent hospital operations platform designed to improve patient flow, "
     "anticipate resource requirements, and support healthcare capacity planning."),
    ("finan-performance-award", "Performance Excellence Award", "FINAN CONSULTING",
     "Recognised for performance, ownership, and contributions to SaaS product development "
     "during my full-stack development internship."),
    ("hackverse-25", "HackVerse’25", "ORGANISER & DESIGNER",
     "Organised and designed for a national-level Web3 × AI hackathon, coordinating event "
     "execution and creative deliverables for an event with 200+ participants."),
]

CONTACT = [  # (file, side, text shown, logo)
    ("email", "left", "bhavnajayakumar@gmail.com", "gmail"),
    ("linkedin", "right", "bhavna-jayakumar", "linkedin"),
]

# =============================================================== LOOK
BG_CARD = "#111017"
BG_PILL = "#15131C"
STROKE = "#2A2533"
TEXT = "#F4F1F8"
TEXT_2 = "#CFC9DA"
MUTED = "#8E879C"
VIOLET = "#A78BFA"
PINK = "#F0A6CA"
CATEGORY_ACCENT = {"development": VIOLET, "design": PINK, "ai-ml": "#C7A4F0", "contact": VIOLET}

FONT_FILES = {
    "serif": "InstrumentSerif-Regular.ttf",
    "serif-i": "InstrumentSerif-Italic.ttf",
    "sans": "Inter-Regular.otf",
    "sans-m": "Inter-Medium.otf",
    "mono": "JetBrainsMono-Regular.ttf",
    "mono-m": "JetBrainsMono-Medium.ttf",
}

# neutral glyphs (24×24) for items without an official icon — never imitations of brand marks
GLYPHS = {
    "development": '<path d="M8 6 2.5 12 8 18M16 6l5.5 6-5.5 6M13.5 4l-3 16" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
    "design": '<circle cx="12" cy="12" r="8.5" fill="none" stroke="{c}" stroke-width="2.2"/><circle cx="12" cy="12" r="3" fill="{c}"/>',
    "ai-ml": '<path d="M12 1.5c.6 5.6 4.9 9.9 10.5 10.5-5.6.6-9.9 4.9-10.5 10.5C11.4 16.9 7.1 12.6 1.5 12 7.1 11.4 11.4 7.1 12 1.5Z" fill="{c}"/>',
    "contact": '<circle cx="12" cy="8" r="4" fill="none" stroke="{c}" stroke-width="2.2"/><path d="M4 21c.8-4.2 4-6.5 8-6.5s7.2 2.3 8 6.5" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>',
}


# =============================================================== helpers
@lru_cache(maxsize=None)
def pil_font(key: str, size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / FONT_FILES[key]), size=size * 10)  # 10x for precision


def text_w(text: str, key: str, size: float, tracking: float = 0) -> float:
    return pil_font(key, size).getlength(text) / 10 + tracking * max(len(text) - 1, 0)


def font_face(usage: dict[str, set[str]]) -> str:
    """@font-face rules with per-file subsets embedded as woff2 data URIs."""
    rules = []
    for key, chars in usage.items():
        if not chars:
            continue
        f = TTFont(FONTS / FONT_FILES[key])
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga"]
        opts.name_IDs = []
        opts.notdef_outline = True
        sub = subset.Subsetter(opts)
        sub.populate(text="".join(sorted(chars | {" "})))
        sub.subset(f)
        buf = io.BytesIO()
        f.flavor = "woff2"
        f.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        rules.append(f"@font-face{{font-family:bj-{key};src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "".join(rules)


class Doc:
    """Tiny SVG builder that tracks which characters each font needs."""

    def __init__(self, w: float, h: float, title: str):
        self.w, self.h, self.title = w, h, title
        self.parts: list[str] = []
        self.defs: list[str] = []
        self.usage: dict[str, set[str]] = {}
        self.pad_bottom = 0  # transparent space below (gap between stacked cards)

    def text(self, x, y, s, key, size, fill, anchor="start", tracking=0.0, opacity=1.0):
        self.usage.setdefault(key, set()).update(s)
        ls = f' letter-spacing="{tracking}"' if tracking else ""
        op = f' fill-opacity="{opacity}"' if opacity != 1 else ""
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="bj-{key}" font-size="{size}" fill="{fill}"{op}'
            f' text-anchor="{anchor}"{ls}>{escape(s)}</text>')

    def raw(self, s: str):
        self.parts.append(s)

    def render(self) -> str:
        style = f"<style>{font_face(self.usage)}</style>"
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        h = self.h + self.pad_bottom
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w:.0f}" height="{h:.0f}" '
                f'viewBox="0 0 {self.w:.0f} {h:.0f}" role="img" aria-label="{escape(self.title)}">'
                f"<title>{escape(self.title)}</title>{style}{defs}{''.join(self.parts)}</svg>\n")


def icon_path(slug: str) -> str:
    svg = (ICONS / f"{slug}.svg").read_text()
    return re.search(r'<path d="([^"]+)"', svg).group(1)


def brand_hex(slug: str) -> str:
    # colours from the Simple Icons data, kept here so the script has no npm dependency
    return {
        "python": "3776AB", "javascript": "F7DF1E", "typescript": "3178C6", "react": "61DAFB",
        "nextdotjs": "000000", "nodedotjs": "5FA04E", "express": "0A0A0A", "flask": "3BABC3",
        "fastapi": "009688", "mongodb": "47A248", "postgresql": "4169E1", "supabase": "3FCF8E",
        "git": "F03C2E", "github": "181717", "figma": "F24E1E", "blender": "E87D0D",
        "pytorch": "EE4C2C", "scikitlearn": "F7931E", "pandas": "150458", "numpy": "013243",
        "googlegemini": "8E75B2", "gmail": "EA4335",
    }[slug]


def lum(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def readable_on_dark(hexcol: str) -> str:
    """Keep the brand hue but lift it until it reads on the dark pill (contrast ≥ 3.2)."""
    rgb = [int(hexcol[i:i + 2], 16) for i in (0, 2, 4)]
    bg = lum((21, 19, 28))
    for _ in range(20):
        if (lum(rgb) + 0.05) / (bg + 0.05) >= 3.2:
            break
        rgb = [min(255, int(c + (255 - c) * 0.18)) for c in rgb]
    return "#%02X%02X%02X" % tuple(rgb)


def hsl(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def wrap(s: str, key: str, size: float, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        t = (cur + " " + word).strip()
        if text_w(t, key, size) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# =============================================================== pills
def pill_light(label: str, icon: str | None, category: str) -> str:
    """White bubble, large brand logo, small black label (development tools)."""
    size, key = 13, "sans-m"
    pad_l, icon_sz, gap, pad_r = 11, 26, 10, 18
    text_only = icon is None and category == "ai-ml"  # no logo: just the name in the bubble
    if text_only:
        pad_l, icon_sz, gap, pad_r = 20, 0, 0, 20
    tw = text_w(label, key, size)
    pw = pad_l + icon_sz + gap + tw + pad_r
    W, H, top, ph = pw + 8, 52, 4, 44
    d = Doc(W, H, label)
    d.raw(f'<rect x="0.5" y="{top + .5}" width="{pw - 1:.1f}" height="{ph - 1}" rx="{(ph - 1) / 2}" '
          f'fill="#FFFFFF" stroke="#D9D6E0"/>')
    iy = top + (ph - icon_sz) / 2
    s = icon_sz / 24
    if text_only:
        pass
    elif icon:
        d.raw(f'<g transform="translate({pad_l},{iy}) scale({s})"><path fill="#{brand_hex(icon)}" d="{icon_path(icon)}"/></g>')
    else:
        g = GLYPHS[category].format(c="#5B3FD1")
        d.raw(f'<g transform="translate({pad_l},{iy}) scale({s})">{g}</g>')
    d.text(pad_l + icon_sz + gap, top + ph / 2 + 4.6, label, key, size, "#111111")
    return d.render()


def pill(label: str, icon: str | None, category: str) -> str:
    if category in ("development", "ai-ml"):
        return pill_light(label, icon, category)
    size, key = 13.5, "sans-m"
    pad_l, icon_sz, gap, pad_r = 13, 16, 9, 15
    tw = text_w(label, key, size)
    pw = pad_l + icon_sz + gap + tw + pad_r
    W, H, top, ph = pw + 8, 46, 5, 36  # transparent margin right/top/bottom = spacing when wrapped
    d = Doc(W, H, label)
    d.raw(f'<rect x="0.5" y="{top + .5}" width="{pw - 1:.1f}" height="{ph - 1}" rx="{(ph - 1) / 2}" '
          f'fill="{BG_PILL}" stroke="{STROKE}"/>')
    iy = top + (ph - icon_sz) / 2
    s = icon_sz / 24
    if icon:
        col = readable_on_dark(brand_hex(icon))
        d.raw(f'<g transform="translate({pad_l},{iy}) scale({s})"><path fill="{col}" d="{icon_path(icon)}"/></g>')
    else:
        g = GLYPHS[category].format(c=CATEGORY_ACCENT[category])
        d.raw(f'<g transform="translate({pad_l},{iy}) scale({s})">{g}</g>')
    d.text(pad_l + icon_sz + gap, top + ph / 2 + 4.9, label, key, size, "#ECE8F3")
    return d.render()


# =============================================================== contact bar
def contact_half(side: str, label: str, logo: str) -> str:
    """One half of the long contact bar (two of these sit edge to edge): white, purple outline."""
    W, H, r, PURPLE = 400, 64, 18, "#8B6CF0"
    d = Doc(W, H, label)
    if side == "left":
        outline = f"M{W},1 H{r + 1} A{r},{r} 0 0 0 1,{r + 1} V{H - r - 1} A{r},{r} 0 0 0 {r + 1},{H - 1} H{W}"
        fill = f"M{W},1 H{r + 1} A{r},{r} 0 0 0 1,{r + 1} V{H - r - 1} A{r},{r} 0 0 0 {r + 1},{H - 1} H{W}Z"
    else:
        outline = f"M0,1 H{W - r - 1} A{r},{r} 0 0 1 {W - 1},{r + 1} V{H - r - 1} A{r},{r} 0 0 1 {W - r - 1},{H - 1} H0"
        fill = outline + "Z"
    d.raw(f'<path d="{fill}" fill="#FFFFFF"/>')
    d.raw(f'<path d="{outline}" fill="none" stroke="{PURPLE}" stroke-width="1.5"/>')
    if side == "right":
        d.raw(f'<line x1="0.75" y1="1" x2="0.75" y2="{H - 1}" stroke="{PURPLE}" stroke-width="1.5"/>')
    size, icon_sz, gap = 16, 30, 12
    tw = text_w(label, "sans-m", size)
    x0 = (W - (icon_sz + gap + tw)) / 2
    y0 = (H - icon_sz) / 2
    if logo == "gmail":
        d.raw(f'<g transform="translate({x0:.1f},{y0}) scale({icon_sz / 24})"><path fill="#EA4335" d="{icon_path("gmail")}"/></g>')
    else:  # LinkedIn: blue rounded square with a white "in"
        d.raw(f'<rect x="{x0:.1f}" y="{y0}" width="{icon_sz}" height="{icon_sz}" rx="6" fill="#0A66C2"/>')
        d.text(x0 + icon_sz / 2, y0 + icon_sz / 2 + 6.5, "in", "sans-m", 18, "#FFFFFF", anchor="middle")
    d.text(x0 + icon_sz + gap, H / 2 + 5.6, label, "sans-m", size, "#111111")
    return d.render()


# =============================================================== project card
def backdrop_uri(slug: str) -> str:
    data = (ASSETS / "source" / "backdrops" / f"{slug}.jpg").read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def project_card(i, slug, title, short, hue, stack, repo, demo) -> str:
    """Backdrop image on top, details panel below (the images carry their own artwork/titles)."""
    W, IMG_H, PANEL = 400, 220, 160
    H = IMG_H + PANEL
    acc = hsl(hue, 0.78, 0.66)
    d = Doc(W, H, f"{title} — {short}")
    d.pad_bottom = 10
    d.defs.append(f'<clipPath id="c"><rect width="{W}" height="{H}" rx="18"/></clipPath>')
    d.raw(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="17.5" fill="{BG_CARD}"/>')
    d.raw(f'<g clip-path="url(#c)"><image href="{backdrop_uri(slug)}" x="0" y="0" width="{W}" height="{IMG_H}" '
          f'preserveAspectRatio="xMidYMid slice"/></g>')
    d.raw(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="17.5" fill="none" stroke="{STROKE}"/>')
    # primary link tag (top-right of the image)
    tag = "github ↗" if repo else "live demo ↗"
    tw = text_w(tag, "mono-m", 10.5) + 22
    d.raw(f'<rect x="{W - 16 - tw:.1f}" y="14" width="{tw:.1f}" height="24" rx="12" fill="#0B0A0F" fill-opacity=".72" '
          f'stroke="{acc}" stroke-opacity=".7"/>')
    d.text(W - 16 - tw / 2, 30, tag, "mono-m", 10.5, TEXT, anchor="middle")
    y0 = IMG_H
    d.text(24, y0 + 28, f"{i:02d}", "mono", 11.5, MUTED)
    d.text(48, y0 + 28, "/ project", "mono", 11.5, MUTED, opacity=.7)
    d.text(23, y0 + 66, title, "serif", 34, TEXT)
    d.text(24, y0 + 88, short, "sans", 13.5, TEXT_2)
    items, line = [s.lower() for s in stack], ""
    for it in items:
        t = (line + " · " + it) if line else it
        if text_w(t, "mono", 11) > W - 48:
            line += " …"
            break
        line = t
    d.text(24, y0 + 110, line, "mono", 11, MUTED)
    d.raw(f'<line x1="24" y1="{y0 + 124}" x2="{W - 24}" y2="{y0 + 124}" stroke="{STROKE}"/>')
    y = y0 + 146
    repo_txt = repo.replace("https://github.com/", "") + " ↗" if repo else "not listed"
    demo_txt = re.sub(r"^https?://|/$", "", demo) + " ↗" if demo else "not listed"
    d.text(24, y, "REPO", "mono-m", 9.5, MUTED, tracking=1.2)
    d.text(58, y, repo_txt, "mono", 11, TEXT if repo else MUTED, opacity=1 if repo else .6)
    dx = W - 24 - text_w(demo_txt, "mono", 11)
    d.text(dx - 8, y, "DEMO", "mono-m", 9.5, MUTED, anchor="end", tracking=1.2)
    d.text(dx, y, demo_txt, "mono", 11, TEXT if demo else MUTED, opacity=1 if demo else .6)
    return d.render()


# =============================================================== achievement card
def achievement_cards() -> dict[str, str]:
    """Slim white cards with a purple outline, one per row: tag + title left, description right."""
    W, LEFT_W, DESC_X = 800, 250, 292
    PURPLE, PURPLE_DK = "#8B6CF0", "#6D4FD8"
    lines_all = [wrap(desc, "sans", 12.5, W - DESC_X - 24) for *_, desc in ACHIEVEMENTS]
    n = max(len(l) for l in lines_all)
    H = max(100, n * 18 + 40)
    out = {}
    for idx, ((slug, title, tag, desc), lines) in enumerate(zip(ACHIEVEMENTS, lines_all), 1):
        d = Doc(W, H, f"{title} — {tag.title()}: {desc}")
        d.pad_bottom = 8
        d.raw(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="#FFFFFF" stroke="{PURPLE}" stroke-width="1.5"/>')
        tw = text_w(tag, "mono-m", 9.5, tracking=1.1) + 20
        d.raw(f'<rect x="22" y="16" width="{tw:.1f}" height="20" rx="10" fill="{PURPLE}" fill-opacity=".10" stroke="{PURPLE}" stroke-opacity=".55"/>')
        d.text(32, 30, tag, "mono-m", 9.5, PURPLE_DK, tracking=1.1)
        for j, ln in enumerate(wrap(title, "serif", 22, LEFT_W - 22)):
            d.text(22, 62 + j * 24, ln, "serif", 22, "#14121C")
        d.raw(f'<line x1="{DESC_X - 22}" y1="18" x2="{DESC_X - 22}" y2="{H - 18}" stroke="#E4DEF5"/>')
        d.text(W - 22, 29, f"A.{idx:02d}", "mono", 10.5, "#8E879C", anchor="end")
        y0 = max(48, (H - len(lines) * 18) / 2 + 12)
        for j, ln in enumerate(lines):
            d.text(DESC_X, y0 + j * 18, ln, "sans", 12.5, "#4A4458")
        out[slug] = d.render()
    return out


# =============================================================== main
def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main():
    n = 0
    for cat, items in SKILLS.items():
        for label, icon in items:
            write(ASSETS / "skills" / f"{slugify(label)}.svg", pill(label, icon, cat)); n += 1
    for i, p in enumerate(PROJECTS, 1):
        write(ASSETS / "projects" / f"{p[0]}.svg", project_card(i, *p)); n += 1
    for slug, svg in achievement_cards().items():
        write(ASSETS / "achievements" / f"{slug}.svg", svg); n += 1
    for slug, side, label, logo in CONTACT:
        write(ASSETS / "contact" / f"{slug}.svg", contact_half(side, label, logo)); n += 1
    print(f"wrote {n} SVG files")


if __name__ == "__main__":
    main()
