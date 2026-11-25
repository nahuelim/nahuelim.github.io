# Fichas

Cada archivo `.html` es una ficha publicada en nahuelim.com.ar/fichas/. Las arma el generador (`auto_ficha.py`), que además agrega una fila en la pestaña FICHAS del Sheet.

## Cambiar un dato de una ficha

La página y la fila del Sheet **no están conectadas**: un cambio va en los dos lados.

- **Página:** editar el archivo de esta carpeta (precio: `<div class="price">` y las dos `description` de arriba, que usa WhatsApp para la vista previa).
- **Sheet (lo que usa el CRM):** editar el valor en la fila de FICHAS. Nunca agregar, borrar ni mover columnas. **No cambiar LINK NL**: con ese link el CRM sabe a quién ya se la mandaste. LINK OG (el aviso original) sí se puede cambiar.
- El CRM toma los cambios del Sheet en hasta 10 minutos (o al toque con `limpiarCache()` en Apps Script).
- No volver a generar una ficha que ya existe: duplica la fila en FICHAS.
