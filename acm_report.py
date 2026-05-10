"""
acm_report.py — Generador de informe ACM en formato .docx
"""

from datetime import date
from io import BytesIO

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

COLOR_PRIMARY = RGBColor(0x00, 0x31, 0x53)
COLOR_ORANGE  = RGBColor(0xE8, 0x63, 0x0A)
COLOR_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
COLOR_GRAY    = RGBColor(0x6B, 0x72, 0x80)
COLOR_LIGHT   = RGBColor(0xE8, 0xF0, 0xF8)

_MESES = {
    "January": "enero", "February": "febrero", "March": "marzo",
    "April": "abril", "May": "mayo", "June": "junio",
    "July": "julio", "August": "agosto", "September": "septiembre",
    "October": "octubre", "November": "noviembre", "December": "diciembre",
}


# ─── Format helpers ────────────────────────────────────────────────────────────

def fmt_usd(n) -> str:
    if n is None or n == 0:
        return "—"
    try:
        return f"USD {int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def fmt_ars(n) -> str:
    if n is None or n == 0:
        return "—"
    try:
        return f"$ {int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


def fecha_es() -> str:
    hoy = date.today()
    mes_en = hoy.strftime("%B")
    return hoy.strftime(f"%d de {_MESES.get(mes_en, mes_en)} de %Y")


# ─── docx helpers ─────────────────────────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color.lstrip("#"))
    tcPr.append(shd)


def _cell_text(cell, text: str, bold=False, color=None, size=10, align=None, italic=False):
    cell.text = ""
    para = cell.paragraphs[0]
    if align is not None:
        para.alignment = align
    run = para.add_run(str(text))
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = "Calibri"
    if color:
        run.font.color.rgb = color


def _section_title(doc: Document, text: str, space_before: float = 14):
    p = doc.add_paragraph()
    p.clear()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(13)
    run.font.name = "Calibri"
    run.font.color.rgb = COLOR_PRIMARY
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(4)
    return p


