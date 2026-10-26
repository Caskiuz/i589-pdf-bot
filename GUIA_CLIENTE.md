# Guía de prueba — I-589 PDF Bot

**Para:** Jhonatan
**Qué es:** un sistema que toma la conversación de WhatsApp (que pegas o importas en el sistema), extrae todos los datos con inteligencia artificial, permite revisarlos y genera el Formulario I-589 de asilo **rellenado y editable**, con el código de barras 2D oficial funcionando.

> **Importante:** el formulario final se completa **en inglés**, porque USCIS lo exige así. La IA traduce automáticamente los datos del chat (aunque la conversación esté en español) y la interfaz de trabajo sigue en español para ti.

---

## 1. Link de prueba

**https://monica-mattress-fixed-combo.trycloudflare.com**

> Este link está activo mientras el demo esté corriendo en la computadora de Ricardo. Si deja de abrir, pídele que lo reactive.

**Requisitos:**
- Un navegador (Chrome, Edge, etc.) — cualquier computadora o teléfono.
- **Adobe Acrobat Reader** (gratis) para abrir el PDF final y ver el código de barras.
- Nada que instalar para probar.

---

## 2. Lo que hay que probar (5–10 minutos)

### Paso 0 — Abrir el sistema
Entra al link. Verás arriba tres indicadores en verde: **IA: conectada**, **pdftk: listo**, **Formulario: 07/28/26 ✓**. El último indica la edición del formulario oficial en uso; el sistema revisa por su cuenta si USCIS publicó una edición nueva y te avisa ahí mismo (en ámbar: **⚠ nueva edición**). Abajo a la izquierda, la lista de casos.

### Paso 1 — Caso de ejemplo ya preparado
Haz clic en **"Demo - Pérez, María"**. Verás un caso completo con datos de una solicitante venezolana de ejemplo.

Recorre las pestañas: **Solicitante, Contacto y Dirección, Entrada a EE. UU., Direcciones (5 años), Familia, Antecedentes, Empleo y Educación, Solicitud (Parte B), Preguntas (B y C), Firma y Preparador, Narrativa**.

👉 **Lo que demuestra:** el sistema organiza la información exactamente como la pide el formulario oficial, sección por sección.

### Paso 2 — Probar la extracción desde WhatsApp (la parte central)
1. Clic en **"+ Nuevo caso"** (arriba a la izquierda). Se crea un caso nuevo.
2. Clic en **"💬 Chat de WhatsApp"**.
3. Clic en **"Cargar ejemplo"** — se carga una conversación real de WhatsApp (puedes editarla o pegar la tuya).
4. Clic en **"🤖 Extraer con IA"** y espera 30–60 segundos.

👉 **Lo que hace el sistema:** envía la conversación a DeepSeek (IA) en 4 llamadas independientes (datos personales, familia, antecedentes, solicitud) y devuelve la información estructurada. No inventa datos: si algo no está en el chat, el campo queda vacío.

👉 **Lo que debes ver:** las pestañas se llenan solas con nombre, fecha de nacimiento, dirección, entrada al país, familia, empleos, educación, motivo de la solicitud y la narrativa de persecución. Los valores aparecen en inglés porque así lo exige USCIS; la interfaz sigue en español.

### Paso 3 — Revisar y corregir (así se trabaja en la vida real)
Modifica cualquier campo (por ejemplo, cambia un teléfono o completa un dato que falte). Los cambios se guardan automáticamente en el caso.

👉 **Sobre los campos vacíos:** es normal que queden vacíos los datos que no se mencionaron en el chat o que son opcionales (segundo nombre, SSN, número A, dirección postal si es igual a la residencia). El sistema no inventa datos. El botón **Validar** te dice si falta algo crítico para poder generar el formulario.

👉 **Lo que demuestra:** la IA propone, el preparador humano confirma y corrige. Nada se genera sin supervisión.

### Paso 4 — Validación obligatoria
Clic en **"✔ Validar"**.
- Si falta un dato crítico (apellido, fecha de nacimiento, dirección actual, motivo de asilo, narrativa), el sistema **bloquea** la generación y te dice exactamente qué falta.
- Si todo está completo, muestra "✅ Datos completos".

👉 **Lo que demuestra:** el sistema no permite generar formularios incompletos o "vacíos" por error.

### Paso 5 — Generar el PDF
Clic en **"📄 Generar PDF"**. Aparece el enlace **"⬇ Descargar"**. Descarga el archivo.

👉 **Lo que hace el sistema:** crea un archivo de datos (XFDF) con toda la información y lo fusiona con el formulario oficial de USCIS (edición 07/28/26) usando pdftk. **No aplana el PDF**: todos los campos quedan editables y el JavaScript interno del formulario se mantiene intacto. La narrativa de persecución se escribe completa en el Suplemento B. El sistema **nunca modifica el archivo original descargado de USCIS**: siempre genera una copia nueva rellenada.

