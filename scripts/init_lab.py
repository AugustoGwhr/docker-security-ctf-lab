#!/usr/bin/env python3
"""CONTROLE: cria segredos e seed do laboratório; não imprime flags."""
import argparse
import hashlib
import io
import json
import os
import secrets
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.catalog import ACTIVE_IDS


def private_write(path, data, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "w") as output:
        output.write(data)
    path.chmod(mode)


def seed_members(flags):
    mapping = {"files": "n1-arquivos", "logs": "n1-logs", "environment": "n1-ambiente"}
    common = 'FROM alpine:3.22\nUSER 10001:10001\n'
    for service, cid in mapping.items():
        if service == "files":
            dockerfile = common + 'COPY flag.txt /challenge/flag\nCMD ["sleep", "86400"]\n'
        elif service == "logs":
            dockerfile = common + 'COPY flag.txt /run/ctf/flag\nCMD ["/bin/sh", "-c", "cat /run/ctf/flag; exec sleep 86400"]\n'
        else:
            dockerfile = common + f'ENV CTF_TRAINING_FLAG={flags[cid]}\nCMD ["sleep", "86400"]\n'
        yield service + "/Dockerfile", dockerfile.encode()
        if service != "environment":
            yield service + "/flag.txt", (flags[cid] + "\n").encode()


def initialize(base):
    base = Path(base).resolve()
    if any((base / directory).is_symlink() for directory in (".private", ".delivery")):
        raise ValueError("Diretório privado não pode ser um symlink.")
    required = [base / ".env", base / ".private/api_token", base / ".private/flag_hashes.json", base / ".delivery/practice-seed.tar.gz"]
    if any(x.exists() for x in required):
        if not all(x.is_file() and not x.is_symlink() for x in required):
            raise ValueError("Inicialização parcial ou symlink encontrado. Não sobrescreva os segredos; restaure o conjunto ou use outro diretório.")
        hashes = json.loads(required[2].read_text())
        if set(hashes) != ACTIVE_IDS:
            raise ValueError("Configuração existente incompatível.")
        print("Inicialização já realizada; segredos e flags preservados.")
        return False
    base.mkdir(parents=True, exist_ok=True)
    for directory in (base / ".private", base / ".delivery"):
        if directory.is_symlink():
            raise ValueError("Diretório privado não pode ser um symlink.")
        directory.mkdir(mode=0o700, exist_ok=True)
        directory.chmod(0o700)
    flags = {cid: f'CTF{{{cid.replace("-", "_")}_{secrets.token_hex(16)}}}' for cid in sorted(ACTIVE_IDS)}
    # Arquivos de secret precisam ser legíveis pelo UID do container. O diretório
    # pai 0700 impede outros usuários do HOST de acessar esses caminhos.
    private_write(required[1], secrets.token_urlsafe(48) + "\n", 0o644)
    private_write(required[2], json.dumps({cid: hashlib.sha256(flag.encode()).hexdigest() for cid, flag in flags.items()}, indent=2) + "\n", 0o644)
    private_write(required[0], "UI_PORT=8501\nSTREAMLIT_COOKIE_SECRET=" + secrets.token_urlsafe(48) + "\n")
    fd = os.open(required[3], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as output, tarfile.open(fileobj=output, mode="w:gz") as tar:
        for name, data in seed_members(flags):
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o444
            tar.addfile(member, io.BytesIO(data))
    print("Configuração criada. Bundle privado: .delivery/practice-seed.tar.gz")
    print("Transfira o bundle ao administrador da VM de prática; não publique nem versione esse arquivo.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        initialize(args.base)
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc))
