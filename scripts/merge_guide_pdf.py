"""Une la portada (cover.pdf) y el cuerpo (body.pdf) en GUIA_CLIENTE.pdf."""
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "data" / "pdf_build"
COVER = BUILD / "cover.pdf"
BODY = BUILD / "body.pdf"
OUT = ROOT / "GUIA_CLIENTE.pdf"

A4_W, A4_H = 595.28, 841.89


def normalize_page_to_a4(page):
    box = page.mediabox
    w, h = float(box.width), float(box.height)
    if abs(w - A4_W) > 2 or abs(h - A4_H) > 2:
        sx, sy = A4_W / w, A4_H / h
        page.add_transformation(Transformation().scale(sx=sx, sy=sy))
        page.mediabox.lower_left = (0, 0)
        page.mediabox.upper_right = (A4_W, A4_H)
    return page


def main() -> None:
    writer = PdfWriter()
    writer.add_page(normalize_page_to_a4(PdfReader(str(COVER)).pages[0]))
    for page in PdfReader(str(BODY)).pages:
        writer.add_page(normalize_page_to_a4(page))
    writer.add_metadata({
        "/Title": "Guía de prueba — I-589 PDF Bot",
        "/Author": "Ricardo (I-589 PDF Bot)",
        "/Creator": "I-589 PDF Bot",
        "/Subject": "Guía de prueba del sistema de preparación del Formulario I-589",
    })
    with OUT.open("wb") as fh:
        writer.write(fh)
    print(f"OK: {OUT} ({OUT.stat().st_size} bytes, {len(PdfReader(str(OUT)).pages)} páginas)")


if __name__ == "__main__":
    main()
