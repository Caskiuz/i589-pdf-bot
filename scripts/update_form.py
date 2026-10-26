"""Actualización asistida del formulario I-589 a una edición nueva de USCIS.

Descarga (o recibe) el PDF oficial nuevo, lo descifra, compara el inventario
de campos con el actual y genera un reporte de cambios:
- campos añadidos (los nuevos quedan sin rellenar hasta mapearlos) — no rompen nada,
- campos eliminados,
- llaves del mapeo que se romperían (requieren revisión manual).

Solo aplica la actualización si NINGÚN campo mapeado desaparece (o con --force).
Antes de reemplazar nada crea respaldos de data/i-589-open.pdf, del inventario
y de las coordenadas de campos.

Uso:
    python scripts/update_form.py                 # descarga, compara y reporta
    python scripts/update_form.py --apply         # aplica si es compatible
    python scripts/update_form.py --pdf nuevo.pdf # usa un PDF local
    python scripts/update_form.py --apply --force # aplica aunque haya roturas
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pymupdf  # noqa: E402
from inventory import parse_dump  # noqa: E402

from app.form_update import (  # noqa: E402
    FORM_URL,
    STATUS_FILE,
    collect_mapping_fields,
    compare_inventories,
    extract_edition,
    fetch_form_bytes,
)

DATA = ROOT / "data"
BLANK = DATA / "i-589-open.pdf"
ORIGINAL = DATA / "i-589.pdf"
INVENTORY = DATA / "fields_inventory.json"
RECTS = DATA / "field_rects.json"
DUMP = DATA / "fields_dump.txt"
MAPPING = ROOT / "config" / "i589_mapping.json"


def find_pdftk() -> str:
    explicit = shutil.which("pdftk")
    if explicit:
        return explicit
    scoop = Path.home() / "scoop" / "shims" / "pdftk.exe"
    if scoop.exists():
        return str(scoop)
    sys.exit("ERROR: pdftk no está instalado (scoop install pdftk)")


def decrypt(src: Path, dst: Path) -> None:
    qpdf = shutil.which("qpdf")
    if not qpdf:
        qpdf_path = Path.home() / "scoop" / "shims" / "qpdf.exe"
        qpdf = str(qpdf_path) if qpdf_path.exists() else ""
    if qpdf:
        subprocess.run([qpdf, "--decrypt", str(src), str(dst)], check=True)
        return
    doc = pymupdf.open(str(src))
    if doc.needs_pass:
        doc.authenticate("")
    doc.save(str(dst), encryption=pymupdf.PDF_ENCRYPT_NONE)
    doc.close()


def build_inventory(pdf: Path, dump_path: Path) -> list[dict]:
    dump = subprocess.run(
        [find_pdftk(), str(pdf), "dump_data_fields_utf8"],
        capture_output=True, text=True, check=True,
    ).stdout
    dump_path.write_text(dump, encoding="utf-8")
    return parse_dump(dump_path)


def build_rects(pdf: Path) -> list[dict]:
    doc = pymupdf.open(str(pdf))
    rows = []
    for pno in range(len(doc)):
        for w in doc[pno].widgets():
            if not w.field_name:
                continue
            r = w.rect
            rows.append({
                "page": pno + 1, "name": w.field_name,
                "x": round(r.x0, 1), "y": round(r.y0, 1),
                "w": round(r.width, 1), "h": round(r.height, 1),
                "type": str(w.field_type),
            })
    doc.close()
    return rows


def print_report(report: dict, edition_old: str, edition_new: str) -> None:
    print("=" * 64)
    print("REPORTE DE ACTUALIZACIÓN DEL FORMULARIO I-589")
    print("=" * 64)
    print(f"Edición actual:   {edition_old or '(desconocida)'}")
    print(f"Edición nueva:    {edition_new or '(sin fecha legible)'}")
    print(f"Campos:           {report['count_old']} -> {report['count_new']}")
    print(f"Añadidos:         {len(report['added'])}")
    print(f"Eliminados:       {len(report['removed'])}")
    print(f"Mapeo afectado:   {len(report['affected'])} llaves")
    if report["added"]:
        print("\nCampos nuevos (quedan sin rellenar hasta mapearlos):")
        for f in report["added"][:40]:
            print(f"  + {f['name'].split('.')[-1]}  |  {f['alt'][:100]}")
        if len(report["added"]) > 40:
            print(f"  … y {len(report['added']) - 40} más")
    if report["removed"]:
        print("\nCampos eliminados:")
        for f in report["removed"][:40]:
            print(f"  - {f['name'].split('.')[-1]}  |  {f['alt'][:100]}")
        if len(report["removed"]) > 40:
            print(f"  … y {len(report['removed']) - 40} más")
    if report["affected"]:
        print("\n⚠ REQUIERE REVISIÓN MANUAL — estas llaves del mapeo apuntan a campos que ya no existen:")
        for item in report["affected"][:60]:
            print(f"  · {item['logical']}  ->  {item['field'].split('.')[-1]}")
        if len(report["affected"]) > 60:
            print(f"  … y {len(report['affected']) - 60} más")
        print("\nRevisa scripts/build_mapping.py y actualiza los nombres de campo afectados.")
    print("\nVeredicto:", "COMPATIBLE (se puede aplicar)" if report["compatible"] else "INCOMPATIBLE (revisión manual)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Actualización asistida del formulario I-589")
    ap.add_argument("--pdf", help="PDF oficial nuevo (local); si se omite, se descarga de USCIS")
    ap.add_argument("--apply", action="store_true", help="aplicar la actualización si es compatible")
    ap.add_argument("--force", action="store_true", help="aplicar aunque haya llaves del mapeo rotas")
    ap.add_argument("--skip-tests", action="store_true", help="no ejecutar pytest al aplicar")
    args = ap.parse_args()

    work = Path(tempfile.mkdtemp(prefix="i589_update_"))
    try:
        if args.pdf:
            src = Path(args.pdf).resolve()
            if not src.exists():
                sys.exit(f"ERROR: no existe {src}")
            print(f"Usando PDF local: {src}")
        else:
            src = work / "i-589.pdf"
            print(f"Descargando {FORM_URL} …")
            src.write_bytes(fetch_form_bytes(FORM_URL))
            print(f"Descargado: {src.stat().st_size} bytes")

        new_open = work / "nuevo-open.pdf"
        decrypt(src, new_open)
        edition_new = extract_edition(new_open)
        edition_old = extract_edition(BLANK) if BLANK.exists() else ""

        new_inventory = build_inventory(new_open, work / "fields_dump_new.txt")
        old_inventory = json.loads(INVENTORY.read_text(encoding="utf-8")) if INVENTORY.exists() else []
        mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
        report = compare_inventories(old_inventory, new_inventory, collect_mapping_fields(mapping))

        print_report(report, edition_old, edition_new)

        if not args.apply:
            print("\nModo reporte (sin cambios). Para aplicar: agrega --apply")
            return 0 if report["compatible"] else 1
        if not report["compatible"] and not args.force:
            print("\nNo se aplicó: hay llaves rotas. Corrige el mapeo o usa --force.")
            return 1

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        DATA.mkdir(exist_ok=True)
        if BLANK.exists():
            shutil.copy2(BLANK, DATA / f"i-589-open.backup-{stamp}.pdf")
        if INVENTORY.exists():
            shutil.copy2(INVENTORY, DATA / f"fields_inventory.backup-{stamp}.json")
        if RECTS.exists():
            shutil.copy2(RECTS, DATA / f"field_rects.backup-{stamp}.json")

        shutil.copy2(new_open, BLANK)
        INVENTORY.write_text(json.dumps(new_inventory, ensure_ascii=False, indent=1), encoding="utf-8")
        RECTS.write_text(json.dumps(build_rects(new_open), ensure_ascii=False, indent=1), encoding="utf-8")
        shutil.copy2(work / "fields_dump_new.txt", DUMP)
        STATUS_FILE.unlink(missing_ok=True)  # fuerza re-verificación del estado
        print(f"\n✅ Formulario actualizado a la edición {edition_new or '(sin fecha)'}.")
        print("   Respaldos guardados en data/*.backup-*")

        if not args.skip_tests:
            print("\nEjecutando pruebas…")
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests", "-q"],
                cwd=str(ROOT),
            )
            if proc.returncode != 0:
                print("\n⚠ Las pruebas fallaron. Revisa el mapeo antes de usar el sistema.")
                return 1
        print("\nListo. Revisa los campos añadidos y, si aplica, amplía scripts/build_mapping.py.")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
