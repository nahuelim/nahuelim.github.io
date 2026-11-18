// CRM Nahuel — proyecto de Apps Script SEPARADO del script del Sheet.
// No pegar esto en el proyecto que tiene doGet/doPost del ACM.

const VERSION = '38';   // tiene que coincidir con VERSION en crm/index.html
const APP_URL = 'https://nahuelim.com.ar/crm/';
const ACM_INDICE_ID = '1kvQ6BzSmLHSjbc2yhUKT-BdnOxJhklQ7W4pKDmIZ5A8';   // planilla "ACMs" (la llena el formulario del ACM)
const SHEET_ID = '1LEBztjtgGCj0PzpRnpcZezQaM0rmdycHVCHr4aZTjmw';
const C21_ID   = '1iYfyoglxV0YSMmAvNLYb1qqHmRnLJMBhsZIwN-udfvc';
const CAL_ID   = 'b2305b70e321e7d586bb4b5d57c5f9ae1345ce2be989f4fd795e02f08c030945@group.calendar.google.com';   // calendario C21

const LLAMADAS = 3;
// Mensajes despues de las 3 llamadas: [codigo, dias habiles desde el contacto anterior]: hoy, +1, +1, +2, +2, +3, +7.
// Despues del ultimo: EN PAUSA, primer recontacto a +15 y desde ahi cada DIAS_ARCHIVO.
const CADENCIA = [['CAD1', 0], ['CAD2', 1], ['CAD4', 1], ['CAD5', 2], ['CAD6', 2], ['CAD8', 3], ['CAD9', 7]];
const DIAS_FIN_CADENCIA = 15;
const DIAS_ARCHIVO = 45;        // habiles, recontacto de archivados
const DIAS_SEGUIMIENTO = 2;     // habiles, default para activos
const REACTIVAR_POR_DIA = 15;
const MARGEN_PRECIO = 0.15;     // matching: precio dentro de +-15% del presupuesto
const ACCIONES = ['Llamada', 'Mensaje', 'Seguimiento', 'Calificar', 'Enviar opciones', 'Coordinar visita', 'Visita', 'Prelisting', 'Entregar ACM', 'Oferta', 'Reserva', 'Firma', 'Recontacto', 'Otro'];
const URGENCIAS = ['Ya', '3 meses', '6 meses o más', 'Sin apuro'];
const MOTIVACIONES = ['Agrandarse', 'Achicarse', 'Primera vivienda', 'Dejar de alquilar', 'Mudanza por trabajo', 'Separación', 'Sucesión', 'Mejorar zona', 'Inversión', 'Otro'];
const ESTADOS_CADENCIA = ['NUEVO'];
// Estados: NUEVO, EN CONTACTO, CLIENTE, EN PAUSA, DESCARTADO. Los nombres viejos se traducen al leer,
// asi un script viejo que escriba "ACTIVO" no rompe nada. EN PAUSA con fecha = recontacto; sin fecha = cola de reactivacion.
const ESTADOS = ['NUEVO', 'EN CONTACTO', 'CLIENTE', 'EN PAUSA', 'DESCARTADO'];
const ESTADO_VIEJO = { 'EN CADENCIA': 'NUEVO', 'ACTIVO': 'EN CONTACTO', 'ARCHIVADO': 'EN PAUSA', 'REACTIVAR': 'EN PAUSA', 'COMPRO CON OTRO': 'DESCARTADO' };
function estadoNuevo(e) { const k = String(e || '').trim().toUpperCase(); return ESTADO_VIEJO[k] || k; }
const PAGO_CON_VENTA = ['VENTA', 'PARTE DE PAGO'];   // tiene algo para vender: captacion
const FUENTES_PROPIAS = ['Instagram', 'Facebook', 'TikTok'];   // tu pauta: sabes que propiedad consulto (mensaje IG1)
const FUENTES_SIN_CADENCIA = ['Conocido', 'Referido', 'Colega', 'Amigo'];   // gente conocida: entra como ACTIVO, sin llamadas en cadencia
// Vendedores que no captaste: revisar si publicaron y recaptar
const VENTA_SEGUIMIENTO = ['NO CAPTADA', 'CON OTRA INMO'];

// ─── LOGICA PURA (testeada en test.js) ───────────────────────────────────────

function normalizarTel(t) {
  let d = String(t || '').replace(/\D/g, '');
  if (d.startsWith('54')) d = d.slice(2);
  if (d.startsWith('9') && d.length === 11) d = d.slice(1);
  if (d.startsWith('0')) d = d.slice(1);
  if (d.length === 10 && d.startsWith('15')) d = '11' + d.slice(2);
  if (d.length === 12) {
    for (let k = 2; k <= 4; k++) if (d.substr(k, 2) === '15') { d = d.slice(0, k) + d.slice(k + 2); break; }
  }
  return d.length === 10 ? '549' + d : '';
}

const MESES_ = { ene: 0, feb: 1, mar: 2, abr: 3, may: 4, jun: 5, jul: 6, ago: 7, sep: 8, oct: 9, nov: 10, dic: 11 };

function fecha_(v) {
  if (v instanceof Date && !isNaN(v)) return new Date(v.getFullYear(), v.getMonth(), v.getDate());
  const s = String(v || '').trim();
  let m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return new Date(+m[3], m[2] - 1, +m[1]);
  m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return new Date(+m[1], m[2] - 1, +m[3]);
  m = s.toLowerCase().match(/^(\d{1,2})-([a-z]{3})-(\d{4})/);
  if (m && m[2] in MESES_) return new Date(+m[3], MESES_[m[2]], +m[1]);
  return null;
}

const MOTIVOS_VUELVE = ['NO BUSCA AHORA'];
const MOTIVOS_DESCARTE = ['NO BUSCA AHORA', 'COMPRO CON OTRO', 'VENDIO CON OTRO', 'ALQUILER', 'NUMERO INVALIDO', 'NO INTERESADO', 'BARRILETE', 'COLEGA', 'OTRO AGENTE C21', 'BLOQUEADO', 'OTRO'];   // al archivar con este motivo, vuelve; con cualquier otro, no
// ─── REGLAS DE HOY (ver REGLAS_CRM.md) ──────────────────────────────────────
const ETAPAS_VENTA = ['CAPTAR', 'PRELISTING', 'ACM', 'NO CAPTADA', 'CON OTRA INMO', 'EN PUBLICACION', 'EN VENTA', 'RESERVA', 'VENDIDA'];
const ETAPA_VENTA_VIEJA = { 'CAPTADA': 'EN VENTA' };
// Compradores: cada cuántos días (corridos) desde el último contacto. Aparece desde min; pasado max está atrasado.
const RITMO = { CALIENTE: [1, 2], TIBIO: [4, 5], FRIO: [10, 12] };
const DIAS_URGENTE = 30;            // fecha límite a 30 días o menos: arriba de todo
const PLAZO_URGENCIA = { 'Ya': 30, '3 meses': 90, '6 meses o más': 180 };   // chip -> fecha límite estimada
const ESTIMADA = 'Estimada';
// Vendedores: hitos en días corridos desde el prelisting. 20-40-60 revisar si publicó; 75-90-105-120 recontactar.
const HITOS_NO_CAPTADA = [20, 40, 60, 75, 90, 105, 120];
const HITOS_CON_OTRA = [75, 90, 105, 120];
const DIAS_VENDEDOR = { CAPTAR: 7, PRELISTING: 7, ACM: 7, 'EN VENTA': 14 };
const DIAS_REVIVIR = 45;            // revivir: un toque cada 45 días como mucho
const REVIVIR_POR_DIA = 15;         // tope de seguridad de WhatsApp (números que no te tienen agendado)
const RELACION_DIAS = { A: 30, B: 60, C: 90 };   // contactos de relacion: cada cuanto aparecen en Hoy
const RELACION_POR_DIA = 5;   // tope por dia, para que no se te junten
const DIAS_FECHAS = 3;   // cumpleanos y aniversarios siguen en Hoy hasta 3 dias despues
function sumarDias_(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
// Dias desde el cumpleanos/aniversario de este anio (0 = hoy). null si no hay fecha o todavia no llego.
function diasDesdeFecha(f, hoy) {
  if (!f) return null;
  const este = new Date(hoy.getFullYear(), f.getMonth(), f.getDate());
  const d = Math.round((hoy - este) / 86400000);
  return d >= 0 ? d : null;
}

function hoy_() { const n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); }
function clave_(d) { return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate(); }
function esHabil_(d, fer) { const w = d.getDay(); return w !== 0 && w !== 6 && !fer.has(clave_(d)); }

function sumarHabiles(desde, n, fer) {
  const d = new Date(desde);
  if (n === 0) { while (!esHabil_(d, fer)) d.setDate(d.getDate() + 1); return d; }
  for (let k = 0; k < n;) { d.setDate(d.getDate() + 1); if (esHabil_(d, fer)) k++; }
  return d;
}

// intento = toques ya hechos (llamadas + mensajes). null = termino la cadencia.
function siguienteToque(intento) {
  if (intento < LLAMADAS) return { accion: 'Llamada', gap: 0 };   // las 3 llamadas pueden ser el mismo día (mañana, mediodía, tarde)
  const i = intento - LLAMADAS;
  return i < CADENCIA.length ? { accion: 'Mensaje', n: i + 1, codigo: CADENCIA[i][0], gap: CADENCIA[i][1] } : null;
}

function norm_(s) { return String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim(); }
function lista_(s) { return String(s || '').split(/,|\/| y /).map(norm_).filter(Boolean); }
function num_(v) { if (typeof v === 'number') return v; const d = String(v || '').replace(/[^\d]/g, ''); return d ? +d : 0; }
const ALIAS_BARRIO_ = { 'vdp': 'del parque', 'general mitre': 'mitre', 'monserrat': 'montserrat', 'velez sarfield': 'velez sarsfield', 'nueva pompeya': 'pompeya' };
function barrioN(s) {
  let x = norm_(String(s || '').replace(/\(.*?\)/g, '')).replace(/\./g, '').replace(/\s+/g, ' ').trim();
  x = x.replace(/^(villa|v)\s+/, '').replace(/^la\s+/, '');
  if (x !== 'barrio norte') x = x.replace(/\s+(norte|sur)$/, '');                // Caballito Sur = Caballito ("Barrio Norte" es un nombre)
  return ALIAS_BARRIO_[x] || x;
}
function tipoN_(t) { const x = norm_(t); return /^(dto|depto|departamento)/.test(x) ? 'departamento' : x; }

function coincide(b, p) {
  if (!b.barrios.length || !p.barrio) return false;
  if (!b.barrios.includes(barrioN(p.barrio))) return false;                       // barrio identico
  if (b.tipos.length && p.tipo && !lista_(p.tipo).map(tipoN_).some(t => b.tipos.includes(t))) return false;
  const max = b.max || b.min;                                                      // ambientes dentro del rango exacto
  if (p.amb && b.min && (p.amb < b.min || p.amb > max)) return false;
  if (p.usd && b.usd && (p.usd > b.usd * (1 + MARGEN_PRECIO) || p.usd < b.usd * (1 - MARGEN_PRECIO))) return false;
  return true;
}

function busca_(c) {
  return {
    tipos: lista_(c['BUSCA TIPO']).map(tipoN_), barrios: String(c['BUSCA BARRIOS'] || '').split(',').map(barrioN).filter(Boolean),
    min: num_(c['BUSCA AMB MIN']), max: num_(c['BUSCA AMB MAX']) >= 5 ? 99 : num_(c['BUSCA AMB MAX']), usd: num_(c['BUSCA HASTA USD'])   // 5 o mas = sin techo
  };
}

// "una busqueda" / "3 busquedas"
function busquedasTxt(n) { return n === 1 ? 'una búsqueda' : n + ' búsquedas'; }

function primerNombre_(n) {
  const s = String(n || '').trim();
  if (!s || /^usuario$/i.test(s)) return '';
  const w = s.split(/\s+/)[0];
  return w.charAt(0).toUpperCase() + w.slice(1);
}

function rellenar(texto, c, codigo, extra) {
  const vende = String(codigo || '').startsWith('V');
  const tipo = vende ? (c['VENDE TIPO'] || c['BUSCA TIPO']) : (c['BUSCA TIPO'] || c['VENDE TIPO']);
  const zona = vende ? (c['VENDE BARRIO'] || c['BUSCA BARRIOS']) : (c['BUSCA BARRIOS'] || c['VENDE BARRIO']);
  const v = {
    nombre: primerNombre_(c.NOMBRE),
    tipo: String(tipo || '').split(',')[0].trim().toLowerCase() || 'propiedad',
    zona: String(zona || '').split(',')[0].trim() || 'la zona',
    propiedad: c['CONSULTO POR'] || 'la propiedad que viste'
  };
  v.barrio = v.zona;   // C21 no trae el barrio: si no lo cargaste, dice "la zona"
  // {untipo}: con el artículo que corresponde ("un departamento", "un PH", "una casa"; sin dato, "una propiedad")
  v.untipo = { departamento:'un departamento', ph:'un PH', casa:'una casa' }[v.tipo] || 'una propiedad';
  // {consulta}: "un PH en Flores" si cargaste tipo; si no, lo de Consultó por ("el PH de Alberdi"); si no, "una propiedad en Flores"
  v.consulta = String(tipo || '').trim() ? v.untipo + ' en ' + v.barrio : (String(c['CONSULTO POR'] || '').trim() || 'una propiedad en ' + v.barrio);
  Object.assign(v, extra || {});   // ej. {busquedas}: solo si hay datos reales
  return texto.replace(/\{(\w+)\}/g, (m, k) => (k in v ? v[k] : m))
    .replace(/^,\s*/, '').replace(/\s+,/g, ',').replace(/\s{2,}/g, ' ');
}

// El nombre sin la parte "- Vende ... / Compra ..." (por si quedo guardado el formato largo)
// Solo el nombre: saca "- Compra ...", "Compra ..." (adelante o en el medio) y lo que empieza con el tipo o los ambientes
function nombreBase_(n) {
  let s = String(n || '').split(' - ')[0].replace(/\s+-\s*$/, '').trim();
  s = s.replace(/^compra\s+/i, '');   // "Compra Liliana Lorenzo PH..." (solo "Compra" adelante: así lo cargabas)
  const m = s.search(/\s(compra|vende)\s|\s(ph|dto|depto|departamento|casa)\b|\s\d+(\/\d+)?\s?amb/i);
  return (m > 0 ? s.slice(0, m) : s).trim();
}
// Barrios como se escriben en la etiqueta de WhatsApp: Villa del Parque -> VDP, Villa Crespo -> Crespo
const BARRIO_CORTO_ = { 'villa del parque': 'VDP', 'villa general mitre': 'Villa Mitre' };
function barrioCorto(b) {
  const t = String(b || '').trim(), n = norm_(t);
  if (BARRIO_CORTO_[n]) return BARRIO_CORTO_[n];
  return /^villa (crespo|devoto|urquiza|pueyrredon|ortuzar|luro|lugano|santa rita)$/.test(n) ? t.replace(/^villa\s+/i, '') : t;
}

