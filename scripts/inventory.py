"""Convierte el dump de pdftk (dump_data_fields_utf8) en un inventario JSON
y produce un resumen legible agrupado por sección del formulario."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse_dump(path: Path) -> list[dict]:
    fields: list[dict] = []
    cur: dict | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(FieldName|FieldNameAlt|FieldType|FieldFlags|FieldMaxLength|FieldStateOption|FieldJustification|FieldValue):\s?(.*)$", line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if key == "FieldName":
            if cur:
                fields.append(cur)
            cur = {"name": value, "alt": "", "type": "", "flags": "", "maxlen": "", "options": []}
        elif cur is not None:
            if key == "FieldNameAlt":
                cur["alt"] = value
            elif key == "FieldType":
                cur["type"] = value
            elif key == "FieldFlags":
                cur["flags"] = value
            elif key == "FieldMaxLength":
                cur["maxlen"] = value
            elif key == "FieldStateOption":
                cur["options"].append(value)
            elif key == "FieldJustification":
                cur["justification"] = value
    if cur:
        fields.append(cur)
    return fields


def section_of(alt: str) -> str:
    m = re.match(r"^(Part[.\s]*[A-GI]+[.\s]*I*[.\s]*\d*|Addendum|Part[.\s]*\d+)", alt, re.I)
    if m:
        return m.group(1).strip()
    return "(sin sección)"


def main() -> None:
    dump = ROOT / "data" / "fields_dump.txt"
    out = ROOT / "data" / "fields_inventory.json"
    fields = parse_dump(dump)
    out.write_text(json.dumps(fields, ensure_ascii=False, indent=1), encoding="utf-8")

    # Resumen: contadores por tipo y por sección
    from collections import Counter
    types = Counter(f["type"] for f in fields)
    sections = Counter(section_of(f["alt"]) for f in fields)
    print(f"Total campos: {len(fields)}")
    print("Tipos:", dict(types))
    print("Secciones:")
    for s, c in sections.most_common():
        print(f"  {s}: {c}")
    print(f"Inventario guardado en {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
