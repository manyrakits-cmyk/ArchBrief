"""Testy spatial graphu: uzly podle id (fallback název), vztahy přes id i název."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from floorplan import build_spatial_graph, generate_floorplan_svg  # noqa: E402


def _model(spaces, relationships=()):
    return {"program": {"spaces": list(spaces), "relationships": list(relationships)}}


def test_relationships_by_id_resolve_to_nodes():
    nodes, edges = build_spatial_graph(_model(
        [
            {"id": "living", "name": "obývací pokoj", "area_target": 40},
            {"id": "kitchen", "name": "kuchyň", "area_target": 20},
        ],
        [{"from": "living", "to": "kitchen", "type": "direct"}],
    ))
    node_ids = {n["id"] for n in nodes}
    assert node_ids == {"living", "kitchen"}
    assert edges == [{"from": "living", "to": "kitchen", "type": "direct"}]


def test_relationships_by_name_still_work_when_spaces_have_id():
    nodes, edges = build_spatial_graph(_model(
        [
            {"id": "living", "name": "Obývací pokoj"},
            {"id": "kitchen", "name": "Kuchyň"},
        ],
        [{"from": "Obývací pokoj", "to": "Kuchyň", "type": "direct"}],
    ))
    assert edges[0]["from"] == "living" and edges[0]["to"] == "kitchen"


def test_legacy_spaces_without_id_keyed_by_name():
    nodes, edges = build_spatial_graph(_model(
        [{"name": "pracovna / pokoj pro hosty"}, {"name": "ložnice rodiny"}],
        [{"from": "pracovna / pokoj pro hosty", "to": "ložnice rodiny", "type": "odděleně"}],
    ))
    assert [n["id"] for n in nodes] == ["pracovna_pokoj_pro_hosty", "ložnice_rodiny"]
    assert edges == [{"from": "pracovna_pokoj_pro_hosty", "to": "ložnice_rodiny", "type": "buffered"}]


def test_same_name_different_id_are_separate_rooms():
    nodes, _ = build_spatial_graph(_model([
        {"id": "bathroom", "name": "Koupelna"},
        {"id": "guest_bathroom", "name": "Koupelna"},
    ]))
    assert [n["id"] for n in nodes] == ["bathroom", "guest_bathroom"]
    assert all(n["zone"] == "private" for n in nodes)


def test_zone_and_area_fall_back_to_id():
    nodes, _ = build_spatial_graph(_model([{"id": "kitchen", "name": "Vaření a stolování"}]))
    assert nodes[0]["zone"] == "shared"
    assert nodes[0]["area_target"] == 15.0
    assert nodes[0]["display_name"] == "Vaření a stolování"


def test_svg_draws_relationship_between_id_keyed_rooms():
    svg = generate_floorplan_svg(_model(
        [
            {"id": "living", "name": "obývací pokoj", "area_target": 40},
            {"id": "kitchen", "name": "kuchyň", "area_target": 20},
        ],
        [{"from": "living", "to": "kitchen", "type": "direct"}],
    ))
    assert "<line" in svg["svg"]
