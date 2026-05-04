"""
agent.py — ArchBrief: agentní logika pro Flask backend

Importuje sdílenou logiku z archbrief_cli.py a přidává
server-specific funkce pro správu in-memory sessions.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from copy import deepcopy

import anthropic

# Sdílená logika žije v archbrief_cli.py (o úroveň výš)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from archbrief_cli import EMPTY_MODEL, apply_patch, call_agent  # noqa: E402

# In-memory storage: { session_id: { "model": {...}, "conversation": [...] } }
sessions: dict[str, dict] = {}

# Sdílený Anthropic klient pro celý backend proces
_client = anthropic.Anthropic()

_INIT_TRIGGER = "Zahájení rozhovoru. Představ se a polož první otázku."


def create_session() -> dict:
    """
    Vytvoří novou session a získá první zprávu agenta.

    Returns:
        dict: session_id, assistant_message, intent_model
    """
    session_id = str(uuid.uuid4())
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

    sessions[session_id] = {"model": model, "conversation": conversation}

    return {
        "session_id": session_id,
        "assistant_message": response.get("assistant_message", ""),
        "intent_model": model,
    }


def process_message(session_id: str, user_message: str) -> dict:
    """
    Zpracuje zprávu uživatele a vrátí odpověď agenta + aktualizovaný model.

    Args:
        session_id:   ID existující session.
        user_message: Text od uživatele.

    Returns:
        dict: assistant_message, intent_model

    Raises:
        KeyError: Pokud session neexistuje.
    """
    if session_id not in sessions:
        raise KeyError(f"Session '{session_id}' neexistuje")

    session = sessions[session_id]
    session["conversation"].append({"role": "user", "content": user_message})

    response = call_agent(_client, session["conversation"], session["model"])

    patch = response.get("intent_model_update", {})
    if patch:
        session["model"] = apply_patch(session["model"], patch)

    session["conversation"].append({
        "role": "assistant",
        "content": json.dumps(response, ensure_ascii=False),
    })

    return {
        "assistant_message": response.get("assistant_message", ""),
        "intent_model": session["model"],
    }
