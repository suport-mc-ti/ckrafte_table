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
+----------------------------------------------------------------------+
|                      AGENTE-S / MODO TERMINAL                        |
|                    Fullstack AI + Professional Team                  |
+----------------------------------------------------------------------+
| Fullstack Lead | Backend Dev | Frontend Dev | QA | Security | DevOps |
+----------------------------------------------------------------------+
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
    os.environ["OPENAI_BASE_URL"] = config["OPENAI_BASE_URL"]
    model = config["LOW_COST_MODEL"] if low_cost else config["OPENAI_MODEL"]
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
    console.print(Panel(
        f"Hola [bold cyan]{user_name}[/bold cyan].\n\n"
        "Actuare como Agente Fullstack con un equipo profesional especializado. "
        "Con una sola peticion, el sistema divide el proyecto por partes y asigna "
        "automaticamente cada parte al agente adecuado.",
        title="Bienvenida",
        border_style="cyan",
    ))

    console.print(Panel(
        f"[bold]Tarea recibida:[/bold]\n{requirement}",
        title="Solicitud del usuario",
        border_style="green",
    ))

    table = Table(title="Proyecto dividido por partes y agentes", box=box.SIMPLE_HEAVY, show_header=True)
    table.add_column("Puesto", style="bold")
    table.add_column("Agente IA")
    table.add_column("Responsabilidad")

    for role_key, role_name, responsibility in ROLE_BLUEPRINT:
        cfg = role_config.get(role_key, {})
        model_name = _resolve_runtime_model(cfg)
        table.add_row(role_name, model_name, responsibility)

    console.print(table)
    console.print("[bold green]Iniciando trabajo del equipo...[/bold green]")


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
        else:
            console.print(
                f"\n[yellow]Pipeline detenido. Sesion guardada: "
                f"[bold]{session['id']}[/bold][/yellow]"
            )
    except Exception as exc:
        _show_error(exc)
        console.print(
            f"\n[yellow]Sesion guardada. Usa 'Continuar sesion' para reanudar: "
            f"[bold]{session['id']}[/bold][/yellow]"
        )


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
            "[bold]1.[/bold]  Nuevo proyecto\n"
            "[bold]2.[/bold]  Continuar sesion guardada\n"
            "[bold]3.[/bold]  Ver diagrama de flujo\n"
            "[bold]4.[/bold]  Abrir proyecto\n"
            "[bold]5.[/bold]  Tomar liderazgo (Lead Review)\n"
            "[bold]6.[/bold]  Modo de uso\n"
            "[bold]7.[/bold]  Salir",
            title="Menu principal",
            border_style="cyan",
            width=46,
        ))
        choice = Prompt.ask(
            "[bold yellow]Elige una opcion[/bold yellow]",
            choices=["1", "2", "3", "4", "5", "6", "7"],
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
            show_usage_guide()

        elif choice == "7":
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
        # Modo interactivo: mostrar menu
        console.print(Panel(
            "[bold]Bienvenido al equipo multi-agente IA.[/bold]\n\n"
            "Te pedire tu nombre y la tarea principal. Luego el Fullstack Lead "
            "dividira el proyecto por partes, asignara cada parte al agente adecuado "
            "y arrancara la ejecucion automaticamente.",
            title="Inicio guiado",
            border_style="blue",
        ))
        show_main_menu(output_language)