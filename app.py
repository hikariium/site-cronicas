import json
import os
import secrets
import string
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

BASE_DIR = Path(__file__).resolve().parent
TOKENS_PATH: Path = BASE_DIR / "tokens.json"
VOTES_PATH: Path = BASE_DIR / "votes.json"

VALID_OFFICES = {
    "presidencia": {"13", "14", "22"},
    "governador": {"1399", "1400", "2222"},
}

DEFAULT_RESULTS = {
    "presidencia": {"13": 0, "14": 0, "22": 0},
    "governador": {"1399": 0, "1400": 0, "2222": 0},
}

DEFAULT_TOKEN_STORAGE = {"registered": [], "used": []}
DEFAULT_VOTE_STORAGE = {"votes": [], "results": deepcopy(DEFAULT_RESULTS)}

storage_lock = Lock()


def _read_json(path: Path, default):
    if not path.exists():
        _write_json(path, default)
        return deepcopy(default)
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        _write_json(path, default)
        return deepcopy(default)


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _normalize_vote_storage():
    vote_data = _read_json(VOTES_PATH, DEFAULT_VOTE_STORAGE)
    vote_data.setdefault("votes", [])
    vote_data.setdefault("results", deepcopy(DEFAULT_RESULTS))

    for office, numbers in DEFAULT_RESULTS.items():
        for number in numbers:
            vote_data["results"].setdefault(office, {})
            vote_data["results"][office].setdefault(str(number), 0)
    _write_json(VOTES_PATH, vote_data)
    return vote_data


def _normalize_token_storage():
    token_data = _read_json(TOKENS_PATH, DEFAULT_TOKEN_STORAGE)
    token_data.setdefault("registered", [])
    token_data.setdefault("used", [])
    _write_json(TOKENS_PATH, token_data)
    return token_data


@app.before_request
def ensure_data_files():
    _normalize_token_storage()
    _normalize_vote_storage()


@app.get("/health")
def health():
    return jsonify({"ok": True, "status": "online"})


@app.post("/api/tokens")
def generate_token():
    payload = request.get_json(silent=True) or {}

    try:
        length = int(payload.get("length", 18))
    except (TypeError, ValueError):
        return jsonify({"error": "Tamanho do token inválido."}), 400

    if length < 8 or length > 32:
        return jsonify({"error": "O token deve ter entre 8 e 32 caracteres."}), 400

    upper = bool(payload.get("upper", True))
    lower = bool(payload.get("lower", True))
    numbers = bool(payload.get("numbers", True))
    symbols = bool(payload.get("symbols", False))

    charset = ""
    if upper:
        charset += string.ascii_uppercase
    if lower:
        charset += string.ascii_lowercase
    if numbers:
        charset += string.digits
    if symbols:
        charset += "!@#$%&*"

    if not charset:
        return jsonify({"error": "Selecione pelo menos um tipo de caractere."}), 400

    with storage_lock:
        token_data = _normalize_token_storage()
        while True:
            token = "".join(secrets.choice(charset) for _ in range(length))
            if (
                token not in token_data["registered"]
                and token not in token_data["used"]
            ):
                token_data["registered"].append(token)
                _write_json(TOKENS_PATH, token_data)
                return jsonify({"token": token})


@app.post("/api/register-token")
def register_token():
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()

    if not token:
        return jsonify({"error": "Token obrigatório."}), 400

    with storage_lock:
        token_data = _normalize_token_storage()
        if token in token_data["used"]:
            return jsonify({"error": "Este token já foi utilizado."}), 409

        if token in token_data["registered"]:
            return jsonify({"ok": True, "message": "Token já registrado."})

        token_data["registered"].append(token)
        _write_json(TOKENS_PATH, token_data)
        return jsonify({"ok": True, "message": "Token registrado."})


@app.post("/api/tokens/validate")
def validate_token():
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()

    if not token:
        return jsonify({"error": "Informe um token."}), 400

    with storage_lock:
        token_data = _normalize_token_storage()
        if token in token_data["used"]:
            return jsonify({"error": "Este token já foi utilizado."}), 409
        if token not in token_data["registered"]:
            return jsonify({"error": "Token inválido."}), 404

    return jsonify({"valid": True, "message": "Token válido."})


@app.post("/api/votes")
def submit_vote():
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()
    presidencia = str(payload.get("presidencia") or "").strip()
    governador = str(payload.get("governador") or "").strip()

    if not token:
        return jsonify({"error": "Token obrigatório."}), 400

    with storage_lock:
        token_data = _normalize_token_storage()
        vote_data = _normalize_vote_storage()

        if token not in token_data["registered"]:
            return jsonify({"error": "Token inválido."}), 403
        if token in token_data["used"]:
            return jsonify({"error": "Este token já foi utilizado."}), 409

        if presidencia not in VALID_OFFICES["presidencia"]:
            return jsonify({"error": "Número de presidência inválido."}), 400
        if governador not in VALID_OFFICES["governador"]:
            return jsonify({"error": "Número de governador inválido."}), 400

        vote_data["results"]["presidencia"][presidencia] = (
            int(vote_data["results"]["presidencia"].get(presidencia, 0)) + 1
        )
        vote_data["results"]["governador"][governador] = (
            int(vote_data["results"]["governador"].get(governador, 0)) + 1
        )

        vote_data["votes"].append(
            {
                "token": token,
                "presidencia": presidencia,
                "governador": governador,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        token_data["used"].append(token)
        _write_json(TOKENS_PATH, token_data)
        _write_json(VOTES_PATH, vote_data)

    return jsonify({"ok": True, "message": "Voto registrado com sucesso."})


@app.get("/api/results")
def get_results():
    with storage_lock:
        vote_data = _normalize_vote_storage()
        results = deepcopy(DEFAULT_RESULTS)
        for office, candidates in vote_data["results"].items():
            for number, count in candidates.items():
                results.setdefault(office, {})
                results[office][str(number)] = int(count)

    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
