"""
Interfaz de linea de comandos (CLI) para el equipo multi-agente.

Para agregar otra interfaz (web, API, etc.) crea un nuevo archivo en este
mismo directorio, por ejemplo:
  - src/interfaces/web.py   -> Streamlit / Gradio
  - src/interfaces/api.py   -> FastAPI con endpoints REST
  - src/interfaces/tui.py   -> Textual (terminal UI interactiva)

Cada interfaz solo necesita llamar a:
    from src.crews.dev_crew import run as run_pipeline
    run_pipeline(requirement, output_language, session)
"""

import argparse
import json
import os
import re
import sys
import webbrowser
from html import escape
from pathlib import Path

from dotenv import load_dotenv
from openai import RateLimitError
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

load_dotenv()

console = Console()

BANNER = """
AGENTE-S  |  terminal mode
multi-agent software builder
"""

STEP_NAMES = {
    "pm":          "Fullstack Lead",
    "backend":     "Backend Developer",
    "frontend":    "Frontend Developer",
    "qa":          "QA Engineer",
    "security":    "Security Auditor",
    "devops":      "DevOps Engineer",
    "tech_writer": "Tech Writer",
}

OUTPUT_FILES = [
    ("01_plan_tecnico.md",    "Arquitectura y plan tecnico"),
    ("02_backend_code.md",    "API y base de datos"),
    ("03_frontend_code.md",   "Interfaz de usuario"),
    ("04_qa_report.md",       "Revision y tests"),
    ("05_security_report.md", "Auditoria de seguridad"),
    ("06_devops_config.md",   "Docker y CI/CD"),
    ("07_documentation.md",   "README y documentacion API"),
]

DEFAULT_LIBRARY_REQUIREMENT = (
    "API local para biblioteca comunitaria con catalogo, prestamos y devoluciones"
)

ROLE_BLUEPRINT = [
    ("planner", "Fullstack Lead", "Divide la solicitud en partes y coordina la arquitectura"),
    ("backend", "Backend Developer", "API, reglas de negocio y persistencia"),
    ("frontend", "Frontend Developer", "UI, vistas e integracion"),
    ("qa", "QA Engineer", "Revision, pruebas y calidad"),
    ("security", "Security Auditor", "Riesgos y mitigaciones"),
    ("infra", "DevOps Engineer", "Infraestructura y automatizacion"),
    ("docs", "Tech Writer", "Documentacion tecnica"),
    ("planner", "Technical Lead", "Revision final y criterio de calidad"),
]

PROVIDER_CONFIGS = {
    "groq": {
        "OPENAI_BASE_URL": "https://api.groq.com/openai/v1",
        "OPENAI_MODEL": "llama-3.3-70b-versatile",
        "LOW_COST_MODEL": "llama-3.3-70b-versatile",
    },
    "openai": {
        "OPENAI_BASE_URL": "",
        "OPENAI_MODEL": "gpt-4o-mini",
        "LOW_COST_MODEL": "gpt-4o-mini",
    },
    "ollama": {
        "OPENAI_BASE_URL": "http://localhost:11434/v1",
        "OPENAI_MODEL": "llama3.2",
        "LOW_COST_MODEL": "llama3.2",
    },
}


def _show_error(exc: Exception) -> None:
    """Muestra un error de forma amigable; detecta rate limit y muestra el tiempo de espera."""
    if isinstance(exc, RateLimitError):
        msg = str(exc)
        wait_match = re.search(r"try again in ([^.\"]+)", msg, re.IGNORECASE)
        wait_str = wait_match.group(1).strip() if wait_match else "un momento"
        console.print(Panel(
            f"[bold red]Limite de tokens diarios alcanzado.[/bold red]\n\n"
            f"Groq (plan gratuito) permite 100 000 tokens/dia.\n"
            f"Tiempo de espera: [bold yellow]{wait_str}[/bold yellow]\n\n"
            f"Puedes volver a intentarlo cuando se restablezca el limite.",
            title="Rate Limit - Groq",
            border_style="red",
        ))
    else:
        console.print(f"[red]Error: {exc}[/red]")


