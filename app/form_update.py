"""Detección de edición nueva del formulario I-589 publicado por USCIS.

Compara la edición local (data/i-589-open.pdf) con la última publicada en
uscis.gov. El resultado se cachea en data/form_status.json para no descargar
el PDF en cada vuelta (vigencia: 12 horas).
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
BLANK_PDF = ROOT / "data" / "i-589-open.pdf"
STATUS_FILE = ROOT / "data" / "form_status.json"
FORM_URL = "https://www.uscis.gov/sites/default/files/document/forms/i-589.pdf"
CACHE_HOURS = 12
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_EDITION_RE = re.compile(r"Edition\s+(\d{1,2}/\d{1,2}/\d{2,4})")


def fetch_form_bytes(url: str = FORM_URL) -> bytes:
    """Descarga el PDF oficial. El WAF de USCIS bloquea el TLS de Python,
    así que se usa curl cuando está disponible (Windows 10+ lo incluye)."""
    curl = shutil.which("curl")
    if curl:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            tmp = Path(fh.name)
        try:
            proc = subprocess.run(
                [curl, "-sSL", "--max-time", "120", "-A", _UA, "-o", str(tmp), url],
                capture_output=True,
            )
            if proc.returncode == 0 and tmp.exists() and tmp.stat().st_size > 10_000:
                return tmp.read_bytes()
        finally:
            tmp.unlink(missing_ok=True)
    req = urllib.request.Request(
        url, headers={"User-Agent": _UA, "Accept": "application/pdf,*/*"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def extract_edition(pdf_path: Path) -> str:
    """Lee la fecha de edición impresa en el pie del formulario (ej. 07/28/26)."""
    try:
        doc = pymupdf.open(str(pdf_path))
        try:
            for page in doc:
                m = _EDITION_RE.search(page.get_text())
                if m:
                    return m.group(1)
        finally:
            doc.close()
    except Exception:
        pass
    return ""


def local_info() -> dict:
    if not BLANK_PDF.exists():
        return {"edition": "", "sha256": ""}
    raw = BLANK_PDF.read_bytes()
    return {"edition": extract_edition(BLANK_PDF), "sha256": hashlib.sha256(raw).hexdigest()}


def _load_status() -> dict:
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_status(status: dict) -> None:
    STATUS_FILE.parent.mkdir(exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")


def _fresh(checked_at: str, estado: str) -> bool:
    # Un fallo de verificación se reintenta pronto (30 min); un resultado válido dura 12 h.
    hours = CACHE_HOURS if estado != "sin_verificar" else 0.5
    try:
        dt = datetime.fromisoformat(checked_at)
        return datetime.now(timezone.utc) - dt < timedelta(hours=hours)
    except Exception:
        return False


def check_status(force: bool = False) -> dict:
    """Devuelve {edition, estado, remote_edition, checked_at, message}.

    estado: 'actualizado' | 'disponible' | 'sin_verificar'
    """
    local = local_info()
    cached = _load_status()
    if (
        cached
        and cached.get("local_edition") == local["edition"]
        and cached.get("local_sha256") == local["sha256"]
        and not force
        and _fresh(cached.get("checked_at", ""), cached.get("estado", ""))
    ):
        return _public(cached)

    status = {
        "local_edition": local["edition"],
        "local_sha256": local["sha256"],
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "remote_edition": "",
        "remote_sha256": "",
        "estado": "sin_verificar",
        "message": "No se pudo verificar la última edición en uscis.gov",
    }
    try:
        raw = fetch_form_bytes()
        status["remote_sha256"] = hashlib.sha256(raw).hexdigest()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(raw)
            tmp = Path(fh.name)
        try:
            status["remote_edition"] = extract_edition(tmp)
        finally:
            tmp.unlink(missing_ok=True)

        if status["remote_edition"] and status["remote_edition"] == local["edition"]:
            status["estado"] = "actualizado"
            status["message"] = f"Formulario actualizado (edición {local['edition']})"
        elif status["remote_edition"]:
            status["estado"] = "disponible"
            status["message"] = (
                f"Hay una edición nueva del I-589: {status['remote_edition']} "
                f"(tienes {local['edition']}). Ejecuta scripts/update_form.py"
            )
        else:
            # Sin fecha legible: comparar por hash
            status["estado"] = "actualizado" if status["remote_sha256"] == local["sha256"] else "disponible"
            status["message"] = (
                "El formulario coincide con la última publicación"
                if status["estado"] == "actualizado"
                else "El PDF publicado por USCIS cambió; ejecuta scripts/update_form.py"
            )
    except Exception as exc:  # red caída, sitio inaccesible, etc.
        status["message"] = f"No se pudo verificar la última edición: {exc}"

    _save_status(status)
    return _public(status)


def _public(status: dict) -> dict:
    return {
        "edition": status.get("local_edition", ""),
        "estado": status.get("estado", "sin_verificar"),
        "remote_edition": status.get("remote_edition", ""),
        "checked_at": status.get("checked_at", ""),
        "message": status.get("message", ""),
    }


def collect_mapping_fields(mapping: dict) -> dict[str, str]:
    """Devuelve {nombre_completo_de_campo: ruta_lógica} para todo el mapeo."""
    out: dict[str, str] = {}

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            field = node.get("field")
            if isinstance(field, str):
                out[field] = path
                return
            for key, value in node.items():
                if key == "meta":
                    continue
                walk(value, f"{path}.{key}" if path else key)
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")

    walk(mapping, "")
    return out


def compare_inventories(
    old: list[dict],
    new: list[dict],
    mapping_fields: dict[str, str],
) -> dict:
    """Compara inventarios de campos y detecta qué mapeo se rompería."""
    old_names = {f["name"] for f in old}
    new_names = {f["name"] for f in new}
    added = [
        {"name": f["name"], "alt": f.get("alt", "")}
        for f in new if f["name"] not in old_names
    ]
    removed = [
        {"name": f["name"], "alt": f.get("alt", "")}
        for f in old if f["name"] not in new_names
    ]
    affected = sorted(
        (
            {"logical": logical, "field": field}
            for field, logical in mapping_fields.items()
            if field not in new_names
        ),
        key=lambda item: item["logical"],
    )
    return {
        "count_old": len(old),
        "count_new": len(new),
        "added": added,
        "removed": removed,
        "affected": affected,
        "compatible": not affected,
    }
