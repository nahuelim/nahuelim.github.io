#!/usr/bin/env python3
"""
test_inmobiliaria.py
Llama a extraer_zonaprop() del auto_ficha.py real y muestra
exactamente qué devuelve en 'inmobiliaria'.

Uso (desde la carpeta nahuelim.github.io):
  python3 test_inmobiliaria.py "URL_DE_ZONAPROP"
"""

import sys
import importlib.util
from pathlib import Path

# Importar auto_ficha.py como módulo
spec = importlib.util.spec_from_file_location("auto_ficha", Path(__file__).parent / "auto_ficha.py")
auto_ficha = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auto_ficha)

def main(url):
    datos = auto_ficha.extraer_zonaprop(url)
    print("=== Campos clave ===")
    print(f"direccion:    {datos.get('direccion')}")
    print(f"barrio:       {datos.get('barrio')}")
    print(f"tipo:         {datos.get('tipo')}")
    print(f"inmobiliaria: '{datos.get('inmobiliaria')}'")
    print()
    print("=== Todas las keys disponibles ===")
    print(sorted(datos.keys()))

if __name__ == "__main__":
    main(sys.argv[1])