def configure_provider(provider: str | None, low_cost: bool = False) -> str:
    provider = (provider or os.getenv("OPENAI_PROVIDER", "groq")).lower()
    if provider not in PROVIDER_CONFIGS:
        console.print(
            Panel(
                f"[bold red]Proveedor desconocido:[/bold red] {provider}\n\n"
                f"Proveedores disponibles: {', '.join(PROVIDER_CONFIGS)}",
                title="Configuracion de proveedor",
                border_style="red",
            )
        )
        sys.exit(1)

    config = PROVIDER_CONFIGS[provider]
    os.environ["OPENAI_PROVIDER"] = provider
    os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL", config["OPENAI_BASE_URL"])

    # Permite forzar el modelo via variables de entorno sin ser pisado por defaults.
    if low_cost:
        model = os.getenv("LOW_COST_MODEL") or os.getenv("OPENAI_MODEL") or config["LOW_COST_MODEL"]
    else:
        model = os.getenv("OPENAI_MODEL") or config["OPENAI_MODEL"]
    os.environ["OPENAI_MODEL"] = model
    os.environ["LOW_COST_MODE"] = "1" if low_cost else "0"
    return provider


def check_env() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        console.print(
            Panel(
                "[bold red]OPENAI_API_KEY no configurada.[/bold red]\n\n"
                "Edita el archivo [cyan].env[/cyan] y agrega tu API key.",
                title="Configuracion requerida",
                border_style="red",
            )
        )
        sys.exit(1)


def display_start(requirement: str, output_language: str, provider: str) -> None:
    console.print(
        Panel(
            f"[bold green]Requerimiento:[/bold green]\n{requirement}\n\n"
            f"[bold green]Proveedor:[/bold green] {provider}\n"
            f"[bold green]Modelo:[/bold green] {os.getenv('OPENAI_MODEL', 'gpt-4o')}\n"
            f"[bold green]Idioma:[/bold green] {output_language}",
            title="Iniciando equipo de desarrollo",
            border_style="green",
        )
    )


def _load_role_config() -> dict:
    root = Path(__file__).resolve().parents[2]
    cfg_path = Path(os.getenv("AGENT_MODEL_CONFIG_FILE", root / "shared" / "agent-models.json"))
    if not cfg_path.exists():
        return {}
    with cfg_path.open("r", encoding="utf-8") as handler:
        return json.load(handler)


def _resolve_runtime_model(role_cfg: dict) -> str:
    return role_cfg.get("runtime_model") or role_cfg.get("model") or os.getenv("OPENAI_MODEL", "gpt-4o")


def display_team_setup(user_name: str, requirement: str) -> None:
    role_config = _load_role_config()

    console.print()
    console.print(f"[bold]Proyecto:[/bold] {requirement}")
    console.print(f"[bold]Operador:[/bold] {user_name}")

    table = Table(title="Asignacion de agentes", box=box.SIMPLE, show_header=True)
    table.add_column("Puesto", style="bold")
    table.add_column("Modelo")
    table.add_column("Responsabilidad")

    for role_key, role_name, responsibility in ROLE_BLUEPRINT:
        cfg = role_config.get(role_key, {})
        model_name = _resolve_runtime_model(cfg)
        table.add_row(role_name, model_name, responsibility)

    console.print(table)
    console.print("[dim]Iniciando ejecucion del pipeline...[/dim]")


def display_complete(output_dir: str) -> None:
    files_str = "\n".join(
        f"  [cyan]{name}[/cyan]  - {desc}"
        for name, desc in OUTPUT_FILES
    )
    console.print(
        Panel(
            f"[bold green]El equipo completo el trabajo.[/bold green]\n\n"
            f"Entregables en: [cyan]{output_dir}/[/cyan]\n\n{files_str}",
            title="Trabajo completado",
            border_style="green",
        )
    )


# ── Flowchart ────────────────────────────────────────────────────────────────

_STATUS_COLOR = {
    "completed": "green",
    "failed":    "red",
    "running":   "yellow",
    "pending":   "dim",
}

_STATUS_LABEL = {
    "completed": "DONE",
    "failed":    "FAIL",
    "running":   "...",
    "pending":   "---",
}


def _badge(status: str) -> str:
    color = _STATUS_COLOR.get(status, "white")
    label = _STATUS_LABEL.get(status, "?")
    return f"[{color}][{label}][/{color}]"


