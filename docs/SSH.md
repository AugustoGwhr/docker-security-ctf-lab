# Acesso do notebook às VMs

Use duas VMs dedicadas: controle e prática. Substitua `IP_CONTROLE`, `IP_PRATICA` e o usuário administrativo inicial pelos valores reais. Nada neste pacote estabelece acesso remoto automaticamente.

## 1. Notebook Windows: chaves

Execute no **PowerShell do notebook**, com OpenSSH Client instalado:

```powershell
ssh -V
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
ssh-keygen -t ed25519 -a 64 -f "$env:USERPROFILE\.ssh\ctf_lab" -C "ctf-estudante"
ssh-keygen -t ed25519 -a 64 -f "$env:USERPROFILE\.ssh\ctf_admin" -C "ctf-operador"
```

Escolha passphrases. Não sobrescreva chaves que já usa. `ctf_lab` e `ctf_admin` são privadas e ficam no notebook; os arquivos `.pub` correspondentes podem ser instalados nas VMs. Linux/macOS: use `~/.ssh/ctf_lab` e `~/.ssh/ctf_admin` como caminhos, no terminal local.

Confira a impressão digital das chaves públicas localmente:

```powershell
ssh-keygen -lf "$env:USERPROFILE\.ssh\ctf_lab.pub"
ssh-keygen -lf "$env:USERPROFILE\.ssh\ctf_admin.pub"
```

Instale **a chave pública completa**, não apenas seu hash. Confirme também o fingerprint do host por um canal administrativo confiável antes de aceitar a primeira conexão.

## 2. Servidores: contas e chaves públicas

Pela sessão do administrador inicial, instale os pacotes conforme SETUP.md. Crie:

**VM CONTROLE, administrador:**

```bash
sudo adduser --disabled-password --gecos '' ctfctl
sudo adduser --disabled-password --gecos '' --shell /usr/sbin/nologin ctfview
sudo install -d -m 700 -o ctfctl -g ctfctl /home/ctfctl/.ssh
sudo install -d -m 700 -o ctfview -g ctfview /home/ctfview/.ssh
```

**VM PRÁTICA, administrador:**

```bash
sudo adduser --disabled-password --gecos '' ctf
sudo install -d -m 700 -o ctf -g ctf /home/ctf/.ssh
```

Transfira os `.pub` para `/tmp` com SCP usando seu acesso administrativo inicial. Exemplo no **NOTEBOOK/PowerShell**; `admin-inicial` precisa ser trocado:

```powershell
scp "$env:USERPROFILE\.ssh\ctf_admin.pub" admin-inicial@IP_CONTROLE:/tmp/ctf_admin.pub
scp "$env:USERPROFILE\.ssh\ctf_lab.pub" admin-inicial@IP_CONTROLE:/tmp/ctf_lab.pub
scp "$env:USERPROFILE\.ssh\ctf_lab.pub" admin-inicial@IP_PRATICA:/tmp/ctf_lab.pub
```

**VM CONTROLE, administrador:**

```bash
sudo install -m 600 -o ctfctl -g ctfctl /tmp/ctf_admin.pub /home/ctfctl/.ssh/authorized_keys
sudo install -m 600 -o ctfview -g ctfview /tmp/ctf_lab.pub /home/ctfview/.ssh/authorized_keys
```

**VM PRÁTICA, administrador:**

```bash
sudo install -m 600 -o ctf -g ctf /tmp/ctf_lab.pub /home/ctf/.ssh/authorized_keys
```

Esses comandos assumem contas novas, sem `authorized_keys` anterior. Se as contas já existem, acrescente a chave após revisar o arquivo; não sobrescreva acessos existentes. Não coloque `ctf` no grupo `sudo` nem no grupo `docker` rootful.

## 3. Configuração SSH do servidor

Mantenha a sessão administrativa atual aberta até testar uma segunda conexão por chave. Configure autenticação por chave e, após confirmar as chaves, desative senhas para estas contas. O usuário `ctfview` deve ter apenas acesso ao túnel do painel.

**VM CONTROLE, administrador:** crie `/etc/ssh/sshd_config.d/60-ctf-lab.conf`:

```text
Match User ctfctl
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PubkeyAuthentication yes
Match User ctfview
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PubkeyAuthentication yes
    AllowTcpForwarding local
    PermitOpen 127.0.0.1:8501
    PermitTTY no
    X11Forwarding no
    AllowAgentForwarding no
    ForceCommand /usr/sbin/nologin
Match all
```

