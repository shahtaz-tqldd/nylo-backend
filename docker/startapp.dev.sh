#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RESET_DB=0

if [[ "${1:-}" == "--reset-db" ]]; then
  RESET_DB=1
  shift
fi

if [[ "${RESET_DB}" == "1" ]]; then
  docker compose -f "${SCRIPT_DIR}/compose.dev.yml" down -v --remove-orphans
else
  docker compose -f "${SCRIPT_DIR}/compose.dev.yml" down --remove-orphans
fi

docker compose -f "${SCRIPT_DIR}/compose.dev.yml" up --build "$@"
