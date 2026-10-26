"""Persistencia local de casos en SQLite (stdlib, sin dependencias)."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "casos.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS casos (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL DEFAULT '',
                texto_fuente TEXT NOT NULL DEFAULT '',
                datos_json TEXT NOT NULL DEFAULT '{}',
                estado TEXT NOT NULL DEFAULT 'borrador',
                creado TEXT NOT NULL,
                actualizado TEXT NOT NULL
            )
            """
        )


def create_case(nombre: str, texto: str = "") -> dict:
    case = {
        "id": uuid.uuid4().hex,
        "nombre": nombre.strip(),
        "texto_fuente": texto,
        "datos_json": "{}",
        "estado": "borrador",
        "creado": _now(),
        "actualizado": _now(),
    }
    with _conn() as conn:
        conn.execute(
            "INSERT INTO casos (id, nombre, texto_fuente, datos_json, estado, creado, actualizado) "
            "VALUES (:id, :nombre, :texto_fuente, :datos_json, :estado, :creado, :actualizado)",
            case,
        )
    return case


def list_cases() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, nombre, estado, creado, actualizado FROM casos ORDER BY actualizado DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_case(case_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM casos WHERE id = ?", (case_id,)).fetchone()
    return dict(row) if row else None


def save_data(case_id: str, datos: dict) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE casos SET datos_json = ?, actualizado = ?, estado = 'con_datos' WHERE id = ?",
            (json.dumps(datos, ensure_ascii=False), _now(), case_id),
        )


def save_text(case_id: str, texto: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE casos SET texto_fuente = ?, actualizado = ? WHERE id = ?",
            (texto, _now(), case_id),
        )


def rename_case(case_id: str, nombre: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE casos SET nombre = ?, actualizado = ? WHERE id = ?",
            (nombre.strip(), _now(), case_id),
        )


def delete_case(case_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM casos WHERE id = ?", (case_id,))
