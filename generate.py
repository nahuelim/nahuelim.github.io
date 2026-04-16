#!/usr/bin/env python3
"""
generar_ficha.py — Generador de fichas inmobiliarias para nahuelim.github.io
Uso: python generar_ficha.py datos.txt [portal.html]
"""

import sys
import os
import re
import hashlib
import time
from pathlib import Path

# ─── ÍCONOS CDN ────────────────────────────────────────────────────────────────
CDN = "https://img10.naventcdn.com/ficha/RPFICv5.401.1-RC1"
ICONOS = {
    "ambientes":   f"{CDN}/ambientes.9e33dd.svg",
    "dormitorios": f"{CDN}/dormitorio.349d35.svg",
    "banos":       f"{CDN}/banos.827612.svg",
    "toilette":    f"{CDN}/toilete.f725dc.svg",
    "sup_total":   f"{CDN}/stotal.38e4f4.svg",
    "sup_cubierta":f"{CDN}/scubierta.695fb2.svg",
    "antiguedad":  f"{CDN}/antiguedad.eb15bc.svg",
    "disposicion": f"{CDN}/disposicion.2ba2d5.svg",
    "orientacion": f"{CDN}/orientacion.3a91e2.svg",
}
LABELS = {
    "ambientes":    "Ambientes",
    "dormitorios":  "Dormitorios",
    "banos":        "Baños",
    "toilette":     "Toilette",
    "sup_total":    "Sup. Total",
    "sup_cubierta": "Sup. Cubierta",
    "antiguedad":   "Antigüedad",
    "disposicion":  "Disposición",
    "orientacion":  "Orientación",
}

