from flask import Blueprint, jsonify

from shared_contracts import AGENT_MODELS, API_INFO

api = Blueprint("api", __name__)


@api.get("/agents")
def list_agents() -> tuple[dict[str, object], int]:
    return {"agents": AGENT_MODELS, "api": API_INFO}, 200


@api.get("/lessons")
def list_lessons() -> tuple[dict[str, list[dict[str, str]]], int]:
    lessons = [
        {
            "role": "backend",
            "goal": "Crear endpoints REST y conectar datos.",
        },
        {
            "role": "frontend",
            "goal": "Consumir la API y renderizar una interfaz accesible.",
        },
        {
            "role": "infra",
            "goal": "Orquestar servicios locales con Docker Compose.",
        },
    ]
    return {"lessons": lessons}, 200