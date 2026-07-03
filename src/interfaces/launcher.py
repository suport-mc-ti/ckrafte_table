"""Launcher unico multiplataforma para AGENTE-S."""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_command(no_run: bool, verbose: bool) -> list[str]:
    root = _project_root()
    system = platform.system().lower()

    if "windows" in system:
        script = root / "infra" / "scripts" / "bootstrap-windows.ps1"
        command = [
            "powershell",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ]
        if no_run:
            command.append("-NoRun")
        if verbose:
            command.append("-VerboseOutput")
        return command

    script = root / "infra" / "scripts" / "bootstrap-linux.sh"
    command = ["bash", str(script)]
    if no_run:
        command.append("--no-run")
    return command


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launcher unico de AGENTE-S (deteccion automatica de sistema operativo)"
    )
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="Solo instala/verifica, sin abrir la aplicacion al final",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Muestra salida detallada del bootstrap (en Windows)",
    )
    args = parser.parse_args()

    print("+--------------------------------------------------------------+")
    print("| AGENTE-S / LAUNCHER UNICO                                   |")
    print("| Deteccion automatica de sistema y arranque guiado           |")
    print("+--------------------------------------------------------------+")

    command = _build_command(no_run=args.no_run, verbose=args.verbose)
    print("Ejecutando:", " ".join(command))

    result = subprocess.run(command, cwd=str(_project_root()))
    raise SystemExit(int(result.returncode))
