"""
acm_scraper.py — Scraper on-demand para ACM con geocodificación y scoring.
Uso: python3.11 acm_scraper.py --direccion "Av. Corrientes 4676" --barrio "Almagro"
       --tipo departamento --ambientes 2 --sup 40 --antiguedad 60
       --piso 3 --disposicion "Frente" --cochera false --sup-semi 0 --apto-credito false
Devuelve JSON por stdout.
"""

import asyncio
import re
import json
import sys
import unicodedata
import argparse
import time
import random
import math
import urllib.request
import urllib.parse
from pathlib import Path

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout
from playwright_stealth import Stealth

BASE_URL = "https://www.zonaprop.com.ar"
MAPS_KEY_FILE           = Path.home() / "Documents" / "2. Inmobiliaria" / ".maps_api_key_geocoding"
MAPS_KEY_FILE_FALLBACK  = Path.home() / "Documents" / "2. Inmobiliaria" / ".maps_api_key"
MIN_DELAY = 1.8
MAX_DELAY = 3.5
MAX_PAGINAS = 5


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_maps_key() -> str:
    if MAPS_KEY_FILE.exists():
        return MAPS_KEY_FILE.read_text().strip()
    if MAPS_KEY_FILE_FALLBACK.exists():
        return MAPS_KEY_FILE_FALLBACK.read_text().strip()
    return ""


def _log(msg: str):
    print(f"[ACM] {msg}", file=sys.stderr, flush=True)


def _slugify(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_s = nfkd.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9\s-]", "", ascii_s.lower().strip())
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


def _build_url(tipo: str, barrio: str, ambientes: int) -> str:
    slug = _slugify(barrio)
    tipo_l = tipo.lower()
    if tipo_l == "departamento":
        if 1 <= ambientes <= 4:
            return f"{BASE_URL}/departamentos-venta-{slug}-{ambientes}-ambientes.html"
        return f"{BASE_URL}/departamentos-venta-{slug}.html"
    elif tipo_l == "ph":
        return f"{BASE_URL}/ph-venta-{slug}.html"
    elif tipo_l == "casa":
        return f"{BASE_URL}/casas-venta-{slug}.html"
    return f"{BASE_URL}/departamentos-venta-{slug}.html"


def _geocode(address: str, api_key: str):
    """Returns (lat, lng) or None."""
    if not api_key:
        return None
    try:
        q = urllib.parse.quote(address)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={q}&key={api_key}"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return float(loc["lat"]), float(loc["lng"])
    except Exception:
        pass
    return None


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in meters using Haversine formula."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _parse_precio_usd(s: str):
    if not s:
        return None
    upper = s.strip().upper()
    if not any(c in upper for c in ["USD", "U$S", "US$", "U$D"]):
        return None
    nums = re.sub(r"[^0-9]", "", upper)
    return float(nums) if nums else None


def _parse_num(s: str, min_v: float = 0, max_v: float = 1e9):
    if not s:
        return None
    m = re.search(r"[\d.,]+", str(s))
    if not m:
        return None
    raw = m.group(0)
    if "." in raw:
        parts = raw.split(".")
        if len(parts[-1]) == 3:  # dot = thousands separator (Argentine format)
            raw = raw.replace(".", "")
    raw = raw.replace(",", ".")
    try:
        v = float(raw)
        return v if min_v <= v <= max_v else None
    except ValueError:
        return None


def _parse_int(s: str):
    m = re.search(r"\d+", str(s) if s else "")
    return int(m.group(0)) if m else None


def _str2bool(s: str) -> bool:
    return str(s).lower() in ("true", "1", "yes", "si", "sí")


def _random_delay():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


# ─── Playwright helpers ────────────────────────────────────────────────────────

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


async def _handle_cloudflare(page: Page, timeout_s: int = 90):
    try:
        for sel in [
            'iframe[src*="challenges.cloudflare"]',
            "#challenge-running",
            "#cf-challenge-running",
        ]:
            el = await page.query_selector(sel)
            if el:
                _log("⚠ Cloudflare detectado — resolvé el captcha en la ventana del browser...")
                await page.wait_for_selector(sel, state="hidden", timeout=timeout_s * 1000)
                await page.wait_for_timeout(2000)
                return
    except Exception:
        pass


