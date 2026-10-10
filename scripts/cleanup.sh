#!/usr/bin/env bash
# Interrompe somente o projeto indicado; nunca executa docker system prune.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
case ${1:-} in
  control)
    if [[ ${2:-} == --erase-progress ]]; then
      docker compose -p docker-ctf-control down --volumes
      echo 'Volume de progresso desta implantação removido. Segredos e seed mantidos.'
    elif [[ $# == 1 ]]; then
      docker compose -p docker-ctf-control down
      echo 'Painel interrompido; progresso preservado.'
    else
      echo 'Uso: cleanup.sh control [--erase-progress]' >&2; exit 1
    fi ;;
  practice)
    [[ $# == 1 ]] || { echo 'Uso: cleanup.sh practice' >&2; exit 1; }
    docker compose -p docker-ctf-practice -f practice/compose.yaml down
    echo 'Exercícios interrompidos; imagens de treinamento preservadas.' ;;
  *) echo 'Uso: cleanup.sh control [--erase-progress] | practice' >&2; exit 1 ;;
esac
