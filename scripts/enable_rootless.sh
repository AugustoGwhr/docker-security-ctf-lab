#!/usr/bin/env bash
# VM DE CONTROLE como ctfctl, ou VM DE PRÁTICA como ctf, por sessão SSH real.
set -euo pipefail
if [[ $EUID -eq 0 ]]; then
  echo 'Use uma sessão SSH do usuário sem privilégios, não sudo su.' >&2
  exit 1
fi
if [[ -z ${XDG_RUNTIME_DIR:-} || ! -d $XDG_RUNTIME_DIR ]]; then
  echo 'Sessão systemd do usuário ausente. Reconecte por SSH e confira dbus-user-session.' >&2
  exit 1
fi
if ! awk -F: -v name="$(id -un)" '$1 == name && $3 >= 65536 { found=1 } END { exit !found }' /etc/subuid; then
  echo 'Faltam pelo menos 65536 subuids. Consulte docs/SETUP.md.' >&2
  exit 1
fi
if ! awk -F: -v name="$(id -un)" '$1 == name && $3 >= 65536 { found=1 } END { exit !found }' /etc/subgid; then
  echo 'Faltam pelo menos 65536 subgids. Consulte docs/SETUP.md.' >&2
  exit 1
fi
dockerd-rootless-setuptool.sh install
docker context use rootless
systemctl --user enable --now docker.service
docker info
echo 'Confirme rootless nas Security Options e Cgroup Driver: systemd / Cgroup Version: 2.'