async def _scrape_listing_page(page: Page, url: str, barrio_default: str) -> list:
    results = []
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=35000)
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all(
            '[class*="postingCardLayout-module__posting-card-layout"]'
        )
        _log(f"  {len(cards)} tarjetas en {url.split('/')[-1]}")

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
                item["barrio"] = (
                    (await loc_el.inner_text()).strip() if loc_el else barrio_default
                )

                feat_els = await card.query_selector_all(
                    '[class*="postingMainFeatures-module__posting-main-features-span"]'
                )
                for fe in feat_els:
                    t = (await fe.inner_text()).strip()
                    tl = t.lower()
                    if ("m²" in tl or "m2" in tl) and "sup_cubierta_raw" not in item:
                        item["sup_cubierta_raw"] = t
                    elif "amb" in tl and "ambientes_raw" not in item:
                        item["ambientes_raw"] = t
                    elif "dorm" in tl and "dormitorios_raw" not in item:
                        item["dormitorios_raw"] = t

                results.append(item)
            except Exception:
                continue

    except PWTimeout:
        _log(f"Timeout: {url}")
    except Exception as e:
        _log(f"Error listado: {e}")
    return results


async def _get_next_page_url(page: Page):
    try:
        current = await page.query_selector('[class*="paging-module__page-item-current"]')
        current_text = (await current.inner_text()).strip() if current else "1"
        links = await page.query_selector_all('a[href*="pagina"]')
        for link in links:
            texto = (await link.inner_text()).strip()
            href = await link.get_attribute("href")
            if href and texto:
                try:
                    if int(texto) == int(current_text) + 1:
                        return href if href.startswith("http") else BASE_URL + href
                except ValueError:
                    continue
    except Exception:
        pass
    return None


