#!/bin/bash
set -e

DATOS="${1:-input/datos.txt}"
PORTAL="${2:-input/portal.html}"

# Verificar que existe datos.txt
if [ ! -f "$DATOS" ]; then
  echo "❌ No encontré $DATOS"
  exit 1
fi

# Subir fotos nuevas si hay (para ML/Argenprop)
if [ -n "$(git status --porcelain assets/fotos/ 2>/dev/null)" ]; then
  echo "📸 Subiendo fotos nuevas..."
  git add assets/fotos/
  git commit -m "fotos: $(ls -t assets/fotos/ | head -1)"
  git push
  echo "✓ Fotos subidas"
fi

# Generar la ficha
if [ -f "$PORTAL" ]; then
  python3 generate.py "$DATOS" "$PORTAL"
else
  python3 generate.py "$DATOS"
fi

# Subir ficha generada
git add fichas/
git commit -m "ficha: $(ls -t fichas/*.html | head -1 | xargs basename)"
git push

echo "✓ Publicada en nahuelim.com.ar/fichas/"