# ─── TEMPLATE HTML ─────────────────────────────────────────────────────────────
TEMPLATE = '''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="icon" type="image/svg+xml" href="https://nahuelim.github.io/assets/favicon.svg">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --primary:#003153;--primary-dark:#00243d;
  --orange:#E8630A;--orange-lt:#fef3eb;--orange-dk:#c4520a;
  --bg:#f2f3f5;--white:#fff;--text:#1c1c1c;--muted:#6b7280;--border:#e2e4e8;
  --r:10px;--bar-h:62px;
}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}}
.bar{{background:var(--primary);height:var(--bar-h);padding:0 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:200;box-shadow:0 2px 16px rgba(0,0,0,.35)}}
.bar-l{{display:flex;align-items:center;gap:14px;min-width:0;flex:1;overflow:hidden}}
.logo-nl{{height:30px;flex-shrink:0;object-fit:contain}}
.logo-c21{{height:14px;flex-shrink:0;object-fit:contain;opacity:.7}}
.bar-sep{{width:1px;height:22px;background:rgba(255,255,255,.2);flex-shrink:0}}
.bar-r{{flex-shrink:0;margin-left:12px}}
.bwa{{display:inline-flex;align-items:center;gap:7px;background:#25D366;color:#fff;padding:9px 14px;border-radius:7px;text-decoration:none;font-weight:700;font-size:13px;transition:background .15s;white-space:nowrap}}
.bwa:hover{{background:#1dba57}}
@media(max-width:480px){{.bar{{padding:0 14px}}.logo-nl{{height:24px}}.logo-c21{{height:11px}}.bar-sep{{height:18px}}.bwa{{padding:8px 12px;font-size:12px}}}}
@media(max-width:360px){{.bwa span{{display:none}}.bwa{{padding:9px 12px}}}}
.mosaic{{display:grid;grid-template-columns:60% 1fr;grid-template-rows:1fr;gap:3px;height:480px;background:var(--bg)}}
@media(max-width:700px){{.mosaic{{grid-template-columns:1fr;height:260px}}.mg-right{{display:none}}}}
.mg-main{{background-size:cover;background-position:center;cursor:pointer;position:relative;transition:filter .2s}}
.mg-main:hover{{filter:brightness(.9)}}
.mg-right{{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:3px}}
.mg-cell{{background-size:cover;background-position:center;cursor:pointer;transition:filter .2s}}
.mg-cell:hover{{filter:brightness(.88)}}
.mg-btn{{position:absolute;bottom:14px;right:14px;display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.92);color:var(--text);padding:8px 14px;border-radius:7px;font-size:12px;font-weight:600;border:1px solid var(--border);cursor:pointer;transition:background .15s;backdrop-filter:blur(4px)}}
.mg-btn:hover{{background:#fff}}
.lb{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.96);z-index:1000;flex-direction:column;align-items:center;justify-content:center}}
.lb.open{{display:flex}}
.lb-img{{max-width:90vw;max-height:80vh;object-fit:contain;border-radius:3px;user-select:none}}
.lb-close{{position:absolute;top:18px;right:22px;background:none;border:none;color:#fff;font-size:30px;cursor:pointer;opacity:.65;transition:opacity .15s;line-height:1}}
.lb-close:hover{{opacity:1}}
.lb-arrow{{position:absolute;top:50%;transform:translateY(-50%);background:rgba(255,255,255,.1);border:none;color:#fff;width:48px;height:48px;border-radius:50%;font-size:26px;cursor:pointer;transition:background .15s;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)}}
.lb-arrow:hover{{background:rgba(255,255,255,.22)}}
.lb-prev{{left:18px}}.lb-next{{right:18px}}
.lb-bottom{{position:absolute;bottom:0;left:0;right:0;padding:14px 20px;display:flex;flex-direction:column;align-items:center;gap:10px;background:linear-gradient(transparent,rgba(0,0,0,.7))}}
.lb-thumbs{{display:flex;gap:5px;overflow-x:auto;scrollbar-width:none;max-width:90vw}}
.lb-thumbs::-webkit-scrollbar{{display:none}}
.lb-thumbs img{{width:58px;height:42px;object-fit:cover;border-radius:3px;cursor:pointer;opacity:.42;transition:opacity .15s;flex-shrink:0;border:2px solid transparent}}
.lb-thumbs img.on{{opacity:1;border-color:var(--orange)}}
.lb-cnt{{color:rgba(255,255,255,.5);font-size:12px;letter-spacing:.5px}}
.wrap{{max-width:1080px;margin:0 auto;padding:24px 18px 40px;display:grid;grid-template-columns:1fr 320px;gap:24px;align-items:start}}
@media(max-width:800px){{.wrap{{grid-template-columns:1fr}}}}
.col{{display:flex;flex-direction:column;gap:20px}}
.card{{background:var(--white);border-radius:var(--r);box-shadow:0 1px 4px rgba(0,0,0,.07)}}
.card-body{{padding:24px}}
.sec-title{{font-size:12px;font-weight:700;color:var(--primary);text-transform:uppercase;letter-spacing:.8px;margin-bottom:18px;display:flex;align-items:center;gap:10px}}
.sec-title::after{{content:'';flex:1;height:1px;background:var(--border)}}
.optag{{display:inline-block;background:var(--primary);color:#fff;font-size:10px;font-weight:700;padding:3px 10px;border-radius:4px;letter-spacing:.8px;text-transform:uppercase;margin-bottom:10px}}
.prop-address{{font-size:20px;font-weight:800;color:var(--primary);line-height:1.2;margin-bottom:2px}}
.prop-barrio{{font-size:12px;color:var(--muted);margin-bottom:14px;text-transform:uppercase;letter-spacing:.5px}}
.price{{font-size:38px;font-weight:800;color:var(--primary);letter-spacing:-.5px;line-height:1}}
.exps{{color:var(--muted);font-size:13px;margin-top:7px}}
.exps b{{color:var(--text)}}
.badges{{display:flex;flex-wrap:wrap;gap:7px;margin-top:16px}}
.badge{{background:#f0f4f8;color:#1a2e42;font-size:12px;font-weight:600;padding:5px 12px;border-radius:20px;border:1px solid #dde3ea}}
.badge.grn{{background:#ecfdf5;color:#065f46;border-color:#a7f3d0}}
.badge.org{{background:var(--orange-lt);color:var(--orange-dk);border-color:#f9c89e}}
.fgrid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}
@media(max-width:560px){{.fgrid{{grid-template-columns:repeat(2,1fr)}}}}
.fi{{background:#f8f9fb;border-radius:8px;padding:16px 8px;text-align:center;border:1px solid var(--border);display:flex;flex-direction:column;align-items:center;gap:7px}}
.fi-icon{{width:26px;height:26px;object-fit:contain;filter:invert(17%) sepia(62%) saturate(800%) hue-rotate(185deg) brightness(85%)}}
.fi-val{{font-size:17px;font-weight:800;color:var(--primary)}}
.fi-lbl{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;line-height:1.3}}
.desc{{font-size:14px;line-height:1.8;color:#374151}}
.desc p{{margin-bottom:10px}}
.desc ul{{margin:6px 0 10px 18px;display:flex;flex-direction:column;gap:6px}}
.desc-note{{font-size:11px;color:#9ca3af;margin-top:16px;padding-top:14px;border-top:1px solid var(--border);line-height:1.65}}
.scard{{background:var(--primary);border-radius:var(--r);padding:26px;box-shadow:0 4px 20px rgba(0,49,83,.3)}}
.agent-photo{{width:74px;height:74px;border-radius:50%;border:2.5px solid var(--orange);display:block;margin:0 auto 14px;object-fit:cover}}
.scard h3{{color:#fff;font-size:17px;font-weight:700;text-align:center}}
.scard-role{{color:rgba(255,255,255,.45);font-size:12px;text-align:center;margin-top:3px}}
.scard-logo{{display:block;margin:16px auto 0;height:18px;object-fit:contain;opacity:.7}}
.sdivider{{border:none;border-top:1px solid rgba(255,255,255,.1);margin:18px 0}}
.bwa-big{{display:flex;align-items:center;justify-content:center;gap:10px;background:#25D366;color:#fff;padding:14px;border-radius:9px;text-decoration:none;font-weight:700;font-size:15px;width:100%;transition:background .15s}}
.bwa-big:hover{{background:#1dba57}}
.snote{{color:rgba(255,255,255,.3);font-size:11px;text-align:center;margin-top:10px}}
.mapcard{{border-radius:var(--r);overflow:hidden;box-shadow:0 4px 20px rgba(0,49,83,.3)}}
.mapcard iframe{{width:100%;height:360px;border:none;display:block}}
.maplbl{{background:#fff;padding:12px 16px;display:flex;align-items:center;gap:8px;border-top:1px solid #e8eaed}}
.maplbl svg{{flex-shrink:0;color:var(--orange)}}
.maplbl-text b{{display:block;color:#1c1c1c;font-size:13px;font-weight:600;line-height:1.3}}
.maplbl-text span{{color:#6b7280;font-size:11px}}
footer{{background:var(--primary-dark);color:rgba(255,255,255,.38);text-align:center;padding:24px;font-size:12px;line-height:1.9}}
footer strong{{color:rgba(255,255,255,.7)}}
footer a{{color:var(--orange);text-decoration:none}}
</style>
</head>
<body>

<header class="bar">
  <div class="bar-l">
    <img src="https://nahuelim.github.io/assets/nl-logo.svg" alt="Nahuel Lim" class="logo-nl">
    <div class="bar-sep"></div>
    <img src="https://nahuelim.github.io/assets/c21-logo.svg" alt="Century 21" class="logo-c21">
  </div>
  <div class="bar-r">
    <a class="bwa" href="{wa_url}" target="_blank"><svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" style="flex-shrink:0"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg><span>&nbsp;Consultar</span></a>
  </div>
</header>

<div class="mosaic">
  <div class="mg-main" style="background-image:url('{foto0}')" onclick="openLB(0)">
    <button class="mg-btn" onclick="event.stopPropagation();openLB(0)">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="13" height="13"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
      Ver las {n_fotos} fotos
    </button>
  </div>
  <div class="mg-right">
{mg_cells}
  </div>
</div>

<div class="lb" id="lb" onclick="closeLB()">
  <button class="lb-close" onclick="closeLB()">&#x2715;</button>
  <button class="lb-arrow lb-prev" onclick="event.stopPropagation();lbGo(-1)">&#8249;</button>
  <img class="lb-img" id="lb-img" src="" alt="" onclick="event.stopPropagation()">
  <button class="lb-arrow lb-next" onclick="event.stopPropagation();lbGo(1)">&#8250;</button>
  <div class="lb-bottom" onclick="event.stopPropagation()">
    <div class="lb-thumbs" id="lb-thumbs">
{thumbs}
    </div>
    <div class="lb-cnt" id="lb-cnt"></div>
  </div>
</div>

<div class="wrap">
  <div class="col">
    <div class="card"><div class="card-body">
      <div class="optag">{operacion}</div>
      <div class="prop-address">{direccion}</div>
      <div class="prop-barrio">{barrio} · CABA</div>
      <div class="price">{precio}</div>
{expensas_html}
      <div class="badges">
{badges_html}
      </div>
    </div></div>

    <div class="card"><div class="card-body">
      <div class="sec-title">Características</div>
      <div class="fgrid">
{caract_html}
      </div>
    </div></div>

    <div class="card"><div class="card-body">
      <div class="sec-title">Descripción</div>
      <div class="desc">
{desc_html}
        <p class="desc-note">Las medidas y superficies informadas son aproximadas. Las exactas surgen del título de propiedad o plano de mensura. Reservas únicamente con el matriculado en la inmobiliaria.</p>
      </div>
    </div></div>
  </div>

  <aside class="col">
    <div class="scard">
      <img src="https://nahuelim.github.io/assets/profile.jpg" alt="Nahuel Lim" class="agent-photo">
      <h3>Nahuel Lim</h3>
      <div class="scard-role">Asesor Inmobiliario</div>
      <img src="https://nahuelim.github.io/assets/c21-logo.svg" alt="Century 21" class="scard-logo">
      <hr class="sdivider">
      <a class="bwa-big" href="{wa_url}" target="_blank"><svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" style="flex-shrink:0"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>&nbsp;Consultar por WhatsApp</a>
      <div class="snote">Consultame sin compromiso</div>
    </div>
    <div class="mapcard">
      <iframe src="{mapa_url}" allowfullscreen loading="lazy" title="Ubicación"></iframe>
      <div class="maplbl">
        <svg viewBox="0 0 24 24" fill="currentColor" width="15" height="15"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
        <div class="maplbl-text"><b>{direccion}</b><span>{barrio}, CABA</span></div>
      </div>
    </div>
  </aside>
</div>

<footer>
  Ficha preparada por <strong>Nahuel Lim</strong> · Century 21 Evolución Inmobiliaria S.A.<br>
  CUCICBA 9135 – MN377 · <a href="https://wa.me/5491178268244">+54 9 11 7826-8244</a>
</footer>

<script>
const photos=[
{photos_json}
];
const N=photos.length;
let lbCur=0;
function openLB(i){{lbCur=i;document.getElementById('lb').classList.add('open');document.body.style.overflow='hidden';lbUpd();}}
function closeLB(){{document.getElementById('lb').classList.remove('open');document.body.style.overflow='';}}
function lbGo(d){{lbCur=(lbCur+d+N)%N;lbUpd();}}
function lbGoTo(i){{lbCur=i;lbUpd();}}
function lbUpd(){{
  document.getElementById('lb-img').src=photos[lbCur];
  document.getElementById('lb-cnt').textContent=(lbCur+1)+' / '+N;
  document.querySelectorAll('#lb-thumbs img').forEach((img,i)=>{{img.className=i===lbCur?'on':'';if(i===lbCur)img.scrollIntoView({{behavior:'smooth',block:'nearest',inline:'center'}});}});
}}
document.addEventListener('keydown',e=>{{if(!document.getElementById('lb').classList.contains('open'))return;if(e.key==='ArrowLeft')lbGo(-1);if(e.key==='ArrowRight')lbGo(1);if(e.key==='Escape')closeLB();}});
</script>
</body>
</html>'''


