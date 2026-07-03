"""
Pipeline de desarrollo: ejecuta los agentes en secuencia con Backend+Frontend en paralelo.
No tiene dependencias de UI - cualquier interfaz puede importar run() directamente.
"""

import asyncio
import os
import re
from pathlib import Path
from contextlib import suppress

from rich.console import Console
from agents import Runner, RunResult
from openai import RateLimitError

from src.agents.team import get_agents
from src.sessions.manager import create_session, save_session

console = Console()

STEP_LABELS = {
    "pm": "Fullstack Lead",
    "backend": "Backend Developer",
    "frontend": "Frontend Developer",
    "qa": "QA Engineer",
    "security": "Security Auditor",
    "devops": "DevOps Engineer",
    "tech_writer": "Tech Writer",
}


def _build_progress_bar(done: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return "[------------------------]"
    ratio = done / total
    filled = int(ratio * width)
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def _print_pipeline_progress(session: dict, heading: str = "Estado") -> None:
    steps = session.get("steps", {})
    total = len(steps)
    done = sum(1 for s in steps.values() if s == "completed")
    running = sum(1 for s in steps.values() if s == "running")
    failed = sum(1 for s in steps.values() if s == "failed")
    bar = _build_progress_bar(done, total)
    pct = int((done / total) * 100) if total else 0
    console.print(
        f"[bold blue]{heading}[/bold blue]  {bar}  {done}/{total} ({pct}%)  "
        f"[yellow]en ejecucion: {running}[/yellow]  [red]fallidos: {failed}[/red]"
    )


async def _heartbeat(step_label: str, stop_event: asyncio.Event) -> None:
    elapsed = 0
    while not stop_event.is_set():
        await asyncio.sleep(12)
        elapsed += 12
        if not stop_event.is_set():
            console.print(
                f"[dim]   trabajando {step_label}... {elapsed}s transcurridos[/dim]"
            )


def _output_path(session: dict, filename: str) -> Path:
    d = Path(session["output_dir"])
    d.mkdir(parents=True, exist_ok=True)
    return d / filename


def _save_output(session: dict, filename: str, content: str) -> None:
    _output_path(session, filename).write_text(content, encoding="utf-8")


def _load_output(session: dict, filename: str) -> str:
    path = _output_path(session, filename)
    return path.read_text(encoding="utf-8") if path.exists() else ""


async def _run_agent(agent, input_text: str, step_label: str,
                     session: dict, step_key: str) -> RunResult:
    console.print(f"\n[bold cyan]>> {step_label}[/bold cyan]")
    session["steps"][step_key] = "running"
    save_session(session)
    _print_pipeline_progress(session, heading="Progreso")

    stop_event = asyncio.Event()
    heartbeat_task = asyncio.create_task(_heartbeat(step_label, stop_event))
    try:
        result = await Runner.run(agent, input=input_text)
        console.print(f"[green]   Completado[/green]")
        session["steps"][step_key] = "completed"
        session["error"] = None
        save_session(session)
        _print_pipeline_progress(session, heading="Progreso")
        return result
    except RateLimitError as exc:
        msg = str(exc)
        wait_match = re.search(r"try again in ([^.\"]+)", msg, re.IGNORECASE)
        wait_str = wait_match.group(1).strip() if wait_match else "un momento"
        console.print(
            f"[red]   Limite de tokens alcanzado. "
            f"Intenta de nuevo en [bold]{wait_str}[/bold][/red]"
        )
        session["steps"][step_key] = "failed"
        session["error"] = (
            f"Rate limit en '{step_label}'. Espera {wait_str} y usa "
            f"'Continuar sesion' para reanudar."
        )
        save_session(session)
        _print_pipeline_progress(session, heading="Progreso")
        raise
    except Exception as exc:
        console.print(f"[red]   Fallo: {exc}[/red]")
        session["steps"][step_key] = "failed"
        session["error"] = f"Error en '{step_label}': {exc}"
        save_session(session)
        _print_pipeline_progress(session, heading="Progreso")
        raise
    finally:
        stop_event.set()
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task


async def run_dev_pipeline(requirement: str, output_language: str,
                           session: dict | None = None) -> dict:
    """
    Pipeline:
      1. Project Manager (plan)
      2. Backend + Frontend  (paralelo)
      3. QA Engineer
      4. Security Auditor
      5. DevOps Engineer
      6. Tech Writer
    Reanuda automaticamente desde el ultimo paso completado si se pasa session.
    """
    if session is None:
        session = create_session(requirement, output_language)
        save_session(session)

    (project_manager, backend_developer, frontend_developer, qa_engineer,
     security_auditor, devops_engineer, tech_writer, tech_lead) = \
        get_agents(output_language)

    outputs: dict = {}

    # ── 1. Project Manager ──────────────────────────────────────────────
    if session["steps"]["pm"] == "completed":
        outputs["plan"] = _load_output(session, "01_plan_tecnico.md")
        console.print(f"\n[dim]>> 1/6  Project Manager  (ya completado, omitido)[/dim]")
    else:
        pm_result = await _run_agent(
            project_manager,
            f"Requerimiento del cliente:\n{requirement}\n\nIdioma de todos los entregables: {output_language}",
            "1/6  Fullstack Lead - Plan tecnico y division por partes",
            session, "pm",
        )
        outputs["plan"] = pm_result.final_output
        _save_output(session, "01_plan_tecnico.md", outputs["plan"])

    # ── 2. Backend + Frontend en paralelo ───────────────────────────────
    be_done = session["steps"]["backend"] == "completed"
    fe_done = session["steps"]["frontend"] == "completed"

    if be_done:
        outputs["backend"] = _load_output(session, "02_backend_code.md")
        console.print(f"\n[dim]>> 2a/6  Backend Developer  (ya completado, omitido)[/dim]")
    if fe_done:
        outputs["frontend"] = _load_output(session, "03_frontend_code.md")
        console.print(f"\n[dim]>> 2b/6  Frontend Developer  (ya completado, omitido)[/dim]")

    if not be_done or not fe_done:
        base = f"Requerimiento original:\n{requirement}\n\nPlan tecnico:\n{outputs['plan']}\n\nIdioma: {output_language}"
        console.print("\n[bold yellow]>> Ejecutando Backend y Frontend en paralelo...[/bold yellow]")
        tasks = []
        if not be_done:
            tasks.append(_run_agent(backend_developer, base, "2a/6  Backend Developer - API y BD", session, "backend"))
        if not fe_done:
            tasks.append(_run_agent(frontend_developer, base, "2b/6  Frontend Developer - UI", session, "frontend"))
        results = await asyncio.gather(*tasks)
        idx = 0
        if not be_done:
            outputs["backend"] = results[idx].final_output
            _save_output(session, "02_backend_code.md", outputs["backend"])
            idx += 1
        if not fe_done:
            outputs["frontend"] = results[idx].final_output
            _save_output(session, "03_frontend_code.md", outputs["frontend"])

    # ── 3. QA Engineer ──────────────────────────────────────────────────
    if session["steps"]["qa"] == "completed":
        outputs["qa"] = _load_output(session, "04_qa_report.md")
        console.print(f"\n[dim]>> 3/6  QA Engineer  (ya completado, omitido)[/dim]")
    else:
        qa_result = await _run_agent(
            qa_engineer,
            f"Requerimiento original:\n{requirement}\n\nPlan tecnico:\n{outputs['plan']}\n\n"
            f"Codigo backend:\n{outputs['backend']}\n\nCodigo frontend:\n{outputs['frontend']}\n\nIdioma: {output_language}",
            "3/6  QA Engineer - Revision y tests",
            session, "qa",
        )
        outputs["qa"] = qa_result.final_output
        _save_output(session, "04_qa_report.md", outputs["qa"])

    # ── 4. Security Auditor ─────────────────────────────────────────────
    if session["steps"]["security"] == "completed":
        outputs["security"] = _load_output(session, "05_security_report.md")
        console.print(f"\n[dim]>> 4/6  Security Auditor  (ya completado, omitido)[/dim]")
    else:
        sec_result = await _run_agent(
            security_auditor,
            f"Requerimiento original:\n{requirement}\n\nCodigo backend:\n{outputs['backend']}\n\n"
            f"Codigo frontend:\n{outputs['frontend']}\n\nIdioma: {output_language}",
            "4/6  Security Auditor - Auditoria de seguridad",
            session, "security",
        )
        outputs["security"] = sec_result.final_output
        _save_output(session, "05_security_report.md", outputs["security"])

    # ── 5. DevOps Engineer ──────────────────────────────────────────────
    if session["steps"]["devops"] == "completed":
        outputs["devops"] = _load_output(session, "06_devops_config.md")
        console.print(f"\n[dim]>> 5/6  DevOps Engineer  (ya completado, omitido)[/dim]")
    else:
        dv_result = await _run_agent(
            devops_engineer,
            f"Requerimiento original:\n{requirement}\n\nPlan tecnico:\n{outputs['plan']}\n\n"
            f"Informe QA:\n{outputs['qa']}\n\nInforme de seguridad:\n{outputs['security']}\n\nIdioma: {output_language}",
            "5/6  DevOps Engineer - Infraestructura y CI/CD",
            session, "devops",
        )
        outputs["devops"] = dv_result.final_output
        _save_output(session, "06_devops_config.md", outputs["devops"])

    # ── 6. Tech Writer ──────────────────────────────────────────────────
    if session["steps"]["tech_writer"] == "completed":
        outputs["docs"] = _load_output(session, "07_documentation.md")
        console.print(f"\n[dim]>> 6/6  Tech Writer  (ya completado, omitido)[/dim]")
    else:
        tw_result = await _run_agent(
            tech_writer,
            f"Requerimiento original:\n{requirement}\n\nPlan tecnico:\n{outputs['plan']}\n\n"
            f"Backend:\n{outputs['backend']}\n\nFrontend:\n{outputs['frontend']}\n\n"
            f"DevOps:\n{outputs['devops']}\n\nIdioma: {output_language}",
            "6/6  Tech Writer - Documentacion final",
            session, "tech_writer",
        )
        outputs["docs"] = tw_result.final_output
        _save_output(session, "07_documentation.md", outputs["docs"])

    return outputs


def run(requirement: str, output_language: str, session: dict | None = None) -> dict:
    return asyncio.run(run_dev_pipeline(requirement, output_language, session))


# ── Lead Review ──────────────────────────────────────────────────────────────

_OUTPUT_FILES = [
    ("01_plan_tecnico.md",    "Plan tecnico"),
    ("02_backend_code.md",    "Codigo backend"),
    ("03_frontend_code.md",   "Codigo frontend"),
    ("04_qa_report.md",       "Informe QA"),
    ("05_security_report.md", "Informe seguridad"),
    ("06_devops_config.md",   "Configuracion DevOps"),
    ("07_documentation.md",   "Documentacion"),
]


async def _run_lead_review(session: dict) -> str:
    sections = []
    for filename, label in _OUTPUT_FILES:
        content = _load_output(session, filename)
        if content:
            sections.append(f"=== {label} ({filename}) ===\n{content}")

    if not sections:
        return "No hay entregables disponibles para revisar en esta sesion."

    import json as _json
    (_, _, _, _, _, _, _, tech_lead) = get_agents(session["language"])

    input_text = (
        f"Requerimiento original:\n{session['requirement']}\n\n"
        f"Estado del pipeline:\n{_json.dumps(session['steps'], indent=2)}\n\n"
        f"Entregables del equipo:\n\n" + "\n\n".join(sections) +
        f"\n\nIdioma de la revision: {session['language']}"
    )

    console.print("\n[bold magenta]>> Technical Lead - Tomando el liderazgo...[/bold magenta]")
    result = await Runner.run(tech_lead, input=input_text)
    console.print("[green]   Revision completada[/green]")
    review = result.final_output
    _save_output(session, "00_lead_review.md", review)
    return review


def run_lead(session: dict) -> str:
    return asyncio.run(_run_lead_review(session))


# ── External project analysis ────────────────────────────────────────────────

_PRIORITY_NAMES = {
    "readme.md", "readme.txt", "readme.rst",
    "package.json", "requirements.txt", "pyproject.toml",
    "cargo.toml", "pom.xml", "build.gradle",
    "docker-compose.yml", "docker-compose.yaml", "dockerfile",
    ".env.example", "env.example",
    "main.py", "app.py", "server.py", "manage.py",
    "index.js", "index.ts", "server.js", "app.js", "app.ts",
}

_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go",
    ".rs", ".cpp", ".c", ".h", ".cs", ".rb", ".php",
    ".html", ".css", ".scss", ".sql", ".sh",
    ".yml", ".yaml", ".json", ".toml", ".cfg", ".ini",
}