def show_flowchart(session: dict) -> None:
    """Muestra un diagrama de flujo ASCII del estado actual del proyecto."""
    steps = session["steps"]
    created = session.get("created_at", "")[:16].replace("T", " ")

    console.print()
    console.print(Panel(
        f"[bold]Proyecto:[/bold] {session['requirement']}\n"
        f"[bold]Sesion:[/bold]   {session['id']}  ({created})\n"
        f"[bold]Idioma:[/bold]   {session['language']}",
        title="Diagrama de flujo del proyecto",
        border_style="cyan",
    ))

    pm  = _badge(steps["pm"])
    be  = _badge(steps["backend"])
    fe  = _badge(steps["frontend"])
    qa  = _badge(steps["qa"])
    sec = _badge(steps["security"])
    dv  = _badge(steps["devops"])
    tw  = _badge(steps["tech_writer"])

    diagram = (
        "\n"
        f"         +---------------------------+\n"
        f"         |    Project Manager        |  {pm}\n"
        f"         +------------+--------------+\n"
        f"                      |\n"
        f"            +---------+---------+\n"
        f"            |                   |\n"
        f"   +--------+-------+  +--------+-------+\n"
        f"   | Backend Dev    |  | Frontend Dev   |\n"
        f"   |   {be}          |  |   {fe}          |\n"
        f"   +--------+-------+  +--------+-------+\n"
        f"            |                   |\n"
        f"            +---------+---------+\n"
        f"                      |\n"
        f"         +------------+--------------+\n"
        f"         |    QA Engineer            |  {qa}\n"
        f"         +------------+--------------+\n"
        f"                      |\n"
        f"         +------------+--------------+\n"
        f"         |    Security Auditor       |  {sec}\n"
        f"         +------------+--------------+\n"
        f"                      |\n"
        f"         +------------+--------------+\n"
        f"         |    DevOps Engineer        |  {dv}\n"
        f"         +------------+--------------+\n"
        f"                      |\n"
        f"         +------------+--------------+\n"
        f"         |    Tech Writer            |  {tw}\n"
        f"         +---------------------------+\n"
    )
    console.print(diagram)

    # Status table
    table = Table(title="Estado detallado", box=box.SIMPLE_HEAVY, show_header=True)
    table.add_column("Agente", style="bold")
    table.add_column("Estado", justify="center")

    status_label = {
        "completed": "[green]Completado[/green]",
        "failed":    "[red]Fallido[/red]",
        "running":   "[yellow]En progreso[/yellow]",
        "pending":   "[dim]Pendiente[/dim]",
    }
    for key, name in STEP_NAMES.items():
        s = steps.get(key, "pending")
        table.add_row(name, status_label.get(s, s))

    console.print(table)

    done = sum(1 for s in steps.values() if s == "completed")
    total = len(steps)
    console.print(f"  [bold]Progreso: {done}/{total} pasos completados[/bold]")

    if session.get("error"):
        console.print(f"\n  [red]Ultimo error:[/red] {session['error']}")
    console.print()


def _status_meta(status: str) -> tuple[str, str]:
        if status == "completed":
                return ("Completado", "ok")
        if status == "running":
                return ("En progreso", "run")
        if status == "failed":
                return ("Fallido", "fail")
        return ("Pendiente", "pending")


