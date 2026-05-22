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
        'universo_stats': data.get('universo_stats', {}),
        'outliers':       data.get('outliers', []),
        'candidatos':     candidatos,
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

    stats     = session.get('universo_stats', {})
    outliers  = session.get('outliers', [])
    candidatos= session.get('candidatos', [])
    dp        = session.get('datos_prop', {})

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

    cands_json = _he.escape(json.dumps(candidatos, ensure_ascii=False))
    dp_json    = _he.escape(json.dumps(dp, ensure_ascii=False))
    stats_json = _he.escape(json.dumps(stats, ensure_ascii=False))

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
</script>
'''
    return _acm_html_page('Preview', body)


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
    <input type="hidden" name="acm_data" value="{acm_data_json}">
    <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
      <div>
        <label style="margin-bottom:6px">Precio final (USD)</label>
        <input type="number" name="precio_final" class="price-input-big"
               value="{p_adj or ps or ''}" min="1000" max="100000000" required>
      </div>
      <div style="margin-top:22px">
        <button type="submit" class="btn btn-orange" id="gen-btn">
          <span id="gen-btn-txt">Generar informe ACM .docx</span>
          <span class="loader" id="gen-loader" style="display:none"></span>
        </button>
      </div>
    </div>
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

    if not comparables or precio_final <= 0:
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
