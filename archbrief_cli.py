#!/usr/bin/env python3
"""
archbrief_cli.py — ArchBrief: Konverzační jádro (Fáze 1)

Vede rozhovor s AI agentem a průběžně plní JSON model záměru.
Na konci uloží model do output_model.json.

Požadavky:
    pip install anthropic

Spuštění:
    python archbrief_cli.py

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

FORMÁT KAŽDÉ ODPOVĚDI — vždy POUZE platný JSON objekt, bez markdown, bez komentářů:
{
  "assistant_message": "<přirozená zpráva pro uživatele v češtině>",
  "intent_model_update": { <patch — pouze změněné části modelu, nebo {} pokud nic nového> }
}

PRAVIDLA PRO PATCH (intent_model_update):
- Zapiš POUZE data z poslední zprávy uživatele
- Nikdy neposílej celý model — jen změny
- Listy (spaces, users, keywords, goals…) zasílej celé, pokud je aktualizuješ
- Konflikty přidávej do conflicts[] jako: {"description": "...", "fields": [...]}
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


def apply_patch(model: dict, patch: dict) -> dict:
    """
    Aplikuje patch na model záměru. Vrací nový model — původní není modifikován.

    Připraveno pro import do server.py.
    """
    return deep_merge(model, patch)  # type: ignore[return-value]


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

    return json.loads(raw)


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
