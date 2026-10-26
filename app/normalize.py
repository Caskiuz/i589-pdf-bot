"""Normalización de fechas a los formatos del formulario (MM/DD/YYYY y MM/YYYY)."""
from __future__ import annotations

import re

_MESES = {
    "ene": 1, "jan": 1, "feb": 2, "mar": 3, "abr": 4, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "ago": 8, "aug": 8, "sep": 9,
    "set": 9, "oct": 10, "nov": 11, "dic": 12, "dec": 12,
}


def _parse_mes(token: str) -> int | None:
    t = token.lower()[:3]
    return _MESES.get(t)


def to_us_date(value: str) -> str:
    """Convierte a MM/DD/YYYY. Acepta YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY,
    '15 de marzo de 1990', '15/mar/90', etc. Devuelve '' si no es fecha."""
    v = (value or "").strip().lower().replace(",", " ").replace(".", " ")
    if not v:
        return ""
    v = re.sub(r"\bde\b|\bdel\b", " ", v)
    v = re.sub(r"\s+", " ", v).strip()

    # ISO: YYYY-MM-DD
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", v)
    if m:
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
        return f"{mo:02d}/{d:02d}/{y:04d}" if 1 <= mo <= 12 and 1 <= d <= 31 else ""

    # Numérico con separadores
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", v)
    if m:
        a, b, c = int(m[1]), int(m[2]), int(m[3])
        if c < 100:
            c += 2000 if c < 50 else 1900
        # MM/DD/YYYY
        if 1 <= a <= 12 and 1 <= b <= 31:
            return f"{a:02d}/{b:02d}/{c:04d}"
        # DD/MM/YYYY (si el primer número > 12)
        if 1 <= b <= 12 and 1 <= a <= 31:
            return f"{b:02d}/{a:02d}/{c:04d}"
        return ""

    # Texto: "15 marzo 1990" / "marzo 15 1990" / "15 de marzo del 90"
    m = re.search(r"(\d{1,2})?\s*([a-záéíóúñ]{3,9})\s+(\d{1,2})?\s*(\d{2,4})?", v)
    if m:
        dia = int(m[1]) if m[1] else None
        mes = _parse_mes(m[2] or "")
        if mes:
            dia2 = int(m[3]) if m[3] else None
            anio = int(m[4]) if m[4] else None
            d = dia or dia2 or 1
            if anio:
                if anio < 100:
                    anio += 2000 if anio < 50 else 1900
                if 1 <= d <= 31:
                    return f"{mes:02d}/{d:02d}/{anio:04d}"
    return ""


def to_month_year(value: str) -> str:
    """Convierte a MM/YYYY. Acepta '03/2024', 'marzo 2024', '03/24', '2024-03'.
    'Presente'/'Actual'/'Hoy' se devuelven como 'Present'."""
    v = (value or "").strip().lower().replace(",", " ").replace(".", " ")
    if not v:
        return ""
    if v in {"presente", "present", "actual", "actualidad", "hoy", "now", "current"}:
        return "Present"
    v = re.sub(r"\bde\b|\bdel\b", " ", v)
    v = re.sub(r"\s+", " ", v).strip()

    m = re.fullmatch(r"(\d{4})-(\d{1,2})", v)
    if m:
        y, mo = int(m[1]), int(m[2])
        return f"{mo:02d}/{y:04d}" if 1 <= mo <= 12 else ""

    m = re.fullmatch(r"(\d{1,2})[/-](\d{2,4})", v)
    if m:
        mo, y = int(m[1]), int(m[2])
        if y < 100:
            y += 2000 if y < 50 else 1900
        return f"{mo:02d}/{y:04d}" if 1 <= mo <= 12 else ""

    m = re.search(r"([a-záéíóúñ]{3,9})\s*[de]?\s*(\d{2,4})", v)
    if m:
        mes = _parse_mes(m[1] or "")
        if mes:
            y = int(m[2])
            if y < 100:
                y += 2000 if y < 50 else 1900
            return f"{mes:02d}/{y:04d}"
    return ""


def phone_parts(phone: str) -> tuple[str, str]:
    """Separa un teléfono en (código de área, número de 7 dígitos)."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) >= 10:
        return digits[-10:-7], digits[-7:]
    if len(digits) == 7:
        return "", digits
    return "", ""
