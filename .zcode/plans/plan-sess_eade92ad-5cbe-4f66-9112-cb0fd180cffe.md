# Plan: I-589 PDF Bot — Producto funcional completo (v1)

## Tu pregunta, respondida primero
**No necesitamos ningún PDF del cliente.** El formulario I-589 es un documento público oficial de USCIS (edición 07/28/26) que se descarga gratis desde uscis.gov. Con `pdftk dump_data_fields` extraemos automáticamente los ~900 nombres de campos internos del PDF en blanco, y sobre eso se construye el mapeo completo. **No hay que pedirle nada a Jhonatan.** (Opcional: pedirle una conversación real de WhatsApp anonimizada para afinar la extracción — no es bloqueante para construir.)

## Qué se entrega (producto v1, no demo)
Una aplicación web local en español, profesional, que el cliente pueda operar de verdad:
1. **Gestión de casos**: crear caso → pegar el texto de WhatsApp → guardar historial (SQLite local).
2. **Extracción con IA (DeepSeek)**: del texto desordenado extrae TODAS las secciones del I-589 (biográficos, base de la solicitud, familiares, historial de direcciones/empleo/educación de 5 años, narrativa de persecución). Usa function calling con `strict: true` (schema JSON estricto), dividido en 4 llamadas por sección para no truncar, con reintentos automáticos.
3. **Formulario editable por secciones**: el operador revisa y corrige los datos extraídos antes de generar (la IA propone, el humano confirma — esencial en un producto real). Campos faltantes se completan a mano.
4. **Validación estricta**: reglas de campos obligatorios con mensajes claros en español; no genera PDF incompleto.
5. **Generación del PDF**: llenado completo de todas las secciones mapeadas del I-589 vía XFDF + pdftk, **SIN flatten** → el JavaScript del código de barras 2D queda vivo y Acrobat Reader lo genera nativamente al abrir. Descarga con nombre por caso.
6. **Instalador de un clic** (`run_demo.bat`): crea entorno, instala dependencias, descarga el formulario oficial, levanta el servidor y abre el navegador.

## Stack (validado en esta PC)
- **Backend**: Python 3.14 + FastAPI + uvicorn (ya instalados en esta máquina).
- **IA**: DeepSeek `deepseek-chat` vía SDK OpenAI con `base_url=https://api.deepseek.com` (confirmado: endpoint accesible desde aquí, sin restricción para Venezuela; tu API key va en `.env`).
- **PDF**: pdftk Server 2.02 (falta instalarlo → `scoop install pdftk`, ya verificado que existe en el bucket oficial; plan B: jar pdftk-java con Java 21 que ya está instalado).
- **Datos**: SQLite (stdlib, sin dependencias extra) + archivos JSON de casos.
- **Frontend**: HTML/CSS/JS vanilla servido por FastAPI (sin build, robusto para entrega local).
- **Versionado**: git + push directo a `Caskiuz/i589-pdf-bot` (repo vacío, se inicia en main).

## Estructura del proyecto
```
C:\i589-pdf-bot\
├── app/
│   ├── main.py            # FastAPI: rutas web + API
│   ├── db.py              # SQLite: casos y extracciones
│   ├── schemas/i589.py    # Modelos Pydantic completos del formulario
│   ├── ai/client.py       # Cliente DeepSeek (function calling strict)
│   ├── ai/extractor.py    # Extracción por secciones + reintentos
│   ├── validation.py      # Reglas de campos obligatorios (español)
│   ├── pdf/fields.py      # Parser de dump_data_fields
│   ├── pdf/xfdf.py        # Generador XFDF (UTF-8)
│   ├── pdf/filler.py      # pdftk fill_form SIN flatten + verificación
│   └── static/            # UI en español (casos, formulario editable, descarga)
├── config/i589_mapping.json   # Diccionario llave lógica → campo Adobe (actualizable sin tocar código)
├── data/i-589.pdf             # Formulario oficial en blanco (descargado por setup)
├── data/samples/              # Conversaciones WhatsApp de ejemplo
├── outputs/                   # PDFs generados por caso
├── scripts/setup.py, download_form.py
├── run_demo.bat               # Un clic: venv + deps + servidor + navegador
├── tests/                     # pytest: validación, XFDF, integración
├── requirements.txt, .env.example, README.md, .gitignore
```

