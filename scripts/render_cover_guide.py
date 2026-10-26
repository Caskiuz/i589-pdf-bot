"""Renderiza la portada de la guía con la paleta del cuerpo y Segoe UI."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL = Path("C:/Users/rijar/.zcode/cli/plugins/cache/zcode-plugins-official/pdf/0.1.8/skills/pdf/scripts")
sys.path.insert(0, str(SKILL))

from cover_render import detect_fonts, render_cover  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "data" / "pdf_build"
CONTENT = json.loads((BUILD / "cover_content.json").read_text(encoding="utf-8"))
OUT = BUILD / "cover.pdf"

PALETTE = {
    "primary": "#4b29b2",     # acento de la paleta generada
    "secondary": "#6a4bc7",   # variante clara del acento
    "text": "#1b1b19",
    "muted": "#817d74",
    "bg": "#ffffff",
}

FONTS = detect_fonts({
    "sans": ("SegoeUI", "C:/Windows/Fonts/segoeui.ttf", None),
    "latin": ("SegoeUI", "C:/Windows/Fonts/segoeui.ttf", None),
})

render_cover("03", CONTENT, str(OUT), palette=PALETTE, fonts=FONTS)
print(f"OK: {OUT}")
