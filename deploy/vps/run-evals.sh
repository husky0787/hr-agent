#!/usr/bin/env bash
# Manually run golden evals on the VPS; no public admin page or database required.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/hr-onboarding}"
COMPOSE_FILE="${APP_DIR}/docker-compose.yml"

cd "${APP_DIR}"
mkdir -p "${APP_DIR}/evals/results"

echo "==== Running golden evals ===="
docker compose -f "${COMPOSE_FILE}" --profile evals run --rm --build evals "$@"
