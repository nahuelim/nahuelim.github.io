#!/usr/bin/env python3
"""
agregar_swipe.py — Corrige touch swipe en fichas ya generadas.
Correr desde: ~/Documents/2. Inmobiliaria/nahuelim.github.io/
"""

from pathlib import Path
import re

FICHAS_DIR = Path(__file__).parent / "fichas"

SWIPE_NUEVO = """
/* Touch swipe — mosaico principal (abre lightbox) */
(function(){let x0=null,y0=null,locked=null;const el=document.querySelector('.mosaic');if(!el)return;el.addEventListener('touchstart',e=>{x0=e.touches[0].clientX;y0=e.touches[0].clientY;locked=null;},{passive:true});el.addEventListener('touchmove',e=>{if(x0===null)return;const dx=e.touches[0].clientX-x0;const dy=e.touches[0].clientY-y0;if(locked===null)locked=Math.abs(dx)>Math.abs(dy)?'h':'v';if(locked==='h')e.preventDefault();},{passive:false});el.addEventListener('touchend',e=>{if(x0===null)return;const dx=e.changedTouches[0].clientX-x0;const dy=e.changedTouches[0].clientY-y0;if(locked==='h'&&Math.abs(dx)>30){if(!document.getElementById('lb').classList.contains('open'))openLB(dx<0?1:0);}x0=null;y0=null;locked=null;},{passive:true});})();
/* Touch swipe — lightbox */
(function(){let x0=null,y0=null,locked=null;const el=document.getElementById('lb');if(!el)return;el.addEventListener('touchstart',e=>{x0=e.touches[0].clientX;y0=e.touches[0].clientY;locked=null;},{passive:true});el.addEventListener('touchmove',e=>{if(x0===null)return;const dx=e.touches[0].clientX-x0;const dy=e.touches[0].clientY-y0;if(locked===null)locked=Math.abs(dx)>Math.abs(dy)?'h':'v';if(locked==='h')e.preventDefault();},{passive:false});el.addEventListener('touchend',e=>{if(x0===null)return;const dx=e.changedTouches[0].clientX-x0;const dy=e.changedTouches[0].clientY-y0;if(locked==='h'&&Math.abs(dx)>30)lbGo(dx<0?1:-1);x0=null;y0=null;locked=null;},{passive:true});})();"""

# El keydown listener completo — sin swipe insertado en el medio
KEYDOWN = "document.addEventListener('keydown',e=>{if(!document.getElementById('lb').classList.contains('open'))return;if(e.key==='ArrowLeft')lbGo(-1);if(e.key==='ArrowRight')lbGo(1);if(e.key==='Escape')closeLB();});"

def limpiar_y_reinsertar(content):
    """
    1. Elimina cualquier swipe existente (viejo o roto)
    2. Reconstruye el keydown correcto
    3. Inserta el swipe nuevo después
    """
    # Eliminar cualquier bloque swipe existente
    content = re.sub(
        r'\n?/\* Touch swipe[^*]*\*/\n?\(function\(\).*?\}\)\(\);',
        '',
        content,
        flags=re.DOTALL
    )

    # Reconstruir keydown roto — puede haberse partido
    # Patrón: buscar fragmento del keydown y reconstruirlo completo
    # Caso 1: keydown partido (termina sin });)
    roto = re.search(
        r"(document\.addEventListener\('keydown'.*?closeLB\(\);\}\);?)",
        content,
        re.DOTALL
    )
    if roto:
        keydown_actual = roto.group(1).strip()
        if not keydown_actual.endswith(');'):
            # Está roto, reemplazar con versión correcta
            content = content.replace(keydown_actual, KEYDOWN)
        elif keydown_actual != KEYDOWN:
            content = content.replace(keydown_actual, KEYDOWN)

    # Insertar swipe nuevo después del keydown completo
    if KEYDOWN in content and "Touch swipe" not in content:
        content = content.replace(KEYDOWN, KEYDOWN + SWIPE_NUEVO, 1)

    return content

def main():
    fichas = list(FICHAS_DIR.glob("*.html"))
    if not fichas:
        print("No se encontraron fichas en", FICHAS_DIR)
        return

    actualizadas = 0
    errores = 0

    for f in sorted(fichas):
        try:
            content = f.read_text(encoding="utf-8")

            # Verificar si tiene swipe nuevo correcto Y keydown intacto
            tiene_swipe_ok = "Touch swipe — mosaico principal" in content
            keydown_ok = KEYDOWN in content

            if tiene_swipe_ok and keydown_ok:
                continue

            nuevo = limpiar_y_reinsertar(content)

            if nuevo != content:
                f.write_text(nuevo, encoding="utf-8")
                actualizadas += 1
                print(f"  ✓ {f.name}")

        except Exception as e:
            print(f"  ✗ {f.name}: {e}")
            errores += 1

    print(f"\nListo — {actualizadas} actualizadas · {errores} errores")
    if actualizadas > 0:
        print("Corré: git add fichas/ && git commit -m 'fix: swipe mobile v2' && git push")

if __name__ == "__main__":
    main()
