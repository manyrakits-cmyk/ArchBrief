"""
pdf_generator.py — ArchBrief Fáze 6: generátor PDF dokumentu

Struktura PDF:
  1. Titulní strana
  2. Shrnutí záměru
  3. AI vizualizace (pokud existuje)
  4. Schematický půdorys (SVG → PDF)
  5. Program: místnosti a vztahy
  6. Kompletní model záměru (JSON)
"""
from __future__ import annotations

import io
import json
import os
import tempfile
from datetime import date

import httpx
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from svglib.svglib import svg2rlg

# ── Konstanty ──────────────────────────────────────────────────────────────────

COLOR_GREEN = colors.HexColor("#1D9E75")
COLOR_GREEN_LIGHT = colors.HexColor("#D4E8D4")
COLOR_GRAY = colors.HexColor("#666666")
COLOR_MONO_BG = colors.HexColor("#F5F5F5")
PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# ── Fonty ──────────────────────────────────────────────────────────────────────
# Standardní Helvetica/Courier nemají glyfy pro č, ř, ě, ů, ň, ť, ď → DejaVu (backend/fonts).

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FONT = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
FONT_MONO = "DejaVuSansMono"

pdfmetrics.registerFont(TTFont(FONT, os.path.join(_FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont(FONT_MONO, os.path.join(_FONT_DIR, "DejaVuSansMono.ttf")))
# <b> v Paragraph → tučný řez
registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD, italic=FONT, boldItalic=FONT_BOLD)

ZONE_LABELS = {"public": "Veřejná", "shared": "Sdílená", "private": "Soukromá"}
ROOF_LABELS = {
    "flat": "plochá", "gable": "sedlová", "hip": "valbová",
    "shed": "pultová", "green": "zelená (vegetační)", "butterfly": "motýlí",
}
REL_LABELS = {"direct": "Přímé", "buffered": "Oddělené", "visual": "Vizuální"}

# ── Styly ──────────────────────────────────────────────────────────────────────

def _styles() -> dict:
    return {
        "title": ParagraphStyle(
            "title", fontSize=28, textColor=COLOR_GREEN,
            spaceAfter=6, fontName=FONT_BOLD,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontSize=14, textColor=COLOR_GRAY,
            spaceAfter=4, fontName=FONT,
        ),
        "h2": ParagraphStyle(
            "h2", fontSize=14, textColor=COLOR_GREEN,
            spaceBefore=10, spaceAfter=4, fontName=FONT_BOLD,
        ),
        "body": ParagraphStyle(
            "body", fontSize=10, textColor=colors.black,
            spaceAfter=3, leading=14, fontName=FONT,
        ),
        "small": ParagraphStyle(
            "small", fontSize=8, textColor=COLOR_GRAY,
            spaceAfter=2, fontName=FONT,
        ),
        "mono": ParagraphStyle(
            "mono", fontSize=8, fontName=FONT_MONO,
            spaceAfter=0, leading=11, backColor=COLOR_MONO_BG,
        ),
        "label": ParagraphStyle(
            "label", fontSize=9, textColor=COLOR_GRAY,
            fontName=FONT_BOLD, spaceAfter=3,
        ),
    }


# ── Pomocné funkce ─────────────────────────────────────────────────────────────

def _safe_str(v) -> str:
    if v is None or v == "" or v == [] or v == {}:
        return "—"
    if isinstance(v, list):
        parts = []
        for item in v:
            if isinstance(item, dict):
                parts.append(", ".join(f"{k}: {val}" for k, val in item.items() if val))
            elif item:
                parts.append(str(item))
        return "; ".join(parts) if parts else "—"
    return str(v)


def _join_terms(v) -> str:
    """Seznam výrazů (keywords, materiály) → „minimalismus, kámen, bílá"."""
    if isinstance(v, str):
        return v.strip() or "—"
    if not isinstance(v, list):
        return "—"
    terms = [str(t).strip() for t in v if t is not None and str(t).strip()]
    return ", ".join(terms) if terms else "—"


def _format_money(value, currency: str = "CZK") -> str:
    """
    40000000 → „40 000 000 CZK" (oddělovač tisíců = nezlomitelná mezera).
    Text, který není číslo („cca 40 mil."), se vrátí beze změny.
    """
    if value is None or value == "":
        return ""
    number = None
    if isinstance(value, bool):
        number = None
    elif isinstance(value, (int, float)):
        number = value
    elif isinstance(value, str):
        cleaned = value.replace(" ", "").replace(" ", "").replace(",", ".")
        try:
            number = float(cleaned)
        except ValueError:
            return value.strip()
    if number is None:
        return str(value)
    formatted = f"{round(number):,}".replace(",", " ")
    return f"{formatted} {currency}" if currency else formatted


def _format_budget(budget: dict) -> str:
    """„40 000 000 CZK (max 45 000 000 CZK)" / „max 45 000 000 CZK" / „40 000 000 CZK"."""
    budget = budget or {}
    raw_currency = budget.get("currency")
    currency = raw_currency.strip() if isinstance(raw_currency, str) and raw_currency.strip() else "CZK"
    target = _format_money(budget.get("target"), currency)
    maximum = _format_money(budget.get("max"), currency)
    if target and maximum:
        return f"{target} (max {maximum})"
    if maximum:
        return f"max {maximum}"
    return target or "—"


def _format_building(building: dict) -> str:
    """„1 podlaží, plochá střecha"."""
    building = building or {}
    parts = []
    floors = building.get("floors")
    if isinstance(floors, (int, float)) and not isinstance(floors, bool) and floors > 0:
        parts.append(f"{floors:g} podlaží" if floors != 1 else "1 podlaží (přízemní)")
    roof = (building.get("roof_type") or "").strip()
    if roof:
        parts.append(f"{ROOF_LABELS.get(roof.lower(), roof)} střecha")
    return ", ".join(parts)


def _download_image(url: str) -> bytes | None:
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def _svg_to_drawing(svg_string: str):
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".svg", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write(svg_string)
            tmp = f.name
        drawing = svg2rlg(tmp)
        os.unlink(tmp)
        return drawing
    except Exception:
        return None


def _table_style(has_header: bool = True) -> TableStyle:
    cmds = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1 if has_header else 0), (-1, -1),
         [colors.white, COLOR_GREEN_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if has_header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ]
    return TableStyle(cmds)