### Paso 6 — La prueba clave: el código de barras
Abre el PDF descargado **en Adobe Acrobat Reader** (recomendado para la revisión final).

👉 **Lo que debes ver:** el formulario llenado y, al pie de cada página, el **código de barras 2D** que ya trae el formulario oficial de USCIS (identifica el formulario I-589, la edición y el número de página). El sistema lo conserva intacto, sin redibujarlo ni aplanarlo, por eso se ve correctamente en Acrobat y en los demás visores.

👉 **Por qué:** el formulario oficial es un PDF híbrido (XFA + Acrobat). Al rellenarlo, el sistema retira la capa XFA vacía que hacía que Acrobat mostrara el documento como si estuviera en blanco. Así los datos y el código de barras se ven bien en todos los visores, y los campos siguen editables.

---

## 3. Checklist de aceptación

| # | Prueba | Resultado esperado |
|---|---|---|
| 1 | Abrir el link | Carga la app con los 3 indicadores en verde |
| 2 | Abrir "Demo - Pérez, María" | Datos completos en las 11 pestañas |
| 3 | Crear caso + Cargar ejemplo + Extraer con IA | Pestañas llenas automáticamente en ~1 minuto |
| 4 | Borrar un dato crítico y Validar | El sistema bloquea y señala el campo |
| 5 | Completar y Validar | "✅ Datos completos" |
| 6 | Generar PDF y descargar | PDF de 12 páginas con los datos |
| 7 | Abrir en Acrobat Reader | Datos visibles y código de barras 2D al pie de cada página |
| 8 | Editar un campo del PDF en Acrobat | El campo sigue editable (no aplanado) |

---

## 4. Lo que el sistema NO hace (para que no haya sorpresas)

- **No envía el formulario a USCIS.** Genera el PDF listo; el envío lo hace el preparador.
- **No firma por el solicitante.** La firma es manuscrita (USCIS no acepta firma digital). El sistema rellena los campos tipográficos y las fechas; la firma se estampa al imprimir.
- **No inventa datos.** Si el chat no menciona algo, el campo queda vacío y el sistema te avisa en la validación.
- **No reemplaza al preparador.** Es una herramienta de productividad: la revisión final siempre es humana.

---

## 5. Sobre la conexión con WhatsApp

**Cómo funciona hoy (versión incluida):** tú pegas el texto de la conversación en el sistema (o usas el botón de ejemplo para probar). Es la forma estándar de operar: sin costos adicionales, sin configuración y sin riesgo para tu número de WhatsApp. Además, en WhatsApp puedes usar **"Exportar chat"** para enviarte la conversación y pegarla completa en el sistema.

**¿Y si la quieres automática?** Para que el sistema reciba los mensajes directamente, sin copiar y pegar, hay que usar la **API oficial de WhatsApp Business de Meta (Cloud API)**. Eso requiere que tú configures y tengas:

- Una **cuenta de Meta Business verificada** (trámite tuyo con Meta).
- Un **número de teléfono dedicado** para la API (no puede ser tu WhatsApp personal en uso).
- Un **servidor con HTTPS público** donde corra el sistema (no una computadora local).
- Asumir el **costo por conversación** que cobra Meta (hay una capa gratuita mensual y el resto son centavos por conversación).

Esa integración **es una fase adicional del proyecto** (se cotiza aparte) y depende de que tengas la cuenta de Meta lista. Sin tu cuenta configurada, la API no puede conectarse.

> Nota: existen herramientas no oficiales que "conectan" WhatsApp escaneando un código QR, pero violan los términos de WhatsApp y Meta puede **bloquear tu número**. No se recomiendan para tu negocio.

## 6. Datos y privacidad

- Los casos se guardan **solo en la computadora donde corre el sistema** (base de datos local).
- El texto del chat se envía a la API de DeepSeek únicamente para la extracción; no se usa para entrenar modelos.
- El PDF generado queda en la carpeta `outputs/` de la máquina local.

---

## 7. Qué se entrega al contratar

1. El sistema completo instalado y funcionando en tu computadora (un solo clic para abrirlo).
2. El formulario mapeado completo (las 12 páginas), con **detección automática de nuevas ediciones de USCIS** (el indicador «Formulario» avisa si hay una edición nueva) y actualización asistida con reporte de cambios.
3. Soporte para dejar la IA funcionando con tu propia cuenta de DeepSeek (el costo por formulario es de centavos).

Cualquier duda durante la prueba, me escribes y la resolvemos en el momento.