function etiqueta(c) {
  const k = n => (num_(n) ? Math.round(num_(n) / 1000) + 'k' : '');
  const amb = (a, b) => (a ? (b && b != a ? a + '/' + b : a) + 'amb' : '');
  const t = s => String(s || '').replace(/Departamento/g, 'Depto').replace(/,\s*/g, '/');
  const z = s => String(s || '').split(',').map(barrioCorto).filter(Boolean).join(' ');
  const pago = { 'CASH': 'Cash', 'VENTA': 'c/venta', 'CREDITO APROBADO': 'Cred', 'CREDITO EN TRAMITE': 'Cred', 'CREDITO SIN CONFIRMAR': 'Cred', 'PARTE DE PAGO': 'Permuta' }[c['BUSCA FORMA DE PAGO']] || '';
  const partes = [];
  if (c['VENDE TIPO']) partes.push(['Vende', t(c['VENDE TIPO']), amb(c['VENDE AMB']), z(c['VENDE BARRIO']), k(c['VENDE PRECIO USD'])].filter(Boolean).join(' '));
  if (c['BUSCA TIPO'] || c['BUSCA BARRIOS']) partes.push(['Compra', t(c['BUSCA TIPO']), amb(c['BUSCA AMB MIN'], c['BUSCA AMB MAX']), z(c['BUSCA BARRIOS']), k(c['BUSCA HASTA USD']), pago].filter(Boolean).join(' '));
  return nombreBase_(c.NOMBRE) + (partes.length ? ' - ' + partes.join(' / ') : '');
}

// ─── ACCESO AL SHEET ─────────────────────────────────────────────────────────

function ss_() { return SpreadsheetApp.openById(SHEET_ID); }

function leer_() {
  const sh = ss_().getSheetByName('CONTACTOS');
  const vals = sh.getDataRange().getValues();
  const h = vals[0].map(x => String(x).trim());
  const filas = [];
  for (let i = 1; i < vals.length; i++) {
    if (!vals[i][h.indexOf('NOMBRE')]) continue;
    const o = { _fila: i + 1 };
    h.forEach((k, j) => (o[k] = vals[i][j]));
    if ('ESTADO' in o) o.ESTADO = estadoNuevo(o.ESTADO);
    if ('ID' in o) o.ID = idTxt(o.ID);
    if (ETAPA_VENTA_VIEJA[o['ETAPA VENTA']]) o['ETAPA VENTA'] = ETAPA_VENTA_VIEJA[o['ETAPA VENTA']];   // el Sheet guarda el telefono como numero; la app lo manda como texto
    filas.push(o);
  }
  return { sh, h, filas };
}

function escribir_(sh, h, fila, cambios) {
  Object.keys(cambios).forEach(k => {
    const j = h.indexOf(k);
    if (j >= 0) sh.getRange(fila, j + 1).setValue(cambios[k]);
  });
}

function asegurarIds_(sh, h, filas) {
  const j = h.indexOf('ID');
  filas.forEach(f => {
    if (f.ID) return;
    f.ID = normalizarTel(f.TELEFONO) || 'X' + Utilities.getUuid().slice(0, 8);
    sh.getRange(f._fila, j + 1).setValue(f.ID);
  });
}

function feriados_() {
  const sh = ss_().getSheetByName('FERIADOS');
  const set = new Set();
  if (sh) sh.getDataRange().getValues().slice(1).forEach(r => { const d = fecha_(r[0]); if (d) set.add(clave_(d)); });
  return set;
}

// Cada CODIGO puede repetirse en varias filas: cada fila es una variante.
// Las columnas se buscan por el titulo (CODIGO, CATEGORIA, SITUACION, TEXTO...): podés reordenarlas en el Sheet.
function plantillas_() {
  const vals = ss_().getSheetByName('MENSAJES').getDataRange().getValues();
  return agruparPlantillas(vals[0], vals.slice(1));
}

function agruparPlantillas(titulos, filas) {
  const col = t => titulos.findIndex(x => String(x).trim().toUpperCase().startsWith(t));
  const [iCod, iCat, iSit, iTxt, iReg] = ['CODIGO', 'CATEGORIA', 'SITUACION', 'TEXTO', 'REGLA'].map(col);
  const por = {};
  const orden = [];
  filas.filter(r => r[iCod] && r[iTxt]).forEach(r => {
    const k = String(r[iCod]).trim();
    const cat = String(r[iCat] || '').trim();
    if (!por[k]) { por[k] = { codigo: k, situacion: String(r[iSit] || ''), categoria: cat, variantes: [], enfoques: [] }; orden.push(k); }
    if (!por[k].categoria && cat) por[k].categoria = cat;
    if (!por[k].situacion && r[iSit]) por[k].situacion = String(r[iSit]);
    por[k].variantes.push(String(r[iTxt]));
    por[k].enfoques.push(iReg >= 0 ? String(r[iReg] || '') : '');
  });
  return orden.map(k => por[k]);
}

// Rotacion: la variante que toca es (veces que mandaste ese codigo) mod (cantidad de variantes).
function varianteQueToca(vecesUsado, total) { return total ? vecesUsado % total : 0; }

function listas_() {
  const sh = ss_().getSheetByName('BARRIOS');
  const barrios = sh ? sh.getRange('A2:A').getValues().map(r => String(r[0]).trim()).filter(Boolean) : [];
  return { barrios, acciones: ACCIONES, urgencias: URGENCIAS, motivaciones: MOTIVACIONES };
}

// IDs siempre como texto: 5491156564944 (numero en el Sheet) y "5491156564944" (de la app) son el mismo contacto
function idTxt(v) { return v === null || v === undefined ? '' : String(v).trim(); }
function historial_() { return ss_().getSheetByName('HISTORIAL').getDataRange().getValues().slice(1).map(x => (x[1] = idTxt(x[1]), x)); }

function log_(id, nombre, tipo, detalle, texto) {
  ss_().getSheetByName('HISTORIAL').appendRow([new Date(), id, nombre, tipo, detalle || '', texto || '']);
}

function hojaFichas_() { return ss_().getSheetByName('FICHAS') || ss_().getSheetByName('Fichas'); }   // acepta el nombre viejo

// Links al Sheet para el menu de la app (los IDs no van en el codigo publico de la app).
function links_() {
  const ss = ss_(), base = 'https://docs.google.com/spreadsheets/d/' + SHEET_ID + '/edit#gid=';
  return { contactos: base + ss.getSheetByName('CONTACTOS').getSheetId(), fichas: base + hojaFichas_().getSheetId() };
}

// Fichas que marcaste "Ya no está" desde la app. Van en una pestaña aparte para no tocar FICHAS (la escribe el generador).
function fichasBaja_() {
  const sh = ss_().getSheetByName('FICHAS BAJA');
  return new Set(sh ? sh.getDataRange().getValues().slice(1).map(r => norm_(r[0])).filter(Boolean) : []);
}
// ACMs de esta persona, desde la planilla índice. El nombre del ACM puede ser más corto ("Mery" = "Mery Gómez").
function mismaPersona(a, b) {
  const x = norm_(nombreBase_(a)), y = norm_(nombreBase_(b));
  return !!x && !!y && (x === y || x.startsWith(y + ' ') || y.startsWith(x + ' '));
}
function acmsDe_(c) {
  try {
    const sh = SpreadsheetApp.openById(ACM_INDICE_ID).getSheets()[0];
    const rg = sh.getDataRange(), v = rg.getValues(), rt = rg.getRichTextValues();
    const h = v[0].map(x => String(x).trim().toLowerCase()), col = t => h.findIndex(x => x.startsWith(t));
    const jN = col('nombre'), jD = col('direcci'), jF = col('fecha'), jP = col('nombre pdf');
    return v.slice(1).map((r, i) => ({ r, link: jP >= 0 && rt[i + 1][jP] ? rt[i + 1][jP].getLinkUrl() : '' }))
      .filter(x => mismaPersona(x.r[jN], c.NOMBRE))
      .map(x => ({ fecha: x.r[jF] instanceof Date ? txt_(x.r[jF]) : String(x.r[jF] || ''), direccion: String(x.r[jD] || ''), link: x.link || '' }));
  } catch (e) { return []; }   // si la planilla no está o no hay permiso, la ficha igual abre
}

function api_fichaBaja(link) {
  if (!link) throw new Error('Esa ficha no tiene link');
  let sh = ss_().getSheetByName('FICHAS BAJA');
  if (!sh) { sh = ss_().insertSheet('FICHAS BAJA'); sh.appendRow(['LINK', 'FECHA']); }
  sh.appendRow([link, new Date()]);
  return true;
}

// Placas armadas en Canva: pestaña PLACAS (BARRIO, TIPO, AMB MIN, AMB MAX, USD DESDE, USD HASTA, LINK DRIVE, FECHA, NOTAS)
function placas_() {
  const sh = ss_().getSheetByName('PLACAS');
  if (!sh) return [];
  const v = sh.getDataRange().getValues(), h = v[0].map(x => String(x).trim()), ix = n => h.indexOf(n);
  return v.slice(1).filter(r => r[ix('BARRIO')] && /^https?:/.test(String(r[ix('LINK DRIVE')]))).map(r => ({
    barrio: String(r[ix('BARRIO')]), tipo: String(r[ix('TIPO')] || ''), min: num_(r[ix('AMB MIN')]), max: num_(r[ix('AMB MAX')]),
    desde: num_(r[ix('USD DESDE')]), hasta: num_(r[ix('USD HASTA')]), link: String(r[ix('LINK DRIVE')]) }));
}
// La placa que le sirve a este vendedor: mismo barrio, tipo, ambientes dentro del rango y precio dentro del rango (si están)
function placaCoincide(pl, c) {
  if (barrioN(pl.barrio) !== barrioN(c['VENDE BARRIO'])) return false;
  if (pl.tipo && c['VENDE TIPO'] && !lista_(c['VENDE TIPO']).map(tipoN_).some(t => lista_(pl.tipo).map(tipoN_).includes(t))) return false;
  const amb = num_(c['VENDE AMB']), usd = num_(c['VENDE PRECIO USD']);
  if (amb && pl.min && (amb < pl.min || amb > (pl.max || pl.min))) return false;
  if (usd && ((pl.desde && usd < pl.desde) || (pl.hasta && usd > pl.hasta))) return false;
  return true;
}
function placaPara_(c, placas) { const p = placas.find(pl => placaCoincide(pl, c)); return p ? p.link : ''; }

function fichas_() {
  const sh = hojaFichas_();
  const vals = sh.getDataRange().getValues();
  const h = vals[0].map(x => String(x).trim());
  const ix = n => h.indexOf(n);
  const iAct = ix('ACTIVA');
  const baja = fichasBaja_();
  return vals.slice(1).filter(r => r[ix('BARRIO')] && !baja.has(norm_(r[ix('LINK NL')]))).map(r => ({
    direccion: String(r[ix('DIRECCIÓN')] || ''), barrio: String(r[ix('BARRIO')]), tipo: String(r[ix('TIPO')] || ''),
    amb: num_(r[ix('AMB')]), usd: num_(r[ix('PRECIO USD')]), link: String(r[ix('LINK NL')] || ''),
    clientes: String(r[ix('CLIENTE')] || '').split(',').map(norm_).filter(Boolean), activa: iAct < 0 ? '' : norm_(r[iAct])
  }));
}

function matches_(c, todos, fichas) {
  const out = [];
  const b = busca_(c);
  if (b.barrios.length) {
    todos.forEach(o => {
      if (o.ID === c.ID || !o['VENDE TIPO'] || o.ESTADO === 'DESCARTADO') return;
      if (coincide(b, { tipo: o['VENDE TIPO'], barrio: o['VENDE BARRIO'], amb: num_(o['VENDE AMB']), usd: num_(o['VENDE PRECIO USD']) }))
        out.push({ tipo: 'Vendedor', texto: o.NOMBRE + ': ' + o['VENDE TIPO'] + ' ' + o['VENDE BARRIO'], id: o.ID });
    });
    const yo = norm_(nombreBase_(c.NOMBRE));
    const enviadas = [];
    fichas.forEach(f => {
      if (f.activa === 'no') return;
      const ya = !!yo && f.clientes.some(x => norm_(nombreBase_(x)) === yo);
      if (coincide(b, f) || ya) (ya ? enviadas : out).push({ tipo: ya ? 'Ficha ya enviada' : 'Ficha', enviada: ya,
        texto: f.tipo + ' ' + f.amb + ' amb, ' + f.direccion + ', ' + f.barrio + ' USD ' + f.usd, link: f.link, direccion: [f.direccion, f.barrio].filter(Boolean).join(', ') });
    });
    out.push(...enviadas);   // las ya enviadas van al final
  } else {
    const yo = norm_(c.NOMBRE);
    fichas.forEach(f => { if (yo && f.clientes.some(x => norm_(nombreBase_(x)) === yo)) out.push({ tipo: 'Ficha ya enviada', enviada: true,
      texto: f.tipo + ' ' + f.amb + ' amb, ' + f.direccion + ', ' + f.barrio + ' USD ' + f.usd, link: f.link, direccion: [f.direccion, f.barrio].filter(Boolean).join(', ') }); });
  }
  if (c['VENDE TIPO'] && c['VENDE BARRIO']) {
    const p = { tipo: c['VENDE TIPO'], barrio: c['VENDE BARRIO'], amb: num_(c['VENDE AMB']), usd: num_(c['VENDE PRECIO USD']) };
    todos.forEach(o => {
      if (o.ID === c.ID || ['DESCARTADO', 'CLIENTE'].includes(o.ESTADO)) return;
      if (coincide(busca_(o), p)) out.push({ tipo: 'Comprador', texto: o.NOMBRE + ': busca ' + o['BUSCA TIPO'] + ' ' + o['BUSCA BARRIOS'], id: o.ID });
    });
  }
  return out;
}

// Compradores reales del CRM para lo que vende c: exactos (matching) y, si no hay, los que buscan en ese barrio.
function compradoresPara_(c, filas) {
  if (!c['VENDE BARRIO']) return { exactos: 0, zona: 0 };
  const p = { tipo: c['VENDE TIPO'], barrio: c['VENDE BARRIO'], amb: num_(c['VENDE AMB']), usd: num_(c['VENDE PRECIO USD']) };
  const activos = filas.filter(o => o.ID !== c.ID && !['DESCARTADO', 'CLIENTE'].includes(o.ESTADO));
  const exactos = activos.filter(o => coincide(busca_(o), p)).length;
  const b = barrioN(c['VENDE BARRIO']);
  const zona = activos.filter(o => busca_(o).barrios.includes(b)).length;
  return { exactos, zona };
}


// ─── API PARA LA APP ─────────────────────────────────────────────────────────

// La pantalla vive en nahuelim.com.ar/crm. Esta URL solo responde a pedidos con la clave.
function doGet() { return ContentService.createTextOutput('CRM Nahuel'); }

const API_ = { api_semana, api_editarHist, api_cartera, api_opciones, api_fichaBaja, api_lista, api_lote, api_hoy, api_buscar, api_ficha, api_accion, api_guardar, api_nuevo, api_contactoGoogle, api_evento, api_estadisticas, api_captura };

function claveOk_(k) {
  const real = PropertiesService.getScriptProperties().getProperty('CRM_KEY');
  if (!real || typeof k !== 'string' || k.length !== real.length) return false;
  let dif = 0;
  for (let i = 0; i < real.length; i++) dif |= real.charCodeAt(i) ^ k.charCodeAt(i);
  return dif === 0;
}

function doPost(e) {
  const out = o => ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
  let req;
  try { req = JSON.parse(e.postData.contents); } catch (err) { return out({ ok: false, error: 'pedido invalido' }); }
  if (!claveOk_(req.k)) { Utilities.sleep(1500); return out({ ok: false, error: 'no autorizado' }); }
  const fn = API_[req.fn];
  if (!fn) return out({ ok: false, error: 'funcion desconocida' });
  try { return out({ ok: true, data: fn.apply(null, req.args || []) }); }
  catch (err) { return out({ ok: false, error: err.message }); }
}