# ─── PARSEAR DATOS.TXT ─────────────────────────────────────────────────────────
def parsear_datos(ruta):
    texto = Path(ruta).read_text(encoding="utf-8")
    datos = {}

    # Campos multilínea entre triple comillas
    for key in ["descripcion", "fotos"]:
        pat = rf'{key}\s*=\s*"""\n(.*?)"""'
        m = re.search(pat, texto, re.DOTALL)
        datos[key] = m.group(1).strip() if m else ""

    # Campos simples clave = valor
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        valor = valor.split("#")[0].strip()  # ignorar comentarios inline
        if clave not in datos:
            datos[clave] = valor

    return datos


# ─── EXTRAER FOTOS ZONAPROP ────────────────────────────────────────────────────
def extraer_fotos_zonaprop(ruta_html):
    texto = Path(ruta_html).read_text(encoding="utf-8", errors="ignore")
    urls = re.findall(r'https://[^\s"\']*zonapropcdn[^\s"\']*1200x1200[^\s"\']*', texto)
    # Limpiar query strings y deduplicar manteniendo orden
    limpias = []
    seen = set()
    for u in urls:
        u = u.split("?")[0]
        if "/resize/" not in u and u not in seen:
            seen.add(u)
            limpias.append(u)

    # Poner la isFirstImage primero si existe
    first = next((u for u in limpias if "isFirstImage" in u), None)
    if first:
        limpias = [first] + [u for u in limpias if u != first]

    return limpias


