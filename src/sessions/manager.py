"""
Gestion de sesiones: guarda el estado de cada ejecucion para poder reanudarla.

Las sesiones se almacenan como JSON en la carpeta ./sessions/
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _sessions_dir() -> Path:
    base = Path(os.getenv("SESSIONS_DIR", str(_PROJECT_ROOT / "sessions")))
    base.mkdir(parents=True, exist_ok=True)
    return base


def _projects_dir() -> Path:
    base = Path(os.getenv("PROJECTS_DIR", str(_PROJECT_ROOT / "project_runs")))
    base.mkdir(parents=True, exist_ok=True)
    return base


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "proyecto").strip().lower()).strip("-")
    return slug[:60] or "proyecto"


def create_session(requirement: str, language: str) -> dict:
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_slug = _slugify(requirement)
    project_dir = _projects_dir() / project_slug
    run_dir = project_dir / session_id
    output_dir = run_dir / "output"
    session_file = run_dir / "session.json"
    return {
        "id": session_id,
        "project_slug": project_slug,
        "project_dir": str(project_dir),
        "run_dir": str(run_dir),
        "session_file": str(session_file),
        "requirement": requirement,
        "language": language,
        "provider": os.getenv("OPENAI_PROVIDER", "groq"),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
        "openai_base_url": os.getenv("OPENAI_BASE_URL", "") or "",
        "low_cost": os.getenv("LOW_COST_MODE", "0") == "1",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        "steps": {
            "pm":          "pending",
            "backend":     "pending",
            "frontend":    "pending",
            "qa":          "pending",
            "security":    "pending",
            "devops":      "pending",
            "tech_writer": "pending",
        },
        "error": None,
    }


def save_session(session: dict) -> None:
    session["updated_at"] = datetime.now().isoformat()
    session_file = session.get("session_file")
    if session_file:
        path = Path(session_file)
    else:
        path = _sessions_dir() / f"{session['id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8")


def load_session(session_id: str) -> dict:
    legacy = _sessions_dir() / f"{session_id}.json"
    if legacy.exists():
        return json.loads(legacy.read_text(encoding="utf-8"))

    for path in _projects_dir().glob(f"**/{session_id}/session.json"):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

    raise FileNotFoundError(f"No existe la sesion {session_id}")


def list_sessions() -> list:
    sessions = []

    # Sesiones nuevas (una carpeta por proyecto/ejecucion)
    for f in _projects_dir().glob("**/session.json"):
        try:
            sessions.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass

    # Compatibilidad con sesiones antiguas en ./sessions/
    d = _sessions_dir()
    for f in d.glob("*.json"):
        try:
            sessions.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass

    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions


def session_progress(session: dict) -> tuple:
    """Returns (completed_count, total_count)"""
    steps = session["steps"]
    total = len(steps)
    completed = sum(1 for s in steps.values() if s == "completed")
    return completed, total