// Correr UNA vez: crea la clave y la muestra en el Registro de ejecucion. Copiala a la app y no la compartas.
function generarClave() {
  const k = (Utilities.getUuid() + Utilities.getUuid()).replace(/-/g, '');
  PropertiesService.getScriptProperties().setProperty('CRM_KEY', k);
  console.log('Tu clave del CRM (copiala en la app): ' + k);
}

function txt_(d) { return d ? Utilities.formatDate(d, Session.getScriptTimeZone(), 'dd/MM/yyyy') : ''; }

// Contacto de relacion: dias de atraso si ya le toca (0 = hoy), o null si no le toca o no tiene nivel.
// Cuenta desde el ultimo contacto; si nunca hubo, desde el alta; si no hay ninguna fecha, le toca ya.
function relacionToca(nivel, ult, alta, hoy) {
  const dias = RELACION_DIAS[String(nivel || '').trim().toUpperCase()];
  if (!dias) return null;
  const base = ult || alta;
  if (!base) return 0;
  const atraso = Math.round((hoy - base) / 86400000) - dias;   // ojo: diasDesdeFecha es para aniversarios, ignora el año
  return atraso >= 0 ? atraso : null;
}

// Contexto para cada tarjeta: la ultima nota y el ultimo contacto (hist va de lo mas viejo a lo mas nuevo)
function contexto_(hist) {
  const ctx = {};
  const tz = Session.getScriptTimeZone();
  hist.forEach(x => {
    const o = ctx[x[1]] = ctx[x[1]] || {};
    if ((x[3] === 'NOTA' || x[3] === 'CONTACTO') && x[5]) o.nota = String(x[5]).slice(0, 110);
    if (TIPOS_CONTACTO.includes(x[3])) o.ultimo = Utilities.formatDate(new Date(x[0]), tz, 'dd/MM') + ' · ' + ({ LLAMADA_NO: 'no contestó', LLAMADA_SI: 'contestó', RESPONDIO: 'contestó', MENSAJE: 'mensaje ' + x[4], REVISION: 'revisión', DESCARTAR: 'archivado', CONTACTO: String(x[4] || '').toLowerCase() }[x[3]] || x[3]);
  });
  return ctx;
}

function contactadosHoy(hist, hoy) {
  const ids = new Set();
  hist.forEach(x => {
    const f = fecha_(x[0]);
    if (!f || f.getTime() !== hoy.getTime() || !TIPOS_CONTACTO.includes(x[3])) return;
    if (x[3] === 'MENSAJE' && /^(CUMPLE|ANIV)/.test(String(x[4]))) return;
    ids.add(x[1]);
  });
  return ids.size;
}
const TIPOS_CONTACTO = ['LLAMADA_NO', 'LLAMADA_SI', 'RESPONDIO', 'MENSAJE', 'REVISION', 'DESCARTAR', 'CONTACTO'];

// Prioridad por forma de pago: 1-2 estar encima; 3 buscar y estar atento; 4-5 cuando hay tiempo. Sin dato: 0.
const PRIORIDAD_PAGO = { 'PARTE DE PAGO': 1, 'VENTA': 1, 'CASH': 2, 'CREDITO APROBADO': 3, 'CREDITO EN TRAMITE': 4, 'CREDITO SIN CONFIRMAR': 5 };
function prioridad(pago) { return PRIORIDAD_PAGO[String(pago || '').trim().toUpperCase()] || 0; }

const diasEntre = (a, b) => Math.round((b - a) / 86400000);

// Comprador EN CONTACTO: si le toca hoy y por qué. inf = { ultimo, opciones, noGusto, nuevos, enviadas } (fechas o null).
function compradorHoy(c, inf, hoy) {
  const p = fecha_(c['PROX CONTACTO']);
  const dias = inf.ultimo ? diasEntre(inf.ultimo, hoy) : 999;
  const califica = !!(c['BUSCA TIPO'] && c['BUSCA FORMA DE PAGO']);
  const temp = String(c.TEMPERATURA || '').toUpperCase();
  const ritmo = RITMO[temp] || RITMO.TIBIO;
  const lim = fecha_(c['FECHA LIMITE']);
  const faltan = lim ? diasEntre(hoy, lim) : null;
  const urgente = faltan !== null && faltan <= DIAS_URGENTE;
  const sinOpciones = !inf.opciones && !inf.enviadas;
  const deuda = califica && dias >= 1 && (sinOpciones || (inf.noGusto && (!inf.opciones || inf.noGusto > inf.opciones)));
  let porque = '', jugada = '', codigo = '', tipo = 'comprador';
  if (p && p > hoy && !deuda) return null;                       // lo agendaste a mano para más adelante
  if (p && p <= hoy) porque = 'Agendado' + (c['PROX ACCION'] ? ': ' + c['PROX ACCION'] : '');
  else if (!califica) {
    if (dias < RITMO.TIBIO[0]) return null;
    tipo = 'calificar';
    porque = 'Falta saber ' + [!c['BUSCA TIPO'] ? 'qué busca' : '', !c['BUSCA FORMA DE PAGO'] ? 'cómo paga' : ''].filter(Boolean).join(' y ');
  } else if (deuda) porque = sinOpciones ? 'Ya sabés qué busca y no le mandaste opciones' : 'No le gustó lo último y no le mandaste más';
  else if (urgente && dias >= 1) porque = (faltan < 0 ? 'Se le pasó la fecha límite' : 'Fecha límite en ' + faltan + (faltan === 1 ? ' día' : ' días')) + (c['MOTIVO LIMITE'] && c['MOTIVO LIMITE'] !== ESTIMADA ? ' (' + c['MOTIVO LIMITE'] + ')' : '');
  else if (dias >= ritmo[0]) porque = (temp ? temp.charAt(0) + temp.slice(1).toLowerCase() : 'Sin temperatura (como tibio)') + ': le toca cada ' + ritmo[0] + '-' + ritmo[1] + ' días' + (dias < 999 ? ' y van ' + dias : '') + (dias > ritmo[1] && dias < 999 ? ' · atrasado' : '');
  else return null;
  if (tipo === 'calificar') { jugada = !c['BUSCA TIPO'] ? 'Calificar: qué busca, zona y presupuesto' : 'Calificar: cómo paga'; codigo = !c['BUSCA TIPO'] ? 'XMSJ' : 'PAGO'; }
  else if (inf.nuevos) { jugada = 'Mandarle opciones: hay ' + inf.nuevos + (inf.nuevos === 1 ? ' match' : ' matches') + ' sin mandar (verificá que sigan activas)'; }
  else if (deuda) { jugada = 'Buscarle opciones (ver "Dónde buscar" en Búsqueda)'; }
  else if (inf.opciones && inf.ultimo && inf.ultimo <= inf.opciones) { jugada = 'Preguntarle si alguna se acerca a lo que busca'; codigo = 'OPC'; }   // si tampoco contesta, a mano: C3
  else { jugada = 'Avisarle que seguís buscando (y buscar algo nuevo)'; codigo = 'SIGO'; }
  return { tipo, porque, jugada, codigo, deuda, urgente, faltan, dias, atrasado: dias > ritmo[1] && dias < 999 };
}

// Vendedor: si le toca hoy y por qué. ultimo = último contacto o revisión.
function vendedorHoy(c, ultimo, hoy) {
  const etapa = String(c['ETAPA VENTA'] || '');
  const p = fecha_(c['PROX CONTACTO']);
  if (p && p > hoy) return null;
  if (p && p <= hoy) return { porque: 'Agendado' + (c['PROX ACCION'] ? ': ' + c['PROX ACCION'] : ''), jugada: c['PROX ACCION'] || 'Contacto con el propietario', codigo: '' };
  const dias = ultimo ? diasEntre(ultimo, hoy) : 999;
  if (DIAS_VENDEDOR[etapa]) {
    if (dias < DIAS_VENDEDOR[etapa]) return null;
    const desde = dias < 999 ? ' (van ' + dias + ' días)' : '';
    if (etapa === 'EN VENTA') return { porque: 'En venta: contacto cada 2 semanas' + desde, jugada: 'Contarle cómo viene la venta', codigo: '' };
    if (etapa === 'CAPTAR') return { porque: 'Para captar: una vez por semana' + desde, jugada: 'Conseguir el prelisting', codigo: 'V1' };
    return { porque: etapa === 'ACM' ? 'ACM entregado: seguimiento semanal' + desde : 'Prelisting: seguimiento semanal' + desde, jugada: 'Ver qué dudas le quedaron', codigo: etapa === 'ACM' ? 'V2' : 'V2B' };
  }
  if (etapa !== 'NO CAPTADA' && etapa !== 'CON OTRA INMO') return null;
  const base = fecha_(c['FECHA PRELISTING']) || fecha_(c['OTRA INMO DESDE']) || fecha_(c['FECHA ALTA']) || hoy;
  const desde = diasEntre(base, hoy);
  const fin = fecha_(c['FIN AUTORIZACION']);
  if (fin && diasEntre(hoy, fin) <= 15 && diasEntre(hoy, fin) >= -3 && (!ultimo || diasEntre(sumarDias_(fin, -15), ultimo) < 0))
    return { porque: 'Se le termina la autorización el ' + ddmm_(fin), jugada: 'Proponerle juntarse y revalorizar', codigo: 'V3E' };
  const hitos = etapa === 'NO CAPTADA' ? HITOS_NO_CAPTADA : HITOS_CON_OTRA;
  const hito = hitos.filter(m => m <= desde).pop();
  if (hito === undefined) return null;
  if (ultimo && diasEntre(sumarDias_(base, hito), ultimo) >= 0) {
    if (hito < 120) return null;
    return dias >= DIAS_REVIVIR ? { revivir: true, porque: 'Pasaron los 120 días sin captarlo', jugada: 'Ver cómo sigue con la venta', codigo: 'V3A' } : null;
  }
  if (hito <= 60) return { porque: 'Día ' + hito + ' desde el prelisting', jugada: 'Revisar si lo publicó con otra inmobiliaria ("Buscar en portales")', codigo: '', revisar: true };
  return { porque: 'Día ' + hito + ' desde el prelisting', jugada: etapa === 'CON OTRA INMO' ? 'Chequear que siga a la venta y preguntarle cómo viene' : 'Preguntarle cómo sigue con la idea de vender',
    codigo: etapa === 'CON OTRA INMO' ? 'V3B' : 'V3A' };
}

// Chip de urgencia -> fecha límite estimada (solo si no cargaste una fecha exacta)
function limiteDesdeUrgencia(urgencia, c, hoy) {
  if (c['FECHA LIMITE'] && c['MOTIVO LIMITE'] !== ESTIMADA) return {};   // cargaste una fecha exacta: no se pisa
  const d = PLAZO_URGENCIA[urgencia];
  return d ? { 'FECHA LIMITE': sumarDias_(hoy, d), 'MOTIVO LIMITE': ESTIMADA } : { 'FECHA LIMITE': '', 'MOTIVO LIMITE': '' };
}

function item_(c, hoy, extra) {
  const p = fecha_(c['PROX CONTACTO']);
  return Object.assign({
    id: c.ID, nombre: String(c.NOMBRE), estado: c.ESTADO,
    accion: c['PROX ACCION'] === 'Mensaje' && num_(c.INTENTO) >= LLAMADAS ? 'Mensaje ' + (num_(c.INTENTO) - LLAMADAS + 1) : String(c['PROX ACCION'] || ''),
    prox: txt_(p), vencido: !!(p && p < hoy), tel: !!normalizarTel(c.TELEFONO), temp: c.TEMPERATURA || '',
    intento: num_(c.INTENTO), prio: prioridad(c['BUSCA FORMA DE PAGO']),
    fuente: String(c.FUENTE || ''), alta: c['FECHA ALTA'] ? txt_(fecha_(c['FECHA ALTA'])) : '',
    resumen: String(etiqueta(c)).split(' - ').slice(1).join(' - '), pago: String(c['BUSCA FORMA DE PAGO'] || ''), consulto: String(c['CONSULTO POR'] || ''),
    diasSin: fecha_(c['ULT CONTACTO']) ? diasEntre(fecha_(c['ULT CONTACTO']), hoy) : null
  }, extra || {});
}

// Lo que pasó con cada contacto, sacado del HISTORIAL una sola vez: opciones mandadas, "no le gustó", revisiones.
function indiceHist_(hist) {
  const ix = {};
  hist.forEach(x => {
    const o = ix[x[1]] = ix[x[1]] || { links: new Set() };
    const f = new Date(x[0]);
    if (x[3] === 'OPCIONES') { o.opciones = f; String(x[5] || '').split('\n').forEach(l => l.split('|').forEach(t => { t = norm_(t); if (t) o.links.add(t); })); }
    if (x[3] === 'NO_GUSTO') o.noGusto = f;
    if (x[3] === 'REVISION') o.revision = f;
  });
  return ix;
}
const VACIO_ = { links: new Set() };

function infoComprador_(c, ix, filas, fichas) {
  const o = ix[c.ID] || VACIO_;
  const ms = matches_(c, filas, fichas);
  const enviada = m => m.enviada || (m.link && o.links.has(norm_(m.link)));
  return { ultimo: fecha_(c['ULT CONTACTO']), opciones: o.opciones || null, noGusto: o.noGusto || null,
    nuevos: ms.filter(m => m.tipo !== 'Comprador' && !enviada(m)).length, enviadas: ms.filter(enviada).length };
}
function ultimoVendedor_(c, ix) {
  const u = fecha_(c['ULT CONTACTO']), rv = (ix[c.ID] || {}).revision;
  const r = rv ? fecha_(rv) : null;
  return u && r ? (u > r ? u : r) : (u || r);
}
const ETAPAS_VENDEDOR_HOY = ['CAPTAR', 'PRELISTING', 'ACM', 'NO CAPTADA', 'CON OTRA INMO', 'EN VENTA'];

// Saludo de las fiestas: el día después (Navidad desde el 26/12, Año Nuevo desde el 2/1)
function fiestaHoy(hoy) {
  const m = hoy.getMonth(), d = hoy.getDate();
  if (m === 11 && d >= 26) return { codigo: 'NAV', desde: new Date(hoy.getFullYear(), 11, 25) };
  if (m === 0 && d >= 2 && d <= 10) return { codigo: 'ANO', desde: new Date(hoy.getFullYear(), 0, 1) };
  return null;
}
const FIESTAS_POR_DIA = 20;
// Quién recibe el saludo, en orden: clientes, amigos, conocidos, referidos, relación A/B/C. 0 = no recibe.
function prioridadFiesta(c) {
  if (c.ESTADO === 'DESCARTADO') return 0;
  if (c.ESTADO === 'CLIENTE') return 1;
  const f = { Amigo: 2, Conocido: 3, Referido: 4 }[String(c.FUENTE || '')];
  if (f) return f;
  const r = { A: 5, B: 6, C: 7 }[String(c.RELACION || '').toUpperCase()];
  return r || 0;
}
// Paso que deja el CRM al 3er "no contestó" seguido: se sugiere el mensaje NOAT
const noAtiende = c => String(c['PROX ACCION'] || '').startsWith('No atiende');
// Próximo paso que pusiste vos (con texto y día): manda sobre las sugerencias
const manual = c => !!fecha_(c['PROX DEFINIDO']) && !!fecha_(c['PROX CONTACTO']);
// Orden de "Estate atento": vendedores, esperan opciones, calientes, tibios (y sin temperatura), fecha límite cerca, fríos, por calificar
function rangoAtento(x) {
  if (x.etapa) return 0;
  if (x.tipo === 'calificar') return 6;
  if (x.deuda) return 1;
  const t = String(x.temp || '').toUpperCase();
  if (t === 'CALIENTE') return 2;
  if (t !== 'FRIO' && t !== 'FRÍO') return 3;
  return x.urgente ? 4 : 5;
}

