"""Comandos auxiliares para uso rapido del proyecto."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_main(extra_args: list[str]) -> int:
    """Ejecuta main.py con los argumentos indicados."""
    command = [sys.executable, str(PROJECT_ROOT / "main.py"), *extra_args]
    completed = subprocess.run(command, cwd=str(PROJECT_ROOT))
    return int(completed.returncode)


def usage_cmd() -> None:
    """Muestra la guia de uso y termina."""
    raise SystemExit(_run_main(["--usage"]))


def start_cmd() -> None:
    """Inicia la CLI interactiva."""
    raise SystemExit(_run_main([]))


def demo_cmd() -> None:
    """Ejecuta un ejemplo listo para Ollama."""
    parser = argparse.ArgumentParser(description="Demo rapida del pipeline")
    parser.add_argument(
        "--req",
        default="API local para biblioteca comunitaria con catalogo, prestamos y devoluciones",
        help="Requerimiento de ejemplo",
    )
    parser.add_argument("--lang", default="espanol", help="Idioma de salida")
    parser.add_argument("--provider", default="ollama", help="Proveedor IA")
    args = parser.parse_args()

    if args.provider == "ollama":
        os.environ.setdefault("OPENAI_PROVIDER", "ollama")
        os.environ.setdefault("OPENAI_API_KEY", "ollama")
        os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:11434/v1")

    raise SystemExit(
        _run_main([
            "--req",
            args.req,
            "--provider",
            args.provider,
            "--lang",
            args.lang,
        ])
    )


def doctor_cmd() -> None:
    """Valida prerequisitos minimos y muestra diagnostico rapido."""
    checks: list[tuple[str, bool, str]] = []

    checks.append((
        "Archivo main.py",
        (PROJECT_ROOT / "main.py").exists(),
        str(PROJECT_ROOT / "main.py"),
    ))
    checks.append((
        "Config modelos",
        (PROJECT_ROOT / "shared" / "agent-models.json").exists(),
        str(PROJECT_ROOT / "shared" / "agent-models.json"),
    ))
    checks.append((
        "Tareas VS Code",
        (PROJECT_ROOT / ".vscode" / "tasks.json").exists(),
        str(PROJECT_ROOT / ".vscode" / "tasks.json"),
    ))

    provider = os.getenv("OPENAI_PROVIDER", "")
    base_url = os.getenv("OPENAI_BASE_URL", "")
    api_key = os.getenv("OPENAI_API_KEY", "")

    checks.append(("OPENAI_PROVIDER definido", bool(provider), provider or "no definido"))
    checks.append(("OPENAI_BASE_URL definido", bool(base_url), base_url or "no definido"))
    checks.append(("OPENAI_API_KEY definido", bool(api_key), "definido" if api_key else "no definido"))

    ollama_ok = False
    ollama_note = "no verificado"
    try:
        with urlopen("http://localhost:11434/api/tags", timeout=2) as response:  # nosec B310
            ollama_ok = response.status == 200
            ollama_note = f"HTTP {response.status}"
    except URLError as exc:
        ollama_note = f"sin respuesta ({exc})"

    checks.append(("Ollama activo en localhost:11434", ollama_ok, ollama_note))

    print("Diagnostico ckrafte_table")
    print("Raiz:", PROJECT_ROOT)

    all_ok = True
    for title, ok, note in checks:
        marker = "OK" if ok else "FAIL"
        print(f"- [{marker}] {title}: {note}")
        all_ok = all_ok and ok

    if all_ok:
        print("Estado final: listo para ejecutar")
        raise SystemExit(0)

    print("Estado final: revisar items con FAIL")
    raise SystemExit(1)
