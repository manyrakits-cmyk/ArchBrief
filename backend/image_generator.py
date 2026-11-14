"""
image_generator.py — ArchBrief: generování AI obrázku přes fal.ai

Funkce:
  build_image_prompt(intent_model)        — sestaví anglický prompt z JSON modelu záměru
  image_seed(session_id)                  — stabilní seed pro konzistentní výsledek
  generate_image(prompt, reference, seed) — zavolá fal.ai a vrátí URL obrázku

Prompt obsahuje jen to, co je v modelu (nic nedomýšlí). Nejdůležitější omezení
(podlažnost, střecha, materiály) jsou na začátku — Flux váží přední tokeny víc.
Formulace jsou jen kladné; Flux nepodporuje negativní prompt a zápor špatně chápe.
"""
from __future__ import annotations

import unicodedata
import zlib

import fal_client


TEXT_TO_IMAGE_MODEL = "fal-ai/flux/dev"
IMAGE_TO_IMAGE_MODEL = "fal-ai/flux/dev/image-to-image"
GUIDANCE_SCALE = 3.5
INFERENCE_STEPS = 28


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

# Kmeny českých slov (bez diakritiky) → anglický výraz. Pořadí rozhoduje (první shoda).
_TERM_STEMS: list[tuple[str, str]] = [
    # styl
    ("minimalis", "minimalist"),
    ("stredomor", "Mediterranean"),
    ("moderni", "modern"),
    ("soucasn", "contemporary"),
    ("soudob", "contemporary"),
    ("funkcional", "functionalist"),
    ("tradicni", "traditional"),
    ("venkovsk", "rustic"),
    ("rustikal", "rustic"),
    ("skandinav", "Scandinavian"),
    ("industrial", "industrial"),
    ("japonsk", "Japanese-inspired"),
    ("brutalis", "brutalist"),
    ("organick", "organic"),
    ("luxusni", "luxury"),
    ("vzdusn", "airy"),
    ("svetl", "bright"),
    # barvy
    ("bil", "white"),
    ("cern", "black"),
    ("sedlov", "gable roof"),   # dřív než "sed…" (šedá)
    ("seda", "grey"), ("sedy", "grey"), ("sede", "grey"), ("sedou", "grey"),
    ("ploch", "flat roof"),
    ("pultov", "single-pitch shed roof"),
    ("bezov", "beige"),
    ("piskov", "sand-coloured"),
    ("zemit", "earthy tones"),
    # materiály
    ("pohledov", "exposed concrete"),
    ("beton", "exposed concrete"),
    ("kamen", "natural stone"),
    ("drev", "wood"),
    ("modrin", "larch wood"),
    ("sklo", "large glass windows"),
    ("sklen", "large glass windows"),
    ("prosklen", "large glass windows"),
    ("cihl", "brick"),
    ("omitk", "rendered facade"),
    ("vapen", "lime plaster"),
    ("terakot", "terracotta"),
    ("ocel", "steel"),
    ("kov", "metal"),
    ("corten", "corten steel"),
]

_ROOF_STEMS: list[tuple[str, str]] = [
    ("flat", "flat roof"),
    ("ploch", "flat roof"),
    ("green", "flat green roof"),
    ("zelen", "flat green roof"),
    ("vegetac", "flat green roof"),
    ("gable", "gable roof"),
    ("sedlov", "gable roof"),
    ("hip", "hip roof"),
    ("valbov", "hip roof"),
    ("shed", "single-pitch shed roof"),
    ("pultov", "single-pitch shed roof"),
    ("butterfly", "butterfly roof"),
    ("motyl", "butterfly roof"),
]

_FLOORS = {1: "single-storey", 2: "two-storey", 3: "three-storey"}

_COUNTRIES = {
    "italie": "Italy", "cesko": "Czech Republic", "ceska republika": "Czech Republic",
    "slovensko": "Slovakia", "rakousko": "Austria", "nemecko": "Germany",
    "chorvatsko": "Croatia", "spanelsko": "Spain", "portugalsko": "Portugal",
    "recko": "Greece", "francie": "France", "slovinsko": "Slovenia",
}

# Lokalita, která není místem, ale poznámkou ("hledá se — preference jižní svah")
_LOCATION_NOISE = ("hled", "prefer", "zatim", "nevim", "nejasn", "?")

_SUFFIX = (
    "architectural photography, eye-level view, natural daylight, "
    "photorealistic, 8k, high quality"
)


def _strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def _match_stems(text: str, stems: list[tuple[str, str]]) -> list[str]:
    """Najde anglické výrazy pro všechna slova textu podle kmenů."""
    plain = _strip_diacritics(text.lower())
    found: list[str] = []
    for word in plain.replace(",", " ").replace("/", " ").replace("-", " ").split():
        for stem, en in stems:
            if word.startswith(stem):
                if en not in found:
                    found.append(en)
                break
    return found


