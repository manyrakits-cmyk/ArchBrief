"""Testy formátování v PDF: rozpočet s měnou a oddělovači, výrazy oddělené čárkou, font s diakritikou."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdf_generator as p  # noqa: E402

NBSP = " "


def test_format_money():
    assert p._format_money(40000000) == f"40{NBSP}000{NBSP}000{NBSP}CZK"
    assert p._format_money(1_000_000, "EUR") == f"1{NBSP}000{NBSP}000{NBSP}EUR"
    assert p._format_money("40 000 000") == f"40{NBSP}000{NBSP}000{NBSP}CZK"
    assert p._format_money(950) == f"950{NBSP}CZK"
    assert p._format_money("cca 40 mil.") == "cca 40 mil."
    assert p._format_money(None) == ""


def test_format_budget_variants():
    assert p._format_budget({"target": 40000000, "currency": "CZK"}) == f"40{NBSP}000{NBSP}000{NBSP}CZK"
    assert p._format_budget({"target": 1000000, "max": 1200000}) == (
        f"1{NBSP}000{NBSP}000{NBSP}CZK (max 1{NBSP}200{NBSP}000{NBSP}CZK)"
    )
    assert p._format_budget({"max": 5000000, "currency": "EUR"}) == f"max 5{NBSP}000{NBSP}000{NBSP}EUR"
    assert p._format_budget({}) == "—"


def test_join_terms():
    assert p._join_terms(["minimalismus", "kámen", "bílá", "sklo"]) == "minimalismus, kámen, bílá, sklo"
    assert p._join_terms(["  kámen ", "", None]) == "kámen"
    assert p._join_terms([]) == "—"


def test_format_building():
    assert p._format_building({"floors": 1, "roof_type": "flat"}) == "1 podlaží (přízemní), plochá střecha"
    assert p._format_building({"floors": 2}) == "2 podlaží"
    assert p._format_building({}) == ""


def test_pdf_uses_font_with_czech_glyphs():
    from reportlab.pdfbase import pdfmetrics

    font = pdfmetrics.getFont(p.FONT)
    for ch in "čřěůňťďČŘŠŽ":
        assert ord(ch) in font.face.charToGlyph, ch


def test_generate_pdf_smoke():
    model = {
        "project": {"name": "Nový dům v Garganu", "type": "rodinný dům"},
        "intent": {"primary_goal": "přízemní dům u moře"},
        "building": {"floors": 1, "roof_type": "flat"},
        "style": {"keywords": ["minimalismus", "středomořská"], "materials": ["kámen", "sklo"]},
        "budget": {"target": 40000000, "currency": "CZK"},
        "program": {
            "spaces": [{"id": "living", "name": "obývací pokoj", "area_target": 45},
                       {"id": "kitchen", "name": "kuchyň", "area_target": 20}],
            "relationships": [{"from": "living", "to": "kitchen", "type": "direct"}],
        },
    }
    pdf = p.generate_pdf({"intent_model": model}, "demo@example.test")
    assert pdf.startswith(b"%PDF")
    assert b"DejaVuSans" in pdf
    # ReportLab Helveticu registruje jako výchozí font stránky; text ale musí jít přes DejaVu
    assert all(st.fontName.startswith("DejaVuSans") for st in p._styles().values())
