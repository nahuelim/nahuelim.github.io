# ACM Form — Working Notes

State of play for iterating on `acm-form.html` / `acm_report.py` / `acm_scraper.py`.
Paste this file's contents (or just say "see ACM_NOTES.md") at the start of a
new chat instead of re-explaining history.

## Done (commit 62c4115, 2026-09-28)
- Form: "Agente" -> "Asesor" (campo, login, badge). Cocina en la fila de 3; Baños+Toilette abajo.
- Espacio exterior: siempre fue multi-select; el tilde no se veía en Safari por
  `-webkit-appearance:none` en `.field input`. Fix: esa regla excluye checkboxes.
- Estado (1–10, sin texto) con leyenda por eje "qué tiene que hacer el comprador":
  9–10 a estrenar/poca antigüedad impecable · 7–8 lista para habitar (incluye reciclados)
  · 5–6 habitable con trabajos menores · 3–4 trabajos importantes · 1–2 puesta en valor integral.
  Misma escala en testigos. En PDF solo el número (sin "/10").
- Testigos: Dir · m² hom · Valor USD · USD/m² (auto = valor÷m², editable) · Estado · Días pub. · Link.
  PDF: días >90 en rojo + nota ("precio no validado por la demanda").
- S8: Publicados / Cierres (red C21), solo mín–máx en TOTAL USD (sin promedios); USD/m² auto
  sobre la m² hom. de la propiedad (editable). PDF: barras sobre escala común + nota red C21.
  Margen de negociación es dato de la red (hoy 5–8%). Tendencia: select, default "En alza".
- S9: Rango de Venta (verde) / Prueba (amarillo) / Espera (rojo, "Más de X", sin techo).
  Prellenados desde S8 (Venta = cierres; Prueba = cierre máx→publicado máx; Espera > publicado máx),
  editables; criterio solo en nota interna. Campo "Conclusión de valor" → bloque destacado en PDF.
  PDF: bloque "Qué pasa si se publica por encima de la ventana" (4 puntos + valor vs tiempo).