## Pasos de implementación
1. **Git**: `git init`, `.gitignore` (excluye `data/i-589.pdf`, `.env`, `outputs/`), remote y primer commit.
2. **Instalar pdftk** (`scoop install pdftk`) y verificar `pdftk --version`.
3. **Descargar el formulario oficial** I-589 (edición 07/28/26) a `data/i-589.pdf`; verificar que es AcroForm y volcar los campos (`dump_data_fields_utf8`).
4. **Mapeo completo** `i589_mapping.json`: inventario de los ~900 campos agrupados por sección lógica (Parte A.I, A.II, B, C, D, E/F, addenda), incluyendo checkboxes (valor export "Yes") y los campos de cálculo del barcode (que se dejan intactos).
5. **Esquemas Pydantic completos** del formulario (solicitante, familiares, direcciones, empleos, educación, narrativa, firmas).
6. **Cliente DeepSeek + extractor**: function calling con schema estricto generado desde Pydantic, 4 llamadas por sección, `temperature=0`, reintentos con feedback de errores de validación; fallback a JSON mode.
7. **Capa de validación**: obligatorios por sección, fechas coherentes, errores JSON descriptivos en español.
8. **Motor PDF**: generador XFDF con escape UTF-8 + ejecutor `pdftk i-589.pdf fill_form datos.xfdf output outputs/i589_<caso>.pdf` **sin flatten** + verificación post-fill (dump de campos del PDF resultante).
9. **App web**: listado de casos, pantalla "Nuevo caso" (pegar WhatsApp), vista de extracción editable por pestañas/secciones, botón "Generar PDF" y descarga; API REST (`/api/casos`, `/api/extraer`, `/api/generar`, `/descargar/{id}`, `/api/health`).
10. **Pruebas**: pytest (validación, XFDF, integración) + prueba end-to-end con conversación de muestra; verificación de que el script del barcode sigue presente en el PDF generado.
11. **Instalador y documentación**: `run_demo.bat`, `scripts/setup.py` (auto-instala pdftk si falta y descarga el formulario), README con instrucciones para la PC del cliente y para crear su propia key de DeepSeek (tu key NO viaja en la entrega — va en `.env` local del cliente; recargar ~$5 cubre cientos de formularios).
12. **Entrega a Jhonatan**: servidor corriendo aquí + túnel temporal (cloudflared) para que pruebe desde Ecuador con un link; luego le envías el paquete completo con el instalador.
13. **Commits por etapa y push a `main`** en GitHub.

## Protección del pago (opcional — tú decides)
Como el acuerdo es "producto completo → prueba → pago por Binance", puedo incluir un **candado de activación**: el app corre 7 días en modo prueba (con marca de agua sutil en el PDF) y se activa definitivamente con un código que tú le entregas al recibir el pago. Si prefieres entrega 100% abierta, también — solo dime cuál.

## Notas técnicas que debes comunicar a Jhonatan
- El código de barras 2D se genera **al abrir el PDF en Adobe Acrobat Reader** (el JS interno corre solo ahí, como exige USCIS). En el navegador/Chrome no se ve — no es un defecto.
- Los campos quedan editables (no se aplana), tal como requiere USCIS para formularios.
- La firma manuscrita del solicitante se estampa a mano al final (el sistema rellena los campos tipográficos y fechas).

## Tiempo estimado de esta construcción
Una jornada de trabajo de agente (varias horas, en una sesión continua), entregando repositorio + producto funcionando localmente hoy.