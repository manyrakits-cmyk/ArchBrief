#!/usr/bin/env python3
"""
archbrief_cli.py — ArchBrief: Konverzační jádro (Fáze 1)

Vede rozhovor s AI agentem a průběžně plní JSON model záměru.
Na konci uloží model do output_model.json.

Požadavky:
    pip install anthropic

Spuštění:
    python backend/archbrief_cli.py

Ukončení:
    Napište 'quit' nebo 'hotovo'
"""

from __future__ import annotations

import json
import os
import sys
from copy import deepcopy

import anthropic


# ── Konfigurace ───────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"       # Pro silnější reasoning: claude-opus-4-7
OUTPUT_FILE = "output_model.json"


# ── Schéma prázdného modelu záměru ───────────────────────────────────────────

EMPTY_MODEL: dict = {
    "project": {
        "id": "",
        "name": "",
        "type": "",
        "schema_version": "1.0",
    },
    "intent": {
        "primary_goal": "",
        "secondary_goals": [],
        "confidence": 0.0,
        "source": "user",
    },
    "goals": [],
    "users": [],
    "site": {
        "location": "",
        "plot": {"width": None, "depth": None},
        "orientation": {"north": None, "access_side": None},
    },
    "program": {
        "spaces": [],
        "relationships": [],
    },
    "constraints": {
        "max_area": None,
    },
    "style": {
        "keywords": [],
        "atmosphere": "",
    },
    "budget": {
        "target": None,
        "max": None,
    },
    "conflicts": [],
}


# ── Systémový prompt agenta ───────────────────────────────────────────────────

_SYSTEM_BASE = """\
Jsi ArchBrief — AI asistent, který nahrazuje první schůzku s architektem.
Vedeš přirozený rozhovor v češtině a postupně zjišťuješ záměr uživatele.

PRAVIDLA ROZHOVORU:
- Kladeš vždy 1–2 otázky najednou, přirozeně a lidsky
- Postupně pokrýváš tyto oblasti (v libovolném pořadí dle přirozeného plynutí):
    typ projektu (dům / byt / rekonstrukce / malá stavba)
    uživatelé (počet lidí, děti, generace, způsob života)
    lokalita a parcela (pokud relevantní)
    velikost a počet místností
    prostorové vztahy a preference
    orientace, zahrada, terasa
    styl a atmosféra
    rozpočet (orientačně)
    omezení a specifické požadavky
- NESMÍŠ navrhovat konkrétní architektonická řešení
- NESMÍŠ rozhodovat za uživatele
- Upozorníš na konflikt v požadavcích a zapíšeš ho do conflicts[]
- Smíš shrnout co víš a zeptat se, zda je to správně

ZJIŠŤOVÁNÍ VELIKOSTÍ MÍSTNOSTÍ:
Nikdy se neptej přímo na m². Místo toho používej přirovnání a kontext:

Příklady otázek:
- "Obývák — představujete si intimní prostor pro rodinu, nebo velký sál kde hostíte 20 lidí?"
- "Kuchyň — vaříte spolu, nebo spíš jeden člověk? Chcete velký ostrov uprostřed?"
- "Ložnice rodičů — chcete ji podobnou jako máte teď, výrazně větší, nebo opravdu prostornou s šatnou?"
- "Pracovna — sdílíte ji, nebo každý potřebuje svůj kout?"

Z odpovědi odvoď orientační plochu a zapiš do modelu:
- "malý / intimní / útulný" → area_target: výchozí × 0.8
- "střední / normální / jako teď" → area_target: výchozí
- "velký / prostorný" → area_target: výchozí × 1.5
- "obrovský / luxusní" → area_target: výchozí × 2

Výchozí hodnoty (m²): living: 30, kitchen: 15, bedroom: 16, bedroom_master: 20,
bathroom: 8, office: 14, dining: 18, terrace: 20

Pro každou místnost zapiš do patche:
- id: stabilní identifikátor ve snake_case anglicky (např. "living", "kitchen",
  "bedroom_master", "guest_bathroom"); jednou přidělené id NIKDY neměň
- name: český název
- area_target: odvozené číslo (vždy, i když jen orientační odhad)
- note: původní popis uživatele

FORMÁT KAŽDÉ ODPOVĚDI — vždy POUZE platný JSON objekt, bez markdown, bez komentářů:
{
  "assistant_message": "<přirozená zpráva pro uživatele v češtině>",
  "intent_model_update": { <patch — pouze změněné části modelu, nebo {} pokud nic nového> }
}

PRAVIDLA PRO PATCH (intent_model_update):
- Zapiš POUZE data z poslední zprávy uživatele
- Nikdy neposílej celý model — jen změny
- program.spaces a program.relationships se slučují podle id: posílej jen NOVÉ
  nebo ZMĚNĚNÉ prostory/vztahy. Prostory, které neuvedeš, v modelu zůstanou.
  Změna existujícího prostoru = stejné id + jen měněná pole.
- Prostory ani vztahy nelze přes patch smazat. Pokud uživatel něco ruší,
  zapiš to do note daného prostoru nebo do conflicts[].
- Vztahy: {"from": "<id prostoru>", "to": "<id prostoru>", "type": "direct|buffered|visual", "note": "..."}
- Ostatní listy (users, keywords, goals…) zasílej celé, pokud je aktualizuješ
- Konflikty přidávej do conflicts[] jako: {"description": "...", "fields": [...]}
  (posílej jen nové konflikty, existující zůstávají)
- Prázdný patch = {}
"""


