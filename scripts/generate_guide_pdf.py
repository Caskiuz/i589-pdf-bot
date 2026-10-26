"""Genera GUIA_CLIENTE.pdf (cuerpo) con ReportLab — guía de prueba para el cliente."""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "data" / "pdf_build"
BUILD.mkdir(parents=True, exist_ok=True)
OUT = BUILD / "body.pdf"

# ━━ Color Palette (auto-generada por pdf.py palette.generate) ━━
# Intent: neutral | Mode: minimal | Harmony: split_complementary
ACCENT = colors.HexColor("#4b29b2")
TEXT_PRIMARY = colors.HexColor("#1b1b19")
TEXT_MUTED = colors.HexColor("#817d74")
BG_SURFACE = colors.HexColor("#dddad4")
TABLE_HEADER = ACCENT
ROW_ALT = colors.HexColor("#f4f2ee")
TINT = colors.HexColor("#eeebf8")          # tinte del acento (8%) para callouts
RULE = colors.HexColor("#cfc8ea")          # acento al 30%

FONT_DIR = Path("C:/Windows/Fonts")


def register_fonts() -> str:
    seg = FONT_DIR / "segoeui.ttf"
    seg_b = FONT_DIR / "segoeuib.ttf"
    seg_i = FONT_DIR / "segoeuii.ttf"
    if seg.exists() and seg_b.exists():
        pdfmetrics.registerFont(TTFont("SegoeUI", str(seg)))
        pdfmetrics.registerFont(TTFont("SegoeUI-Bold", str(seg_b)))
        pdfmetrics.registerFont(
            TTFont("SegoeUI-Italic", str(seg_i if seg_i.exists() else seg))
        )
        registerFontFamily(
            "SegoeUI", normal="SegoeUI", bold="SegoeUI-Bold", italic="SegoeUI-Italic"
        )
        return "SegoeUI"
    arial = FONT_DIR / "arial.ttf"
    arial_b = FONT_DIR / "arialbd.ttf"
    if arial.exists() and arial_b.exists():
        pdfmetrics.registerFont(TTFont("ArialLocal", str(arial)))
        pdfmetrics.registerFont(TTFont("ArialLocal-Bold", str(arial_b)))
        registerFontFamily("ArialLocal", normal="ArialLocal", bold="ArialLocal-Bold")
        return "ArialLocal"
    raise SystemExit("No se encontró Segoe UI ni Arial en C:/Windows/Fonts")


FONT = register_fonts()

PAGE_W, PAGE_H = A4
ML, MR = 2.2 * cm, 2.2 * cm
MT, MB = 2.4 * cm, 2.2 * cm
CONTENT_W = PAGE_W - ML - MR

S = {
    "title": ParagraphStyle("title", fontName=FONT, fontSize=20, leading=25,
                            textColor=TEXT_PRIMARY, spaceAfter=4),
    "subtitle": ParagraphStyle("subtitle", fontName=FONT, fontSize=11, leading=15,
                               textColor=TEXT_MUTED, spaceAfter=12),
    "h1": ParagraphStyle("h1", fontName=FONT, fontSize=16, leading=20,
                         textColor=ACCENT, spaceBefore=16, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName=FONT, fontSize=12.5, leading=16,
                         textColor=TEXT_PRIMARY, spaceBefore=12, spaceAfter=4),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=10.5, leading=15.5,
                           textColor=TEXT_PRIMARY, alignment=TA_JUSTIFY,
                           spaceAfter=7),
    "bullet": ParagraphStyle("bullet", fontName=FONT, fontSize=10.5, leading=15,
                             textColor=TEXT_PRIMARY, leftIndent=14,
                             bulletIndent=2, spaceAfter=4),
    "step": ParagraphStyle("step", fontName=FONT, fontSize=10.5, leading=15,
                           textColor=TEXT_PRIMARY, leftIndent=16,
                           spaceAfter=6),
    "small": ParagraphStyle("small", fontName=FONT, fontSize=9, leading=13,
                            textColor=TEXT_MUTED),
    "callout": ParagraphStyle("callout", fontName=FONT, fontSize=10.5, leading=15,
                              textColor=TEXT_PRIMARY, alignment=TA_LEFT),
    "cell": ParagraphStyle("cell", fontName=FONT, fontSize=9.5, leading=13,
                           textColor=TEXT_PRIMARY, alignment=TA_LEFT),
    "cell_c": ParagraphStyle("cell_c", fontName=FONT, fontSize=9.5, leading=13,
                             textColor=TEXT_PRIMARY, alignment=TA_CENTER),
    "th": ParagraphStyle("th", fontName=FONT, fontSize=9.5, leading=13,
                         textColor=colors.white, alignment=TA_CENTER),
}
# título en negrita mediante tags <b> en el texto

