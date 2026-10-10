# Preparação das VMs e inicialização

## Pré-requisitos

Use duas VMs novas e dedicadas, Ubuntu 24.04 LTS, usuário administrativo inicial com sudo, saída HTTPS e regras de entrada restritas ao SSH. Consulte SSH.md para criar contas e chaves. Execute comandos administrativos com o usuário inicial do provedor; `ctfctl` e `ctf` não precisam de sudo.

Se a sua VM já executa PostgreSQL ou outro projeto, use VMs novas para este laboratório. O instalador desativa o daemon rootful numa VM dedicada; não deve ser aplicado a um servidor compartilhado.

## 1. Transferir o pacote público

**NOTEBOOK:** envie o ZIP a cada administrador inicial com SCP. Nas VMs, extraia o projeto. Exemplo **SERVIDOR, administrador**, após upload:

```bash
unzip docker-security-ctf-lab-etapa1.zip
cd docker-security-ctf-lab
sudo bash scripts/install_docker_ubuntu.sh --dedicated-vm
```

O nome do ZIP entregue é `docker-security-ctf-lab-etapa1.zip`. O script prepara o repositório APT oficial do Docker, instala Engine/CLI/Buildx/Compose/rootless extras e pré-requisitos. Recusa versão diferente de Ubuntu 24.04, pacotes conflitantes ou containers em daemon rootful existente. Não remove pacotes ou dados de outros projetos.

## 2. Usuários e recursos rootless

Crie as contas e instale as chaves conforme SSH.md. Então:

**CONTROLE, administrador:**

```bash
sudo loginctl enable-linger ctfctl
sudo install -d -m 750 -o ctfctl -g ctfctl /home/ctfctl/docker-security-ctf-lab
sudo cp -a . /home/ctfctl/docker-security-ctf-lab/
sudo chown -R ctfctl:ctfctl /home/ctfctl/docker-security-ctf-lab
```

**PRÁTICA, administrador:**

```bash
sudo loginctl enable-linger ctf
sudo install -d -m 750 -o ctf -g ctf /home/ctf/docker-security-ctf-lab
sudo cp -a . /home/ctf/docker-security-ctf-lab/
sudo chown -R ctf:ctf /home/ctf/docker-security-ctf-lab
```

Esses comandos pressupõem que o diretório atual é a extração pública recém-criada e que os destinos são novos. Nunca copie `.private`/`.delivery` para a conta do estudante. Em contas existentes, revise destino e propriedade antes de usar `cp`/`chown`.

O adduser normalmente aloca faixas subordinadas. Confira no **SERVIDOR, administrador**, trocando o nome conforme a VM:

```bash
grep '^ctf:' /etc/subuid /etc/subgid
```

É necessária uma faixa de pelo menos 65536 IDs em cada arquivo, sem sobreposição com outros usuários. Se estiver ausente, aloque uma faixa livre usando `usermod --add-subuids INICIO-FIM --add-subgids INICIO-FIM ctf`; não reutilize números de um exemplo sem conferir o inventário da VM.

### Delegar cgroups

Os limites rootless precisam de cgroups v2, systemd e controllers delegados. Em **ambas as VMs, administrador**, prepare:

```bash
sudo mkdir -p /etc/systemd/system/user@.service.d
sudo tee /etc/systemd/system/user@.service.d/delegate.conf >/dev/null <<'EOF'
[Service]
Delegate=cpu cpuset io memory pids
EOF
sudo systemctl daemon-reload
```

Em uma VM nova, reinicie antes de iniciar o rootless para aplicar a delegação aos user managers já abertos. Preserve seu meio de reconexão: `sudo reboot`. Após voltar, entre diretamente por SSH como `ctfctl`/`ctf`.

## 3. Habilitar Docker rootless

**NOTEBOOK:**

```bash
ssh ctf-control
```

**CONTROLE, ctfctl:**

```bash
cd ~/docker-security-ctf-lab
bash scripts/enable_rootless.sh
```

Faça o equivalente pela conexão `ssh ctf-practice`, como **ctf**, na VM de prática. Não use sudo nesses comandos. Confira rootless nas Security Options, Cgroup Driver systemd e Cgroup Version 2.

Na **sessão do usuário em cada VM:**

```bash
cat "/sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service/cgroup.controllers"
docker info
docker compose version
docker buildx version
```

A lista precisa conter `cpu`, `memory` e `pids`. No Ubuntu 24.04, se AppArmor bloquear user namespaces, siga a seção específica da documentação oficial de troubleshooting rootless. Não desative AppArmor globalmente nem desabilite restrições do kernel para contornar o erro. O pacote APT oficial inclui a integração necessária nas configurações suportadas; confira sua instalação e logs.