# ── ANSI barvy ────────────────────────────────────────────────────────────────

if sys.platform == "win32":
    os.system("")  # aktivuje ANSI v starém Windows terminálu

CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"


# ── Patch / deep merge ────────────────────────────────────────────────────────

def deep_merge(base: object, patch: object) -> object:
    """
    Rekurzivní deep merge pro aplikaci JSON patche na model záměru.

    Pravidla:
      dict + dict  → rekurzivní sloučení klíčů
      list/skalár  → patch nahradí celou hodnotu
      None v patch → původní hodnota zůstane (data se nesmažou)

    Pozor: pole program.spaces, program.relationships a conflicts se tudy
    nemergují — řeší je apply_patch podle id (viz _merge_list).
    """
    if patch is None:
        return base
    if not isinstance(patch, dict) or not isinstance(base, dict):
        return deepcopy(patch)

    result = deepcopy(base)
    for key, value in patch.items():
        if value is None:
            continue  # nezamazáváme existující data
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _norm(value: object) -> str:
    """Normalizace klíče pro porovnání: malá písmena, bez okrajových a zdvojených mezer."""
    return " ".join(str(value).strip().lower().split())


def _as_list(value: object) -> list:
    """Patch může omylem poslat jeden objekt místo pole — sjednotíme na list."""
    if isinstance(value, list):
        return value
    if isinstance(value, (dict, str)):
        return [value]
    return []


def _same_space(a: object, b: object) -> bool:
    """Dva prostory jsou totožné, pokud mají stejné id, nebo (fallback pro starší data bez id) stejný název."""
    if isinstance(a, str) or isinstance(b, str):
        name_a = a if isinstance(a, str) else (a or {}).get("name") or (a or {}).get("id")
        name_b = b if isinstance(b, str) else (b or {}).get("name") or (b or {}).get("id")
        return bool(name_a) and bool(name_b) and _norm(name_a) == _norm(name_b)
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    if a.get("id") and b.get("id"):
        return _norm(a["id"]) == _norm(b["id"])
    return bool(a.get("name")) and bool(b.get("name")) and _norm(a["name"]) == _norm(b["name"])


