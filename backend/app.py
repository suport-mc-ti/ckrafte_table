from flask import Flask, jsonify

from routes import api


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok", "service": "backend"}, 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)