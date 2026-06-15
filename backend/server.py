"""
server.py — ArchBrief Flask backend (Fáze 3 — Supabase)

Endpoints:
    POST /api/session/new        — nový projekt + session, první zpráva agenta
    POST /api/chat               — zpráva uživatele → odpověď agenta + uložení
    GET  /api/projects           — seznam projektů přihlášeného uživatele
    GET  /api/session/<id>       — stav session + čitelná historie konverzace
"""
from __future__ import annotations

from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()  # načíst .env před importem modulů používajících env proměnné

from flask import Flask, jsonify, request
from flask_cors import CORS

from agent import create_session, process_message, get_user_projects, get_session, rename_project, generate_and_save_image
from floorplan import generate_floorplan_svg
from supabase_client import get_supabase

app = Flask(__name__)
CORS(app)


def _require_auth() -> tuple:
    """
    Ověří Bearer token ze záhlaví požadavku.

    Returns:
        (user, None) při úspěchu
        (None, (error_message, status_code)) při chybě
    """
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        return None, ("Chybí Authorization header", 401)
    try:
        result = get_supabase().auth.get_user(token)
        return result.user, None
    except Exception as exc:
        return None, (f"Neplatný token: {exc}", 401)


@app.route("/api/session/new", methods=["POST"])
def new_session():
    user, auth_err = _require_auth()
    if auth_err:
        return jsonify({"error": auth_err[0]}), auth_err[1]
    try:
        data = request.get_json(force=True) or {}
        project_name = data.get("project_name", "Nový projekt")
        result = create_session(str(user.id), project_name)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    user, auth_err = _require_auth()
    if auth_err:
        return jsonify({"error": auth_err[0]}), auth_err[1]
    try:
        data = request.get_json(force=True)
        session_id = (data.get("session_id") or "").strip()
        message = (data.get("message") or "").strip()
        if not session_id or not message:
            return jsonify({"error": "session_id a message jsou povinné"}), 400
        result = process_message(session_id, message)
        return jsonify(result)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/projects", methods=["GET"])
def projects():
    user, auth_err = _require_auth()
    if auth_err:
        return jsonify({"error": auth_err[0]}), auth_err[1]
    try:
        result = get_user_projects(str(user.id))
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session_endpoint(session_id: str):
    _, auth_err = _require_auth()
    if auth_err:
        return jsonify({"error": auth_err[0]}), auth_err[1]
    try:
        data = get_session(session_id)
        return jsonify(data)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/generate-image", methods=["POST"])
def generate_image_endpoint():
    _, auth_err = _require_auth()
    if auth_err:
        return jsonify({"error": auth_err[0]}), auth_err[1]
    try:
        data = request.get_json(force=True) or {}
        session_id = (data.get("session_id") or "").strip()
        reference_url = data.get("reference_image_url") or None
        if not session_id:
            return jsonify({"error": "session_id je povinný"}), 400
        result = generate_and_save_image(session_id, reference_url)
        return jsonify(result)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/floorplan-svg", methods=["POST"])
def floorplan_svg_endpoint():
    _, auth_err = _require_auth()
    if auth_err:
        return jsonify({"error": auth_err[0]}), auth_err[1]
    try:
        data = request.get_json(force=True) or {}
        session_id = (data.get("session_id") or "").strip()
        if not session_id:
            return jsonify({"error": "session_id je povinný"}), 400

        sb = get_supabase()
        result = sb.table("sessions").select("intent_model").eq("id", session_id).execute()
        if not result.data:
            return jsonify({"error": f"Session '{session_id}' nenalezena"}), 404

        floorplan_data = generate_floorplan_svg(result.data[0]["intent_model"])

        try:
            sb.table("sessions").update({
                "floorplan_svg": floorplan_data["svg"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", session_id).execute()
        except Exception:
            pass  # non-fatal — sloupec možná ještě neexistuje v DB

        return jsonify(floorplan_data)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/projects/<project_id>", methods=["PATCH"])
def patch_project(project_id: str):
    _, auth_err = _require_auth()
    if auth_err:
        return jsonify({"error": auth_err[0]}), auth_err[1]
    try:
        data = request.get_json(force=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name je povinný"}), 400
        rename_project(project_id, name)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
