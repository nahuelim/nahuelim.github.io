# auto_ficha — Generador automático de fichas

## Setup (una sola vez)

```bash
# 1. Copiar los archivos al repo
cp auto_ficha.py ~/Documents/nahuelim.github.io/
cp generate_template.py ~/Documents/nahuelim.github.io/

# 2. Instalar dependencias (en el venv del scraper o globalmente)
pip install flask requests beautifulsoup4

# 3. Correr
cd ~/Documents/nahuelim.github.io
python auto_ficha.py
```

Abre http://localhost:5050

---

## Flujo por portal

### ZonaProp ✦ Automático completo
1. Pegá la URL → Extraer
2. Revisá los datos (editá si algo está mal)
3. Generar y publicar → copiás el link

### MercadoLibre
1. Pegá la URL → Extraer (datos básicos)
2. Completá lo que falta
3. Copiá las fotos a `assets/fotos/barrio-direccion/` con nombres `foto-1.webp`, `foto-2.webp`, etc.
4. Generar y publicar

### Century 21
Igual que MercadoLibre.

### Manual
Directamente al formulario, sin URL.

---

## Fotos para ML/C21

El slug de la carpeta se forma automáticamente: `barrio-direccion`.  
Ejemplo: `caballito-av-avellaneda-1100/`

La app detecta automáticamente las fotos `.webp`, `.jpg`, `.png` en esa carpeta.  
También podés pegar URLs externas directamente en el campo de fotos.

---

## Notas técnicas

- El TEMPLATE HTML se importa de tu `generate.py` existente → los cambios en el template se reflejan automáticamente
- Git push se hace con SSH (sin contraseña) desde `~/Documents/nahuelim.github.io`
- GitHub Pages tarda ~30 segundos en publicar tras el push