# ─── EXTRAER FOTOS ARGENPROP ───────────────────────────────────────────────────
def extraer_fotos_argenprop(ruta_html):
    texto = Path(ruta_html).read_text(encoding="utf-8", errors="ignore")
    # Buscar ID de la propiedad (número largo en las URLs de static-content)
    ids = re.findall(r'static-content/(\d+)/', texto)
    if not ids:
        return []
    # El ID más frecuente es el de la propiedad
    prop_id = max(set(ids), key=ids.count)
    urls = re.findall(rf'https://www\.argenprop\.com/static-content/{prop_id}/[^\s"\'()]+\.jpg', texto)
    # Preferir URLs sin sufijos (_small, _medium) = mayor resolución
    limpias = []
    seen = set()
    for u in urls:
        base = u
        if base not in seen:
            seen.add(base)
            limpias.append(base)
    # Ordenar: sin sufijo primero (mayor res)
    sin_sufijo = [u for u in limpias if "_u_" not in u]
    con_sufijo = [u for u in limpias if "_u_" in u]
    # Si no hay sin sufijo, usar con sufijo
    return sin_sufijo if sin_sufijo else con_sufijo


# ─── EXTRAER FOTOS ML ──────────────────────────────────────────────────────────
def extraer_fotos_ml(ruta_html):
    texto = Path(ruta_html).read_text(encoding="utf-8", errors="ignore")
    urls = re.findall(r'https://http2\.mlstatic\.com/D_NQ_NP[^\s"\']+\.webp', texto)
    limpias = []
    seen = set()
    for u in urls:
        u = u.split("?")[0]
        if u not in seen:
            seen.add(u)
            limpias.append(u)
    return limpias