`ssh -N` não pede shell, portanto o usuário de túnel funciona com nologin. O bloqueio de shell ajuda a impedir que a conta de prática consulte arquivos do controle.

**VM PRÁTICA, administrador:** crie o mesmo arquivo com:

```text
Match User ctf
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    PubkeyAuthentication yes
    X11Forwarding no
    AllowAgentForwarding no
Match all
```

**Em cada VM, administrador:**

```bash
sudo sshd -t
sudo systemctl reload ssh
sudo systemctl status ssh --no-pager
```

Ubuntu pode usar ativação por socket; confira também `systemctl status ssh.socket`. Configurações prévias e snippets cloud-init podem interferir. No controle, confira a configuração efetiva com `sudo sshd -T -C user=ctfview,host=localhost,addr=IP_DO_NOTEBOOK`, especialmente `permitopen`, `allowtcpforwarding` e autenticação.

## 4. Notebook: aliases

Edite `%USERPROFILE%\.ssh\config` no Windows (ou `~/.ssh/config` em Linux/macOS):

```sshconfig
Host ctf-control
    HostName IP_CONTROLE
    User ctfctl
    IdentityFile ~/.ssh/ctf_admin
    IdentitiesOnly yes
    ServerAliveInterval 30

Host ctf-panel
    HostName IP_CONTROLE
    User ctfview
    IdentityFile ~/.ssh/ctf_lab
    IdentitiesOnly yes
    ServerAliveInterval 30

Host ctf-practice
    HostName IP_PRATICA
    User ctf
    IdentityFile ~/.ssh/ctf_lab
    IdentitiesOnly yes
    ServerAliveInterval 30
```

O alias `ctf-control` é administrativo e fica somente com o operador. O estudante usa `ctf-panel` e `ctf-practice`.

**NOTEBOOK:**

```bash
ssh ctf-practice
# Em outro terminal, quando o painel estiver iniciado:
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8501:127.0.0.1:8501 ctf-panel
```

Abra `http://127.0.0.1:8501` no navegador do notebook. `127.0.0.1` antes da primeira porta é a interface do notebook; `127.0.0.1` depois é visto pela VM controle. Fechar o terminal encerra o túnel.

## 5. Arquivos e VS Code

**NOTEBOOK:**

```bash
scp arquivo.py ctf-practice:/home/ctf/
sftp ctf-practice
```

No SFTP, use `put arquivo.py`, `get arquivo.py` e `exit`. VS Code Remote SSH pode se conectar a `ctf-practice`; selecione o alias. Não habilite shell no usuário `ctfview` para usar VS Code.

## 6. Firewall

Na regra de entrada do provedor/cloud, permita TCP 22 somente do seu IP público autorizado `/32` (ou da rede/VPN administrada). Não crie regra pública para 8501, 8080, 2375, 2376 ou PostgreSQL.

Em **cada VM**, administrador, com sessão alternativa disponível e IP real definido:

```bash
sudo apt-get install -y ufw
CTF_NOTEBOOK_IP='SEU_IP_PUBLICO'
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from "$CTF_NOTEBOOK_IP" to any port 22 proto tcp
sudo ufw enable
sudo ufw status verbose
```

Se usa VPN/IAP, configure a origem adequada ao caminho real. O pacote não altera firewall ou SSH automaticamente. A etapa 1 depende de saída HTTPS para downloads. UFW não é uma garantia geral contra portas publicadas pelo Docker rootful; o isolamento inclui rootless, binds locais e firewall do provedor.

## 7. Diagnóstico

| Erro | Ação |
|---|---|
| `Permission denied (publickey)` | Confira usuário, `.pub` instalado, chave selecionada, owner e modos 700/600; use `ssh -v` |
| Timeout na porta 22 | Revise IP, firewall cloud, origem autorizada, estado da VM e serviço SSH |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Confirme o fingerprint da nova VM antes de atualizar known_hosts |
| `Address already in use` no notebook | Use porta local 18501 e mantenha destino 8501: `-L 127.0.0.1:18501:127.0.0.1:8501` |
| `administratively prohibited` | Confira `AllowTcpForwarding` e `PermitOpen` efetivos para `ctfview` |
| `Connection refused` após túnel | Confira `docker compose ps` no controle e o bind local 8501 |
| `Failed to connect to bus` | Entre por uma sessão SSH real do usuário; confira dbus-user-session e linger |

Resultado esperado: `ctf` tem shell na prática; `ctfview` cria o túnel, mas um pedido de shell recebe nologin; a UI funciona localmente no notebook.
