"""Traduce I589Data + mapping a valores de campos y ejecuta pdftk.

Punto crítico del producto: se rellena con `pdftk fill_form` SIN flatten,
de modo que:
- todos los campos quedan editables (requisito de USCIS),
- el JavaScript interno del formulario (código de barras 2D PDF417) sigue
  vivo y Adobe Acrobat lo recalcula al abrir el documento.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from ..normalize import phone_parts, to_month_year, to_us_date
from ..schemas.i589 import I589Data, Spouse
from .xfdf import build_xfdf

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "config" / "i589_mapping.json"
BLANK_PDF = ROOT / "data" / "i-589-open.pdf"
OUTPUT_DIR = ROOT / "outputs"

_GENERO = {
    "m": "M", "masculino": "M", "male": "M", "hombre": "M", "varón": "M", "varon": "M",
    "f": "F", "femenino": "F", "female": "F", "mujer": "F",
}


def _gender(value: str) -> str:
    """Normaliza el sexo a 'M'/'F' desde valores como 'Femenino', 'female', etc."""
    return _GENERO.get((value or "").strip().lower(), "")


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def find_pdftk() -> str:
    """Localiza el ejecutable de pdftk (PATH o instalación de scoop)."""
    explicit = os.getenv("PDFTK_PATH", "").strip()
    if explicit:
        return explicit
    found = shutil.which("pdftk")
    if found:
        return found
    scoop = Path.home() / "scoop" / "shims" / "pdftk.exe"
    if scoop.exists():
        return str(scoop)
    raise RuntimeError(
        "pdftk no está instalado. Ejecuta: scoop install pdftk  (o define PDFTK_PATH en .env)"
    )


def _load_mapping() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _us_date(v: str) -> str:
    return to_us_date(v)


def _my(v: str) -> str:
    return to_month_year(v)


def _text(values: dict, node: dict, value: str) -> None:
    if value is None or not str(value).strip():
        return
    values[node["field"]] = str(value).strip()


def _check(values: dict, node: dict, checked: bool) -> None:
    values[node["field"]] = node["value"] if checked else "Off"


def _set_bool(values: dict, node: dict, value: bool | None) -> None:
    if value is not None:
        _check(values, node, value)


def build_values(data: I589Data) -> dict[str, str]:
    """Convierte I589Data en {campo_completo: valor} listo para XFDF."""
    m = _load_mapping()
    v: dict[str, str] = {}
    a = data.applicant

    # ---------- Parte A.I: solicitante ----------
    ap = m["applicant"]
    for key, fld in [
        ("a_number", a.a_number), ("ssn", a.ssn), ("uscis_account", a.uscis_account),
        ("last_name", a.last_name), ("first_name", a.first_name), ("middle_name", a.middle_name),
        ("street", a.street), ("apt", a.apt), ("city", a.city), ("state", a.state),
        ("zip", a.zip),
    ]:
        _text(v, ap[key], fld)
    _text(v, ap["phone_area"], _digits(a.phone_area))
    _text(v, ap["phone"], _digits(a.phone))
    for key, fld in [
        ("mailing_in_care_of", a.mailing_in_care_of), ("mailing_street", a.mailing_street),
        ("mailing_apt", a.mailing_apt), ("mailing_city", a.mailing_city),
        ("mailing_state", a.mailing_state), ("mailing_zip", a.mailing_zip),
        ("mailing_phone_area", _digits(a.mailing_phone_area)), ("mailing_phone", _digits(a.mailing_phone)),
    ]:
        _text(v, ap[key], fld)

    aliases = "; ".join(
        f"{al.first_name} {al.middle_name} {al.last_name}".replace("  ", " ").strip()
        for al in a.aliases
        if any([al.first_name, al.last_name, al.middle_name])
    )
    _text(v, ap["other_names"], a.other_names.strip() or aliases)

    _check(v, ap["sex_male"], _gender(a.gender) == "M")
    _check(v, ap["sex_female"], _gender(a.gender) == "F")
    _check(v, ap["marital_single"], a.marital_status in ("single", "soltero", "soltera"))
    _check(v, ap["marital_married"], a.marital_status in ("married", "casado", "casada"))
    _check(v, ap["marital_divorced"], a.marital_status in ("divorced", "divorciado", "divorciada"))
    _check(v, ap["marital_widowed"], a.marital_status in ("widowed", "viudo", "viuda"))

    _text(v, ap["dob"], _us_date(a.dob))
    _text(v, ap["birth_city_country"], a.birth_city_country)
    _text(v, ap["nationality"], a.nationality)
    _text(v, ap["nationality_at_birth"], a.nationality_at_birth)
    _text(v, ap["race_ethnic_group"], a.race_ethnic_group)
    _text(v, ap["religion"], a.religion)
    _check(v, ap["court_a_never"], a.court_status in ("never", "nunca", "a"))
    _check(v, ap["court_b_now"], a.court_status in ("now", "actualmente", "b"))
    _check(v, ap["court_c_not_now"], a.court_status in ("not_now", "ya_no", "c"))

    _text(v, ap["last_left_country_date"], _us_date(a.last_left_country_date))
    _text(v, ap["i94_number"], a.i94_number)
    for idx, entry in enumerate(a.entries[:3], 1):
        _text(v, ap[f"entry{idx}_date"], _us_date(entry.date))
        _text(v, ap[f"entry{idx}_place"], entry.place)
        _text(v, ap[f"entry{idx}_status"], entry.status)
        # Solo la entrada más reciente tiene columna "date status expires" en el formulario
        expires_key = f"entry{idx}_status_expires"
        if expires_key in ap:
            _text(v, ap[expires_key], _us_date(entry.status_expires))

    _text(v, ap["passport_country"], a.passport_country)
    _text(v, ap["passport_number"], a.passport_number)
    _text(v, ap["travel_doc_number"], a.travel_doc_number)
    _text(v, ap["passport_expiration"], _us_date(a.passport_expiration))
    _text(v, ap["native_language"], a.native_language)
    if a.fluent_english is not None:
        _check(v, ap["fluent_english_yes"], a.fluent_english)
        _check(v, ap["fluent_english_no"], not a.fluent_english)
    _text(v, ap["other_languages"], a.other_languages)
    _check(v, ap["cat_withholding"], a.cat_withholding)

    # ---------- Parte A.II: cónyuge ----------
    sp = data.spouse
    if sp is not None and not sp.not_married:
        sm = m["spouse"]
        for key, fld in [
            ("a_number", sp.a_number), ("passport", sp.passport), ("ssn", sp.ssn),
            ("last_name", sp.last_name), ("first_name", sp.first_name), ("middle_name", sp.middle_name),
            ("maiden_name", sp.maiden_name), ("marriage_place", sp.marriage_place),
            ("birth_city_country", sp.birth_city_country), ("nationality", sp.nationality),
            ("race_ethnic_group", sp.race_ethnic_group),
            ("location_if_abroad", sp.location_if_abroad),
            ("entry_place", sp.entry_place), ("i94_number", sp.i94_number),
            ("entry_status", sp.entry_status), ("current_status", sp.current_status),
        ]:
            _text(v, sm[key], fld)
        _text(v, sm["dob"], _us_date(sp.dob))
        _text(v, sm["marriage_date"], _us_date(sp.marriage_date))
        _text(v, sm["entry_date"], _us_date(sp.entry_date))
        _text(v, sm["status_expiration"], _us_date(sp.status_expiration))
        _text(v, sm["previous_arrival_date"], _us_date(sp.previous_arrival_date))
        _check(v, sm["sex_male"], _gender(sp.gender) == "M")
        _check(v, sm["sex_female"], _gender(sp.gender) == "F")
        if sp.in_us is not None:
            _check(v, sm["in_us_yes"], sp.in_us)
            _check(v, sm["in_us_no"], not sp.in_us)
        _set_bool(v, sm["proceedings_yes"], sp.in_proceedings)
        _set_bool(v, sm["proceedings_no"], sp.in_proceedings)
        _set_bool(v, sm["included_yes"], sp.included_in_application)
        _set_bool(v, sm["included_no"], sp.included_in_application)
    elif sp is not None and sp.not_married:
        _check(v, m["spouse"]["not_married"], True)

    # ---------- Hijos ----------
    if data.has_children is not None:
        _check(v, m["children_flag"]["has_children"], data.has_children)
        _check(v, m["children_flag"]["no_children"], not data.has_children)
    total = data.total_children.strip() or (
        str(len(data.children)) if data.children else ("0" if data.has_children is False else "")
    )
    _text(v, m["children_flag"]["total"], total)
    for idx, ch in enumerate(data.children[:6], 1):
        cm = m["children"][str(idx)]
        for key, fld in [
            ("a_number", ch.a_number), ("passport", ch.passport), ("ssn", ch.ssn),
            ("marital_status", ch.marital_status), ("last_name", ch.last_name),
            ("first_name", ch.first_name), ("middle_name", ch.middle_name),
            ("birth_city_country", ch.birth_city_country), ("nationality", ch.nationality),
            ("race_ethnic_group", ch.race_ethnic_group),
            ("location_if_abroad", ch.location_if_abroad),
            ("entry_place", ch.entry_place), ("i94_number", ch.i94_number),
            ("entry_status", ch.entry_status), ("current_status", ch.current_status),
        ]:
            _text(v, cm[key], fld)
        _text(v, cm["dob"], _us_date(ch.dob))
        _text(v, cm["entry_date"], _us_date(ch.entry_date))
        _text(v, cm["status_expiration"], _us_date(ch.status_expiration))
        _check(v, cm["sex_male"], _gender(ch.gender) == "M")
        _check(v, cm["sex_female"], _gender(ch.gender) == "F")
        if ch.in_us is not None:
            _check(v, cm["in_us_yes"], ch.in_us)
            _check(v, cm["in_us_no"], not ch.in_us)
        _set_bool(v, cm["proceedings_yes"], ch.in_proceedings)
        _set_bool(v, cm["proceedings_no"], ch.in_proceedings)
        _set_bool(v, cm["included_yes"], ch.included_in_application)
        _set_bool(v, cm["included_no"], ch.included_in_application)

    # ---------- Parte A.III: antecedentes ----------
    for idx, addr in enumerate(data.addresses_abroad[:2], 1):
        am = m["addresses_abroad"][str(idx)]
        _text(v, am["street"], addr.street)
        _text(v, am["city"], addr.city)
        _text(v, am["province"], addr.province)
        _text(v, am["country"], addr.country)
        _text(v, am["from"], _my(addr.from_date))
        _text(v, am["to"], _my(addr.to_date))

    for idx, addr in enumerate(data.residences[:5], 1):
        rm = m["residences"][str(idx)]
        _text(v, rm["street"], addr.street)
        _text(v, rm["city"], addr.city)
        _text(v, rm["province"], addr.province)
        _text(v, rm["country"], addr.country)
        _text(v, rm["from"], _my(addr.from_date))
        _text(v, rm["to"], _my(addr.to_date))

    for idx, edu in enumerate(data.education[:4], 1):
        em = m["education"][str(idx)]
        _text(v, em["name"], edu.name)
        _text(v, em["type"], edu.type)
        _text(v, em["location"], edu.location)
        _text(v, em["from"], _my(edu.from_date))
        _text(v, em["to"], _my(edu.to_date))

    for idx, job in enumerate(data.employment[:3], 1):
        jm = m["employment"][str(idx)]
        _text(v, jm["employer"], job.employer)
        _text(v, jm["occupation"], job.occupation)
        _text(v, jm["from"], _my(job.from_date))
        _text(v, jm["to"], _my(job.to_date))

    for who, rel in (("mother", data.mother), ("father", data.father)):
        rm = m["relatives"][who]
        _text(v, rm["name"], rel.name)
        _text(v, rm["birth_city_country"], rel.birth_city_country)
        _text(v, rm["current_location"], rel.current_location)
        _check(v, rm["deceased"], rel.deceased)
    for idx, sib in enumerate(data.siblings[:4], 1):
        rm = m["relatives"]["siblings"][str(idx)]
        _text(v, rm["name"], sib.name)
        _text(v, rm["birth_city_country"], sib.birth_city_country)
        _text(v, rm["current_location"], sib.current_location)
        _check(v, rm["deceased"], sib.deceased)

    # ---------- Parte B: base y preguntas ----------
    for key in ("race", "religion", "nationality", "political_opinion", "social_group", "torture"):
        _check(v, m["basis"][key], bool(getattr(data.basis, key)))

    bmap = {
        "1a": data.basis.q1a_harm_experienced,
        "1b": data.basis.q1b_fear_return,
        "2": data.basis.q2_accused_detained,
        "3a": data.basis.q3a_organizations,
        "3b": data.basis.q3b_still_participating,
        "4": data.basis.q4_torture_fear,
    }
    for key, q in bmap.items():
        qm = m["b_questions"][key]
        if q.answer is not None:
            _check(v, qm["yes"], q.answer)
            _check(v, qm["no"], not q.answer)
        _text(v, qm["explain"], q.explain)

    cmap = {
        "1": data.questions.q1_family_applied,
        "2a": data.questions.q2a_traveled_after_leaving,
        "2b": data.questions.q2b_other_country_status,
        "3": data.questions.q3_ordered_harm,
        "4": data.questions.q4_returned_to_country,
        "5": data.questions.q5_late_filing,
        "6": data.questions.q6_crime_arrest,
    }
    # El formulario usa UNA sola caja de explicación para 2A y 2B: se concatenan.
    q2_shared = " ".join(
        t for t in (
            data.questions.q2a_traveled_after_leaving.explain.strip(),
            data.questions.q2b_other_country_status.explain.strip(),
        ) if t
    )
    for key, q in cmap.items():
        qm = m["c_questions"][key]
        if q.answer is not None:
            _check(v, qm["yes"], q.answer)
            _check(v, qm["no"], not q.answer)
        if key == "2b":
            _text(v, qm["explain"], q2_shared)
        elif "explain" in qm:
            _text(v, qm["explain"], q.explain)

    # ---------- Partes D/E: firma y preparador ----------
    sg = data.signature
    sm = m["signature"]
    _text(v, sm["print_name"], sg.print_name)
    _text(v, sm["native_alphabet_name"], sg.native_alphabet_name)
    _text(v, sm["date"], _us_date(sg.date) or date.today().strftime("%m/%d/%Y"))
    _set_bool(v, sm["assisted_yes"], sg.assisted_by_family)
    _set_bool(v, sm["assisted_no"], sg.assisted_by_family)
    for i, assist in enumerate(sg.assistants[:2], 1):
        _text(v, sm[f"assistant{i}_name"], assist.name)
        _text(v, sm[f"assistant{i}_relationship"], assist.relationship)
    _set_bool(v, sm["prepared_by_other_yes"], sg.prepared_by_other)
    _set_bool(v, sm["prepared_by_other_no"], sg.prepared_by_other)
    _set_bool(v, sm["counsel_list_yes"], sg.counsel_list_provided)
    _set_bool(v, sm["counsel_list_no"], sg.counsel_list_provided)
    _check(v, sm["attorney_check"], sg.attorney_check)
    _text(v, sm["attorney_bar_number"], sg.attorney_bar_number)
    _text(v, sm["attorney_uscis_account"], sg.attorney_uscis_account)

    if sg.preparer_print_name:
        pm = m["preparer"]
        _text(v, pm["print_name"], sg.preparer_print_name)
        _text(v, pm["street"], sg.preparer_street)
        _text(v, pm["apt"], sg.preparer_apt)
        _text(v, pm["city"], sg.preparer_city)
        _text(v, pm["state"], sg.preparer_state)
        _text(v, pm["zip"], sg.preparer_zip)
        _text(v, pm["phone_area"], sg.preparer_phone_area)
        _text(v, pm["phone"], _digits(sg.preparer_phone))

    # ---------- Suplementos ----------
    full_name = f"{a.first_name} {a.middle_name} {a.last_name}".replace("  ", " ").strip()
    sa = m["supplement_a"]
    _text(v, sa["a_number"], a.a_number)
    _text(v, sa["applicant_name"], full_name)
    _text(v, sa["date"], date.today().strftime("%m/%d/%Y"))
    sb = m["supplement_b"]
    _text(v, sb["a_number"], a.a_number)
    _text(v, sb["applicant_name"], full_name)
    _text(v, sb["date"], date.today().strftime("%m/%d/%Y"))
    # Narrativa: un solo campo multilínea grande (Suplemento B). Si excede el espacio,
    # la validación advierte para adjuntar páginas adicionales (no se trunca en silencio).
    narrative_text = data.narrative.strip()
    if data.supplement_b_continuation.strip():
        narrative_text = (narrative_text + "\n\n" + data.supplement_b_continuation.strip()).strip()
    _text(v, sb["continuation"], narrative_text)

    return v


def fill_pdf(data: I589Data, case_id: str, case_name: str = "") -> Path:
    """Genera el PDF rellenado (sin flatten) y devuelve su ruta."""
    if not BLANK_PDF.exists():
        raise RuntimeError(
            "Falta el formulario en blanco. Ejecuta scripts/setup.py para descargarlo."
        )
    values = build_values(data)
    xfdf = build_xfdf(values)
    OUTPUT_DIR.mkdir(exist_ok=True)
    safe = "".join(c for c in case_name if c.isalnum() or c in " -_").strip() or "caso"
    out_path = OUTPUT_DIR / f"i589_{safe}_{case_id[:8]}.pdf"

    with tempfile.NamedTemporaryFile("w", suffix=".xfdf", delete=False, encoding="utf-8") as fh:
        fh.write(xfdf)
        xfdf_path = fh.name
    try:
        cmd = [
            find_pdftk(),
            str(BLANK_PDF),
            "fill_form",
            xfdf_path,
            "output",
            str(out_path),
            # El I-589 oficial es un PDF híbrido XFA+AcroForm. Sin esta opción,
            # Adobe Acrobat prioriza la capa XFA (vacía) y muestra el formulario
            # como si no se hubiera rellenado. drop_xfa elimina esa capa y deja
            # el AcroForm rellenado visible en todos los visores.
            "drop_xfa",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"pdftk falló: {proc.stderr.strip()[:800]}")
    finally:
        os.unlink(xfdf_path)
    return out_path


def verify_filled(pdf_path: Path, expected_field: str, expected_value: str) -> bool:
    """Verifica que el PDF generado contiene un valor esperado (post-fill check)."""
    try:
        proc = subprocess.run(
            [find_pdftk(), str(pdf_path), "dump_data_fields_utf8"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            return False
        dump = proc.stdout
        lines = dump.splitlines()
        for i, line in enumerate(lines):
            if line.strip() == f"FieldName: {expected_field}":
                for j in range(i + 1, min(i + 12, len(lines))):
                    if lines[j].startswith("FieldValue:"):
                        return lines[j].split(":", 1)[1].strip() == expected_value
        return False
    except Exception:
        return False