# ── Sekce dokumentu ────────────────────────────────────────────────────────────

def _section_title(story: list, intent_model: dict, user_email: str, s: dict) -> None:
    project = (intent_model or {}).get("project") or {}
    project_name = project.get("name") or "Nový projekt"
    today = date.today().strftime("%d. %m. %Y")

    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("ArchBrief", s["title"]))
    story.append(Paragraph(_safe_str(project_name), s["subtitle"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Připraveno pro předání architektovi", s["small"]))
    story.append(Paragraph(today, s["small"]))
    if user_email:
        story.append(Paragraph(user_email, s["small"]))
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width=CONTENT_W, color=COLOR_GREEN, thickness=1.5))


def _section_summary(story: list, intent_model: dict, s: dict) -> None:
    m = intent_model or {}
    intent = m.get("intent") or {}
    site = m.get("site") or {}
    plot = site.get("plot") or {}
    style = m.get("style") or {}
    budget = m.get("budget") or {}
    conflicts = m.get("conflicts") or []
    users = m.get("users") or []
    project = m.get("project") or {}

    story.append(Paragraph("Shrnutí záměru", s["h2"]))

    rows = [
        ("Primární cíl", _safe_str(intent.get("primary_goal"))),
        ("Typ projektu", _safe_str(project.get("type"))),
        ("Lokalita", _safe_str(site.get("location"))),
    ]
    if plot.get("width") or plot.get("depth"):
        rows.append(("Parcela", f"{plot.get('width', '?')} × {plot.get('depth', '?')} m"))
    if users:
        rows.append(("Uživatelé", _safe_str(users)))
    building_str = _format_building(m.get("building") or {})
    if building_str:
        rows.append(("Hmota", building_str))
    if style.get("keywords") or style.get("atmosphere"):
        kw = _join_terms(style.get("keywords"))
        atm = _safe_str(style.get("atmosphere"))
        if kw == "—":
            rows.append(("Styl", atm))
        else:
            rows.append(("Styl", f"{kw} — {atm}" if atm != "—" else kw))
    if style.get("materials"):
        rows.append(("Materiály", _join_terms(style.get("materials"))))
    if budget.get("target") or budget.get("max"):
        rows.append(("Rozpočet", _format_budget(budget)))
    if conflicts:
        rows.append(("Konflikty", _safe_str(conflicts)))

    for label, value in rows:
        story.append(
            Paragraph(f"<b>{label}:</b> {value}", s["body"])
        )


def _section_image(story: list, generated_image_url: str | None,
                   image_prompt: str | None, s: dict) -> None:
    story.append(Paragraph("Vizualizace", s["h2"]))
    if not generated_image_url:
        story.append(Paragraph("Vizualizace nebyla vygenerována.", s["small"]))
        return

    img_bytes = _download_image(generated_image_url)
    if img_bytes:
        buf = io.BytesIO(img_bytes)
        img = Image(buf)
        # Zachovat poměr stran, max šířka = CONTENT_W
        ratio = img.imageWidth / img.imageHeight if img.imageHeight else 1
        img.drawWidth = CONTENT_W
        img.drawHeight = CONTENT_W / ratio
        story.append(img)
        if image_prompt:
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(image_prompt, s["small"]))
    else:
        story.append(Paragraph("Vizualizaci se nepodařilo načíst.", s["small"]))


