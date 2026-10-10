#!/usr/bin/env bash
# PRÁTICA, ctf. Recria somente o serviço pedido, mantendo flag e progresso.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
case ${1:-} in
  files|logs|environment) service=$1 ;;
  *) echo 'Uso: bash scripts/reset.sh files|logs|environment' >&2; exit 1 ;;
esac
docker compose -p docker-ctf-practice -f practice/compose.yaml up -d --no-deps --force-recreate --pull never "$service"
echo 'Exercício recriado; os outros serviços e o progresso foram preservados.'