def open_visual_flowchart_tab(session: dict) -> None:
        """Genera y abre un diagrama visual minimalista del flujo y estructura de la sesion."""
        output_dir = Path(session["output_dir"])
        run_dir = Path(session.get("run_dir") or output_dir.parent)
        run_dir.mkdir(parents=True, exist_ok=True)

        steps = session.get("steps", {})
        done = sum(1 for s in steps.values() if s == "completed")
        total = len(steps) if steps else 0
        percent = int((done / total) * 100) if total else 0

        flow = [
                ("Fullstack Lead", steps.get("pm", "pending")),
                ("Backend Developer", steps.get("backend", "pending")),
                ("Frontend Developer", steps.get("frontend", "pending")),
                ("QA Engineer", steps.get("qa", "pending")),
                ("Security Auditor", steps.get("security", "pending")),
                ("DevOps Engineer", steps.get("devops", "pending")),
                ("Tech Writer", steps.get("tech_writer", "pending")),
        ]

        output_items = []
        for filename, desc in OUTPUT_FILES:
                exists = (output_dir / filename).exists()
                output_items.append((filename, desc, exists))

        def _node_html(label: str, state: str) -> str:
                text, cls = _status_meta(state)
                return (
                        "<div class='node'>"
                        f"<div class='node-title'>{escape(label)}</div>"
                        f"<span class='pill {cls}'>{escape(text)}</span>"
                        "</div>"
                )

        pm_node = _node_html(flow[0][0], flow[0][1])
        be_node = _node_html(flow[1][0], flow[1][1])
        fe_node = _node_html(flow[2][0], flow[2][1])
        qa_node = _node_html(flow[3][0], flow[3][1])
        sec_node = _node_html(flow[4][0], flow[4][1])
        dv_node = _node_html(flow[5][0], flow[5][1])
        tw_node = _node_html(flow[6][0], flow[6][1])

        files_html = "\n".join(
                (
                        "<li>"
                        f"<span>{escape(name)}</span>"
                        f"<span class='pill {'ok' if exists else 'pending'}'>{'Generado' if exists else 'Pendiente'}</span>"
                        "</li>"
                )
                for name, _, exists in output_items
        )

        html = f"""<!doctype html>
<html lang=\"es\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>AGENTE-S | Diagrama visual</title>
    <style>
        :root {{
            --bg: #040807;
            --bg2: #07110f;
            --card: rgba(11, 22, 18, 0.78);
            --line: #1a3a30;
            --text: #ddf7ee;
            --muted: #8aa59a;
            --ok: #39dba0;
            --run: #f8cf64;
            --fail: #ff7272;
            --pending: #6c877d;
            --neon: #59f7c2;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: "Consolas", "Fira Code", "SFMono-Regular", "Segoe UI", monospace;
            background: radial-gradient(1000px 600px at 100% -50%, #0b221b 0%, var(--bg) 52%), var(--bg2);
            color: var(--text);
            padding: 28px;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }}
        .matrix-rain {{
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: 0.14;
            background-image:
                repeating-linear-gradient(
                    90deg,
                    rgba(89, 247, 194, 0.5) 0,
                    rgba(89, 247, 194, 0.5) 1px,
                    transparent 1px,
                    transparent 24px
                ),
                repeating-linear-gradient(
                    0deg,
                    rgba(89, 247, 194, 0.13) 0,
                    rgba(89, 247, 194, 0.13) 2px,
                    transparent 2px,
                    transparent 20px
                );
            animation: rainShift 7s linear infinite;
        }}
        .scanlines {{
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: 0.12;
            background: repeating-linear-gradient(
                0deg,
                rgba(255, 255, 255, 0.12) 0,
                rgba(255, 255, 255, 0.12) 1px,
                transparent 1px,
                transparent 4px
            );
        }}
        @keyframes rainShift {{
            from {{ transform: translateY(-10px); }}
            to {{ transform: translateY(30px); }}
        }}
        .wrap {{
            max-width: 980px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }}
        .ascii {{
            margin: 0 0 12px;
            color: var(--neon);
            text-shadow: 0 0 10px rgba(89, 247, 194, 0.32);
            white-space: pre;
            font-size: 11px;
            line-height: 1.2;
        }}
        h1 {{
            margin: 0 0 8px;
            font-size: 22px;
            letter-spacing: 0.6px;
            text-shadow: 0 0 12px rgba(89, 247, 194, 0.26);
        }}
        .meta {{ color: var(--muted); margin-bottom: 18px; }}
        .kpi {{
            display: flex; align-items: center; gap: 10px; margin-bottom: 22px;
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 10px 12px;
            backdrop-filter: blur(3px);
            box-shadow: inset 0 0 0 1px rgba(89, 247, 194, 0.08);
        }}
        .bar {{ height: 8px; flex: 1; border-radius: 999px; background: #0f1a17; overflow: hidden; }}
        .bar > span {{ display: block; height: 100%; width: {percent}%; background: linear-gradient(90deg, #36d399, #7dd3fc); box-shadow: 0 0 10px rgba(54, 211, 153, 0.55); }}
        .flow {{ display: grid; gap: 10px; }}
        .row, .split {{ display: grid; gap: 10px; }}
        .row {{ grid-template-columns: 1fr; }}
        .split {{ grid-template-columns: 1fr 1fr; }}
        .arrow {{ text-align: center; color: var(--muted); font-size: 18px; line-height: 1; }}
        .node {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 10px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 50px;
            backdrop-filter: blur(3px);
            box-shadow: inset 0 0 0 1px rgba(89, 247, 194, 0.08);
        }}
        .node-title {{ font-weight: 600; }}
        .pill {{
            font-size: 12px; border-radius: 999px; padding: 3px 9px;
            border: 1px solid transparent; color: #fff;
        }}
        .pill.ok {{ background: rgba(52, 211, 153, .18); border-color: rgba(52, 211, 153, .4); color: #86efac; }}
        .pill.run {{ background: rgba(251, 191, 36, .15); border-color: rgba(251, 191, 36, .38); color: #fde68a; }}
        .pill.fail {{ background: rgba(248, 113, 113, .17); border-color: rgba(248, 113, 113, .4); color: #fecaca; }}
        .pill.pending {{ background: rgba(107, 114, 128, .2); border-color: rgba(107, 114, 128, .42); color: #d1d5db; }}
        .files {{ margin-top: 22px; background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 12px; backdrop-filter: blur(3px); box-shadow: inset 0 0 0 1px rgba(89, 247, 194, 0.08); }}
        .files h2 {{ margin: 0 0 8px; font-size: 15px; color: #dbe3ea; }}
        .files ul {{ margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; }}
        .files li {{ display: flex; justify-content: space-between; gap: 10px; color: #cdd6df; }}
        .tree {{ margin-top: 10px; color: var(--muted); font-size: 13px; line-height: 1.6; }}
        @media (max-width: 720px) {{
            body {{ padding: 16px; }}
            .split {{ grid-template-columns: 1fr; }}
            .ascii {{ font-size: 10px; overflow-x: auto; }}
        }}
    </style>
</head>
<body>
    <div class=\"matrix-rain\"></div>
    <div class=\"scanlines\"></div>
    <div class=\"wrap\">
        <pre class=\"ascii\">  ___   _____ ______ _   _ _____ _____      ____
 / _ \ / ____|  ____| \ | |_   _/ ____|    / __ \
| | | | (___ | |__  |  \| | | || |  __    | |  | |
| | | |\___ \|  __| | . ` | | || | |_ |   | |  | |
| |_| |____) | |____| |\  |_| || |__| |   | |__| |
 \___/|_____/|______|_| \_|_____\_____|    \____/
        </pre>
        <h1>Diagrama visual del proyecto</h1>
        <div class=\"meta\">Sesion {escape(session['id'])} | {escape(session.get('provider', ''))} | {escape(session.get('model', ''))}</div>

        <div class=\"kpi\">
            <strong>Progreso:</strong>
            <span>{done}/{total} pasos</span>
            <div class=\"bar\"><span></span></div>
            <span>{percent}%</span>
        </div>

        <section class=\"flow\">
            <div class=\"row\">{pm_node}</div>
            <div class=\"arrow\">↓</div>
            <div class=\"split\">{be_node}{fe_node}</div>
            <div class=\"arrow\">↓</div>
            <div class=\"row\">{qa_node}</div>
            <div class=\"arrow\">↓</div>
            <div class=\"row\">{sec_node}</div>
            <div class=\"arrow\">↓</div>
            <div class=\"row\">{dv_node}</div>
            <div class=\"arrow\">↓</div>
            <div class=\"row\">{tw_node}</div>
        </section>

        <section class=\"files\">
            <h2>Estructura creada</h2>
            <ul>
                {files_html}
            </ul>
            <div class=\"tree\">
                {escape(str(run_dir))}<br/>
                ├─ session.json<br/>
                └─ output/
            </div>
        </section>
    </div>
</body>
</html>
"""

        html_path = run_dir / "visual_flow.html"
        html_path.write_text(html, encoding="utf-8")
        webbrowser.open_new_tab(html_path.resolve().as_uri())
        console.print(f"[green]Diagrama visual abierto en pestaña:[/green] [cyan]{html_path}[/cyan]")