def _same_relationship(a: object, b: object) -> bool:
    """Vztah je totožný podle id, jinak podle dvojice prostorů (bez ohledu na směr)."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    if a.get("id") and b.get("id"):
        return _norm(a["id"]) == _norm(b["id"])
    pair_a = {_norm(a.get("from") or ""), _norm(a.get("to") or "")}
    pair_b = {_norm(b.get("from") or ""), _norm(b.get("to") or "")}
    return "" not in pair_a and pair_a == pair_b


def _same_conflict(a: object, b: object) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        if a.get("id") and b.get("id"):
            return _norm(a["id"]) == _norm(b["id"])
        return bool(a.get("description")) and _norm(a.get("description")) == _norm(b.get("description") or "")
    return _norm(a) == _norm(b)


def _merge_list(existing: object, incoming: object, same, keep: tuple[str, ...] = ("id",)) -> list:
    """
    Merge pole podle identity prvku (funkce `same`).

    - shodný prvek → deep_merge (nové hodnoty se zapíšou, None nic nesmaže),
      identifikační pole z `keep` zůstanou původní (ID se nepřejmenovávají)
    - nový prvek → přidá se na konec
    - prvky, které v patchi nejsou, zůstávají — přes patch nelze mazat
    """
    result = deepcopy(existing) if isinstance(existing, list) else []
    for item in _as_list(incoming):
        if item is None:
            continue
        idx = next((i for i, cur in enumerate(result) if same(cur, item)), None)
        if idx is None:
            result.append(deepcopy(item))
            continue
        current = result[idx]
        if isinstance(current, dict) and isinstance(item, dict):
            merged = deep_merge(current, item)
            for field in keep:
                if current.get(field):
                    merged[field] = current[field]
            result[idx] = merged
        elif isinstance(item, dict):
            result[idx] = deepcopy(item)  # legacy string → plnohodnotný objekt
    return result


def apply_patch(model: dict, patch: dict) -> dict:
    """
    Aplikuje patch na model záměru. Vrací nový model — původní není modifikován.

    Model Update Rule: program.spaces, program.relationships a conflicts se
    mergují podle id (fallback název / dvojice prostorů / popis), nikdy se
    nepřepisují ani nemažou. Ostatní části modelu řeší deep_merge.

    Připraveno pro import do server.py.
    """
    if not isinstance(patch, dict):
        return deepcopy(model)

    patch = deepcopy(patch)
    program_patch = patch.get("program") if isinstance(patch.get("program"), dict) else None
    spaces_patch = program_patch.pop("spaces", None) if program_patch is not None else None
    rels_patch = program_patch.pop("relationships", None) if program_patch is not None else None
    conflicts_patch = patch.pop("conflicts", None)

    result: dict = deep_merge(model, patch)  # type: ignore[assignment]

    if spaces_patch is not None or rels_patch is not None:
        program = result.get("program")
        if not isinstance(program, dict):
            program = result["program"] = {}
        if spaces_patch is not None:
            program["spaces"] = _merge_list(program.get("spaces"), spaces_patch, _same_space)
        if rels_patch is not None:
            program["relationships"] = _merge_list(
                program.get("relationships"), rels_patch, _same_relationship,
                keep=("id", "from", "to"),
            )

    if conflicts_patch is not None:
        result["conflicts"] = _merge_list(
            result.get("conflicts"), conflicts_patch, _same_conflict, keep=("id", "description")
        )

    return result


# ── Volání LLM ────────────────────────────────────────────────────────────────

def call_agent(
    client: anthropic.Anthropic,
    conversation: list[dict],
    current_model: dict,
) -> dict:
    """
    Zavolá LLM agenta s historií konverzace a aktuálním modelem záměru.

    Agent vždy obdrží:
      - systémový prompt s pravidly a aktuálním stavem modelu
      - celou historii konverzace (user / assistant střídání)

    Args:
        client:        Inicializovaný Anthropic klient.
        conversation:  Liste dict [{"role": "user"|"assistant", "content": str}].
        current_model: Aktuální stav JSON modelu záměru.

    Returns:
        Parsed odpověď: {"assistant_message": str, "intent_model_update": dict}

    Raises:
        json.JSONDecodeError: Pokud agent nevrátí validní JSON.
        anthropic.APIError:   Při chybě komunikace s API.

    Připraveno pro import do server.py.
    """
    system_prompt = (
        _SYSTEM_BASE
        + "\nAKTUÁLNÍ MODEL ZÁMĚRU (pouze pro orientaci — neposílej ho celý zpět):\n"
        + f"```json\n{json.dumps(current_model, ensure_ascii=False, indent=2)}\n```\n"
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=conversation,
    )

    raw = response.content[0].text.strip()

    # Odstraníme případný markdown obal ```json ... ```
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]).strip()

    # raw_decode přečte první platný JSON a ignoruje případný trailing text
    parsed, _ = json.JSONDecoder().raw_decode(raw)
    return parsed


# ── Zobrazení modelu v terminálu ──────────────────────────────────────────────

def _colorize_json(json_str: str) -> str:
    """Přidá ANSI barvy do JSON stringu pro lepší čitelnost v terminálu."""
    result = []
    for line in json_str.splitlines():
        stripped = line.lstrip()
        if ":" in stripped and stripped.startswith('"'):
            # řádek s klíčem a hodnotou
            idx = line.index(":")
            result.append(f"{CYAN}{line[:idx]}{RESET}:{GREEN}{line[idx + 1:]}{RESET}")
        elif stripped.startswith('"'):
            # řetězcová hodnota v listu
            result.append(f"{GREEN}{line}{RESET}")
        elif stripped in ("{", "}", "[", "]", "{,", "},", "],"):
            result.append(f"{DIM}{line}{RESET}")
        else:
            result.append(line)
    return "\n".join(result)


def display_model(model: dict) -> None:
    """Vypíše aktuální stav modelu záměru barevně do terminálu."""
    bar = f"{BOLD}{BLUE}{'─' * 62}{RESET}"
    print(f"\n{bar}")
    print(f"{BOLD}{BLUE}  MODEL ZÁMĚRU  (aktuální stav){RESET}")
    print(bar)
    print(_colorize_json(json.dumps(model, ensure_ascii=False, indent=2)))
    print(f"{bar}\n")


# ── Hlavní CLI smyčka ─────────────────────────────────────────────────────────

def run_cli() -> None:
    """Hlavní smyčka ArchBrief CLI."""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"{YELLOW}Chyba: Proměnná prostředí ANTHROPIC_API_KEY není nastavena.{RESET}")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    model_state = deepcopy(EMPTY_MODEL)

    # Celá JSON odpověď agenta se ukládá do konverzace —
    # model tak vždy vidí svůj vlastní výstupní formát a zůstane konzistentní.
    conversation: list[dict] = []

    # ── Banner ────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{MAGENTA}{'═' * 62}{RESET}")
    print(f"{BOLD}{MAGENTA}  ARCHBRIEF — Konverzační jádro  (Fáze 1){RESET}")
    print(f"{BOLD}{MAGENTA}{'═' * 62}{RESET}")
    print(f"{DIM}  Model: {MODEL}  |  Ukončení: 'quit' nebo 'hotovo'{RESET}\n")

    # ── Inicializace: agent zahajuje rozhovor ─────────────────────────────────
    INIT_TRIGGER = "Zahájení rozhovoru. Představ se a polož první otázku."
    conversation.append({"role": "user", "content": INIT_TRIGGER})

    try:
        first_resp = call_agent(client, conversation, model_state)
    except Exception as exc:
        print(f"{YELLOW}Chyba při startu: {exc}{RESET}")
        sys.exit(1)

    first_msg = first_resp.get("assistant_message", "")
    first_patch = first_resp.get("intent_model_update", {})

    if first_patch:
        model_state = apply_patch(model_state, first_patch)

    conversation.append({
        "role": "assistant",
        "content": json.dumps(first_resp, ensure_ascii=False),
    })

    print(f"{BOLD}{GREEN}ArchBrief:{RESET} {first_msg}")
    display_model(model_state)

    # ── Hlavní smyčka ─────────────────────────────────────────────────────────
    while True:
        try:
            user_input = input(f"{BOLD}{YELLOW}Vy: {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{CYAN}Přerušeno.{RESET}")
            break

        if not user_input:
            continue

        if user_input.lower() in {"quit", "hotovo", "exit", "konec"}:
            print(f"\n{CYAN}Rozhovor ukončen.{RESET}")
            break

        conversation.append({"role": "user", "content": user_input})

        # Max 2 pokusy — při JSONDecodeError zkusíme znovu (beze změny konverzace)
        agent_resp = None
        for attempt in range(2):
            try:
                agent_resp = call_agent(client, conversation, model_state)
                break
            except json.JSONDecodeError:
                if attempt == 0:
                    print(f"{DIM}(nevalidní JSON, opakuji...){RESET}")
                else:
                    print(f"{YELLOW}Agent vrátil nevalidní odpověď. Zkuste přeformulovat.{RESET}")
                    conversation.pop()
            except anthropic.APIError as exc:
                print(f"{YELLOW}Chyba API: {exc}{RESET}")
                conversation.pop()
                break

        if agent_resp is None:
            continue

        msg = agent_resp.get("assistant_message", "")
        patch = agent_resp.get("intent_model_update", {})

        if patch:
            model_state = apply_patch(model_state, patch)

        conversation.append({
            "role": "assistant",
            "content": json.dumps(agent_resp, ensure_ascii=False),
        })

        print(f"\n{BOLD}{GREEN}ArchBrief:{RESET} {msg}")
        display_model(model_state)

    # ── Uložení výsledku ──────────────────────────────────────────────────────
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(model_state, f, ensure_ascii=False, indent=2)

    print(f"{BOLD}{GREEN}✓ Model záměru uložen: {OUTPUT_FILE}{RESET}\n")


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