story: list = []


def h1(text: str) -> None:
    story.append(CondPageBreak(PAGE_H * 0.25))
    story.append(Paragraph(text, S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.0, color=RULE,
                            spaceBefore=0, spaceAfter=8))


def h2(text: str) -> None:
    story.append(Paragraph(text, S["h2"]))


def p(text: str) -> None:
    story.append(Paragraph(text, S["body"]))


def bullets(items: list[str]) -> None:
    for item in items:
        story.append(Paragraph(f"•  {item}", S["bullet"]))


def callout(inner: list, bg=TINT, border=ACCENT) -> None:
    box = Table([[inner]], colWidths=[CONTENT_W], hAlign="CENTER")
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (0, -1), 3, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(box)
    story.append(Spacer(1, 10))


def checklist_table(rows: list[tuple[str, str, str]]) -> None:
    data = [[Paragraph("#", S["th"]), Paragraph("Prueba", S["th"]),
             Paragraph("Resultado esperado", S["th"])]]
    for num, prueba, esperado in rows:
        data.append([Paragraph(num, S["cell_c"]), Paragraph(prueba, S["cell"]),
                     Paragraph(esperado, S["cell"])])
    widths = [0.07 * CONTENT_W, 0.48 * CONTENT_W, 0.45 * CONTENT_W]
    t = Table(data, colWidths=widths, hAlign="CENTER", repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
        ("GRID", (0, 0), (-1, -1), 0.5, TEXT_MUTED),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        style.append(("BACKGROUND", (0, i), (-1, i), colors.white if i % 2 else ROW_ALT))
    t.setStyle(TableStyle(style))
    story.append(t)
    story.append(Spacer(1, 12))


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(ML, PAGE_H - 1.5 * cm, "I-589 PDF Bot  ·  Guía de prueba")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(ML, PAGE_H - 1.65 * cm, PAGE_W - MR, PAGE_H - 1.65 * cm)
        canvas.drawString(ML, 1.35 * cm, "Preparado para Jhonatan")
        canvas.drawRightString(PAGE_W - MR, 1.35 * cm, f"Página {doc.page}")
        canvas.setStrokeColor(RULE)
        canvas.line(ML, 1.55 * cm, PAGE_W - MR, 1.55 * cm)
    canvas.restoreState()


# ══════════════════════════ CONTENIDO ══════════════════════════
story.append(Paragraph("<b>Guía de prueba del sistema</b>", S["title"]))
story.append(Paragraph(
    "Sistema de preparación asistida del Formulario I-589 (solicitud de asilo) a partir "
    "de la conversación de WhatsApp. Documento de prueba para el cliente.", S["subtitle"]))

h1("1. Qué es y qué necesitas para probar")
p("El sistema toma la conversación de WhatsApp (que pegas o importas), extrae todos los "
  "datos con inteligencia artificial, te permite revisarlos y genera el Formulario I-589 "
  "de asilo <b>rellenado y editable</b>, con el código de barras 2D oficial funcionando.")
p("<b>Importante:</b> el formulario final se completa <b>en inglés</b>, porque USCIS lo exige. "
  "La IA traduce automáticamente los datos del chat (aunque la conversación esté en español) y "
  "la interfaz de trabajo sigue en español para ti.")
callout([
    Paragraph("<b>Link de prueba</b><br/>"
              '<a href="https://monica-mattress-fixed-combo.trycloudflare.com" '
              'color="#4b29b2"><b>https://monica-mattress-fixed-combo.trycloudflare.com</b></a><br/>'
              '<font size="9" color="#817d74">Activo mientras el demo esté corriendo en la '
              "computadora de Ricardo. Si deja de abrir, pídele que lo reactive.</font>",
              S["callout"]),
])
p("<b>Requisitos:</b>")
bullets([
    "Un navegador (Chrome, Edge, etc.) — cualquier computadora o teléfono.",
    "<b>Adobe Acrobat Reader</b> (gratis) para abrir el PDF final y ver el código de barras.",
    "Nada que instalar para probar.",
])

h1("2. Lo que hay que probar (5–10 minutos)")
h2("Paso 0 — Abrir el sistema")
p("Entra al link. Verás arriba tres indicadores en verde: <b>IA: conectada</b>, "
  "<b>pdftk: listo</b> y <b>Formulario: 07/28/26 ✓</b>. El último indica la edición del "
  "formulario oficial en uso; el sistema revisa por su cuenta si USCIS publicó una edición "
  "nueva y te avisa ahí mismo (en ámbar: <b>⚠ nueva edición</b>). Abajo a la izquierda, la "
  "lista de casos.")

h2("Paso 1 — Caso de ejemplo ya preparado")
p("Haz clic en <b>«Demo - Pérez, María»</b>. Verás un caso completo con datos de una "
  "solicitante venezolana de ejemplo. Recorre las pestañas: <b>Solicitante, Contacto y "
  "Dirección, Entrada a EE. UU., Direcciones (5 años), Familia, Antecedentes, Empleo y "
  "Educación, Solicitud (Parte B), Preguntas (B y C), Firma y Preparador, Narrativa</b>.")
p("<b>Qué demuestra:</b> el sistema organiza la información exactamente como la pide el "
  "formulario oficial, sección por sección.")

h2("Paso 2 — Probar la extracción desde WhatsApp (la parte central)")
story.append(Paragraph("<b>1.</b>  Clic en <b>«+ Nuevo caso»</b> (arriba a la izquierda). "
                       "Se crea un caso nuevo.", S["step"]))
story.append(Paragraph("<b>2.</b>  Clic en <b>«Chat de WhatsApp»</b>.", S["step"]))
story.append(Paragraph("<b>3.</b>  Clic en <b>«Cargar ejemplo»</b> — se carga una "
                       "conversación real de WhatsApp (puedes editarla o pegar la tuya).", S["step"]))
story.append(Paragraph("<b>4.</b>  Clic en <b>«Extraer con IA»</b> y espera de 30 a 60 segundos.",
                       S["step"]))
p("<b>Qué hace el sistema:</b> envía la conversación a DeepSeek (IA) en cuatro llamadas "
  "independientes (datos personales, familia, antecedentes y solicitud) y devuelve la "
  "información estructurada. No inventa datos: si algo no está en el chat, el campo queda vacío.")
p("<b>Qué debes ver:</b> las pestañas se llenan solas con nombre, fecha de nacimiento, "
  "dirección, entrada al país, familia, empleos, educación, motivo de la solicitud y la "
  "narrativa de persecución. Los valores aparecen en inglés porque así lo exige USCIS; la "
  "interfaz sigue en español.")

h2("Paso 3 — Revisar y corregir (así se trabaja en la vida real)")
p("Modifica cualquier campo (por ejemplo, cambia un teléfono o completa un dato que falte). "
  "Los cambios se guardan automáticamente en el caso.")
p("<b>Sobre los campos vacíos:</b> es normal que queden vacíos los datos que no se mencionaron "
  "en el chat o que son opcionales (segundo nombre, SSN, número A, dirección postal si es igual "
  "a la residencia). El sistema no inventa datos. El botón <b>Validar</b> te dice si falta algo "
  "crítico para poder generar el formulario.")
p("<b>Qué demuestra:</b> la IA propone, el preparador humano confirma y corrige. Nada se "
  "genera sin supervisión.")

h2("Paso 4 — Validación obligatoria")
p("Clic en <b>«Validar»</b>. Si falta un dato crítico (apellido, fecha de nacimiento, "
  "dirección actual, motivo de asilo o narrativa), el sistema <b>bloquea</b> la generación "
  "y te dice exactamente qué falta. Si todo está completo, muestra «Datos completos».")
p("<b>Qué demuestra:</b> el sistema no permite generar formularios incompletos o vacíos por error.")

h2("Paso 5 — Generar el PDF")
p("Clic en <b>«Generar PDF»</b>. Aparece el enlace <b>«Descargar»</b>. Descarga el archivo.")
p("<b>Qué hace el sistema:</b> crea un archivo de datos (XFDF) con toda la información y lo "
  "fusiona con el formulario oficial de USCIS (edición 07/28/26) usando pdftk. <b>No aplana "
  "el PDF</b>: todos los campos quedan editables y el JavaScript interno del formulario se "
  "mantiene intacto. La narrativa de persecución se escribe completa en el Suplemento B. El "
  "sistema <b>nunca modifica el archivo original descargado de USCIS</b>: siempre genera una "
  "copia nueva rellenada.")

h2("Paso 6 — La prueba clave: el código de barras")
p("Abre el PDF descargado <b>en Adobe Acrobat Reader</b> (recomendado para la revisión final).")
p("<b>Qué debes ver:</b> el formulario llenado y, al pie de cada página, el <b>código de "
  "barras 2D</b> que ya trae el formulario oficial de USCIS (identifica el formulario I-589, "
  "la edición y el número de página). El sistema lo conserva intacto, sin redibujarlo ni "
  "aplanarlo, por eso se ve correctamente en Acrobat y en los demás visores.")
p("<b>Por qué:</b> el formulario oficial es un PDF híbrido (XFA + Acrobat). Al rellenarlo, "
  "el sistema retira la capa XFA vacía que hacía que Acrobat mostrara el documento como si "
  "estuviera en blanco. Así los datos y el código de barras se ven bien en todos los "
  "visores, y los campos siguen editables.")

h1("3. Checklist de aceptación")
checklist_table([
    ("1", "Abrir el link", "Carga la app con los tres indicadores en verde"),
    ("2", "Abrir «Demo - Pérez, María»", "Datos completos en las once pestañas"),
    ("3", "Caso nuevo + Cargar ejemplo + Extraer con IA",
     "Pestañas llenas automáticamente en ~1 minuto"),
    ("4", "Borrar un dato crítico y Validar", "El sistema bloquea y señala el campo"),
    ("5", "Completar y Validar", "Mensaje «Datos completos»"),
    ("6", "Generar PDF y descargar", "PDF de 12 páginas con los datos"),
    ("7", "Abrir en Acrobat Reader", "Datos visibles y código de barras 2D al pie de cada página"),
    ("8", "Editar un campo del PDF en Acrobat", "El campo sigue editable (no aplanado)"),
])

h1("4. Lo que el sistema no hace (para que no haya sorpresas)")
bullets([
    "<b>No envía el formulario a USCIS.</b> Genera el PDF listo; el envío lo hace el preparador.",
    "<b>No firma por el solicitante.</b> La firma es manuscrita (USCIS no acepta firma digital). "
    "El sistema rellena los campos tipográficos y las fechas; la firma se estampa al imprimir.",
    "<b>No inventa datos.</b> Si el chat no menciona algo, el campo queda vacío y la validación te avisa.",
    "<b>No reemplaza al preparador.</b> Es una herramienta de productividad: la revisión final "
    "siempre es humana.",
])

h1("5. Sobre la conexión con WhatsApp")
p("<b>Cómo funciona hoy (versión incluida):</b> tú pegas el texto de la conversación en el "
  "sistema (o usas el botón de ejemplo para probar). Es la forma estándar de operar: sin "
  "costos adicionales, sin configuración y sin riesgo para tu número de WhatsApp. Además, en "
  "WhatsApp puedes usar <b>«Exportar chat»</b> para enviarte la conversación y pegarla "
  "completa en el sistema.")
p("<b>¿Y si la quieres automática?</b> Para que el sistema reciba los mensajes directamente, "
  "sin copiar y pegar, hay que usar la <b>API oficial de WhatsApp Business de Meta "
  "(Cloud API)</b>. Eso requiere que tú configures y tengas:")
bullets([
    "Una <b>cuenta de Meta Business verificada</b> (trámite tuyo con Meta).",
    "Un <b>número de teléfono dedicado</b> para la API (no puede ser tu WhatsApp personal en uso).",
    "Un <b>servidor con HTTPS público</b> donde corra el sistema (no una computadora local).",
    "Asumir el <b>costo por conversación</b> que cobra Meta (hay una capa gratuita mensual y "
    "el resto son centavos por conversación).",
])
p("Esa integración <b>es una fase adicional del proyecto</b> (se cotiza aparte) y depende de "
  "que tengas la cuenta de Meta lista. Sin tu cuenta configurada, la API no puede conectarse.")
callout([Paragraph(
    "Nota: existen herramientas no oficiales que «conectan» WhatsApp escaneando un código QR, "
    "pero violan los términos de WhatsApp y Meta puede <b>bloquear tu número</b>. No se "
    "recomiendan para tu negocio.", S["callout"])])

h1("6. Datos y privacidad")
bullets([
    "Los casos se guardan <b>solo en la computadora donde corre el sistema</b> (base de datos local).",
    "El texto del chat se envía a la API de DeepSeek únicamente para la extracción; no se usa "
    "para entrenar modelos.",
    "El PDF generado queda en la carpeta <b>outputs/</b> de la máquina local.",
])

h1("7. Qué se entrega al contratar")
story.append(Paragraph("<b>1.</b>  El sistema completo instalado y funcionando en tu "
                       "computadora (un solo clic para abrirlo).", S["step"]))
story.append(Paragraph("<b>2.</b>  El formulario mapeado completo (las 12 páginas), con "
                       "<b>detección automática de nuevas ediciones de USCIS</b> (el indicador "
                       "«Formulario» avisa si hay una edición nueva) y actualización asistida "
                       "con reporte de cambios.", S["step"]))
story.append(Paragraph("<b>3.</b>  Soporte para dejar la IA funcionando con tu propia "
                       "cuenta de DeepSeek (el costo por formulario es de centavos).", S["step"]))
story.append(Spacer(1, 8))
p("Cualquier duda durante la prueba, me escribes y la resolvemos en el momento.")

doc = SimpleDocTemplate(
    str(OUT), pagesize=A4,
    leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
    title="Guía de prueba — I-589 PDF Bot",
    author="Ricardo (I-589 PDF Bot)",
    creator="I-589 PDF Bot",
    subject="Guía de prueba del sistema de preparación del Formulario I-589",
)
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(f"OK: {OUT}")