async def _scrape_detail(page: Page, url: str) -> dict:
    """Scrapes a detail page for enriched data (called only for Top 3)."""
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
            partes = [p.strip() for p in loc_text.split(",")]
            if partes:
                data["direccion"] = partes[0]

        lis = await page.query_selector_all(".section-icon-features-property li")
        if not lis:
            lis = await page.query_selector_all(".section-main-features li")

        ORIENTACIONES = {"n", "s", "e", "o", "no", "ne", "so", "se", "nor", "sur"}
        for li in lis:
            t = (await li.inner_text()).strip()
            tl = t.lower()
            if "m² cub" in tl or "m2 cub" in tl:
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

        # Cochera / piso desde general features
        gen_els = await page.query_selector_all(
            '[class*="generalFeaturesProperty-module__description-text"]'
        )
        amenities = []
        for el in gen_els:
            t = (await el.inner_text()).strip()
            tl = t.lower()
            if "cochera" in tl or "garage" in tl or "garaje" in tl:
                data["cochera"] = True
            elif any(x in tl for x in [
                "pileta", "piscina", "parrilla", "quincho", "sum ", "gimnasio",
                "gym", "laundry", "sauna", "jacuzzi", "portero", "baulera",
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

        # Lat/Lng from JSON-LD
        scripts = await page.query_selector_all('script[type="application/ld+json"]')
        for script in scripts:
            try:
                content = await script.inner_text()
                jdata = json.loads(content)
                if isinstance(jdata, dict):
                    geo = jdata.get("geo") or (jdata.get("location") or {}).get("geo") or {}
                    if geo.get("latitude"):
                        data["lat"] = float(geo["latitude"])
                        data["lng"] = float(geo.get("longitude", 0))
                        break
            except Exception:
                pass

    except Exception as e:
        _log(f"Error detalle {url}: {e}")
    return data


# ─── Scoring ──────────────────────────────────────────────────────────────────

def _calc_score(comp: dict, datos: dict) -> int:
    score = 0
    if datos.get("ambientes") and comp.get("ambientes") == datos["ambientes"]:
        score += 30
    if datos.get("sup_cubierta") and comp.get("sup_cubierta"):
        ratio = comp["sup_cubierta"] / datos["sup_cubierta"]
        if 0.90 <= ratio <= 1.10:
            score += 20
        elif 0.80 <= ratio <= 1.20:
            score += 10
    if datos.get("piso") is not None and comp.get("piso") is not None:
        if abs(comp["piso"] - datos["piso"]) <= 2:
            score += 15
    if datos.get("disposicion") and comp.get("disposicion"):
        if datos["disposicion"].lower() in (comp["disposicion"] or "").lower():
            score += 15
    if datos.get("cochera") is not None and comp.get("cochera") is not None:
        if bool(comp["cochera"]) == bool(datos["cochera"]):
            score += 10
    if datos.get("antiguedad") is not None and comp.get("antiguedad") is not None:
        if abs((comp["antiguedad"] or 0) - datos["antiguedad"]) <= 10:
            score += 10
    return score


# ─── Stats ────────────────────────────────────────────────────────────────────

def _calc_stats(filtered: list, sup_cubierta, radio: int, n_total_antes_iqr: int) -> dict:
    vals = [c["precio_por_m2"] for c in filtered if c.get("precio_por_m2")]
    n_usados = len(vals)

    if len(vals) < 3:
        return {
            "mediana_m2": 0, "p25": 0, "p75": 0,
            "n_total": n_total_antes_iqr, "n_usados": n_usados,
            "radio_metros": radio, "stock_barrio": n_total_antes_iqr,
            "precio_sugerido": 0, "rango_min": 0, "rango_max": 0,
        }

    vals_s = sorted(vals)
    n = len(vals_s)
    p25 = vals_s[n // 4]
    p75 = vals_s[(3 * n) // 4]
    nf = len(vals_s)
    mediana = (vals_s[nf // 2] + vals_s[~(nf // 2)]) / 2

    sup = sup_cubierta or 0
    return {
        "mediana_m2": round(mediana),
        "p25": round(p25),
        "p75": round(p75),
        "n_total": n_total_antes_iqr,
        "n_usados": n_usados,
        "radio_metros": radio,
        "stock_barrio": n_total_antes_iqr,
        "precio_sugerido": round(mediana * sup) if sup > 0 else 0,
        "rango_min": round(p25 * sup) if sup > 0 else 0,
        "rango_max": round(p75 * sup) if sup > 0 else 0,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

async def scrape_comparables(
    direccion: str,
    barrio: str,
    tipo: str,
    ambientes: int,
    sup_cubierta,
    antiguedad,
    piso,
    disposicion,
    cochera: bool,
    sup_semicubierta,
    apto_credito: bool,
) -> dict:

    maps_key = _load_maps_key()
    datos_prop = {
        "ambientes": ambientes or None,
        "sup_cubierta": sup_cubierta,
        "piso": piso,
        "disposicion": disposicion,
        "cochera": cochera,
        "antiguedad": antiguedad,
    }

    # PASO A: Geocodificar la propiedad analizada (obligatorio antes de abrir browser)
    full_addr = f"{direccion}, {barrio}, Buenos Aires, Argentina"
    _log(f"Geocodificando propiedad: {full_addr}")
    origin = _geocode(full_addr, maps_key)
    if not origin:
        _log("ERROR: No se pudo geocodificar la dirección de la propiedad analizada.")
        sys.exit(1)
    olat, olng = origin
    _log(f"Coordenadas origen: ({olat:.6f}, {olng:.6f})")

    # 2. Build URL
    search_url = _build_url(tipo, barrio, ambientes)
    _log(f"URL ZonaProp: {search_url}")

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
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            },
        )
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        page = await context.new_page()
        await stealth.apply_stealth_async(page)

        # 3. Scrape listing pages
        current_url = search_url
        page_num = 1
        while current_url and page_num <= MAX_PAGINAS:
            _log(f"Página {page_num}/{MAX_PAGINAS}...")
            items = await _scrape_listing_page(page, current_url, barrio)

            if page_num == 1:
                await _handle_cloudflare(page)
                await _accept_cookies(page)
                if not items:
                    items = await _scrape_listing_page(page, current_url, barrio)

            raw_items.extend(items)

            if page_num < MAX_PAGINAS:
                next_url = await _get_next_page_url(page)
                if not next_url:
                    break
                current_url = next_url
                _random_delay()
            else:
                break
            page_num += 1

        _log(f"Total tarjetas scrapeadas: {len(raw_items)}")

        # 4. Parse + filter USD + m²
        seen_urls = set()
        candidates = []
        for item in raw_items:
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            precio = _parse_precio_usd(item.get("precio_raw", ""))
            sup = _parse_num(item.get("sup_cubierta_raw", ""), 10, 2000)

            if not precio or not sup:
                continue

            # m² filter ±30%
            if sup_cubierta and sup_cubierta > 0:
                if not (sup_cubierta * 0.70 <= sup <= sup_cubierta * 1.30):
                    continue

            comp = {
                "url": url,
                "direccion": item.get("direccion", ""),
                "barrio": item.get("barrio", barrio),
                "precio": precio,
                "sup_cubierta": sup,
                "sup_semicubierta": None,
                "ambientes": _parse_int(item.get("ambientes_raw", "")),
                "dormitorios": _parse_int(item.get("dormitorios_raw", "")),
                "piso": None,
                "disposicion": None,
                "orientacion": None,
                "cochera": False,
                "expensas": None,
                "amenities": [],
                "antiguedad": None,
                "lat": None,
                "lng": None,
                "distancia_metros": None,
                "precio_por_m2": round(precio / sup, 2),
            }
            candidates.append(comp)

        _log(f"Tras filtro USD+m²: {len(candidates)}")

        # PASO D: Deduplicación robusta (URL ya deduplicada; ahora por precio+sup+dir[:15])
        seen_dedup: set = set()
        deduped = []
        for comp in candidates:
            dir_key = (comp.get("direccion") or "")[:15].lower().strip()
            dedup_key = (int(comp["precio"]), int(comp["sup_cubierta"]), dir_key)
            if dedup_key not in seen_dedup:
                seen_dedup.add(dedup_key)
                deduped.append(comp)
        n_dedup = len(candidates) - len(deduped)
        if n_dedup:
            _log(f"Deduplicados por contenido: {n_dedup}")
        candidates = deduped

        # PASO B: Geocodificar comparables (0.1s delay; descartar si falla)
        _log(f"Geocodificando {len(candidates)} comparables...")
        for comp in candidates:
            if comp.get("lat"):
                continue
            dir_part = comp["direccion"] if comp.get("direccion") else comp.get("barrio", "")
            addr = (
                f"{dir_part}, Buenos Aires, Argentina"
                if dir_part else "Buenos Aires, Argentina"
            )
            coords = _geocode(addr, maps_key)
            if coords:
                comp["lat"], comp["lng"] = coords
            time.sleep(0.1)

        n_sin_geo = sum(1 for c in candidates if not c.get("lat"))
        candidates_geo = [c for c in candidates if c.get("lat")]

        # PASO C: Filtro por radio con Haversine (800 → 1.200 → 1.800m)
        radio = 800
        in_r = candidates_geo
        for radio in (800, 1200, 1800):
            in_r = [
                c for c in candidates_geo
                if _haversine(olat, olng, c["lat"], c["lng"]) <= radio
            ]
            if len(in_r) >= 10 or radio == 1800:
                break

        n_by_dist = len(candidates_geo) - len(in_r)
        _log(
            f"Radio usado: {radio}m | Descartados por distancia: {n_by_dist} | "
            f"Descartados sin geocoding: {n_sin_geo}"
        )
        candidates = in_r

        # 6. IQR filter
        n_total_antes_iqr = len(candidates)
        if len(candidates) >= 4:
            vals = sorted(c["precio_por_m2"] for c in candidates if c.get("precio_por_m2"))
            n = len(vals)
            p25 = vals[n // 4]
            p75 = vals[(3 * n) // 4]
            iqr = p75 - p25
            lo, hi = p25 - 1.5 * iqr, p75 + 1.5 * iqr
            candidates = [c for c in candidates if lo <= (c.get("precio_por_m2") or 0) <= hi]
            _log(f"Tras filtro IQR: {len(candidates)}")

        # 7. Score all candidates
        for comp in candidates:
            comp["_score"] = _calc_score(comp, datos_prop)

        # 8. Top 3 by score
        sorted_by_score = sorted(candidates, key=lambda c: c["_score"], reverse=True)
        top3 = sorted_by_score[:3]
        top3_urls = {c["url"] for c in top3}

        # 9. Scrape detail pages for Top 3
        if top3:
            _log("Scrapeando detalles para Top 3...")
            for comp in top3:
                detail = await _scrape_detail(page, comp["url"])

                if detail.get("precio_raw"):
                    p = _parse_precio_usd(detail["precio_raw"])
                    if p:
                        comp["precio"] = p
                if detail.get("sup_cubierta_raw"):
                    s = _parse_num(detail["sup_cubierta_raw"], 10, 2000)
                    if s:
                        comp["sup_cubierta"] = s
                        comp["precio_por_m2"] = round(comp["precio"] / s, 2)
                if detail.get("sup_semicubierta_raw"):
                    comp["sup_semicubierta"] = _parse_num(detail["sup_semicubierta_raw"], 0, 500)
                if detail.get("ambientes_raw"):
                    a = _parse_int(detail["ambientes_raw"])
                    if a:
                        comp["ambientes"] = a
                if detail.get("dormitorios_raw"):
                    d = _parse_int(detail["dormitorios_raw"])
                    if d:
                        comp["dormitorios"] = d
                if detail.get("piso") is not None:
                    comp["piso"] = detail["piso"]
                if detail.get("disposicion"):
                    comp["disposicion"] = detail["disposicion"]
                if detail.get("orientacion"):
                    comp["orientacion"] = detail["orientacion"]
                if detail.get("cochera"):
                    comp["cochera"] = True
                if detail.get("expensas_raw"):
                    exp = _parse_num(detail["expensas_raw"], 0, 2_000_000)
                    comp["expensas"] = exp
                if detail.get("antiguedad_raw"):
                    comp["antiguedad"] = _parse_int(detail["antiguedad_raw"])
                if detail.get("amenities"):
                    comp["amenities"] = detail["amenities"]
                if detail.get("lat"):
                    comp["lat"] = detail["lat"]
                    comp["lng"] = detail.get("lng")

                # Recalculate score with enriched data
                comp["_score"] = _calc_score(comp, datos_prop)
                _random_delay()

        await browser.close()

    # 10. Build final list: Top 3 first + hasta 12 más cercanos por distancia ASC
    stats = _calc_stats(candidates, sup_cubierta, radio, n_total_antes_iqr)

    # Calcular distancia_metros para todos los candidatos
    for comp in candidates:
        if comp.get("lat") and comp.get("lng"):
            comp["distancia_metros"] = int(_haversine(olat, olng, comp["lat"], comp["lng"]))
        else:
            comp["distancia_metros"] = None

    non_top3 = [c for c in candidates if c["url"] not in top3_urls]
    by_dist = sorted(
        non_top3,
        key=lambda c: (c.get("distancia_metros") is None, c.get("distancia_metros") or 0),
    )

    final = list(top3) + by_dist[:12]

    # Remove internal _score before output
    for c in final:
        c.pop("_score", None)

    top3_indices = list(range(min(len(top3), 3)))

    _log(f"Resultado final: {len(final)} comparables, Top3 indices: {top3_indices}")

    return {
        "comparables": final,
        "top3_indices": top3_indices,
        "stats": stats,
    }


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ACM Scraper")
    parser.add_argument("--direccion", required=True)
    parser.add_argument("--barrio", required=True)
    parser.add_argument("--tipo", default="departamento")
    parser.add_argument("--ambientes", type=int, default=0)
    parser.add_argument("--sup", type=float, default=0, help="M² cubiertos")
    parser.add_argument("--antiguedad", type=int, default=None)
    parser.add_argument("--piso", type=int, default=None)
    parser.add_argument("--disposicion", default=None)
    parser.add_argument("--cochera", default="false")
    parser.add_argument("--sup-semi", type=float, default=0, dest="sup_semi")
    parser.add_argument("--apto-credito", default="false", dest="apto_credito")
    args = parser.parse_args()

    async def main():
        result = await scrape_comparables(
            direccion=args.direccion,
            barrio=args.barrio,
            tipo=args.tipo,
            ambientes=args.ambientes,
            sup_cubierta=args.sup if args.sup > 0 else None,
            antiguedad=args.antiguedad,
            piso=args.piso,
            disposicion=args.disposicion,
            cochera=_str2bool(args.cochera),
            sup_semicubierta=args.sup_semi if args.sup_semi > 0 else None,
            apto_credito=_str2bool(args.apto_credito),
        )
        print(json.dumps(result, ensure_ascii=False))

    asyncio.run(main())
