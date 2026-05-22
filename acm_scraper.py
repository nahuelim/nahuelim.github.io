"""
acm_scraper.py — Scraper on-demand para ACM.

Uso:
  python3.11 acm_scraper.py --url "https://www.zonaprop.com.ar/departamentos-venta-palermo-2-ambientes.html"
    --sup 55 --ambientes 2 [--cochera false] [--antiguedad 15] [--piso 4] [--disposicion Frente]

Flujo:
  1. Scrapea TODAS las páginas de la URL de búsqueda provista (sin límite)
  2. Parsea datos básicos del card: precio, m², ambientes, dirección, días publicado
  3. Calcula estadísticas del universo completo (mediana, IQR, outliers, días en mercado)
  4. Rankea todos los válidos por score de similitud al inmueble
  5. Entra al detalle de los Top 24 candidatos (datos enriquecidos)
  6. Devuelve JSON por stdout

Llamado por auto_ficha.py via subprocess.
"""

import asyncio
import re
import json
import sys
import argparse
import time
import random
import math
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout
from playwright_stealth import Stealth

BASE_URL  = "https://www.zonaprop.com.ar"
MIN_DELAY = 1.5
MAX_DELAY = 3.0
N_DETALLE = 12


# ─── Utilidades ───────────────────────────────────────────────────────────────

def _log(msg: str):
    print(f"[ACM] {msg}", file=sys.stderr, flush=True)


def _random_delay():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def _str2bool(s: str) -> bool:
    return str(s).lower() in ("true", "1", "yes", "si", "sí")


def _parse_precio_usd(s: str) -> Optional[float]:
    if not s:
        return None
    upper = s.strip().upper()
    if not any(c in upper for c in ["USD", "U$S", "US$", "U$D"]):
        return None
    nums = re.sub(r"[^0-9]", "", upper)
    return float(nums) if nums else None


def _parse_num(s: str, min_v=0, max_v=1e9) -> Optional[float]:
    if not s:
        return None
    m = re.search(r"[\d.,]+", str(s))
    if not m:
        return None
    raw = m.group(0)
    if "." in raw:
        parts = raw.split(".")
        if len(parts[-1]) == 3:
            raw = raw.replace(".", "")
    raw = raw.replace(",", ".")
    try:
        v = float(raw)
        return v if min_v <= v <= max_v else None
    except ValueError:
        return None


def _parse_int(s) -> Optional[int]:
    m = re.search(r"\d+", str(s) if s else "")
    return int(m.group(0)) if m else None


def _parse_dias(texto: str) -> Optional[int]:
    if not texto:
        return None
    t = texto.lower().strip()
    if "hoy" in t or "hace 0" in t:
        return 0
    m = re.search(r"hace\s+(\d+)\s+d[ií]a", t)
    if m:
        return int(m.group(1))
    m = re.search(r"hace\s+(\d+)\s+semana", t)
    if m:
        return int(m.group(1)) * 7
    m = re.search(r"hace\s+(\d+)\s+mes", t)
    if m:
        return int(m.group(1)) * 30
    return None


# ─── Scoring ──────────────────────────────────────────────────────────────────

