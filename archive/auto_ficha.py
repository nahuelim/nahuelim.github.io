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
REPO_PATH = Path.home() / "Documents" / "2. Inmobiliaria" / "nahuelim.github.io"
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
    <a href="/leads" style="color:rgba(255,255,255,.75);font-size:13px;font-weight:500;text-decoration:none">Leads</a>
    <a href="/acm" style="color:rgba(255,255,255,.75);font-size:13px;font-weight:500;text-decoration:none">ACM</a>
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
   'f-badge1','f-badge2','f-badge3','f-badge4','f-badge5','f-badge6','f-descripcion',
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


def _cargar_maps_key() -> str:
    from pathlib import Path
    key_file = Path.home() / "Documents" / "2. Inmobiliaria" / ".maps_api_key"
    if key_file.exists():
        return key_file.read_text().strip()
    raise RuntimeError(f"No encontré la Google Maps API key en {key_file}")

MAPS_API_KEY = _cargar_maps_key()

def mapa_url(direccion: str, barrio: str) -> str:
    import re
    dir_limpia = re.sub(r'\bal\s+(\d+)', r'\1', direccion, flags=re.IGNORECASE).strip()
    q = quote(f"{dir_limpia}, {barrio}, Buenos Aires, Argentina")
    return f"https://www.google.com/maps/embed/v1/place?key={MAPS_API_KEY}&q={q}&zoom=17"

def generar_html(d: dict, fotos: list) -> str:
    import re
    direccion    = d.get('direccion', '').strip()
    # Limpiar "al NNNN" → "NNNN" en texto visible de la ficha
    direccion    = re.sub(r'\bal\s+(\d+)', r'\1', direccion, flags=re.IGNORECASE).strip()
    barrio       = d.get('barrio', '').strip()
    operacion    = d.get('operacion', 'Venta').strip()
    tipo         = d.get('tipo', 'Departamento').strip()
    precio       = d.get('precio', '').strip()
    expensas     = d.get('expensas', '').strip()
    descripcion  = d.get('descripcion', '').strip()
    ambientes    = str(d.get('ambientes', '')).strip()
    badges_raw   = d.get('badges', [])

    title = f"{operacion} {ambientes} Ambientes – {direccion}, {barrio}" if ambientes else f"{operacion} {tipo} – {direccion}, {barrio}"

    # Mosaico
    foto0 = fotos[0] if fotos else ''
    mg_cells = ''
    for i in range(1, 5):
        url = fotos[i] if i < len(fotos) else (fotos[0] if fotos else '')
        mg_cells += f'    <div class="mg-cell" style="background-image:url(\'{url}\')" onclick="openLB({i})"></div>\n'

    # Thumbnails
    thumbs = ''
    for i, url in enumerate(fotos):
        thumbs += f'      <img src="{url}" onclick="lbGoTo({i})">\n'

    photos_json = ',\n'.join(f'  "{u}"' for u in fotos)

    # Expensas
    expensas_html = f'      <div class="exps">Expensas: <b>{expensas}</b></div>' if expensas else ''

    # Badges
    badges_html = ''
    badge_clases = {
        'a estrenar': 'org', 'apto crédito': 'grn', 'apto credito': 'grn',
        'apto profesional': 'grn',
    }
    if tipo:
        badges_html += f'        <span class="badge">{tipo}</span>\n'
    if ambientes:
        badges_html += f'        <span class="badge">{ambientes} ambientes</span>\n'
    for b in badges_raw:
        b = b.strip()
        if not b:
            continue
        cls = badge_clases.get(b.lower(), '')
        cls_str = f' class="badge {cls}"' if cls else ' class="badge"'
        badges_html += f'        <span{cls_str}>{b}</span>\n'

    # Características
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

    # Descripción
    if descripcion:
        parrafos = [p.strip() for p in descripcion.split('\n\n') if p.strip()]
        if not parrafos:
            parrafos = [descripcion]
        desc_html = '\n'.join(f'        <p>{p.replace(chr(10), "<br>")}</p>' for p in parrafos)
    else:
        desc_html = '        <p>Consultá más información sobre esta propiedad.</p>'

    _wa = wa_url(direccion)
    _mapa = mapa_url(direccion, barrio)

    # Importar template desde generate.py (inline para no depender del archivo)
    from generate_template import TEMPLATE as TPL
    html = TPL.format(
        title=title,
        wa_url=_wa,
        mapa_url=_mapa,
        operacion=operacion,
        precio=precio,
        expensas_html=expensas_html,
        badges_html=badges_html,
        caract_html=caract_html,
        desc_html=desc_html,
        foto0=foto0,
        mg_cells=mg_cells,
        n_fotos=len(fotos),
        thumbs=thumbs,
        photos_json=photos_json,
        direccion=direccion,
        barrio=barrio,
    )
    return html


def nombre_unico(directorio: Path, nombre_base: str) -> Path:
    path = directorio / f"{nombre_base}.html"
    if not path.exists():
        return path
    h = hashlib.md5(str(time.time()).encode()).hexdigest()[:4]
    return directorio / f"{nombre_base}-{h}.html"


def git_push(repo: Path, mensaje: str):
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', mensaje], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'push'], cwd=repo, check=True, capture_output=True)


# ─── BÚSQUEDA EN DB LOCAL ──────────────────────────────────────────────────────
DB_PATH = Path.home() / 'Documents' / '2. Inmobiliaria' / 'zonaprop_scraper' / 'propiedades.db'

def _parse_amb_min(val):
    """Extrae el mínimo de un campo AMB. '3' -> 3, '2-3' -> 2, '3+' -> 3."""
    s = str(val or '').strip()
    m = re.search(r'\d+', s)
    return int(m.group()) if m else None

def buscar_opciones_para_lead(tipo, barrios, amb, hasta_usd, offset=0, solo_credito=False):
    """
    Busca en propiedades.db activos que matcheen el perfil del lead.
    Retorna lista de dicts ordenada por barrio de prioridad, luego precio asc.
    """
    import sqlite3 as _sqlite3

    amb_n    = _parse_amb_min(amb)
    precio_n = _parse_usd(hasta_usd)
    barrios_l = [b.strip() for b in str(barrios or '').replace(';',',').split(',') if b.strip()]

    if not barrios_l:
        return []

    barrio_orden = {b.lower(): i for i, b in enumerate(barrios_l)}
    placeholders = ','.join('?' for _ in barrios_l)
    params = [b.lower() for b in barrios_l]

    wheres = [f'LOWER(barrio) IN ({placeholders})']
    if tipo:
        wheres.append('LOWER(tipo_propiedad) = LOWER(?)')
        params.append(tipo)
    if amb_n is not None:
        wheres.append('ambientes = ?')
        params.append(amb_n)
    if precio_n:
        wheres.append('precio <= ?')
        params.append(precio_n)
    wheres.append("estado_aviso = 'activo'")
    wheres.append("operacion = 'venta'")
    if solo_credito:
        wheres.append("(LOWER(tags) LIKE '%apto cr%' OR LOWER(descripcion) LIKE '%apto cr%')")

    sql = (
        'SELECT url, direccion, barrio, tipo_propiedad, ambientes, '
        'precio, moneda_precio, sup_cubierta, expensas, moneda_expensas, '
        'cochera, fecha_detectado, fecha_publicacion_portal '
        f'FROM propiedades WHERE {" AND ".join(wheres)} '
        f'ORDER BY precio DESC, id DESC LIMIT 50 OFFSET {offset}'
    )

    try:
        con = _sqlite3.connect(str(DB_PATH))
        con.row_factory = _sqlite3.Row
        rows = con.execute(sql, params).fetchall()
        con.close()
    except Exception as e:
        raise RuntimeError(f'Error DB: {e}')

    today = _date.today()
    results = []
    for r in rows:
        barrio_key = (r['barrio'] or '').strip().lower()
        pri = barrio_orden.get(barrio_key, 99)

        fecha_s = r['fecha_publicacion_portal'] or r['fecha_detectado'] or ''
        try:
            fecha_d = _datetime.fromisoformat(fecha_s[:10]).date()
            dias = (today - fecha_d).days
        except Exception:
            dias = None

        precio_fmt = ''
        if r['precio']:
            moneda = r['moneda_precio'] or 'USD'
            precio_fmt = f"{moneda} {int(r['precio']):,}".replace(',', '.')

        exp_fmt = ''
        if r['expensas']:
            m_exp = r['moneda_expensas'] or '$'
            exp_fmt = f"{m_exp} {int(r['expensas']):,}".replace(',', '.')

        results.append({
            'barrio_pri': pri,
            'barrio':     r['barrio'] or '',
            'url':        r['url'] or '',
            'direccion':  r['direccion'] or '',
            'tipo':       r['tipo_propiedad'] or '',
            'amb':        r['ambientes'],
            'sup':        int(r['sup_cubierta']) if r['sup_cubierta'] else None,
            'precio':     precio_fmt,
            'precio_raw': int(r['precio']) if r['precio'] else 0,
            'expensas':   exp_fmt,
            'cochera':    bool(r['cochera']),
            'dias':       dias,
        })

    results.sort(key=lambda x: (x['barrio_pri'], -(x.get('precio_raw') or 0)))
    return results


# ─── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
SHEET_ID      = '1LEBztjtgGCj0PzpRnpcZezQaM0rmdycHVCHr4aZTjmw'
CREDS_PATH    = Path.home() / 'Documents' / '2. Inmobiliaria' / 'zonaprop_scraper' / 'google_credentials.json'
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


# ─── LEADS ─────────────────────────────────────────────────────────────────────

