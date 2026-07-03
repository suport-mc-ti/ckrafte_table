[CmdletBinding()]
param(
	[switch]$NoRun,
	[switch]$VerboseOutput
)

$ErrorActionPreference = "Stop"

try {
	$Host.UI.RawUI.WindowTitle = "AGENTE-S | Bootstrap Windows"
}
catch {
	# Ignore if host does not support window title
}

Clear-Host
Write-Host "+------------------------------------------------------------------+" -ForegroundColor Cyan
Write-Host "|                  AGENTE-S / BOOTSTRAP WINDOWS                   |" -ForegroundColor Cyan
Write-Host "|   Instalacion y verificacion (modo resumido por defecto)        |" -ForegroundColor Cyan
Write-Host "+------------------------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

Set-Location -Path (Resolve-Path "$PSScriptRoot\..\..").Path

$logDir = Join-Path (Resolve-Path ".").Path "logs\bootstrap"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir ("bootstrap_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")

function Invoke-Cmd {
	param(
		[string]$Label,
		[string]$FilePath,
		[string[]]$Arguments
	)

	Write-Host "   - $Label..." -ForegroundColor Yellow
	# En PowerShell 5.1, warnings de stderr pueden convertirse en NativeCommandError.
	# Usamos Start-Process con redireccion para evaluar fallo solo por ExitCode.
	$resolvedPath = $FilePath
	$cmdCandidates = Get-Command $FilePath -All -ErrorAction SilentlyContinue
	if ($cmdCandidates) {
		$nativeCandidate = $cmdCandidates |
			Where-Object { $_.Source -match "\.(exe|cmd|bat)$" } |
			Select-Object -First 1
		if (-not $nativeCandidate) {
			$nativeCandidate = $cmdCandidates | Select-Object -First 1
		}
		if ($nativeCandidate -and $nativeCandidate.Source) {
			$resolvedPath = $nativeCandidate.Source
		}
	}

	$stdoutFile = Join-Path $env:TEMP ("agente_s_bootstrap_stdout_" + [guid]::NewGuid().ToString() + ".log")
	$stderrFile = Join-Path $env:TEMP ("agente_s_bootstrap_stderr_" + [guid]::NewGuid().ToString() + ".log")

	try {
		$process = Start-Process -FilePath $resolvedPath -ArgumentList $Arguments -NoNewWindow -Wait -PassThru `
			-RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile

		$stdoutText = if (Test-Path $stdoutFile) { Get-Content -Path $stdoutFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue } else { "" }
		$stderrText = if (Test-Path $stderrFile) { Get-Content -Path $stderrFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue } else { "" }

		if ($VerboseOutput) {
			if ($stdoutText) { Write-Host $stdoutText.TrimEnd() }
			if ($stderrText) { Write-Host $stderrText.TrimEnd() -ForegroundColor Yellow }
		}
		else {
			"`n### $Label`n$resolvedPath $($Arguments -join ' ')" | Out-File -FilePath $logFile -Append -Encoding utf8
			if ($stdoutText) { $stdoutText | Out-File -FilePath $logFile -Append -Encoding utf8 }
			if ($stderrText) { $stderrText | Out-File -FilePath $logFile -Append -Encoding utf8 }
		}

		if ($process.ExitCode -ne 0) {
			throw "Fallo en '$Label' (codigo $($process.ExitCode))."
		}
	}
	finally {
		Remove-Item -Path $stdoutFile -ErrorAction SilentlyContinue
		Remove-Item -Path $stderrFile -ErrorAction SilentlyContinue
	}

	Write-Host "     OK" -ForegroundColor Green
}

function Test-Command($name) {
	return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

Write-Host "0) Verificando herramientas basicas..." -ForegroundColor Yellow
$missing = @()
foreach ($cmd in @("python", "npm", "git")) {
	if (Test-Command $cmd) {
		Write-Host "   OK: $cmd" -ForegroundColor Green
	} else {
		Write-Host "   FALTA: $cmd" -ForegroundColor Red
		$missing += $cmd
	}
}
if ($missing.Count -gt 0) {
	throw "Faltan herramientas basicas: $($missing -join ', ')"
}

Write-Host "1) Preparando dependencias..." -ForegroundColor Yellow
Invoke-Cmd -Label "Actualizar pip" -FilePath "python" -Arguments @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Cmd -Label "Instalar dependencias Python" -FilePath "python" -Arguments @("-m", "pip", "install", "-r", "requirements.txt")
Invoke-Cmd -Label "Instalar paquete editable" -FilePath "python" -Arguments @("-m", "pip", "install", "-e", ".")
Invoke-Cmd -Label "Instalar dependencias Frontend" -FilePath "npm" -Arguments @("--prefix", "frontend", "install")

Write-Host "2) Verificando Ollama y modelos recomendados..." -ForegroundColor Yellow
if (Test-Command "ollama") {
	Write-Host "   OK: ollama encontrado" -ForegroundColor Green

	try {
		$null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2
		Write-Host "   OK: Ollama activo en http://localhost:11434" -ForegroundColor Green
	}
	catch {
		Write-Host "   AVISO: Ollama no responde en localhost:11434" -ForegroundColor Yellow
		Write-Host "   Sugerencia: abre Ollama Desktop o ejecuta 'ollama serve'" -ForegroundColor Yellow
	}

	$listOutput = (ollama list | Out-String)
	$requiredModels = @("phi3", "codellama", "starcoder2")
	foreach ($model in $requiredModels) {
		if ($listOutput -match [regex]::Escape($model)) {
			Write-Host "   OK: modelo $model" -ForegroundColor Green
		}
		else {
			Write-Host "   FALTA modelo: $model" -ForegroundColor Yellow
			Write-Host "   Ejecuta: ollama pull $model" -ForegroundColor Yellow
		}
	}
}
else {
	Write-Host "   AVISO: Ollama no esta instalado o no esta en PATH" -ForegroundColor Yellow
	Write-Host "   Instala Ollama para usar el modo local de IA" -ForegroundColor Yellow
}

Write-Host "3) Configurando entorno local para Ollama..." -ForegroundColor Yellow
$env:OPENAI_PROVIDER = "ollama"
$env:OPENAI_API_KEY = "ollama"
$env:OPENAI_BASE_URL = "http://localhost:11434/v1"
$env:OPENAI_MODEL = "phi3"
$env:AGENT_MODEL_CONFIG_FILE = (Resolve-Path "shared/agent-models.json").Path
Write-Host "   OK: entorno configurado para esta terminal" -ForegroundColor Green

Write-Host "" 
Write-Host "Listo. Siguientes pasos:" -ForegroundColor Green
Write-Host "- Ejecuta: agente-s-start" -ForegroundColor Green
Write-Host "- O ejecuta: python main.py --provider ollama --lang espanol" -ForegroundColor Green
if (-not $VerboseOutput) {
	Write-Host "- Log detallado: $logFile" -ForegroundColor DarkGray
}

if (-not $NoRun) {
	Write-Host "" 
	Write-Host "[AGENTE-S] Arrancando herramienta automaticamente..." -ForegroundColor Cyan
	python main.py --provider ollama --lang espanol
}
