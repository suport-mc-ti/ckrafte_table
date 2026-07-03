@echo off
setlocal

title AGENTE-S ^| Inicio rapido
color 0B
cls

echo +---------------------------------------------------------------+
echo ^|                    AGENTE-S / INICIO RAPIDO                  ^|
echo ^|       Preparacion resumida y arranque bajo tu confirmacion   ^|
echo +---------------------------------------------------------------+
echo.

cd /d "%~dp0"

set "NORUN="
set "VERBOSE="

if /I "%~1"=="--verbose" set "VERBOSE=-VerboseOutput"

set /p RUNNOW=Iniciar AGENTE-S automaticamente al finalizar? [S/n]: 
if /I "%RUNNOW%"=="n" set "NORUN=-NoRun"

echo [AGENTE-S] Preparando entorno...
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "infra\scripts\bootstrap-windows.ps1" %NORUN% %VERBOSE%
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
