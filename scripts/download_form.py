"""Descarga el formulario oficial I-589 de USCIS y genera la copia descifrada.

El formulario oficial viene cifrado con contraseña de propietario (USCIS lo
publica así). qpdf lo descifra sin tocar nada más: campos, JavaScript del
código de barras 2D y estructura quedan intactos.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FORM_URL = "https://www.uscis.gov/sites/default/files/document/forms/i-589.pdf"
ORIGINAL = DATA / "i-589.pdf"
OPEN = DATA / "i-589-open.pdf"


def download() -> None:
    DATA.mkdir(exist_ok=True)
    print(f"Descargando {FORM_URL} …")
    req = urllib.request.Request(FORM_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, ORIGINAL.open("wb") as fh:
        fh.write(resp.read())
    print(f"Guardado: {ORIGINAL} ({ORIGINAL.stat().st_size} bytes)")


def decrypt() -> None:
    qpdf = shutil.which("qpdf")
    if qpdf:
        subprocess.run([qpdf, "--decrypt", str(ORIGINAL), str(OPEN)], check=True)
        print(f"Descifrado con qpdf: {OPEN}")
        return
    # Plan B: PyMuPDF (menos fiel que qpdf; qpdf es el método recomendado)
    try:
        import pymupdf  # type: ignore

        doc = pymupdf.open(str(ORIGINAL))
        if doc.needs_pass:
            doc.authenticate("")
        doc.save(str(OPEN), encryption=pymupdf.PDF_ENCRYPT_NONE)
        doc.close()
        print(f"Descifrado con PyMuPDF (instala qpdf para máxima fidelidad): {OPEN}")
    except ImportError:
        sys.exit("ERROR: instala qpdf (scoop install qpdf) o pymupdf (pip install pymupdf)")


def main() -> None:
    if not OPEN.exists() and not ORIGINAL.exists():
        download()
    elif not OPEN.exists():
        print("Usando copia local del formulario original.")
    if not OPEN.exists():
        decrypt()
    if not OPEN.exists():
        sys.exit("ERROR: no se pudo generar el formulario descifrado")
    print("Listo. El formulario descifrado está en data/i-589-open.pdf")


if __name__ == "__main__":
    main()