def _translate_term(term: str) -> list[str]:
    """
    Český výraz → anglické výrazy. Neznámý výraz bez diakritiky projde
    (pravděpodobně už je anglicky), neznámý český výraz se vynechá.
    """
    term = term.strip()
    if not term:
        return []
    found = _match_stems(term, _TERM_STEMS)
    if found:
        return found
    return [term] if term.isascii() else []


def _floors_phrase(floors: object) -> str:
    try:
        value = float(floors)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return ""
    if value == 1.5:
        return "one-and-a-half-storey"
    n = int(round(value))
    return _FLOORS.get(n, f"{n}-storey")


def _location_phrase(location: str) -> str:
    location = (location or "").strip()
    if not location or len(location) >= 80:
        return ""
    plain = _strip_diacritics(location)
    if any(noise in plain.lower() for noise in _LOCATION_NOISE):
        return ""
    parts = []
    for part in plain.split(","):
        part = part.strip()
        parts.append(_COUNTRIES.get(part.lower(), part))
    return ", ".join(p for p in parts if p)


def build_image_prompt(intent_model: dict) -> str:
    """
    Sestaví anglický prompt pro image generation z intent_model.

    Pořadí: typ + podlažnost → střecha → materiály → styl → lokalita → prostory → suffix.
    Chybějící údaje se vynechají, nic se nedomýšlí.
    """
    building = intent_model.get("building") or {}
    style = intent_model.get("style") or {}

    # Typ projektu + podlažnost
    project_type = ((intent_model.get("project") or {}).get("type") or "").strip().lower()
    en_type = _TYPE_MAP.get(project_type) or _strip_diacritics(project_type) or "family house"
    floors = _floors_phrase(building.get("floors"))
    head = f"{floors} {en_type}" if floors else en_type

    parts: list[str] = [head]

    # Střecha
    roof = _match_stems(str(building.get("roof_type") or ""), _ROOF_STEMS)
    if roof:
        parts.append(roof[0])

    # Materiály a styl (materiály napřed), bez duplicit
    terms: list[str] = []
    for raw in list(style.get("materials") or []) + list(style.get("keywords") or []):
        if isinstance(raw, str):
            for en in _translate_term(raw):
                if en not in terms:
                    terms.append(en)
    for en in _match_stems(str(style.get("atmosphere") or ""), _TERM_STEMS):
        if en not in terms:
            terms.append(en)
    if terms:
        parts.append(", ".join(terms[:8]))

    # Lokalita
    location = _location_phrase((intent_model.get("site") or {}).get("location") or "")
    if location:
        parts.append(f"in {location}")

    # Pozoruhodné prostory (max 2)
    spaces = (intent_model.get("program") or {}).get("spaces") or []
    features: list[str] = []
    for space in spaces:
        if len(features) >= 2:
            break
        if isinstance(space, dict):
            name = f"{space.get('name') or ''} {space.get('id') or ''}".lower()
        elif isinstance(space, str):
            name = space.lower()
        else:
            continue
        for keyword, feature in _SPACE_FEATURES.items():
            if keyword in name and feature not in features:
                features.append(feature)
                break
    parts.extend(features)

    return f"Photorealistic exterior of a {', '.join(parts)}, {_SUFFIX}"


def image_seed(session_id: str) -> int:
    """
    Stabilní seed odvozený ze session_id. Stejný projekt + stejný prompt
    → stejný záběr; po změně modelu se obrázek mění jen kvůli promptu.
    """
    return zlib.crc32(str(session_id).encode("utf-8")) & 0x7FFFFFFF


def generate_image(
    prompt: str,
    reference_image_url: str | None = None,
    seed: int | None = None,
) -> str:
    """
    Zavolá fal.ai API a vrátí URL vygenerovaného obrázku.

    Args:
        prompt:               Textový prompt sestavený z intent_model.
        reference_image_url:  URL referenčního obrázku pro image-to-image (volitelné).
        seed:                 Seed pro reprodukovatelný výsledek (volitelné).

    Returns:
        URL vygenerovaného obrázku (dočasné, platí několik hodin).
    """
    arguments: dict = {
        "prompt": prompt,
        "num_images": 1,
        "guidance_scale": GUIDANCE_SCALE,
        "num_inference_steps": INFERENCE_STEPS,
    }
    if seed is not None:
        arguments["seed"] = seed

    if reference_image_url:
        arguments.update({"image_url": reference_image_url, "strength": 0.80})
        result = fal_client.run(IMAGE_TO_IMAGE_MODEL, arguments=arguments)
    else:
        arguments["image_size"] = "landscape_16_9"
        result = fal_client.run(TEXT_TO_IMAGE_MODEL, arguments=arguments)

    return result["images"][0]["url"]
