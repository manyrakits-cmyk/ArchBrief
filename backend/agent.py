"""
agent.py — ArchBrief: agentní logika s Supabase persistencí

Každá session je uložena v tabulce `sessions` (Supabase).
Konverzační historie se načítá ze Supabase před každým voláním agenta
a ukládá zpět po každé odpovědi.
"""
from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timezone

import anthropic

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from archbrief_cli import EMPTY_MODEL, apply_patch, call_agent  # noqa: E402
from supabase_client import get_supabase
from image_generator import build_image_prompt, generate_image

_client = anthropic.Anthropic()
_INIT_TRIGGER = "Zahájení rozhovoru. Představ se a polož první otázku."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(user_id: str, project_name: str = "Nový projekt") -> dict:
    """
    Vytvoří nový projekt a session v Supabase, zavolá agenta pro první zprávu.

    Returns:
        dict: session_id, project_id, assistant_message, intent_model
    """
    sb = get_supabase()

    # 1. Vytvořit projekt
    project_res = sb.table("projects").insert({
        "user_id": user_id,
        "name": project_name,
    }).execute()
    project_id = project_res.data[0]["id"]

    # 2. Zavolat agenta pro první zprávu
    conversation = [{"role": "user", "content": _INIT_TRIGGER}]
    model = deepcopy(EMPTY_MODEL)
    response = call_agent(_client, conversation, model)

    patch = response.get("intent_model_update", {})
    if patch:
        model = apply_patch(model, patch)

    conversation.append({
        "role": "assistant",
        "content": json.dumps(response, ensure_ascii=False),
    })

    # 3. Aktualizovat typ projektu pokud agent zjistil
    project_type = model.get("project", {}).get("type", "")
    if project_type:
        sb.table("projects").update({"type": project_type}).eq("id", project_id).execute()

    # 4. Vytvořit session
    session_res = sb.table("sessions").insert({
        "project_id": project_id,
        "intent_model": model,
        "conversation": conversation,
    }).execute()
    session_id = session_res.data[0]["id"]

    return {
        "session_id": session_id,
        "project_id": project_id,
        "assistant_message": response.get("assistant_message", ""),
        "intent_model": model,
    }


def process_message(session_id: str, user_message: str) -> dict:
    """
    Zpracuje zprávu uživatele — načte session ze Supabase, zavolá agenta,
    uloží nový stav zpět.

    Raises:
        KeyError: Pokud session neexistuje.
    """
    sb = get_supabase()

    # 1. Načíst session ze Supabase
    result = sb.table("sessions").select("*").eq("id", session_id).execute()
    if not result.data:
        raise KeyError(f"Session '{session_id}' nenalezena")

    row = result.data[0]
    model: dict = row["intent_model"]
    conversation: list = row["conversation"]

    # 2. Přidat zprávu uživatele a zavolat agenta
    conversation.append({"role": "user", "content": user_message})
    response = call_agent(_client, conversation, model)

    # 3. Aplikovat patch
    patch = response.get("intent_model_update", {})
    if patch:
        model = apply_patch(model, patch)

    conversation.append({
        "role": "assistant",
        "content": json.dumps(response, ensure_ascii=False),
    })

    # 4. Uložit zpět do Supabase
    sb.table("sessions").update({
        "intent_model": model,
        "conversation": conversation,
        "updated_at": _now(),
    }).eq("id", session_id).execute()

    # 5. Aktualizovat typ projektu pokud se změnil
    project_type = model.get("project", {}).get("type", "")
    if project_type:
        sb.table("projects").update({
            "type": project_type,
            "updated_at": _now(),
        }).eq("id", row["project_id"]).execute()

    return {
        "assistant_message": response.get("assistant_message", ""),
        "intent_model": model,
    }


def get_user_projects(user_id: str) -> list:
    """Vrátí seznam projektů uživatele seřazených od nejnovějšího."""
    sb = get_supabase()
    projects = (
        sb.table("projects")
        .select("*")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )

    result = []
    for project in projects.data:
        # Přidáme session_id nejnovější session projektu
        session = (
            sb.table("sessions")
            .select("id")
            .eq("project_id", project["id"])
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        project["session_id"] = session.data[0]["id"] if session.data else None
        result.append(project)

    return result


def rename_project(project_id: str, name: str) -> None:
    """Přejmenuje projekt."""
    get_supabase().table("projects").update({
        "name": name,
        "updated_at": _now(),
    }).eq("id", project_id).execute()


def generate_and_save_image(session_id: str, reference_image_url: str | None = None) -> dict:
    """
    Sestaví prompt z intent_model, vygeneruje obrázek přes fal.ai a uloží do Supabase.

    Returns:
        dict: image_url, prompt_used
    """
    sb = get_supabase()

    # 1. Načíst intent_model ze session
    result = sb.table("sessions").select("intent_model").eq("id", session_id).execute()
    if not result.data:
        raise KeyError(f"Session '{session_id}' nenalezena")

    intent_model = result.data[0]["intent_model"]

    # 2. Sestavit prompt a vygenerovat obrázek
    prompt = build_image_prompt(intent_model)
    image_url = generate_image(prompt, reference_image_url)

    # 3. Uložit výsledek do Supabase
    sb.table("sessions").update({
        "generated_image_url": image_url,
        "image_prompt": prompt,
        "updated_at": _now(),
    }).eq("id", session_id).execute()

    return {"image_url": image_url, "prompt_used": prompt}


def get_session(session_id: str) -> dict:
    """
    Načte session ze Supabase a extrahuje čitelnou historii konverzace.

    Returns:
        dict: intent_model, project_id, messages (čitelné zprávy pro UI)
    """
    sb = get_supabase()
    result = sb.table("sessions").select("*").eq("id", session_id).execute()
    if not result.data:
        raise KeyError(f"Session '{session_id}' nenalezena")

    row = result.data[0]

    # Extrahovat čitelné zprávy z konverzace (přeskočit init trigger)
    messages = []
    for msg in row["conversation"]:
        if msg["role"] == "user" and msg["content"] == _INIT_TRIGGER:
            continue
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            try:
                parsed = json.loads(msg["content"])
                messages.append({
                    "role": "assistant",
                    "content": parsed.get("assistant_message", ""),
                })
            except json.JSONDecodeError:
                messages.append({"role": "assistant", "content": msg["content"]})

    return {
        "intent_model": row["intent_model"],
        "project_id": row["project_id"],
        "messages": messages,
        "generated_image_url": row.get("generated_image_url"),
        "image_prompt": row.get("image_prompt"),
    }
