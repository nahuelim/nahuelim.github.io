#!/bin/bash
set -e

DATOS="${1:-input/datos.txt}"
PORTAL="${2:-input/portal.html}"

# Verificar que existe datos.txt
if [ ! -f "$DATOS" ]; then
  echo "❌ No encontré $DATOS"
  exit 1
fi

# Generar la ficha
if [ -f "$PORTAL" ]; then
  python3 generate.py "$DATOS" "$PORTAL"
else
  python3 generate.py "$DATOS"
fi

# Subir a GitHub
git add fichas/
git commit -m "ficha: $(ls -t fichas/*.html | head -1 | xargs basename)"
git push

echo "✓ Publicada en nahuelim.com.ar/fichas/"