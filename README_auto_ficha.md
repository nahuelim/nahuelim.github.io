# auto_ficha — Generador de Fichas

## Setup (una sola vez)

```bash
# 1. Copiar archivos al repo
cp auto_ficha.py ~/Documents/nahuelim.github.io/
cp generate_template.py ~/Documents/nahuelim.github.io/

# 2. Instalar dependencias
pip install flask requests beautifulsoup4

# 3. Dar permisos al launcher
chmod +x ~/Documents/nahuelim.github.io/abrir_fichas.command
```

---

## Uso diario

Doble clic en **abrir_fichas.command** → abre el browser en `http://127.0.0.1:5050`

Para cerrar el servidor, cerrás la ventana de terminal que se abre.

---

## Flujo por portal

### ZonaProp — Automático completo
1. Seleccioná **ZonaProp**
2. Pegá la URL del aviso
3. Click en **Extraer** → se completa todo automáticamente (datos + fotos)
4. Revisá y editá lo que necesites
5. Click en **Generar y publicar** → te devuelve el link listo

### MercadoLibre — Semi-automático
1. Abrí la propiedad en el browser
2. `Cmd+S` → **Webpage, HTML Only** → guardá en Downloads
3. Seleccioná **MercadoLibre** en la app
4. Pegá el path completo al archivo guardado:
   `/Users/nahuellim/Downloads/nombre-archivo.html`
5. Click en **Extraer** → se completa todo (datos + fotos en alta resolución desde el CDN de ML)
6. Revisá, completá lo que falte, click en **Generar y publicar**

> Las fotos de ML se sirven directamente desde su CDN — no hace falta descargarlas ni subirlas al repo.

### Century 21 — Semi-automático
1. Abrí la propiedad en el browser
2. `Cmd+S` → **Webpage, HTML Only** → guardá en Downloads
3. Seleccioná **Century 21** en la app
4. Pegá el path completo al archivo guardado
5. Click en **Extraer** → se completan título, descripción, barrio, tipo y fotos disponibles
6. Completá el **precio** manualmente (no está en el HTML estático)
7. Para fotos adicionales: copiá los archivos a `assets/fotos/tipo-barrio-direccion/`
8. Click en **Generar y publicar**

### Manual — Sin URL
1. Seleccioná **Manual**
2. Completá todos los campos a mano
3. Para fotos: pegá URLs externas o copiá archivos a `assets/fotos/tipo-barrio-direccion/`
4. Click en **Generar y publicar**

---

## Formato del slug (nombre del archivo)

```
tipo-barrio-direccion-Xamb.html
```

Ejemplos:
- `ph-caballito-espinosa-1400-4amb.html`
- `dto-palermo-armenia-2100-3amb.html`
- `casa-belgrano-vuelta-de-obligado-850-6amb.html`

Si ya existe una ficha con el mismo nombre, se agrega un hash de 4 caracteres:
- `ph-caballito-espinosa-1400-4amb-a3f1.html`

---

## Fotos para C21 / Manual

La carpeta de fotos se forma con el mismo slug que el archivo:

```
~/Documents/nahuelim.github.io/assets/fotos/tipo-barrio-direccion/
```

Las fotos pueden llamarse como quieras — la app las detecta automáticamente por extensión (`.webp`, `.jpg`, `.jpeg`, `.png`).

---

## Editar una ficha publicada

1. Abrís el `.html` en `~/Documents/nahuelim.github.io/fichas/` con VSCode
2. Editás lo que necesitás
3. Desde terminal:
```bash
cd ~/Documents/nahuelim.github.io
git add fichas/
git commit -m "edit: nombre-ficha.html"
git push
```

GitHub Pages tarda ~30 segundos en actualizarse.
