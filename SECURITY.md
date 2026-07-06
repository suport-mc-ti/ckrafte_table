# Security Policy

## Supported Versions

Se da soporte de seguridad activo a la rama `main`.

## Reporting a Vulnerability

No abras vulnerabilidades en issues publicos.

1. Reporta por email a: security@ckrafte.local
2. Incluye pasos de reproduccion y alcance.
3. Si hay credenciales expuestas, rota primero y luego reporta.

Objetivo de respuesta inicial: 72 horas.

## Hardening recomendado para forks

- Configura secretos en GitHub Actions Secrets, no en archivos.
- Usa modelos locales o claves con permisos minimos.
- Revisa PRs por filtraciones de rutas personales y tokens.
- Mantiene `.env` fuera de git y comparte solo `.env.example` sin valores reales.
