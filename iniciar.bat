@echo off
setlocal

title CKRAFTE_TABLE ^| Inicio rapido
color 0B
cls

echo +---------------------------------------------------------------+
echo ^|                 CKRAFTE_TABLE / INICIO RAPIDO                ^|
echo ^|       Preparacion resumida y arranque bajo tu confirmacion   ^|
echo +---------------------------------------------------------------+
echo.

cd /d "%~dp0"

set "NORUN="
set "VERBOSE="
set "ASKRUN=1"
set "RUNNOW="

if /I "%~1"=="--verbose" set "VERBOSE=-VerboseOutput"
if /I "%~1"=="--no-run" (
	set "NORUN=-NoRun"
	set "ASKRUN=0"
	set "RUNNOW=n"
)
if /I "%~1"=="--yes" (
	set "ASKRUN=0"
	set "RUNNOW=s"
)

if /I "%~2"=="--verbose" set "VERBOSE=-VerboseOutput"
if /I "%~2"=="--no-run" (
	set "NORUN=-NoRun"
	set "ASKRUN=0"
	set "RUNNOW=n"
)
if /I "%~2"=="--yes" (
	set "ASKRUN=0"
	set "RUNNOW=s"
)

if "%ASKRUN%"=="1" (
	set /p RUNNOW=Iniciar CKRAFTE_TABLE automaticamente al finalizar? [S/n]: 
)
if /I "%RUNNOW%"=="n" set "NORUN=-NoRun"

echo [CKRAFTE_TABLE] Preparando entorno...
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
