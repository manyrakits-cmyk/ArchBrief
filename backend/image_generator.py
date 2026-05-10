"""
image_generator.py — ArchBrief: generování AI obrázku přes fal.ai

Funkce:
  build_image_prompt(intent_model)  — sestaví anglický prompt z JSON modelu záměru
  generate_image(prompt, reference) — zavolá fal.ai a vrátí URL obrázku
"""
from __future__ import annotations

import fal_client


# Překlady českých typů projektu do angličtiny pro prompt
_TYPE_MAP = {
    "rodinný dům": "family house",
    "novostavba rodinného domu": "new family house",
    "rodinný dům novostavba": "new family house",
    "byt": "apartment",
    "rekonstrukce": "renovated house",
    "rekonstrukce bytu": "renovated apartment",
    "malá stavba": "small building",
    "chalupa": "cottage",
    "vila": "villa",
    "dvojdům": "semi-detached house",
}

_SPACE_FEATURES = {
    "terasa": "with terrace",
    "terrace": "with terrace",
    "zahrada": "with garden",
    "garden": "with garden",
    "bazén": "with swimming pool",
    "pool": "with swimming pool",
    "garáž": "with garage",
    "garage": "with garage",
    "balkon": "with balcony",
    "balcony": "with balcony",
}

_SUFFIX = "photorealistic exterior, architectural photography, 8k, natural lighting, high quality"


def build_image_prompt(intent_model: dict) -> str:
    """
    Sestaví anglický prompt pro image generation z intent_model.

    Zahrne: typ projektu, lokalitu, styl, klíčové prostory.
    Přidá fotografický suffix pro kvalitní výsledek.
    """
    parts: list[str] = []

    # Typ projektu
    project_type = (intent_model.get("project") or {}).get("type", "").strip().lower()
    en_type = _TYPE_MAP.get(project_type) or project_type or "family house"
    parts.append(en_type)

    # Lokalita
    location = (intent_model.get("site") or {}).get("location", "").strip()
    if location and len(location) < 80:
        parts.append(f"in {location}")

    # Styl
    style = intent_model.get("style") or {}
    keywords = [k for k in (style.get("keywords") or []) if isinstance(k, str)]
    atmosphere = (style.get("atmosphere") or "").strip()
    if keywords:
        parts.append(", ".join(keywords[:4]))
    if atmosphere:
        parts.append(atmosphere)

    # Pozoruhodné prostory (max 2)
    spaces = (intent_model.get("program") or {}).get("spaces") or []
    features_added = 0
    for space in spaces:
        if features_added >= 2:
            break
        name = ""
        if isinstance(space, dict):
            name = (space.get("name") or "").lower()
        elif isinstance(space, str):
            name = space.lower()
        for keyword, feature in _SPACE_FEATURES.items():
            if keyword in name:
                parts.append(feature)
                features_added += 1
                break

    description = ", ".join(parts)
    return f"Photorealistic exterior of a {description}, {_SUFFIX}"


def generate_image(prompt: str, reference_image_url: str | None = None) -> str:
    """
    Zavolá fal.ai API a vrátí URL vygenerovaného obrázku.

    Args:
        prompt:               Textový prompt sestavený z intent_model.
        reference_image_url:  URL referenčního obrázku pro image-to-image (volitelné).

    Returns:
        URL vygenerovaného obrázku (dočasné, platí několik hodin).
    """
    if reference_image_url:
        result = fal_client.run(
            "fal-ai/flux/dev/image-to-image",
            arguments={
                "prompt": prompt,
                "image_url": reference_image_url,
                "strength": 0.80,
                "num_images": 1,
            },
        )
    else:
        result = fal_client.run(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": "landscape_16_9",
                "num_images": 1,
            },
        )

    return result["images"][0]["url"]