def _calc_score(comp: dict, datos: dict) -> int:
    score = 0
    # Ambientes
    if datos.get("ambientes") and comp.get("ambientes"):
        if comp["ambientes"] == datos["ambientes"]:
            score += 25
        elif abs(comp["ambientes"] - datos["ambientes"]) == 1:
            score += 10
    # Superficie cubierta
    if datos.get("sup_cubierta") and comp.get("sup_cubierta"):
        ratio = comp["sup_cubierta"] / datos["sup_cubierta"]
        if 0.90 <= ratio <= 1.10:
            score += 20
        elif 0.80 <= ratio <= 1.20:
            score += 10
        elif 0.70 <= ratio <= 1.30:
            score += 4
    # Piso (solo disponible post-detalle)
    if datos.get("piso") is not None and comp.get("piso") is not None:
        if abs(comp["piso"] - datos["piso"]) <= 2:
            score += 10
    # Disposición
    if datos.get("disposicion") and comp.get("disposicion"):
        if datos["disposicion"].lower() in (comp["disposicion"] or "").lower():
            score += 10
    # Antigüedad — más preciso
    if datos.get("antiguedad") is not None and comp.get("antiguedad") is not None:
        diff = abs((comp["antiguedad"] or 0) - datos["antiguedad"])
        if diff <= 5:
            score += 12
        elif diff <= 15:
            score += 6
        elif diff <= 25:
            score += 2
    # Baños
    if datos.get("banos") and comp.get("banos"):
        if comp["banos"] == datos["banos"]:
            score += 10
        elif abs(comp["banos"] - datos["banos"]) == 1:
            score += 4
    # Frescura
    if comp.get("dias_publicado") is not None and comp["dias_publicado"] <= 30:
        score += 5
    return score


# ─── Playwright helpers ───────────────────────────────────────────────────────

async def _accept_cookies(page: Page):
    try:
        for sel in [
            'button:has-text("Aceptar")',
            'button:has-text("Aceptar todo")',
            'button:has-text("Accept")',
        ]:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await page.wait_for_timeout(900)
                return
    except Exception:
        pass


async def _handle_cloudflare(page: Page, timeout_s=90):
    try:
        for sel in [
            'iframe[src*="challenges.cloudflare"]',
            "#challenge-running",
            "#cf-challenge-running",
        ]:
            el = await page.query_selector(sel)
            if el:
                _log("⚠ Cloudflare — resolvé el captcha en la ventana del browser...")
                await page.wait_for_selector(sel, state="hidden", timeout=timeout_s * 1000)
                await page.wait_for_timeout(2000)
                return
    except Exception:
        pass


async def _get_next_page_url(page: Page) -> Optional[str]:
    try:
        current = await page.query_selector('[class*="paging-module__page-item-current"]')
        current_text = (await current.inner_text()).strip() if current else "1"
        links = await page.query_selector_all('a[href*="pagina"]')
        for link in links:
            texto = (await link.inner_text()).strip()
            href  = await link.get_attribute("href")
            if href and texto:
                try:
                    if int(texto) == int(current_text) + 1:
                        return href if href.startswith("http") else BASE_URL + href
                except ValueError:
                    continue
    except Exception:
        pass
    return None


# ─── Fase 1: scraping del listado ─────────────────────────────────────────────

async def _scrape_listing_page(page: Page, url: str) -> list:
    results = []
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all(
            '[class*="postingCardLayout-module__posting-card-layout"]'
        )
        _log(f"  {len(cards)} tarjetas.")

        for card in cards:
            try:
                item = {}

                link_el = await card.query_selector('a[href*="/propiedades/"]')
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href:
                        clean = href.split("?")[0]
                        item["url"] = clean if clean.startswith("http") else BASE_URL + clean
                if not item.get("url"):
                    continue

                precio_el = await card.query_selector('[class*="postingPrices-module__price"]')
                if precio_el:
                    item["precio_raw"] = (await precio_el.inner_text()).strip()

                dir_el = await card.query_selector(
                    '[class*="postingLocations-module__location-address"]'
                )
                if dir_el:
                    item["direccion"] = (await dir_el.inner_text()).strip()

                loc_el = await card.query_selector(
                    '[class*="postingLocations-module__location-title"]'
                )
                if loc_el:
                    item["barrio"] = (await loc_el.inner_text()).strip().split(",")[0]

                feat_els = await card.query_selector_all(
                    '[class*="postingMainFeatures-module__posting-main-features-span"]'
                )
                for fe in feat_els:
                    t  = (await fe.inner_text()).strip()
                    tl = t.lower()
                    if ("m²" in tl or "m2" in tl) and "sup_cubierta_raw" not in item:
                        item["sup_cubierta_raw"] = t
                    elif "amb" in tl and "ambientes_raw" not in item:
                        item["ambientes_raw"] = t
                    elif "dorm" in tl and "dormitorios_raw" not in item:
                        item["dormitorios_raw"] = t

                fecha_el = await card.query_selector(
                    '[class*="postingCardLayout-module__post-antiquity"]'
                )
                if fecha_el:
                    item["fecha_publicacion_raw"] = (await fecha_el.inner_text()).strip()

                results.append(item)

            except Exception:
                continue

    except PWTimeout:
        _log(f"Timeout listado: {url}")
    except Exception as e:
        _log(f"Error listado: {e}")
    return results


