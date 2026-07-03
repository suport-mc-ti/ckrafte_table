@echo off
setlocal

title AGENTE-S ^| Inicio rapido
color 0B
cls

echo +---------------------------------------------------------------+
echo ^|                    AGENTE-S / INICIO RAPIDO                  ^|
echo ^|          Un comando para preparar y arrancar la herramienta  ^|
echo +---------------------------------------------------------------+
echo.

cd /d "%~dp0"

echo [AGENTE-S] Preparando entorno y arrancando...
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "infra\scripts\bootstrap-windows.ps1"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
	color 0C
	echo.
 echo Ocurrio un problema durante el arranque. Codigo: %EXITCODE%
) else (
	color 0A
	echo.
	echo Proceso completado correctamente.
)

pause
endlocal & exit /b %EXITCODE%
