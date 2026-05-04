"""
server.py — ArchBrief Flask backend

Endpoints:
    POST /api/session/new        — nová session + první zpráva agenta
    POST /api/chat               — zpracování zprávy uživatele
    GET  /api/session/<id>       — aktuální stav modelu záměru
"""
from __future__ import annotations

from flask import Flask, jsonify, request
from flask_cors import CORS

from agent import create_session, process_message, sessions

app = Flask(__name__)
CORS(app)


@app.route("/api/session/new", methods=["POST"])
def new_session():
    try:
        result = create_session()
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    session_id = (data.get("session_id") or "").strip()
    message = (data.get("message") or "").strip()

    if not session_id or not message:
        return jsonify({"error": "session_id a message jsou povinné"}), 400

    try:
        result = process_message(session_id, message)
        return jsonify(result)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session(session_id: str):
    if session_id not in sessions:
        return jsonify({"error": "Session nenalezena"}), 404
    return jsonify({"intent_model": sessions[session_id]["model"]})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
