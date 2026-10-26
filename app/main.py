"""FastAPI: API REST + frontend estático del I-589 PDF Bot."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db
from . import form_update
from .ai.client import DeepSeekConfigError, ai_available
from .ai.extractor import extract_all
from .pdf.filler import BLANK_PDF, OUTPUT_DIR, fill_pdf, find_pdftk, verify_filled
from .schemas.i589 import I589Data
from .validation import validate

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="I-589 PDF Bot", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


# ---------------- Modelos de petición ----------------

class CreateCaseReq(BaseModel):
    nombre: str = ""
    texto: str = ""


class ExtractReq(BaseModel):
    texto: str


# ---------------- API ----------------

@app.get("/api/health")
def health() -> dict:
    local = form_update.local_info()
    return {
        "ok": True,
        "ia": ai_available(),
        "pdftk": bool(find_pdftk() if _pdftk_safe() else False),
        "formulario": BLANK_PDF.exists(),
        "formulario_edicion": local["edition"],
    }


@app.get("/api/formulario/estado")
def formulario_estado(force: bool = False) -> dict:
    """Compara la edición local con la última publicada por USCIS (cache 12 h)."""
    return form_update.check_status(force=force)


def _pdftk_safe() -> bool:
    try:
        return bool(find_pdftk())
    except Exception:
        return False


@app.get("/api/casos")
def casos() -> list[dict]:
    return db.list_cases()


@app.post("/api/casos")
def crear_caso(req: CreateCaseReq) -> dict:
    return db.create_case(req.nombre, req.texto)


@app.get("/api/casos/{case_id}")
def obtener_caso(case_id: str) -> dict:
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(404, "Caso no encontrado")
    return case


@app.put("/api/casos/{case_id}/datos")
def guardar_datos(case_id: str, payload: dict) -> dict:
    """Guarda el I589Data (validado con Pydantic) del caso."""
    if db.get_case(case_id) is None:
        raise HTTPException(404, "Caso no encontrado")
    try:
        data = I589Data.model_validate(payload)
    except Exception as exc:
        raise HTTPException(400, f"Datos inválidos: {exc}") from exc
    db.save_data(case_id, data.model_dump())
    return {"ok": True}


@app.put("/api/casos/{case_id}")
def renombrar_caso(case_id: str, payload: dict) -> dict:
    if db.get_case(case_id) is None:
        raise HTTPException(404, "Caso no encontrado")
    db.rename_case(case_id, str(payload.get("nombre", "")))
    return {"ok": True}


@app.put("/api/casos/{case_id}/texto")
def guardar_texto(case_id: str, payload: dict) -> dict:
    if db.get_case(case_id) is None:
        raise HTTPException(404, "Caso no encontrado")
    db.save_text(case_id, str(payload.get("texto", "")))
    return {"ok": True}


@app.delete("/api/casos/{case_id}")
def eliminar_caso(case_id: str) -> dict:
    if db.get_case(case_id) is None:
        raise HTTPException(404, "Caso no encontrado")
    db.delete_case(case_id)
    return {"ok": True}


@app.post("/api/casos/{case_id}/extraer")
def extraer(case_id: str, req: ExtractReq) -> dict:
    """Extrae los datos con DeepSeek y los guarda en el caso."""
    if db.get_case(case_id) is None:
        raise HTTPException(404, "Caso no encontrado")
    try:
        data = extract_all(req.texto)
    except DeepSeekConfigError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        log.exception("extracción fallida")
        raise HTTPException(502, f"La extracción con IA falló: {exc}") from exc
    db.save_text(case_id, req.texto)
    db.save_data(case_id, data.model_dump())
    return {"ok": True, "datos": data.model_dump()}


@app.post("/api/casos/{case_id}/validar")
def validar(case_id: str, payload: dict) -> dict:
    try:
        data = I589Data.model_validate(payload)
    except Exception as exc:
        raise HTTPException(400, f"Datos inválidos: {exc}") from exc
    result = validate(data)
    return result.model_dump()


@app.post("/api/casos/{case_id}/generar")
def generar(case_id: str, payload: dict) -> dict:
    """Valida y genera el PDF (sin flatten). Bloquea si hay errores críticos."""
    case = db.get_case(case_id)
    if case is None:
        raise HTTPException(404, "Caso no encontrado")
    try:
        data = I589Data.model_validate(payload)
    except Exception as exc:
        raise HTTPException(400, f"Datos inválidos: {exc}") from exc

    result = validate(data)
    if not result.ok:
        return {"ok": False, "errores": result.errors, "advertencias": result.warnings}

    try:
        out = fill_pdf(data, case_id, case["nombre"])
    except Exception as exc:
        log.exception("generación fallida")
        raise HTTPException(500, f"Error al generar el PDF: {exc}") from exc

    # Verificación post-fill: el apellido debe estar en el PDF resultante
    verified = verify_filled(out, "form1[0].#subform[0].PtAILine4_LastName[0]", data.applicant.last_name)
    db.save_data(case_id, data.model_dump())
    return {
        "ok": True,
        "pdf": f"/descargar/{out.name}",
        "nombre_archivo": out.name,
        "verificado": verified,
        "advertencias": result.warnings,
        "nota_barcode": (
            "Abre el PDF en Adobe Acrobat Reader para revisarlo. El código de barras 2D "
            "ya viene incluido en el formulario oficial y se conserva intacto; los datos "
            "se muestran correctamente en Acrobat y en los demás visores."
        ),
    }


@app.get("/descargar/{filename}")
def descargar(filename: str) -> FileResponse:
    path = (OUTPUT_DIR / filename).resolve()
    if not path.is_file() or path.parent != OUTPUT_DIR.resolve():
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(path, filename=filename, media_type="application/pdf")


# ---------------- Frontend ----------------

app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "app" / "static" / "index.html")
