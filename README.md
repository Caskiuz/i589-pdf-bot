# I-589 PDF Bot

Aplicación web local que prepara el **Formulario I-589 (Solicitud de Asilo y de Retención de Expulsión)** de USCIS a partir de la conversación de WhatsApp con el cliente.

Flujo de trabajo:

1. **Crear caso** y pegar el texto del chat de WhatsApp.
2. **Extraer con IA** (DeepSeek): el sistema extrae todos los datos biográficos, familia, antecedentes, empleo, educación y la narrativa de persecución.
3. **Revisar y corregir** los datos en el formulario editable por secciones (la IA propone, el humano confirma).
4. **Generar el PDF** con los datos rellenados en el formulario oficial.

> ⚠️ **Puntos críticos (por diseño):** el PDF **NO se aplana** (no flatten): todos los campos quedan editables. El I-589 oficial es un PDF **híbrido XFA + AcroForm**; el sistema rellena los campos AcroForm y genera el PDF con `drop_xfa`, de modo que **Adobe Acrobat y cualquier visor muestran los datos rellenados** (sin esa opción, Acrobat prioriza la capa XFA vacía y el documento se ve en blanco). El **código de barras 2D** (PDF417) ya viene dibujado en el formulario oficial —su contenido es el identificador del formulario, la edición y el número de página, no los datos del solicitante— y se conserva intacto.

---

## Requisitos

| Herramienta | Cómo instalarla |
|---|---|
| Python 3.11+ | https://python.org |
| pdftk (pdftk Server 2.02) | `scoop install pdftk` (o `winget`/manual) |
| qpdf (solo para regenerar el formulario) | `scoop install qpdf` |
| API key de DeepSeek | https://platform.deepseek.com (recargar ~US$5 cubre cientos de formularios) |

## Instalación (un clic)

1. Copia `.env.example` → `.env` y pega tu key de DeepSeek:
   ```
   DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
   ```
2. Doble clic en **`run_demo.bat`** — crea el entorno, instala dependencias, verifica pdftk y el formulario, y abre `http://127.0.0.1:8000`.

El formulario oficial (edición 07/28/26) ya viene incluido descifrado en `data/i-589-open.pdf`. Si USCIS publica una edición nueva:

```bash
python scripts/download_form.py          # descarga y descifra la nueva edición
pdftk data/i-589-open.pdf dump_data_fields_utf8 > data/fields_dump.txt
python scripts/inventory.py              # regenera el inventario
python scripts/build_mapping.py          # regenera el mapeo (revisar cambios de nombres)
```

## Uso

1. **+ Nuevo caso** → escribe el nombre (ej. `García, María`).
2. Botón **💬 Chat de WhatsApp** → pega la conversación (o usa **Cargar ejemplo**).
3. Botón **🤖 Extraer con IA** → espera 30-60 s.
4. Revisa cada pestaña (Solicitante, Contacto, Entrada, Direcciones, Familia, Antecedentes, Empleo/Educación, Solicitud, Preguntas, Firma, Narrativa) y corrige lo necesario.
5. **✔ Validar** → muestra errores bloqueantes y advertencias.
6. **📄 Generar PDF** → descarga el PDF rellenado. Ábrelo en **Adobe Acrobat Reader**: el código de barras 2D de la última página se genera solo.

## Arquitectura

```
app/
├── main.py            # FastAPI: API REST + frontend
├── db.py              # SQLite local (casos y datos)
├── schemas/i589.py    # Modelo de datos lógico del I-589 (Pydantic)
├── ai/client.py       # Cliente DeepSeek (API compatible con OpenAI)
├── ai/extractor.py    # Extracción por secciones (function calling estricto + fallback JSON)
├── validation.py      # Campos obligatorios con mensajes en español
├── normalize.py       # Fechas → MM/DD/YYYY y MM/YYYY
├── pdf/xfdf.py        # Generador XFDF
├── pdf/filler.py      # Traducción datos → campos + pdftk fill_form (SIN flatten)
└── static/index.html  # UI en español
config/i589_mapping.json  # Diccionario llave lógica → campo interno de Adobe
data/i-589-open.pdf       # Formulario oficial en blanco (descifrado)
scripts/                  # setup, descarga del formulario, inventario y mapeo
tests/                    # pytest (unidad + integración con pdftk real)
```

**Por qué XFDF + pdftk y `drop_xfa`:** el formulario de USCIS es un PDF híbrido (XFA + AcroForm). Rellenar solo la capa AcroForm deja la capa XFA vacía, y Adobe Acrobat prioriza XFA al abrir el documento: por eso el PDF puede verse "en blanco" aunque los valores estén escritos. Con `pdftk fill_form … drop_xfa` se elimina la capa XFA y Acrobat renderiza los campos AcroForm con sus apariencias (los datos visibles), manteniendo el formulario editable y sin aplanar. El código de barras 2D es una imagen ya incluida en el formulario oficial (su contenido es `I-589|edición|página`) y se conserva tal cual.

**Por qué DeepSeek:** API compatible con OpenAI, disponible desde Venezuela sin restricciones, con modo *strict function calling* (schema JSON garantizado). El módulo `app/ai/` está aislado: cambiar de proveedor solo toca `client.py` y `extractor.py`.

## Validación

Los siguientes campos son **bloqueantes** (no se genera el PDF sin ellos):

- Apellido, nombre y fecha de nacimiento del solicitante
- Nacionalidad y ciudad/país de nacimiento
- Dirección actual en EE. UU.
- Al menos una residencia de los últimos 5 años
- Al menos un motivo de la solicitud (raza, religión, nacionalidad, opinión política, grupo social o tortura)
- Declaración/narrativa de persecución

## Pruebas

```bash
.venv\Scripts\python -m pytest tests/ -q
```

Incluye una prueba de integración que rellena el PDF real con pdftk y verifica los valores dentro del documento resultante.

## Notas legales y de uso

- El formulario I-589 es un documento público del gobierno de EE. UU. (libre de derechos).
- La **firma manuscrita** del solicitante no se puede rellenar electrónicamente: el sistema completa los campos tipográficos y la firma húmeda se estampa al imprimir.
- Esta herramienta asiste en la preparación del formulario; la revisión final de un profesional de inmigración es responsabilidad del usuario.
