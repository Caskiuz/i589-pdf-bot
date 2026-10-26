"""Pruebas de la detección de edición y del comparador de inventarios."""
import json
from pathlib import Path

from app.form_update import collect_mapping_fields, compare_inventories, extract_edition

ROOT = Path(__file__).resolve().parent.parent


def test_extrae_edicion_del_formulario_local():
    assert extract_edition(ROOT / "data" / "i-589-open.pdf") == "07/28/26"


def test_collect_mapping_fields():
    mapping = json.loads((ROOT / "config" / "i589_mapping.json").read_text(encoding="utf-8"))
    fields = collect_mapping_fields(mapping)
    assert len(fields) > 300
    assert fields["form1[0].#subform[0].PtAILine4_LastName[0]"] == "applicant.last_name"


def test_comparador_compatible_con_campos_nuevos():
    old = [{"name": "a", "alt": ""}, {"name": "b", "alt": ""}]
    new = [{"name": "a", "alt": ""}, {"name": "b", "alt": ""}, {"name": "c", "alt": "nuevo"}]
    report = compare_inventories(old, new, {"a": "x.a", "b": "x.b"})
    assert report["compatible"]
    assert len(report["added"]) == 1
    assert report["affected"] == []


def test_comparador_detecta_campo_eliminado():
    old = [{"name": "a", "alt": ""}, {"name": "b", "alt": ""}]
    new = [{"name": "a", "alt": ""}, {"name": "b2", "alt": ""}]
    report = compare_inventories(old, new, {"a": "x.a", "b": "x.b"})
    assert not report["compatible"]
    assert report["affected"] == [{"logical": "x.b", "field": "b"}]
    assert [f["name"] for f in report["removed"]] == ["b"]
