[CmdletBinding()]
param(
	[switch]$NoRun
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
Write-Host "|   Instalacion, verificacion y arranque automatico de la app     |" -ForegroundColor Cyan
Write-Host "+------------------------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

Set-Location -Path (Resolve-Path "$PSScriptRoot\..\..").Path

function Test-Command($name) {
	return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

Write-Host "0) Verificando herramientas basicas..." -ForegroundColor Yellow
foreach ($cmd in @("python", "npm", "git")) {
	if (Test-Command $cmd) {
		Write-Host "   OK: $cmd" -ForegroundColor Green
	} else {
		Write-Host "   FALTA: $cmd" -ForegroundColor Red
	}
}

Write-Host "1) Actualizando pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

Write-Host "2) Instalando dependencias Python..." -ForegroundColor Yellow
python -m pip install -r requirements.txt
python -m pip install -e .

Write-Host "3) Instalando dependencias Frontend..." -ForegroundColor Yellow
npm --prefix frontend install

Write-Host "4) Verificando Ollama y modelos recomendados..." -ForegroundColor Yellow
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

Write-Host "5) Configurando entorno local para Ollama..." -ForegroundColor Yellow
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

if (-not $NoRun) {
	Write-Host "" 
	Write-Host "[AGENTE-S] Arrancando herramienta automaticamente..." -ForegroundColor Cyan
	python main.py --provider ollama --lang espanol
}