function api_hoy() {
  const { sh, h, filas } = leer_();
  asegurarIds_(sh, h, filas);
  const hoy = hoy_();
  const vence = c => { const p = fecha_(c['PROX CONTACTO']); return !p || p <= hoy; };
  const r = { version: VERSION, links: links_(), fechas: [], fiestas: [], proximos: [], opciones: [], llamar: [], mensajes: [], atento: [], relacion: [], revivir: [], sinTel: 0, incompletos: 0 };
  const fichas = fichas_(), placas = placas_(), plant = {};
  plantillas_().forEach(p => (plant[p.codigo] = p));
  const hist = historial_(), ix = indiceHist_(hist), ctx = contexto_(hist);
  const esHoy = x => { const f = fecha_(x[0]); return f && f.getTime() === hoy.getTime(); };
  const usado = new Set();
  // Con las opciones del mensaje ya completas, para mandar sin abrir la ficha
  const conTextos = (it, c, codigo, extra) => {
    const p = plant[codigo];
    if (p) it.opciones = p.variantes.map((t, k) => ({ texto: rellenar(t, c, codigo, extra || {}), enfoque: (p.enfoques || [])[k] || '' }));
    it.codigo = codigo; it.wa = normalizarTel(c.TELEFONO);
    return it;
  };
  const sinHablar = c => { const u = fecha_(c['ULT CONTACTO']); return u ? diasEntre(u, hoy) : null; };
  const tarjeta = (c, extra) => { usado.add(c.ID); return Object.assign(item_(c, hoy, { diasSin: sinHablar(c), wa: normalizarTel(c.TELEFONO) }), ctx[c.ID] || {}, extra || {}); };
  const fiesta = fiestaHoy(hoy), candidatosFiesta = [];

  const etapaV = h.indexOf('ETAPA VENTA');
  filas.forEach(c => {
    const e = c.ESTADO;
    if (!c['ETAPA VENTA'] && ['EN CONTACTO', 'NUEVO', 'CLIENTE'].includes(e) && (c['VENDE TIPO'] || PAGO_CON_VENTA.includes(c['BUSCA FORMA DE PAGO'])) && etapaV >= 0) {
      c['ETAPA VENTA'] = 'CAPTAR';
      sh.getRange(c._fila, etapaV + 1).setValue('CAPTAR');
    }
    if (e !== 'DESCARTADO' && e !== 'EN PAUSA' && !normalizarTel(c.TELEFONO)) r.sinTel++;
    if (incompleto(c)) r.incompletos++;
    // Cumpleaños: el día después (hasta 3 días). Aniversario de compra: ese día (hasta 3 días).
    [['CUMPLEANOS', 'CUMPLE', 'Cumpleaños', 1], ['FECHA COMPRA', 'ANIV', 'Aniversario de compra', 0]].forEach(([col, cod, txt, desde]) => {
      const atraso = diasDesdeFecha(fecha_(c[col]), hoy);
      if (atraso === null || atraso < desde || atraso > DIAS_FECHAS) return;
      if (hist.some(x => x[1] === c.ID && x[3] === 'MENSAJE' && String(x[4]).startsWith(cod) && new Date(x[0]) >= sumarDias_(hoy, -atraso))) return;   // ya lo mandaste
      r.fechas.push(conTextos(Object.assign(item_(c, hoy, { accion: txt + (atraso ? (atraso === 1 ? ' (fue ayer)' : ' (fue hace ' + atraso + ' días)') : ' (hoy)') }), ctx[c.ID] || {}), c, cod, { cuando: atraso === 1 ? 'ayer' : 'hace unos días' }));
    });
    if (fiesta && normalizarTel(c.TELEFONO) && prioridadFiesta(c) && !hist.some(x => x[1] === c.ID && x[3] === 'MENSAJE' && String(x[4]).startsWith(fiesta.codigo) && new Date(x[0]) >= fiesta.desde))
      candidatosFiesta.push(c);
    if (e === 'DESCARTADO') return;

    // 1. Tus próximos pasos de hoy (los que pusiste vos)
    if (manual(c)) {
      if (vence(c)) {
        const def = fecha_(c['PROX DEFINIDO']);
        const t = tarjeta(c, { porque: String(c['PROX ACCION'] || 'Próximo paso'), canal: String(c['PROX CANAL'] || ''), hora: horaTxt_(c['PROX HORA']),
          definidoHace: def ? diasEntre(def, hoy) : null, atrasado: diasEntre(fecha_(c['PROX CONTACTO']), hoy) });
        r.proximos.push(noAtiende(c) ? conTextos(t, c, 'NOAT') : t);
      }
      return;
    }
    // 2. Leads nuevos: llamadas y mensajes de la cadencia
    if (ESTADOS_CADENCIA.includes(e)) {
      if (!vence(c)) return;
      const n = num_(c.INTENTO), sig = siguienteToque(n) || {};
      if (n < LLAMADAS) r.llamar.push(tarjeta(c, { alta_: (fecha_(c['FECHA ALTA']) || 0).valueOf(), porque: 'Llamada ' + (n + 1) + ' de 3', jugada: '' }));
      else {
        const cod = sig.codigo === 'CAD1' && FUENTES_PROPIAS.includes(String(c.FUENTE)) ? 'IG1' : sig.codigo;
        r.mensajes.push(conTextos(tarjeta(c, { alta_: (fecha_(c['FECHA ALTA']) || 0).valueOf(), porque: 'Mensaje ' + (n - LLAMADAS + 1) + ' de ' + CADENCIA.length, jugada: '' }), c, cod));
      }
      return;
    }
    // 3. Vendedores, según su etapa
    if (ETAPAS_VENDEDOR_HOY.includes(c['ETAPA VENTA'])) {
      const v = vendedorHoy(c, ultimoVendedor_(c, ix), hoy);
      if (v && v.revivir) { r.revivir.push(conTextos(tarjeta(c, { porque: v.porque, jugada: v.jugada, orden: fecha_(c['ULT CONTACTO']) || fecha_(c['FECHA ALTA']) }), c, 'V3A')); return; }
      if (v) {
        const placa = placaPara_(c, placas), comp = compradoresPara_(c, filas);
        if (!v.revisar && placa && ['CAPTAR', 'NO CAPTADA', 'CON OTRA INMO', 'ACM', 'PRELISTING'].includes(c['ETAPA VENTA'])) v.jugada += ' · tenés placa para mandarle';
        else if (!v.revisar && comp.exactos && ['CAPTAR', 'NO CAPTADA', 'CON OTRA INMO'].includes(c['ETAPA VENTA'])) { v.jugada += ' · hay ' + comp.exactos + (comp.exactos === 1 ? ' comprador' : ' compradores') + ' para su zona'; if (v.codigo === 'V3A') v.codigo = 'V3D'; }
        r.atento.push(tarjeta(c, { porque: v.porque, jugada: v.jugada, codigo: v.codigo, etapa: c['ETAPA VENTA'], placa: placa || '' }));
        return;
      }
    }
    // 4. Compradores: a los calientes y tibios con opciones pendientes, antes que nada; el resto, a "Estate atento"
    if (e === 'EN CONTACTO' || (e === 'CLIENTE' && fecha_(c['PROX CONTACTO']))) {
      const k = compradorHoy(c, infoComprador_(c, ix, filas, fichas), hoy);
      if (!k) return;
      const t = tarjeta(c, Object.assign(k, { prox: '' }));
      if (k.deuda && ['CALIENTE', 'TIBIO'].includes(String(c.TEMPERATURA || '').toUpperCase())) r.opciones.push(t); else r.atento.push(t);
      return;
    }
    // 6. Revivir: recontactos de los que están en pausa (con fecha vencida) y la base vieja (sin fecha)
    if (e === 'EN PAUSA' && normalizarTel(c.TELEFONO) && vence(c)) {
      const conFecha = !!fecha_(c['PROX CONTACTO']);
      r.revivir.push(conTextos(tarjeta(c, { porque: conFecha ? 'Recontacto: te dejó de contestar' : 'Base vieja: nunca contestó',
        jugada: '¿Sigue buscando o ya resolvió?', orden: fecha_(c['ULT CONTACTO']) || fecha_(c['FECHA ALTA']), prox: '' }), c, conFecha ? 'A1' : (c['BUSCA TIPO'] || c['BUSCA BARRIOS'] ? 'R2' : 'R1')));
    }
  });

  r.proximos.sort((a, b) => (b.atrasado || 0) - (a.atrasado || 0) || (a.hora || '99').localeCompare(b.hora || '99') || ((a.prio || 3.5) - (b.prio || 3.5)));
  r.opciones.sort((a, b) => (String(a.temp).toUpperCase() === 'CALIENTE' ? 0 : 1) - (String(b.temp).toUpperCase() === 'CALIENTE' ? 0 : 1) || ((a.prio || 3.5) - (b.prio || 3.5)));
  // Leads: los más nuevos arriba (cuanto antes lo contactás, más chances de que atienda)
  [r.llamar, r.mensajes].forEach(xs => { xs.sort((a, b) => b.alta_ - a.alta_); xs.forEach(x => delete x.alta_); });
  r.atento.sort((a, b) => rangoAtento(a) - rangoAtento(b) || ((a.urgente ? a.faltan : 999) - (b.urgente ? b.faltan : 999)) || ((a.prio || 3.5) - (b.prio || 3.5)) || ((b.dias || 0) - (a.dias || 0)));

  // Fiestas: hasta 20 por día, en orden de prioridad
  if (fiesta) {
    const yaHoy = hist.filter(x => esHoy(x) && x[3] === 'MENSAJE' && String(x[4]).startsWith(fiesta.codigo)).length;
    r.fiestas = candidatosFiesta.sort((a, b) => prioridadFiesta(a) - prioridadFiesta(b)).slice(0, Math.max(0, FIESTAS_POR_DIA - yaHoy))
      .map(c => conTextos(Object.assign(item_(c, hoy, { accion: fiesta.codigo === 'NAV' ? 'Saludo de Navidad' : 'Saludo de Año Nuevo' }), ctx[c.ID] || {}), c, fiesta.codigo, { anio: hoy.getFullYear() }));
    r.fiestasPendientes = candidatosFiesta.length;
  }

  // Relación (máximo 5 por día), los que no aparecen en otro bloque
  const relHoy = hist.filter(x => esHoy(x) && x[3] === 'MENSAJE' && String(x[4]).startsWith('REL')).length;
  const rel = filas.filter(c => c.ESTADO !== 'DESCARTADO' && normalizarTel(c.TELEFONO) && !usado.has(c.ID))
    .map(c => ({ c, atraso: relacionToca(c.RELACION, fecha_(c['ULT CONTACTO']), fecha_(c['FECHA ALTA']), hoy) }))
    .filter(x => x.atraso !== null);
  r.relacionPendientes = rel.length;
  r.relacion = rel.sort((a, b) => String(a.c.RELACION).localeCompare(String(b.c.RELACION)) || b.atraso - a.atraso)
    .slice(0, Math.max(0, RELACION_POR_DIA - relHoy))
    .map(x => conTextos(Object.assign(item_(x.c, hoy, { porque: 'Relación ' + String(x.c.RELACION).toUpperCase() + ': cada ' + RELACION_DIAS[String(x.c.RELACION).toUpperCase()] + ' días', jugada: 'Saludar, sin vender nada', prox: '' }), ctx[x.c.ID] || {}), x.c, 'REL'));

  // Revivir: del más viejo al más nuevo, con tope de seguridad por día
  r.revividosHoy = hist.filter(x => esHoy(x) && x[3] === 'MENSAJE' && /^(R\d|A1|V3A)/.test(String(x[4]))).length;
  r.revivirPendientes = r.revivir.length;
  r.revivir = r.revivir.sort((a, b) => (a.orden || 0) - (b.orden || 0)).slice(0, Math.max(0, REVIVIR_POR_DIA - r.revividosHoy));
  r.revivir.forEach(x => delete x.orden);

  try { r.visitas = visitas_(filas, hist, hoy); } catch (e) { r.visitas = []; }   // si Calendar falla, Hoy igual carga
  return r;
}

// El Guardar de cada solapa: todo en un solo viaje. Orden: la accion (si hay), los campos, la nota y el proximo paso
// (lo que elegiste a mano pisa lo que calcula la accion).
// Operacion cerrada: compra CERRADA o venta VENDIDA -> CLIENTE. En la compra, ademas, la fecha para el aniversario.
// Lo que se calcula solo al guardar: vendedor (fecha de prelisting, estado, aviso de salida a la venta) y urgencia -> fecha límite.
function alGuardar(set, c, hoy) {
  const r = {};
  const etapa = set['ETAPA VENTA'];
  if (etapa && etapa !== c['ETAPA VENTA']) {
    const pre = c['FECHA PRELISTING'] || set['FECHA PRELISTING'], desde = c['OTRA INMO DESDE'] || set['OTRA INMO DESDE'];
    if (etapa === 'NO CAPTADA' && !pre) r['FECHA PRELISTING'] = hoy;
    // Con otra sin prelisting tuyo: el calendario se cuenta desde que la publicaron (si no lo sabés, desde hoy)
    if (etapa === 'CON OTRA INMO' && !pre && !desde) r['OTRA INMO DESDE'] = hoy;
    if (etapa === 'EN VENTA') { r['PROX CONTACTO'] = hoy; r['PROX ACCION'] = 'Avisarle que salimos a la venta'; }
    if (ETAPAS_VENDEDOR_HOY.includes(etapa) && ['NUEVO', 'EN PAUSA'].includes(c.ESTADO) && !set.ESTADO) r.ESTADO = 'EN CONTACTO';
  }
  if ('URGENCIA' in set && !('FECHA LIMITE' in set)) Object.assign(r, limiteDesdeUrgencia(set.URGENCIA, c, hoy));
  if (set['FECHA LIMITE'] && !set['MOTIVO LIMITE'] && c['MOTIVO LIMITE'] === ESTIMADA) r['MOTIVO LIMITE'] = '';   // la cargaste a mano: deja de ser estimada
  return r;
}

function alCerrar(set, c, hoy) {
  const r = {};
  const compra = set['ETAPA COMPRA'] === 'CERRADA', venta = set['ETAPA VENTA'] === 'VENDIDA';
  if ((compra || venta) && !set.ESTADO) r.ESTADO = 'CLIENTE';
  if (compra && !c['FECHA COMPRA'] && !set['FECHA COMPRA']) r['FECHA COMPRA'] = hoy;
  return r;
}

function api_lote(id, campos, nota, proximo, accion) {
  if (accion && accion[0]) api_accion(id, accion[0], accion[1], accion[2]);
  if (campos && Object.keys(campos).length) api_guardar(id, campos);
  if (nota) api_accion(id, 'NOTA', '', nota);
  if (proximo) api_accion(id, 'PROXIMO', (proximo.fecha || '') + '|' + (proximo.canal || '') + '|' + (proximo.hora || ''), proximo.accion || '');
  return true;
}