# ─── Fase 2: detalle del Top 24 ───────────────────────────────────────────────

async def _scrape_detail(page: Page, url: str) -> dict:
    data = {}
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        precio_el = await page.query_selector(".price-value")
        if precio_el:
            data["precio_raw"] = (await precio_el.inner_text()).strip()

        exp_el = await page.query_selector(".price-expenses")
        if exp_el:
            data["expensas_raw"] = (await exp_el.inner_text()).strip()

        loc_el = await page.query_selector(".section-location-property")
        if loc_el:
            loc_text = (await loc_el.inner_text()).strip()
            partes   = [p.strip() for p in loc_text.split(",")]
            if partes:
                data["direccion"] = partes[0]
            for idx in range(1, len(partes)):
                if not re.match(r'^\s*entre\b', partes[idx], re.IGNORECASE):
                    data["barrio_detalle"] = partes[idx]
                    break

        lis = await page.query_selector_all(".section-icon-features-property li")
        if not lis:
            lis = await page.query_selector_all(".section-main-features li")

        ORIENTACIONES = {"n", "s", "e", "o", "no", "ne", "so", "se", "nor", "sur"}
        for li in lis:
            t  = (await li.inner_text()).strip()
            tl = t.lower()
            if "m² tot" in tl or "m2 tot" in tl:
                data["sup_total_raw"] = t
            elif "m² cub" in tl or "m2 cub" in tl:
                data["sup_cubierta_raw"] = t
            elif "m² sem" in tl or "m2 sem" in tl:
                data["sup_semicubierta_raw"] = t
            elif ("m²" in tl or "m2" in tl) and "sup_cubierta_raw" not in data:
                data["sup_cubierta_raw"] = t
            elif "amb" in tl and "ambientes_raw" not in data:
                data["ambientes_raw"] = t
            elif "dorm" in tl and "dormitorios_raw" not in data:
                data["dormitorios_raw"] = t
            elif "baño" in tl and "toilet" not in tl:
                data["banos_raw"] = t
            elif re.match(r"^\d+\s*años?$", tl):
                data["antiguedad_raw"] = t
            elif any(x in tl for x in ["frente", "contrafrente", "interno", "lateral"]):
                data["disposicion"] = t.strip().capitalize()
            elif tl.strip() in ORIENTACIONES:
                data.setdefault("orientacion", t.upper())

        gen_els = await page.query_selector_all(
            '[class*="generalFeaturesProperty-module__description-text"]'
        )
        amenities = []
        for el in gen_els:
            t  = (await el.inner_text()).strip()
            tl = t.lower()
            if "cochera" in tl or "garage" in tl or "garaje" in tl:
                data["cochera"] = True
            elif "apto crédito" in tl or "apto credito" in tl:
                data.setdefault("tags", []).append("apto crédito")
            elif any(x in tl for x in [
                "pileta", "piscina", "parrilla", "quincho", "sum ",
                "gimnasio", "gym", "laundry", "sauna", "jacuzzi",
                "portero", "baulera",
            ]):
                amenities.append(t)

        amenity_els = await page.query_selector_all(
            '[class*="amenities"] li, [class*="Amenities"] li'
        )
        for ae in amenity_els:
            t = (await ae.inner_text()).strip()
            if t and len(t) < 100:
                amenities.append(t)
        data["amenities"] = list(dict.fromkeys(amenities))[:12]

        # Piso desde dirección
        dir_str = data.get("direccion", "")
        m = re.search(
            r'\b(\d{1,2})[°º]?\s*(?:piso|°|º)|\b(?:piso|p\.)\s*(\d{1,2})\b',
            dir_str, re.IGNORECASE
        )
        if m:
            piso_val = m.group(1) or m.group(2)
            if piso_val and int(piso_val) < 50:
                data["piso"] = int(piso_val)

        # Lat/Lng desde JSON-LD
        scripts = await page.query_selector_all('script[type="application/ld+json"]')
        for script in scripts:
            try:
                content = await script.inner_text()
                jdata   = json.loads(content)
                if isinstance(jdata, dict):
                    geo = (
                        jdata.get("geo")
                        or (jdata.get("location") or {}).get("geo")
                        or {}
                    )
                    if geo.get("latitude"):
                        data["lat"] = float(geo["latitude"])
                        data["lng"] = float(geo.get("longitude", 0))
                        break
            except Exception:
                pass

        # Fecha publicación en detalle
        for sel in [
            '[class*="postingCardLayout-module__post-antiquity"]',
            '[class*="userViews-module__post-antiquity"]',
            '[class*="post-antiquity"]',
        ]:
            fecha_el = await page.query_selector(sel)
            if fecha_el:
                data["fecha_publicacion_raw"] = (await fecha_el.inner_text()).strip()
                break

    except Exception as e:
        _log(f"Error detalle {url}: {e}")
    return data


