# Auditoría completa de campos — bugs encontrados y plan de corrección

## Resultado de la auditoría
- **Cobertura del mapeo: 424/463 campos (91,6%)**. Los 39 restantes son internos y no se rellenan por diseño: 12 códigos de barras, contenedores, uso exclusivo de USCIS/EOIR, Partes F y G (se completan en entrevista/audiencia) y 3 líneas de firma manuscrita. **No falta ningún campo funcional.**
- **0 duplicados y 0 referencias inválidas** en el mapeo. El formulario no tiene campos de email ni móvil.
- Los bugs están en otras capas: normalización de valores, UI y colocación de datos.

## Bugs encontrados (11)

### Críticos
1. **Narrativa mal ubicada**: se escribe en 3 campos, pero 2 de ellos son diminutos (71×12 pt, las casillas de "correcciones número X a Y") y el campo grande de continuación (`TextField32`, 540×492 pt) queda casi vacío. Además se trunca en silencio a 4.500 caracteres.
2. **Idioma**: los valores se extraen en español y USCIS exige el I-589 en inglés (narrativa, religión, ocupación, país, explicaciones). El prompt ya fue corregido pero falta aplicarlo, probarlo y regenerar los datos demo.
3. **Códigos sin normalizar**: la IA devuelve "Femenino", "Soltera" y "Nunca he estado en corte de inmigración"; el selector espera F/single/never. Por eso la UI muestra "—" y el PDF no marca la casilla de corte.

### Importantes
4. **Entradas a EE. UU. no editables**: la IA extrae fecha, lugar y estatus de entrada, pero la UI no tiene campos para revisarlos/corregirlos.
5. **Validación incompleta**: una residencia vacía añadida a mano pasa el control; la fecha de nacimiento no se valida como fecha real; un objeto de cónyuge vacío genera la advertencia falsa "Faltan datos del cónyuge".
6. **Explicación C.2A descartada**: el formulario usa una caja compartida para 2A/2B, pero el mapeo solo escribe la explicación de 2B.
7. **Campos sin editor en la UI**: teléfono postal (2), fecha de llegada previa del cónyuge, apto y código de área del preparador, y "otros nombres usados" (alias) no se pueden editar.

### Menores
8. `cat_withholding` (Convención contra la Tortura): el backend lo marca por defecto pero el checkbox aparece desmarcado en casos nuevos.
9. Hijos: si "tiene hijos" está en No pero hay hijos cargados (o al revés), no hay aviso; "Total de hijos" queda vacío en vez de 0.
10. Se escribe texto en la línea de firma del preparador (el formulario indica que no puede firmarse electrónicamente) y hay un mapeo muerto en la firma del Suplemento A.
11. Las pruebas no cubren cónyuge, hijos, dirección postal ni preparador (esas rutas nunca se ejecutaron).

## Plan de corrección

1. **Normalización canónica** (`app/schemas/i589.py`): validadores Pydantic para sexo (M/F), estado civil (single/married/divorced/widowed) y corte (never/now/not_now), aceptando cualquier variante en español/inglés. Aplica a solicitante, cónyuge e hijos; arregla UI y PDF.
2. **Extracción en inglés** (`app/ai/extractor.py`): prompt ya actualizado; añadir códigos canónicos y reiniciar el servidor para aplicarlo.
3. **Narrativa** (`config/i589_mapping.json` + `app/pdf/filler.py`): mapear solo el campo grande de continuación; si la narrativa supera ~3.000 caracteres, mostrar advertencia de "adjuntar páginas adicionales" en lugar de truncar.
4. **Pregunta C.2A/2B** (`app/pdf/filler.py`): concatenar las explicaciones de 2A y 2B en la caja compartida.
5. **UI** (`app/static/index.html`): añadir editor de entradas a EE. UU. (máx. 3), "otros nombres usados", teléfono postal, llegada previa del cónyuge, apto y área del preparador; nota de que los campos vacíos son opcionales; marcar "(opcional)" en etiquetas no críticas.
6. **Validación** (`app/validation.py`): residencia con calle y ciudad obligatorias; fecha de nacimiento parseable a fecha real; sin advertencia de cónyuge vacío; coherencia "tiene hijos"/lista; total de hijos 0 cuando corresponda.
7. **Firmas**: dejar de escribir en la línea de firma del preparador (firma manuscrita) y eliminar el mapeo muerto del Suplemento A.
8. **Default CAT**: checkbox marcado coherente desde el primer momento en casos nuevos.
9. **Pruebas**: nuevo fixture completo (cónyuge + 2 hijos + dirección postal + preparador) y pruebas de `build_values` para esas ramas; pruebas de normalización de códigos.
10. **Datos demo**: traducir el fixture al inglés, actualizar los casos demo y regenerar sus PDFs; re-extraer el caso "Extraído por IA" con el prompt nuevo.
11. **Guía del cliente** (`GUIA_CLIENTE.md` + PDF): explicar que el formulario final va en inglés y que los campos vacíos legítimos son normales.
12. **Verificación final**: pytest completo, extracción real con DeepSeek, generación de PDF (barcode intacto, campos editables), verificación programática de la narrativa en el campo correcto, reinicio de servidor/túnel y push a GitHub.

## Resultado esperado
- Sexo: "Femenino" · Estado civil: "Soltero/a" · Corte: "A. Nunca en corte" (sin "—").
- Formulario final 100% en inglés.
- Narrativa completa en el campo grande del Suplemento B.
- Todos los datos extraídos revisables y corregibles en la UI.