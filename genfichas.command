#!/bin/bash
cd "$HOME/Documents/2. Inmobiliaria/nahuelim.github.io"

# Buscar Python con requests disponible
if [ -f "$HOME/Documents/2. Inmobiliaria/zonaprop_scraper/venv/bin/python" ]; then
  PYTHON="$HOME/Documents/2. Inmobiliaria/zonaprop_scraper/venv/bin/python"
elif command -v python3 &>/dev/null; then
  PYTHON=python3
else
  PYTHON=python
fi

# Instalar dependencias si faltan
$PYTHON -m pip install flask requests beautifulsoup4 -q 2>/dev/null || true

# Matar instancia anterior
lsof -ti:5050 | xargs kill -9 2>/dev/null || true
sleep 1

# Levantar servidor
$PYTHON auto_ficha.py &

# Esperar hasta que responda (máx 15s)
for i in {1..15}; do
  sleep 1
  if curl -s http://127.0.0.1:5050 > /dev/null 2>&1; then
    open http://127.0.0.1:5050
    break
  fi
done

wait
