"""Verificación programática del PDF rellenado (sustituye la inspección visual):

- cada valor de TEXTO está dibujado dentro del rectángulo de su campo,
- sin desbordes groseros (texto que sobresalga mucho del campo),
- los campos siguen existiendo (no aplanado),
- los checkboxes marcados tienen apariencia dibujada (marca visible).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.pdf.filler import build_values  # noqa: E402
from app.schemas.i589 import I589Data  # noqa: E402

PDF = next(Path("outputs").glob("i589_*.pdf"))
data = I589Data.model_validate(json.loads(Path("tests/fixtures/caso_completo.json").read_text(encoding="utf-8")))
values = build_values(data)

doc = pymupdf.open(str(PDF))
widgets: dict[str, tuple[int, object, int]] = {}
for page in doc:
    for w in list(page.widgets()):
        if w.field_name:
            widgets[w.field_name] = (page.number, w.rect, w.field_type)

TEXT_TYPE = pymupdf.PDF_WIDGET_TYPE_TEXT
fallos = 0
text_ok = 0
checks_ok = 0
checks_tot = 0
for field, value in values.items():
    v = str(value).strip()
    if not v:
        continue
    if field not in widgets:
        print(f"! campo no encontrado en el PDF: {field}")
        fallos += 1
        continue
    pno, rect, ftype = widgets[field]
    page = doc[pno]

    if ftype == TEXT_TYPE:
        words = page.get_text("words", clip=rect + (-2, -2, 3, 3))
        text = " ".join(w[4] for w in words)
        probe = v[:12].replace("\n", " ")
        ok = probe in text or v[:8] in text
        overflow = [w[4] for w in words if w[2] > rect.x1 + 8]
        if ok:
            text_ok += 1
        else:
            print(f"! valor no visible en posición: {field} = {v!r} (encontrado: {text!r})")
            fallos += 1
        if overflow:
            print(f"! posible desborde en {field}: {overflow[:4]}")
            fallos += 1
    else:
        # checkbox/radio: si está marcado (valor != Off), debe haber apariencia dibujada
        checks_tot += 1
        if v != "Off":
            zone = rect + (-2, -2, 2, 2)
            has_mark = any(
                pymupdf.Rect(d["rect"]).intersects(zone)
                for d in page.get_drawings()
            )
            if has_mark:
                checks_ok += 1
            else:
                print(f"! checkbox sin marca visible: {field} = {v}")
                fallos += 1

n_widgets = sum(len(list(p.widgets())) for p in doc)
print(f"\nvalores de texto verificados en posición: {text_ok}")
print(f"checkboxes marcados con marca visible: {checks_ok}/{checks_tot}")
print(f"widgets restantes en el PDF (editables): {n_widgets}")
print(f"páginas: {doc.page_count}")
print("RESULTADO:", "OK" if fallos == 0 and n_widgets >= 460 else "REVISAR")
