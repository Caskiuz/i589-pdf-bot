"""Verifica que el entorno del I-589 PDF Bot esté listo y da instrucciones claras."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def check_pdftk() -> tuple[bool, str]:
    explicit = os.getenv("PDFTK_PATH", "").strip()
    if explicit and Path(explicit).exists():
        return True, explicit
    found = shutil.which("pdftk")
    if found:
        return True, found
    scoop = Path.home() / "scoop" / "shims" / "pdftk.exe"
    if scoop.exists():
        return True, str(scoop)
    return False, ""


def main() -> int:
    from app.db import init_db

    init_db()
    problems: list[str] = []

    pdftk_ok, pdftk_path = check_pdftk()
    if pdftk_ok:
        print(f"[OK] pdftk: {pdftk_path}")
    else:
        problems.append("pdftk no está instalado. Ejecuta:  scoop install pdftk")

    form = ROOT / "data" / "i-589-open.pdf"
    if form.exists():
        print(f"[OK] Formulario I-589: {form.name} ({form.stat().st_size} bytes)")
    else:
        problems.append("Falta el formulario. Ejecuta:  python scripts/download_form.py")
        from scripts.download_form import decrypt, download

        print("Intentando descargarlo ahora…")
        try:
            if not (ROOT / "data" / "i-589.pdf").exists():
                download()
            decrypt()
            problems.remove("Falta el formulario. Ejecuta:  python scripts/download_form.py")
        except Exception as exc:
            print(f"  No se pudo descargar: {exc}")

    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if key:
        print("[OK] API key de DeepSeek configurada (.env)")
    else:
        problems.append(
            "No hay DEEPSEEK_API_KEY. Copia .env.example a .env y pega tu key de "
            "https://platform.deepseek.com (sin ella, la extracción con IA no funciona)."
        )

    if problems:
        print("\n⚠ Pendientes:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\n✅ Todo listo. Ejecuta: run_demo.bat  (o: python -m uvicorn app.main:app)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
