from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from backend.chatbot import handle_chat
from backend.recommender import load_schemes, recommend_schemes


BASE_DIR = Path(__file__).resolve().parent


def create_app(data_path: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SCHEME_DATA_PATH"] = Path(data_path) if data_path else BASE_DIR / "data" / "government_schemes.csv"

    def schemes() -> list[dict[str, str]]:
        return load_schemes(app.config["SCHEME_DATA_PATH"])

    def json_body() -> dict[str, Any] | None:
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else None

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/api/schemes")
    def list_schemes():
        items = schemes()
        category = request.args.get("category", "").strip().casefold()
        query = request.args.get("q", "").strip().casefold()
        if category:
            items = [item for item in items if item["category"].casefold() == category]
        if query:
            items = [
                item for item in items
                if query in " ".join((item["scheme_name"], item["category"], item["description"])).casefold()
            ]
        return jsonify({"count": len(items), "schemes": items})

    @app.post("/api/recommend")
    def recommend():
        payload = json_body()
        if payload is None or not isinstance(payload.get("profile"), dict):
            return jsonify({"error": "Send a JSON object with a profile object."}), 400
        try:
            results = recommend_schemes(schemes(), payload["profile"])
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"count": len(results), "recommendations": results})

    @app.post("/api/chat")
    def chat():
        payload = json_body()
        if payload is None:
            return jsonify({"error": "Send a valid JSON object."}), 400
        message = payload.get("message", "")
        profile = payload.get("profile", {})
        stage = payload.get("stage", "interest")
        if not isinstance(message, str) or len(message) > 500:
            return jsonify({"error": "Message must be text with at most 500 characters."}), 400
        if not isinstance(profile, dict) or not isinstance(stage, str):
            return jsonify({"error": "Profile must be an object and stage must be text."}), 400
        try:
            result = handle_chat(message, profile, stage, schemes())
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify(result)

    @app.get("/api/scheme/<scheme_id>")
    def scheme_detail(scheme_id: str):
        item = next((row for row in schemes() if row["scheme_id"] == scheme_id), None)
        if item is None:
            return jsonify({"error": "Scheme not found."}), 404
        return jsonify({"scheme": item})

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"error": "The request could not be completed. Please try again."}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)