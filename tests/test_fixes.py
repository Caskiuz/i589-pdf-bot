"""Pruebas de la auditoría de campos: normalización, narrativa, familia y validación."""
import json
from pathlib import Path

import pytest

from app.pdf.filler import BLANK_PDF, build_values, fill_pdf, find_pdftk, verify_filled
from app.schemas.i589 import Applicant, Child, I589Data, Spouse
from app.validation import validate

FIXTURES = Path(__file__).parent / "fixtures"
CASO = FIXTURES / "caso_completo.json"
FAMILIA = FIXTURES / "caso_familia.json"

pdftk_missing = False
try:
    find_pdftk()
except RuntimeError:
    pdftk_missing = True


def load(path: Path) -> I589Data:
    return I589Data.model_validate(json.loads(path.read_text(encoding="utf-8")))


# ---------------- Normalización de códigos ----------------

def test_normaliza_sexo_estado_civil_y_corte():
    a = Applicant(
        gender="Femenino",
        marital_status="Soltera",
        court_status="Nunca he estado en corte de inmigración",
    )
    assert (a.gender, a.marital_status, a.court_status) == ("F", "single", "never")

    b = Applicant(gender="male", marital_status="casada", court_status="Ya no estoy en corte")
    assert (b.gender, b.marital_status, b.court_status) == ("M", "married", "not_now")

    assert Spouse(gender="Femenino").gender == "F"
    ch = Child(gender="Masculino", marital_status="Soltero")
    assert (ch.gender, ch.marital_status) == ("M", "single")


# ---------------- Mapeo de campos ----------------

def test_narrativa_en_campo_grande_suplemento_b():
    data = load(CASO)
    v = build_values(data)
    grande = "form1[0].#subform[13].TextField32[0]"
    assert v[grande].startswith("I am María Fernanda")
    assert not any("TextField31" in k for k in v), "no debe escribir en las casillas de correcciones"


def test_narrativa_larga_no_se_trunca():
    data = load(CASO)
    data.narrative = "A" * 4000
    v = build_values(data)
    assert len(v["form1[0].#subform[13].TextField32[0]"]) == 4000


def test_explicacion_c2a_c2b_combinada():
    data = load(FAMILIA)
    data.questions.q2b_other_country_status.explain = "No other country granted me status."
    v = build_values(data)
    explicacion = v["form1[0].#subform[8].PCL2B_TextField[0]"]
    assert "traveled through Colombia" in explicacion
    assert "No other country" in explicacion


def test_total_hijos_cero_cuando_no_tiene():
    data = load(CASO)
    v = build_values(data)
    assert v["form1[0].#subform[1].TotalChild[0]"] == "0"


def test_familia_completa_mapea_conyuge_hijos_y_suplemento_a():
    data = load(FAMILIA)
    v = build_values(data)
    assert v["form1[0].#subform[1].NotMarried[0].PtAIILine5_LastName[0]"] == "Torres"  # cónyuge
    assert v["form1[0].#subform[1].ChildLast1[0]"] == "García Torres"           # hijo 1
    assert v["form1[0].#subform[12].TextField12[0]"] == "García Torres"         # hijo 5 (Suplemento A)
    assert v["form1[0].#subform[12].TextField12[10]"] == "García Torres"        # hijo 6 (Suplemento A)
    assert v["form1[0].#subform[0].PtAILine9_InCareOf[0]"] == "Ana Torres"      # dirección postal
    assert v["form1[0].#subform[10].PtE_PreparerName[0]"] == "Ricardo Pérez"    # preparador
    # el sexo del hijo 1 llega como "Femenino" y se normaliza
    assert v["form1[0].#subform[1].CheckBox12_Sex[1]"] == "2"


def test_no_se_escribe_firma_del_preparador():
    data = load(FAMILIA)
    v = build_values(data)
    assert "form1[0].#subform[10].PtE_PreparerSignature[0]" not in v
    assert v["form1[0].#subform[10].PtE_PreparerName[0]"] == "Ricardo Pérez"


def test_otros_nombres_editables_preferidos():
    data = load(FAMILIA)
    v = build_values(data)
    assert v["form1[0].#subform[0].TextField1[1]"] == "Charlie García"


# ---------------- Validación ----------------

def test_dob_invalida_bloquea():
    data = load(CASO)
    data.applicant.dob = "no sé"
    r = validate(data)
    assert not r.ok
    assert any("fecha de nacimiento no es una fecha válida" in e.lower() for e in r.errors)


def test_residencia_vacia_no_cuenta():
    data = load(CASO)
    data.residences = [data.residences[0].model_copy(update={"street": "", "city": ""})]
    r = validate(data)
    assert not r.ok
    assert any("al menos una dirección de residencia" in e.lower() for e in r.errors)


def test_conyuge_vacio_sin_advertencia():
    data = load(CASO)
    data.spouse = Spouse()  # objeto vacío, no hay datos reales
    r = validate(data)
    assert r.ok
    assert not any("cónyuge" in w.lower() for w in r.warnings)


def test_hijos_incoherentes_advierten():
    data = load(FAMILIA)
    data.has_children = False
    r = validate(data)
    assert any("sin hijos" in w.lower() for w in r.warnings)


# ---------------- Integración con pdftk ----------------

@pytest.mark.skipif(pdftk_missing or not BLANK_PDF.exists(), reason="requiere pdftk y el formulario")
def test_fill_familia_end_to_end():
    data = load(FAMILIA)
    assert validate(data).ok
    out = fill_pdf(data, "familia123456", "prueba_familia")
    assert out.exists() and out.stat().st_size > 100_000
    assert verify_filled(out, "form1[0].#subform[1].NotMarried[0].PtAIILine5_LastName[0]", "Torres")
    assert verify_filled(out, "form1[0].#subform[1].ChildLast1[0]", "García Torres")
    assert verify_filled(out, "form1[0].#subform[12].TextField12[0]", "García Torres")
