#!/usr/bin/env python3
"""
dump_avisoinfo.py
Descarga una ficha de ZonaProp con Playwright y dumpea el avisoInfo
de forma legible (key: tipo, valor truncado) para análisis.

Uso:
  python3 dump_avisoinfo.py "URL_DE_ZONAPROP"
"""

import sys
import re
from playwright.sync_api import sync_playwright


def main(url):
    print("Descargando HTML con Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    m = re.search(r'const avisoInfo\s*=\s*(\{.*?\})\s*\n\s*const dataLayerInfo', html, re.DOTALL)
    if not m:
        print("No encontre avisoInfo")
        return

    raw = m.group(1)

    # Encontrar todos los pares 'key': valor a nivel superficial
    # Esto es best-effort, no es un parser JSON real (el JS tiene comillas simples,
    # trailing commas, y valores sin comillas como false/true/numeros)

    print(f"\navisoInfo tiene {len(raw)} caracteres\n")
    print("=" * 70)

    # Buscar todas las claves de primer y segundo nivel
    # Patron: 'clave': seguido de string, numero, true/false, [ o {
    pattern = re.compile(r"'(\w+)'\s*:\s*('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|\[|\{|true|false|\d+(?:\.\d+)?|null)")

    nivel = 0
    for m2 in pattern.finditer(raw):
        key = m2.group(1)
        val = m2.group(2)

        # Calcular nivel de indentacion aproximado contando llaves antes de esta posicion
        antes = raw[:m2.start()]
        nivel = antes.count('{') - antes.count('}')

        indent = "  " * nivel

        if val in ('[', '{'):
            print(f"{indent}{key}: <{'lista' if val == '[' else 'objeto'}>")
        else:
            val_corto = val[:80] + ('...' if len(val) > 80 else '')
            print(f"{indent}{key}: {val_corto}")


if __name__ == "__main__":
    main(sys.argv[1])