# ─── Estadísticas del universo ────────────────────────────────────────────────

def _calc_universo_stats(validos: list, invalidos_count: int, sup_cubierta) -> dict:
    vals_m2 = [c["precio_por_m2"] for c in validos if c.get("precio_por_m2")]
    n = len(vals_m2)

    if n < 3:
        return {
            "n_total": n + invalidos_count, "n_validos": n,
            "n_invalidos": invalidos_count,
            "mediana_m2": 0, "p25": 0, "p75": 0,
            "iqr_lo": 0, "iqr_hi": 0, "n_outliers": 0,
            "precio_sugerido": 0, "rango_min": 0, "rango_max": 0,
            "dias_mediana": None, "dias_pct_30": 0,
            "dias_pct_90": 0, "dias_pct_mas90": 0,
            "señal_mercado": "Datos insuficientes.",
        }

    vals_s  = sorted(vals_m2)
    p25     = vals_s[n // 4]
    p75     = vals_s[(3 * n) // 4]
    mediana = (vals_s[n // 2] + vals_s[~(n // 2)]) / 2
    iqr     = p75 - p25
    iqr_lo  = p25 - 1.5 * iqr
    iqr_hi  = p75 + 1.5 * iqr
    n_out   = sum(1 for v in vals_m2 if v < iqr_lo or v > iqr_hi)

    sup = sup_cubierta or 0

    dias_list = [c["dias_publicado"] for c in validos if c.get("dias_publicado") is not None]
    dias_mediana = pct_30 = pct_90 = pct_mas90 = None
    if dias_list:
        dl = sorted(dias_list)
        nd = len(dl)
        dias_mediana = int((dl[nd // 2] + dl[~(nd // 2)]) / 2)
        pct_30    = round(sum(1 for d in dl if d <= 30)       / nd * 100)
        pct_90    = round(sum(1 for d in dl if 31 <= d <= 90) / nd * 100)
        pct_mas90 = round(sum(1 for d in dl if d > 90)        / nd * 100)

    if pct_mas90 and pct_mas90 >= 50:
        señal = (
            f"El {pct_mas90}% del stock lleva más de 90 días publicado. "
            "El mercado está rechazando los precios actuales. "
            "Publicar por debajo de la mediana es diferenciarse."
        )
    elif pct_30 and pct_30 >= 40:
        señal = (
            f"El {pct_30}% del stock lleva 30 días o menos. "
            "Rotación activa — el mercado absorbe bien a estos precios."
        )
    elif pct_30 is not None:
        señal = (
            f"Mercado mixto: {pct_30}% ≤30 días, {pct_90}% 31–90 días, "
            f"{pct_mas90}% >90 días. El precio y la presentación definen el tiempo de venta."
        )
    else:
        señal = "Sin datos de fecha de publicación suficientes para analizar la rotación."

    return {
        "n_total":        n + invalidos_count,
        "n_validos":      n,
        "n_invalidos":    invalidos_count,
        "mediana_m2":     round(mediana),
        "p25":            round(p25),
        "p75":            round(p75),
        "iqr_lo":         round(iqr_lo),
        "iqr_hi":         round(iqr_hi),
        "n_outliers":     n_out,
        "precio_sugerido":round(mediana * sup) if sup > 0 else 0,
        "rango_min":      round(p25 * sup)     if sup > 0 else 0,
        "rango_max":      round(p75 * sup)     if sup > 0 else 0,
        "dias_mediana":   dias_mediana,
        "dias_pct_30":    pct_30    or 0,
        "dias_pct_90":    pct_90    or 0,
        "dias_pct_mas90": pct_mas90 or 0,
        "señal_mercado":  señal,
    }


# ─── Orquestador ──────────────────────────────────────────────────────────────

async def scrape_comparables(
    search_url: str,
    sup_cubierta: Optional[float],
    ambientes: Optional[int],
    cochera: bool,
    antiguedad: Optional[int],
    piso: Optional[int],
    disposicion: Optional[str],
    banos: Optional[int] = None,
) -> dict:

    datos_prop = {
        "sup_cubierta": sup_cubierta,
        "ambientes":    ambientes,
        "antiguedad":   antiguedad,
        "piso":         piso,
        "disposicion":  disposicion,
        "banos":        banos,
    }

    raw_items = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1280,800",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="es-AR",
            timezone_id="America/Argentina/Buenos_Aires",
            extra_http_headers={
                "Accept-Language": "es-AR,es;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        page = await context.new_page()
        await stealth.apply_stealth_async(page)

        # ── Fase 1: scrapear TODAS las páginas de la URL provista ──
        _log(f"FASE 1 — URL: {search_url}")
        current_url = search_url
        page_num    = 1

        while current_url:
            _log(f"  Página {page_num}...")
            items = await _scrape_listing_page(page, current_url)

            if page_num == 1:
                await _handle_cloudflare(page)
                await _accept_cookies(page)
                if not items:
                    _log("  Reintentando...")
                    items = await _scrape_listing_page(page, current_url)

            if not items:
                _log("  Sin resultados — fin del listado.")
                break

            raw_items.extend(items)
            _log(f"  Acumulado: {len(raw_items)}")

            next_url = await _get_next_page_url(page)
            if not next_url:
                _log("  Última página.")
                break

            current_url = next_url
            page_num   += 1
            _random_delay()

        _log(f"FASE 1 COMPLETA — {len(raw_items)} tarjetas.")

        # ── Parseo y limpieza ──
        seen_urls = set()
        validos   = []
        invalidos = []

        for item in raw_items:
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            precio = _parse_precio_usd(item.get("precio_raw", ""))
            sup    = _parse_num(item.get("sup_cubierta_raw", ""), 10, 2000)

            if not precio:
                invalidos.append({"url": url, "motivo": "sin precio USD"})
                continue
            if not sup:
                invalidos.append({"url": url, "motivo": "sin superficie"})
                continue
            if precio < 10_000 or precio > 20_000_000:
                invalidos.append({"url": url, "motivo": f"precio fuera de rango: {int(precio)}"})
                continue

            comp = {
                "url":              url,
                "direccion":        item.get("direccion", ""),
                "barrio":           item.get("barrio", ""),
                "precio":           precio,
                "sup_cubierta":     sup,
                "sup_total":        None,
                "sup_semicubierta": None,
                "ambientes":        _parse_int(item.get("ambientes_raw", "")),
                "dormitorios":      _parse_int(item.get("dormitorios_raw", "")),
                "banos":            None,
                "piso":             None,
                "disposicion":      None,
                "orientacion":      None,
                "cochera":          False,
                "expensas":         None,
                "amenities":        [],
                "antiguedad":       None,
                "lat":              None,
                "lng":              None,
                "precio_por_m2":    round(precio / sup, 2),
                "dias_publicado":   _parse_dias(item.get("fecha_publicacion_raw", "")),
                "detalle_completo": False,
            }
            validos.append(comp)

        _log(f"Válidos: {len(validos)} | Inválidos: {len(invalidos)}")

        # Deduplicación
        seen_dedup = set()
        deduped    = []
        for comp in validos:
            dir_key   = (comp.get("direccion") or "")[:15].lower().strip()
            key       = (int(comp["precio"]), int(comp["sup_cubierta"]), dir_key)
            if key not in seen_dedup:
                seen_dedup.add(key)
                deduped.append(comp)
        if len(validos) - len(deduped):
            _log(f"Deduplicados: {len(validos) - len(deduped)}")
        validos = deduped

        # Outliers IQR
        vals_m2 = [c["precio_por_m2"] for c in validos]
        if len(vals_m2) >= 4:
            vs  = sorted(vals_m2)
            n   = len(vs)
            p25 = vs[n // 4]
            p75 = vs[(3 * n) // 4]
            iqr = p75 - p25
            lo, hi = p25 - 1.5 * iqr, p75 + 1.5 * iqr
            for comp in validos:
                pm2 = comp["precio_por_m2"]
                comp["es_outlier"]     = pm2 < lo or pm2 > hi
                comp["outlier_motivo"] = "alto" if pm2 > hi else ("bajo" if pm2 < lo else "")

        # Score preliminar sobre todos los válidos
        for comp in validos:
            comp["_score"] = _calc_score(comp, datos_prop)

        # Top 12 candidatos (sin outliers) + resto para paginación
        no_outliers        = [c for c in validos if not c.get("es_outlier")]
        sorted_cands       = sorted(no_outliers, key=lambda c: c["_score"], reverse=True)
        top12              = sorted_cands[:N_DETALLE]
        candidatos_rest    = sorted_cands[N_DETALLE:]  # los que siguen, sin detalle aún
        top24_urls         = {c["url"] for c in top12}  # compatibilidad nombre

        # ── Fase 2: detalle del Top 12 ──
        _log(f"FASE 2 — Detalle de {len(top12)} candidatos...")
        for i, comp in enumerate(top12):
            _log(f"  [{i+1}/{len(top12)}] {comp['url'].split('/')[-1][:65]}")
            detail = await _scrape_detail(page, comp["url"])

            if detail.get("precio_raw"):
                p = _parse_precio_usd(detail["precio_raw"])
                if p:
                    comp["precio"] = p
                    if comp.get("sup_cubierta"):
                        comp["precio_por_m2"] = round(p / comp["sup_cubierta"], 2)

            if detail.get("sup_cubierta_raw"):
                s = _parse_num(detail["sup_cubierta_raw"], 10, 2000)
                if s:
                    comp["sup_cubierta"]  = s
                    comp["precio_por_m2"] = round(comp["precio"] / s, 2)

            for field, raw_key, parser, min_v, max_v in [
                ("sup_total",        "sup_total_raw",        _parse_num, 10, 5000),
                ("sup_semicubierta", "sup_semicubierta_raw", _parse_num,  0,  500),
                ("expensas",         "expensas_raw",         _parse_num,  0, 2_000_000),
            ]:
                if detail.get(raw_key):
                    v = parser(detail[raw_key], min_v, max_v)
                    if v is not None:
                        comp[field] = v

            for field, raw_key in [
                ("ambientes",   "ambientes_raw"),
                ("dormitorios", "dormitorios_raw"),
                ("banos",       "banos_raw"),
                ("antiguedad",  "antiguedad_raw"),
            ]:
                if detail.get(raw_key):
                    v = _parse_int(detail[raw_key])
                    if v is not None:
                        comp[field] = v

            for field in ("piso", "disposicion", "orientacion", "lat", "lng"):
                if detail.get(field) is not None:
                    comp[field] = detail[field]

            if detail.get("cochera"):
                comp["cochera"] = True

            if detail.get("amenities"):
                comp["amenities"] = detail["amenities"]

            if detail.get("fecha_publicacion_raw") and comp.get("dias_publicado") is None:
                comp["dias_publicado"] = _parse_dias(detail["fecha_publicacion_raw"])

            comp["detalle_completo"] = True
            comp["_score"] = _calc_score(comp, datos_prop)

            _random_delay()

        await browser.close()

    # Re-ordenar por score final
    top24.sort(key=lambda c: c["_score"], reverse=True)

    # Limpiar campos internos
    for comp in top12:
        comp.pop("_score", None)
        comp.pop("es_outlier", None)
        comp.pop("outlier_motivo", None)

    # Lista de outliers para mostrar en la app
    outliers_list = [
        {
            "url":          c["url"],
            "direccion":    c["direccion"],
            "barrio":       c["barrio"],
            "precio":       c["precio"],
            "precio_m2":    c["precio_por_m2"],
            "sup_cubierta": c["sup_cubierta"],
            "motivo":       c.get("outlier_motivo", ""),
        }
        for c in validos if c.get("es_outlier")
    ]

    universo_stats = _calc_universo_stats(
        validos=[c for c in validos if not c.get("es_outlier")],
        invalidos_count=len(invalidos),
        sup_cubierta=sup_cubierta,
    )

    _log(
        f"LISTO — Universo: {universo_stats['n_total']} | "
        f"Válidos: {universo_stats['n_validos']} | "
        f"Outliers: {len(outliers_list)} | "
        f"Candidatos: {len(top24)}"
    )

    # Candidatos restantes: solo datos del card (sin detalle), para paginación
    for c in candidatos_rest:
        c.pop("_score", None)
        c.pop("es_outlier", None)
        c.pop("outlier_motivo", None)

    return {
        "universo_stats":      universo_stats,
        "outliers":            outliers_list,
        "candidatos":          top12,
        "candidatos_restantes": candidatos_rest,
        "datos_prop":          datos_prop,
    }



# ─── Detalle bajo demanda (batch adicional) ────────────────────────────────────

async def scrape_detalle_batch(urls: list, datos_prop: dict) -> list:
    """
    Entra al detalle de una lista de URLs adicionales (siguiente batch de candidatos).
    Llamado via /acm/mas-candidatos cuando el usuario pide "Ver próximos 12".
    Devuelve la lista enriquecida con scores recalculados.
    """
    results = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1280,800",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="es-AR",
            timezone_id="America/Argentina/Buenos_Aires",
        )
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        page = await context.new_page()
        await stealth.apply_stealth_async(page)

        await _handle_cloudflare(page)

        for i, comp in enumerate(urls):
            url = comp.get("url") if isinstance(comp, dict) else comp
            _log(f"  [batch {i+1}/{len(urls)}] {str(url).split('/')[-1][:65]}")
            detail = await _scrape_detail(page, url)

            if isinstance(comp, dict):
                enriched = dict(comp)
            else:
                enriched = {"url": url}

            if detail.get("precio_raw"):
                p = _parse_precio_usd(detail["precio_raw"])
                if p:
                    enriched["precio"] = p
                    if enriched.get("sup_cubierta"):
                        enriched["precio_por_m2"] = round(p / enriched["sup_cubierta"], 2)

            if detail.get("sup_cubierta_raw"):
                s = _parse_num(detail["sup_cubierta_raw"], 10, 2000)
                if s:
                    enriched["sup_cubierta"]  = s
                    if enriched.get("precio"):
                        enriched["precio_por_m2"] = round(enriched["precio"] / s, 2)

            for field, raw_key, parser, mn, mx in [
                ("sup_total",        "sup_total_raw",        _parse_num, 10, 5000),
                ("sup_semicubierta", "sup_semicubierta_raw", _parse_num,  0,  500),
                ("expensas",         "expensas_raw",         _parse_num,  0, 2_000_000),
            ]:
                if detail.get(raw_key):
                    v = parser(detail[raw_key], mn, mx)
                    if v is not None:
                        enriched[field] = v

            for field, raw_key in [
                ("ambientes",  "ambientes_raw"),
                ("dormitorios","dormitorios_raw"),
                ("banos",      "banos_raw"),
                ("antiguedad", "antiguedad_raw"),
            ]:
                if detail.get(raw_key):
                    v = _parse_int(detail[raw_key])
                    if v is not None:
                        enriched[field] = v

            for field in ("piso", "disposicion", "orientacion", "lat", "lng"):
                if detail.get(field) is not None:
                    enriched[field] = detail[field]

            if detail.get("cochera"):
                enriched["cochera"] = True

            if detail.get("amenities"):
                enriched["amenities"] = detail["amenities"]

            if detail.get("fecha_publicacion_raw") and not enriched.get("dias_publicado"):
                enriched["dias_publicado"] = _parse_dias(detail["fecha_publicacion_raw"])

            enriched["detalle_completo"] = True
            enriched["_score"] = _calc_score(enriched, datos_prop)
            results.append(enriched)
            _random_delay()

        await browser.close()

    results.sort(key=lambda c: c["_score"], reverse=True)
    for c in results:
        c.pop("_score", None)
    return results


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ACM Scraper")
    parser.add_argument("--url",         required=False, default=None, help="URL de búsqueda de ZonaProp")
    parser.add_argument("--batch-file",  required=False, default=None, dest="batch_file",
                        help="JSON file con candidatos para scrape de detalle batch")
    parser.add_argument("--sup",         type=float, default=0,    dest="sup_cubierta")
    parser.add_argument("--ambientes",   type=int,   default=None)
    parser.add_argument("--cochera",     default="false")
    parser.add_argument("--antiguedad",  type=int,   default=None)
    parser.add_argument("--piso",        type=int,   default=None)
    parser.add_argument("--disposicion", default=None)
    parser.add_argument("--banos",       type=int,   default=None)
    args = parser.parse_args()

    async def main():
        if args.batch_file:
            # Modo batch: entra al detalle de una lista de candidatos
            import os
            with open(args.batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            candidatos  = batch_data.get('candidatos', [])
            datos_prop  = batch_data.get('datos_prop', {})
            enriched    = await scrape_detalle_batch(candidatos, datos_prop)
            print(json.dumps({'candidatos': enriched}, ensure_ascii=False))
        else:
            if not args.url:
                print("ERROR: --url es requerido si no se usa --batch-file", file=sys.stderr)
                sys.exit(1)
            result = await scrape_comparables(
                search_url   = args.url,
                sup_cubierta = args.sup_cubierta if args.sup_cubierta > 0 else None,
                ambientes    = args.ambientes,
                cochera      = _str2bool(args.cochera),
                antiguedad   = args.antiguedad,
                piso         = args.piso,
                disposicion  = args.disposicion,
                banos        = args.banos,
            )
            print(json.dumps(result, ensure_ascii=False))

    asyncio.run(main())
