"""Reporte legible del inventario para construir el mapeo manual."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

fields = json.loads((ROOT / "data" / "fields_inventory.json").read_text(encoding="utf-8"))

lines: list[str] = []
for i, f in enumerate(fields):
    name = f["name"].split(".")[-1]  # nombre corto
    opts = f" opt={f['options']}" if f["options"] else ""
    alt = (f["alt"][:120] + "…") if len(f["alt"]) > 120 else f["alt"]
    lines.append(f"{i:3d} [{f['type'] or '?'}] {name}{opts}\n    ~ {alt}")

(ROOT / "data" / "fields_report.txt").write_text("\n".join(lines), encoding="utf-8")
print(f"{len(fields)} campos -> data/fields_report.txt")
