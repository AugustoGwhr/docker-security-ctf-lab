#!/usr/bin/env python3
"""PRÁTICA, administrador: transmite contexts privados ao daemon rootless.

Não extrai arquivos do tar no host, não interpola shell, não aceita comandos.
Os arquivos públicos ficam em practice/; o seed permanece com o administrador.
"""
import argparse
import io
import json
import os
import pwd
import stat
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ("files", "logs", "environment")


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def read_contexts(seed):
    contexts = {}
    expected = {"files/Dockerfile", "files/flag.txt", "logs/Dockerfile", "logs/flag.txt", "environment/Dockerfile"}
    if seed.stat().st_size > 1024 * 1024:
        raise ValueError("Bundle maior que o permitido.")
    with tarfile.open(seed, "r:gz") as tar:
        members = tar.getmembers()
        if {m.name for m in members} != expected or len(members) != len(expected):
            raise ValueError("Bundle não corresponde aos três exercícios desta etapa.")
        if any(not m.isfile() or m.size > 8192 for m in members):
            raise ValueError("Bundle contém arquivo inválido ou excessivamente grande.")
        for service in SERVICES:
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w") as target:
                for member in members:
                    if member.name.startswith(service + "/"):
                        data = tar.extractfile(member).read()
                        info = tarfile.TarInfo(member.name.split("/", 1)[1])
                        info.size = len(data)
                        info.mode = 0o444
                        target.addfile(info, io.BytesIO(data))
            contexts[service] = stream.getvalue()
    return contexts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True, help="Usuário dono do daemon rootless, normalmente ctf")
    parser.add_argument("--seed", type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Execute como administrador com sudo, usando apenas o bundle gerado na VM de controle.")
    account = pwd.getpwnam(args.user)
    if account.pw_uid == 0:
        raise SystemExit("O daemon deve pertencer a usuário sem privilégios.")
    path = Path(f"/run/user/{account.pw_uid}/docker.sock")
    if not path.exists() or not stat.S_ISSOCK(path.stat().st_mode) or path.stat().st_uid != account.pw_uid:
        raise SystemExit("Socket rootless do usuário não encontrado.")
    seed = args.seed.resolve()
    if seed.stat().st_uid != 0 or seed.stat().st_mode & 0o077:
        raise SystemExit("O seed deve pertencer a root e ter permissão 0600.")
    contexts = read_contexts(seed)
    docker = ["docker", "--host", "unix://" + str(path)]
    info = json.loads(run(docker + ["info", "--format", "{{json .}}"], capture_output=True, text=True).stdout)
    if not any("rootless" in opt for opt in info.get("SecurityOptions", [])):
        raise SystemExit("Daemon não está em modo rootless.")
    if info.get("CgroupVersion") != "2" or info.get("CgroupDriver") != "systemd":
        raise SystemExit("Limites requerem cgroups v2/systemd. Consulte docs/SETUP.md antes de continuar.")
    delegated = Path(f"/sys/fs/cgroup/user.slice/user-{account.pw_uid}.slice/user@{account.pw_uid}.service/cgroup.controllers").read_text().split()
    if not {"cpu", "memory", "pids"} <= set(delegated):
        raise SystemExit("Controllers CPU, memory e pids não foram todos delegados. Consulte docs/SETUP.md.")
    for service in SERVICES:
        run(docker + ["build", "--tag", f"docker-ctf/intro-{service}:session", "-"], input=contexts[service], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"Imagem provisionada: {service}")
    run(docker + ["compose", "-p", "docker-ctf-practice", "-f", str(ROOT / "practice/compose.yaml"), "up", "-d", "--pull", "never"])
    print("Prática iniciada. O seed deve permanecer em /root com permissão 0600; não o entregue ao estudante.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Provisionamento interrompido ({type(exc).__name__}); revise a configuração sem expor o seed.")