# ── Session selection ────────────────────────────────────────────────────────

def _select_session(prompt_text: str) -> "dict | None":
    from src.sessions.manager import list_sessions

    sessions = list_sessions()
    if not sessions:
        console.print("\n[yellow]No hay sesiones guardadas aun.[/yellow]")
        return None

    table = Table(title="Sesiones guardadas", box=box.SIMPLE_HEAVY)
    table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="cyan")
    table.add_column("Requerimiento")
    table.add_column("Progreso", justify="center")
    table.add_column("Estado", justify="center")

    for i, s in enumerate(sessions, 1):
        done  = sum(1 for v in s["steps"].values() if v == "completed")
        total = len(s["steps"])
        any_failed = any(v == "failed" for v in s["steps"].values())
        if done == total:
            estado = "[green]Completo[/green]"
        elif any_failed:
            estado = "[red]Fallido[/red]"
        else:
            estado = "[yellow]Incompleto[/yellow]"
        req_short = s["requirement"][:50] + ("..." if len(s["requirement"]) > 50 else "")
        table.add_row(str(i), s["id"], req_short, f"{done}/{total}", estado)

    console.print(table)
    choice = IntPrompt.ask(f"\n{prompt_text} (0 para cancelar)", default=0)
    if choice == 0 or choice > len(sessions):
        return None
    return sessions[choice - 1]