_LEADS_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{--primary:#003153;--orange:#E8630A;--bg:#f0f2f5;--white:#fff;--muted:#6b7280;--border:#dde1e7;--red:#dc2626;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:#111;min-height:100vh;}
nav{background:var(--primary);padding:0 28px;height:54px;display:flex;align-items:center;justify-content:space-between;}
.brand{color:#fff;font-weight:600;font-size:14px;letter-spacing:.04em;}
.nav-links{display:flex;align-items:center;gap:16px;}
.nav-link{color:rgba(255,255,255,.7);font-size:13px;font-weight:500;text-decoration:none;}
.nav-link:hover{color:#fff;}
.nav-link.active{color:var(--orange);}
.nav-badge{background:var(--orange);color:#fff;font-size:10px;font-weight:600;padding:3px 9px;border-radius:20px;letter-spacing:.06em;text-transform:uppercase;}
main{max-width:1500px;margin:36px auto;padding:0 20px;}
.page-hdr{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px;}
h1{font-size:22px;font-weight:600;color:var(--primary);}
.subtitle{color:var(--muted);font-size:13px;margin-top:4px;}
.refresh-btn{color:var(--primary);font-size:13px;font-weight:500;text-decoration:none;padding:8px 14px;border:1.5px solid var(--border);border-radius:8px;background:#fff;white-space:nowrap;}
.refresh-btn:hover{background:var(--bg);}
.filters-bar{display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;}
.filter-sel{border:1.5px solid var(--border);border-radius:8px;padding:7px 12px;font-size:13px;font-family:'DM Sans',sans-serif;background:#fff;color:#111;outline:none;cursor:pointer;transition:border-color .15s;}
.filter-sel:focus{border-color:var(--primary);}
.filter-sep{width:1px;height:24px;background:var(--border);flex-shrink:0;}
.sort-btn{display:inline-flex;align-items:center;gap:5px;border:1.5px solid var(--border);border-radius:8px;padding:7px 12px;font-size:13px;font-family:'DM Sans',sans-serif;background:#fff;color:#111;cursor:pointer;transition:border-color .15s;white-space:nowrap;}
.sort-btn:hover{border-color:var(--primary);}
.sort-btn.active{border-color:var(--primary);color:var(--primary);font-weight:600;}
.filter-count{margin-left:auto;font-size:12px;color:var(--muted);}
.table-wrap{background:var(--white);border-radius:12px;box-shadow:0 1px 6px rgba(0,0,0,.07);overflow-x:auto;}
table{width:100%;border-collapse:collapse;}
.leads-tbl{min-width:1100px;}
thead th{background:var(--primary);color:#fff;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;padding:12px 14px;text-align:left;white-space:nowrap;}
thead th:first-child{border-radius:12px 0 0 0;}
thead th:last-child{border-radius:0 12px 0 0;text-align:center;}
tbody tr{border-bottom:1px solid var(--border);}
tbody tr:last-child{border-bottom:none;}
tbody tr:hover{background:#f8fafc;}
tbody tr.hidden{display:none;}
td{padding:11px 14px;font-size:13px;vertical-align:top;}
.td-nombre{font-weight:600;white-space:nowrap;vertical-align:middle;}
.tc-c{text-align:center;vertical-align:middle;}
.tc-r{text-align:right;font-family:'DM Mono',monospace;font-size:12px;vertical-align:middle;}
.tc-m{color:var(--muted);font-size:12px;vertical-align:middle;}
.tc-red{color:var(--red);vertical-align:middle;}
.tc-org{color:var(--orange);vertical-align:middle;}
.td-wrap{white-space:normal;min-width:160px;max-width:260px;word-break:break-word;line-height:1.45;font-size:12px;}
.seg-b{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap;border:1px solid transparent;display:inline-block;}
.fichas-cell{text-align:center;vertical-align:middle;}
.fichas-toggle{display:inline-flex;align-items:center;gap:5px;background:var(--primary);color:#fff;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;cursor:pointer;border:none;transition:background .15s;}
.fichas-toggle:hover{background:#00243d;}
.fichas-toggle .arr{font-size:9px;transition:transform .2s;}
.fichas-toggle.open .arr{transform:rotate(180deg);}
.fichas-drop{display:none;margin-top:6px;text-align:left;}
.fichas-drop.open{display:block;}
.ficha-item{padding:5px 0;border-bottom:1px solid var(--border);font-size:12px;line-height:1.5;}
.ficha-item:last-child{border-bottom:none;}
.ficha-item a{color:var(--orange);text-decoration:none;font-weight:500;}
.ficha-item a:hover{text-decoration:underline;}
.fichas-empty{display:inline-block;color:var(--muted);font-size:12px;}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:500;align-items:flex-start;justify-content:center;padding:40px 20px;overflow-y:auto;}
.modal-overlay.open{display:flex;}
.modal{background:#fff;border-radius:14px;width:100%;max-width:900px;box-shadow:0 8px 40px rgba(0,0,0,.22);overflow:hidden;}
.modal-hdr{background:var(--primary);padding:18px 24px;display:flex;align-items:center;justify-content:space-between;}
.modal-hdr h2{color:#fff;font-size:16px;font-weight:600;}
.modal-hdr .modal-sub{color:rgba(255,255,255,.55);font-size:12px;margin-top:2px;}
.modal-close{background:none;border:none;color:rgba(255,255,255,.7);font-size:22px;cursor:pointer;line-height:1;padding:0;}
.modal-close:hover{color:#fff;}
.modal-body{padding:20px 24px;max-height:70vh;overflow-y:auto;}
.modal-loading{text-align:center;padding:40px;color:var(--muted);font-size:14px;}
.modal-empty{text-align:center;padding:40px;color:var(--muted);}
.modal-barrio-hdr{font-size:11px;font-weight:700;color:var(--primary);text-transform:uppercase;letter-spacing:.07em;padding:10px 0 6px;border-bottom:2px solid var(--primary);margin-bottom:8px;margin-top:16px;}
.modal-barrio-hdr:first-child{margin-top:0;}
.opt-card{border:1px solid var(--border);border-radius:8px;padding:12px 14px;margin-bottom:8px;display:grid;grid-template-columns:1fr auto;gap:6px;align-items:start;}
.opt-card:hover{border-color:var(--primary);background:#f8fafc;}
.opt-dir{font-weight:600;font-size:13px;color:#111;}
.opt-meta{font-size:12px;color:var(--muted);margin-top:2px;display:flex;flex-wrap:wrap;gap:6px;}
.opt-tag{background:#f0f4f8;color:#374151;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500;}
.opt-tag.coch{background:#ecfdf5;color:#065f46;}
.opt-precio{font-size:16px;font-weight:800;color:var(--primary);text-align:right;white-space:nowrap;}
.opt-exp{font-size:11px;color:var(--muted);text-align:right;}
.opt-dias{font-size:11px;margin-top:4px;text-align:right;}
.opt-dias.fresh{color:#15803d;} .opt-dias.mid{color:#a16207;} .opt-dias.old{color:var(--red);}
.opt-link{display:inline-block;margin-top:6px;font-size:12px;color:var(--orange);text-decoration:none;font-weight:500;}
.opt-link:hover{text-decoration:underline;}
.opt-tag-ficha{display:inline-block;margin-top:6px;font-size:12px;color:#fff;background:#15803d;padding:2px 10px;border-radius:12px;text-decoration:none;font-weight:600;}
.opt-tag-ficha:hover{background:#166534;}
.opt-card-done{background:#f0fdf4;border-color:#86efac;}
.opt-card-done .opt-dir{color:#15803d;}
.opt-baja{display:inline-block;margin-top:6px;font-size:11px;color:var(--red);background:none;border:1px solid var(--red);border-radius:6px;padding:2px 8px;cursor:pointer;font-family:inherit;font-weight:500;}
.opt-baja:hover{background:#fef2f2;}
.opt-baja:disabled{opacity:.4;cursor:default;}
.buscar-btn{display:inline-flex;align-items:center;gap:4px;background:none;border:1px solid var(--border);border-radius:6px;padding:3px 9px;font-size:11px;font-weight:600;color:var(--primary);cursor:pointer;transition:border-color .15s;white-space:nowrap;}
.buscar-btn:hover{border-color:var(--primary);background:#f0f4f8;}
.section-ov{margin-top:32px;}
.section-h{font-size:12px;font-weight:600;color:var(--primary);text-transform:uppercase;letter-spacing:.06em;margin-bottom:14px;}
.err-box{background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:24px;color:var(--red);margin-top:40px;}
.err-box h2{font-size:16px;margin-bottom:10px;}
.err-box pre{font-family:'DM Mono',monospace;font-size:12px;background:#fff;padding:12px;border-radius:6px;overflow-x:auto;color:#374151;margin-top:10px;}
/* MacBook Pro 14" */
@media screen and (max-width:1400px){
nav{padding:0 18px;height:48px;}
main{margin:24px auto;padding:0 14px;}
h1{font-size:19px;}
.page-hdr{margin-bottom:12px;}
.filters-bar{gap:7px;margin-bottom:10px;}
.filter-sel{font-size:12px;padding:6px 10px;}
.sort-btn{font-size:12px;padding:6px 10px;}
thead th{padding:9px 10px;font-size:10px;}
td{padding:8px 10px;font-size:12px;}
.td-wrap{max-width:200px;}
.seg-b{font-size:10px;padding:2px 8px;}
.modal{max-width:800px;}
.modal-hdr{padding:14px 18px;}
.modal-body{padding:14px 18px;}
}
@media screen and (max-width:1100px){
.leads-tbl{min-width:900px;}
}
"""

def _leads_nav(active):
    fichas_cls = ' active' if active == 'fichas' else ''
    leads_cls  = ' active' if active == 'leads'  else ''
    acm_cls    = ' active' if active == 'acm'    else ''
    return (
        '<nav><span class="brand">NL · Generador de Fichas</span>'
        '<div class="nav-links">'
        f'<a href="/" class="nav-link{fichas_cls}">Fichas</a>'
        f'<a href="/leads" class="nav-link{leads_cls}">Leads</a>'
        f'<a href="/acm" class="nav-link{acm_cls}">ACM</a>'
        '<span class="nav-badge">Internal Tool</span>'
        '</div></nav>'
    )

def _parse_fecha_lead(s):
    s = (s or '').strip()
    if not s:
        return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return _datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

_PRIORIDAD_ORD = {
    'VENDE PARA COMPRAR': 0,
    'CRÉDITO APROBADO':   1,
    'EFECTIVO':           2,
    'CRÉDITO EN TRÁMITE': 3,
    'INVERSIÓN/MIRANDO':  4,
}

def _prioridad_n(row):
    p = str(row.get('PRIORIDAD', '')).strip().upper()
    # normalizar tildes para mayor robustez
    p = p.replace('CREDITO', 'CRÉDITO').replace('TRAMITE', 'TRÁMITE').replace('INVERSION', 'INVERSIÓN')
    return _PRIORIDAD_ORD.get(p, 9)


_PRIORIDAD_STYLE = {
    'VENDE PARA COMPRAR': ('#fef2f2', '#dc2626'),
    'CRÉDITO APROBADO':   ('#fff7ed', '#c2410c'),
    'EFECTIVO':           ('#fefce8', '#a16207'),
    'CRÉDITO EN TRÁMITE': ('#f3f4f6', '#6b7280'),
    'INVERSIÓN/MIRANDO':  ('#f3f4f6', '#6b7280'),
}

def _badge_prioridad(pri):
    pri_key = str(pri).strip().upper()
    pri_key = pri_key.replace('CREDITO', 'CRÉDITO').replace('TRAMITE', 'TRÁMITE').replace('INVERSION', 'INVERSIÓN')
    bg, fg = _PRIORIDAD_STYLE.get(pri_key, ('#f3f4f6', '#374151'))
    label  = pri if pri else '—'
    return (
        f'<span class="seg-b" style="background:{bg};color:{fg};border-color:{fg}44">'
        f'{_html_esc.escape(label)}</span>'
    )

def _cell_followup(s):
    prox  = _parse_fecha_lead(s)
    today = _date.today()
    val   = _html_esc.escape(s) if s else '—'
    if prox is None:
        return f'<td class="tc-m">{val}</td>'
    if prox < today:
        return f'<td class="tc-red"><b>{val}</b> ⚠</td>'
    if prox == today:
        return f'<td class="tc-org"><b>{val}</b> ●</td>'
    return f'<td>{val}</td>'

def _parse_usd(s):
    try:
        return int(re.sub(r'[^0-9]', '', str(s or '')))
    except (ValueError, TypeError):
        return None

def _find_overlaps(leads):
    n = len(leads)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    def barrios_of(r):
        return {b.strip() for b in (r.get('BARRIOS') or '').replace(';', ',').split(',') if b.strip()}

    for i in range(n):
        for j in range(i + 1, n):
            a, b = leads[i], leads[j]
            tipo_a = (a.get('TIPO') or '').strip().upper()
            tipo_b = (b.get('TIPO') or '').strip().upper()
            if not tipo_a or tipo_a != tipo_b:
                continue
            amb_a = str(a.get('AMB') or '').strip()
            amb_b = str(b.get('AMB') or '').strip()
            if not amb_a or amb_a != amb_b:
                continue
            if not (barrios_of(a) & barrios_of(b)):
                continue
            p_a = _parse_usd(a.get('HASTA USD', ''))
            p_b = _parse_usd(b.get('HASTA USD', ''))
            if p_a and p_b and abs(p_a - p_b) > 20000:
                continue
            union(i, j)

    from collections import defaultdict as _dd
    groups = _dd(list)
    for i in range(n):
        groups[find(i)].append(i)

    results = []
    for root, indices in groups.items():
        if len(indices) < 2:
            continue
        gl = [leads[i] for i in indices]

        all_barrios = set()
        for lead in gl:
            for b in (lead.get('BARRIOS') or '').replace(';', ',').split(','):
                b = b.strip()
                if b:
                    all_barrios.add(b)

        prices = [p for p in (_parse_usd(l.get('HASTA USD', '')) for l in gl) if p]
        if prices:
            p_min, p_max = min(prices), max(prices)
            p_str = 'USD ' + f'{p_min:,}'.replace(',', '.')
            if p_min != p_max:
                p_str += ' – ' + f'{p_max:,}'.replace(',', '.')
        else:
            p_str = '—'

        results.append({
            'tipo':    gl[0].get('TIPO', ''),
            'barrios': sorted(all_barrios),
            'amb':     str(gl[0].get('AMB', '')),
            'precio':  p_str,
            'nombres': [l.get('NOMBRE', '') for l in gl],
        })

    return results

def leer_leads_data():
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SHEETS_SCOPES)
    gc    = gspread.authorize(creds)
    sh    = gc.open_by_key(SHEET_ID)
    # numericise_ignore=['all'] evita que "200.000" se convierta a float 200.0
    kw = dict(numericise_ignore=['all'])
    return sh.worksheet('Leads').get_all_records(**kw), sh.worksheet('Fichas').get_all_records(**kw)

def _render_leads_html(leads, fichas):
    # Sort default: prioridad asc, luego fecha ingreso asc (más antiguo primero)
    def _default_sort(row):
        pri_n = _prioridad_n(row)
        fecha = _parse_fecha_lead(row.get('FECHA', '')) or _date.max
        return (pri_n, fecha)

    sorted_leads = sorted(leads, key=_default_sort)

    # Mapear fichas por cliente (nombre lower → lista de {dir, link_og})
    fichas_map = {}
    for f in fichas:
        clientes_raw = str(f.get('CLIENTE', '')).strip()
        if not clientes_raw:
            continue
        for cliente in clientes_raw.replace(';', ',').split(','):
            key = cliente.strip().lower()
            if not key:
                continue
            if key not in fichas_map:
                fichas_map[key] = []
            fichas_map[key].append({
                'dir':     str(f.get('DIRECCIÓN', f.get('DIRECCION', ''))).strip(),
                'link_og': str(f.get('LINK OG', '')).strip(),
            })

    # Valores únicos para dropdowns
    prioridades_vals = ['VENDE PARA COMPRAR','CRÉDITO APROBADO','EFECTIVO','CRÉDITO EN TRÁMITE','INVERSIÓN/MIRANDO']
    tipos_set = sorted({str(r.get('TIPO','')).strip() for r in leads if str(r.get('TIPO','')).strip()})
    lc_set    = sorted({str(r.get('LAST CONTACT','')).strip() for r in leads if str(r.get('LAST CONTACT','')).strip()})

    def _opts(vals, label):
        opts = f'<option value="">Todos — {label}</option>'
        for v in vals:
            opts += f'<option value="{_html_esc.escape(v)}">{_html_esc.escape(v)}</option>'
        return opts

    filters_html = (
        '<div class="filters-bar">'
        f'<select class="filter-sel" id="f-prioridad" onchange="applyFilters()">'
        f'{_opts(prioridades_vals, "Prioridad")}</select>'
        f'<select class="filter-sel" id="f-tipo" onchange="applyFilters()">'
        f'{_opts(tipos_set, "Tipo")}</select>'
        f'<select class="filter-sel" id="f-lc" onchange="applyFilters()">'
        f'{_opts(lc_set, "Last Contact")}</select>'
        '<div class="filter-sep"></div>'
        '<button class="sort-btn active" id="btn-asc" onclick="setSortDir(\'asc\')">↑ Más antiguos</button>'
        '<button class="sort-btn" id="btn-desc" onclick="setSortDir(\'desc\')">↓ Más recientes</button>'
        '<span class="filter-count" id="filter-count"></span>'
        '</div>'
    )

    rows = []
    for row in sorted_leads:
        nombre    = _html_esc.escape(str(row.get('NOMBRE', '')))
        pri       = str(row.get('PRIORIDAD', ''))
        tipo      = _html_esc.escape(str(row.get('TIPO', '')))
        barrios   = _html_esc.escape(str(row.get('BARRIOS', '')))
        amb       = _html_esc.escape(str(row.get('AMB', '')))
        _p_usd    = _parse_usd(row.get('HASTA USD', ''))
        hasta_usd = f'{_p_usd:,}'.replace(',', '.') if _p_usd else '—'
        lc        = _html_esc.escape(str(row.get('LAST CONTACT', '') or '—'))
        prox_raw  = str(row.get('PROX FOLLOWUP', ''))
        res_raw   = str(row.get('RESULTADO LAST CONTACT', '') or '')
        next_raw  = str(row.get('NEXT STEP', '') or '')
        fecha_raw = str(row.get('FECHA', '') or '')
        pri_n     = _prioridad_n(row)

        # Fichas del cliente — desplegable
        cliente_key    = str(row.get('NOMBRE', '')).strip().lower()
        fichas_cliente = fichas_map.get(cliente_key, [])
        if fichas_cliente:
            ficha_items = ''.join(
                '<div class="ficha-item">'
                + _html_esc.escape(f['dir'] or 'Sin dirección')
                + (f' — <a href="{_html_esc.escape(f["link_og"])}" target="_blank">Ver portal ↗</a>' if f['link_og'] else '')
                + '</div>'
                for f in fichas_cliente
            )
            fichas_cell = (
                '<div class="fichas-cell">'
                f'<button class="fichas-toggle" onclick="toggleFichas(this)">'
                f'{len(fichas_cliente)} <span class="arr">▼</span></button>'
                f'<div class="fichas-drop">{ficha_items}</div>'
                '</div>'
            )
        else:
            fichas_cell = '<span class="fichas-empty">—</span>'

        rows.append(
            f'<tr data-pri="{pri_n}" data-fecha="{_html_esc.escape(fecha_raw)}"'
            f' data-prioridad="{_html_esc.escape(pri)}"'
            f' data-tipo="{_html_esc.escape(str(row.get("TIPO","")).strip())}"'
            f' data-lc="{_html_esc.escape(str(row.get("LAST CONTACT","")).strip())}">'
            + f'<td class="td-nombre">'
            + f'{nombre} '
            + f'<button class="buscar-btn" onclick="abrirBuscar(this)"'
              f' data-nombre="{nombre}"'
              f' data-tipo="{tipo}"'
              f' data-barrios="{barrios}"'
              f' data-amb="{amb}"'
              f' data-usd="{hasta_usd}"'
              f' data-prioridad="{_html_esc.escape(pri)}">&#128269;</button></td>'
            + f'<td style="vertical-align:middle">{_badge_prioridad(pri)}</td>'
            + f'<td style="vertical-align:middle">{tipo}</td>'
            + f'<td style="vertical-align:middle">{barrios}</td>'
            + f'<td class="tc-c">{amb}</td>'
            + f'<td class="tc-r">{hasta_usd}</td>'
            + f'<td class="tc-m">{lc}</td>'
            + _cell_followup(prox_raw)
            + f'<td class="td-wrap">{_html_esc.escape(res_raw) or "—"}</td>'
            + f'<td class="td-wrap">{_html_esc.escape(next_raw) or "—"}</td>'
            + f'<td class="fichas-cell">{fichas_cell}</td>'
            + '</tr>'
        )

    overlaps = _find_overlaps(leads)
    if overlaps:
        ov_rows = []
        for g in overlaps:
            tipo_s     = _html_esc.escape(g['tipo'])
            barrios_s  = ', '.join(_html_esc.escape(b) for b in g['barrios'])
            amb_s      = _html_esc.escape(g['amb'])
            precio_s   = _html_esc.escape(g['precio'])
            clientes_s = ' · '.join(_html_esc.escape(nm) for nm in g['nombres'])
            ov_rows.append(
                '<tr>'
                + f'<td style="vertical-align:middle">{tipo_s}</td>'
                + f'<td style="vertical-align:middle">{barrios_s}</td>'
                + f'<td class="tc-c">{amb_s}</td>'
                + f'<td class="tc-r" style="vertical-align:middle">{precio_s}</td>'
                + f'<td style="font-weight:500;vertical-align:middle">{clientes_s}</td>'
                + '</tr>'
            )
        overlap_section = (
            '<section class="section-ov">'
            '<div class="section-h">Búsquedas similares</div>'
            '<div class="table-wrap">'
            '<table><thead><tr>'
            '<th>Tipo</th><th>Barrios</th><th style="text-align:center">Amb</th>'
            '<th style="text-align:right">Presupuesto</th><th>Clientes</th>'
            '</tr></thead>'
            '<tbody>' + '\n'.join(ov_rows) + '</tbody>'
            '</table></div>'
            '</section>'
        )
    else:
        overlap_section = ''

    updated_at = _datetime.now().strftime('%d/%m/%Y %H:%M')
    n = len(sorted_leads)

    js = (
        "var sortDir='asc';"
        "function applyFilters(){"
        "var fPri=document.getElementById('f-prioridad').value.toLowerCase();"
        "var fTipo=document.getElementById('f-tipo').value.toLowerCase();"
        "var fLc=document.getElementById('f-lc').value.toLowerCase();"
        "var rows=document.querySelectorAll('.leads-tbl tbody tr');"
        "var vis=0;"
        "rows.forEach(function(tr){"
        "var pri=(tr.dataset.prioridad||'').toLowerCase();"
        "var tipo=(tr.dataset.tipo||'').toLowerCase();"
        "var lc=(tr.dataset.lc||'').toLowerCase();"
        "var ok=(!fPri||pri===fPri)&&(!fTipo||tipo===fTipo)&&(!fLc||lc===fLc);"
        "tr.classList.toggle('hidden',!ok);"
        "if(ok)vis++;});"
        f"document.getElementById('filter-count').textContent=vis+' de {n} leads';}}"
        "function setSortDir(dir){"
        "sortDir=dir;"
        "document.getElementById('btn-asc').classList.toggle('active',dir==='asc');"
        "document.getElementById('btn-desc').classList.toggle('active',dir==='desc');"
        "var tbody=document.querySelector('.leads-tbl tbody');"
        "var rows=Array.from(tbody.querySelectorAll('tr'));"
        "rows.sort(function(a,b){"
        "var pa=parseInt(a.dataset.pri||9),pb=parseInt(b.dataset.pri||9);"
        "if(pa!==pb)return dir==='asc'?pa-pb:pb-pa;"
        "var fa=a.dataset.fecha||'',fb=b.dataset.fecha||'';"
        "if(fa<fb)return dir==='asc'?-1:1;"
        "if(fa>fb)return dir==='asc'?1:-1;"
        "return 0;});"
        "rows.forEach(function(r){tbody.appendChild(r);});}"
        "function toggleFichas(btn){"
        "btn.classList.toggle('open');"
        "btn.nextElementSibling.classList.toggle('open');}"
        "var _modalItems=[];"
        "var _modalPage=1;"
        "var _MODAL_PER_PAGE=10;"
        "var _modalOffset=0;"
        "var _modalParams={};"
        "var _fichasOG={};"
        "function _cargarFichasOG(cb){fetch('/fichas-generadas').then(function(r){return r.json();}).then(function(d){_fichasOG=d.links_nl||{};cb();}).catch(function(){_fichasOG={};cb();});}"
        "function abrirBuscar(btn){"
        "var n=btn.dataset.nombre,t=btn.dataset.tipo,b=btn.dataset.barrios,a=btn.dataset.amb,u=btn.dataset.usd,pr=(btn.dataset.prioridad||'').toUpperCase();var sc=pr.indexOf('CRÉDITO')!==-1||pr.indexOf('CREDITO')!==-1;"
        "_modalParams={tipo:t,barrios:b,amb:a,hasta_usd:u,solo_credito:sc};"
        "_modalOffset=0;"
        "document.getElementById('modal-titulo').textContent='Opciones para '+n;"
        "document.getElementById('modal-sub').textContent=t+' · '+a+' amb · hasta USD '+u+' · '+b;"
        "document.getElementById('modal-body').innerHTML='<div class=\"modal-loading\">Buscando...</div>';"
        "document.getElementById('modal-overlay').classList.add('open');"
        "_cargarFichasOG(function(){_fetchOpciones(0,true);});}"
        "function _fetchOpciones(offset,reset){"
        "var p=Object.assign({},_modalParams,{offset:offset});"
        "fetch('/buscar-opciones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(reset){_modalItems=d||[];_modalPage=1;_modalOffset=50;"
        "if(!_modalItems.length){document.getElementById('modal-body').innerHTML='<div class=\"modal-empty\">Sin resultados para este perfil.</div>';return;}"
        "_renderModalPage();}else{"
        "if(!d||!d.length){"
        "var ag=document.createElement('div');"
        "ag.style.cssText='text-align:center;padding:20px;border-top:1px solid var(--border);margin-top:8px';"
        "ag.innerHTML='<p style=\"font-size:13px;color:var(--muted);margin-bottom:10px\">Ya revisaste todas las opciones disponibles.</p>'"
        "+'<button onclick=\"_fetchOpciones(0,true)\" style=\"font-family:inherit;font-size:12px;padding:6px 16px;border:1.5px solid var(--primary);border-radius:6px;background:#fff;color:var(--primary);cursor:pointer;font-weight:600\">↻ Reiniciar búsqueda</button>';"
        "document.getElementById('modal-body').appendChild(ag);return;}"
        "_modalItems=_modalItems.concat(d);"
        "_modalOffset=offset+50;"
        "_renderModalPage();}})"
        ".catch(function(){document.getElementById('modal-body').innerHTML='<div class=\"modal-empty\">Error al buscar.</div>';});}"
        "function cerrarModal(e){"
        "if(!e||e.target===document.getElementById('modal-overlay'))"
        "document.getElementById('modal-overlay').classList.remove('open');}"
        "function _renderModalPage(){"
        "var body=document.getElementById('modal-body');"
        "var total=_modalItems.length;"
        "var pages=Math.ceil(total/_MODAL_PER_PAGE);"
        "var start=(_modalPage-1)*_MODAL_PER_PAGE;"
        "var page=_modalItems.slice(start,start+_MODAL_PER_PAGE);"
        "var html='',last=null;"
        "page.forEach(function(p){"
        "if(p.barrio!==last){html+='<div class=\"modal-barrio-hdr\">'+p.barrio+'</div>';last=p.barrio;}"
        "var dc=p.dias===null?'':p.dias<=30?'fresh':p.dias<=90?'mid':'old';"
        "var dt=p.dias===null?'':'Publicado hace '+p.dias+' días';"
        "var tags='<span class=\"opt-tag\">'+p.tipo+'</span>';"
        "if(p.amb)tags+='<span class=\"opt-tag\">'+p.amb+' amb</span>';"
        "if(p.sup)tags+='<span class=\"opt-tag\">'+p.sup+' m²</span>';"
        "if(p.cochera)tags+='<span class=\"opt-tag coch\">Cochera</span>';"
        "var fichaLink=_fichasOG[p.url]||'';"
        "var fichaTag=fichaLink?'<a class=\"opt-tag-ficha\" href=\"'+fichaLink+'\" target=\"_blank\">✔ Ficha generada ↗</a>':'';"
        "var lnk=p.url?'<a class=\"opt-link\" href=\"'+p.url+'\" target=\"_blank\">Ver portal ↗</a>':'';"
        "var exp=p.expensas?'<div class=\"opt-exp\">Expensas: '+p.expensas+'</div>':'';"
        "var dd=dt?'<div class=\"opt-dias '+dc+'\">'+ dt+'</div>':'';"
        "var bajaBtn=p.url?'<button class=\"opt-baja\" data-url=\"'+p.url+'\" onclick=\"_darDeBaja(this)\">Dar de baja</button>':'';"
        "html+='<div class=\"opt-card'+(fichaLink?' opt-card-done':'')+'\">';"
        "html+='<div><div class=\"opt-dir\">'+p.direccion+'</div>';"
        "html+='<div class=\"opt-meta\">'+tags+'</div>'+dd+lnk+fichaTag+'</div>';"
        "html+='<div><div class=\"opt-precio\">'+p.precio+'</div>'+exp+bajaBtn+'</div>';"
        "html+='</div>';"
        "});"
        "html+='<div style=\"display:flex;align-items:center;justify-content:space-between;padding:12px 0 4px;border-top:1px solid var(--border);margin-top:8px\">';"
        "html+='<button onclick=\"_modalGoPage(_modalPage-1)\" '+((_modalPage===1)?'disabled':'')+' style=\"font-family:inherit;font-size:12px;padding:5px 12px;border:1.5px solid var(--border);border-radius:6px;background:#fff;cursor:pointer\">&#8592; Ant</button>';"
        "html+='<span style=\"font-size:12px;color:var(--muted)\">'+_modalPage+' / '+pages+' &nbsp;('+total+' cargados)</span>';"
        "html+='<button onclick=\"_modalGoPage(_modalPage+1)\" '+((_modalPage===pages)?'disabled':'')+' style=\"font-family:inherit;font-size:12px;padding:5px 12px;border:1.5px solid var(--border);border-radius:6px;background:#fff;cursor:pointer\">Sig &#8594;</button>';"
        "html+='</div>';"
        "if(_modalPage===pages){"
        "html+='<div style=\"text-align:center;padding:10px 0 2px\">';"
        "html+='<button onclick=\"_fetchOpciones(_modalOffset,false)\" style=\"font-family:inherit;font-size:12px;padding:6px 16px;border:1.5px solid var(--primary);border-radius:6px;background:#fff;color:var(--primary);cursor:pointer;font-weight:600\">Ver 50 más</button>';"
        "if(_modalOffset>50)html+=' <button onclick=\"_modalPage=1;_renderModalPage()\" style=\"font-family:inherit;font-size:12px;padding:6px 16px;border:1.5px solid var(--border);border-radius:6px;background:#fff;color:var(--muted);cursor:pointer\">&#8593; Volver al inicio</button>';"
        "html+='</div>';"
        "}"
        "body.innerHTML=html;}"
        "function _modalGoPage(p){"
        "var pages=Math.ceil(_modalItems.length/_MODAL_PER_PAGE);"
        "if(p<1||p>pages)return;"
        "_modalPage=p;"
        "_renderModalPage();"
        "document.getElementById('modal-body').scrollTop=0;}"
        "function _darDeBaja(btn){"
        "var url=btn.dataset.url;"
        "if(!confirm('\u00bfMarcar esta propiedad como bajada?'))return;"
        "btn.disabled=true;btn.textContent='Bajando...';"
        "fetch('/marcar-bajado',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url})})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){btn.textContent='✓ Bajada';btn.style.color='var(--muted)';btn.style.borderColor='var(--muted)';"
        "btn.closest('.opt-card').style.opacity='0.45';}"
        "else{btn.disabled=false;btn.textContent='Dar de baja';alert('Error: '+d.error);}})"
        ".catch(function(){btn.disabled=false;btn.textContent='Dar de baja';});}"
        "var s=300,cd=document.getElementById('cd');"
        "setInterval(function(){if(--s<=0)return;"
        "var m=Math.floor(s/60),ss=String(s%60).padStart(2,'0');"
        "cd.textContent='auto-refresh en '+m+':'+ss;},1000);"
        "applyFilters();"
    )

    return (
        '<!DOCTYPE html><html lang="es"><head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="300">'
        '<title>Leads · NL</title>'
        '<style>' + _LEADS_CSS + '</style>'
        '</head><body>'
        + _leads_nav('leads') +
        '<main>'
        '<div class="page-hdr">'
        f'<div><h1>CRM Leads <span style="font-size:15px;font-weight:400;color:var(--muted)">({n})</span></h1>'
        f'<div class="subtitle">Actualizado {updated_at}'
        f' &nbsp;·&nbsp; <span id="cd">auto-refresh en 5:00</span></div></div>'
        '<a href="/leads" class="refresh-btn">↺ Refrescar</a>'
        '</div>'
        + filters_html +
        '<div class="table-wrap"><table class="leads-tbl">'
        '<thead><tr>'
        '<th>Nombre</th><th>Prioridad</th><th>Tipo</th><th>Barrios</th>'
        '<th>Amb</th><th>Hasta USD</th><th>Last Contact</th><th>Prox Followup</th>'
        '<th>Resultado</th><th>Next Step</th><th>Fichas</th>'
        '</tr></thead>'
        '<tbody>' + '\n'.join(rows) + '</tbody>'
        '</table></div>'
        + overlap_section +
        '</main>'

        '<div class="modal-overlay" id="modal-overlay" onclick="cerrarModal(event)">'
        '<div class="modal" onclick="event.stopPropagation()">'
        '<div class="modal-hdr">'
        '<div><h2 id="modal-titulo">Opciones para cliente</h2>'
        '<div class="modal-sub" id="modal-sub"></div></div>'
        '<button class="modal-close" onclick="cerrarModal()">&#x2715;</button>'
        '</div>'
        '<div class="modal-body" id="modal-body">'
        '<div class="modal-loading">Buscando...</div>'
        '</div></div></div>'

        '<script>' + js + '</script>'
        '</body></html>'
    )

def _render_leads_error(msg):
    return (
        '<!DOCTYPE html><html lang="es"><head>'
        '<meta charset="UTF-8"><title>Error · Leads</title>'
        '<style>' + _LEADS_CSS + '</style>'
        '</head><body>'
        + _leads_nav('leads') +
        '<main><div class="err-box">'
        '<h2>⚠ Error al conectar con Google Sheets</h2>'
        f'<pre>{_html_esc.escape(msg)}</pre>'
        '<p style="margin-top:14px">'
        '<a href="/leads" style="color:var(--red);font-weight:500">↺ Reintentar</a>'
        '</p></div></main></body></html>'
    )


# ─── ROUTES ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/leads')
def leads():
    try:
        leads_data, fichas_data = leer_leads_data()
    except Exception as e:
        return _render_leads_error(str(e)), 500
    return _render_leads_html(leads_data, fichas_data)



@app.route('/marcar-bajado', methods=['POST'])
def marcar_bajado_leads():
    import sqlite3 as _sq3
    from datetime import datetime as _dt2
    data = request.get_json()
    url  = (data or {}).get('url', '').strip()
    if not url:
        return jsonify({'ok': False, 'error': 'Sin URL'}), 400
    try:
        con = _sq3.connect(str(DB_PATH))
        con.execute(
            "UPDATE propiedades SET estado_aviso='bajado', fecha_bajada=? WHERE url=?",
            (_dt2.now().isoformat(), url)
        )
        con.commit()
        con.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/buscar-opciones', methods=['POST'])
def buscar_opciones():
    d            = request.get_json()
    tipo         = d.get('tipo', '').strip()
    barrios      = d.get('barrios', '').strip()
    amb          = d.get('amb', '').strip()
    hasta_usd    = d.get('hasta_usd', '').strip()
    offset       = int(d.get('offset', 0))
    solo_credito = bool(d.get('solo_credito', False))
    try:
        results = buscar_opciones_para_lead(tipo, barrios, amb, hasta_usd, offset, solo_credito)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/fichas-generadas', methods=['GET'])
def fichas_generadas():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SHEETS_SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet('Fichas')
        records = ws.get_all_records(numericise_ignore=['all'])
        links_nl = {str(r.get('LINK OG', '')).strip(): str(r.get('LINK NL', '')).strip()
                    for r in records if str(r.get('LINK OG', '')).strip()}
        return jsonify({'links_nl': links_nl})
    except Exception as e:
        return jsonify({'links_nl': {}, 'error': str(e)})


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
        from generate_template import TEMPLATE as TPL
    except ImportError:
        return jsonify({'error': 'No se encontró generate_template.py. Asegurate de tenerlo en la misma carpeta.'}), 500

    # Generar HTML
    html = _render(d, fotos, TPL)
    out_path.write_text(html, encoding='utf-8')

    # Git push
    try:
        git_push(REPO_PATH, f'ficha: {out_path.name}')
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Error en git push: {e.stderr.decode() if e.stderr else str(e)}'}), 500

    url_publica = f'{GITHUB_BASE}/fichas/{out_path.name}'
    url_sheets  = f'https://nahuelim.com.ar/fichas/{out_path.name}'
    ficha_id = hashlib.md5(nombre_base.encode()).hexdigest()[:5]
    agregar_ficha_a_sheets(d, url_sheets, d.get('url_original', ''), ficha_id)
    return jsonify({'url': url_publica, 'archivo': out_path.name})


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

    return TPL.format(
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
        thumbs=thumbs,
        photos_json=photos_json,
        direccion=direccion,
        barrio=barrio,
    )



# ═══════════════════════════════════════════════════════════════════════════════
# PATCH ACM v2 — reemplaza las rutas ACM en auto_ficha.py
#
# Cómo aplicar:
#   1. Abrí auto_ficha.py en VS Code
#   2. Buscá la línea:  # ─── ACM ──────────
#   3. Seleccioná todo desde esa línea hasta el final del archivo
#   4. Reemplazá con este bloque completo
#   5. Guardá
# ═══════════════════════════════════════════════════════════════════════════════

# ─── ACM ───────────────────────────────────────────────────────────────────────

_ACM_BARRIOS = [
    "Agronomía", "Almagro", "Balvanera", "Barracas", "Belgrano",
    "Boedo", "Caballito", "Chacarita", "Coghlan", "Colegiales",
    "Constitución", "Flores", "Floresta", "La Boca", "La Paternal",
    "Liniers", "Mataderos", "Monte Castro", "Monserrat", "Nueva Pompeya",
    "Núñez", "Palermo", "Parque Avellaneda", "Parque Chacabuco",
    "Parque Chas", "Parque Patricios", "Puerto Madero", "Recoleta",
    "Retiro", "Saavedra", "San Cristóbal", "San Nicolás", "San Telmo",
    "Vélez Sársfield", "Versalles", "Villa Crespo", "Villa del Parque",
    "Villa Devoto", "Villa General Mitre", "Villa Lugano", "Villa Luro",
    "Villa Ortúzar", "Villa Pueyrredón", "Villa Real", "Villa Riachuelo",
    "Villa Santa Rita", "Villa Soldati", "Villa Urquiza", "Barrio Norte",
    "Las Cañitas", "Palermo Soho", "Palermo Hollywood",
]

_SCRAPER_ACM = Path(__file__).parent / 'acm_scraper.py'
_PYTHON_VENV = (
    Path.home() / 'Documents' / '2. Inmobiliaria' / 'zonaprop_scraper'
    / 'venv' / 'bin' / 'python3.11'
)

_ACM_ESTADO_COEFS = {
    'a_estrenar':             0.15,
    'impecable':              0.08,
    'buen_estado':            0.00,
    'a_refaccionar':         -0.10,
    'necesita_restauracion': -0.20,
}
_ACM_ESTADO_LABELS = {
    'a_estrenar':            'A estrenar / En pozo',
    'impecable':             'Impecable',
    'buen_estado':           'Buen estado',
    'a_refaccionar':         'A refaccionar',
    'necesita_restauracion': 'Necesita restauración',
}

_ACM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{--primary:#003153;--orange:#E8630A;--bg:#f0f2f5;--white:#fff;--muted:#6b7280;--border:#dde1e7;--red:#dc2626;--green:#16a34a;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:#111;min-height:100vh;}
nav{background:var(--primary);padding:0 28px;height:54px;display:flex;align-items:center;justify-content:space-between;}
.brand{color:#fff;font-weight:600;font-size:14px;letter-spacing:.04em;}
.nav-links{display:flex;align-items:center;gap:16px;}
.nav-link{color:rgba(255,255,255,.7);font-size:13px;font-weight:500;text-decoration:none;}
.nav-link:hover{color:#fff;}
.nav-link.active{color:var(--orange);}
.nav-badge{background:var(--orange);color:#fff;font-size:10px;font-weight:600;padding:3px 9px;border-radius:20px;letter-spacing:.06em;text-transform:uppercase;}
main{max-width:980px;margin:36px auto;padding:0 20px;}
h1{font-size:22px;font-weight:600;color:var(--primary);margin-bottom:4px;}
.subtitle{color:var(--muted);font-size:14px;margin-bottom:28px;}
.card{background:var(--white);border-radius:12px;padding:24px;box-shadow:0 1px 6px rgba(0,0,0,.07);margin-bottom:20px;}
label{display:block;font-size:12px;font-weight:600;color:var(--primary);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;}
input[type=text],input[type=number],select,textarea{width:100%;border:1.5px solid var(--border);border-radius:8px;padding:10px 14px;font-size:14px;font-family:'DM Sans',sans-serif;outline:none;transition:border-color .15s;background:#fff;}
input:focus,select:focus,textarea:focus{border-color:var(--primary);}
textarea{resize:vertical;min-height:60px;font-family:'DM Mono',monospace;font-size:13px;}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.form-grid .full{grid-column:1/-1;}
.btn{display:inline-flex;align-items:center;gap:6px;padding:11px 22px;border-radius:8px;border:none;font-size:14px;font-weight:600;cursor:pointer;transition:opacity .15s,transform .1s;white-space:nowrap;font-family:'DM Sans',sans-serif;}
.btn:hover{opacity:.88;transform:translateY(-1px);}
.btn-orange{background:var(--orange);color:#fff;}
.btn-primary{background:var(--primary);color:#fff;}
.btn:disabled{opacity:.5;cursor:not-allowed;transform:none;}
.loader{display:inline-block;width:15px;height:15px;border:2.5px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}
.section-hdr{font-size:12px;font-weight:700;color:var(--primary);text-transform:uppercase;letter-spacing:.07em;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid var(--primary);}
.alert{padding:12px 16px;border-radius:8px;font-size:13px;margin-bottom:16px;}
.alert-info{background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;}
.alert-error{background:#fef2f2;color:var(--red);border:1px solid #fecaca;}
.alert-warn{background:#fffbeb;color:#92400e;border:1px solid #fde68a;}
.alert-success{background:#f0fdf4;color:var(--green);border:1px solid #bbf7d0;}
.metric-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;}
.metric-card{background:#f8fafc;border-radius:10px;padding:14px 16px;border:1px solid var(--border);}
.metric-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;}
.metric-value{font-size:19px;font-weight:700;color:var(--primary);}
.metric-value.orange{color:var(--orange);}
.metric-value.sm{font-size:14px;}
table.cand-tbl{width:100%;border-collapse:collapse;font-size:13px;}
.cand-tbl th{background:var(--primary);color:#fff;padding:9px 10px;font-size:11px;font-weight:600;text-align:left;text-transform:uppercase;letter-spacing:.04em;}
.cand-tbl td{padding:8px 10px;border-bottom:1px solid var(--border);vertical-align:middle;}
.cand-tbl tr:hover td{background:#f8fafc;}
.cand-tbl tr.confirmado td{background:#f0fdf4;}
.link-zp{color:var(--orange);font-weight:600;font-size:12px;text-decoration:none;}
.link-zp:hover{text-decoration:underline;}
.dias-badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;}
.dias-fresh{background:#dcfce7;color:#15803d;}
.dias-mid{background:#fef3c7;color:#92400e;}
.dias-old{background:#fee2e2;color:#b91c1c;}
.chk-cell{text-align:center;width:44px;}
input[type=checkbox]{width:18px;height:18px;cursor:pointer;accent-color:var(--orange);}
.score-bar{height:6px;border-radius:3px;background:var(--border);overflow:hidden;width:70px;display:inline-block;vertical-align:middle;}
.score-fill{height:100%;background:var(--orange);border-radius:3px;}
.price-adj-card{background:var(--white);border-radius:12px;padding:24px;box-shadow:0 1px 6px rgba(0,0,0,.07);border-left:4px solid var(--orange);}
.price-input-big{font-size:20px;font-weight:700;padding:14px 18px;border:2px solid var(--orange) !important;border-radius:8px;width:260px;color:var(--primary);}
@media(max-width:1400px){nav{padding:0 18px;height:48px;}main{margin:24px auto;}.metric-row{grid-template-columns:repeat(2,1fr);}}
"""


def _acm_fmt(n) -> str:
    if n is None:
        return '—'
    try:
        return f'USD {int(n):,}'.replace(',', '.')
    except (TypeError, ValueError):
        return '—'


def _acm_fmt_ars(n) -> str:
    if n is None:
        return '—'
    try:
        return f'$ {int(n):,}'.replace(',', '.')
    except (TypeError, ValueError):
        return '—'


def _acm_html_page(title: str, body: str) -> str:
    nav = _leads_nav('acm')
    return (
        '<!DOCTYPE html><html lang="es"><head>'
        '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{title} · ACM · NL</title>'
        '<style>' + _ACM_CSS + '</style>'
        '</head><body>' + nav + '<main>' + body + '</main></body></html>'
    )


# ── /acm — Formulario ─────────────────────────────────────────────────────────

@app.route('/acm')
def acm():
    import html as _he
    barrio_opts = ''.join(
        f'<option value="{_he.escape(b)}">{_he.escape(b)}</option>'
        for b in sorted(_ACM_BARRIOS)
    )
    body = f'''
<h1>Análisis Comparativo de Mercado</h1>
<p class="subtitle">
  Buscá en ZonaProp con los filtros que quieras, copiá la URL de resultados y pegala acá.
  El scraper analiza el universo completo y te trae los 24 mejores candidatos para que valides los 6 testigos.
</p>

<div class="alert alert-info">
  Al hacer clic en <b>Analizar</b> se abre una ventana del browser que navega ZonaProp automáticamente.
  Tarda entre 10 y 20 minutos según el volumen de resultados.
</div>

<div class="card">
  <div class="section-hdr">URL de búsqueda y datos del inmueble</div>
  <form id="acm-form" action="/acm/analizar" method="POST">
    <div class="form-grid">

      <div class="full">
        <label>URL de búsqueda de ZonaProp *</label>
        <textarea name="search_url" rows="2"
          placeholder="https://www.zonaprop.com.ar/departamentos-venta-palermo-2-ambientes.html"
          required style="font-size:13px"></textarea>
        <p style="font-size:11px;color:var(--muted);margin-top:5px">
          Filtrá en ZonaProp por barrio, tipo, ambientes, precio — lo que quieras. Copiá la URL y pegala acá.
        </p>
      </div>

      <div>
        <label>M² cubiertos del inmueble *</label>
        <input type="number" name="sup_cubierta" placeholder="Ej: 55" min="1" max="2000" required>
      </div>
      <div>
        <label>Ambientes</label>
        <input type="number" name="ambientes" placeholder="Ej: 2" min="1" max="10">
      </div>
      <div>
        <label>Antigüedad (años)</label>
        <input type="number" name="antiguedad" placeholder="Ej: 15" min="0" max="200">
      </div>
      <div>
        <label>Piso</label>
        <input type="number" name="piso" placeholder="Ej: 4" min="1" max="50">
      </div>
      <div>
        <label>Baños</label>
        <input type="number" name="banos" placeholder="Ej: 1" min="1" max="10">
      </div>
      <div>
        <label>Disposición</label>
        <select name="disposicion">
          <option value="">—</option>
          <option value="Frente">Frente</option>
          <option value="Contrafrente">Contrafrente</option>
          <option value="Interno">Interno</option>
          <option value="Lateral">Lateral</option>
        </select>
      </div>
      <div>
        <label>Cochera</label>
        <select name="cochera">
          <option value="false">No</option>
          <option value="true">Sí</option>
        </select>
      </div>
      <div>
        <label>M² semicubiertos</label>
        <input type="number" name="sup_semi" placeholder="Ej: 8" min="0" max="500" value="0">
      </div>
      <div>
        <label>Expensas est. ($)</label>
        <input type="number" name="expensas" placeholder="Ej: 45000" min="0">
      </div>
      <div>
        <label>Apto crédito</label>
        <select name="apto_credito">
          <option value="false">No</option>
          <option value="true">Sí</option>
        </select>
      </div>

      <!-- Datos para el informe (barrio + dirección + tipo + estado) -->
      <div>
        <label>Barrio del inmueble *</label>
        <select name="barrio" required>
          <option value="" disabled selected>Seleccioná</option>
          {barrio_opts}
        </select>
      </div>
      <div>
        <label>Tipo</label>
        <select name="tipo">
          <option value="Departamento">Departamento</option>
          <option value="PH">PH</option>
          <option value="Casa">Casa</option>
        </select>
      </div>
      <div class="full">
        <label>Dirección *</label>
        <input type="text" name="direccion" placeholder="Ej: Gurruchaga 1800, Piso 3 B" required>
      </div>
      <div class="full">
        <label>Estado del inmueble *</label>
        <select name="estado" required>
          <option value="a_estrenar">A estrenar / En pozo (+15%)</option>
          <option value="impecable">Impecable (+8%)</option>
          <option value="buen_estado" selected>Buen estado (sin ajuste)</option>
          <option value="a_refaccionar">A refaccionar (-10%)</option>
          <option value="necesita_restauracion">Necesita restauración (-20%)</option>
        </select>
      </div>

    </div>
    <div style="margin-top:20px;display:flex;align-items:center;gap:16px;">
      <button type="submit" class="btn btn-orange" id="acm-btn">
        <span id="acm-btn-txt">Analizar mercado</span>
        <span class="loader" id="acm-loader" style="display:none"></span>
      </button>
      <span style="font-size:13px;color:var(--muted)">
        El browser se abre automáticamente.<br>
        Tarda 10–20 min según el volumen.
      </span>
    </div>
  </form>
</div>

<script>
document.getElementById('acm-form').addEventListener('submit', function() {{
  var btn = document.getElementById('acm-btn');
  btn.disabled = true;
  document.getElementById('acm-btn-txt').textContent = 'Analizando...';
  document.getElementById('acm-loader').style.display = 'inline-block';
}});
</script>
'''
    return _acm_html_page('Formulario', body)


# ── /acm/analizar ─────────────────────────────────────────────────────────────

@app.route('/acm/analizar', methods=['POST'])
def acm_analizar():
    import html as _he

    search_url   = request.form.get('search_url', '').strip()
    sup_cubierta = request.form.get('sup_cubierta', '').strip()
    ambientes    = request.form.get('ambientes', '').strip()
    antiguedad   = request.form.get('antiguedad', '').strip()
    piso         = request.form.get('piso', '').strip()
    disposicion  = request.form.get('disposicion', '').strip()
    cochera      = request.form.get('cochera', 'false').strip()
    sup_semi     = request.form.get('sup_semi', '0').strip()
    expensas     = request.form.get('expensas', '').strip()
    apto_credito = request.form.get('apto_credito', 'false').strip()
    barrio       = request.form.get('barrio', '').strip()
    tipo         = request.form.get('tipo', 'Departamento').strip()
    direccion    = request.form.get('direccion', '').strip()
    estado_slug  = request.form.get('estado', 'buen_estado').strip()

    if not search_url or not search_url.startswith('http'):
        return _acm_html_page('Error', '<div class="alert alert-error">Pegá una URL válida de ZonaProp.</div>')
    if not sup_cubierta:
        return _acm_html_page('Error', '<div class="alert alert-error">Los m² cubiertos son obligatorios.</div>')
    if not _SCRAPER_ACM.exists():
        return _acm_html_page('Error', f'<div class="alert alert-error">No se encontró acm_scraper.py en {_SCRAPER_ACM}</div>')
    if not _PYTHON_VENV.exists():
        return _acm_html_page('Error', f'<div class="alert alert-error">No se encontró el venv en {_PYTHON_VENV}</div>')

    cmd = [
        str(_PYTHON_VENV), str(_SCRAPER_ACM),
        '--url',     search_url,
        '--sup',     sup_cubierta,
        '--cochera', cochera,
    ]
    if ambientes:
        cmd += ['--ambientes', ambientes]
    if antiguedad:
        cmd += ['--antiguedad', antiguedad]
    if piso:
        cmd += ['--piso', piso]
    if disposicion:
        cmd += ['--disposicion', disposicion]
    banos_form = request.form.get('banos', '').strip()
    if banos_form:
        cmd += ['--banos', banos_form]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            err = _he.escape((result.stderr or '')[-1200:])
            return _acm_html_page('Error', f'<div class="alert alert-error"><b>Error en el scraper:</b><pre style="margin-top:8px;font-size:12px;white-space:pre-wrap">{err}</pre></div>')
        stdout = (result.stdout or '').strip()
        if not stdout:
            return _acm_html_page('Error', '<div class="alert alert-error">El scraper no devolvió datos.</div>')
        data = json.loads(stdout)
    except subprocess.TimeoutExpired:
        return _acm_html_page('Error', '<div class="alert alert-error">Timeout (&gt;30 min). Intentá de nuevo.</div>')
    except Exception as e:
        return _acm_html_page('Error', f'<div class="alert alert-error">{_he.escape(str(e))}</div>')

    candidatos = data.get('candidatos', [])
    if len(candidatos) < 6:
        return _acm_html_page('Sin datos',
            f'<div class="alert alert-warn">Solo se encontraron {len(candidatos)} candidatos. '
            'Ampliá los filtros en ZonaProp (más ambientes, mayor rango de m², barrios limítrofes).</div>')

    session = {
        'universo_stats':       data.get('universo_stats', {}),
        'outliers':             data.get('outliers', []),
        'candidatos':           candidatos,
        'candidatos_restantes': data.get('candidatos_restantes', []),
        'datos_prop': {
            'direccion':       direccion,
            'barrio':          barrio,
            'tipo':            tipo,
            'ambientes':       ambientes,
            'sup_cubierta':    sup_cubierta,
            'sup_semicubierta':sup_semi if sup_semi and sup_semi != '0' else '',
            'antiguedad':      antiguedad,
            'piso':            piso,
            'disposicion':     disposicion,
            'cochera':         cochera,
            'apto_credito':    apto_credito,
            'expensas':        expensas,
            'estado':          _ACM_ESTADO_LABELS.get(estado_slug, 'Buen estado'),
            'estado_slug':     estado_slug,
            'coef_estado':     _ACM_ESTADO_COEFS.get(estado_slug, 0.0),
        },
    }
    return _render_acm_preview(session)


# ── Render preview ────────────────────────────────────────────────────────────

def _render_acm_preview(session: dict) -> str:
    import html as _he

    stats               = session.get('universo_stats', {})
    outliers            = session.get('outliers', [])
    candidatos          = session.get('candidatos', [])
    candidatos_rest     = session.get('candidatos_restantes', [])
    dp                  = session.get('datos_prop', {})

    señal_cls = 'alert-info'
    if stats.get('dias_pct_mas90', 0) >= 50:
        señal_cls = 'alert-warn'
    elif stats.get('dias_pct_30', 0) >= 40:
        señal_cls = 'alert-success'

    dias_html = ''
    if stats.get('dias_mediana') is not None:
        dias_html = f'''
<div class="metric-row" style="margin-top:12px">
  <div class="metric-card">
    <div class="metric-label">Mediana días en mercado</div>
    <div class="metric-value sm">{stats["dias_mediana"]} días</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">≤ 30 días</div>
    <div class="metric-value sm" style="color:var(--green)">{stats.get("dias_pct_30",0)}%</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">31–90 días</div>
    <div class="metric-value sm" style="color:#92400e">{stats.get("dias_pct_90",0)}%</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">&gt; 90 días</div>
    <div class="metric-value sm" style="color:var(--red)">{stats.get("dias_pct_mas90",0)}%</div>
  </div>
</div>
<div class="alert {señal_cls}" style="margin-top:8px">📊 {_he.escape(stats.get("señal_mercado",""))}</div>
'''

    outliers_html = ''
    if outliers:
        rows_out = ''.join(
            f'<tr>'
            f'<td>{_he.escape(o.get("direccion","") or o.get("barrio",""))}</td>'
            f'<td style="text-align:right;font-family:monospace">{_acm_fmt(o.get("precio_m2"))}</td>'
            f'<td style="text-align:center">{"⬆ alto" if o.get("motivo")=="alto" else "⬇ bajo"}</td>'
            f'<td style="text-align:center">'
            + (f'<a href="{_he.escape(o["url"])}" target="_blank" class="link-zp">Ver →</a>' if o.get('url') else '—')
            + '</td></tr>'
            for o in outliers[:10]
        )
        outliers_html = f'''
<div class="card">
  <div class="section-hdr">Outliers — {len(outliers)} propiedades fuera del IQR (excluidas del ranking)</div>
  <p style="font-size:13px;color:var(--muted);margin-bottom:12px">Abrí los links para confirmar si son datos reales o errores de carga.</p>
  <div style="overflow-x:auto">
  <table class="cand-tbl">
    <thead><tr><th>Dirección</th><th style="text-align:right">USD/m²</th><th style="text-align:center">Motivo</th><th style="text-align:center">Link</th></tr></thead>
    <tbody>{rows_out}</tbody>
  </table></div>
</div>'''

    max_score = max((c.get('_score', 0) for c in candidatos), default=1) or 1

    rows_cand = ''
    for i, c in enumerate(candidatos):
        score     = c.get('_score', 0)
        score_pct = int(score / max_score * 100)
        dias      = c.get('dias_publicado')
        if dias is None:
            dias_cell = '<span class="dias-badge" style="background:#f3f4f6;color:var(--muted)">—</span>'
        elif dias <= 30:
            dias_cell = f'<span class="dias-badge dias-fresh">{dias}d</span>'
        elif dias <= 90:
            dias_cell = f'<span class="dias-badge dias-mid">{dias}d</span>'
        else:
            dias_cell = f'<span class="dias-badge dias-old">{dias}d</span>'

        link_html = (
            f'<a href="{_he.escape(c["url"])}" target="_blank" class="link-zp">Ver ↗</a>'
            if c.get('url') else '—'
        )

        rows_cand += f'''<tr id="row-{i}">
  <td class="chk-cell"><input type="checkbox" name="confirmados" value="{i}" onchange="onCheck(this)" id="chk-{i}"></td>
  <td style="font-weight:600;color:var(--primary)">{i+1}</td>
  <td>{_he.escape((c.get("direccion") or c.get("barrio") or "—")[:45])}</td>
  <td style="text-align:center">{c.get("ambientes") or "—"}</td>
  <td style="text-align:center">{f"{int(c['sup_cubierta'])} m²" if c.get("sup_cubierta") else "—"}</td>
  <td style="text-align:center">{str(c.get("piso")) if c.get("piso") is not None else "—"}</td>
  <td style="text-align:center">{_he.escape(c.get("disposicion") or "—")}</td>
  <td style="text-align:center">{"✓" if c.get("cochera") else "—"}</td>
  <td style="text-align:right;font-family:monospace">{_acm_fmt(c.get("precio_por_m2"))}</td>
  <td style="text-align:right;font-family:monospace">{_acm_fmt(c.get("precio"))}</td>
  <td style="text-align:right;font-family:monospace">{_acm_fmt_ars(c.get("expensas")) if c.get("expensas") else "—"}</td>
  <td>{dias_cell}</td>
  <td><div class="score-bar"><div class="score-fill" style="width:{score_pct}%"></div></div></td>
  <td style="text-align:center">{link_html}</td>
</tr>'''

    cands_json      = _he.escape(json.dumps(candidatos, ensure_ascii=False))
    dp_json         = _he.escape(json.dumps(dp, ensure_ascii=False))
    stats_json      = _he.escape(json.dumps(stats, ensure_ascii=False))
    restantes_json  = _he.escape(json.dumps(candidatos_rest, ensure_ascii=False))
    restantes_display = ';display:none' if not candidatos_rest else ''
    len_candidatos  = len(candidatos)
    dp_json_inline  = json.dumps(dp, ensure_ascii=False)

    body = f'''
<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:4px">
  <h1>Resultado del Análisis</h1>
  <a href="/acm" style="font-size:13px;color:var(--muted);text-decoration:none">← Nueva búsqueda</a>
</div>
<p class="subtitle">{_he.escape(dp.get("barrio",""))} · {_he.escape(dp.get("tipo",""))} · {_he.escape(dp.get("sup_cubierta",""))} m² · {_he.escape(dp.get("direccion",""))}</p>

<div class="card">
  <div class="section-hdr">Universo de mercado analizado</div>
  <div class="metric-row">
    <div class="metric-card">
      <div class="metric-label">Propiedades analizadas</div>
      <div class="metric-value">{stats.get("n_validos",0)} <span style="font-size:13px;color:var(--muted)">de {stats.get("n_total",0)}</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Mediana USD/m²</div>
      <div class="metric-value orange">{_acm_fmt(stats.get("mediana_m2"))}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Rango Q1–Q3</div>
      <div class="metric-value sm">{_acm_fmt(stats.get("p25"))} – {_acm_fmt(stats.get("p75"))}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Outliers excluidos</div>
      <div class="metric-value sm">{stats.get("n_outliers",0)}</div>
    </div>
  </div>
  {dias_html}
</div>

{outliers_html}

<div class="card">
  <div class="section-hdr">Top 24 candidatos — marcá exactamente 6 testigos</div>
  <div class="alert alert-info" style="margin-bottom:16px">
    Abrí cada aviso en ZonaProp antes de marcar. Verificá estado real, fotos, m² descubiertos y que siga activo.
    Marcá exactamente <b>6</b> testigos para continuar.
  </div>
  <div id="sel-status" style="margin-bottom:12px;font-size:14px;font-weight:600;color:var(--primary)">
    Seleccionados: <span id="sel-count">0</span> / 6
  </div>
  <div style="overflow-x:auto">
  <form id="confirm-form" action="/acm/confirmar" method="POST">
    <input type="hidden" name="candidatos_json" value="{cands_json}">
    <input type="hidden" name="datos_prop_json" value="{dp_json}">
    <input type="hidden" name="stats_json"      value="{stats_json}">
    <input type="hidden" id="restantes-json" value="{restantes_json}">
    <table class="cand-tbl">
      <thead><tr>
        <th class="chk-cell">✓</th><th>#</th><th>Dirección</th>
        <th style="text-align:center">Amb</th><th style="text-align:center">m²</th>
        <th style="text-align:center">Piso</th><th style="text-align:center">Disp</th>
        <th style="text-align:center">Coch</th><th style="text-align:right">USD/m²</th>
        <th style="text-align:right">Precio</th><th style="text-align:right">Expensas</th>
        <th style="text-align:center">Días</th><th style="text-align:center">Simil.</th>
        <th style="text-align:center">Link</th>
      </tr></thead>
      <tbody>{rows_cand}</tbody>
    </table>
    <div style="margin-top:20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap">
      <button type="submit" class="btn btn-orange" id="confirm-btn" disabled>
        Confirmar 6 testigos →
      </button>
      <span id="confirm-hint" style="font-size:13px;color:var(--muted)">Seleccioná exactamente 6.</span>
    </div>
  </form>
  </div>

  <div id="mas-candidatos-section" style="margin-top:16px{restantes_display}">
    <button id="mas-btn" class="btn btn-outline" onclick="cargarMasCandidatos()">
      Ver próximos 12 candidatos
      <span class="loader" id="mas-loader" style="display:none"></span>
    </button>
    <span id="mas-hint" style="font-size:13px;color:var(--muted);margin-left:12px"></span>
  </div>
  <div id="tabla-extra" style="overflow-x:auto;margin-top:12px"></div>

</div>

<script>
function onCheck(cb) {{
  var all = document.querySelectorAll('input[name="confirmados"]');
  var checked = Array.from(all).filter(function(c){{return c.checked;}});
  var n = checked.length;
  if (!cb.checked === false && n > 6) {{ cb.checked = false; return; }}
  document.getElementById('sel-count').textContent = Math.min(n, 6);
  all.forEach(function(c) {{
    var row = document.getElementById('row-' + c.value);
    if (row) row.classList.toggle('confirmado', c.checked);
  }});
  var btn  = document.getElementById('confirm-btn');
  var hint = document.getElementById('confirm-hint');
  if (n === 6) {{
    btn.disabled = false;
    hint.textContent = '✓ 6 testigos seleccionados.';
    hint.style.color = 'var(--green)';
  }} else {{
    btn.disabled = true;
    hint.textContent = 'Seleccioná exactamente 6.';
    hint.style.color = 'var(--muted)';
  }}
}}

var _globalOffset = {len_candidatos};

function cargarMasCandidatos() {{
  var btn = document.getElementById('mas-btn');
  btn.disabled = true;
  document.getElementById('mas-loader').style.display = 'inline-block';
  document.getElementById('mas-hint').textContent = 'Abriendo browser y scrapeando detalles...';

  var restantesRaw = document.getElementById('restantes-json').value;
  var restantes;
  try {{ restantes = JSON.parse(restantesRaw); }} catch(e) {{ restantes = []; }}

  var batch = restantes.slice(0, 12);
  var resto = restantes.slice(12);

  fetch('/acm/mas-candidatos', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{
      candidatos: batch,
      datos_prop: {dp_json_inline}
    }})
  }})
  .then(function(r) {{ return r.json(); }})
  .then(function(data) {{
    if (data.error) {{
      document.getElementById('mas-hint').textContent = 'Error: ' + data.error;
      btn.disabled = false;
      document.getElementById('mas-loader').style.display = 'none';
      return;
    }}

    var nuevos = data.candidatos || [];
    var tbody = document.querySelector('.cand-tbl tbody') ||
                document.getElementById('tabla-extra');

    // Agregar filas a la tabla principal
    var mainTbody = document.querySelector('.cand-tbl tbody');
    nuevos.forEach(function(c, idx) {{
      var i = _globalOffset + idx;
      var diasCls = c.dias_publicado === null ? '' :
                    c.dias_publicado <= 30 ? 'dias-fresh' :
                    c.dias_publicado <= 90 ? 'dias-mid' : 'dias-old';
      var diasTxt = c.dias_publicado === null ? '—' : c.dias_publicado + 'd';
      var tr = document.createElement('tr');
      tr.id = 'row-' + i;
      tr.innerHTML =
        '<td class="chk-cell"><input type="checkbox" name="confirmados" value="' + i + '" onchange="onCheck(this)" id="chk-' + i + '"></td>' +
        '<td style="font-weight:600;color:var(--primary)">' + (i+1) + '</td>' +
        '<td>' + (c.direccion || c.barrio || '—').substring(0,45) + '</td>' +
        '<td style="text-align:center">' + (c.ambientes || '—') + '</td>' +
        '<td style="text-align:center">' + (c.sup_cubierta ? Math.round(c.sup_cubierta) + ' m²' : '—') + '</td>' +
        '<td style="text-align:center">' + (c.piso !== null && c.piso !== undefined ? c.piso : '—') + '</td>' +
        '<td style="text-align:center">' + (c.disposicion || '—') + '</td>' +
        '<td style="text-align:center">' + (c.cochera ? '✓' : '—') + '</td>' +
        '<td style="text-align:right;font-family:monospace">' + (c.precio_por_m2 ? 'USD ' + Math.round(c.precio_por_m2).toLocaleString('es-AR') : '—') + '</td>' +
        '<td style="text-align:right;font-family:monospace">' + (c.precio ? 'USD ' + Math.round(c.precio).toLocaleString('es-AR') : '—') + '</td>' +
        '<td style="text-align:right;font-family:monospace">' + (c.expensas ? '$ ' + Math.round(c.expensas).toLocaleString('es-AR') : '—') + '</td>' +
        '<td><span class="dias-badge ' + diasCls + '">' + diasTxt + '</span></td>' +
        '<td></td>' +
        '<td style="text-align:center">' + (c.url ? '<a href="' + c.url + '" target="_blank" class="link-zp">Ver ↗</a>' : '—') + '</td>';
      mainTbody.appendChild(tr);

      // Registrar en el form hidden para que el confirm lo pueda usar
      document.querySelector('input[name="candidatos_json"]').value =
        JSON.stringify(
          JSON.parse(document.querySelector('input[name="candidatos_json"]').value).concat([c])
        );
    }});

    _globalOffset += nuevos.length;

    // Actualizar restantes
    document.getElementById('restantes-json').value = JSON.stringify(resto);

    document.getElementById('mas-loader').style.display = 'none';
    if (resto.length === 0) {{
      btn.style.display = 'none';
      document.getElementById('mas-hint').textContent = 'No hay más candidatos disponibles.';
    }} else {{
      btn.disabled = false;
      document.getElementById('mas-hint').textContent = nuevos.length + ' candidatos agregados. Quedan ' + resto.length + ' más.';
    }}
  }})
  .catch(function(e) {{
    document.getElementById('mas-hint').textContent = 'Error de conexión.';
    btn.disabled = false;
    document.getElementById('mas-loader').style.display = 'none';
  }});
}}
</script>
'''
    return _acm_html_page('Preview', body)



# ── /acm/mas-candidatos — Scrape detalle de batch adicional ───────────────────

@app.route('/acm/mas-candidatos', methods=['POST'])
def acm_mas_candidatos():
    import html as _he
    body = request.get_json()
    if not body:
        return jsonify({'error': 'Sin datos'}), 400

    candidatos_batch = body.get('candidatos', [])
    datos_prop       = body.get('datos_prop', {})

    if not candidatos_batch:
        return jsonify({'candidatos': []})

    if not _SCRAPER_ACM.exists() or not _PYTHON_VENV.exists():
        return jsonify({'error': 'Scraper no encontrado'}), 500

    # Llamar al scraper en modo batch: pasamos las URLs como JSON stdin
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json',
                                     delete=False, encoding='utf-8') as tf:
        json.dump({'candidatos': candidatos_batch, 'datos_prop': datos_prop},
                  tf, ensure_ascii=False)
        tf_path = tf.name

    try:
        cmd = [
            str(_PYTHON_VENV), str(_SCRAPER_ACM),
            '--batch-file', tf_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        os.unlink(tf_path)

        if result.returncode != 0:
            return jsonify({'error': (result.stderr or '')[-500:]}), 500

        stdout = (result.stdout or '').strip()
        if not stdout:
            return jsonify({'error': 'Sin datos del scraper'}), 500

        data = json.loads(stdout)
        return jsonify({'candidatos': data.get('candidatos', [])})

    except subprocess.TimeoutExpired:
        try: os.unlink(tf_path)
        except: pass
        return jsonify({'error': 'Timeout — intentá de nuevo'}), 500
    except Exception as e:
        try: os.unlink(tf_path)
        except: pass
        return jsonify({'error': str(e)}), 500


# ── /acm/confirmar ────────────────────────────────────────────────────────────

@app.route('/acm/confirmar', methods=['POST'])
def acm_confirmar():
    import html as _he

    try:
        candidatos = json.loads(request.form.get('candidatos_json', '[]'))
        dp         = json.loads(request.form.get('datos_prop_json', '{}'))
        stats      = json.loads(request.form.get('stats_json', '{}'))
    except Exception as e:
        return _acm_html_page('Error', f'<div class="alert alert-error">{_he.escape(str(e))}</div>')

    indices_str = request.form.getlist('confirmados')
    if len(indices_str) != 6:
        return _acm_html_page('Error',
            f'<div class="alert alert-error">Seleccionaste {len(indices_str)} testigos. Deben ser exactamente 6.</div>')

    try:
        indices  = [int(i) for i in indices_str]
        testigos = [candidatos[i] for i in indices if i < len(candidatos)]
    except Exception as e:
        return _acm_html_page('Error', f'<div class="alert alert-error">{_he.escape(str(e))}</div>')

    if len(testigos) < 6:
        return _acm_html_page('Error', '<div class="alert alert-error">Error recuperando testigos. Volvé atrás.</div>')

    vals_m2  = [t['precio_por_m2'] for t in testigos if t.get('precio_por_m2')]
    if not vals_m2:
        return _acm_html_page('Error', '<div class="alert alert-error">Los testigos no tienen precio/m².</div>')

    vals_s   = sorted(vals_m2)
    n        = len(vals_s)
    mediana  = (vals_s[n // 2] + vals_s[~(n // 2)]) / 2
    m2_min   = min(vals_m2)
    m2_max   = max(vals_m2)
    sup      = float(dp.get('sup_cubierta') or 0)
    coef     = float(dp.get('coef_estado') or 0)
    estado   = dp.get('estado', 'Buen estado')

    ps        = round(mediana * sup) if sup > 0 else 0
    r_min     = round(m2_min * sup)  if sup > 0 else 0
    r_max     = round(m2_max * sup)  if sup > 0 else 0
    p_adj     = round(ps * (1 + coef))    if ps    else 0
    r_min_adj = round(r_min * (1 + coef)) if r_min else 0
    r_max_adj = round(r_max * (1 + coef)) if r_max else 0
    coef_pct  = (
        f"+{int(round(coef*100))}%" if coef > 0
        else (f"{int(round(coef*100))}%" if coef < 0 else "0%")
    )

    stats_final    = {**stats, 'mediana_m2': round(mediana),
                      'precio_sugerido': ps, 'rango_min': r_min, 'rango_max': r_max}
    datos_prop_fin = {**dp,
        'precio_ajustado': p_adj,
        'cochera':         dp.get('cochera') in ('true', True),
        'apto_credito':    dp.get('apto_credito') in ('true', True),
        'expensas':        dp.get('expensas') or None,
    }

    acm_data_json = _he.escape(json.dumps({
        'comparables':   testigos,
        'stats':         stats_final,
        'top3_indices':  list(range(min(3, len(testigos)))),
        'datos_prop':    datos_prop_fin,
    }, ensure_ascii=False))

    cards_html = ''
    for i, t in enumerate(testigos):
        meta = []
        if t.get('ambientes'):      meta.append(f"{t['ambientes']} amb")
        if t.get('sup_cubierta'):   meta.append(f"{int(t['sup_cubierta'])} m²")
        if t.get('piso') is not None: meta.append(f"Piso {t['piso']}")
        if t.get('disposicion'):    meta.append(t['disposicion'])
        if t.get('antiguedad'):     meta.append(f"{t['antiguedad']} años")
        if t.get('cochera'):        meta.append('✓ Cochera')
        if t.get('dias_publicado') is not None: meta.append(f"{t['dias_publicado']}d pub")
        meta_html = ''.join(
            f'<span style="background:#f0f4f8;padding:2px 8px;border-radius:4px;font-size:12px;color:var(--muted)">{_he.escape(m)}</span>'
            for m in meta
        )
        link_html = (
            f'<a href="{_he.escape(t["url"])}" target="_blank" class="link-zp">Ver en ZonaProp →</a>'
            if t.get('url') else ''
        )
        cards_html += f'''
<div style="border:2px solid var(--orange);border-radius:10px;padding:16px 18px;background:#fff;margin-bottom:10px">
  <div style="font-size:11px;font-weight:700;color:var(--orange);text-transform:uppercase;margin-bottom:6px">Testigo {i+1}</div>
  <div style="font-size:15px;font-weight:700;color:var(--primary);margin-bottom:4px">{_he.escape((t.get("direccion") or t.get("barrio") or "—"))}</div>
  <div style="font-size:17px;font-weight:800;color:var(--orange);margin-bottom:8px">{_acm_fmt(t.get("precio"))}</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px">{meta_html}</div>
  <div style="font-size:13px;font-weight:600">USD/m²: {_acm_fmt(t.get("precio_por_m2"))}</div>
  {"<div style='font-size:12px;color:var(--muted)'>Expensas: " + _acm_fmt_ars(t.get("expensas")) + "/mes</div>" if t.get("expensas") else ""}
  <div style="margin-top:8px">{link_html}</div>
</div>'''

    body = f'''
<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:4px">
  <h1>Análisis Final — 6 Testigos Confirmados</h1>
  <a href="/acm" style="font-size:13px;color:var(--muted);text-decoration:none">← Nueva búsqueda</a>
</div>
<p class="subtitle">{_he.escape(dp.get("barrio",""))} · {_he.escape(dp.get("tipo",""))} · {_he.escape(dp.get("sup_cubierta",""))} m²</p>

<div class="card">
  <div class="section-hdr">6 Testigos Validados</div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">{cards_html}</div>
</div>

<div class="card">
  <div class="section-hdr">Resultado del Análisis</div>
  <div class="metric-row">
    <div class="metric-card">
      <div class="metric-label">Mediana USD/m² testigos</div>
      <div class="metric-value orange">{_acm_fmt(round(mediana))}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Rango testigos</div>
      <div class="metric-value sm">{_acm_fmt(round(m2_min))} – {_acm_fmt(round(m2_max))}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Precio sugerido mediana</div>
      <div class="metric-value sm" style="text-decoration:line-through;color:var(--muted)">{_acm_fmt(ps)}</div>
    </div>
    <div class="metric-card" style="border:2px solid var(--orange)">
      <div class="metric-label">Ajustado — {_he.escape(estado)} ({_he.escape(coef_pct)})</div>
      <div class="metric-value orange">{_acm_fmt(p_adj)}</div>
    </div>
  </div>
  <div class="metric-row">
    <div class="metric-card">
      <div class="metric-label">Rango ajustado</div>
      <div class="metric-value sm">{_acm_fmt(r_min_adj)} – {_acm_fmt(r_max_adj)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Universo analizado</div>
      <div class="metric-value sm">{stats.get("n_validos",0)} propiedades</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Mediana universo USD/m²</div>
      <div class="metric-value sm">{_acm_fmt(stats.get("mediana_m2"))}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Señal de mercado</div>
      <div class="metric-value sm" style="font-size:11px;line-height:1.4">{_he.escape((stats.get("señal_mercado",""))[:100])}</div>
    </div>
  </div>
</div>

<div class="price-adj-card">
  <div class="section-hdr" style="margin-bottom:10px">Generar informe .docx</div>
  <p style="font-size:13px;color:#374151;margin-bottom:16px">
    Precio sugerido: <span style="color:var(--muted);text-decoration:line-through">{_acm_fmt(ps)}</span>
    &nbsp;→&nbsp; Ajustado ({_he.escape(estado)}, {_he.escape(coef_pct)}):
    <b style="color:var(--orange)">{_acm_fmt(p_adj)}</b>
  </p>
  <form action="/acm/generar" method="POST">
    <input type="hidden" name="acm_data" value="{{acm_data_json}}">
    <p style="font-size:13px;color:var(--muted);margin-bottom:14px">
      Editá el rango antes de generar. El informe muestra el rango como recomendación principal
      y calcula el precio/m² y el posicionamiento en base a estos valores.
    </p>
    <div style="display:flex;align-items:flex-end;gap:16px;flex-wrap:wrap">
      <div>
        <label style="margin-bottom:6px">Rango mínimo (USD)</label>
        <input type="number" name="rango_min" class="price-input-big"
               value="{{r_min_adj or r_min or ''}}" min="1000" max="100000000" required
               style="width:200px">
      </div>
      <div style="padding-bottom:14px;font-size:20px;color:var(--muted)">–</div>
      <div>
        <label style="margin-bottom:6px">Rango máximo (USD)</label>
        <input type="number" name="rango_max" class="price-input-big"
               value="{{r_max_adj or r_max or ''}}" min="1000" max="100000000" required
               style="width:200px">
      </div>
      <div style="padding-bottom:12px">
        <button type="submit" class="btn btn-orange" id="gen-btn">
          <span id="gen-btn-txt">Generar informe ACM .docx</span>
          <span class="loader" id="gen-loader" style="display:none"></span>
        </button>
      </div>
    </div>
    <p style="font-size:11px;color:var(--muted);margin-top:8px">
      Precio de referencia interno (mediana ajustada): {_acm_fmt(p_adj or ps)}
    </p>
  </form>
</div>
<script>
document.querySelector('form[action="/acm/generar"]').addEventListener('submit', function() {{
  document.getElementById('gen-btn').disabled = true;
  document.getElementById('gen-btn-txt').textContent = 'Generando...';
  document.getElementById('gen-loader').style.display = 'inline-block';
}});
</script>
'''
    return _acm_html_page('Confirmación', body)


# ── /acm/generar ─────────────────────────────────────────────────────────────

@app.route('/acm/generar', methods=['POST'])
def acm_generar():
    from flask import send_file
    from io import BytesIO as _BytesIO
    from datetime import date as _d2
    import html as _he

    precio_final_str = request.form.get('precio_final', '0').strip()
    rango_min_str    = request.form.get('rango_min', '0').strip()
    rango_max_str    = request.form.get('rango_max', '0').strip()
    acm_data_raw     = request.form.get('acm_data', '{}')

    try:
        acm_data     = json.loads(acm_data_raw)
        comparables  = acm_data.get('comparables', [])
        stats        = acm_data.get('stats', {})
        top3_indices = acm_data.get('top3_indices', [])
        datos_prop   = acm_data.get('datos_prop', {})
    except Exception as e:
        return _acm_html_page('Error', f'<div class="alert alert-error">{_he.escape(str(e))}</div>')

    try:
        precio_final = float(re.sub(r'[^0-9.]', '', precio_final_str)) if precio_final_str else 0
    except ValueError:
        precio_final = 0

    try:
        rango_min = float(re.sub(r'[^0-9.]', '', rango_min_str)) if rango_min_str else 0
        rango_max = float(re.sub(r'[^0-9.]', '', rango_max_str)) if rango_max_str else 0
    except ValueError:
        rango_min = rango_max = 0

    # Si no hay rango explícito, usar precio_final como punto medio
    if not rango_min and not rango_max and precio_final:
        rango_min = round(precio_final * 0.95)
        rango_max = round(precio_final * 1.05)

    if not comparables or (not precio_final and not rango_min):
        return _acm_html_page('Error', '<div class="alert alert-error">Datos incompletos.</div>')

    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from acm_report import generar_docx
    except ImportError as e:
        return _acm_html_page('Error', f'<div class="alert alert-error">No se pudo importar acm_report: {_he.escape(str(e))}</div>')

    try:
        docx_bytes = generar_docx(
            datos_propiedad = datos_prop,
            comparables     = comparables,
            stats           = stats,
            top3_indices    = top3_indices,
            precio_final    = precio_final,
            rango_min       = rango_min,
            rango_max       = rango_max,
        )
    except Exception as e:
        return _acm_html_page('Error', f'<div class="alert alert-error">Error generando .docx: {_he.escape(str(e))}</div>')

    fecha_str = _d2.today().strftime('%Y%m%d')
    barrio_fn = datos_prop.get('barrio', 'ACM').replace(' ', '_')
    filename  = f"ACM_{barrio_fn}_{fecha_str}.docx"

    buf = _BytesIO(docx_bytes)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=filename,
    )


if __name__ == '__main__':
    print(f"\n✓ Generador de fichas corriendo en http://localhost:{PORT}\n")
    app.run(debug=False, port=PORT, host="127.0.0.1")
