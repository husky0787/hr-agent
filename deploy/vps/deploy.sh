#!/usr/bin/env bash
# Deploy hr-onboarding on the Zanbeel VPS (run on server or via CI SSH)
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/hr-onboarding}"
COMPOSE_FILE="${APP_DIR}/deploy/vps/docker-compose.yml"
SERVICE="${1:-all}"

cd "${APP_DIR}"

if [[ ! -f .env ]]; then
  echo "Missing ${APP_DIR}/.env — configure GPT, xAI and Jina credentials"
  exit 1
fi

docker network inspect zanbeel >/dev/null 2>&1 || docker network create zanbeel

git fetch origin "${DEPLOY_BRANCH:-main}"
git checkout "${DEPLOY_BRANCH:-main}"
git reset --hard "origin/${DEPLOY_BRANCH:-main}"

case "${SERVICE}" in
  all)
    docker compose -f "${COMPOSE_FILE}" up -d --build --remove-orphans
    ;;
  backend)
    docker compose -f "${COMPOSE_FILE}" up -d --build backend
    ;;
  frontend)
    docker compose -f "${COMPOSE_FILE}" up -d --build frontend
    ;;
  evals)
    bash "${APP_DIR}/deploy/vps/run-evals.sh" "${@:2}"
    ;;
  *)
    docker compose -f "${COMPOSE_FILE}" up -d --build "${SERVICE}"
    ;;
esac

# Evals consume external API credits; run only via the explicit `evals` action.

docker compose -f "${COMPOSE_FILE}" ps