# ── Run helpers ──────────────────────────────────────────────────────────────

def _run_pipeline_safe(session: dict) -> None:
    """Ejecuta el pipeline y maneja errores mostrando como reanudar."""
    from src.crews.dev_crew import run as run_pipeline
    try:
        run_pipeline(session["requirement"], session["language"], session)
        done = sum(1 for s in session["steps"].values() if s == "completed")
        if done == len(session["steps"]):
            display_complete(session["output_dir"])
            if session.get("run_dir"):
                console.print(f"[dim]Carpeta del proyecto: {session['run_dir']}[/dim]")
            if session.get("session_file"):
                console.print(f"[dim]Sesion: {session['session_file']}[/dim]")
        else:
            console.print(
                f"\n[yellow]Pipeline detenido. Sesion guardada: "
                f"[bold]{session['id']}[/bold][/yellow]"
            )
            console.print(f"[yellow]Entregables parciales en:[/yellow] [cyan]{session['output_dir']}[/cyan]")
            if session.get("session_file"):
                console.print(f"[yellow]Archivo de sesion:[/yellow] [cyan]{session['session_file']}[/cyan]")
    except Exception as exc:
        _show_error(exc)
        console.print(
            f"\n[yellow]Sesion guardada. Usa 'Continuar sesion' para reanudar: "
            f"[bold]{session['id']}[/bold][/yellow]"
        )
        console.print(f"[yellow]Entregables parciales en:[/yellow] [cyan]{session['output_dir']}[/cyan]")
        if session.get("session_file"):
            console.print(f"[yellow]Archivo de sesion:[/yellow] [cyan]{session['session_file']}[/cyan]")


def run_new(requirement: str, output_language: str, user_name: str = "Usuario") -> None:
    from src.sessions.manager import create_session, save_session

    os.environ["OUTPUT_LANGUAGE"] = output_language
    os.environ["PROJECT_USER_NAME"] = user_name
    session = create_session(requirement, output_language)
    save_session(session)
    provider = os.getenv("OPENAI_PROVIDER", "groq")
    display_team_setup(user_name, requirement)
    display_start(requirement, output_language, provider)
    _run_pipeline_safe(session)


def run_guided_new_project(output_language: str) -> None:
    user_name = Prompt.ask(
        "[bold yellow]Como te llamas?[/bold yellow]",
        default=os.getenv("PROJECT_USER_NAME", "Usuario"),
    ).strip() or "Usuario"

    requirement = Prompt.ask(
        "\n[bold yellow]Que tarea quieres que realice el equipo?[/bold yellow]",
        default=DEFAULT_LIBRARY_REQUIREMENT,
    ).strip()

    run_new(requirement, output_language, user_name=user_name)


def run_quickstart_new_project(output_language: str) -> None:
    """Inicio rapido: un solo prompt para requerimiento y arranque inmediato."""
    requirement = Prompt.ask(
        "[bold yellow]Requerimiento del proyecto[/bold yellow]",
        default=DEFAULT_LIBRARY_REQUIREMENT,
    ).strip()

    run_new(
        requirement,
        output_language,
        user_name=os.getenv("PROJECT_USER_NAME", "Usuario"),
    )


def run_continue(session: dict) -> None:
    os.environ["OUTPUT_LANGUAGE"] = session["language"]
    os.environ["OPENAI_PROVIDER"] = session.get("provider", os.getenv("OPENAI_PROVIDER", "groq"))
    os.environ["OPENAI_MODEL"] = session.get("model", os.getenv("OPENAI_MODEL", "gpt-4o"))
    os.environ["OPENAI_BASE_URL"] = session.get("openai_base_url", os.getenv("OPENAI_BASE_URL", "")) or ""
    os.environ["LOW_COST_MODE"] = "1" if session.get("low_cost", False) else "0"

    console.print(f"\n[bold cyan]Reanudando sesion: {session['id']}[/bold cyan]")
    provider = os.getenv("OPENAI_PROVIDER", "groq")
    display_start(session["requirement"], session["language"], provider)
    _run_pipeline_safe(session)


