#!/usr/bin/env python3
"""Teste de implantação a executar no servidor, depois de iniciar os serviços."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=["control", "practice"])
    args = parser.parse_args()
    info = json.loads(docker("info", "--format", "{{json .}}"))
    assert any("rootless" in x for x in info["SecurityOptions"]), "Docker não está rootless"
    assert info["CgroupVersion"] == "2" and info["CgroupDriver"] == "systemd", "Limites sem cgroup v2/systemd"
    project = "docker-ctf-" + args.role
    ids = docker("ps", "-aq", "--filter", "label=com.docker.compose.project=" + project).split()
    assert len(ids) == (2 if args.role == "control" else 3), "Número de containers inesperado"
    for container in json.loads(docker("inspect", *ids)):
        conf = container["HostConfig"]
        assert container["State"]["Running"], "Container parado"
        assert not conf["Privileged"] and conf["ReadonlyRootfs"], "Container sem hardening esperado"
        assert container["Config"]["User"] == "10001:10001", "Usuário inesperado"
        assert "ALL" in (conf["CapDrop"] or []), "Capabilities não removidas"
        assert any("no-new-privileges" in opt for opt in conf["SecurityOpt"]), "no-new-privileges ausente"
        assert conf["Memory"] > 0 and conf["NanoCpus"] > 0 and conf["PidsLimit"] > 0, "Limite ausente"
        actual_memory = docker("exec", container["Id"], "cat", "/sys/fs/cgroup/memory.max").strip()
        actual_pids = docker("exec", container["Id"], "cat", "/sys/fs/cgroup/pids.max").strip()
        cpu_quota, cpu_period = docker("exec", container["Id"], "cat", "/sys/fs/cgroup/cpu.max").split()
        assert actual_memory == str(conf["Memory"]), "Limite de memória não aplicado no cgroup"
        assert actual_pids == str(conf["PidsLimit"]), "Limite de processos não aplicado no cgroup"
        assert cpu_quota != "max" and abs(int(cpu_quota) / int(cpu_period) - conf["NanoCpus"] / 1e9) < 0.01, "Limite de CPU não aplicado no cgroup"
        assert all("docker.sock" not in mount["Source"] for mount in container["Mounts"]), "Socket montado"
        if args.role == "practice":
            assert conf["NetworkMode"] == "none" and not conf["PortBindings"], "Prática com rede ou portas"
        else:
            service = container["Config"]["Labels"]["com.docker.compose.service"]
            assert container["State"]["Health"]["Status"] == "healthy", "Healthcheck falhou"
            if service == "api":
                assert not conf["PortBindings"], "API publicada"
            else:
                bindings = conf["PortBindings"]["8501/tcp"]
                assert all(b["HostIp"] == "127.0.0.1" for b in bindings), "UI exposta externamente"
    print("Inspeção de runtime OK: estado, hardening, isolamento, sockets e limites lidos dos cgroups.")
    print("Este teste não executa carga de estresse nem valida telemetria Falcon.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, subprocess.CalledProcessError, KeyError) as exc:
        raise SystemExit(f"Verificação falhou: {exc}")
