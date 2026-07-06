from pathlib import Path
import json


_ROOT = Path(__file__).resolve().parents[1]
_MODELS_FILE = _ROOT / "shared" / "agent-models.json"

with _MODELS_FILE.open("r", encoding="utf-8") as handler:
    AGENT_MODELS = json.load(handler)

API_INFO = {
    "name": "ckrafte_table API",
    "version": "0.1.0",
    "docs": "/api/agents",
}