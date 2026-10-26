"""Modelo de datos lógico del Formulario I-589 (edición 07/28/26).

Este esquema es independiente del PDF: la IA extrae hacia esta estructura,
el operador la corrige en la UI y `config/i589_mapping.json` la traduce a
los nombres de campo internos del formulario oficial de USCIS.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Alias(BaseModel):
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""


class Applicant(BaseModel):
    """Parte A.I — Información del solicitante (items 1-25)."""
    a_number: str = ""
    ssn: str = ""
    uscis_account: str = ""
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    aliases: List[Alias] = Field(default_factory=list)
    street: str = ""
    apt: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    phone_area: str = ""
    phone: str = ""
    mailing_in_care_of: str = ""
    mailing_street: str = ""
    mailing_apt: str = ""
    mailing_city: str = ""
    mailing_state: str = ""
    mailing_zip: str = ""
    mailing_phone_area: str = ""
    mailing_phone: str = ""
    gender: str = ""            # "M" | "F" | ""
    marital_status: str = ""    # "single" | "married" | "divorced" | "widowed"
    dob: str = ""               # YYYY-MM-DD
    birth_city_country: str = ""
    nationality: str = ""
    nationality_at_birth: str = ""
    race_ethnic_group: str = ""
    religion: str = ""
    court_status: str = ""      # "never" | "now" | "not_now"
    last_left_country_date: str = ""
    i94_number: str = ""
    entries: List["Entry"] = Field(default_factory=list)  # máx 3, más reciente primero
    passport_country: str = ""
    passport_number: str = ""
    travel_doc_number: str = ""
    passport_expiration: str = ""
    native_language: str = ""
    fluent_english: Optional[bool] = None
    other_languages: str = ""
    cat_withholding: bool = True  # convención contra la tortura: casilla al inicio


class Entry(BaseModel):
    """19.C — Entradas a EE. UU. (más reciente primero)."""
    date: str = ""
    place: str = ""
    status: str = ""
    status_expires: str = ""


class Address(BaseModel):
    """Dirección (A.3.1 / A.3.2): calle, ciudad, provincia, país, fechas."""
    street: str = ""
    city: str = ""
    province: str = ""
    country: str = ""
    from_date: str = ""         # MM/YYYY
    to_date: str = ""           # MM/YYYY o "Presente"


class Spouse(BaseModel):
    """Parte A.II — Cónyuge."""
    not_married: bool = False
    a_number: str = ""
    passport: str = ""
    ssn: str = ""
    dob: str = ""
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    maiden_name: str = ""
    marriage_date: str = ""
    marriage_place: str = ""
    birth_city_country: str = ""
    nationality: str = ""
    race_ethnic_group: str = ""
    gender: str = ""
    in_us: Optional[bool] = None
    location_if_abroad: str = ""
    entry_place: str = ""
    entry_date: str = ""
    i94_number: str = ""
    entry_status: str = ""
    current_status: str = ""
    status_expiration: str = ""
    in_proceedings: Optional[bool] = None
    previous_arrival_date: str = ""
    included_in_application: Optional[bool] = None


class Child(BaseModel):
    """Parte A.II — Hijo(a)."""
    a_number: str = ""
    passport: str = ""
    ssn: str = ""
    marital_status: str = ""
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    dob: str = ""
    birth_city_country: str = ""
    nationality: str = ""
    race_ethnic_group: str = ""
    gender: str = ""
    in_us: Optional[bool] = None
    location_if_abroad: str = ""
    entry_place: str = ""
    entry_date: str = ""
    i94_number: str = ""
    entry_status: str = ""
    current_status: str = ""
    status_expiration: str = ""
    in_proceedings: Optional[bool] = None
    included_in_application: Optional[bool] = None


class Employment(BaseModel):
    """A.3.4 — Empleo de los últimos 5 años."""
    employer: str = ""
    occupation: str = ""
    from_date: str = ""         # MM/YYYY
    to_date: str = ""           # MM/YYYY o "Presente"


class Education(BaseModel):
    """A.3.3 — Educación (más reciente primero)."""
    name: str = ""
    type: str = ""              # primaria/secundaria/universidad/técnica
    location: str = ""
    from_date: str = ""
    to_date: str = ""


class Relative(BaseModel):
    """A.3.5 — Padre/madre/hermano."""
    name: str = ""
    birth_city_country: str = ""
    current_location: str = ""
    deceased: bool = False


class BQuestion(BaseModel):
    """Parte B — pregunta sí/no con explicación."""
    answer: Optional[bool] = None
    explain: str = ""


class Basis(BaseModel):
    """Parte B — Base de la solicitud."""
    race: bool = False
    religion: bool = False
    nationality: bool = False
    political_opinion: bool = False
    social_group: bool = False
    torture: bool = False
    q1a_harm_experienced: BQuestion = Field(default_factory=BQuestion)
    q1b_fear_return: BQuestion = Field(default_factory=BQuestion)
    q2_accused_detained: BQuestion = Field(default_factory=BQuestion)
    q3a_organizations: BQuestion = Field(default_factory=BQuestion)
    q3b_still_participating: BQuestion = Field(default_factory=BQuestion)
    q4_torture_fear: BQuestion = Field(default_factory=BQuestion)


class CQuestion(BaseModel):
    """Parte C — pregunta sí/no con explicación opcional."""
    answer: Optional[bool] = None
    explain: str = ""


class Questions(BaseModel):
    """Parte C — Preguntas de elegibilidad."""
    q1_family_applied: CQuestion = Field(default_factory=CQuestion)
    q2a_traveled_after_leaving: CQuestion = Field(default_factory=CQuestion)
    q2b_other_country_status: CQuestion = Field(default_factory=CQuestion)
    q3_ordered_harm: CQuestion = Field(default_factory=CQuestion)
    q4_returned_to_country: CQuestion = Field(default_factory=CQuestion)
    q5_late_filing: CQuestion = Field(default_factory=CQuestion)
    q6_crime_arrest: CQuestion = Field(default_factory=CQuestion)


class Assistant(BaseModel):
    """Parte D — familiar que ayudó a completar el formulario."""
    name: str = ""
    relationship: str = ""


class Signature(BaseModel):
    """Partes D/E — Firma, asistencia, abogado y preparador."""
    print_name: str = ""
    native_alphabet_name: str = ""
    date: str = ""
    assisted_by_family: Optional[bool] = None
    assistants: List[Assistant] = Field(default_factory=list)
    prepared_by_other: Optional[bool] = None
    counsel_list_provided: Optional[bool] = None
    attorney_check: bool = False
    attorney_bar_number: str = ""
    attorney_uscis_account: str = ""
    # Preparador (Parte E)
    preparer_signature_name: str = ""
    preparer_print_name: str = ""
    preparer_street: str = ""
    preparer_apt: str = ""
    preparer_city: str = ""
    preparer_state: str = ""
    preparer_zip: str = ""
    preparer_phone_area: str = ""
    preparer_phone: str = ""


class I589Data(BaseModel):
    """Estructura completa de datos del I-589."""
    applicant: Applicant = Field(default_factory=Applicant)
    spouse: Optional[Spouse] = None
    has_children: Optional[bool] = None
    total_children: str = ""
    children: List[Child] = Field(default_factory=list)  # máx 6 (4 en forma, 2 en suplemento A)
    addresses_abroad: List[Address] = Field(default_factory=list)   # A.3.1, máx 2
    residences: List[Address] = Field(default_factory=list)         # A.3.2, máx 5
    education: List[Education] = Field(default_factory=list)        # A.3.3, máx 4
    employment: List[Employment] = Field(default_factory=list)      # A.3.4, máx 3
    mother: Relative = Field(default_factory=Relative)
    father: Relative = Field(default_factory=Relative)
    siblings: List[Relative] = Field(default_factory=list)          # A.3.5, máx 4
    basis: Basis = Field(default_factory=Basis)
    questions: Questions = Field(default_factory=Questions)
    signature: Signature = Field(default_factory=Signature)
    narrative: str = ""          # declaración: se vuelca en Suplemento B
    supplement_b_continuation: str = ""  # notas adicionales (Suplemento B)
    source_text: str = ""
    notes: str = ""
