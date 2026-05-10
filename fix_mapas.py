#!/usr/bin/env python3
"""
fix_mapas.py
Actualiza la URL del mapa Y el texto de dirección en todas las fichas HTML publicadas.
Correr desde: ~/Documents/2. Inmobiliaria/nahuelim.github.io/
"""

import re
from pathlib import Path
from urllib.parse import quote, unquote

FICHAS_DIR = Path(__file__).parent / "fichas"

def limpiar_direccion(direccion: str) -> str:
    """Convierte 'Juncal al 3700' → 'Juncal 3700'"""
    return re.sub(r'\bal\s+(\d+)', r'\1', direccion, flags=re.IGNORECASE).strip()

def _cargar_maps_key() -> str:
    from pathlib import Path
    key_file = Path.home() / "Documents" / "2. Inmobiliaria" / ".maps_api_key"
    if key_file.exists():
        return key_file.read_text().strip()
    raise RuntimeError(f"No encontré la Google Maps API key en {key_file}")

MAPS_API_KEY = _cargar_maps_key()

def nueva_mapa_url(dir_limpia: str, barrio: str) -> str:
    q = quote(f"{dir_limpia}, {barrio}, Buenos Aires, Argentina")
    return f"https://www.google.com/maps/embed/v1/place?key={MAPS_API_KEY}&q={q}&zoom=17"

def procesar_ficha(path: Path) -> dict:
    html = path.read_text(encoding='utf-8')
    cambios = []

    # ── 1. Fix URL del mapa ─────────────────────────────────────────────────
    m_iframe = re.search(r'<iframe src="(https?://(?:maps\.google\.com|www\.google\.com/maps)[^"]+)"', html)
    if m_iframe:
        url_actual = m_iframe.group(1)
        q_match = re.search(r'[?&]q=([^&]+)', url_actual)
        if q_match:
            q_decoded = unquote(q_match.group(1))
            partes    = [p.strip() for p in q_decoded.split(',')]
            direccion = partes[0] if partes else ''
            barrio    = partes[1] if len(partes) > 1 else ''
            dir_limpia = limpiar_direccion(direccion)
            url_nueva  = nueva_mapa_url(dir_limpia, barrio)
            if url_actual != url_nueva:
                html = html.replace(f'src="{url_actual}"', f'src="{url_nueva}"', 1)
                cambios.append(f"mapa: {direccion} → {dir_limpia}")

    # ── 2. Fix texto de dirección visible ───────────────────────────────────
    # Busca cualquier "PALABRA al NNNN" en el HTML y lo convierte a "PALABRA NNNN"
    # Solo aplica dentro de tags de contenido, no en URLs ni atributos
    patron = re.compile(r'(\b[A-Za-záéíóúÁÉÍÓÚüÜñÑ\.]+\s+al\s+\d+)', re.IGNORECASE)

    def reemplazar_en_texto(m):
        original = m.group(1)
        limpio   = limpiar_direccion(original)
        return limpio

    # Aplicar solo fuera de atributos HTML (src=, href=, content=, etc.)
    def fix_texto_visible(html_str):
        resultado = []
        i = 0
        while i < len(html_str):
            # Si estamos dentro de un tag, no tocar
            if html_str[i] == '<':
                fin_tag = html_str.find('>', i)
                if fin_tag == -1:
                    resultado.append(html_str[i:])
                    break
                resultado.append(html_str[i:fin_tag+1])
                i = fin_tag + 1
            else:
                # Estamos en texto visible — aplicar limpieza
                fin_texto = html_str.find('<', i)
                if fin_texto == -1:
                    texto = html_str[i:]
                    resultado.append(patron.sub(reemplazar_en_texto, texto))
                    break
                texto = html_str[i:fin_texto]
                nuevo_texto = patron.sub(reemplazar_en_texto, texto)
                if nuevo_texto != texto:
                    cambios.append(f"texto: '{texto.strip()[:50]}' → '{nuevo_texto.strip()[:50]}'")
                resultado.append(nuevo_texto)
                i = fin_texto
        return ''.join(resultado)

    html_nuevo = fix_texto_visible(html)

    if not cambios:
        return {'path': path, 'cambios': 0}

    path.write_text(html_nuevo, encoding='utf-8')
    return {'path': path, 'cambios': len(cambios), 'detalle': cambios}

def main():
    if not FICHAS_DIR.exists():
        print(f"❌ No encontré el directorio: {FICHAS_DIR}")
        return

    fichas = list(FICHAS_DIR.glob("*.html"))
    print(f"Fichas encontradas: {len(fichas)}")

    actualizadas = 0
    sin_cambios  = 0
    errores      = 0

    for path in sorted(fichas):
        try:
            r = procesar_ficha(path)
            if r['cambios'] > 0:
                actualizadas += 1
                print(f"  ✅ {path.name}")
                for d in r.get('detalle', []):
                    print(f"     · {d}")
            else:
                sin_cambios += 1
        except Exception as e:
            errores += 1
            print(f"  ❌ {path.name}: {e}")

    print(f"\nResumen:")
    print(f"  Actualizadas:  {actualizadas}")
    print(f"  Sin cambios:   {sin_cambios}")
    print(f"  Errores:       {errores}")
    print(f"\nSi todo OK:")
    print(f"  git add fichas/ && git commit -m 'fix: direccion sin al, mapa pin exacto' && git push")

if __name__ == "__main__":
    main()