def _orange_line(doc: Document):
    """Adds a thin orange paragraph border as a visual divider."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:color"), "E8630A")
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_hyperlink(paragraph, url: str, text: str):
    """Adds a clickable hyperlink to a paragraph."""
    try:
        part = paragraph.part
        r_id = part.relate_to(
            url,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
            is_external=True,
        )
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), r_id)
        new_run = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "E8630A")
        rPr.append(color)
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rPr.append(u)
        font = OxmlElement("w:rFonts")
        font.set(qn("w:ascii"), "Calibri")
        rPr.append(font)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "18")  # 9pt
        rPr.append(sz)
        new_run.append(rPr)
        t = OxmlElement("w:t")
        t.text = text
        new_run.append(t)
        hyperlink.append(new_run)
        paragraph._p.append(hyperlink)
    except Exception:
        paragraph.add_run(text)


def _set_col_widths(table, widths_cm: list):
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            if i < len(widths_cm):
                cell.width = Cm(widths_cm[i])


# ─── Main function ─────────────────────────────────────────────────────────────

def generar_docx(
    datos_propiedad: dict,
    comparables: list,
    stats: dict,
    top3_indices: list,
    precio_final: float,
) -> bytes:

    doc = Document()

    # Página A4, márgenes 2cm
    for section in doc.sections:
        section.page_height = Cm(29.7)
        section.page_width  = Cm(21.0)
        section.top_margin    = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin   = Cm(2.0)
        section.right_margin  = Cm(2.0)

        # Footer
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.clear()
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run1 = fp.add_run("Nahuel Lim · Asesor Inmobiliario · nahuelim.com.ar")
        run1.font.size = Pt(8)
        run1.font.name = "Calibri"
        run1.font.color.rgb = COLOR_GRAY
        fp.add_run("\n")
        run2 = fp.add_run(
            "Valores de oferta publicada. No representan precios de cierre. "
            "La información es orientativa y no constituye asesoramiento legal ni financiero."
        )
        run2.font.size = Pt(7)
        run2.font.name = "Calibri"
        run2.font.color.rgb = COLOR_GRAY
        run2.italic = True

    # ── HEADER ──────────────────────────────────────────────────────────────────
    p_title = doc.add_paragraph()
    r_title = p_title.add_run("Análisis Comparativo de Mercado")
    r_title.bold = True
    r_title.font.size = Pt(22)
    r_title.font.name = "Calibri"
    r_title.font.color.rgb = COLOR_PRIMARY
    p_title.paragraph_format.space_after = Pt(2)

    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run("Nahuel Lim · Asesor Inmobiliario")
    r_sub.font.size = Pt(11)
    r_sub.font.name = "Calibri"
    r_sub.font.color.rgb = COLOR_GRAY
    p_sub.paragraph_format.space_after = Pt(2)

    p_fecha = doc.add_paragraph()
    r_fecha = p_fecha.add_run(f"Fecha: {fecha_es()}")
    r_fecha.font.size = Pt(10)
    r_fecha.font.name = "Calibri"
    r_fecha.font.color.rgb = COLOR_GRAY
    p_fecha.paragraph_format.space_after = Pt(6)

    _orange_line(doc)

    # ── SECCIÓN 1: Propiedad Analizada ──────────────────────────────────────────
    _section_title(doc, "1. Propiedad Analizada")

    campos = [
        ("Dirección",          datos_propiedad.get("direccion") or "—"),
        ("Barrio",             datos_propiedad.get("barrio") or "—"),
        ("Tipo",               datos_propiedad.get("tipo") or "—"),
        ("Ambientes",          str(datos_propiedad.get("ambientes") or "—")),
        ("M² cubiertos",       f'{datos_propiedad.get("sup_cubierta") or "—"} m²'),
    ]
    if datos_propiedad.get("sup_semicubierta") and float(datos_propiedad.get("sup_semicubierta", 0) or 0) > 0:
        campos.append(("M² semicubiertos", f'{datos_propiedad["sup_semicubierta"]} m²'))
    if datos_propiedad.get("antiguedad"):
        campos.append(("Antigüedad", f'{datos_propiedad["antiguedad"]} años'))
    if datos_propiedad.get("piso"):
        campos.append(("Piso", str(datos_propiedad["piso"])))
    if datos_propiedad.get("disposicion"):
        campos.append(("Disposición", datos_propiedad["disposicion"]))
    campos.append(("Cochera",      "Sí" if datos_propiedad.get("cochera") else "No"))
    campos.append(("Apto crédito", "Sí" if datos_propiedad.get("apto_credito") else "No"))
    if datos_propiedad.get("expensas"):
        campos.append(("Expensas est.", fmt_ars(datos_propiedad["expensas"])))
    if datos_propiedad.get("estado"):
        campos.append(("Estado del inmueble", datos_propiedad["estado"]))

    t1 = doc.add_table(rows=1, cols=2)
    t1.style = "Table Grid"
    hdr = t1.rows[0].cells
    _set_cell_bg(hdr[0], "003153")
    _set_cell_bg(hdr[1], "003153")
    _cell_text(hdr[0], "Campo", bold=True, color=COLOR_WHITE, size=10)
    _cell_text(hdr[1], "Valor", bold=True, color=COLOR_WHITE, size=10)

    for i, (campo, valor) in enumerate(campos):
        row = t1.add_row()
        bg = "EEF3F8" if i % 2 == 0 else "FFFFFF"
        _set_cell_bg(row.cells[0], bg)
        _set_cell_bg(row.cells[1], bg)
        _cell_text(row.cells[0], campo, bold=True, size=10)
        _cell_text(row.cells[1], valor, size=10)

    doc.add_paragraph()

    # ── SECCIÓN 2: Resumen de Mercado ───────────────────────────────────────────
    _section_title(doc, "2. Resumen de Mercado")

    mediana_m2 = stats.get("mediana_m2", 0)
    p25 = stats.get("p25", 0)
    p75 = stats.get("p75", 0)
    radio = stats.get("radio_metros", 0)
    stock = stats.get("stock_barrio", 0)
    n_usados = stats.get("n_usados", 0)
    n_total = stats.get("n_total", 0)
    precio_sugerido = stats.get("precio_sugerido", 0)
    rango_min = stats.get("rango_min", 0)
    rango_max = stats.get("rango_max", 0)

    rango_mkt = (
        f"USD {p25:,.0f} – USD {p75:,.0f}".replace(",", ".")
        if p25 and p75 else "—"
    )

    t2 = doc.add_table(rows=1, cols=2)
    t2.style = "Table Grid"
    hdr2 = t2.rows[0].cells
    _set_cell_bg(hdr2[0], "003153")
    _set_cell_bg(hdr2[1], "003153")
    _cell_text(hdr2[0], "Indicador", bold=True, color=COLOR_WHITE, size=10)
    _cell_text(hdr2[1], "Valor", bold=True, color=COLOR_WHITE, size=10)

    estado       = datos_propiedad.get("estado", "Buen estado")
    coef_estado  = float(datos_propiedad.get("coef_estado", 0.0) or 0.0)
    precio_ajust = datos_propiedad.get("precio_ajustado", 0) or 0

    coef_pct = (
        f"+{int(round(coef_estado * 100))}%"
        if coef_estado > 0
        else (f"{int(round(coef_estado * 100))}%" if coef_estado < 0 else "0% (sin ajuste)")
    )

    stats_rows = [
        ("Mediana precio/m²",             fmt_usd(mediana_m2),                              False),
        ("Rango P25–P75",                  rango_mkt,                                        False),
        ("Radio de análisis",              f"{radio} metros",                                False),
        ("Stock en zona",                  f"{stock} propiedades",                           False),
        ("Comparables utilizados",         f"{n_usados} (de {n_total} analizados)",          False),
        ("Precio sugerido (mediana pura)", fmt_usd(precio_sugerido),                         False),
        (f"Ajuste por estado ({estado})",  coef_pct,                                         False),
        ("Precio ajustado por estado",     fmt_usd(precio_ajust),                            False),
        ("Rango estimado",                 f"{fmt_usd(rango_min)} – {fmt_usd(rango_max)}",   False),
    ]

    for i, (label, valor, _) in enumerate(stats_rows):
        row = t2.add_row()
        bg = "EEF3F8" if i % 2 == 0 else "FFFFFF"
        _set_cell_bg(row.cells[0], bg)
        _set_cell_bg(row.cells[1], bg)
        _cell_text(row.cells[0], label, bold=True, size=10)
        _cell_text(row.cells[1], valor, size=10)

    # Fila destacada en naranja: PRECIO FINAL CONFIRMADO
    row_final = t2.add_row()
    _set_cell_bg(row_final.cells[0], "E8630A")
    _set_cell_bg(row_final.cells[1], "E8630A")
    _cell_text(row_final.cells[0], "PRECIO FINAL CONFIRMADO", bold=True, color=COLOR_WHITE, size=11)
    _cell_text(row_final.cells[1], fmt_usd(precio_final), bold=True, color=COLOR_WHITE, size=11)

    doc.add_paragraph()

    # ── SECCIÓN 3: Top 3 Comparables ────────────────────────────────────────────
    if top3_indices and comparables:
        _section_title(doc, "3. Top 3 Comparables Más Similares")

        for idx in top3_indices:
            if idx >= len(comparables):
                continue
            comp = comparables[idx]

            # Bloque con borde izquierdo naranja usando tabla 2 cols (decoración + contenido)
            t_comp = doc.add_table(rows=1, cols=2)
            t_comp.style = "Table Grid"

            # Col izquierda: borde naranja (2mm de ancho)
            left_cell = t_comp.rows[0].cells[0]
            _set_cell_bg(left_cell, "E8630A")
            left_cell.width = Cm(0.4)
            left_cell.text = ""

            right_cell = t_comp.rows[0].cells[1]
            _set_cell_bg(right_cell, "FFFFFF")

            # Contenido de la card
            right_cell.text = ""
            for para in right_cell.paragraphs:
                para.clear()

            def add_right_para(text="", bold=False, size=10, color=None, italic=False):
                p = right_cell.add_paragraph()
                if text:
                    r = p.add_run(text)
                    r.bold = bold
                    r.italic = italic
                    r.font.size = Pt(size)
                    r.font.name = "Calibri"
                    if color:
                        r.font.color.rgb = color
                return p

            # Limpia el párrafo inicial vacío
            right_cell.paragraphs[0].clear()

            # Dirección
            p_dir = right_cell.paragraphs[0]
            r_dir = p_dir.add_run(comp.get("direccion") or comp.get("barrio") or "—")
            r_dir.bold = True
            r_dir.font.size = Pt(12)
            r_dir.font.name = "Calibri"
            r_dir.font.color.rgb = COLOR_PRIMARY

            # Precio total (naranja, grande)
            p_precio = right_cell.add_paragraph()
            r_precio = p_precio.add_run(fmt_usd(comp.get("precio")))
            r_precio.bold = True
            r_precio.font.size = Pt(14)
            r_precio.font.name = "Calibri"
            r_precio.font.color.rgb = COLOR_ORANGE

            # Fila de datos
            ficha_parts = []
            if comp.get("ambientes"):
                ficha_parts.append(f"{comp['ambientes']} amb")
            if comp.get("sup_cubierta"):
                ficha_parts.append(f"{int(comp['sup_cubierta'])} m²")
            if comp.get("piso") is not None:
                ficha_parts.append(f"Piso {comp['piso']}")
            if comp.get("disposicion"):
                ficha_parts.append(comp["disposicion"])
            if comp.get("antiguedad"):
                ficha_parts.append(f"{comp['antiguedad']} años")
            if comp.get("cochera"):
                ficha_parts.append("✓ Cochera")

            if ficha_parts:
                p_ficha = right_cell.add_paragraph()
                r_ficha = p_ficha.add_run(" · ".join(ficha_parts))
                r_ficha.font.size = Pt(9.5)
                r_ficha.font.name = "Calibri"
                r_ficha.font.color.rgb = COLOR_GRAY

            # USD/m²
            p_m2 = right_cell.add_paragraph()
            r_m2 = p_m2.add_run(f"USD/m²: {fmt_usd(comp.get('precio_por_m2'))}")
            r_m2.font.size = Pt(9.5)
            r_m2.font.name = "Calibri"

            # Expensas
            if comp.get("expensas"):
                p_exp = right_cell.add_paragraph()
                r_exp = p_exp.add_run(f"Expensas: {fmt_ars(comp['expensas'])}/mes")
                r_exp.font.size = Pt(9)
                r_exp.font.name = "Calibri"
                r_exp.font.color.rgb = COLOR_GRAY

            # Link
            p_link = right_cell.add_paragraph()
            if comp.get("url"):
                _add_hyperlink(p_link, comp["url"], "Ver en ZonaProp →")

            doc.add_paragraph()

    # ── SECCIÓN 4: Tabla de Comparables ─────────────────────────────────────────
    _section_title(doc, "4. Tabla de Comparables")

    top3_set = set(top3_indices)
    show_list = comparables[:15]

    if show_list:
        t5 = doc.add_table(rows=1, cols=9)
        t5.style = "Table Grid"

        col_headers = ["", "Dirección", "Dist.", "Amb", "m²", "Piso", "USD/m²", "Precio", "Link"]
        hdr5 = t5.rows[0].cells
        for i, h in enumerate(col_headers):
            _set_cell_bg(hdr5[i], "003153")
            alg = WD_ALIGN_PARAGRAPH.LEFT if i == 1 else WD_ALIGN_PARAGRAPH.CENTER
            _cell_text(hdr5[i], h, bold=True, color=COLOR_WHITE, size=8, align=alg)

        for j, comp in enumerate(show_list):
            row = t5.add_row()
            is_top3 = j in top3_set
            bg = "D6E4F0" if is_top3 else ("F4F4F4" if j % 2 == 0 else "FFFFFF")
            for cell in row.cells:
                _set_cell_bg(cell, bg)

            star    = "★" if is_top3 else ""
            dir_txt = (comp.get("direccion") or comp.get("barrio") or "—")[:40]
            dist_txt = (
                f"{comp['distancia_metros']}m" if comp.get("distancia_metros") else "—"
            )
            amb_txt  = str(comp.get("ambientes") or "—")
            sup_txt  = str(int(comp["sup_cubierta"])) if comp.get("sup_cubierta") else "—"
            piso_txt = str(comp.get("piso")) if comp.get("piso") is not None else "—"
            m2_txt   = fmt_usd(int(comp["precio_por_m2"])) if comp.get("precio_por_m2") else "—"
            tot_txt  = fmt_usd(int(comp["precio"])) if comp.get("precio") else "—"

            _cell_text(row.cells[0], star, size=8, align=WD_ALIGN_PARAGRAPH.CENTER,
                       color=COLOR_ORANGE if is_top3 else None)
            _cell_text(row.cells[1], dir_txt, size=8)
            _cell_text(row.cells[2], dist_txt, size=8, align=WD_ALIGN_PARAGRAPH.CENTER)
            _cell_text(row.cells[3], amb_txt, size=8, align=WD_ALIGN_PARAGRAPH.CENTER)
            _cell_text(row.cells[4], sup_txt, size=8, align=WD_ALIGN_PARAGRAPH.CENTER)
            _cell_text(row.cells[5], piso_txt, size=8, align=WD_ALIGN_PARAGRAPH.CENTER)
            _cell_text(row.cells[6], m2_txt, size=8, align=WD_ALIGN_PARAGRAPH.CENTER)
            _cell_text(row.cells[7], tot_txt, size=8, align=WD_ALIGN_PARAGRAPH.CENTER)

            # Link cell
            row.cells[8].text = ""
            p_link = row.cells[8].paragraphs[0]
            p_link.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if comp.get("url"):
                _add_hyperlink(p_link, comp["url"], "Ver →")

        # Nota al pie
        p_nota = doc.add_paragraph()
        r_nota = p_nota.add_run("★ Alta similitud con la propiedad analizada")
        r_nota.font.size = Pt(8)
        r_nota.font.color.rgb = COLOR_GRAY
        r_nota.italic = True

    doc.add_paragraph()

    # ── SECCIÓN 5: Ajustes Manuales ──────────────────────────────────────────────
    _section_title(doc, "5. Ajustes Manuales Post-visita")

    p_nota6 = doc.add_paragraph()
    r_nota6 = p_nota6.add_run("Completar después de la visita.")
    r_nota6.font.size = Pt(9)
    r_nota6.font.name = "Calibri"
    r_nota6.font.color.rgb = COLOR_GRAY
    r_nota6.italic = True
    p_nota6.paragraph_format.space_after = Pt(4)

    t6 = doc.add_table(rows=1, cols=4)
    t6.style = "Table Grid"
    ajuste_headers = ["Factor", "Ajuste %", "Impacto USD", "Notas"]
    hdr6 = t6.rows[0].cells
    for i, h in enumerate(ajuste_headers):
        _set_cell_bg(hdr6[i], "003153")
        _cell_text(hdr6[i], h, bold=True, color=COLOR_WHITE, size=9)

    ajuste_factores = [
        "Piso / altura",
        "Estado conservación",
        "Calidad constructiva",
        "Orientación",
        "Entorno inmediato",
        "Documentación",
        "PRECIO AJUSTADO FINAL",
    ]
    for i, factor in enumerate(ajuste_factores):
        row = t6.add_row()
        is_total = factor.startswith("PRECIO")
        bg = "E8630A" if is_total else ("EEF3F8" if i % 2 == 0 else "FFFFFF")
        col = COLOR_WHITE if is_total else None
        for cell in row.cells:
            _set_cell_bg(cell, bg)
        _cell_text(row.cells[0], factor, bold=is_total, color=col, size=9)
        _cell_text(row.cells[1], "", size=9)
        _cell_text(row.cells[2], "", size=9)
        _cell_text(row.cells[3], "", size=9)

    # Guardar en bytes
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
