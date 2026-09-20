#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create venv if it doesn't exist
if [ ! -f ".venv/bin/activate" ]; then
  echo "Criando ambiente virtual..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# Install/update dependencies
pip install -q -r requirements.txt

mkdir -p data

echo "Iniciando Chromecast Manager em http://localhost:${API_PORT:-8001}"
LOG_LEVEL=DEBUG exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${API_PORT:-8001}" \
  --reload \
  --reload-include '*.html' \
  --reload-include '*.js' \
  --reload-include '*.css'
