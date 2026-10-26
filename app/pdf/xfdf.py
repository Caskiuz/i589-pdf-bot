"""Generación de XFDF (XML Forms Data Format) a partir de un dict de valores.

El XFDF se fusiona con el PDF en blanco vía `pdftk fill_form` — NUNCA se
aplana (flatten), para que los campos sigan editables y el JavaScript del
código de barras 2D se ejecute en Adobe Acrobat al abrir el documento.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

XFDF_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<xfdf xmlns="http://ns.adobe.com/xfdf/" xml:space="preserve">\n'
    "<fields>\n"
)
XFDF_FOOTER = "</fields>\n</xfdf>\n"


def build_xfdf(values: dict[str, str]) -> str:
    """values: {nombre_completo_del_campo: valor}. Solo incluye valores no vacíos."""
    parts = [XFDF_HEADER]
    for field, value in values.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        parts.append(f'  <field name="{escape(str(field))}"><value>{escape(str(value))}</value></field>\n')
    parts.append(XFDF_FOOTER)
    return "".join(parts)
