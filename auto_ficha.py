#!/usr/bin/env python3
"""
auto_ficha.py — Generador automático de fichas para nahuelim.github.io
Uso: python auto_ficha.py
Abre: http://localhost:5050
"""

import json
import os
import re
import sys
import subprocess
import hashlib
import time
import shutil
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse
import html as _html_esc
from datetime import date as _date, datetime as _datetime
from collections import Counter as _Counter

from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup

# ─── CONFIG ────────────────────────────────────────────────────────────────────
REPO_PATH = Path(__file__).resolve().parent
FICHAS_DIR = REPO_PATH / "fichas"
FOTOS_DIR  = REPO_PATH / "assets" / "fotos"
GITHUB_BASE = "https://nahuelim.github.io"
PORT = 5050

app = Flask(__name__)

# ─── TEMPLATE HTML ─────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Generador de Fichas · Nahuel Lim</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
  :root {
    --primary: #003153;
    --orange:  #E8630A;
    --bg:      #f0f2f5;
    --white:   #fff;
    --muted:   #6b7280;
    --border:  #dde1e7;
    --green:   #16a34a;
    --red:     #dc2626;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'DM Sans', sans-serif; background: var(--bg); color: #111; min-height: 100vh; }

  /* NAV */
  nav {
    background: var(--primary);
    padding: 0 28px;
    height: 54px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  nav .brand {
    color: #fff;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: .04em;
  }
  nav .badge {
    background: var(--orange);
    color: #fff;
    font-size: 10px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 20px;
    letter-spacing: .06em;
    text-transform: uppercase;
  }

  /* MAIN */
  main {
    max-width: 700px;
    margin: 48px auto;
    padding: 0 20px;
  }

  h1 {
    font-size: 22px;
    font-weight: 600;
    color: var(--primary);
    margin-bottom: 6px;
  }
  .subtitle {
    color: var(--muted);
    font-size: 14px;
    margin-bottom: 32px;
  }

  /* URL INPUT CARD */
  .card {
    background: var(--white);
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 1px 6px rgba(0,0,0,.07);
    margin-bottom: 20px;
  }

  label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--primary);
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-bottom: 8px;
  }

  .url-row {
    display: flex;
    gap: 10px;
  }
  input[type=text], input[type=number], select, textarea {
    width: 100%;
    border: 1.5px solid var(--border);
    border-radius: 8px;
    padding: 11px 14px;
    font-size: 14px;
    font-family: 'DM Sans', sans-serif;
    outline: none;
    transition: border-color .15s;
    background: #fff;
  }
  input[type=text]:focus, input[type=number]:focus, select:focus, textarea:focus {
    border-color: var(--primary);
  }
  textarea { resize: vertical; min-height: 120px; font-family: 'DM Mono', monospace; font-size: 13px; }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 11px 20px;
    border-radius: 8px;
    border: none;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity .15s, transform .1s;
    white-space: nowrap;
  }
  .btn:hover { opacity: .88; transform: translateY(-1px); }
  .btn:active { transform: translateY(0); }
  .btn-primary   { background: var(--primary); color: #fff; }
  .btn-orange    { background: var(--orange); color: #fff; }
  .btn-outline   { background: transparent; border: 1.5px solid var(--border); color: #374151; }
  .btn-green     { background: var(--green); color: #fff; }
  .btn-sm        { padding: 7px 14px; font-size: 13px; }

  /* PORTAL PILLS */
  .portal-pills {
    display: flex;
    gap: 8px;
    margin-bottom: 18px;
    flex-wrap: wrap;
  }
  .pill {
    padding: 6px 16px;
    border-radius: 20px;
    border: 1.5px solid var(--border);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all .15s;
    background: #fff;
    color: var(--muted);
  }
  .pill.active {
    background: var(--primary);
    border-color: var(--primary);
    color: #fff;
  }

  /* FORM GRID */
  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .form-grid .full { grid-column: 1 / -1; }

  /* STATUS */
  .status {
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    margin-top: 16px;
    display: none;
  }
  .status.info    { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
  .status.success { background: #f0fdf4; color: var(--green); border: 1px solid #bbf7d0; }
  .status.error   { background: #fef2f2; color: var(--red); border: 1px solid #fecaca; }

  /* RESULT LINK */
  .result-box {
    margin-top: 20px;
    padding: 18px 20px;
    background: var(--primary);
    border-radius: 10px;
    display: none;
  }
  .result-box .lbl { color: rgba(255,255,255,.55); font-size: 12px; margin-bottom: 6px; }
  .result-link {
    font-family: 'DM Mono', monospace;
    font-size: 14px;
    color: #fff;
    word-break: break-all;
  }
  .result-actions {
    display: flex;
    gap: 10px;
    margin-top: 14px;
    flex-wrap: wrap;
  }

  /* FOTOS PENDIENTES */
  .fotos-info {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 13px;
    color: #92400e;
    margin-top: 14px;
    display: none;
  }
  .fotos-info code {
    font-family: 'DM Mono', monospace;
    background: #fef3c7;
    padding: 1px 6px;
    border-radius: 4px;
  }

  /* LOADER */
  .loader {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2.5px solid rgba(255,255,255,.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin .6s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .sep { border: none; border-top: 1px solid var(--border); margin: 20px 0; }
  .field-hint { font-size: 11px; color: var(--muted); margin-top: 5px; }
  .section-title { font-size: 12px; font-weight: 600; color: var(--primary); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 14px; }

  /* BADGES INPUT */
  .badges-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .badges-row input { flex: 1; min-width: 140px; }

  /* MacBook Pro 14" */
  @media screen and (max-width: 1400px) {
    nav { padding: 0 18px; height: 48px; }
    main { margin: 28px auto; }
    h1 { font-size: 19px; }
    .card { padding: 18px; }
    .btn { padding: 9px 16px; font-size: 13px; }
  }
</style>
</head>
<body>

<nav>
  <span class="brand">NL · Generador de Fichas</span>
  <div style="display:flex;align-items:center;gap:14px">
    <a href="/" style="color:rgba(255,255,255,.75);font-size:13px;font-weight:500;text-decoration:none">Fichas</a>
    <span class="badge">Internal Tool</span>
  </div>
</nav>

<main>
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
    <h1 style="margin-bottom:0">Generador de Fichas</h1>
    <button class="btn btn-outline btn-sm" onclick="resetTodo()">↺ Nueva ficha</button>
  </div>
  <p class="subtitle">Pegá una URL o completá los datos manualmente para publicar una ficha en nahuelim.com.ar</p>

  <!-- PASO 1: URL o modo manual -->
  <div class="card">
    <div class="section-title">Portal</div>
    <div class="portal-pills">
      <div class="pill active" onclick="setPortal('zonaprop')">ZonaProp</div>
      <div class="pill" onclick="setPortal('ml')">MercadoLibre</div>
      <div class="pill" onclick="setPortal('c21')">Century 21</div>
      <div class="pill" onclick="setPortal('manual')">Manual</div>
    </div>

    <div id="url-section">
      <label>URL del aviso</label>
      <div class="url-row">
        <input type="text" id="url-input" id="url-input" placeholder="https://www.zonaprop.com.ar/propiedades/... o /Users/tu/archivo.html" />
        <button class="btn btn-primary" onclick="extraerDatos()">
          <span id="btn-extraer-txt">Extraer</span>
          <span id="btn-extraer-loader" class="loader" style="display:none"></span>
        </button>
      </div>
      <p class="field-hint" id="url-hint">ZonaProp: extracción automática completa. ML: pegá la URL del aviso, extracción automática vía API. C21: guardá con Cmd+S y pegá el path.</p>
    </div>
  </div>

  <!-- PASO 2: Formulario de datos -->
  <div class="card" id="form-card" style="display:none">
    <div class="section-title">Datos de la propiedad</div>

    <div class="form-grid">
      <div>
        <label>Operación</label>
        <select id="f-operacion">
          <option>Venta</option>
          <option>Alquiler</option>
          <option>Alquiler temporal</option>
        </select>
      </div>
      <div>
        <label>Tipo</label>
        <select id="f-tipo">
          <option>Departamento</option>
          <option>PH</option>
          <option>Casa</option>
          <option>Local</option>
          <option>Oficina</option>
          <option>Terreno</option>
        </select>
      </div>
      <div>
        <label>Dirección</label>
        <input type="text" id="f-direccion" placeholder="Av. Corrientes 1234">
      </div>
      <div>
        <label>Barrio</label>
        <input type="text" id="f-barrio" placeholder="Palermo">
      </div>
      <div>
        <label>Precio</label>
        <input type="text" id="f-precio" placeholder="USD 150.000">
      </div>
      <div>
        <label>Expensas</label>
        <input type="text" id="f-expensas" placeholder="$ 80.000 (opcional)">
      </div>
      <div>
        <label>Ambientes</label>
        <input type="number" id="f-ambientes" min="1" max="20">
      </div>
      <div>
        <label>Dormitorios</label>
        <input type="number" id="f-dormitorios" min="0" max="20">
      </div>
      <div>
        <label>Baños</label>
        <input type="number" id="f-banos" min="0" max="20">
      </div>
      <div>
        <label>Toilette</label>
        <input type="number" id="f-toilette" min="0" max="10">
      </div>
      <div>
        <label>Sup. Total (m²)</label>
        <input type="number" id="f-sup-total" min="0">
      </div>
      <div>
        <label>Sup. Cubierta (m²)</label>
        <input type="number" id="f-sup-cubierta" min="0">
      </div>
      <div>
        <label>Antigüedad (años)</label>
        <input type="number" id="f-antiguedad" min="0">
      </div>
      <div>
        <label>Disposición</label>
        <select id="f-disposicion">
          <option value="">—</option>
          <option>Frente</option>
          <option>Contrafrente</option>
          <option>Lateral</option>
          <option>Interno</option>
        </select>
      </div>
      <div>
        <label>Orientación</label>
        <select id="f-orientacion">
          <option value="">—</option>
          <option>Norte</option>
          <option>Sur</option>
          <option>Este</option>
          <option>Oeste</option>
          <option>Noreste</option>
          <option>Noroeste</option>
          <option>Sureste</option>
          <option>Suroeste</option>
        </select>
      </div>

      <div class="full">
        <label>Badges / Amenities (hasta 6 — se detectan automáticamente)</label>
        <div class="badges-row">
          <input type="text" id="f-badge1" placeholder="Cochera">
          <input type="text" id="f-badge2" placeholder="Apto mascota">
          <input type="text" id="f-badge3" placeholder="Parrilla">
          <input type="text" id="f-badge4" placeholder="">
          <input type="text" id="f-badge5" placeholder="">
          <input type="text" id="f-badge6" placeholder="">
        </div>
      </div>

      <div class="full">
        <label>Video (opcional)</label>
        <input type="text" id="f-video" placeholder="https://youtube.com/...  (o Instagram, Drive, etc.)">
        <small style="display:block;margin-top:4px;color:#888;font-size:12px">Pegá el link normal de YouTube o Vimeo (se reproduce en un popup). Otras URLs abren en pestaña nueva.</small>
      </div>

      <div class="full">
        <label>Descripción</label>
        <textarea id="f-descripcion" placeholder="Descripción del inmueble..."></textarea>
      </div>
    </div>

    <!-- Fotos -->
    <hr class="sep">
    <div class="section-title">Fotos</div>

    <div id="fotos-zp-section" style="display:none">
      <label>URLs de fotos (una por línea — extraídas automáticamente)</label>
      <textarea id="f-fotos" style="min-height:100px; font-size:12px;" placeholder="https://..."></textarea>
      <p class="field-hint">Podés editar, agregar o quitar URLs.</p>
    </div>

    <div id="fotos-manual-section" style="display:none">
      <div class="fotos-info" style="display:block">
        <strong>Fotos manuales:</strong> Copiá las fotos a la carpeta
        <code id="fotos-carpeta-path">assets/fotos/slug/</code>
        antes de generar la ficha.<br><br>
        Las fotos deben llamarse <code>foto-1.webp</code>, <code>foto-2.webp</code>, etc.<br>
        También podés pegar URLs externas directamente abajo.
      </div>
      <br>
      <label>URLs de fotos (una por línea)</label>
      <textarea id="f-fotos-manual" style="min-height:80px; font-size:12px;" placeholder="Pegá URLs externas, o dejá vacío si ya copiaste las fotos a la carpeta"></textarea>
    </div>

    <hr class="sep">

    <button class="btn btn-orange" style="width:100%" onclick="generarFicha()">
      <span id="btn-generar-txt">✦ Generar y publicar ficha</span>
      <span id="btn-generar-loader" class="loader" style="display:none"></span>
    </button>

    <div id="status-msg" class="status"></div>

    <div class="result-box" id="result-box">
      <div class="lbl">Ficha publicada en</div>
      <div class="result-link" id="result-link"></div>
      <div class="result-actions">
        <button class="btn btn-sm btn-outline" style="background:rgba(255,255,255,.1);color:#fff;border-color:rgba(255,255,255,.2)" onclick="copiarLink()">Copiar link</button>
        <a id="result-open" href="#" target="_blank" class="btn btn-sm btn-orange">Abrir ficha →</a>
      </div>
    </div>
  </div>
</main>

<script>
let portalActual = 'zonaprop';
let fotosZP = [];

function setPortal(p) {
  portalActual = p;
  document.querySelectorAll('.pill').forEach(el => el.classList.remove('active'));
  event.target.classList.add('active');

  const urlSection = document.getElementById('url-section');
  const hint = document.getElementById('url-hint');

  if (p === 'manual') {
    urlSection.style.display = 'none';
    mostrarFormulario({});
  } else {
    urlSection.style.display = 'block';
    if (p === 'zonaprop') hint.textContent = 'ZonaProp: extracción automática completa de datos y fotos.';
    else if (p === 'ml') hint.textContent = 'MercadoLibre: pegá la URL del aviso directamente. Extracción automática completa vía API (datos + fotos).';
    else if (p === 'c21') hint.textContent = 'Century 21: guardá la página con Cmd+S y pegá el path al archivo. El precio completalo manualmente.';
  }
}

async function extraerDatos() {
  const url = document.getElementById('url-input').value.trim();
  if (!url) { showStatus('Ingresá una URL primero.', 'error'); return; }

  setBtnLoading('btn-extraer', true);
  showStatus('Extrayendo datos...', 'info');

  try {
    const resp = await fetch('/extraer', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ url, portal: portalActual })
    });
    const data = await resp.json();
    if (data.error) { showStatus(data.error, 'error'); return; }
    showStatus('✓ Datos extraídos. Revisá y completá lo que falte.', 'success');
    mostrarFormulario(data);
  } catch(e) {
    showStatus('Error al conectar con el servidor.', 'error');
  } finally {
    setBtnLoading('btn-extraer', false);
  }
}

function mostrarFormulario(d) {
  document.getElementById('form-card').style.display = 'block';
  document.getElementById('form-card').scrollIntoView({ behavior: 'smooth', block: 'start' });

  if (d.operacion) setSelect('f-operacion', d.operacion);
  if (d.tipo) setSelect('f-tipo', d.tipo);
  if (d.direccion) document.getElementById('f-direccion').value = d.direccion;
  if (d.barrio) document.getElementById('f-barrio').value = d.barrio;
  if (d.precio) document.getElementById('f-precio').value = d.precio;
  if (d.expensas) document.getElementById('f-expensas').value = d.expensas;
  if (d.ambientes) document.getElementById('f-ambientes').value = d.ambientes;
  if (d.dormitorios) document.getElementById('f-dormitorios').value = d.dormitorios;
  if (d.banos) document.getElementById('f-banos').value = d.banos;
  if (d.toilette) document.getElementById('f-toilette').value = d.toilette;
  if (d.sup_total) document.getElementById('f-sup-total').value = d.sup_total;
  if (d.sup_cubierta) document.getElementById('f-sup-cubierta').value = d.sup_cubierta;
  if (d.antiguedad) document.getElementById('f-antiguedad').value = d.antiguedad;
  if (d.disposicion) setSelect('f-disposicion', d.disposicion);
  if (d.orientacion) setSelect('f-orientacion', d.orientacion);
  if (d.descripcion) document.getElementById('f-descripcion').value = d.descripcion;
  window.scrapedInmo = d.inmobiliaria || '';
  window.scrapedWa = d.whatsapp_publicador || '';

  // Badges
  const badges = d.badges || [];
  ['f-badge1','f-badge2','f-badge3','f-badge4','f-badge5','f-badge6'].forEach((id, i) => {
    document.getElementById(id).value = badges[i] || '';
  });

  // Fotos
  const zpSec = document.getElementById('fotos-zp-section');
  const manSec = document.getElementById('fotos-manual-section');

  if ((portalActual === 'zonaprop' || portalActual === 'ml') && d.fotos && d.fotos.length) {
    zpSec.style.display = 'block';
    manSec.style.display = 'none';
    document.getElementById('f-fotos').value = d.fotos.join('\n');
    fotosZP = d.fotos;
  } else if (portalActual === 'manual') {
    zpSec.style.display = 'block';
    manSec.style.display = 'none';
    document.getElementById('f-fotos').value = '';
  } else {
    zpSec.style.display = 'none';
    manSec.style.display = 'block';
    // Mostrar path esperado de carpeta
    const slug = slugify((d.barrio || '') + '-' + (d.direccion || ''));
    document.getElementById('fotos-carpeta-path').textContent = 'assets/fotos/' + slug + '/';
  }
}

function setSelect(id, val) {
  const sel = document.getElementById(id);
  for (let opt of sel.options) {
    if (opt.value.toLowerCase() === val.toLowerCase() || opt.text.toLowerCase() === val.toLowerCase()) {
      sel.value = opt.value;
      break;
    }
  }
}

function slugify(s) {
  return s.toLowerCase()
    .replace(/[áàä]/g,'a').replace(/[éèë]/g,'e')
    .replace(/[íìï]/g,'i').replace(/[óòö]/g,'o')
    .replace(/[úùü]/g,'u').replace(/ñ/g,'n')
    .replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
}

async function generarFicha() {
  const dir = document.getElementById('f-direccion').value.trim();
  const bar = document.getElementById('f-barrio').value.trim();
  if (!dir || !bar) { showStatus('Dirección y barrio son obligatorios.', 'error'); return; }

  // Recopilar fotos
  let fotos = [];
  if (portalActual === 'zonaprop' || portalActual === 'manual') {
    const txt = document.getElementById('f-fotos').value.trim();
    fotos = txt ? txt.split('\n').map(l => l.trim()).filter(l => l.startsWith('http')) : [];
  } else {
    const txt = document.getElementById('f-fotos-manual').value.trim();
    fotos = txt ? txt.split('\n').map(l => l.trim()).filter(l => l.startsWith('http')) : [];
  }

  const payload = {
    portal: portalActual,
    url_original: portalActual !== 'manual' ? document.getElementById('url-input').value.trim() : '',
    operacion: document.getElementById('f-operacion').value,
    tipo: document.getElementById('f-tipo').value,
    direccion: dir,
    barrio: bar,
    precio: document.getElementById('f-precio').value,
    expensas: document.getElementById('f-expensas').value,
    ambientes: document.getElementById('f-ambientes').value,
    dormitorios: document.getElementById('f-dormitorios').value,
    banos: document.getElementById('f-banos').value,
    toilette: document.getElementById('f-toilette').value,
    sup_total: document.getElementById('f-sup-total').value,
    sup_cubierta: document.getElementById('f-sup-cubierta').value,
    antiguedad: document.getElementById('f-antiguedad').value,
    disposicion: document.getElementById('f-disposicion').value,
    orientacion: document.getElementById('f-orientacion').value,
    badges: [
      document.getElementById('f-badge1').value,
      document.getElementById('f-badge2').value,
      document.getElementById('f-badge3').value,
      document.getElementById('f-badge4').value,
      document.getElementById('f-badge5').value,
      document.getElementById('f-badge6').value,
    ].filter(b => b.trim()),
    descripcion: document.getElementById('f-descripcion').value,
    video: document.getElementById('f-video').value,
    inmobiliaria: window.scrapedInmo || '',
    whatsapp_publicador: window.scrapedWa || '',
    fotos: fotos,
  };

  setBtnLoading('btn-generar', true);
  showStatus('Generando ficha y subiendo a GitHub...', 'info');

  try {
    const resp = await fetch('/generar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (data.error) { showStatus('Error: ' + data.error, 'error'); return; }

    showStatus('✓ Ficha publicada. GitHub Pages tarda ~30 segundos en actualizarse.', 'success');
    const box = document.getElementById('result-box');
    box.style.display = 'block';
    document.getElementById('result-link').textContent = data.url;
    document.getElementById('result-open').href = data.url;
    box.scrollIntoView({ behavior: 'smooth' });
  } catch(e) {
    showStatus('Error al generar la ficha.', 'error');
  } finally {
    setBtnLoading('btn-generar', false);
  }
}

function copiarLink() {
  const link = document.getElementById('result-link').textContent;
  navigator.clipboard.writeText(link).then(() => {
    showStatus('✓ Link copiado al portapapeles.', 'success');
  });
}

function showStatus(msg, type) {
  const el = document.getElementById('status-msg');
  el.textContent = msg;
  el.className = 'status ' + type;
  el.style.display = 'block';
}

function setBtnLoading(btnId, loading) {
  document.getElementById(btnId + '-txt').style.display = loading ? 'none' : '';
  document.getElementById(btnId + '-loader').style.display = loading ? 'inline-block' : 'none';
}

function resetTodo() {
  // Reset portal
  portalActual = 'zonaprop';
  fotosZP = [];
  document.querySelectorAll('.pill').forEach(el => el.classList.remove('active'));
  document.querySelector('.pill').classList.add('active');
  document.getElementById('url-section').style.display = 'block';
  document.getElementById('url-hint').textContent = 'ZonaProp: extracción automática completa de datos y fotos.';

  // Limpiar URL
  document.getElementById('url-input').value = '';

  // Ocultar formulario y resultados
  document.getElementById('form-card').style.display = 'none';
  document.getElementById('result-box').style.display = 'none';
  document.getElementById('status-msg').style.display = 'none';

  // Limpiar todos los campos
  ['f-direccion','f-barrio','f-precio','f-expensas',
   'f-badge1','f-badge2','f-badge3','f-badge4','f-badge5','f-badge6','f-descripcion','f-video',
   'f-fotos','f-fotos-manual'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['f-ambientes','f-dormitorios','f-banos','f-toilette',
   'f-sup-total','f-sup-cubierta','f-antiguedad'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('f-operacion').selectedIndex = 0;
  document.getElementById('f-tipo').selectedIndex = 0;
  document.getElementById('f-disposicion').selectedIndex = 0;
  document.getElementById('f-orientacion').selectedIndex = 0;

  window.scrollTo({ top: 0, behavior: 'smooth' });
}
</script>
</body>
</html>"""

# ─── DETECCIÓN AUTOMÁTICA DE BADGES ───────────────────────────────────────────
BADGE_RULES = [
    # (lista de keywords, badge a mostrar, clase css)
    (['apto crédito', 'apto credito', 'apto al crédito', 'apto al credito'], 'Apto crédito', 'grn'),
    (['apto mascota', 'apto mascotas', 'mascotas permitidas'], 'Apto mascota', ''),
    (['apto profesional'], 'Apto profesional', ''),
    (['parrilla'], 'Parrilla', ''),
    (['quincho'], 'Quincho', ''),
    (['cochera', 'garage', 'garaje', 'guarda coche', 'guardacoche', 'coche'], 'Cochera', ''),
    (['amenities', 'sum ', ' sum,', 'pileta', 'gimnasio', 'piscina'], 'Amenities', ''),
    (['muy luminoso', 'luminoso', 'mucha luz', 'excelente luminosidad'], 'Luminoso', ''),
    (['terraza'], 'Terraza', ''),
    (['jardín', 'jardin'], 'Jardín', ''),
    (['seguridad 24', 'vigilancia', 'seguridad las 24'], 'Seguridad 24hs', ''),
    (['a estrenar', 'estrenar'], 'A estrenar', 'org'),
]
MAX_BADGES = 6

def detectar_badges(datos: dict) -> list:
    """
    Detecta badges automáticamente desde descripción + título + atributos.
    Devuelve lista de strings, máximo MAX_BADGES.
    Respeta badges ya seteados manualmente si vienen en datos['badges'].
    """
    # Texto base para buscar
    texto = ' '.join([
        datos.get('descripcion', ''),
        datos.get('titulo', ''),
        datos.get('tipo', ''),
        datos.get('disposicion', ''),
        str(datos.get('ambientes', '')),
        datos.get('tags', ''),
    ]).lower()

    encontrados = []
    for keywords, badge, _ in BADGE_RULES:
        for kw in keywords:
            if kw in texto:
                encontrados.append(badge)
                break  # no duplicar si hay múltiples keywords del mismo badge

    # Respetar badges manuales existentes, agregar detectados sin duplicar
    manuales = [b for b in datos.get('badges', []) if b and b.strip()]
    vistos = set(b.lower() for b in manuales)
    for b in encontrados:
        if b.lower() not in vistos and len(manuales) < MAX_BADGES:
            manuales.append(b)
            vistos.add(b.lower())

    return manuales[:MAX_BADGES]


# ─── EXTRACCIÓN ZONAPROP ────────────────────────────────────────────────────────
def extraer_zonaprop(url: str) -> dict:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'es-AR,es;q=0.9',
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    html = r.text

    # Extraer JSON avisoInfo embebido
    m = re.search(r'const avisoInfo\s*=\s*(\{.*?\})\s*\n\s*const dataLayerInfo', html, re.DOTALL)
    if not m:
        raise ValueError("No se encontró avisoInfo en la página. ZonaProp puede estar bloqueando el scraping.")

    # Limpiar y parsear JSON (tiene trailing commas a veces)
    raw = m.group(1)
    # Extraer campos específicos con regex más robusto
    datos = {}

    # Precio
    pm = re.search(r"'price'\s*:\s*'([^']+)'", raw)
    datos['precio'] = pm.group(1).strip() if pm else ''

    # Operación
    om = re.search(r"'operationType'\s*:\s*'([^']+)'", html)
    datos['operacion'] = om.group(1).capitalize() if om else 'Venta'

    # Tipo de propiedad — tipoDePropiedad es el campo más confiable
    tm = re.search(r"'tipoDePropiedad'\s*:\s*'([^']+)'", html)
    if not tm:
        tm = re.search(r"'realEstateType'\s*:\s*\{\"name\":\"([^\"]+)\"", raw)
    if not tm:
        tm = re.search(r"'propertyType'\s*:\s*'([^']+)'", html)
    datos['tipo'] = tm.group(1).strip() if tm else 'Departamento'

    # Dirección
    dm = re.search(r'"name"\s*:\s*"([^"]+)","visibility"', raw)
    datos['direccion'] = dm.group(1) if dm else ''

    # Barrio — múltiples fuentes de fallback
    bm = re.search(r"'terminoUbicacion'\s*:\s*'([^']+)'", html)
    if not bm:
        bm = re.search(r"locationName\s*=\s*\"([^\"]+)\"", html)
    if not bm:
        bm = re.search(r"'ciudad'\s*:\s*'([^']+)'", html)
    datos['barrio'] = bm.group(1).strip() if bm else ''

    # Descripción — el campo usa comillas dobles en el HTML de ZonaProp
    desc_m = re.search(r"'description'\s*:\s*\"(.*?)\",\s*\n", raw, re.DOTALL)
    if not desc_m:
        desc_m = re.search(r"'description'\s*:\s*'(.*?)',\s*\n", raw, re.DOTALL)
    if desc_m:
        desc = desc_m.group(1)
        desc = re.sub(r'<span[^>]*>.*?</span>', '', desc, flags=re.DOTALL)
        desc = re.sub(r'<[^>]+>', '\n', desc)
        desc = re.sub(r'\\n', '\n', desc)
        desc = re.sub(r'\n{3,}', '\n\n', desc)
        datos['descripcion'] = desc.strip()
    else:
        datos['descripcion'] = ''

    # Main features
    mf_m = re.search(r"'mainFeatures'\s*:\s*(\{.*?\}),\s*\n", raw, re.DOTALL)
    if mf_m:
        mf_raw = mf_m.group(1)
        def feat(key):
            m = re.search(rf'"{key}"\s*:\s*\{{[^}}]*"value"\s*:\s*"([^"]+)"', mf_raw)
            return m.group(1) if m else ''
        datos['ambientes']    = feat('CFT1')
        datos['dormitorios']  = feat('CFT2')
        datos['banos']        = feat('CFT3')
        datos['toilette']     = feat('CFT4') or ''
        datos['sup_total']    = feat('CFT100')
        datos['sup_cubierta'] = feat('CFT101')
        datos['antiguedad']   = feat('CFT5')
        datos['disposicion']  = feat('1000019')
        datos['orientacion']  = feat('1000027') or ''

    # Expensas
    exp_m = re.search(r"'expenses'\s*:\s*'([^']+)'", raw)
    if not exp_m:
        exp_m = re.search(r'"expenses"\s*:\s*"([^"]+)"', raw)
    if not exp_m:
        exp_m = re.search(r"'expenses'\s*:\s*(\d+)", raw)
    if exp_m:
        exp_val = exp_m.group(1).strip()
        if exp_val and exp_val != '0':
            if exp_val.isdigit():
                datos['expensas'] = f"$ {int(exp_val):,}".replace(',', '.')
            else:
                datos['expensas'] = exp_val
        else:
            datos['expensas'] = ''
    else:
        datos['expensas'] = ''

    # Fotos (pictures array)
    pics_m = re.search(r"'pictures'\s*:\s*(\[.*?\]),\s*\n\s*\n", raw, re.DOTALL)
    fotos = []
    if pics_m:
        urls = re.findall(r'"url1200x1200"\s*:\s*"([^"]+)"', pics_m.group(1))
        fotos = [u for u in urls if u]
    datos['fotos'] = fotos

    # Tags/flags de ZonaProp (flagsFeatures) — incluye "Apto crédito", etc.
    flags_m = re.search(r"'flagsFeatures'\s*:\s*(\[.*?\])", raw, re.DOTALL)
    if flags_m:
        labels = re.findall(r'"label"\s*:\s*"([^"]+)"', flags_m.group(1))
        datos['tags'] = ' '.join(labels).lower()
    else:
        datos['tags'] = ''

    # Inmobiliaria/publisher
    pub_m = re.search(r"'publisher'\s*:\s*\{[^}]*'name'\s*:\s*'([^']+)'", raw)
    if not pub_m:
        pub_m = re.search(r'"realEstateAgency"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', raw)
    if not pub_m:
        pub_m = re.search(r'"advertiser"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', raw)
    datos['inmobiliaria'] = pub_m.group(1).strip() if pub_m else ''

    # WhatsApp / teléfono — fallback chain
    wa_m = re.search(r"'whatsApp'\s*:\s*'([^']+)'", raw)
    if wa_m:
        datos['whatsapp_publicador'] = wa_m.group(1).strip()
    else:
        ph_m = re.search(r"'phone'\s*:\s*'([^']+)'", raw)
        if ph_m:
            datos['whatsapp_publicador'] = ph_m.group(1).strip()
        else:
            pp_m = re.search(r"'partialPhone'\s*:\s*'([^']+)'", raw)
            datos['whatsapp_publicador'] = pp_m.group(1).strip() if pp_m else ''

    # Fecha real de publicacion
    fp_m = re.search(r"'publicationDateFormatted'\s*:\s*'([^']+)'", raw)
    datos['fecha_publicacion'] = fp_m.group(1).strip() if fp_m else ''

    datos['badges'] = detectar_badges(datos)
    return datos
def extraer_ml(url: str) -> dict:
    """
    Llama a la API pública de MercadoLibre.
    Acepta cualquier URL de ML (ej: https://inmuebles.mercadolibre.com.ar/...MLA123456789-...)
    Extrae el item ID y consulta api.mercadolibre.com/items/{ID}
    Gratis, sin auth, sin Cmd+S.
    """
    # Extraer ID del item de la URL (formato MLA + dígitos)
    id_m = re.search(r'MLA-?(\d+)', url)
    if not id_m:
        raise ValueError("No se encontró un ID de MercadoLibre en la URL. Asegurate de pegar la URL completa del aviso (debe contener MLAxxxxxxxx).")
    item_id = f"MLA{id_m.group(1)}"

    # Llamar API pública — no requiere auth para datos básicos
    api_url = f"https://api.mercadolibre.com/items/{item_id}"
    r = requests.get(api_url, timeout=20)
    r.raise_for_status()
    item = r.json()

    # También traer descripción desde endpoint separado
    desc_r = requests.get(f"{api_url}/description", timeout=20)
    descripcion = ''
    if desc_r.status_code == 200:
        descripcion = desc_r.json().get('plain_text', '')

    datos = {'operacion': 'Venta', 'fotos': []}

    # Tipo y operación desde título / categoría
    titulo = item.get('title', '')
    TIPO_MAP = {'ph': 'PH', 'departamento': 'Departamento', 'casa': 'Casa',
                'local': 'Local', 'oficina': 'Oficina', 'terreno': 'Terreno',
                'duplex': 'Duplex', 'loft': 'Loft'}
    datos['tipo'] = 'Departamento'
    for k, v in TIPO_MAP.items():
        if k in titulo.lower():
            datos['tipo'] = v
            break

    # Precio
    precio_val = item.get('price', '')
    moneda = item.get('currency_id', '')
    sym = 'USD' if moneda in ('USD', 'U$S', 'US$') else '$'
    if precio_val:
        datos['precio'] = f"{sym} {int(precio_val):,}".replace(',', '.')
    else:
        datos['precio'] = ''

    # Ubicación
    loc = item.get('location', {})
    calle = loc.get('address_line', '')
    barrio = (loc.get('neighborhood', {}) or {}).get('name', '')
    if not barrio:
        barrio = (loc.get('city', {}) or {}).get('name', '')
    datos['direccion'] = calle
    datos['barrio'] = barrio

    # Atributos (ambientes, dorms, baños, sup, antigüedad, expensas, etc.)
    attrs = {a['id']: a.get('value_name', '') or str(a.get('value_struct', {}).get('number', '')) 
             for a in item.get('attributes', []) if a.get('value_name') or a.get('value_struct')}

    def num(val):
        m = re.search(r'\d+', str(val).replace('.',''))
        return m.group(0) if m else ''

    datos['ambientes']    = num(attrs.get('ROOMS', ''))
    datos['dormitorios']  = num(attrs.get('BEDROOMS', ''))
    datos['banos']        = num(attrs.get('FULL_BATHROOMS', '') or attrs.get('BATHROOMS', ''))
    datos['toilette']     = num(attrs.get('HALF_BATHROOMS', ''))
    datos['sup_total']    = num(attrs.get('TOTAL_AREA', ''))
    datos['sup_cubierta'] = num(attrs.get('COVERED_AREA', ''))
    datos['antiguedad']   = num(attrs.get('PROPERTY_AGE', ''))
    datos['disposicion']  = attrs.get('DISPOSITION', '')
    datos['orientacion']  = attrs.get('ORIENTATION', '')

    # Expensas
    exp_raw = attrs.get('EXPENSES', '') or attrs.get('MAINTENANCE_FEE', '')
    if exp_raw and exp_raw not in ('0', '0 ARS', ''):
        datos['expensas'] = f"$ {num(exp_raw)}" if num(exp_raw) else exp_raw
    else:
        datos['expensas'] = ''

    # Descripción
    datos['descripcion'] = descripcion.strip()

    # Fotos en alta resolución
    pictures = item.get('pictures', [])
    fotos = []
    for pic in pictures:
        url_foto = pic.get('url', '') or pic.get('secure_url', '')
        if url_foto:
            # ML API devuelve URLs con sufijo -F (full) o -O (original)
            url_big = re.sub(r'-[A-Z]\.(?:jpg|webp|jpeg)$', '-O.jpg', url_foto, flags=re.IGNORECASE)
            fotos.append(url_big)
    datos['fotos'] = fotos

    # Inmobiliaria — seller_contact en la respuesta de la API
    seller = item.get('seller_contact', {}) or {}
    datos['inmobiliaria'] = seller.get('contact', '') or seller.get('other_info', '') or ''
    if not datos['inmobiliaria']:
        # Fallback: seller address o company_name si existe
        datos['inmobiliaria'] = item.get('official_store_name', '') or ''

    # WhatsApp/telefono y fecha publicacion — no disponibles via API publica de ML
    datos['whatsapp_publicador'] = ''
    datos['fecha_publicacion'] = ''

    datos['badges'] = detectar_badges(datos)
    return datos


# ─── EXTRACCIÓN C21 ────────────────────────────────────────────────────────────
def extraer_c21(html_path_or_url: str) -> dict:
    """C21 es SPA — extrae desde meta OG tags. Acepta HTML guardado o URL."""
    from pathlib import Path as _Path
    if _Path(html_path_or_url).exists():
        html = _Path(html_path_or_url).read_text(encoding='utf-8', errors='ignore')
    else:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        r = requests.get(html_path_or_url, headers=headers, timeout=20)
        r.raise_for_status()
        html = r.text

    soup = BeautifulSoup(html, 'html.parser')
    datos = {'operacion': 'Venta', 'fotos': []}

    # Meta OG
    og = {}
    for meta in soup.find_all('meta'):
        prop = meta.get('property','') or meta.get('name','')
        content = meta.get('content','')
        if prop and content:
            og[prop] = content

    titulo = og.get('og:title', '')
    descripcion = og.get('og:description', '')

    # Tipo desde título
    TIPO_MAP = {'ph': 'PH', 'departamento': 'Departamento', 'casa': 'Casa',
                'local': 'Local', 'oficina': 'Oficina', 'terreno': 'Terreno'}
    datos['tipo'] = 'Departamento'
    for k, v in TIPO_MAP.items():
        if k in titulo.lower():
            datos['tipo'] = v
            break

    # Operación desde título
    datos['operacion'] = 'Alquiler' if 'alquiler' in titulo.lower() else 'Venta'

    # Barrio desde título — último token antes de "Argentina"
    barrio_m = re.search(r'en\s+([\w\s]+?)(?:\s+\w+)?\s+Argentina', titulo, re.I)
    datos['barrio'] = barrio_m.group(1).strip() if barrio_m else ''

    # Dirección desde descripción — primera línea suele tenerla
    datos['direccion'] = ''
    dir_m = re.search(r'(?:calle|av[.]|avenida|entre)\s+([^.\n]+)', descripcion, re.I)
    if dir_m:
        datos['direccion'] = dir_m.group(1).strip()

    # Precio — C21 SPA no lo incluye en el HTML estático, dejamos vacío para completar
    datos['precio'] = ''

    # Descripción limpia
    datos['descripcion'] = descripcion.strip()

    # Dormitorios desde título
    dorm_m = re.search(r'(\d+)\s+[Dd]ormitorios?', titulo)
    datos['dormitorios'] = dorm_m.group(1) if dorm_m else ''

    # Fotos desde meta og:image (solo las que hay — resto manual)
    fotos = []
    for meta in soup.find_all('meta', property='og:image:secure_url'):
        url = meta.get('content','')
        if url and url not in fotos:
            fotos.append(url)
    if not fotos:
        for meta in soup.find_all('meta', property='og:image'):
            url = meta.get('content','')
            if url and url.startswith('http') and url not in fotos:
                fotos.append(url)
    # También buscar en CDN
    cdn_urls = re.findall(r"https://cdn\.21online\.lat[^\s\"'<>]+\.(?:jpg|jpeg|png|webp)", html, re.I)
    for u in cdn_urls:
        if u not in fotos:
            fotos.append(u)
    datos['fotos'] = fotos

    # Inmobiliaria — C21 SPA no expone este dato en meta OG, se deja vacío
    datos['inmobiliaria'] = ''
    datos['whatsapp_publicador'] = ''
    datos['fecha_publicacion'] = ''

    datos['badges'] = detectar_badges(datos)
    return datos
CDN = "https://img10.naventcdn.com/ficha/RPFICv5.401.1-RC1"
ICONOS = {
    "ambientes":    f"{CDN}/ambientes.9e33dd.svg",
    "dormitorios":  f"{CDN}/dormitorio.349d35.svg",
    "banos":        f"{CDN}/banos.827612.svg",
    "toilette":     f"{CDN}/toilete.f725dc.svg",
    "sup_total":    f"{CDN}/stotal.38e4f4.svg",
    "sup_cubierta": f"{CDN}/scubierta.695fb2.svg",
    "antiguedad":   f"{CDN}/antiguedad.eb15bc.svg",
    "disposicion":  f"{CDN}/disposicion.2ba2d5.svg",
    "orientacion":  f"{CDN}/orientacion.3a91e2.svg",
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

TEMPLATE = open(Path(__file__).parent / "template_ficha.html").read() if (Path(__file__).parent / "template_ficha.html").exists() else None

def slugify(texto: str) -> str:
    texto = texto.lower().strip()
    for src, dst in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n'),
                     ('à','a'),('è','e'),('ì','i'),('ò','o'),('ù','u'),
                     ('ä','a'),('ë','e'),('ï','i'),('ö','o'),('ü','u')]:
        texto = texto.replace(src, dst)
    texto = re.sub(r'[^a-z0-9]+', '-', texto)
    return texto.strip('-')

def wa_url(direccion: str) -> str:
    msg = f"Hola, vi la ficha de {direccion} y quiero más información."
    return f"https://wa.me/5491178268244?text={quote(msg)}"


def mapa_url(direccion: str, barrio: str) -> str:
    # Embed de Google Maps SIN API key. Normaliza "al NNN" -> "NNN" (altura CABA).
    import re
    dir_limpia = re.sub(r'\bal\s+(\d+)', r'\1', direccion, flags=re.IGNORECASE).strip()
    q = quote(f"{dir_limpia}, {barrio}, Buenos Aires, Argentina")
    return f"https://maps.google.com/maps?q={q}&z=17&output=embed"


def nombre_unico(directorio: Path, nombre_base: str) -> Path:
    path = directorio / f"{nombre_base}.html"
    if not path.exists():
        return path
    h = hashlib.md5(str(time.time()).encode()).hexdigest()[:4]
    return directorio / f"{nombre_base}-{h}.html"


def git_push(repo: Path, mensaje: str):
    # ponytail: limpia un index.lock viejo antes de operar (single-user, no hay git concurrente)
    lock = repo / '.git' / 'index.lock'
    if lock.exists():
        try: lock.unlink()
        except OSError: pass
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', mensaje], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'push'], cwd=repo, check=True, capture_output=True)




# ─── GOOGLE SHEETS (registro de fichas) ─────────────────────────────────────────
SHEET_ID      = '1LEBztjtgGCj0PzpRnpcZezQaM0rmdycHVCHr4aZTjmw'
CREDS_PATH    = REPO_PATH.parent / 'zonaprop_scraper' / 'google_credentials.json'
SHEETS_SCOPES = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
]

def agregar_ficha_a_sheets(d: dict, link_nl: str, link_og: str, ficha_id: str):
    """
    Agrega una fila en la solapa 'Fichas' del Google Sheet.
    Si falla la conexión, logea el error pero NO interrumpe el flujo.
    """
    import traceback
    print(f'[Sheets] Iniciando — ficha_id={ficha_id!r}', flush=True)
    print(f'[Sheets] CREDS_PATH={CREDS_PATH} exists={CREDS_PATH.exists()}', flush=True)
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        from datetime import date

        print('[Sheets] Cargando credenciales...', flush=True)
        creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SHEETS_SCOPES)
        print(f'[Sheets] Service account: {creds.service_account_email}', flush=True)

        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        print(f'[Sheets] Spreadsheet: {sh.title!r}', flush=True)

        ws = sh.worksheet('Fichas')
        print(f'[Sheets] Worksheet: {ws.title!r}', flush=True)

        fecha = date.today().strftime('%d/%m/%Y')

        precio_raw = d.get('precio', '')
        precio_usd = re.sub(r'^(USD|U\$S|US\$|\$)\s*', '', precio_raw, flags=re.IGNORECASE).strip()

        badges_lower = [b.lower() for b in d.get('badges', [])]
        descripcion_lower = d.get('descripcion', '').lower()

        cochera_keywords = ['cochera', 'garage', 'garaje', 'guarda coche', 'guardacoche', 'coche']
        cochera = 'SI' if (any('cochera' in b for b in badges_lower) or
                           any(k in descripcion_lower for k in cochera_keywords)) else 'NO'

        credito_keywords = ['apto crédito', 'apto credito', 'apto al crédito', 'apto al credito', 'crédito', 'credito']
        apto_credito = 'SI' if (any('apto cr' in b for b in badges_lower) or
                                any(k in descripcion_lower for k in credito_keywords)) else 'NO'

        fila = [
            fecha,                   # FECHA
            d.get('direccion', ''),  # DIRECCIÓN
            d.get('barrio', ''),     # BARRIO
            d.get('tipo', ''),       # TIPO
            d.get('ambientes', ''),  # AMB
            precio_usd,              # PRECIO USD
            d.get('expensas', ''),   # EXPENSAS
            cochera,                 # COCHERA
            apto_credito,            # APTO CREDITO
            link_nl,                 # LINK NL
            link_og,                 # LINK OG
            '',                      # CLIENTE
            '',                      # ESTADO
            '',                      # COMENTARIOS
            ficha_id,                # ID
            d.get('inmobiliaria', ''),         # INMOBILIARIA
            d.get('whatsapp_publicador', ''),   # WHATSAPP/TEL PUBLICADOR
            d.get('fecha_publicacion', ''),     # FECHA PUBLICACION REAL
        ]

        print(f'[Sheets] Fila a escribir: {fila}', flush=True)
        resultado = ws.append_row(fila, value_input_option='USER_ENTERED')
        print(f'[Sheets] Respuesta de la API: {resultado}', flush=True)
        print(f'[Sheets] OK — fila agregada: {ficha_id}', flush=True)

        # ── Dedup check: marcar en amarillo si la dirección ya existía ──────
        try:
            nueva_fila_idx = ws.row_count  # fila recién agregada
            dir_nueva = str(d.get('direccion', '')).strip().lower()
            if dir_nueva:
                todas = ws.get_all_values()
                headers = todas[0] if todas else []
                col_dir = next((i for i, h in enumerate(headers) if 'DIRECCI' in h.upper()), None)
                if col_dir is not None:
                    # Buscar dirección igual en filas anteriores (excluir la recién agregada)
                    duplicados = [
                        i + 2  # +1 por header, +1 por base-1
                        for i, row in enumerate(todas[1:-1])  # excluir última fila (la nueva)
                        if len(row) > col_dir and row[col_dir].strip().lower() == dir_nueva
                    ]
                    if duplicados:
                        # Pintar DIRECCIÓN de la fila nueva en amarillo
                        ultima_fila = len(todas)
                        ws.format(
                            f'{chr(65 + col_dir)}{ultima_fila}',
                            {'backgroundColor': {'red': 1.0, 'green': 0.95, 'blue': 0.0}}
                        )
                        print(f'[Sheets] ⚠️  Posible duplicado — dirección ya existe en fila(s): {duplicados}', flush=True)
                    else:
                        print(f'[Sheets] ✅ Sin duplicados detectados', flush=True)
        except Exception as dedup_err:
            print(f'[Sheets] Dedup check falló (no crítico): {dedup_err}', flush=True)

    except Exception as e:
        print(f'[Sheets] EXCEPCIÓN: {type(e).__name__}: {e}', flush=True)
        print(traceback.format_exc(), flush=True)



# ─── ROUTES ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/extraer', methods=['POST'])
def extraer():
    body = request.get_json()
    url = body.get('url', '').strip()
    portal = body.get('portal', 'zonaprop')

    try:
        if portal == 'zonaprop':
            datos = extraer_zonaprop(url)
        elif portal == 'ml':
            datos = extraer_ml(url)
        elif portal == 'c21':
            datos = extraer_c21(url)
        else:
            datos = {}
        return jsonify(datos)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/generar', methods=['POST'])
def generar():
    d = request.get_json()
    fotos = d.get('fotos', [])

    # Para C21 sin fotos externas: buscar fotos locales en la carpeta
    portal = d.get('portal', 'zonaprop')
    if portal == 'c21' and not fotos:
        slug_dir = slugify(d.get('barrio','') + '-' + d.get('direccion',''))
        carpeta = FOTOS_DIR / slug_dir
        if carpeta.exists():
            fotos_locales = sorted(carpeta.glob('*.webp')) + sorted(carpeta.glob('*.jpg')) + sorted(carpeta.glob('*.jpeg')) + sorted(carpeta.glob('*.png'))
            fotos = [f'{GITHUB_BASE}/assets/fotos/{slug_dir}/{f.name}' for f in fotos_locales]

    if not fotos:
        error_msg = 'No hay fotos. Para C21 copiá las imágenes a assets/fotos/slug/ antes de generar.' if portal == 'c21' else 'No hay fotos disponibles.'
        return jsonify({'error': error_msg}), 400

    # Generar nombre de archivo — formato: tipo-direccion-Xamb[-hash]
    TIPO_SLUG = {
        'Departamento': 'dto', 'PH': 'ph', 'Casa': 'casa',
        'Local': 'local', 'Oficina': 'oficina', 'Terreno': 'terreno',
        'Duplex': 'duplex', 'Loft': 'loft',
    }
    tipo_raw  = d.get('tipo', 'Departamento')
    tipo_slug  = TIPO_SLUG.get(tipo_raw, slugify(tipo_raw))
    barrio_slug = slugify(d.get('barrio', ''))
    direccion  = slugify(d.get('direccion', 'sin-direccion'))
    ambientes = str(d.get('ambientes', '')).strip()
    slug_amb  = f'-{ambientes}amb' if ambientes else ''
    nombre_base = f'{tipo_slug}-{barrio_slug}-{direccion}{slug_amb}'

    FICHAS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = nombre_unico(FICHAS_DIR, nombre_base)

    try:
        # Importar template
        sys.path.insert(0, str(Path(__file__).parent))
        from template_ficha import TEMPLATE as TPL
    except ImportError:
        return jsonify({'error': 'No se encontró template_ficha.py. Asegurate de tenerlo en la misma carpeta.'}), 500

    # Generar HTML
    html = _render(d, fotos, TPL)
    out_path.write_text(html, encoding='utf-8')

    # Git push (no-fatal: si falla —sin internet o sin .git en modo test— la ficha
    # igual quedó escrita en fichas/ y se registró en Sheets)
    try:
        git_push(REPO_PATH, f'ficha: {out_path.name}')
    except Exception as e:
        print(f'[git] push falló (no crítico): {e}', flush=True)

    url_publica = f'{GITHUB_BASE}/fichas/{out_path.name}'
    url_sheets  = f'https://nahuelim.com.ar/fichas/{out_path.name}'
    ficha_id = hashlib.md5(nombre_base.encode()).hexdigest()[:5]
    agregar_ficha_a_sheets(d, url_sheets, d.get('url_original', ''), ficha_id)
    return jsonify({'url': url_publica, 'archivo': out_path.name})


def _video_embed_src(url: str):
    """URL /embed (con autoplay) de YouTube o Vimeo, o None si no es embebible."""
    url = (url or '').strip()
    if not url:
        return None
    yt = re.search(r'(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/|live/))([\w-]{11})', url)
    if yt:
        return f'https://www.youtube.com/embed/{yt.group(1)}?autoplay=1&rel=0'
    vi = re.search(r'vimeo\.com/(?:video/)?(\d+)', url)
    if vi:
        return f'https://player.vimeo.com/video/{vi.group(1)}?autoplay=1'
    return None


_VIDEO_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
               'width="13" height="13" style="flex-shrink:0"><polygon points="6 4 20 12 6 20 6 4"/></svg>')


def _video_button(url: str) -> str:
    """Botón 'Ver video' sobre el hero (abajo-izq). Abre modal si es YouTube/Vimeo;
    para cualquier otra URL abre en pestaña nueva. Vacío si no hay video."""
    url = (url or '').strip()
    if not url:
        return ''
    if _video_embed_src(url):
        return ('    <button class="mg-btn mg-btn-video" onclick="event.stopPropagation();openVideo()">'
                f'{_VIDEO_ICON} Ver video</button>\n')
    safe = _html_esc.escape(url, quote=True)
    return (f'    <a class="mg-btn mg-btn-video" href="{safe}" target="_blank" rel="noopener" '
            f'onclick="event.stopPropagation()">{_VIDEO_ICON} Ver video</a>\n')


def _video_modal(url: str) -> str:
    """Modal (lightbox) que reproduce el video embebido. Solo YouTube/Vimeo; vacío si no."""
    src = _video_embed_src(url)
    if not src:
        return ''
    return (
        '<div class="vlb" id="vlb" onclick="closeVideo()">'
        '<button class="lb-close" onclick="closeVideo()">&#x2715;</button>'
        '<div class="vlb-frame" onclick="event.stopPropagation()">'
        '<iframe id="vlb-iframe" src="" allow="autoplay; fullscreen; encrypted-media" '
        'allowfullscreen title="Video"></iframe>'
        '</div></div>\n'
        '<script>'
        f'var VLB_SRC={json.dumps(src)};'
        'function openVideo(){document.getElementById("vlb-iframe").src=VLB_SRC;'
        'document.getElementById("vlb").style.display="flex";document.body.style.overflow="hidden";}'
        'function closeVideo(){document.getElementById("vlb").style.display="none";'
        'document.getElementById("vlb-iframe").src="";document.body.style.overflow="";}'
        'document.addEventListener("keydown",function(e){if(e.key==="Escape")closeVideo();});'
        '</script>\n'
    )


def _render(d: dict, fotos: list, TPL: str) -> str:
    """Renderiza el HTML de la ficha usando el template de generate.py"""
    direccion   = d.get('direccion', '').strip()
    barrio      = d.get('barrio', '').strip()
    operacion   = d.get('operacion', 'Venta').strip()
    tipo        = d.get('tipo', 'Departamento').strip()
    precio      = d.get('precio', '').strip()
    expensas    = d.get('expensas', '').strip()
    descripcion = d.get('descripcion', '').strip()
    ambientes   = str(d.get('ambientes', '')).strip()
    badges_raw  = d.get('badges', [])

    title = f"{operacion} {ambientes} Ambientes – {direccion}, {barrio}" if ambientes else f"{operacion} {tipo} – {direccion}, {barrio}"

    foto0 = fotos[0] if fotos else ''
    mg_cells = ''
    for i in range(1, 5):
        url = fotos[i] if i < len(fotos) else (fotos[0] if fotos else '')
        mg_cells += f'    <div class="mg-cell" style="background-image:url(\'{url}\')" onclick="openLB({i})"></div>\n'

    thumbs = ''.join(f'      <img src="{url}" onclick="lbGoTo({i})">\n' for i, url in enumerate(fotos))
    photos_json = ',\n'.join(f'  "{u}"' for u in fotos)

    expensas_html = f'      <div class="exps">Expensas: <b>{expensas}</b></div>' if expensas else ''

    badge_clases = {'a estrenar': 'org', 'apto crédito': 'grn', 'apto credito': 'grn'}
    badges_html = ''
    if tipo:
        badges_html += f'        <span class="badge">{tipo}</span>\n'
    if ambientes:
        badges_html += f'        <span class="badge">{ambientes} ambientes</span>\n'
    for b in badges_raw:
        b = str(b).strip()
        if not b:
            continue
        cls = badge_clases.get(b.lower(), '')
        cls_str = f' class="badge {cls}"' if cls else ' class="badge"'
        badges_html += f'        <span{cls_str}>{b}</span>\n'

    CARACT_KEYS = ['ambientes','dormitorios','banos','toilette',
                   'sup_total','sup_cubierta','antiguedad','disposicion','orientacion']
    caract_html = ''
    for key in CARACT_KEYS:
        val = str(d.get(key, '')).strip()
        if not val:
            continue
        if key in ('sup_total', 'sup_cubierta'):
            val = f"{val} m²"
        if key == 'antiguedad':
            val = f"{val} años"
        caract_html += f'''        <div class="fi">
          <img class="fi-icon" src="{ICONOS[key]}" alt="{LABELS[key]}">
          <div class="fi-val">{val}</div>
          <div class="fi-lbl">{LABELS[key]}</div>
        </div>\n'''

    if descripcion:
        parrafos = [p.strip() for p in descripcion.split('\n\n') if p.strip()]
        if not parrafos:
            parrafos = [descripcion]
        desc_html = '\n'.join(f'        <p>{p.replace(chr(10), "<br>")}</p>' for p in parrafos)
    else:
        desc_html = '        <p>Consultá más información sobre esta propiedad.</p>'

    _og_parts = [tipo, f"{ambientes} amb" if ambientes else "", f"{barrio}, CABA" if barrio else "", precio]
    og_desc = _html_esc.escape(" · ".join(p for p in _og_parts if p), quote=True)

    return TPL.format(
        title=title,
        og_desc=og_desc,
        wa_url=wa_url(direccion),
        mapa_url=mapa_url(direccion, barrio),
        operacion=operacion,
        precio=precio,
        expensas_html=expensas_html,
        badges_html=badges_html,
        caract_html=caract_html,
        video_btn=_video_button(d.get('video', '')),
        video_modal=_video_modal(d.get('video', '')),
        desc_html=desc_html,
        foto0=foto0,
        mg_cells=mg_cells,
        n_fotos=len(fotos),
        thumbs=thumbs,
        photos_json=photos_json,
        direccion=direccion,
        barrio=barrio,
    )



if __name__ == '__main__':
    print(f"\n✓ Generador de fichas corriendo en http://localhost:{PORT}\n")
    app.run(debug=False, port=PORT, host="127.0.0.1")
