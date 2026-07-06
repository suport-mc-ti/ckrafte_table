# Contributing to ckrafte_table

Gracias por aportar.

## Como contribuir

1. Abre un issue para discutir el cambio si es grande.
2. Crea una rama desde `main`.
3. Mantiene los cambios pequenos y con contexto claro.
4. Incluye pruebas o validaciones manuales reproducibles.
5. Abre un Pull Request usando la plantilla.

## Configuracion local

```bash
git clone https://github.com/suport-mc-ti/ckrafte_table.git
cd ckrafte_table
python -m pip install -r requirements.txt
python -m pip install -e .
npm --prefix frontend install
```

## Validaciones minimas antes de PR

```bash
python -m py_compile backend/app.py backend/routes.py backend/shared_contracts.py
npm --prefix frontend run build
```

## Reglas de seguridad y privacidad

- No subir secretos, tokens, cookies o credenciales.
- No subir rutas locales personales (por ejemplo `C:\\Users\\<nombre>`).
- No subir archivos de `project_runs/`, `output/`, `sessions/` ni logs con datos del equipo local.
- Si detectas filtracion, rota credenciales y reporta por `SECURITY.md`.
