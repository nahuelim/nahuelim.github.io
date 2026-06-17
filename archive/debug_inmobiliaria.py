#!/usr/bin/env python3
"""
debug_inmobiliaria.py
Script de debug temporal — imprime todo lo relacionado a
publisher/inmobiliaria/agency en el avisoInfo de una ficha ZonaProp.

Uso:
  python3 debug_inmobiliaria.py "URL_DE_ZONAPROP"

Requiere Playwright (--visible, igual que el scraper).
"""

import sys
import re
import json
from playwright.sync_api import sync_playwright

def main(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    # Extraer avisoInfo
    m = re.search(r'const avisoInfo\s*=\s*(\{.*?\})\s*\n\s*const dataLayerInfo', html, re.DOTALL)
    if not m:
        print("❌ No encontré avisoInfo")
        return

    raw = m.group(1)

    # Buscar todas las ocurrencias de palabras clave relacionadas a inmobiliaria
    keywords = ['publisher', 'inmobiliaria', 'agency', 'advertiser', 'realEstate', 'broker', 'seller', 'company']

    print("=== Búsqueda de campos relacionados a inmobiliaria ===\n")
    for kw in keywords:
        # Buscar el keyword y mostrar 200 caracteres de contexto
        for m2 in re.finditer(re.escape(kw), raw, re.IGNORECASE):
            start = max(0, m2.start() - 30)
            end = min(len(raw), m2.end() + 200)
            snippet = raw[start:end]
            print(f"--- '{kw}' encontrado ---")
            print(snippet)
            print()

    # Intentar parsear como JSON para navegar estructura (puede fallar por trailing commas)
    print("\n=== Intento de parseo JSON (puede fallar) ===")
    try:
        # Limpiar comillas simples a dobles de forma básica para JSON
        cleaned = raw.replace("'", '"')
        data = json.loads(cleaned)
        # Buscar recursivamente
        def buscar(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_path = f"{path}.{k}"
                    if any(kw.lower() in k.lower() for kw in keywords):
                        print(f"{new_path} = {v}")
                    buscar(v, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    buscar(item, f"{path}[{i}]")
        buscar(data)
    except Exception as e:
        print(f"No se pudo parsear como JSON: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 debug_inmobiliaria.py 'URL'")
        sys.exit(1)
    main(sys.argv[1])
