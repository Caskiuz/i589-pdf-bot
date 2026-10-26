# Corrección: los datos no se veían en Adobe Acrobat (capa XFA)

## Causa raíz
El I-589 oficial es un PDF **híbrido XFA + AcroForm**. El sistema rellena la capa AcroForm y genera las apariencias correctamente (verificado: 137 campos con valor, 100% con apariencia dibujada), pero **Adobe Acrobat da prioridad a la capa XFA vacía**, por lo que muestra el formulario como si estuviera en blanco. En Chrome/Edge/MuPDF sí se ve rellenado. Además, el sistema nunca modifica el PDF original de USCIS: siempre crea una copia nueva (comportamiento correcto que se mantendrá).

## Cambios
1. `app/pdf/filler.py`: añadir `drop_xfa` al comando de pdftk (`fill_form … output … drop_xfa`), eliminando la capa XFA para que Acrobat muestre los campos rellenados.
2. Verificación post-generación: sin XFA, 137 campos con valor y apariencias intactas, JavaScript del código de barras conservado, 12 páginas, campos editables (sin aplanar).
3. `tests/test_fixes.py`: prueba que el PDF generado no contiene XFA y conserva valores/apariencias.
4. Regenerar el PDF demo y verificar en el visor del navegador y por extracción de texto.
5. Actualizar `GUIA_CLIENTE.md` y su PDF: el sistema genera una copia nueva (no altera el original) y el PDF se visualiza correctamente en Acrobat Reader.
6. Commit y push. La comprobación final en Acrobat la hace el cliente (esta PC no tiene Adobe instalado); se le pide abrir el PDF regenerado y confirmar que ve los datos y el código de barras.