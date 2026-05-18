#!/usr/bin/env bash
# Roda os 3 casos de teste sugeridos pelo case e regenera as saidas
# em outputs/exemplos/. Em ambiente sem rede aberta para Meta, usa --demo.
#
# Uso:
#   ./scripts/rodar_casos_teste.sh           # modo demo (default)
#   USAR_REDE=1 ./scripts/rodar_casos_teste.sh   # producao real

set -euo pipefail

cd "$(dirname "$0")/.."

DEMO_FLAG="--demo"
if [[ "${USAR_REDE:-0}" == "1" ]]; then
  DEMO_FLAG=""
fi

OUTPUT_DIR="outputs/exemplos"
mkdir -p "$OUTPUT_DIR"

PY=${PYTHON:-python3}
RUN="PYTHONPATH=src $PY -m vaipri_ref buscar"

echo "==> Caso 1: dermatologia"
eval "$RUN @clinica.exemplo dermatologia $DEMO_FLAG --output $OUTPUT_DIR"

echo
echo "==> Caso 2: nutrologia"
eval "$RUN @nutrologo.teste nutrologia $DEMO_FLAG --output $OUTPUT_DIR"

echo
echo "==> Caso 3: ortopedia"
eval "$RUN @ortopedista.test ortopedia $DEMO_FLAG --output $OUTPUT_DIR"

echo
echo "==> Saidas em $OUTPUT_DIR/:"
ls -la "$OUTPUT_DIR/"
