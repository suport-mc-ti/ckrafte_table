# ckrafte_table

[![CI](https://github.com/suport-mc-ti/ckrafte_table/actions/workflows/ci.yml/badge.svg)](https://github.com/suport-mc-ti/ckrafte_table/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Proyecto ckrafte_table para generar soluciones de software separadas por roles: backend, frontend e infraestructura.

## Que hace

1. Recibe un requerimiento en lenguaje natural.
2. Lo divide por responsabilidades tecnicas.
3. Ejecuta un flujo con agentes especializados.
4. Genera artefactos de salida en markdown/codigo para continuar desarrollo.

## Instalacion

Requisitos minimos:

1. Python 3.11+
2. Node.js 20+
3. Git
4. Ollama (si usas proveedor local)

Pasos:

```bash
git clone https://github.com/suport-mc-ti/ckrafte_table.git
cd ckrafte_table
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
npm --prefix frontend install
```

## Uso rapido

Ejecutar frontend y backend en VS Code:

1. Run Task -> dev:all

Ejecutar pipeline por CLI:

```bash
python main.py --provider ollama --lang espanol --req "API local para biblioteca comunitaria con catalogo, prestamos y devoluciones"
```

Modo interactivo rapido (1 prompt):

```bash
python main.py --provider ollama --lang espanol
```

Menu completo (incluye diagrama visual en pestana):

```bash
python main.py --provider ollama --lang espanol --menu
```

Si usas Ollama, valida modelos base:

```bash
ollama pull phi3
ollama pull codellama
ollama pull starcoder2
```

## Alcances

1. Prototipado acelerado de soluciones fullstack.
2. Generacion guiada de entregables tecnicos por rol.
3. Base para equipos pequenos que quieran flujo local sin servicios pagos.

## Aptitudes

1. Backend: estructura de APIs, rutas y contratos basicos.
2. Frontend: base React/Vite para iterar interfaz.
3. Infra: soporte Docker y scripts de arranque.
4. Orquestacion: pipeline de ckrafte_table configurable por proveedor/modelo.

## Estructura

```text
backend/      API y contratos
frontend/     UI React + Vite
infra/        Dockerfiles y scripts de bootstrap
shared/       Configuracion de modelos por agente
src/          Motor/orquestacion del pipeline
```

## Notas

1. Este repositorio prioriza entorno local y flujo reproducible.
2. Puedes adaptar modelos y prompts segun capacidad de hardware y objetivo del proyecto.

Tareas incluidas:

- `dev:backend`
- `dev:frontend`
- `dev:all`
- `bootstrap:windows`
- `run:ollama-pipeline`
- `run:service-mode:library`
- `run:service-mode:from-env`
- `run:service-mode:env-requirement`

## Componentes incluidos

### Backend

El backend usa Flask e incluye:

- `GET /health`
- `GET /api/agents`
- `GET /api/lessons`

### Frontend

El frontend usa React con Vite y muestra:

- los roles de agentes,
- el modelo local asignado a cada uno,
- el stack principal de cada área.

### Infra

La infraestructura incluye:

- `docker-compose.yml` para backend + frontend,
- Dockerfiles separados,
- workflow básico de GitHub Actions.

## Instalación en Windows

### Requisitos libres o gratuitos

- Python 3.11+
- Node.js 20+
- Git
- VS Code

### Backend

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/pip install -r backend/requirements.txt
backend/.venv/Scripts/python backend/app.py
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Instalación en Linux

### Requisitos libres o gratuitos

- Python 3.11+
- Node.js 20+
- Git
- VS Code o VSCodium

### Backend

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python backend/app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Modelos IA locales y gratuitos

Opciones recomendadas:

### Ollama

Ideal para equipos personales con terminal y ejecución local simple.

```bash
ollama pull codellama
ollama pull starcoder2
ollama pull phi3
```

Sugerencia de mapeo:

- Backend: `codellama`
- Frontend: `starcoder2`
- Infra: `phi3` o `llama3.2`

Integracion operativa en este repositorio:

1. Instala Ollama.
2. Ejecuta `ollama serve`.
3. Descarga los modelos que usa el workspace.
4. Configura estas variables de entorno antes de correr `main.py`.

Windows (PowerShell):

```powershell
$env:OPENAI_PROVIDER = "ollama"
$env:OPENAI_API_KEY = "ollama"
$env:OPENAI_BASE_URL = "http://localhost:11434/v1"
$env:OPENAI_MODEL = "llama3.2"
$env:AGENT_MODEL_CONFIG_FILE = "shared/agent-models.json"
python main.py --req "API local para biblioteca" --provider ollama --lang espanol
```

Linux (bash):

```bash
export OPENAI_PROVIDER="ollama"
export OPENAI_API_KEY="ollama"
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_MODEL="llama3.2"
export AGENT_MODEL_CONFIG_FILE="shared/agent-models.json"
python3 main.py --req "API local para biblioteca" --provider ollama --lang espanol
```

Con esta configuracion, el pipeline de `src/agents/team.py` ya no usa un unico modelo para todos los agentes: toma el modelo por rol desde `shared/agent-models.json`.

Mapeo actual del pipeline:

- Project Manager y Technical Lead: `phi3`
- Backend y QA y Security: `codellama`
- Frontend: `starcoder2`
- DevOps: `phi3`
- Documentacion: `phi3`

### GPT4All

Útil para equipos modestos y uso offline desde interfaz gráfica.

Pasos generales:

1. Instalar GPT4All.
2. Descargar un modelo de código o propósito general.
3. Asignarlo al rol que necesites documentando el nombre en `shared/agent-models.json`.

### CodeLlama y StarCoder

Pueden ejecutarse localmente a través de Ollama, LM Studio u otros runtimes compatibles.

## Scripts de automatizacion

En la raíz hay un `package.json` con comandos:

```json
{
    "dev:backend": "python backend/app.py",
    "dev:frontend": "npm --prefix frontend run dev -- --host 0.0.0.0",
    "dev:infra": "echo Docker deshabilitado en este entorno",
    "dev:all": "powershell -NoProfile -ExecutionPolicy Bypass -File infra/scripts/dev-all.ps1",
    "check:backend": "python -m py_compile backend/app.py backend/routes.py backend/shared_contracts.py",
    "build:frontend": "npm --prefix frontend run build"
}
```

## Ejemplos rapidos por sistema

### Windows

Arranque guiado:

```powershell
iniciar.bat
```

Arranque con salida detallada (verbose):

```powershell
iniciar.bat --verbose
```

Bootstrap directo:

```powershell
powershell -ExecutionPolicy Bypass -File infra/scripts/bootstrap-windows.ps1
```

Bootstrap sin ejecutar la app al final:

```powershell
powershell -ExecutionPolicy Bypass -File infra/scripts/bootstrap-windows.ps1 -NoRun
```

Modo no interactivo con requerimiento:

```powershell
$env:OPENAI_PROVIDER = "ollama"
$env:OPENAI_API_KEY = "ollama"
$env:OPENAI_BASE_URL = "http://localhost:11434/v1"
$env:OPENAI_MODEL = "llama3.2"
python main.py --provider ollama --lang espanol --req "API local para biblioteca comunitaria con catalogo, prestamos y devoluciones"
```

### Linux

Bootstrap con ejecucion:

```bash
bash infra/scripts/bootstrap-linux.sh
```

Solo validacion/instalacion (sin correr app):

```bash
bash infra/scripts/bootstrap-linux.sh --no-run
```

Modo no interactivo con requerimiento:

```bash
export OPENAI_PROVIDER="ollama"
export OPENAI_API_KEY="ollama"
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_MODEL="llama3.2"
python3 main.py --provider ollama --lang espanol --req "API local para biblioteca comunitaria con catalogo, prestamos y devoluciones"
```

## Uso equivalente en ambos entornos

1. Instalar dependencias de Python y frontend.
2. Levantar backend y frontend con tareas de VS Code (`dev:all`) o en terminal separada.
3. Levantar proveedor local de modelos (Ollama).
4. Ejecutar pipeline con `main.py` pasando `--req`.
5. Revisar resultados en la carpeta `project_runs/<slug>/<session_id>/output`.

## Estructura de salidas por proyecto

Cada ejecucion nueva crea una carpeta unica por proyecto y sesion:

```text
project_runs/
    <slug-del-proyecto>/
        <session_id>/
            session.json
            visual_flow.html
            output/
                01_plan_tecnico.md
                02_backend_code.md
                ...
```

En el menu completo tienes dos vistas de seguimiento:

1. Diagrama ASCII en terminal (opcion 3).
2. Diagrama visual minimalista/tech en pestana del navegador (opcion 6).

## Tabla rapida Windows vs Linux

| Tarea | Windows | Linux |
|---|---|---|
| Bootstrap completo | `iniciar.bat` o `powershell -ExecutionPolicy Bypass -File infra/scripts/bootstrap-windows.ps1` | `bash infra/scripts/bootstrap-linux.sh` |
| Solo instalar/verificar | `powershell -ExecutionPolicy Bypass -File infra/scripts/bootstrap-windows.ps1 -NoRun` | `bash infra/scripts/bootstrap-linux.sh --no-run` |
| Crear venv backend | `python -m venv backend/.venv` | `python3 -m venv backend/.venv` |
| Instalar req backend | `backend/.venv/Scripts/pip install -r backend/requirements.txt` | `backend/.venv/bin/pip install -r backend/requirements.txt` |
| Ejecutar backend | `backend/.venv/Scripts/python backend/app.py` | `backend/.venv/bin/python backend/app.py` |
| Ejecutar frontend | `cd frontend && npm install && npm run dev` | `cd frontend && npm install && npm run dev` |
| Variables de entorno Ollama | `$env:OPENAI_BASE_URL="http://localhost:11434/v1"` | `export OPENAI_BASE_URL="http://localhost:11434/v1"` |
| Pipeline directo | `python main.py --provider ollama --lang espanol --req "..."` | `python3 main.py --provider ollama --lang espanol --req "..."` |
| Script de arranque all-in-one | `infra/scripts/dev-all.ps1` | `infra/scripts/bootstrap-linux.sh` |

## CI/CD gratuito

El workflow `.github/workflows/ci.yml` ejecuta:

- validacion de sintaxis del backend,
- instalación del frontend,
- build del frontend.

Es una base gratuita suficiente para proyectos educativos o comunitarios en GitHub.

## Seguridad y privacidad para repositorio publico

Antes de abrir PR o publicar fork:

1. No subir secretos, tokens ni cookies.
2. No subir rutas personales del sistema local.
3. No subir salidas de ejecucion con metadatos locales (`project_runs/`, `output/`, `sessions/`, `logs/`).
4. Si detectas filtracion, rota credenciales y reporta por `SECURITY.md`.

Referencias:

- `LICENSE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`

## Impacto social

Este workspace busca democratizar el acceso a la programación y la IA local:

- permite practicar roles distintos sobre el mismo proyecto,
- reduce la barrera económica al evitar dependencias pagas,
- facilita la colaboración en un entorno visual conocido,
- ofrece una base clara para talleres, cursos y autoaprendizaje.

## Proyecto Python original

El sistema principal de este repositorio sigue disponible para generar entregables de ckrafte_table desde `main.py` y `src/`.

Ejecucion directa:

```powershell
python main.py --req "API REST para biblioteca local" --provider ollama --lang espanol
```

Si quieres operar completamente sin nube, configura Ollama u otro runtime local compatible y ajusta las variables del proveedor en tu entorno.