- PDF: marca nueva (verde #005941, logo nl-lockup-crema, íconos verdes, foto nahuel-perfil.webp),
  numeración dinámica, intro de ACM + textos cortos por sección, "m²" se imprimía como "m"
  (helvetica sin ²) → se imprime "m2". Secciones no se parten entre páginas.
- Nueva página fija "¿Por qué trabajar conmigo?": checklist 10 servicios vs Inmob. 1/2
  (todos confirmados por Nahuel; incluye reporte de consultas/visitas = compromiso escrito).
- Borradores viejos siguen cargando (mapeo de vend_m2_* → vend_tot_* y ventana vieja → rangos).

## Deferred / next up (pick ONE per new chat)
1. **Calendario de estrategia dinámica (cliente-facing):** tabla semanas 1–2 / 3–5 / 6–9 / 10–13 / 14–18
   con valor por etapa + criterios de reajuste (0 consultas −15%, pocas −10%, sin reservas −5%).
   Hoy solo es callout interno en S9. Referencia: ACM ejemplo C21 (Campichuelo 244).
2. **Análisis presupuestario** (valor probable − gastos de venta ~6%), para quien vende para comprar.
3. **Testigos autofill por URL** (requiere puente Mac→Sheets; el form estático no puede scrapear).
4. **Proceso de reporte de consultas/visitas**: ya está prometido en el PDF, falta armarlo.
5. `acm_scraper.py` NO está conectado al form — descartado por ahora.

## Key files
- `acm-form.html` — TODO vive acá: form (HTML), lógica (JS) y generador del PDF (jsPDF). Un solo archivo.
- `acm_report.py` — generador .docx aparte. NO conectado al form.
- `acm_scraper.py` — scraping + stats. NO conectado al form (el form es estático en GitHub Pages).

## Mapa de acm-form.html (buscar por estos nombres, NO por número de línea)
**Arriba del archivo**
- `:root { --primary ... }` — colores de marca del form (verde #005941).
- `.acm-cards`, `.rango-card.verde/.amarillo/.rojo` — CSS de las cards de S8 y S9.
- `const IMG_NL / IMG_C21 / IMG_WA / IMG_IG / IMG_MAIL / IMG_FOTO` — imágenes del PDF en base64.
  Para cambiarlas: rasterizar el asset (logo = `assets/nl-lockup-crema.svg`, foto = `assets/nahuel-perfil.webp`
  recortada en círculo 360px) y reemplazar el string. `AR_NL` = ancho/alto del logo.

**Secciones del form (HTML)** — cada una es `<div class="section" id="...">`
- `sec-1` Datos del cliente (campo `agente`, label "Asesor") · `sec-2` Contextual · `sec-3` Propiedad
  (`prop_estado` 1–10, `.espacio-libre` checkboxes) · `sec-4` Características · `sec-5` Objeciones
- `sec-6` Comparables → filas creadas por `addTestigoRow()`; ids `t_dir_N, t_sup_N, t_tot_N, t_m2_N, t_estado_N, t_dias_N, t_link_N`
- `sec-reporte` (S7) Reporte Inmobiliario
- `sec-8` Mercado → `pub_tot_min/max`, `pub_m2_min/max`, `vend_tot_min/max`, `vend_m2_min/max`, `acm_dias`, `acm_margen`, `acm_tendencia`
- `sec-9` Ventana → `v_conclusion`, `v_venta_min/max`, `v_prueba_min/max`, `v_espera`, `precio_acordado`, `compromisos`
- `sec-agent` Modo Asesor (privado, nunca va al PDF)

**Lógica (JS)**
- `num(v)` parsea "169.000" → 169000 · `fmt(v)` formatea es-AR.
- Patrón auto+editable: `setAuto(id,v)` solo escribe si el campo NO tiene `dataset.manual`;
  el `oninput` del campo pone `dataset.manual='1'` cuando lo tocás a mano.
- `calcTestigoM2(n)` USD/m² de un comparable · `calcHom()` m² homogénea · `calcAcmM2()` USD/m² de S8 → llama a `calcRangos()` (prellena S9).
- `collect()` arma el objeto de datos (lo que se guarda en borradores/Sheets y usa el PDF).
- `populateForm(d)` carga un borrador. **Si cambiás/renombrás un campo, agregá el mapeo acá** para que los borradores viejos sigan cargando (ya hay ejemplos: `vend_m2_*` viejo → `vend_tot_*`, ventana vieja → rangos).
- `resetForm()` limpia todo · `saveDraft()` / `loadDraftsFromSheets()` borradores (localStorage + webhook Apps Script).
- `PDF_SECCIONES` + `injectPdfToggles()` — tildes "PDF" por sección.

**PDF — dentro de `function generatePDF()`, en orden:**
- Colores `PR,PG,PB` (verde) y `OR,OG,OB` (dorado acento). `header()` logos · `checkY(n)` salta de página si no entran n mm.
- Helpers: `secN('TÍTULO')` = título numerado automático · `secTitle()` sin número · `intro(txt)` texto explicativo · `note(txt)` itálica · `grid(pairs)` pares etiqueta/valor.
- Orden: título + intro ACM → PREPARADO PARA → PROPIEDAD (+ `escalaConservacion()`, leyenda `ESCALA`) → CARACTERÍSTICAS → OBJECIONES → PROPIEDADES COMPARABLES (+nota >90 días) → MARKET VALUATION → ANÁLISIS DE MERCADO (barras) → VENTANA DE VENTA (conclusión, cards, bloque `IMP` "qué pasa si…") → ¿POR QUÉ TRABAJAR CONMIGO? (lista `SERV`, página propia) → CONTACTO → footer legal.
- Textos fijos del PDF: buscarlos directo (ej. `IMP=`, `SERV=`, `ESCALA=`, `intro('`).
- Para que una sección no se parta entre páginas: `checkY(alto_estimado)` justo antes de su `secN(...)`.

**Trampas conocidas**
- helvetica de jsPDF NO tiene "²": `generatePDF` reemplaza ² → 2 (textos y datos). No uses otros caracteres raros (✓, emojis) en el PDF: dibujalos (ver checks de `SERV`).
- Safari/iPad: estilos de inputs genéricos rompen checkboxes → `.field input:not([type=checkbox])`.
- El texto legal del footer dice "agentes" a propósito (texto legal C21, no tocar).

## Cómo probar antes de pushear
- Abrir `acm-form.html` en el browser (localmente), completar datos de ejemplo, "Finalizar" → revisar el PDF.
- Revisar en iPad/Safari los checkboxes y las cards (layout a 1 columna < 640px).
- Cargar un borrador viejo para confirmar que `populateForm` sigue funcionando.

## Data sources (validated, real)
- Colegio de Escribanos CABA — escrituras stats (linked in-app now, see above).
- Colegio de Escribanos PBA — same, for Quilmes-area work if relevant.
- BCRA — crédito hipotecario stats.
- Reporte Inmobiliario — CABA valuation index (already used).
- No MLS in Argentina — no mandatory closing-price disclosure, so "vendidos"
  data is always an agent estimate, never verified — call this out to clients
  rather than presenting it as fact (already done, see Section 8 above).

## Git/deploy notes
- Repo: `nahuelim/nahuelim.github.io`, branch `main`, deploy automático con GitHub Pages (~1–2 min).
- Local edit ≠ live: commit + push. Verificar en nahuelim.com.ar/acm-form.html (iPad: recargar por caché).
- Si Claude trabaja desde la nube y pushea: después hacer `git pull` en la Mac antes de editar nada.
- Este archivo (`ACM_NOTES.md`) NO está en git — vive solo en la Mac.
- `.git/index.lock: File exists` → verificar que no haya git corriendo (`ps aux | grep git`); si no hay,
  `rm .git/index.lock`. Causa confirmada: una sesión de Claude corriendo git sobre esta carpeta sin permiso
  de borrado deja el lock trabado. Claude no debe correr git en la carpeta local de la Mac.
