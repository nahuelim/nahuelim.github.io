#!/usr/bin/env python3
"""
agregar_swipe.py — Agrega touch swipe a fichas ya generadas.
Correr desde: ~/Documents/2. Inmobiliaria/nahuelim.github.io/
Uso: python3 agregar_swipe.py
"""

from pathlib import Path

FICHAS_DIR = Path(__file__).parent / "fichas"

BUSCAR = "document.addEventListener('keydown',e=>{if(!document.getElementById('lb').classList.contains('open'))return;if(e.key==='ArrowLeft')lbGo(-1);if(e.key==='ArrowRight')lbGo(1);if(e.key==='Escape')closeLB();});"

SWIPE = """
/* Touch swipe — slider principal */
(function(){let x0=null;const el=document.getElementById('slider');el.addEventListener('touchstart',e=>{x0=e.touches[0].clientX;},{passive:true});el.addEventListener('touchend',e=>{if(x0===null)return;const dx=e.changedTouches[0].clientX-x0;if(Math.abs(dx)>50)sGo(dx<0?1:-1);x0=null;},{passive:true});})();
/* Touch swipe — lightbox */
(function(){let x0=null;const el=document.getElementById('lb');el.addEventListener('touchstart',e=>{x0=e.touches[0].clientX;},{passive:true});el.addEventListener('touchend',e=>{if(x0===null)return;const dx=e.changedTouches[0].clientX-x0;if(Math.abs(dx)>50)lbGo(dx<0?1:-1);x0=null;},{passive:true});})();"""

def main():
    fichas = list(FICHAS_DIR.glob("*.html"))
    if not fichas:
        print("No se encontraron fichas en", FICHAS_DIR)
        return

    actualizadas = 0
    ya_tenian = 0
    errores = 0

    for f in sorted(fichas):
        try:
            content = f.read_text(encoding="utf-8")
            if "Touch swipe" in content:
                ya_tenian += 1
                continue
            if BUSCAR not in content:
                print(f"  ⚠ Sin marker: {f.name}")
                errores += 1
                continue
            nuevo = content.replace(BUSCAR, BUSCAR + SWIPE, 1)
            f.write_text(nuevo, encoding="utf-8")
            actualizadas += 1
            print(f"  ✓ {f.name}")
        except Exception as e:
            print(f"  ✗ Error en {f.name}: {e}")
            errores += 1

    print(f"\nListo — {actualizadas} actualizadas · {ya_tenian} ya tenían swipe · {errores} errores")
    if actualizadas > 0:
        print("\nAhora corré: git add fichas/ && git commit -m 'swipe: fichas existentes' && git push")

if __name__ == "__main__":
    main()
