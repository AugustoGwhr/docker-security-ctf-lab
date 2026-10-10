# Backup e recuperação

O conjunto de recuperação inclui o backup SQLite, `.env`, `.private` e `.delivery`. O seed deve corresponder aos hashes usados pelo banco. Proteja o conjunto como material administrativo. Não o versione nem envie ao estudante.

## Exportar

**CONTROLE, ctfctl, pasta do projeto:**

```bash
mkdir -p backups
chmod 700 backups
docker compose -p docker-ctf-control exec -T api python3 -m backend.admin backup /data/backup.sqlite3
docker compose -p docker-ctf-control cp api:/data/backup.sqlite3 backups/lab.sqlite3
chmod 600 backups/lab.sqlite3
umask 077
tar -czf backups/recovery.tar.gz .env .private .delivery backups/lab.sqlite3
```

Copie `backups/recovery.tar.gz` a um destino seguro do operador. A API usa a função de backup SQLite, que produz uma cópia consistente mesmo com WAL. Não faça apenas cópia bruta de `lab.sqlite3` enquanto estiver em uso.

## Restaurar em implantação nova

Prepare outra VM controle conforme SETUP.md. Extraia a mesma versão do projeto. Antes de executar init_lab.py, restaure o arquivo de recuperação na raiz do projeto. Use somente arquivo seu, confiável, num diretório privado do operador. Confirme `.private` e `.delivery` com modo 0700, `.env` e o backup 0600.

O backup 0600 do host não é legível pelo UID remapeado 10001 do container rootless. Prepare uma **cópia** de leitura dentro de um diretório privado do operador. **NOVO CONTROLE, ctfctl:**

```bash
mkdir -p backups/restore-input
chmod 700 backups/restore-input
cp backups/lab.sqlite3 backups/restore-input/lab.sqlite3
chmod 644 backups/restore-input/lab.sqlite3
# Recuperação já extraída e segredos originais presentes:
docker compose -p docker-ctf-control build
# Cria o volume com a propriedade definida na imagem e restaura numa execução pontual.
docker compose -p docker-ctf-control run --rm --no-deps -v "$PWD/backups/restore-input/lab.sqlite3:/restore/lab.sqlite3:ro" api python3 -c 'import sqlite3; src=sqlite3.connect("/restore/lab.sqlite3"); dst=sqlite3.connect("/data/lab.sqlite3"); src.backup(dst); dst.close(); src.close()'
bash scripts/start.sh
python3 scripts/check_runtime.py control
# Depois de confirmar a restauração:
rm backups/restore-input/lab.sqlite3
```

O diretório pai 0700 protege a cópia no host; o bind de arquivo permite ao processo do container ler o backup. Não restaure sobre um banco em uso; pare o painel antes de recuperar uma implantação existente.

Na prática, reexecute o provisionamento com o mesmo seed administrativo. Se mudar o seed, use outra implantação e banco novos. A inicialização recusa substituir silenciosamente segredos; o backend recusa abrir um banco com hashes de uma sessão diferente.
