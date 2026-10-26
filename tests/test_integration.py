"""Pruebas de integración: validación, construcción de valores y llenado real del PDF."""
import json
from pathlib import Path

import pytest

from app.pdf.filler import BLANK_PDF, build_values, fill_pdf, find_pdftk, verify_filled
from app.schemas.i589 import I589Data
from app.validation import validate

FIXTURE = Path(__file__).parent / "fixtures" / "caso_completo.json"

pdftk_missing = False
try:
    find_pdftk()
except RuntimeError:
    pdftk_missing = True


def load_fixture() -> I589Data:
    return I589Data.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_validacion_completa_ok():
    data = load_fixture()
    result = validate(data)
    assert result.ok, result.errors


def test_validacion_vacia_bloquea():
    result = validate(I589Data())
    assert not result.ok
    assert any("Apellido" in e for e in result.errors)
    assert any("narrativa" in e.lower() for e in result.errors)


def test_build_values_mapea_campos():
    data = load_fixture()
    values = build_values(data)
    apellido_field = "form1[0].#subform[0].PtAILine4_LastName[0]"
    assert values[apellido_field] == "Pérez Rodríguez"
    # fecha normalizada
    assert values["form1[0].#subform[0].DateTimeField1[0]"] == "05/14/1990"
    # checkbox CAT marcado
    assert values["form1[0].#subform[0].CheckBox31[0]"] == "1"
    # checkbox sexo femenino
    assert values["form1[0].#subform[0].PartALine9Sex[1]"] == "F"
    assert values["form1[0].#subform[0].PartALine9Sex[0]"] == "Off"
    # residencia con "Presente"
    assert "Present" in values.values()


@pytest.mark.skipif(pdftk_missing or not BLANK_PDF.exists(), reason="requiere pdftk y el formulario")
def test_fill_pdf_end_to_end(tmp_path):
    data = load_fixture()
    out = fill_pdf(data, "test1234567890", "prueba_integracion")
    assert out.exists() and out.stat().st_size > 100_000
    # el apellido debe estar dentro del PDF resultante
    assert verify_filled(out, "form1[0].#subform[0].PtAILine4_LastName[0]", "Pérez Rodríguez")
    # el formulario NO debe estar aplanado: los campos siguen existiendo
    assert verify_filled(out, "form1[0].#subform[0].DateTimeField1[0]", "05/14/1990")
