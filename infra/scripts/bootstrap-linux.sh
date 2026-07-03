#!/usr/bin/env bash
set -euo pipefail

NO_RUN="0"
if [[ "${1:-}" == "--no-run" ]]; then
	NO_RUN="1"
fi

echo "[AGENTE-S] Bootstrap Linux"

cd "$(dirname "$0")/../.."

echo "0) Verificando herramientas basicas..."
for cmd in python3 npm git; do
	if command -v "$cmd" >/dev/null 2>&1; then
		echo "   OK: $cmd"
	else
		echo "   FALTA: $cmd"
	fi
done

echo "1) Actualizando pip..."
python3 -m pip install --upgrade pip

echo "2) Instalando dependencias Python..."
python3 -m pip install -r requirements.txt
python3 -m pip install -e .

echo "3) Instalando dependencias Frontend..."
npm --prefix frontend install

echo "4) Verificando Ollama y modelos recomendados..."
if command -v ollama >/dev/null 2>&1; then
	echo "   OK: ollama encontrado"

	if curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
		echo "   OK: Ollama activo en http://localhost:11434"
	else
		echo "   AVISO: Ollama no responde en localhost:11434"
		echo "   Sugerencia: abre Ollama Desktop o ejecuta 'ollama serve'"
	fi

	list_output="$(ollama list 2>/dev/null || true)"
	for model in phi3 codellama starcoder2; do
		if echo "$list_output" | grep -q "$model"; then
			echo "   OK: modelo $model"
		else
			echo "   FALTA modelo: $model"
			echo "   Ejecuta: ollama pull $model"
		fi
	done
else
	echo "   AVISO: Ollama no esta instalado o no esta en PATH"
	echo "   Instala Ollama para usar el modo local de IA"
fi

echo "5) Configurando entorno local para Ollama..."
export OPENAI_PROVIDER="ollama"
export OPENAI_API_KEY="ollama"
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_MODEL="phi3"
export AGENT_MODEL_CONFIG_FILE="$(pwd)/shared/agent-models.json"
echo "   OK: entorno configurado para esta terminal"

echo
echo "Listo. Siguientes pasos:"
echo "- Ejecuta: agente-s-start"
echo "- O ejecuta: python3 main.py --provider ollama --lang espanol"

if [[ "$NO_RUN" == "0" ]]; then
	echo
	echo "[AGENTE-S] Arrancando herramienta automaticamente..."
	python3 main.py --provider ollama --lang espanol
fi