def open_project() -> None:
    """Pide la ruta de un proyecto externo, lo escanea, lo analiza y entra en modo consulta."""
    from pathlib import Path
    from src.crews.dev_crew import analyze_external_project, ask_about_project

    console.print()
    folder_raw = Prompt.ask(
        "[bold yellow]Ruta de la carpeta raiz del proyecto[/bold yellow]\n"
        "  (ejemplo: C:\\Users\\yo\\mi-proyecto)"
    )
    folder_path = folder_raw.strip().strip('"').strip("'")

    if not Path(folder_path).is_dir():
        console.print(f"[red]La carpeta no existe o no es accesible: {folder_path}[/red]")
        return

    lang = os.getenv("OUTPUT_LANGUAGE", "espanol")

    console.print(Panel(
        f"Leyendo archivos de:\n[cyan]{folder_path}[/cyan]\n\n"
        "Esto puede tomar unos segundos...",
        title="Abriendo proyecto externo",
        border_style="cyan",
    ))

    try:
        session, analysis = analyze_external_project(folder_path, lang)
    except Exception as exc:
        _show_error(exc)
        return

    console.print()
    console.print(Panel(
        analysis[:900] + ("...\n\n[dim](analisis completo en 00_project_analysis.md)[/dim]"
                          if len(analysis) > 900 else ""),
        title="Analisis inicial del proyecto",
        border_style="green",
    ))

    # Modo consulta interactiva
    console.print(Panel(
        "Ahora puedes preguntarme cualquier cosa sobre este proyecto.\n"
        "Ejemplos: ¿como mejoro la seguridad? / ¿que falta para produccion?\n"
        "[dim]Deja en blanco, escribe 'menu' o un numero del menu (1-6) para volver.[/dim]",
        title="Modo consulta",
        border_style="cyan",
    ))

    _MENU_EXITS = {"", "menu", "salir", "exit", "volver", "1", "2", "3", "4", "5", "6", "7"}

    while True:
        question = Prompt.ask("\n[bold yellow]Pregunta[/bold yellow]")
        if question.strip().lower() in _MENU_EXITS:
            break
        try:
            answer = ask_about_project(session, question.strip())
            console.print(Panel(answer, title="Technical Lead", border_style="magenta"))
        except Exception as exc:
            _show_error(exc)


def lead_review(session: dict) -> None:
    """Ejecuta el Technical Lead para revisar todos los entregables y tomar el liderazgo."""
    from src.crews.dev_crew import run_lead

    done = sum(1 for s in session["steps"].values() if s == "completed")
    if done == 0:
        console.print("\n[yellow]Esta sesion no tiene entregables aun. Ejecuta el pipeline primero.[/yellow]")
        return

    console.print()
    console.print(Panel(
        f"[bold]Proyecto:[/bold] {session['requirement']}\n\n"
        f"El Technical Lead revisara los [bold]{done}[/bold] entregable(s) disponibles\n"
        f"y emitira directivas para el equipo.",
        title="Technical Lead - Tomando el liderazgo",
        border_style="magenta",
    ))

    try:
        review = run_lead(session)
        console.print()
        console.print(Panel(
            f"[bold magenta]Revision guardada en:[/bold magenta]\n"
            f"  [cyan]{session['output_dir']}/00_lead_review.md[/cyan]\n\n"
            f"[bold]Vista previa:[/bold]\n{review[:600]}{'...' if len(review) > 600 else ''}",
            title="Lead Review completada",
            border_style="magenta",
        ))
    except Exception as exc:
        _show_error(exc)


# ── Main menu ────────────────────────────────────────────────────────────────

def show_usage_guide() -> None:
    """Muestra una guia paso a paso para usar el proyecto con un ejemplo Hello World con efectos."""
    guide = (
        "[bold]Modo de uso: paso a paso[/bold]\n\n"
        "1. Asegurate de tener un entorno Python activo y las dependencias instaladas:\n"
        "   python -m pip install -r requirements.txt\n\n"
        "2. Configura tu .env con la API key y el proveedor, por ejemplo con Groq:\n"
        "   OPENAI_API_KEY=gsk_...\n"
        "   OPENAI_BASE_URL=https://api.groq.com/openai/v1\n"
        "   OPENAI_MODEL=llama-3.3-70b-versatile\n"
        "   OPENAI_PROVIDER=groq\n\n"
        "3. Ejecuta este ejemplo con bajo costo usando Groq:\n"
        "   python main.py --req \"Hello World con efectos animados en una app web\" "
        "--provider groq --low-cost --lang espanol\n\n"
        "4. El proyecto creara una sesion y generara los entregables en la carpeta [cyan]output/[/cyan].\n"
        "   Revisa especialmente estos archivos:\n"
        "   - output/01_plan_tecnico.md\n"
        "   - output/02_backend_code.md\n"
        "   - output/03_frontend_code.md\n\n"
        "5. Si quieres repetir el ejemplo, selecciona \"Nuevo proyecto\" en el menu.\n"
        "   Copia este prompt exacto:\n\n"
        "   \"Crea un proyecto web simple que muestre un \"Hello World\" con efectos visuales, animaciones suaves, y un boton que cambia el color de fondo. Entregame el plan tecnico, backend, frontend y documentacion.\"\n\n"
        "6. Para reanudar una sesion existente, usa la opcion \"Continuar sesion guardada\".\n\n"
        "[bold]Consejo:[/bold] Si quieres gastar aun menos tokens, mantén el prompt claro y directo, y usa --low-cost."
    )
    console.print(Panel(guide, title="Guia de uso", border_style="blue", width=90))


