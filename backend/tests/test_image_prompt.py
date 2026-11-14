"""Testy promptu pro vizualizaci: respektuje styl, materiály, podlažnost a střechu."""
from __future__ import annotations

import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import image_generator  # noqa: E402
from image_generator import build_image_prompt, image_seed  # noqa: E402

GARGANO = {
    "project": {"type": "rodinný dům"},
    "site": {"location": "Gargano, Itálie"},
    "building": {"floors": 1, "roof_type": "flat"},
    "style": {
        "keywords": ["minimalismus", "bílá", "středomořská"],
        "materials": ["kámen", "sklo"],
        "atmosphere": "klidná, světlá",
    },
    "program": {"spaces": [
        {"id": "living", "name": "obývací pokoj"},
        {"id": "terrace", "name": "terasa"},
        {"id": "pool", "name": "bazén"},
    ]},
}


def test_gargano_prompt_respects_model():
    prompt = build_image_prompt(GARGANO)
    assert prompt.startswith("Photorealistic exterior of a single-storey family house, flat roof,")
    for expected in ("natural stone", "large glass windows", "minimalist", "white",
                     "Mediterranean", "bright", "in Gargano, Italy",
                     "with terrace", "with swimming pool"):
        assert expected in prompt
    # materiály před stylem
    assert prompt.index("natural stone") < prompt.index("minimalist")


def test_prompt_contains_no_czech():
    assert build_image_prompt(GARGANO).isascii()


def test_missing_data_is_not_invented():
    prompt = build_image_prompt({"project": {"type": "rodinný dům"}})
    assert "storey" not in prompt
    assert "roof" not in prompt
    assert prompt.startswith("Photorealistic exterior of a family house,")


def test_legacy_model_without_building_field():
    legacy = {k: v for k, v in GARGANO.items() if k != "building"}
    prompt = build_image_prompt(legacy)
    assert "natural stone" in prompt and "storey" not in prompt


def test_roof_and_floors_variants():
    assert "two-storey" in build_image_prompt({"building": {"floors": "2"}})
    assert "gable roof" in build_image_prompt({"building": {"roof_type": "sedlová"}})
    assert "flat green roof" in build_image_prompt({"building": {"roof_type": "green"}})
    # sedlová ve stylu neznamená šedou
    prompt = build_image_prompt({"style": {"keywords": ["sedlová střecha"]}})
    assert "gable roof" in prompt and "grey" not in prompt


def test_location_note_is_skipped():
    prompt = build_image_prompt({"site": {"location": "hledá se — preference jižní svah"}})
    assert " in " not in prompt


def test_seed_is_stable_and_per_session():
    assert image_seed("abc") == image_seed("abc")
    assert image_seed("abc") != image_seed("abd")
    assert 0 <= image_seed("abc") < 2**31


def test_generate_image_passes_seed_and_dev_model():
    fake = {"images": [{"url": "https://example.test/x.png"}]}
    with mock.patch.object(image_generator.fal_client, "run", return_value=fake) as run:
        url = image_generator.generate_image("prompt", seed=42)
    assert url == "https://example.test/x.png"
    model_id, = run.call_args.args
    args = run.call_args.kwargs["arguments"]
    assert model_id == "fal-ai/flux/dev"
    assert args["seed"] == 42 and args["image_size"] == "landscape_16_9"

    with mock.patch.object(image_generator.fal_client, "run", return_value=fake) as run:
        image_generator.generate_image("prompt", "https://example.test/ref.png", seed=7)
    assert run.call_args.args[0] == "fal-ai/flux/dev/image-to-image"
    assert run.call_args.kwargs["arguments"]["seed"] == 7
