# Marca · Nahuel Lim

Referencia única de la marca personal. Si algo acá contradice otro lugar (Drive, artifact), manda este archivo.

- **Design system visual:** https://claude.ai/artifact/NEtMoHjK4t3s2o8z6gNZk8
- **Assets en uso:** carpeta `assets/` de este repo, publicados en `https://nahuelim.com.ar/assets/<archivo>`
- **Copia de respaldo:** Google Drive → carpeta "Marca · Nahuel Lim" (el lockup de ahí es la versión vieja en Fraunces; el vigente es el de este repo)

## Regla de contraste: AAA

Todo texto cumple WCAG AAA: 7:1 texto normal, 4,5:1 texto grande (24px+, o 19px+ en negrita).

Válidas a cualquier tamaño:
- `tinta`, `tinta-suave`, `verde-profundo` o `dorado-oscuro` sobre `crema`, `blanco` o `verde-claro`
- `sobre-verde` sobre `verde-profundo`
- `dorado` o `crema` sobre `tinta`

Solo desde 24px: `verde` sobre fondos claros, `sobre-verde` sobre `verde`. `dorado` sobre fondos claros o sobre verde: nunca como texto.

## Color

| Token | Hex | Uso |
|---|---|---|
| crema | `#F7F4EC` | Fondo por defecto (no blanco) |
| blanco | `#FFFFFF` | Tarjetas elevadas, firma C21 |
| verde-claro | `#E3EEE9` | Separar secciones |
| linea | `#DDD6C6` | Bordes y líneas finas |
| tinta | `#14231D` | Texto principal; fondo de navbar, hero y footer |
| tinta-suave | `#434C47` | Texto secundario |
| verde | `#006A4E` | Color de marca: logo, bloques grandes, títulos 24px+ |
| verde-profundo | `#005941` | Verde para texto chico y botones con texto chico |
| sobre-verde | `#F7F4EC` | Texto sobre verde-profundo |
| dorado | `#BEAF87` | Relentless Gold (compartido con C21). Decorativo; texto solo sobre tinta |
| dorado-oscuro | `#5B4700` | Dorado legible: etiquetas, cifras, links sobre claro |

Proporción orientativa: 60% crema/blanco, 30% verde/tinta, 10% dorado.

## Tipografía

- **Fraunces 300** para titulares y precios (números alineados, no estilo antiguo). No pasar de 500.
- **Inter** para todo lo demás: texto, etiquetas, botones, direcciones, características de fichas.
- Google Fonts: `family=Fraunces:opsz,wght@9..144,300..500&family=Inter:wght@400;500;600;700`
- No usar Cormorant ni Playfair.

## Logo

- **Lockup** (`nl-lockup-*.svg`, `nl-logo.svg`): monograma NL + "Nahuel Lim" en Inter + "ASESOR INMOBILIARIO" al mismo ancho que el nombre. Vectorizado (no depende de fuentes).
- **Monograma** (`nl-mono-*.svg`): la N y la L como dos edificios.
- Versiones: `verde` sobre claro (principal) · `crema` sobre verde o tinta · `dorado` solo sobre tinta · `tinta` para impresión a un color.
- `favicon.svg`: NL crema sobre cuadrado verde.
- No rotar, estirar, ni agregar sombras o degradados. Mínimo 24px de alto.

## Century 21

- Siempre "Century 21 Evolución", nunca "Century 21" solo.
- Logo C21 en sus colores (`c21-*-crema`, `-dorado`, `-tinta`). `c21-evolucion-*` alineado a la izquierda; `c21-evolucion-centro-*` centrado.
- En la web: "Parte de" + logo C21 Evolución.
- Firma legal: **Century 21 Evolución · Karina Carrasquero · CUCICBA 9135**
- El manual de C21 es orientativo, no regla.

## Inventario de `assets/`

| Archivo | Qué es |
|---|---|
| `nl-logo.svg` | Lockup crema (navbar y footer de web/fichas) |
| `nl-lockup-{verde,crema,tinta}.svg` | Lockup en cada color |
| `nl-mono-{verde,crema,tinta,dorado}.svg` | Monograma solo |
| `favicon.svg` | Favicon |
| `c21-logo{,-dorado,-tinta}.svg` | Sello C21 solo (`c21-logo.svg` = crema) |
| `c21-evolucion-{crema,dorado,tinta}.svg` | C21 + "Evolución", alineado a izquierda |
| `c21-evolucion-centro-{crema,dorado,tinta}.svg` | Ídem, centrado (tarjeta de contacto en fichas) |
| `hero-nahuel.webp` | Foto del hero de la web |
| `nahuel-perfil.webp` | Retrato de "Sobre mí" |
| `profile.jpg` | Avatar 480px (fichas, todas) |
| `nahuelim{1,2,3}.{jpg,webp}` | Fotos anteriores (jpg originales pesados; webp comprimidos) |

## Dónde se aplica

- `index.html` — web
- `template_ficha.py` (auto_ficha) y `generate.py` (publicar.sh) — fichas nuevas. Las ~257 fichas viejas mantienen el diseño anterior.
- `acm-form.html` — formulario ACM