## 4. Inicializar o controle

**CONTROLE, ctfctl:**

```bash
cd ~/docker-security-ctf-lab
python3 scripts/init_lab.py
bash scripts/start.sh
python3 scripts/check_runtime.py control
```

Resultado esperado: serviços `api` e `ui` saudáveis; somente `127.0.0.1:8501` publicado; arquivos gerados em `.private`, `.delivery` e `.env`. A inicialização é idempotente e preserva flags quando executada outra vez.

O diretório `.private` é 0700. Seus arquivos de secret são 0644 para leitura pelo UID do container em bind mount; usuários do host não atravessam o diretório pai. Apenas o token é montado na UI; só a API recebe os hashes. `.env` e o seed são 0600. Não relaxe permissões dos diretórios privados.

O healthcheck valida o backend e a inicialização do banco. O verificador de runtime também lê `memory.max`, `pids.max` e `cpu.max` dos cgroups dentro dos containers. Se a verificação falhar, investigue a causa antes de continuar.

## 5. Transferir o seed privado ao administrador da prática

O seed liga as flags dos exercícios aos hashes do painel. O estudante recebe as imagens, não os contexts de provisionamento.

**NOTEBOOK do operador:**

```bash
scp ctf-control:/home/ctfctl/docker-security-ctf-lab/.delivery/practice-seed.tar.gz ./ctf-seed.tar.gz
scp ./ctf-seed.tar.gz admin-inicial@IP_PRATICA:/tmp/ctf-seed.tar.gz
```

O comando local usa a chave administrativa de `ctf-control`; o segundo usa seu acesso administrativo inicial à prática. Mantenha o arquivo local sob acesso restrito. Em **PRÁTICA, administrador**, mova-o para área protegida:

```bash
sudo install -m 600 -o root -g root /tmp/ctf-seed.tar.gz /root/ctf-seed.tar.gz
rm /tmp/ctf-seed.tar.gz
# Ainda na extração pública original do administrador, fora do home de ctf:
sudo python3 scripts/provision_practice.py --user ctf --seed /root/ctf-seed.tar.gz
```

Execute o provisionador usando uma cópia administrativa confiável do script público, a extração original do administrador. **Não execute como root um script que um estudante pode modificar.** Mantenha essa cópia em diretório do administrador, junto de `practice/compose.yaml`, para provisionamentos posteriores.

O script verifica dono e permissões do seed, socket rootless, cgroup v2 e controllers. Transmite os três contexts via stdin sem extrair flags no home do estudante. Faz build das imagens e inicia o Compose no daemon de `ctf`. Os arquivos Dockerfile que contêm os valores aleatórios ficam apenas no seed protegido. As flags podem ser recuperadas nas imagens/containers pelo próprio exercício.

Resultado esperado: serviços `files`, `logs` e `environment` executando; nenhum publica portas, monta arquivos do host ou tem rede.

## 6. Conferir a prática e abrir a UI

**PRÁTICA, ctf:**

```bash
cd ~/docker-security-ctf-lab
docker context use rootless
python3 scripts/check_runtime.py practice
docker compose -p docker-ctf-practice -f practice/compose.yaml ps
```

**NOTEBOOK do estudante:**

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8501:127.0.0.1:8501 ctf-panel
```

Abra `http://127.0.0.1:8501`. A primeira tela mostra zero de três desafios concluídos. Consulte os enunciados; as flags não são mostradas antecipadamente na interface.

## 7. Se algo falhar

| Sintoma | Verificação |
|---|---|
| Build não baixa Alpine/Python | Saída HTTPS, DNS, proxy, credenciais/rate limits de registry |
| Volume `/data` sem permissão | Confira UID 10001, imagem API e volume novo; não use chmod 777 como solução geral |
| Secrets não encontrados | Rode init_lab.py na pasta correta; veja `.private` e os arquivos montados |
| UI sem backend | Logs API, healthcheck, rede `control`, mesmo token nos dois serviços |
| Seed parcial ou divergente | Restaure o conjunto original; não apague o banco para esconder o erro |
| Limite CPU não aplicado | Delegação systemd, reinício do user manager/VM e leitura de `cpu.max` |
| Daemon errado | `docker context show`; selecione rootless e confira DOCKER_HOST se configurado |

Não publique os logs privados ou o seed ao pedir ajuda. Compartilhe a mensagem de erro e comandos de diagnóstico sem tokens, chaves, flags ou CID.