# ─── CONSTRUIR NOMBRE DE ARCHIVO ───────────────────────────────────────────────
def slugify(texto):
    texto = texto.lower().strip()
    texto = re.sub(r'[áàä]', 'a', texto)
    texto = re.sub(r'[éèë]', 'e', texto)
    texto = re.sub(r'[íìï]', 'i', texto)
    texto = re.sub(r'[óòö]', 'o', texto)
    texto = re.sub(r'[úùü]', 'u', texto)
    texto = re.sub(r'[ñ]', 'n', texto)
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    return texto.strip('-')


def nombre_unico(directorio, nombre_base):
    path = directorio / f"{nombre_base}.html"
    if not path.exists():
        return path
    h = hashlib.md5(str(time.time()).encode()).hexdigest()[:4]
    nuevo = directorio / f"{nombre_base}-{h}.html"
    print(f"⚠️  Nombre duplicado — generando como: {nuevo.name}")
    return nuevo


# ─── GENERAR WA URL ────────────────────────────────────────────────────────────
def wa_url(direccion):
    from urllib.parse import quote
    msg = f"Hola, vi la ficha de {direccion} y quiero más información."
    return f"https://wa.me/5491178268244?text={quote(msg)}"


# ─── GENERAR MAPA URL ──────────────────────────────────────────────────────────
def mapa_url(direccion, barrio):
    from urllib.parse import quote
    q = quote(f"{direccion}, {barrio}, Buenos Aires")
    return f"https://www.google.com/maps?q={q}&output=embed"


# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Uso: python generar_ficha.py datos.txt [portal.html]")
        sys.exit(1)

    datos = parsear_datos(sys.argv[1])
    portal = datos.get("portal", "zonaprop").lower()

    # ── Fotos ──
    fotos = []
    ruta_html = sys.argv[2] if len(sys.argv) > 2 else None

    if datos.get("fotos"):
        # Fotos manuales desde datos.txt
        fotos = [l.strip() for l in datos["fotos"].splitlines() if l.strip().startswith("http")]
    elif ruta_html:
        if portal == "zonaprop":
            fotos = extraer_fotos_zonaprop(ruta_html)
        elif portal == "argenprop":
            fotos = extraer_fotos_argenprop(ruta_html)
        elif portal in ("ml", "mercadolibre"):
            fotos = extraer_fotos_ml(ruta_html)

    if not fotos:
        print("⚠️  No se encontraron fotos. Verificá el HTML o completá el campo fotos= en datos.txt")
        sys.exit(1)

    print(f"✓ {len(fotos)} fotos encontradas")

    # ── Mosaico ──
    foto0 = fotos[0]
    mg_cells = ""
    for i in range(1, 5):
        url = fotos[i] if i < len(fotos) else fotos[0]
        mg_cells += f'    <div class="mg-cell" style="background-image:url(\'{url}\')" onclick="openLB({i})"></div>\n'

    # ── Slides HTML (para lightbox) ──
    slides_html = ""
    for i, url in enumerate(fotos):
        cls = "slide active" if i == 0 else "slide"
        slides_html += f'  <div class="{cls}" style="background-image:url(\'{url}\')"></div>\n'

    # ── Thumbnails ──
    thumbs_html = ""
    for i, url in enumerate(fotos):
        thumbs_html += f'      <img src="{url}" onclick="lbGoTo({i})">\n'

    # ── Photos JSON ──
    photos_json = ",\n".join(f'  "{u}"' for u in fotos)

    # ── Expensas ──
    expensas = datos.get("expensas", "").strip()
    expensas_html = f'      <div class="exps">Expensas: <b>{expensas}</b></div>' if expensas else ""

    # ── Badges ──
    badge_clases = {
        "a estrenar": "org", "apto crédito": "grn", "apto credito": "grn",
        "apto profesional": "grn", "cochera": "", "parrilla": "",
    }
    badges_html = ""
    tipo = datos.get("tipo", "").strip()
    ambientes = datos.get("ambientes", "").strip()
    if tipo:
        badges_html += f'        <span class="badge">{tipo}</span>\n'
    if ambientes:
        badges_html += f'        <span class="badge">{ambientes} ambientes</span>\n'
    for i in range(1, 5):
        b = datos.get(f"badge_{i}", "").strip()
        if b:
            cls = badge_clases.get(b.lower(), "")
            cls_str = f' class="badge {cls}"' if cls else ' class="badge"'
            badges_html += f'        <span{cls_str}>{b}</span>\n'

    # ── Características ──
    CARACT_KEYS = ["ambientes", "dormitorios", "banos", "toilette",
                   "sup_total", "sup_cubierta", "antiguedad", "disposicion", "orientacion"]
    caract_html = ""
    for key in CARACT_KEYS:
        val = datos.get(key, "").strip()
        if not val:
            continue
        if key in ("sup_total", "sup_cubierta"):
            val = f"{val} m²"
        caract_html += f'''        <div class="fi">
          <img class="fi-icon" src="{ICONOS[key]}" alt="{LABELS[key]}">
          <div class="fi-val">{val}</div>
          <div class="fi-lbl">{LABELS[key]}</div>
        </div>\n'''

    # ── Descripción ──
    desc_raw = datos.get("descripcion", "").strip()
    if desc_raw:
        parrafos = [p.strip() for p in desc_raw.split("\n\n") if p.strip()]
        desc_html = "\n".join(f"        <p>{p.replace(chr(10), '<br>')}</p>" for p in parrafos)
    else:
        desc_html = "        <p>Consultá más información sobre esta propiedad.</p>"

    # ── Datos base ──
    direccion = datos.get("direccion", "").strip()
    barrio = datos.get("barrio", "").strip()
    operacion = datos.get("operacion", "Venta").strip()
    precio = datos.get("precio", "").strip()
    ambientes_val = datos.get("ambientes", "").strip()

    # ── Nombre de archivo ──
    slug_barrio = slugify(barrio)
    slug_dir = slugify(direccion)
    slug_amb = f"-{ambientes_val}amb" if ambientes_val else ""
    nombre = f"{slug_barrio}-{slug_dir}{slug_amb}.html"

    # ── Title ──
    title = f"{operacion} {ambientes_val} Ambientes – {direccion}, {barrio}"

    # ── Renderizar ──
    html = TEMPLATE.format(
        title=title,
        wa_url=wa_url(direccion),
        mapa_url=mapa_url(direccion, barrio),
        operacion=operacion,
        precio=precio,
        expensas_html=expensas_html,
        badges_html=badges_html,
        caract_html=caract_html,
        desc_html=desc_html,
        foto0=foto0,
        mg_cells=mg_cells,
        n_fotos=len(fotos),
        thumbs=thumbs_html,
        photos_json=photos_json,
        direccion=direccion,
        barrio=barrio,
    )

    # ── Guardar ──
    out_dir = Path("fichas")
    out_dir.mkdir(exist_ok=True)
    out_path = nombre_unico(out_dir, Path(nombre).stem)
    out_path.write_text(html, encoding="utf-8")
    print(f"✓ Ficha generada: {out_path}")


if __name__ == "__main__":
    main()
