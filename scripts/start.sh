#!/usr/bin/env bash
# CONTROLE, ctfctl
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if ! docker info --format '{{json .SecurityOptions}}' | grep -q rootless; then
  echo 'Selecione um daemon rootless antes de iniciar.' >&2
  exit 1
fi
if [[ $(docker info --format '{{.CgroupVersion}}') != 2 || $(docker info --format '{{.CgroupDriver}}') != systemd ]]; then
  echo 'cgroups v2 e driver systemd são necessários para aplicar limites.' >&2
  exit 1
fi
ctf_controllers=$(cat "/sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service/cgroup.controllers")
for ctf_controller in cpu memory pids; do
  if ! grep -qw "$ctf_controller" <<< "$ctf_controllers"; then
    echo "Controller não delegado: $ctf_controller. Consulte docs/SETUP.md." >&2
    exit 1
  fi
done
python3 scripts/init_lab.py
docker compose -p docker-ctf-control config --quiet
docker compose -p docker-ctf-control up -d --build --wait --wait-timeout 180
docker compose -p docker-ctf-control ps
echo 'Painel: http://127.0.0.1:8501, acessível pelo túnel SSH.'