_SKIP_DIRS = {
    "node_modules", "__pycache__", "dist", "build",
    ".git", "venv", ".venv", "env", ".env",
    "target", "out", "coverage", ".next", ".nuxt",
}


def _build_tree(folder: Path) -> tuple[list[str], list[Path]]:
    """Devuelve (lineas_del_arbol, lista_de_archivos) sin leer contenido."""
    tree_lines: list[str] = []
    all_files:  list[Path] = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS and not d.startswith("."))
        rel_root = Path(root).relative_to(folder)
        depth = len(rel_root.parts)
        prefix = "  " * depth
        label = Path(root).name if depth > 0 else folder.name
        tree_lines.append(f"{prefix}{label}/")
        for f in sorted(files):
            tree_lines.append(f"{prefix}  {f}")
            all_files.append(Path(root) / f)
    return tree_lines, all_files


def _scan_light(folder: Path) -> tuple[str, str]:
    """
    Modo economico: arbol de archivos + README solamente.
    ~500-2000 tokens de entrada. Ideal para el analisis inicial.
    """
    tree_lines, all_files = _build_tree(folder)
    tree_str = "\n".join(tree_lines[:200])

    readme = ""
    for f in all_files:
        if f.name.lower() in ("readme.md", "readme.txt", "readme.rst"):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore").strip()
                readme = text[:3_000]
                if len(text) > 3_000:
                    readme += "\n[... truncado]"
            except Exception:
                pass
            break

    return tree_str, readme