def _section_floorplan(story: list, floorplan_svg: str | None, s: dict) -> None:
    story.append(Paragraph("Schematický půdorys", s["h2"]))
    if not floorplan_svg:
        story.append(Paragraph("Půdorys nebyl vygenerován.", s["small"]))
        return

    drawing = _svg_to_drawing(floorplan_svg)
    if drawing is None:
        story.append(Paragraph("Půdorys se nepodařilo převést.", s["small"]))
        return

    # Škálovat na CONTENT_W
    scale = CONTENT_W / drawing.width if drawing.width else 1
    drawing.width = CONTENT_W
    drawing.height = drawing.height * scale
    drawing.transform = (scale, 0, 0, scale, 0, 0)
    story.append(drawing)

    # Legenda
    story.append(Spacer(1, 3 * mm))
    legend_data = [
        [colors.HexColor("#E8E8E8"), "Veřejná zóna (garáž, terasa, zahrada)"],
        [colors.HexColor("#D4E8D4"), "Sdílená zóna (obývák, kuchyň, jídelna)"],
        [colors.HexColor("#D4E0F0"), "Soukromá zóna (ložnice, koupelna, pracovna)"],
    ]
    for color, label in legend_data:
        tbl = Table(
            [["", label]],
            colWidths=[8 * mm, CONTENT_W - 8 * mm],
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), color),
            ("GRID", (0, 0), (0, 0), 0.5, colors.HexColor("#CCCCCC")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (1, 0), (1, 0), 4),
        ]))
        story.append(tbl)


def _section_program(story: list, intent_model: dict, s: dict) -> None:
    from floorplan import ZONE_MAP, _normalize_key, _infer_zone

    story.append(Paragraph("Prostorový program", s["h2"]))
    program = (intent_model or {}).get("program") or {}
    spaces = program.get("spaces") or []
    relationships = program.get("relationships") or []

    if spaces:
        header = [["Místnost", "Zóna", "Plocha (m²)"]]
        rows = []
        for space in spaces:
            if isinstance(space, dict):
                name = space.get("name") or "—"
                area = space.get("area_target") or space.get("area") or "—"
            else:
                name = str(space)
                area = "—"
            key = _normalize_key(name)
            zone_key = ZONE_MAP.get(key) or _infer_zone(name.lower())
            zone_label = ZONE_LABELS.get(zone_key, zone_key)
            rows.append([name, zone_label, str(area) if area != "—" else "—"])

        tbl = Table(header + rows, colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.3, CONTENT_W * 0.2])
        tbl.setStyle(_table_style(has_header=True))
        story.append(tbl)
    else:
        story.append(Paragraph("Program nebyl specifikován.", s["small"]))

    if relationships:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Prostorové vztahy", s["label"]))
        header = [["Od", "Do", "Typ"]]
        rows = []
        # vztahy odkazují na id prostorů → zobrazit název
        names_by_id = {
            str(sp["id"]): sp.get("name") or str(sp["id"])
            for sp in spaces if isinstance(sp, dict) and sp.get("id")
        }
        for rel in relationships:
            if not isinstance(rel, dict):
                continue
            rel_type = (rel.get("type") or "").lower()
            rows.append([
                names_by_id.get(str(rel.get("from")), rel.get("from")) or "—",
                names_by_id.get(str(rel.get("to")), rel.get("to")) or "—",
                REL_LABELS.get(rel_type, rel_type or "—"),
            ])
        if rows:
            tbl = Table(header + rows, colWidths=[CONTENT_W * 0.4, CONTENT_W * 0.4, CONTENT_W * 0.2])
            tbl.setStyle(_table_style(has_header=True))
            story.append(tbl)


def _section_json(story: list, intent_model: dict, s: dict) -> None:
    story.append(PageBreak())
    story.append(Paragraph("Model záměru", s["h2"]))
    story.append(Paragraph(
        "Kompletní datový model pro předání architektovi.", s["small"]
    ))
    story.append(Spacer(1, 2 * mm))

    json_str = json.dumps(intent_model, ensure_ascii=False, indent=2)
    for line in json_str.splitlines():
        # Escapovat HTML znaky v JSON
        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Zachovat odsazení pomocí non-breaking spaces
        leading = len(line) - len(line.lstrip())
        indent_str = " " * leading
        story.append(Paragraph(indent_str + escaped.lstrip(), s["mono"]))


# ── Hlavní vstupní bod ─────────────────────────────────────────────────────────

def generate_pdf(session_data: dict, user_email: str) -> bytes:
    """
    Vygeneruje PDF dokument z dat session.
    Vrátí PDF jako bytes.
    """
    intent_model = session_data.get("intent_model") or {}
    generated_image_url = session_data.get("generated_image_url")
    image_prompt = session_data.get("image_prompt")
    floorplan_svg = session_data.get("floorplan_svg")

    s = _styles()
    story: list = []

    _section_title(story, intent_model, user_email, s)
    story.append(PageBreak())

    _section_summary(story, intent_model, s)
    story.append(Spacer(1, 4 * mm))

    _section_image(story, generated_image_url, image_prompt, s)
    story.append(Spacer(1, 4 * mm))

    _section_floorplan(story, floorplan_svg, s)
    story.append(Spacer(1, 4 * mm))

    _section_program(story, intent_model, s)

    _section_json(story, intent_model, s)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    doc.build(story)
    return buf.getvalue()
