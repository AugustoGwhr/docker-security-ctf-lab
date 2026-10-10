#!/usr/bin/env bash
# ADMINISTRADOR de uma VM NOVA e dedicada. Não adiciona usuários ao grupo docker.
set -euo pipefail
if [[ ${1:-} != --dedicated-vm || $EUID -ne 0 ]]; then
  echo 'Uso: sudo bash scripts/install_docker_ubuntu.sh --dedicated-vm' >&2
  exit 1
fi
. /etc/os-release
if [[ $ID != ubuntu || $VERSION_ID != 24.04 ]]; then
  echo 'Este script foi escrito para Ubuntu 24.04. Consulte a documentação para outras versões.' >&2
  exit 1
fi
if [[ -S /var/run/docker.sock ]] && command -v docker >/dev/null; then
  if [[ -n $(docker --host unix:///var/run/docker.sock ps -aq) ]]; then
    echo 'Há containers no daemon rootful. Use uma VM nova; o script não vai interrompê-los.' >&2
    exit 1
  fi
fi
for package in docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc; do
  if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$'; then
    echo "Pacote conflitante: $package. Revise manualmente; nada será removido automaticamente." >&2
    exit 1
  fi
done
apt-get update
apt-get install -y ca-certificates curl uidmap dbus-user-session slirp4netns openssh-server python3 unzip
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras
systemctl disable --now docker.service docker.socket
echo 'Pacotes instalados; daemon rootful desativado nesta VM dedicada.'
echo 'Execute a preparação do usuário e enable_rootless.sh conforme docs/SETUP.md.'
