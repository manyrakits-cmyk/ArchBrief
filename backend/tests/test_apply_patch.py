"""
Testy Model Update Rule: program.spaces / program.relationships / conflicts
se mergují podle id, nikdy se nepřepisují ani nemažou.

Spuštění:  cd backend && python -m pytest
"""
from __future__ import annotations

import os
import sys
from copy import deepcopy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archbrief_cli import EMPTY_MODEL, apply_patch  # noqa: E402


def _ids(model: dict) -> list[str]:
    return [s.get("id") or s.get("name") for s in model["program"]["spaces"]]


HOUSE_PATCH = {
    "project": {"type": "rodinný dům"},
    "program": {
        "spaces": [
            {"id": "living", "name": "obývací pokoj", "area_target": 45},
            {"id": "kitchen", "name": "kuchyň", "area_target": 22},
            {"id": "bedroom_master", "name": "ložnice", "area_target": 20},
        ],
        "relationships": [{"from": "living", "to": "kitchen", "type": "direct"}],
    },
}

GUEST_PATCH = {
    "program": {
        "spaces": [
            {"id": "guest_bedroom", "name": "hostovský pokoj", "area_target": 20},
            {"id": "guest_bathroom", "name": "hostovská koupelna", "area_target": 8},
            {"id": "guest_kitchenette", "name": "kuchyňský kout", "area_target": 26},
        ],
        "relationships": [{"from": "guest_bedroom", "to": "guest_bathroom", "type": "direct"}],
    },
}


def test_later_patch_does_not_drop_existing_spaces():
    """Scénář „Nový dům v Garganu": dům, pak hostovská jednotka → v modelu je obojí."""
    model = apply_patch(EMPTY_MODEL, HOUSE_PATCH)
    model = apply_patch(model, GUEST_PATCH)

    assert _ids(model) == [
        "living", "kitchen", "bedroom_master",
        "guest_bedroom", "guest_bathroom", "guest_kitchenette",
    ]
    assert len(model["program"]["relationships"]) == 2


def test_update_existing_space_by_id_keeps_other_fields():
    model = apply_patch(EMPTY_MODEL, HOUSE_PATCH)
    model = apply_patch(model, {"program": {"spaces": [
        {"id": "living", "area_target": 60, "note": "hostíme často 20 lidí"},
    ]}})

    living = model["program"]["spaces"][0]
    assert living == {
        "id": "living", "name": "obývací pokoj", "area_target": 60,
        "note": "hostíme často 20 lidí",
    }
    assert len(model["program"]["spaces"]) == 3


def test_none_in_space_patch_does_not_erase_data():
    model = apply_patch(EMPTY_MODEL, HOUSE_PATCH)
    model = apply_patch(model, {"program": {"spaces": [{"id": "kitchen", "area_target": None}]}})
    assert model["program"]["spaces"][1]["area_target"] == 22


def test_legacy_spaces_without_id_match_by_name_and_keep_id():
    """Starší modely v Supabase mají prostory bez id — párujeme podle názvu."""
    legacy = deepcopy(EMPTY_MODEL)
    legacy["program"]["spaces"] = [{"name": "Kuchyň", "note": "vaříme spolu"}]

    model = apply_patch(legacy, {"program": {"spaces": [
        {"id": "kitchen", "name": "kuchyň", "area_target": 18},
    ]}})
    assert model["program"]["spaces"] == [
        {"name": "kuchyň", "note": "vaříme spolu", "id": "kitchen", "area_target": 18},
    ]

    # update bez id se spáruje podle názvu a id zůstane
    model = apply_patch(model, {"program": {"spaces": [{"name": "Kuchyň", "area_target": 20}]}})
    assert len(model["program"]["spaces"]) == 1
    assert model["program"]["spaces"][0]["id"] == "kitchen"
    assert model["program"]["spaces"][0]["area_target"] == 20


def test_same_name_different_id_are_distinct_spaces():
    """Dvě dětské ložnice se stejným názvem jsou dva prostory."""
    model = apply_patch(EMPTY_MODEL, {"program": {"spaces": [
        {"id": "bedroom_child_1", "name": "dětský pokoj"},
        {"id": "bedroom_child_2", "name": "dětský pokoj"},
    ]}})
    assert _ids(model) == ["bedroom_child_1", "bedroom_child_2"]


def test_relationships_are_not_duplicated_or_overwritten():
    model = apply_patch(EMPTY_MODEL, HOUSE_PATCH)
    # stejná dvojice (i v opačném směru) = update, ne nový vztah
    model = apply_patch(model, {"program": {"relationships": [
        {"from": "kitchen", "to": "living", "note": "otevřený prostor"},
    ]}})
    rels = model["program"]["relationships"]
    assert rels == [{"from": "living", "to": "kitchen", "type": "direct", "note": "otevřený prostor"}]


def test_conflicts_are_appended_not_replaced():
    model = apply_patch(EMPTY_MODEL, {"conflicts": [{"description": "Rozpočet vs. plocha", "fields": ["budget"]}]})
    model = apply_patch(model, {"conflicts": [{"description": "Bazén vs. svah", "fields": ["site"]}]})
    model = apply_patch(model, {"conflicts": [{"description": "rozpočet vs. plocha", "fields": ["budget"]}]})
    assert [c["description"] for c in model["conflicts"]] == ["Rozpočet vs. plocha", "Bazén vs. svah"]


def test_empty_list_in_patch_does_not_delete():
    model = apply_patch(EMPTY_MODEL, HOUSE_PATCH)
    model = apply_patch(model, {"program": {"spaces": [], "relationships": []}, "conflicts": []})
    assert len(model["program"]["spaces"]) == 3
    assert len(model["program"]["relationships"]) == 1


def test_single_object_instead_of_list_is_tolerated():
    model = apply_patch(EMPTY_MODEL, HOUSE_PATCH)
    model = apply_patch(model, {"program": {"spaces": {"id": "office", "name": "pracovna"}}})
    assert _ids(model)[-1] == "office"


def test_other_fields_still_deep_merge():
    model = apply_patch(EMPTY_MODEL, HOUSE_PATCH)
    model = apply_patch(model, {"style": {"keywords": ["minimalismus", "kámen"]}, "budget": {"target": 40_000_000}})
    assert model["project"]["type"] == "rodinný dům"
    assert model["style"]["keywords"] == ["minimalismus", "kámen"]
    assert model["budget"] == {"target": 40_000_000, "max": None}


def test_input_model_and_patch_are_not_mutated():
    base = apply_patch(EMPTY_MODEL, HOUSE_PATCH)
    base_snapshot = deepcopy(base)
    patch = deepcopy(GUEST_PATCH)
    apply_patch(base, patch)
    assert base == base_snapshot
    assert patch == GUEST_PATCH
    assert EMPTY_MODEL["program"]["spaces"] == []