// Pestaña Contactos: listas por segmento. Primero P1-P2, despues el que hace mas que no contactas.
const ETAPAS_VENTA_ABIERTAS = ['CAPTAR', 'PRELISTING', 'ACM', 'NO CAPTADA', 'CON OTRA INMO', 'CAPTADA', 'RESERVA'];
function segmentoDe(c) {
  if (['DESCARTADO'].includes(c.ESTADO)) return '';
  const pago = String(c['BUSCA FORMA DE PAGO'] || '').toUpperCase();
  if (ETAPAS_VENTA_ABIERTAS.includes(c['ETAPA VENTA']) || (c['VENDE TIPO'] && c['ETAPA VENTA'] !== 'VENDIDA') || PAGO_CON_VENTA.includes(pago)) return 'vendedores';
  if (c.ESTADO === 'EN PAUSA' || !c['BUSCA TIPO']) return '';
  if (pago === 'CASH') return 'cash';
  if (pago.startsWith('CREDITO')) return 'credito';
  return 'sinpago';
}
// Comprador en contacto (ya sabés qué busca) al que le falta forma de pago o temperatura: sin eso no se puede priorizar
// Para completar: solo si ya hablaste con él (antes de hablar no podés saber cómo paga ni su temperatura)
const incompleto = c => c.ESTADO === 'EN CONTACTO' && !!c['BUSCA TIPO'] && !!fecha_(c['ULT CONTACTO']) && (!c['BUSCA FORMA DE PAGO'] || !c.TEMPERATURA);
function api_lista(seg) {
  const { filas } = leer_();
  const hoy = hoy_(), ctx = contexto_(historial_());
  const k = (n => (num_(n) ? Math.round(num_(n) / 1000) + 'k' : ''));
  if (seg === 'incompletos') return filas.filter(incompleto).map(c => Object.assign(item_(c, hoy, { prox: '',
    accion: 'Falta: ' + [!c['BUSCA FORMA DE PAGO'] ? 'forma de pago' : '', !c.TEMPERATURA ? 'temperatura' : ''].filter(Boolean).join(' y ') }), ctx[c.ID] || {}));
  return filas.filter(c => segmentoDe(c) === seg)
    .sort((a, b) => (prioridad(a['BUSCA FORMA DE PAGO']) || 3.5) - (prioridad(b['BUSCA FORMA DE PAGO']) || 3.5) || (fecha_(a['ULT CONTACTO']) || 0) - (fecha_(b['ULT CONTACTO']) || 0))
    .map(c => Object.assign(item_(c, hoy, { accion: seg === 'vendedores'
      ? ['Venta: ' + (c['ETAPA VENTA'] || 'sin etapa'), c['VENDE TIPO'], c['VENDE BARRIO']].filter(Boolean).join(' · ')
      : [c['ETAPA COMPRA'] || 'sin etapa', c['BUSCA TIPO'], c['BUSCA BARRIOS'], k(c['BUSCA HASTA USD'])].filter(Boolean).join(' · '), prox: '' }), ctx[c.ID] || {}));
}

// "Le mandé opciones": items = [{ direccion, link }]. Queda en el HISTORIAL por ID (una línea por opción: "dirección | link").
function api_opciones(id, items) {
  const xs = (items || []).map(x => ({ d: String(x.direccion || '').trim(), l: String(x.link || '').trim() })).filter(x => x.d || x.l);
  if (!xs.length) throw new Error('No marcaste ninguna opción');
  if (xs.some(x => !x.d)) throw new Error('Cada opción tiene que tener la dirección (el link puede cambiar)');
  return api_accion(id, 'OPCIONES', String(xs.length), xs.map(x => x.d + (x.l ? ' | ' + x.l : '')).join('\n'));
}

// Cartera (pestaña Contactos): los activos agrupados, con cuántos hay en cada grupo
// Corregir el texto de lo que anotaste (Qué pasó o una nota). Se identifica por contacto + fecha y hora exacta del registro.
const TIPOS_EDITABLES = ['CONTACTO', 'NOTA'];
function api_editarHist(id, ts, texto) {
  const sh = ss_().getSheetByName('HISTORIAL'), v = sh.getDataRange().getValues();
  for (let i = v.length - 1; i > 0; i--) {
    if (idTxt(v[i][1]) === idTxt(id) && new Date(v[i][0]).getTime() === Number(ts) && TIPOS_EDITABLES.includes(v[i][3])) {
      sh.getRange(i + 1, 6).setValue(String(texto || ''));
      return true;
    }
  }
  throw new Error('No encontré ese registro');
}

// Esta semana: tus próximos pasos (los que pusiste a mano) y los eventos del calendario C21 y del personal, día por día.
// ponytail: las sugerencias del CRM no van: se calculan cada día según el ritmo, no tienen fecha fija.
function api_semana() {
  const { filas } = leer_();
  const hoy = hoy_(), hist = historial_();
  const dias = Array.from({ length: 7 }, (_, i) => { const d = sumarDias_(hoy, i); return { titulo: (i === 0 ? 'Hoy' : i === 1 ? 'Mañana' : DIAS_SEMANA[d.getDay()]) + ' ' + ddmm_(d), items: [] }; });
  let atrasados = 0;
  filas.forEach(c => {
    if (c.ESTADO === 'DESCARTADO' || !manual(c)) return;
    const n = diasEntre(hoy, fecha_(c['PROX CONTACTO']));
    if (n < 0) { atrasados++; return; }
    if (n < 7) dias[n].items.push({ id: c.ID, nombre: String(c.NOMBRE).split(' - ')[0], texto: String(c['PROX ACCION'] || 'Próximo paso'), canal: String(c['PROX CANAL'] || ''), hora: horaTxt_(c['PROX HORA']) });
  });
  const porEvento = {};
  hist.forEach(x => { if (x[3] === 'EVENTO' || x[3] === 'EVENTO CORREGIDO') porEvento[String(x[4])] = x[1]; });
  const vistos = new Set();
  [CalendarApp.getCalendarById(CAL_ID), CalendarApp.getDefaultCalendar && CalendarApp.getDefaultCalendar()].forEach(cal => {
    if (!cal) return;
    try {
      cal.getEvents(hoy, sumarDias_(hoy, 7)).forEach(e => {
        if (vistos.has(e.getId()) || String(e.getTitle()).startsWith(PREFIJO_PASO)) return; vistos.add(e.getId());   // los avisos de tus pasos ya están como paso
        const ini = e.getStartTime(), n = Math.max(0, diasEntre(hoy, new Date(ini.getFullYear(), ini.getMonth(), ini.getDate())));
        if (n < 7) dias[n].items.push({ id: porEvento[e.getId()] || '', nombre: '', texto: e.getTitle(), canal: 'Evento', hora: e.isAllDayEvent() ? '' : hhmm_(ini) });
      });
    } catch (err) {}   // si Calendar falla, la semana igual muestra tus pasos
  });
  dias.forEach(d => d.items.sort((a, b) => (a.hora || '99') < (b.hora || '99') ? -1 : 1));
  return { dias, atrasados };
}

function api_cartera() {
  const { filas } = leer_();
  const hoy = hoy_(), ctx = contexto_(historial_());
  const it = c => Object.assign(item_(c, hoy, { prox: '', diasSin: fecha_(c['ULT CONTACTO']) ? diasEntre(fecha_(c['ULT CONTACTO']), hoy) : null,
    accion: c['PROX DEFINIDO'] && c['PROX ACCION'] ? 'Próximo: ' + c['PROX ACCION'] + ' (' + txt_(fecha_(c['PROX CONTACTO'])) + ')' : '' }), ctx[c.ID] || {});
  const g = { leads: [], compradores: { CALIENTE: [], TIBIO: [], FRIO: [], SIN: [] }, vendedores: {}, clientes: [] };
  filas.forEach(c => {
    if (c.ESTADO === 'DESCARTADO' || c.ESTADO === 'EN PAUSA') return;
    if (c.ESTADO === 'NUEVO') { const x = it(c); x.accion = x.accion || (num_(c.INTENTO) < LLAMADAS ? 'Llamada ' + (num_(c.INTENTO) + 1) + ' de 3' : 'Mensaje ' + (num_(c.INTENTO) - LLAMADAS + 1) + ' de ' + CADENCIA.length); g.leads.push(x); return; }
    if (c.ESTADO === 'CLIENTE') g.clientes.push(it(c));
    if (ETAPAS_VENTA.includes(c['ETAPA VENTA']) && c['ETAPA VENTA'] !== 'VENDIDA') (g.vendedores[c['ETAPA VENTA']] = g.vendedores[c['ETAPA VENTA']] || []).push(it(c));
    if (c.ESTADO === 'EN CONTACTO' && (c['BUSCA TIPO'] || !c['ETAPA VENTA'])) {
      const t = String(c.TEMPERATURA || '').toUpperCase();
      g.compradores[RITMO[t] ? t : 'SIN'].push(it(c));
    }
  });
  return g;
}

function api_buscar(q) {
  const t = norm_(q), d = String(q || '').replace(/\D/g, '');
  const hoy = hoy_();
  return leer_().filas
    .filter(c => norm_(c.NOMBRE).includes(t) || (d.length > 3 && String(c.TELEFONO).replace(/\D/g, '').includes(d)))
    .slice(0, 40).map(c => item_(c, hoy));
}

function api_ficha(id) {
  const { filas } = leer_();
  const c = filas.find(f => f.ID === idTxt(id));
  if (!c) throw new Error('No encontre el contacto');
  const datos = {};
  Object.keys(c).forEach(k => { if (k !== '_fila') datos[k] = c[k] instanceof Date ? txt_(c[k]) : String(c[k]); });
  const todo = historial_(), ix = indiceHist_(todo), fichas = fichas_();
  const hist = todo
    .filter(x => x[1] === idTxt(id)).reverse()
    .map(x => ({ ts: new Date(x[0]).getTime(), fecha: Utilities.formatDate(new Date(x[0]), Session.getScriptTimeZone(), 'dd/MM HH:mm'), tipo: x[3], detalle: String(x[4]), texto: String(x[5]) }));
  const comp = compradoresPara_(c, filas);
  const sig = ESTADOS_CADENCIA.includes(c.ESTADO) ? siguienteToque(num_(c.INTENTO)) : null;
  let sugerido = sig && sig.codigo ? sig.codigo : (c.ESTADO === 'EN PAUSA' ? (fecha_(c['PROX CONTACTO']) ? 'A1' : c['BUSCA TIPO'] ? 'R2' : 'R1') : '');
  if (sugerido === 'CAD1' && FUENTES_PROPIAS.includes(String(c.FUENTE))) sugerido = 'IG1';
  // La misma jugada que muestra Hoy
  const hoy = hoy_();
  let jugada = null;
  if (ETAPAS_VENDEDOR_HOY.includes(c['ETAPA VENTA']) && !ESTADOS_CADENCIA.includes(c.ESTADO)) jugada = vendedorHoy(c, ultimoVendedor_(c, ix), hoy);
  if (!jugada && c.ESTADO === 'EN CONTACTO') jugada = compradorHoy(c, infoComprador_(c, ix, filas, fichas), hoy);
  if (jugada && jugada.codigo) sugerido = jugada.codigo === 'V3A' && comp.exactos ? 'V3D' : jugada.codigo;
  else if (c['ETAPA VENTA'] === 'NO CAPTADA') sugerido = comp.exactos ? 'V3D' : 'V3A';
  else if (c['ETAPA VENTA'] === 'CON OTRA INMO') sugerido = 'V3B';
  if (noAtiende(c) && fecha_(c['PROX CONTACTO']) && fecha_(c['PROX CONTACTO']) <= hoy) sugerido = 'NOAT';
  if (!sugerido && relacionToca(c.RELACION, fecha_(c['ULT CONTACTO']), fecha_(c['FECHA ALTA']), hoy_()) !== null) sugerido = 'REL';
  // Si lo ultimo que paso es que respondio, sugerir del grupo "Responde"
  const ultimo = hist.find(x => ['RESPONDIO', 'LLAMADA_SI', 'LLAMADA_NO', 'MENSAJE'].includes(x.tipo));
  const sugeridoCategoria = !sugerido && ultimo && ultimo.tipo === 'RESPONDIO' ? 'Responde' : '';
  const extra = comp.exactos ? { busquedas: busquedasTxt(comp.exactos), compradores: String(comp.exactos) } : {};
  const usos = {};
  todo
    .filter(x => x[1] === idTxt(id) && x[3] === 'MENSAJE').forEach(x => { const k = String(x[4]).split('-')[0]; usos[k] = (usos[k] || 0) + 1; });   // por persona: a la misma no le repite el enfoque
  const mensajes = plantillas_().map(p => ({ codigo: p.codigo, situacion: p.situacion, categoria: p.categoria, enfoques: p.enfoques,
    variantes: p.variantes.map(t => rellenar(t, c, p.codigo, extra)), toca: varianteQueToca(usos[p.codigo] || 0, p.variantes.length) }));
  return {
    datos, hist, mensajes, sugerido, sugeridoCategoria, compradores: comp, etiqueta: etiqueta(c), wa: normalizarTel(c.TELEFONO), listas: listas_(),
    matches: matches_(c, filas, fichas).map(m => Object.assign(m, { enviada: m.enviada || !!(m.link && (ix[c.ID] || VACIO_).links.has(norm_(m.link))) })),
    jugada: jugada ? { porque: jugada.porque, jugada: jugada.jugada } : null,
    placa: ETAPAS_VENDEDOR_HOY.includes(c['ETAPA VENTA']) ? placaPara_(c, placas_()) : '',
    acms: c['ETAPA VENTA'] || c['VENDE TIPO'] ? acmsDe_(c) : []
  };
}

