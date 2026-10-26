"""Validación del I589Data antes de generar el PDF.

Devuelve errores bloqueantes (datos críticos ausentes) y advertencias
(campos recomendados vacíos). Todo en español, listo para la UI.
"""
from __future__ import annotations

from pydantic import BaseModel

from .normalize import to_us_date
from .schemas.i589 import I589Data


class ValidationResult(BaseModel):
    ok: bool
    errors: list[str] = []
    warnings: list[str] = []


def validate(data: I589Data) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    a = data.applicant

    def crit(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(msg)

    def warn(cond: bool, msg: str) -> None:
        if not cond:
            warnings.append(msg)

    # --- Críticos: bloquean la generación del PDF ---
    crit(bool(a.last_name), "Apellido del solicitante (Parte A.I, ítem 4)")
    crit(bool(a.first_name), "Nombre del solicitante (Parte A.I, ítem 5)")
    crit(bool(a.dob), "Fecha de nacimiento (Parte A.I, ítem 12)")
    if a.dob and not to_us_date(a.dob):
        errors.append("La fecha de nacimiento no es una fecha válida (usa MM/DD/YYYY o AAAA-MM-DD)")
    crit(bool(a.nationality), "Nacionalidad actual (Parte A.I, ítem 14)")
    crit(bool(a.birth_city_country), "Ciudad y país de nacimiento (Parte A.I, ítem 13)")
    crit(bool(a.street and a.city), "Dirección actual en EE. UU. (Parte A.I, ítem 8)")
    valid_residences = [r for r in data.residences if r.street.strip() and r.city.strip()]
    crit(
        bool(valid_residences),
        "Al menos una dirección de residencia con calle y ciudad de los últimos 5 años (Parte A.III, ítem 2)",
    )
    crit(
        any([data.basis.race, data.basis.religion, data.basis.nationality,
             data.basis.political_opinion, data.basis.social_group, data.basis.torture]),
        "Al menos un motivo de la solicitud de asilo (Parte B, ítem 1)",
    )
    narrative = (data.narrative + "\n" + data.supplement_b_continuation).strip()
    crit(bool(narrative), "Declaración/narrativa de persecución (necesaria para la solicitud de asilo)")

    # --- Advertencias: no bloquean, pero conviene completar ---
    warn(bool(a.race_ethnic_group), "Grupo racial/étnico o tribal (A.I, ítem 16)")
    warn(bool(a.religion), "Religión (A.I, ítem 17)")
    warn(bool(a.gender), "Sexo (A.I, ítem 10)")
    warn(bool(a.marital_status), "Estado civil (A.I, ítem 11)")
    warn(bool(a.native_language), "Idioma nativo (A.I, ítem 23)")

    spouse_has_data = data.spouse is not None and any(
        [data.spouse.last_name, data.spouse.first_name, data.spouse.middle_name,
         data.spouse.dob, data.spouse.not_married]
    )
    if spouse_has_data and not data.spouse.not_married:
        if not (data.spouse.last_name and data.spouse.dob):
            warnings.append("Cónyuge: faltan apellido o fecha de nacimiento (Parte A.II)")
    if data.has_children and not data.children:
        warnings.append("Indica que tiene hijos pero no hay datos de ninguno (Parte A.II)")
    if data.has_children is False and data.children:
        warnings.append("Marcaste «sin hijos» pero hay hijos cargados: corrige una de las dos opciones (Parte A.II)")
    if data.has_children is None and data.children:
        warnings.append("Hay hijos cargados: marca «¿Tiene hijos?» en la pestaña Familia")
    for i, ch in enumerate(data.children[:6], 1):
        if not ch.last_name or not ch.dob:
            warnings.append(f"Hijo {i}: faltan apellido o fecha de nacimiento (Parte A.II)")
    if len(narrative) > 3000:
        warnings.append(
            "La narrativa supera ~3.000 caracteres: el Suplemento B podría no mostrarla completa. "
            "Adjunta páginas adicionales al formulario."
        )
    if not data.signature.print_name:
        warnings.append("Nombre impreso en la firma (Parte D)")

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)