def show_main_menu(output_language: str) -> None:
    while True:
        console.print()
        console.print(Panel(
            "[bold]1.[/bold]  Nuevo proyecto (guiado)\n"
            "[bold]2.[/bold]  Continuar sesion guardada\n"
            "[bold]3.[/bold]  Ver diagrama de flujo\n"
            "[bold]4.[/bold]  Abrir proyecto\n"
            "[bold]5.[/bold]  Tomar liderazgo (Lead Review)\n"
            "[bold]6.[/bold]  Abrir diagrama visual (pestana)\n"
            "[bold]7.[/bold]  Modo de uso\n"
            "[bold]8.[/bold]  Salir",
            title="Menu",
            border_style="white",
            width=44,
        ))
        choice = Prompt.ask(
            "[bold yellow]Elige una opcion[/bold yellow]",
            choices=["1", "2", "3", "4", "5", "6", "7", "8"],
            default="1",
        )

        if choice == "1":
            run_guided_new_project(output_language)

        elif choice == "2":
            session = _select_session("Elige el numero de sesion a continuar")
            if session:
                run_continue(session)

        elif choice == "3":
            session = _select_session("Elige el numero de sesion para ver el diagrama")
            if session:
                show_flowchart(session)

        elif choice == "4":
            open_project()

        elif choice == "5":
            session = _select_session("Elige el numero de sesion para la revision del Lead")
            if session:
                lead_review(session)

        elif choice == "6":
            session = _select_session("Elige el numero de sesion para abrir el diagrama visual")
            if session:
                open_visual_flowchart_tab(session)

        elif choice == "7":
            show_usage_guide()

        elif choice == "8":
            console.print("[dim]Hasta luego.[/dim]")
            break


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Equipo de desarrollo multi-agente IA")
    parser.add_argument(
        "--req", "--requirement", type=str, default=None, dest="req",
        help="Requerimiento del proyecto (omite para menu interactivo)",
    )
    parser.add_argument(
        "--lang", type=str, default=None,
        help="Idioma de salida: espanol | english",
    )
    parser.add_argument(
        "--provider", type=str, default=None,
        help="Proveedor de IA: groq | openai | ollama",
    )
    parser.add_argument(
        "--low-cost", action="store_true",
        help="Usar un modelo de IA de menor costo",
    )
    parser.add_argument(
        "--usage", action="store_true",
        help="Mostrar el modo de uso paso a paso y salir",
    )
    parser.add_argument(
        "--user", type=str, default=None,
        help="Nombre de usuario para una experiencia guiada",
    )
    parser.add_argument(
        "--menu", action="store_true",
        help="Mostrar menu completo en lugar de inicio rapido",
    )
    parser.add_argument(
        "--guided", action="store_true",
        help="Usar nuevo proyecto guiado (nombre + requerimiento)",
    )
    args = parser.parse_args()

    console.print(Text(BANNER, style="bold cyan"))
    if args.usage:
        show_usage_guide()
        return

    low_cost = args.low_cost or os.getenv("LOW_COST_MODE", "0") == "1"
    provider = configure_provider(args.provider, low_cost=low_cost)
    check_env()

    output_language = args.lang or os.getenv("OUTPUT_LANGUAGE", "espanol")

    if args.req:
        # Modo directo: sin menu
        run_new(args.req.strip(), output_language, user_name=args.user or os.getenv("PROJECT_USER_NAME", "Usuario"))
    else:
        # Modo interactivo por defecto: inicio rapido con un solo prompt.
        if args.menu:
            show_main_menu(output_language)
        elif args.guided:
            run_guided_new_project(output_language)
        else:
            run_quickstart_new_project(output_language)