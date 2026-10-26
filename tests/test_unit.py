"""Pruebas de normalización de fechas y generación XFDF."""
from app.normalize import phone_parts, to_month_year, to_us_date
from app.pdf.xfdf import build_xfdf


def test_to_us_date_iso():
    assert to_us_date("1990-05-14") == "05/14/1990"


def test_to_us_date_slashes():
    assert to_us_date("05/14/1990") == "05/14/1990"
    assert to_us_date("14/05/1990") == "05/14/1990"


def test_to_us_date_texto():
    assert to_us_date("15 de marzo de 1990") == "03/15/1990"
    assert to_us_date("marzo 15, 1990") == "03/15/1990"


def test_to_us_date_vacia():
    assert to_us_date("") == ""
    assert to_us_date("no sé") == ""


def test_to_month_year():
    assert to_month_year("03/2024") == "03/2024"
    assert to_month_year("marzo de 2024") == "03/2024"
    assert to_month_year("2024-03") == "03/2024"
    assert to_month_year("Presente") == "Present"


def test_phone_parts():
    assert phone_parts("305-555-1234") == ("305", "5551234")
    assert phone_parts("5551234") == ("", "5551234")


def test_xfdf_escape():
    x = build_xfdf({"form1[0].#subform[0].PtAILine4_LastName[0]": "O'Brien & Co <test>"})
    # & < > se escapan; las comillas simples son válidas en contenido XML
    assert "O'Brien &amp; Co &lt;test&gt;" in x
    assert 'name="form1[0].#subform[0].PtAILine4_LastName[0]"' in x


def test_xfdf_ignora_vacios():
    x = build_xfdf({"campo": "", "campo2": None, "campo3": "valor"})
    assert "<field " in x
    assert x.count("<field ") == 1