def _scan_deep(folder: Path, max_files: int = 8, max_total: int = 12_000) -> str:
    """
    Modo detallado: lee archivos clave para responder preguntas especificas.
    Limite conservador para no gastar tokens.
    """
    MAX_PER_FILE = 2_500
    _, all_files = _build_tree(folder)

    read_files: set[Path] = set()
    contents:   list[str] = []
    total = 0

    def _read(path: Path) -> None:
        nonlocal total
        if path in read_files or total >= max_total or len(read_files) >= max_files:
            return
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                return
            chunk = text[:MAX_PER_FILE]
            contents.append(f"=== {path.relative_to(folder)} ===\n{chunk}"
                            + ("\n[truncado]" if len(text) > MAX_PER_FILE else ""))
            total += len(chunk)
            read_files.add(path)
        except Exception:
            pass

    for f in all_files:
        if f.name.lower() in _PRIORITY_NAMES:
            _read(f)
    for f in all_files:
        if f not in read_files and f.suffix.lower() in _CODE_EXTENSIONS:
            _read(f)

    return "\n\n".join(contents)


async def _analyze_project(folder_path: str, language: str) -> tuple[dict, str]:
    folder = Path(folder_path)
    tree, readme = _scan_light(folder)

    # Crear sesion
    from src.sessions.manager import create_session, save_session
    session = create_session(f"[Externo] {folder.name}", language)
    session["external_folder"] = str(folder.resolve())
    save_session(session)

    # Guardar solo arbol + readme como contexto base
    _save_output(session, "_context.txt", f"ARBOL:\n{tree}\n\nREADME:\n{readme}")

    readme_block = f"\nREADME:\n{readme}" if readme else ""
    input_text = (
        f"Analiza este proyecto basandote en su estructura de archivos"
        f"{' y README' if readme else ''}.\n\n"
        f"Responde en Markdown con:\n"
        f"1. De que trata el proyecto\n"
        f"2. Stack tecnologico detectado\n"
        f"3. Estado (completo / en desarrollo / prototipo)\n"
        f"4. Que hace cada carpeta/archivo principal\n"
        f"5. Primeras recomendaciones (max 3 puntos)\n\n"
        f"Proyecto: {folder.name}\n"
        f"Ruta: {folder_path}\n\n"
        f"Estructura:\n{tree}"
        f"{readme_block}\n\n"
        f"Idioma: {language}. Se breve y directo."
    )

    console.print("\n[bold magenta]>> Analizando proyecto externo...[/bold magenta]")
    result = await Runner.run(tech_lead, input=input_text)
    analysis = result.final_output
    console.print("[green]   Analisis completado[/green]")
    _save_output(session, "00_project_analysis.md", analysis)
    return session, analysis


