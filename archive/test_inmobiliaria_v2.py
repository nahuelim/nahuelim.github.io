#!/usr/bin/env python3
"""
test_inmobiliaria_v2.py
1. Descarga el HTML con Playwright (--visible, como el scraper)
2. Corre la misma lógica de extraccion de auto_ficha.py sobre ese HTML
3. Muestra el resultado de 'inmobiliaria'

Uso:
  python3 test_inmobiliaria_v2.py "URL_DE_ZONAPROP"
"""

import sys
import re
import importlib.util
from pathlib import Path
from playwright.sync_api import sync_playwright

# Importar auto_ficha.py como módulo (para usar detectar_badges si hace falta)
spec = importlib.util.spec_from_file_location("auto_ficha", Path(__file__).parent / "auto_ficha.py")
auto_ficha = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auto_ficha)


def main(url):
    print("Descargando HTML con Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    print(f"HTML descargado: {len(html)} caracteres\n")

    # Extraer avisoInfo — misma regex que extraer_zonaprop
    m = re.search(r'const avisoInfo\s*=\s*(\{.*?\})\s*\n\s*const dataLayerInfo', html, re.DOTALL)
    if not m:
        print("❌ No encontré avisoInfo en el HTML")
        return

    raw = m.group(1)
    print(f"avisoInfo extraído: {len(raw)} caracteres\n")

    # Aplicar EXACTAMENTE el mismo regex que está en auto_ficha.py línea 883-888
    pub_m = re.search(r"'publisher'\s*:\s*\{[^}]*'name'\s*:\s*'([^']+)'", raw)
    if not pub_m:
        pub_m = re.search(r'"realEstateAgency"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', raw)
    if not pub_m:
        pub_m = re.search(r'"advertiser"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', raw)

    inmobiliaria = pub_m.group(1).strip() if pub_m else ''

    print(f"=== RESULTADO ===")
    print(f"pub_m matcheo: {'SI' if pub_m else 'NO'}")
    print(f"inmobiliaria: '{inmobiliaria}'")

    if not pub_m:
        # Mostrar contexto alrededor de 'publisher' en raw para debug
        idx = raw.find("'publisher'")
        if idx == -1:
            idx = raw.find('"publisher"')
        if idx >= 0:
            print(f"\nContexto en raw alrededor de 'publisher' (pos {idx}):")
            print(repr(raw[idx:idx+250]))
        else:
            print("\n'publisher' no aparece en raw en absoluto")


if __name__ == "__main__":
    main(sys.argv[1])