function api_accion(id, tipo, detalle, texto) {
  const lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    const { sh, h, filas } = leer_();
    const c = filas.find(f => f.ID === idTxt(id));
    if (!c) throw new Error('No encontre el contacto');
    const hoy = hoy_(), fer = feriados_();
    const set = {};
    const avanzarCadencia = () => {
      const n = num_(c.INTENTO) + 1;
      set.INTENTO = n;
      const s = siguienteToque(n);
      if (s) { set['PROX CONTACTO'] = sumarHabiles(hoy, s.gap, fer); set['PROX ACCION'] = s.accion; }
      else archivar(DIAS_FIN_CADENCIA);
    };
    const archivar = dias => { set.ESTADO = 'EN PAUSA'; set['PROX CONTACTO'] = sumarHabiles(hoy, dias || DIAS_ARCHIVO, fer); set['PROX ACCION'] = 'Recontacto'; };
    const activar = () => { set.ESTADO = 'EN CONTACTO'; set.RESPONDIO = 'SI'; set['PROX CONTACTO'] = ''; set['PROX ACCION'] = ''; };
    // Ya lo contactaste: si tenía algo agendado para hoy o antes, se cumplió. El próximo lo calcula Hoy con el ritmo.
    const cumplido = () => { const p = fecha_(c['PROX CONTACTO']); if (p && p <= hoy) { set['PROX CONTACTO'] = ''; set['PROX ACCION'] = ''; set['PROX CANAL'] = ''; set['PROX DEFINIDO'] = ''; set['PROX HORA'] = ''; set['PROX EVENTO'] = ''; borrarEventoPaso_(c); } };

    if (tipo === 'CONTACTO') {
      // "Qué pasó": hubo una charla (llamada, WhatsApp, reunión, prelisting, ACM, visita). detalle = tipo, texto = lo que se habló.
      set['ULT CONTACTO'] = hoy; set.RESPONDIO = 'SI';
      if (ESTADOS_CADENCIA.includes(c.ESTADO) || c.ESTADO === 'EN PAUSA') activar();
      cumplido();
    } else if (tipo === 'LLAMADA_NO' && ESTADOS_CADENCIA.includes(c.ESTADO)) {
      set['ULT CONTACTO'] = hoy; set.ESTADO = 'NUEVO'; avanzarCadencia();
    } else if (tipo === 'LLAMADA_NO') {
      // No es un lead: no cuenta como haber hablado. Queda como paso tuyo: reintentar hoy, mañana y, si sigue sin atender, WhatsApp.
      const reintento = proximoSinRespuesta(intentosSinRespuesta_(historial_(), c.ID) + 1, hoy);
      Object.assign(set, reintento, { 'PROX DEFINIDO': hoy });
    } else if (tipo === 'LLAMADA_SI') {
      set['ULT CONTACTO'] = hoy; set.RESPONDIO = 'SI';
      if (ESTADOS_CADENCIA.includes(c.ESTADO) || c.ESTADO === 'EN PAUSA') activar();
      else { if (c.ESTADO !== 'CLIENTE') set.ESTADO = 'EN CONTACTO'; cumplido(); }
    } else if (tipo === 'REVISION' || (tipo === 'MENSAJE' && ETAPAS_VENDEDOR_HOY.includes(c['ETAPA VENTA']) && !ESTADOS_CADENCIA.includes(c.ESTADO))) {
      // vendedor: los hitos los calcula Hoy desde el prelisting; la revisión cuenta como hecha
      if (tipo === 'MENSAJE') set['ULT CONTACTO'] = hoy;
      cumplido();
    } else if (tipo === 'OPCIONES') {
      set['ULT CONTACTO'] = hoy; cumplido();
      if (!c['ETAPA COMPRA'] || c['ETAPA COMPRA'] === 'CALIFICADO') set['ETAPA COMPRA'] = 'OPCIONES';
    } else if (tipo === 'MENSAJE' && String(detalle).startsWith('REL')) {
      set['ULT CONTACTO'] = hoy;   // relacion: solo reinicia el reloj, no toca estado ni cadencia
    } else if (tipo === 'MENSAJE') {
      set['ULT CONTACTO'] = hoy;
      if (ESTADOS_CADENCIA.includes(c.ESTADO)) { set.ESTADO = 'NUEVO'; avanzarCadencia(); }
      else if (c.ESTADO === 'EN PAUSA') archivar();
      else cumplido();
    } else if (tipo === 'RESPONDIO') {
      set['ULT CONTACTO'] = hoy;
      if (['NUEVO', 'EN PAUSA'].includes(c.ESTADO)) activar();
      else set.RESPONDIO = 'SI';
    } else if (tipo === 'DESCARTAR' && MOTIVOS_VUELVE.includes(detalle)) {
      archivar(); set['MOTIVO DESCARTE'] = detalle;   // vuelve a aparecer en DIAS_ARCHIVO dias habiles
    } else if (tipo === 'DESCARTAR') {
      set.ESTADO = 'DESCARTADO'; set['MOTIVO DESCARTE'] = detalle; set['PROX CONTACTO'] = ''; set['PROX ACCION'] = '';
    } else if (tipo === 'PROXIMO') {
      // detalle = "fecha|medio" (medio: Llamada, WhatsApp, Reunión, Visita). Fecha vacía = "que lo decida el CRM".
      const [f, canal, hora] = String(detalle || '').split('|');
      const d = fecha_(f);
      set['PROX CONTACTO'] = d || ''; set['PROX ACCION'] = d ? (texto || '') : ''; set['PROX CANAL'] = d ? (canal || '') : ''; set['PROX DEFINIDO'] = d ? hoy : '';
      // Con hora: aviso en tu calendario a esa hora (el anterior, si había, se borra)
      borrarEventoPaso_(c);
      set['PROX HORA'] = d && hora ? "'" + hora : ''; set['PROX EVENTO'] = '';
      if (d && hora) try { set['PROX EVENTO'] = eventoPaso_(c, d, hora, canal, texto); } catch (e) {}
    } else if (tipo !== 'NOTA' && tipo !== 'AVISO' && tipo !== 'NO_GUSTO') throw new Error('Accion desconocida: ' + tipo);   // AVISO: solo queda en el historial

    escribir_(sh, h, c._fila, set);
    log_(id, c.NOMBRE, tipo, detalle, texto);
    return true;
  } finally { lock.releaseLock(); }
}

// Cuántas veces seguidas no atendió desde la última vez que hablaron (sin contar esta)
function intentosSinRespuesta_(hist, id) {
  let n = 0;
  for (let i = hist.length - 1; i >= 0; i--) {
    const x = hist[i]; if (x[1] !== idTxt(id)) continue;
    if (x[3] === 'LLAMADA_NO') n++;
    else if (['CONTACTO', 'LLAMADA_SI', 'RESPONDIO'].includes(x[3])) break;
  }
  return n;
}
function proximoSinRespuesta(n, hoy) {
  if (n === 1) return { 'PROX CONTACTO': hoy, 'PROX ACCION': 'Volver a llamar (no atendió)', 'PROX CANAL': 'Llamada' };
  if (n === 2) return { 'PROX CONTACTO': sumarDias_(hoy, 1), 'PROX ACCION': 'Volver a llamar (no atendió 2 veces)', 'PROX CANAL': 'Llamada' };
  return { 'PROX CONTACTO': hoy, 'PROX ACCION': 'No atiende: escribile por WhatsApp', 'PROX CANAL': 'WhatsApp' };
}

// Aviso en el calendario C21 para un próximo paso con hora (notificación a esa hora)
const horaTxt_ = v => v instanceof Date ? hhmm_(v) : String(v || '').trim().replace(/^'/, '');
function eventoPaso_(c, fecha, hora, canal, texto) {
  const [hh, mm] = String(hora).split(':').map(Number);
  const ini = new Date(fecha); ini.setHours(hh || 0, mm || 0, 0, 0);
  const verbo = { Llamada: 'Llamar a', WhatsApp: 'Escribirle a', 'Reunión': 'Reunión con', Visita: 'Visita con' }[canal] || 'Contactar a';
  const tel = normalizarTel(c.TELEFONO);
  const ev = CalendarApp.getCalendarById(CAL_ID).createEvent(PREFIJO_PASO + verbo + ' ' + nombreBase_(c.NOMBRE), ini, new Date(ini.getTime() + 15 * 60000),
    { description: (texto || '') + (tel ? '\nWhatsApp: https://wa.me/' + tel : '') });
  ev.removeAllReminders(); ev.addPopupReminder(0);
  return ev.getId();
}
const PREFIJO_PASO = 'CRM · ';
// Si el paso cambia o se cumple antes de la hora, el aviso se borra (los pasados quedan como registro)
function borrarEventoPaso_(c) {
  const id = String(c['PROX EVENTO'] || ''); if (!id) return;
  try { const ev = CalendarApp.getCalendarById(CAL_ID).getEventById(id); if (ev && ev.getStartTime() > new Date()) ev.deleteEvent(); } catch (e) {}
}

const NO_EDITABLES_ = ['ID', 'ORIGEN', '_fila'];

function api_guardar(id, campos) {
  const lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    const { sh, h, filas } = leer_();
    const c = filas.find(f => f.ID === idTxt(id));
    if (!c) throw new Error('No encontre el contacto');
    const set = {};
    Object.keys(campos).forEach(k => {
      if (NO_EDITABLES_.includes(k) || h.indexOf(k) < 0) return;
      const v = campos[k];
      set[k] = /FECHA|PROX CONTACTO|ULT CONTACTO|CUMPLEANOS|AUTORIZACION|DESDE/.test(k) ? (fecha_(v) || '') : v;
    });
    const hoy = hoy_();
    Object.assign(set, alGuardar(set, c, hoy));
    const nuevo = Object.assign({}, c, set);
    Object.assign(set, alCerrar(set, c, hoy));
    escribir_(sh, h, c._fila, set);
    // Cambió el nombre o lo que compra/vende: lo paso a Contactos ya ("Nombre - Compra..."), así WhatsApp lo muestra igual que el CRM.
    // Con el nombre, además, si no la sincronización de la noche lo volvería al viejo.
    if (etiqueta(nuevo) !== etiqueta(c) && c.TELEFONO) {
      try { log_(id, set.NOMBRE, 'CONTACTO GOOGLE', contactoGoogle_(c.TELEFONO, etiqueta(nuevo), false, nombreBase_(c.NOMBRE)), etiqueta(nuevo)); } catch (e) {}
    }
    return true;
  } finally { lock.releaseLock(); }
}

function api_nuevo(d) {
  const lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    const { sh, h, filas } = leer_();
    const tel = normalizarTel(d.TELEFONO);
    if (tel) { const dup = filas.find(f => normalizarTel(f.TELEFONO) === tel); if (dup) return { duplicado: true, id: dup.ID, nombre: dup.NOMBRE }; }
    const id = tel || 'X' + Utilities.getUuid().slice(0, 8);
    const conocido = FUENTES_SIN_CADENCIA.includes(String(d.FUENTE));
    const base = { ID: id, NOMBRE: d.NOMBRE, TELEFONO: d.TELEFONO, FUENTE: d.FUENTE, ROL: d.ROL, 'CONSULTO POR': d['CONSULTO POR'],
      'FECHA ALTA': hoy_(), ESTADO: conocido ? 'EN CONTACTO' : 'NUEVO', 'PROX CONTACTO': hoy_(), 'PROX ACCION': conocido ? 'Calificar' : 'Llamada',
      INTENTO: 0, RESPONDIO: conocido ? 'SI' : 'NO', ORIGEN: 'App' };
    if (d['ETAPA VENTA']) {
      base['ETAPA VENTA'] = d['ETAPA VENTA'];
      if (VENTA_SEGUIMIENTO.includes(d['ETAPA VENTA'])) { base.ESTADO = 'EN CONTACTO'; base['PROX CONTACTO'] = ''; base['PROX ACCION'] = ''; base['FECHA PRELISTING'] = hoy_(); }
    }
    sh.appendRow(h.map(k => (k in base ? base[k] : '')));
    log_(id, d.NOMBRE, 'ALTA', d.FUENTE, '');
    let google = '';
    try { google = contactoGoogle_(d.TELEFONO, String(d.NOMBRE).trim(), true); } catch (e) { google = 'no se pudo agendar: ' + e.message; }
    return { id, google };
  } finally { lock.releaseLock(); }
}


// ─── GOOGLE CONTACTS (se sincroniza con el iPhone y WhatsApp toma el nombre de ahi) ───

// Mismo nombre: igual al nombre base, o al formato largo "Nombre - Compra ...".
// Solo para nombres de 2 palabras o mas: "Karina" sola coincidiria con cualquier Karina de tu agenda.
function mismoNombre(displayName, nombre) {
  const nom = norm_(nombre), d = norm_(displayName);
  if (nom.split(/\s+/).length < 2) return false;
  return d === nom || d.startsWith(nom + ' - ');
}

// Prioridad 1: el telefono. Prioridad 2 (solo si no hay telefono que coincida): el nombre.
function buscarContactoGoogle_(tel, nombre) {
  const n = normalizarTel(tel);
  let token, porNombre = null;
  do {
    const r = People.People.Connections.list('people/me', { personFields: 'names,phoneNumbers', pageSize: 1000, pageToken: token });
    for (const p of r.connections || []) {
      if ((p.phoneNumbers || []).some(x => normalizarTel(x.value) === n)) return { porTel: p };
      if (!porNombre && (p.names || []).some(x => mismoNombre(x.displayName, nombre))) porNombre = p;
    }
    token = r.nextPageToken;
  } while (token);
  return { porNombre };
}

// soloCrear: si el telefono ya esta agendado no le toca el nombre (para no pisar lo que editaste a mano).
// Si el telefono no esta pero hay alguien con el mismo nombre, NO crea nada: avisa para que lo revises.
function contactoGoogle_(tel, nombreAgenda, soloCrear, nombreBase) {
  const n = normalizarTel(tel);
  if (!n || !nombreAgenda) return 'sin telefono valido';
  const { porTel, porNombre } = buscarContactoGoogle_(tel, nombreBase || nombreAgenda);
  if (porTel) {
    if (soloCrear) return 'ya estaba agendado';
    People.People.updateContact({ etag: porTel.etag, names: [{ givenName: nombreAgenda }] }, porTel.resourceName, { updatePersonFields: 'names' });
    return 'actualizado';
  }
  if (porNombre) {
    const otro = ((porNombre.names || [])[0] || {}).displayName || '';
    return 'NO agendado: ya tenes a "' + otro + '" con otro numero. Revisalo a mano';
  }
  People.People.createContact({ names: [{ givenName: nombreAgenda }], phoneNumbers: [{ value: '+' + n, type: 'mobile' }] });
  return 'creado';
}

// Contactos -> CRM. Devuelve el nombre nuevo, o '' si no hay que tocar nada.
// Solo mira lo de antes del " - " y no acepta un nombre que sea solo un numero.
function nombreDesdeContacto(display, nombreCRM) {
  const base = nombreBase_(display);
  if (!base || /^[+\d\s()-]+$/.test(base)) return '';
  return norm_(base) === norm_(nombreBase_(nombreCRM)) ? '' : base;
}

// Corre todas las mañanas antes del mail. Si cambiaste un nombre en WhatsApp (o en Contactos), lo trae al CRM.
// ponytail: lista toda la agenda cada vez (1 llamada por cada 1000 contactos); alcanza para una agenda personal.
function sincronizarNombres() {
  const porTel = {};
  let token;
  do {
    const r = People.People.Connections.list('people/me', { personFields: 'names,phoneNumbers', pageSize: 1000, pageToken: token });
    for (const p of r.connections || []) {
      const nom = ((p.names || [])[0] || {}).displayName || '';
      (p.phoneNumbers || []).forEach(x => { const n = normalizarTel(x.value); if (n) porTel[n] = n in porTel ? null : nom; });  // tel repetido en 2 contactos: no se toca
    }
    token = r.nextPageToken;
  } while (token);
  const lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    const { sh, h, filas } = leer_();
    let n = 0;
    filas.forEach(c => {
      const nuevo = nombreDesdeContacto(porTel[normalizarTel(c.TELEFONO)], c.NOMBRE);
      if (!nuevo) return;
      escribir_(sh, h, c._fila, { NOMBRE: nuevo });
      log_(c.ID, nuevo, 'NOMBRE DESDE CONTACTOS', 'antes: ' + c.NOMBRE, '');
      n++;
    });
    return n;
  } finally { lock.releaseLock(); }
}

function api_contactoGoogle(id) {
  const c = leer_().filas.find(f => f.ID === idTxt(id));
  if (!c) throw new Error('No encontre el contacto');
  const nombre = etiqueta(c);
  const r = contactoGoogle_(c.TELEFONO, nombre, false, nombreBase_(c.NOMBRE));
  log_(id, c.NOMBRE, 'CONTACTO GOOGLE', r, nombre);
  return r + ': ' + nombre;
}

// ─── EVENTOS EN GOOGLE CALENDAR (mismas reglas que el proyecto de Claude) ───

const DURACION_EVENTO = { VISITA: 30, ACM: 90, PRELISTING: 90, FIRMA: 60 };
const ACCION_EVENTO = { VISITA: 'Visita', ACM: 'Entregar ACM', PRELISTING: 'Prelisting', FIRMA: 'Firma' };
const DIAS_SEMANA = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
const MINUSCULAS_ = ['de', 'del', 'la', 'las', 'los', 'y', 'e'];