async def _ask_project(session: dict, question: str) -> str:
    folder_path = session.get("external_folder", "")
    base_context = _load_output(session, "_context.txt")  # arbol + readme (ligero)

    # Si la pregunta parece pedir codigo/implementacion, carga archivos adicionales
    code_keywords = ("codigo", "code", "implementa", "archivo", "file", "funcion",
                     "function", "clase", "class", "como funciona", "error", "bug")
    needs_code = any(k in question.lower() for k in code_keywords)

    extra = ""
    if needs_code and folder_path and Path(folder_path).is_dir():
        extra = "\n\nARCHIVOS DE CODIGO (seleccion):\n" + _scan_deep(Path(folder_path))

    input_text = (
        f"Proyecto: {session.get('external_folder', session['requirement'])}\n\n"
        f"Contexto:\n{base_context}{extra}\n\n"
        f"Pregunta: {question}\n\n"
        f"Responde de forma clara y directa. Idioma: {session['language']}"
    )
    result = await Runner.run(tech_lead, input=input_text)
    return result.final_output


def analyze_external_project(folder_path: str, language: str) -> tuple[dict, str]:
    return asyncio.run(_analyze_project(folder_path, language))


def ask_about_project(session: dict, question: str) -> str:
    return asyncio.run(_ask_project(session, question))