// "av. juan b. alberdi 1226" -> "Av. Juan B. Alberdi 1226"
function mayusculas(s) {
  return String(s || '').trim().replace(/\s+/g, ' ').toLowerCase().split(' ')
    .map((w, i) => (i > 0 && MINUSCULAS_.includes(w)) ? w : w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

// e: { tipo, lado, direccion, uf, nombre, colega, vendedor, comprador }
function tituloEvento(e) {
  const lugar = [mayusculas(e.direccion), String(e.uf || '').trim().toUpperCase()].filter(Boolean).join(' ');
  const t = e.tipo, lado = e.lado ? ' [' + e.lado + ']' : '';
  if (t === 'ACM' || t === 'PRELISTING') return t + ' ' + lugar + ' – ' + e.nombre;
  if (t === 'VISITA') return 'VISITA' + lado + ' ' + lugar + ' – ' + e.nombre + (e.lado !== 'DP' && e.colega ? ' (' + e.colega + ')' : '');
  if (t === 'FIRMA') return 'FIRMA' + lado + ' ' + lugar + ' – ' + (e.lado === 'DP' ? e.vendedor + ' [V] / ' + e.comprador + ' [C]' : e.nombre);
  throw new Error('Tipo de evento desconocido: ' + t);
}

function ubicacionEvento(e) {
  return mayusculas(e.direccion) + ', ' + (String(e.localidad || '').trim() ? mayusculas(e.localidad) : 'Ciudad Autónoma de Buenos Aires') + ', Argentina';
}

function dosDig_(n) { return String(n).padStart(2, '0'); }
function hhmm_(d) { return dosDig_(d.getHours()) + ':' + dosDig_(d.getMinutes()); }
function ddmm_(d) { return dosDig_(d.getDate()) + '/' + dosDig_(d.getMonth() + 1); }

// fecha 'yyyy-mm-dd', hora 'HH:MM' -> { inicio, fin }
function horarioEvento(fecha, hora, tipo) {
  const f = String(fecha).match(/^(\d{4})-(\d{2})-(\d{2})$/), h = String(hora).match(/^(\d{1,2}):(\d{2})$/);
  if (!f || !h) throw new Error('Fecha u hora invalida');
  const inicio = new Date(+f[1], f[2] - 1, +f[3], +h[1], +h[2]);
  return { inicio, fin: new Date(inicio.getTime() + DURACION_EVENTO[tipo] * 60000) };
}

function resumenEvento(titulo, inicio, fin) {
  return '✓ ' + titulo + ' · ' + DIAS_SEMANA[inicio.getDay()] + ' ' + ddmm_(inicio) + ' ' + hhmm_(inicio) + '–' + hhmm_(fin);
}

function mensajeEvento(e, inicio) {
  const cab = '📅 ' + DIAS_SEMANA[inicio.getDay()] + ' ' + ddmm_(inicio) + '\n⏰ ' + hhmm_(inicio) + 'hs\n📍 ' + mayusculas(e.direccion);
  if (e.tipo === 'VISITA') return '✅ *Visita confirmada*\n' + cab + '\n\n[LINK]\n\n*Notas:*\n' +
    '- Te pido por favor puntualidad ya que cada visita tiene una franja horaria asignada y hay muchos interesados para verlo.\n' +
    '- Si quieren avanzar con la compra podemos tomar la reserva ahí mismo con un monto mínimo de usd 1000.\n' +
    '- Por favor, si no podés venir avisame con la mayor anticipación posible 🙂';
  if (e.tipo === 'FIRMA') return '🔑 *Escrituración confirmada*\n' + cab;
  return '✅ *ACM confirmada*\n' + cab;   // ACM y PRELISTING usan el mismo mensaje
}

function validarEvento_(e) {
  const falta = [];
  if (!DURACION_EVENTO[e.tipo]) falta.push('tipo');
  if ((e.tipo === 'VISITA' || e.tipo === 'FIRMA') && !['PV', 'PC', 'DP'].includes(e.lado)) falta.push('punta (vendedora, compradora o doble)');
  if (!String(e.direccion || '').trim()) falta.push('dirección');
  if (e.tipo === 'FIRMA' && e.lado === 'DP') { if (!e.vendedor) falta.push('nombre del vendedor'); if (!e.comprador) falta.push('nombre del comprador'); }
  else if (!String(e.nombre || '').trim()) falta.push('nombre');
  if (!e.fecha) falta.push('fecha');
  if (!e.hora) falta.push('hora');
  if (falta.length) throw new Error('Falta: ' + falta.join(', '));
}

// Crea el evento, o si viene eventoId, corrige ese evento. Deja el proximo paso en la fecha del evento.
function api_evento(id, e) {
  validarEvento_(e);
  const c = leer_().filas.find(f => f.ID === idTxt(id));
  if (!c) throw new Error('No encontre el contacto');
  const { inicio, fin } = horarioEvento(e.fecha, e.hora, e.tipo);
  const titulo = tituloEvento(e), ubicacion = ubicacionEvento(e);
  const cal = CalendarApp.getCalendarById(CAL_ID);
  if (!cal) throw new Error('No tengo acceso al calendario C21');
  let ev;
  if (e.eventoId) {
    ev = cal.getEventById(e.eventoId);
    if (!ev) throw new Error('No encontre el evento para corregir');
    ev.setTitle(titulo); ev.setTime(inicio, fin); ev.setLocation(ubicacion);
  } else {
    ev = cal.createEvent(titulo, inicio, fin, { location: ubicacion });
    ev.removeAllReminders(); ev.addPopupReminder(60);
  }
  api_accion(id, 'PROXIMO', Utilities.formatDate(inicio, Session.getScriptTimeZone(), 'yyyy-MM-dd'), ACCION_EVENTO[e.tipo]);
  log_(id, c.NOMBRE, e.eventoId ? 'EVENTO CORREGIDO' : 'EVENTO', ev.getId(), titulo);
  return { eventoId: ev.getId(), resumen: resumenEvento(titulo, inicio, fin), mensaje: mensajeEvento(e, inicio) };
}

// ─── CAPTURAS (publicacion con otra inmobiliaria) ────────────────────────────
// Guarda la imagen en la carpeta "CRM Capturas" de tu Drive y deja el link en la columna CAPTURAS.
function api_captura(id, base64, nombre) {
  const { sh, h, filas } = leer_();
  const c = filas.find(f => f.ID === idTxt(id));
  if (!c) throw new Error('No encontre el contacto');
  if (String(base64).length > 8e6) throw new Error('La imagen es muy grande');
  const it = DriveApp.getFoldersByName('CRM Capturas');
  const carpeta = it.hasNext() ? it.next() : DriveApp.createFolder('CRM Capturas');
  const f = carpeta.createFile(Utilities.newBlob(Utilities.base64Decode(base64), 'image/jpeg',
    nombreBase_(c.NOMBRE) + ' ' + Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH.mm') + '.jpg'));
  const link = f.getUrl();
  escribir_(sh, h, c._fila, { CAPTURAS: [c.CAPTURAS, link].filter(Boolean).join('\n') });
  log_(id, c.NOMBRE, 'CAPTURA', link, nombre || '');
  return link;
}

// ─── VISITAS: CONFIRMAR ANTES Y SEGUIR DESPUES ───────────────────────────────
// Usa los eventos creados desde la app (el historial guarda el id del evento y del contacto).
// El mensaje queda listo; lo manda Nahuel. Al mandarlo se registra un AVISO y deja de aparecer.
const FRASE_EVENTO = { VISITA: 'la visita', ACM: 'la reunión', PRELISTING: 'la reunión', FIRMA: 'la firma' };

function textoEvento(plantilla, c, codigo, ev, hoy) {
  const ini = ev.inicio, man = new Date(hoy); man.setDate(man.getDate() + 1);
  const cuando = ini.toDateString() === man.toDateString() ? 'mañana' : 'el ' + DIAS_SEMANA[ini.getDay()].toLowerCase() + ' ' + ddmm_(ini);
  return rellenar(plantilla, c, codigo).replace(/\{evento\}/g, FRASE_EVENTO[ev.tipo] || 'lo que acordamos')
    .replace(/\{dia\}/g, cuando).replace(/\{hora\}/g, hhmm_(ini)).replace(/\{direccion\}/g, ev.direccion);
}

function visitas_(filas, hist, hoy) {
  const porEvento = {};
  hist.forEach(x => { if (x[3] === 'EVENTO' || x[3] === 'EVENTO CORREGIDO') porEvento[String(x[4])] = x[1]; });
  if (!Object.keys(porEvento).length) return [];
  const hechos = new Set(hist.filter(x => x[3] === 'AVISO').map(x => String(x[4])));
  const cal = CalendarApp.getCalendarById(CAL_ID);
  if (!cal) return [];
  const plant = {}; plantillas_().forEach(p => (plant[p.codigo] = p.variantes));
  const conf = plant.CONF || ['Hola {nombre}, te confirmo {evento}: {dia} a las {hora} en {direccion}. Seguimos en pie?'];
  const post = plant.C4 || ['Cómo te quedaste con la visita? Qué te gustó y qué no?'];
  const dia = n => { const d = new Date(hoy); d.setDate(d.getDate() + n); return d; };
  const hasta = sumarHabiles(hoy, 1, feriados_()); hasta.setDate(hasta.getDate() + 1);   // hasta el proximo dia habil inclusive
  const out = [];
  const armar = (evs, codigo, plantillas, accion) => evs.forEach(e => {
    const id = porEvento[e.getId()], clave = codigo + ' ' + e.getId();
    const c = filas.find(f => f.ID === idTxt(id));
    if (!c || hechos.has(clave)) return;
    const tipo = String(e.getTitle()).split(' ')[0];
    if (codigo === 'C4' && tipo !== 'VISITA') return;
    const ev = { inicio: e.getStartTime(), tipo, direccion: String(e.getLocation() || '').split(',')[0] };
    out.push(item_(c, hoy, { accion, evento: e.getTitle(), clave, wa: normalizarTel(c.TELEFONO),
      texto: textoEvento(plantillas[hechos.size % plantillas.length], c, codigo, ev, hoy),
      cuando: DIAS_SEMANA[ev.inicio.getDay()] + ' ' + ddmm_(ev.inicio) + ' ' + hhmm_(ev.inicio) }));
  });
  armar(cal.getEvents(dia(1), hasta), 'CONF', conf, 'Confirmar');
  armar(cal.getEvents(dia(-3), hoy), 'C4', post, 'Cómo le fue en la visita');
  return out;
}

// ─── ESTADISTICAS ────────────────────────────────────────────────────────────
// Pura (testeada): hist = filas de HISTORIAL [fecha, id, nombre, tipo, detalle, texto], filas = CONTACTOS.
const FRANJAS_ = [['9 a 11', 9, 11], ['12 a 14', 12, 14], ['16 a 18:30', 16, 19]];
function estadisticas_(hist, filas, desde) {
  hist = hist.map(x => x[3] === 'CONTACTO' ? [x[0], x[1], x[2], x[4] === 'Llamada' ? 'LLAMADA_SI' : 'RESPONDIO', x[4], x[5]] : x);
  const DIA = 86400000;
  const resp = {};                                    // id -> fechas en que respondio o atendio
  const toques = {};                                  // id -> fechas de toques (llamada no atendida o mensaje)
  hist.forEach(x => {
    const t = new Date(x[0]).getTime(), id = x[1];
    if (x[3] === 'RESPONDIO' || x[3] === 'LLAMADA_SI') (resp[id] = resp[id] || []).push(t);
    if (x[3] === 'LLAMADA_NO' || x[3] === 'MENSAJE') (toques[id] = toques[id] || []).push(t);
  });
  const enRango = hist.filter(x => new Date(x[0]).getTime() >= desde.getTime());

  // Por plantilla y opcion: respondio dentro de los 7 dias siguientes
  const pl = {};
  enRango.filter(x => x[3] === 'MENSAJE').forEach(x => {
    const clave = String(x[4] || 'sin codigo'), t = new Date(x[0]).getTime();
    const p = pl[clave] = pl[clave] || { clave, codigo: clave.split('-')[0], enviados: 0, respondidos: 0 };
    p.enviados++;
    if ((resp[x[1]] || []).some(r => r > t && r - t <= 7 * DIA)) p.respondidos++;
  });

  // Por intento: cuantos toques hubo antes de la primera respuesta
  const intentos = {};
  const primera = {};
  hist.forEach(x => { if (x[3] === 'RESPONDIO' || x[3] === 'LLAMADA_SI') { const t = new Date(x[0]).getTime(); if (!primera[x[1]] || t < primera[x[1]]) primera[x[1]] = t; } });
  Object.keys(primera).forEach(id => {
    if (primera[id] < desde.getTime()) return;
    const n = (toques[id] || []).filter(t => t < primera[id]).length;
    const k = n >= 7 ? '7 o más' : n >= 4 ? '4 a 6' : String(n);
    intentos[k] = (intentos[k] || 0) + 1;
  });

  // Llamadas por franja horaria
  const franjas = FRANJAS_.map(([nombre]) => ({ nombre, llamadas: 0, atendidas: 0 })).concat([{ nombre: 'Otro horario', llamadas: 0, atendidas: 0 }]);
  enRango.filter(x => x[3] === 'LLAMADA_SI' || x[3] === 'LLAMADA_NO').forEach(x => {
    const d = new Date(x[0]), h = d.getHours() + d.getMinutes() / 60;
    let i = FRANJAS_.findIndex(([, a, b]) => h >= a && h < (b === 19 ? 18.5 : b));
    if (i < 0) i = franjas.length - 1;
    franjas[i].llamadas++; if (x[3] === 'LLAMADA_SI') franjas[i].atendidas++;
  });

  // Por fuente: contactos que entraron en el periodo
  const fu = {};
  filas.filter(c => { const f = fecha_(c['FECHA ALTA']); return f && f >= desde; }).forEach(c => {
    const k = String(c.FUENTE || 'Sin fuente');
    const f = fu[k] = fu[k] || { fuente: k, total: 0, respondieron: 0, descartados: 0, motivos: {} };
    f.total++;
    if (c.RESPONDIO === 'SI') f.respondieron++;
    if (c.ESTADO === 'DESCARTADO') { f.descartados++; const m = String(c['MOTIVO DESCARTE'] || 'Sin motivo'); f.motivos[m] = (f.motivos[m] || 0) + 1; }
  });

  return {
    plantillas: Object.values(pl).sort((a, b) => a.clave.localeCompare(b.clave, 'es', { numeric: true })),
    intentos, franjas, fuentes: Object.values(fu).sort((a, b) => b.total - a.total)
  };
}

function api_estadisticas(dias) {
  const desde = hoy_(); desde.setDate(desde.getDate() - (+dias || 90));
  const hist = historial_();
  return Object.assign({ dias: +dias || 90 }, estadisticas_(hist, leer_().filas, desde));
}

// ─── AUTOMATICO ──────────────────────────────────────────────────────────────

// Leads de C21 (corre cada 15 minutos). Lee sin trabar nada; solo bloquea si hay filas nuevas para escribir.
function importarC21() {
  const c21 = SpreadsheetApp.openById(C21_ID).getSheets()[0].getDataRange().getValues();
  const candidatos = (existentes) => {
    const out = [];
    for (let i = 2; i < c21.length; i++) {          // filas 1-2 son encabezado
      const fecha = c21[i][1], cel = c21[i][4];
      let nombre = String(c21[i][3] || '').trim();
      const id = normalizarTel(cel);
      if (!nombre || !id || existentes.has(id)) continue;
      existentes.add(id);
      // Solo el nombre de pila ("Alejandra"): se le suma el día que entró ("Alejandra 18/11") para distinguirla en el CRM y en WhatsApp
      if (!/\s/.test(nombre) && fecha_(fecha)) nombre += ' ' + ddmm_(fecha_(fecha));
      out.push({ i, id, nombre, cel: String(cel).trim(), fecha });
    }
    return out;
  };
  const tels = filas => new Set(filas.map(f => normalizarTel(f.TELEFONO)).filter(Boolean));
  if (!candidatos(tels(leer_().filas)).length) return 0;   // lo normal: nada nuevo, sin bloquear
  const lock = LockService.getScriptLock(); lock.waitLock(20000);
  let nuevas;
  try {
    const { sh, h, filas } = leer_();                         // se relee con el bloqueo puesto, por si entró algo en el medio
    nuevas = candidatos(tels(filas));
    if (!nuevas.length) return 0;
    const filasNuevas = nuevas.map(x => {
      const base = { ID: x.id, NOMBRE: x.nombre, TELEFONO: x.cel, FUENTE: 'C21', 'FECHA ALTA': fecha_(x.fecha) || hoy_(),
        ESTADO: 'NUEVO', 'PROX CONTACTO': hoy_(), 'PROX ACCION': 'Llamada', INTENTO: 0, RESPONDIO: 'NO', ORIGEN: 'C21!' + (x.i + 1) };
      return h.map(k => (k in base ? base[k] : ''));
    });
    sh.getRange(sh.getLastRow() + 1, 1, filasNuevas.length, h.length).setValues(filasNuevas);
  } finally { lock.releaseLock(); }
  nuevas.forEach(x => {
    let res;
    try { res = contactoGoogle_(x.cel, x.nombre, true); } catch (e) { res = 'error: ' + e.message; }
    log_(x.id, x.nombre, 'CONTACTO GOOGLE', res, '');
  });
  avisar_(nuevas.length === 1 ? 'Entró 1 lead nuevo de C21' : 'Entraron ' + nuevas.length + ' leads nuevos de C21', 'Están en Hoy → Llamar.');
  return nuevas.length;
}

// Notificación al celular por ntfy. El tema va en Propiedades del script (NTFY_TOPIC), nunca en el código.
// ponytail: solo la cantidad, sin nombres ni teléfonos: ntfy.sh es un servicio público.
function avisar_(titulo, mensaje) {
  const tema = PropertiesService.getScriptProperties().getProperty('NTFY_TOPIC');
  if (!tema) return;
  try {
    UrlFetchApp.fetch('https://ntfy.sh/', { method: 'post', contentType: 'application/json', muteHttpExceptions: true,
      payload: JSON.stringify({ topic: tema, title: titulo, message: mensaje, click: 'https://nahuelim.com.ar/crm/', tags: ['house'] }) });
  } catch (e) { console.log('ntfy: ' + e.message); }
}
// Para probar ntfy sin esperar un lead
function probarAviso() { avisar_('Prueba del CRM', 'Si ves esto, las notificaciones funcionan.'); return PropertiesService.getScriptProperties().getProperty('NTFY_TOPIC') ? 'Enviado' : 'Falta NTFY_TOPIC en Propiedades del script'; }

// El mail de las 7 en HTML: arriba "Hoy en 3 líneas" y los números; después, una sección por bloque.
const esc_ = t => String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
function mailHtml_(r, sec, o) {
  const n = k => (r[k] || []).length, nom = x => esc_(nombreBase_(x.nombre));
  const tl = [];
  if (n('proximos')) tl.push('Tenés <b>' + n('proximos') + (n('proximos') === 1 ? ' próximo paso' : ' próximos pasos') + '</b> que pusiste vos (' + r.proximos.slice(0, 3).map(nom).join(', ') + (n('proximos') > 3 ? '…' : '') + ').');
  if (n('opciones')) tl.push('<b>' + n('opciones') + (n('opciones') === 1 ? ' comprador' : ' compradores') + '</b> esperando opciones (' + r.opciones.slice(0, 3).map(nom).join(', ') + ').');
  if (n('llamar') || o.nuevos) tl.push((o.nuevos ? 'Entraron <b>' + o.nuevos + ' leads nuevos</b> de C21. ' : '') + (n('llamar') ? '<b>' + n('llamar') + ' para llamar</b>: antes del mediodía.' : ''));
  if (!tl.length) tl.push('Día tranquilo: no hay nada urgente. Buen día para revivir contactos.');
  const caja = (num, t) => '<td style="background:#24352E;border-radius:8px;padding:8px 4px;text-align:center;color:#F7F4EC;font-size:12px"><div style="font-size:22px;font-weight:700">' + num + '</div>' + t + '</td>';
  let h = '<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:560px;margin:0 auto;color:#14231D">' +
    '<div style="background:#14231D;color:#F7F4EC;border-radius:14px;padding:16px">' +
    '<div style="color:#BEAF87;font-weight:700;margin-bottom:6px">Hoy en 3 líneas</div>' + tl.map(t => '<div style="margin:4px 0">· ' + t + '</div>').join('') +
    '<table style="width:100%;border-spacing:6px;margin-top:8px"><tr>' + caja(n('proximos'), 'Tus pasos') + caja(n('llamar') + n('mensajes'), 'Leads') + caja(n('opciones') + n('atento'), 'Atento') + '</tr></table></div>';
  sec.forEach(([t, xs]) => {
    if (!xs.length) return;
    h += '<div style="margin:20px 0 6px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#434C47;border-bottom:1px solid #DDD6C6;padding-bottom:4px">' + esc_(t) + ' (' + xs.length + ')</div>';
    xs.forEach(x => {
      h += '<div style="padding:7px 0;border-bottom:1px solid #F0ECE2;font-size:14px"><b>' + nom(x) + '</b>' + (x.canal ? ' <span style="color:#005941">· ' + esc_(x.canal) + '</span>' : '') +
        '<div style="color:#434C47">' + esc_(x.porque || x.accion || x.evento || '') + (x.jugada ? ' → ' + esc_(x.jugada) : '') + '</div></div>';
    });
  });
  const extra = [r.incompletos ? r.incompletos + ' compradores sin forma de pago o temperatura' : '', r.sinTel ? r.sinTel + ' contactos activos sin teléfono' : '',
    r.revivirPendientes ? r.revivirPendientes + ' para revivir (mínimo 5 por día)' : '', o.nombres ? o.nombres + ' nombres actualizados desde Contactos' : ''].filter(Boolean);
  if (extra.length) h += '<div style="margin:20px 0 6px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#434C47">Para completar</div><div style="font-size:14px;color:#434C47">' + extra.map(esc_).join(' · ') + '</div>';
  h += '<div style="margin:24px 0 8px;text-align:center"><a href="' + APP_URL + '" style="background:#005941;color:#F7F4EC;text-decoration:none;padding:12px 22px;border-radius:12px;display:inline-block;font-weight:600">Abrir el CRM</a></div></div>';
  return h;
}

// Para ver cómo queda el mail sin esperar a las 7 (se manda aunque sea fin de semana)
function probarMail() { mailDiario(true); }

function mailDiario(forzar) {
  let nombres = 0;
  try { nombres = sincronizarNombres(); } catch (e) { console.log('sincronizarNombres: ' + e.message); }
  const nuevos = importarC21();
  if (!forzar && !esHabil_(hoy_(), feriados_())) return;
  const r = api_hoy();
  const sec = [
    ['Tus próximos pasos de hoy', r.proximos], ['Con fecha fija', (r.visitas || []).concat(r.fechas)], ['Mandale opciones', r.opciones],
    ['Llamar', r.llamar], ['Mensajes de la cadencia', r.mensajes], ['Estate atento', r.atento]];
  const html = mailHtml_(r, sec, { nuevos, nombres, fecha: hoy_() });
  const asunto = 'CRM · ' + DIAS_SEMANA[hoy_().getDay()] + ' ' + ddmm_(hoy_()) + ': ' + [
    r.proximos.length ? r.proximos.length + (r.proximos.length === 1 ? ' paso tuyo' : ' pasos tuyos') : '',
    r.opciones.length ? r.opciones.length + ' para mandar opciones' : '',
    r.llamar.length ? r.llamar.length + ' para llamar' : '', r.atento.length ? r.atento.length + ' para estar atento' : ''].filter(Boolean).join(', ') || 'día tranquilo';
  const texto = sec.filter(([, xs]) => xs.length).map(([t, xs]) => t.toUpperCase() + '\n' + xs.map(x => '- ' + nombreBase_(x.nombre) + ': ' + (x.porque || x.accion || '') + (x.jugada ? ' -> ' + x.jugada : '')).join('\n')).join('\n\n') + '\n\nAbrir la app: ' + APP_URL;
  MailApp.sendEmail(Session.getEffectiveUser().getEmail(), asunto, texto, { htmlBody: html, name: 'CRM Nahuel' });
}

// Correr UNA vez: pasa los datos escritos a mano a los valores de las listas.
// - Barrios -> nombres de la pestana BARRIOS. Lo que no reconoce va a BUSCA REQUISITOS ("Zona: ...").
// - Proxima accion, urgencia y motivacion -> valores de la lista. El texto original va a NOTAS. No se pierde nada.
function limpiezaUnaVez() {
  const { sh, h, filas } = leer_();
  const canon = {};
  listas_().barrios.forEach(b => (canon[barrioN(b)] = b));
  const por = {};
  // barrios toca BUSCA BARRIOS/REQUISITOS/VENDE BARRIO; listas toca PROX ACCION/URGENCIA/MOTIVACION/NOTAS: no se pisan
  [...limpiarBarrios(filas, canon), ...limpiarListas(filas)].forEach(r => (por[r.fila] = Object.assign(por[r.fila] || {}, r.cambios)));
  Object.keys(por).forEach(f => escribir_(sh, h, +f, por[f]));
  console.log('Filas actualizadas: ' + Object.keys(por).length);
}

function mapAccion(a) {
  const x = norm_(a);
  if (!x) return '';
  const exacta = ACCIONES.find(v => norm_(v) === x);
  if (exacta) return exacta;
  if (/^mensaje/.test(x)) return 'Mensaje';
  if (/^llam/.test(x)) return 'Llamada';
  if (/recontacto archivado/.test(x)) return 'Recontacto';
  if (/visita/.test(x)) return 'Visita';
  if (/buscar|opciones/.test(x)) return 'Enviar opciones';
  return 'Seguimiento';
}
const ACCIONES_SIMPLES_ = /^(mensaje( de reactivacion| \d+)?|recontacto archivado|llamar|llamada|buscar opciones|volver a buscar|seguimiento)$/;

function limpiarListas(filas) {
  const out = [];
  filas.forEach(f => {
    const cambios = {}, notas = [];
    const acc = String(f['PROX ACCION'] || '').trim(), nueva = mapAccion(acc);
    if (nueva !== acc) { cambios['PROX ACCION'] = nueva; if (!ACCIONES_SIMPLES_.test(norm_(acc))) notas.push('Proximo paso: ' + acc); }
    const urg = String(f.URGENCIA || '').trim();
    if (urg && !URGENCIAS.includes(urg)) { cambios.URGENCIA = ''; notas.push('Urgencia: ' + urg); }
    const mot = String(f.MOTIVACION || '').trim();
    if (mot && !MOTIVACIONES.includes(mot)) {
      const m = MOTIVACIONES.find(v => norm_(mot).includes(norm_(v)));
      cambios.MOTIVACION = m || '';
      if (!m || norm_(mot) !== norm_(m)) notas.push('Motivacion: ' + mot);
    }
    if (notas.length) cambios.NOTAS = [f.NOTAS, ...notas].filter(Boolean).join(' | ');
    if (Object.keys(cambios).length) out.push({ fila: f._fila, cambios });
  });
  return out;
}

function limpiarBarrios(filas, canon) {
  const out = [];
  filas.forEach(f => {
    const cambios = {};
    const partir = s => String(s || '').split(/,|\/| y /).map(t => t.trim()).filter(Boolean);
    const ok = [], resto = [];
    partir(f['BUSCA BARRIOS']).forEach(t => { const c = canon[barrioN(t)]; c ? (ok.includes(c) || ok.push(c)) : resto.push(t); });
    const nuevo = ok.join(', ');
    if (nuevo !== String(f['BUSCA BARRIOS'] || '')) {
      cambios['BUSCA BARRIOS'] = nuevo;
      if (resto.length) cambios['BUSCA REQUISITOS'] = [f['BUSCA REQUISITOS'], 'Zona: ' + resto.join(', ')].filter(Boolean).join('. ');
    }
    const vb = canon[barrioN(f['VENDE BARRIO'])];
    if (f['VENDE BARRIO'] && vb && vb !== f['VENDE BARRIO']) cambios['VENDE BARRIO'] = vb;
    if (Object.keys(cambios).length) out.push({ fila: f._fila, cambios });
  });
  return out;
}

// Correr UNA vez a mano despues de pegar el codigo.
function instalar() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('mailDiario').timeBased().everyDays(1).atHour(7).nearMinute(0).create();
  // Leads de C21: cada 15 minutos (antes solo a las 7). Con un lead, la velocidad es lo que más pesa.
  ScriptApp.newTrigger('importarC21').timeBased().everyMinutes(15).create();
  const { sh, h, filas } = leer_();
  asegurarIds_(sh, h, filas);
  const cambiados = migrarEstados_(sh, h);
  const nombres = limpiarNombres_(sh, h);
  return 'Listo: mail diario a las 7, leads de C21 cada 15 minutos, IDs asignados, ' + cambiados + ' estados pasados a los nombres nuevos y ' + nombres + ' nombres limpiados.';
}

// En NOMBRE va solo el nombre: "Romi Ulloque - Depto 1-2amb..." -> "Romi Ulloque". El formato largo lo arma la app para WhatsApp.
function limpiarNombres_(sh, h) {
  const j = h.indexOf('NOMBRE'), n = sh.getLastRow() - 1;
  if (j < 0 || n < 1) return 0;
  const rg = sh.getRange(2, j + 1, n, 1), v = rg.getValues();
  let k = 0;
  v.forEach(r => { const b = nombreBase_(r[0]); if (r[0] && b && b !== String(r[0]).trim()) { r[0] = b; k++; } });
  if (k) rg.setValues(v);
  return k;
}

// Una sola vez (se puede repetir sin problema): pasa los estados viejos a los nuevos y actualiza las listas del Sheet.
function migrarEstados_(sh, h) {
  const jE = h.indexOf('ESTADO'), jM = h.indexOf('MOTIVO DESCARTE');
  const n = sh.getLastRow() - 1;
  if (jE < 0 || n < 1) return 0;
  const rE = sh.getRange(2, jE + 1, n, 1), rM = jM >= 0 ? sh.getRange(2, jM + 1, n, 1) : null;
  const est = rE.getValues(), mot = rM ? rM.getValues() : null;
  let k = 0;
  est.forEach((r, i) => {
    const v = String(r[0]).trim().toUpperCase();
    if (v === 'COMPRO CON OTRO' && mot && !mot[i][0]) mot[i][0] = 'COMPRO CON OTRO';
    const nv = estadoNuevo(v);
    if (r[0] && nv !== r[0]) { r[0] = nv; k++; }
  });
  const regla = l => SpreadsheetApp.newDataValidation().requireValueInList(l, true).build();
  rE.clearDataValidations(); rE.setValues(est); rE.setDataValidation(regla(ESTADOS));
  if (rM) { rM.clearDataValidations(); rM.setValues(mot); rM.setDataValidation(regla(MOTIVOS_DESCARTE)); }
  // Etapas de venta: CAPTADA -> EN VENTA (v25), y la lista nueva
  const jV = h.indexOf('ETAPA VENTA');
  if (jV >= 0) {
    const rV = sh.getRange(2, jV + 1, n, 1), ev = rV.getValues();
    ev.forEach(r => { const nv = ETAPA_VENTA_VIEJA[String(r[0]).trim().toUpperCase()]; if (nv) { r[0] = nv; k++; } });
    rV.clearDataValidations(); rV.setValues(ev); rV.setDataValidation(regla(ETAPAS_VENTA));
  }
  return k;
}
