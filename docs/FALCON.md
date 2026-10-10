# Preparação do módulo CrowdStrike Falcon

**Estado desta entrega:** estudo e preparação. Não há sensor instalado por este pacote, conexão API, consulta à console ou detecção real validada. Ubuntu 24.04 é a base do laboratório; isso não comprova suporte de qualquer versão do sensor ao seu kernel.

## Escopos que precisam ser distinguidos

| Escopo | Pergunta que o módulo deve responder |
|---|---|
| Sensor Linux no host da prática | A versão escolhida suporta o SO/kernel/arquitetura e se comunica com o tenant? |
| Opções específicas para containers | Qual produto, método e runtime são suportados neste ambiente/licença? |
| Imagens, registry e pipeline | Há integração e permissão licenciada para avaliar a imagem antes de executá-la? |

Não instale o sensor de host dentro de um container comum como se fosse equivalente à instalação no host. Não presuma que instruções Helm/Kubernetes se aplicam ao Docker Compose. Confirme também a visibilidade de workloads rootless com a documentação/apoio do fornecedor para o método escolhido.

Fontes de implantação oficiais: [Sensor Deployment](https://developer.crowdstrike.com/falcon-sensor/), [falcon-scripts](https://github.com/CrowdStrike/falcon-scripts) e [role de instalação Ansible](https://developer.crowdstrike.com/falcon-sensor/ansible/roles/falcon-install/). A matriz detalhada da sua versão e requisitos do tenant devem ser conferidos na documentação autenticada da sua console; ela não foi acessada nesta entrega.

## Inventário antes de instalar

**VM PRÁTICA, terminal Linux:**

```bash
cat /etc/os-release
uname -r
uname -m
docker version
docker info
date -u --iso-8601=seconds
```

Preencha esta ficha com o operador:

| Campo | Registrar |
|---|---|
| SO, kernel e arquitetura | Saída real dos comandos |
| Sensor Linux | Versão aprovada e modo suportado na matriz oficial |
| Tenant/região/CID | Conferidos localmente na console correta |
| Licenças | Módulos contratados e permissões de usuário disponíveis |
| Instalação | Pacote oficial ou método automatizado revisado |
| Provisioning token | Se exigido pela configuração do tenant |
| Proxy/saída | Requisitos de comunicação da região do tenant |
| Política/grupo | Grupo do laboratório e política aprovada para testes |

CID associa o host ao tenant. Um processo rodando localmente, por si só, não comprova associação e comunicação corretas. Não compartilhe CID/tokens e dados do tenant em prints públicos.

## Instalação: intervenção manual prevista

Baixe da console o pacote `.deb` aprovado para seu host e confirme sua integridade pelo mecanismo fornecido pelo fabricante. A instalação deve ocorrer no host de prática por um administrador. O estudante não recebe sudo nem tokens administrativos.

Fluxo de referência, **somente depois de conferir os requisitos e o guia do pacote**:

```bash
# VM PRÁTICA, administrador; arquivo real baixado da console:
sudo dpkg -i ./NOME_REAL_DO_PACOTE_APROVADO.deb
# Leia o CID localmente, sem escrevê-lo como literal no histórico:
read -r -p 'CID do laboratório: ' CTF_FALCON_CID
sudo /opt/CrowdStrike/falconctl -s --cid="$CTF_FALCON_CID"
unset CTF_FALCON_CID
sudo systemctl start falcon-sensor
sudo systemctl status falcon-sensor --no-pager
sudo /opt/CrowdStrike/falconctl -g --version
sudo /opt/CrowdStrike/falconctl -g --aid
```

Esses comandos básicos não contemplam todas as políticas de provisioning/proxy. Se o tenant exigir token de provisionamento ou tiver método diferente, siga o guia da versão antes de executar. O script oficial de Linux documenta opções e configura CID, provisioning token e serviço: [código oficial](https://github.com/CrowdStrike/falcon-scripts/blob/main/bash/install/falcon-linux-install.sh). Para automação por API, revise a versão exata e os escopos requeridos; esta primeira etapa não cria uma API key.

Não incorpore pacote proprietário ou credenciais ao repositório. Não use modos de debug que imprimam segredos. Não copie automaticamente versões de exemplos sem verificar sua aprovação no tenant.

## Comprovar a operação

Na console correta, confira o host pelo hostname e identificador, horário de comunicação, versão, grupo e política aplicada. Use a informação realmente apresentada no seu tenant. Registre uma evidência sem dados sensíveis. AID local e serviço ativo são verificações complementares; não garantem que todas as funções de proteção estão habilitadas.

Se instalação ou comunicação falhar, não desative o sensor nem altere políticas para contornar o problema. Revise matriz SO/kernel/versão, CID/tenant, provisioning, proxy e logs permitidos pelo fabricante. Atualizações de kernel exigem nova conferência de suporte.

## Exercício benigno futuro: correlação, sem promessa de alerta

Depois da confirmação do sensor, gere uma execução identificável num container já autorizado. **PRÁTICA, ctf:**

```bash
CTF_CONTAINER_ID=$(docker compose -p docker-ctf-practice -f practice/compose.yaml ps -q files)
date -u --iso-8601=seconds
docker inspect --format 'container={{.Id}} pid={{.State.Pid}} image={{.Image}}' "$CTF_CONTAINER_ID"
docker exec "$CTF_CONTAINER_ID" sh -c 'echo CTF_BENIGN_PROCESS_CHECK; id; sleep 2'
date -u --iso-8601=seconds
unset CTF_CONTAINER_ID
```

O teste não baixa código, não faz conexões externas, não persiste e não tenta evadir prevenção. Seu objetivo é investigar a visibilidade disponível; não se espera obrigatoriamente uma detecção para esses comandos.

Na console, pesquise pela janela UTC e pelo host usando o recurso disponível e licenciado. Se o evento tiver metadados de container, compare-os com o ID/imagem. PIDs de namespaces podem diferir dos PIDs vistos pelo host; não correlacione só pelo número. Registre processo, parent, horário, host e contexto observado.

Modelo de registro próprio do laboratório:

| Campo | Valor observado |
|---|---|
| Identificador do teste | CTF_BENIGN_PROCESS_CHECK |
| Horário UTC inicial/final | Preencher com os comandos |
| Host/AID | Confirmar localmente e na console |
| Container/imagem | Dados de inspect |
| Processo e parent | Dados disponíveis no evento |
| Telemetria localizada | Sim/Não/Não acessível com a licença atual |
| Alerta/detecção/incidente | Tipo e ID somente se existir |
| Política aplicada | Nome/estado realmente observado |
| Limitações | Cobertura, retenção, permissões e campos ausentes |

Telemetria é observação. Detecção/alerta indica classificação pelo produto. Incidente é um agrupamento/tratamento de atividade, quando disponível. Preserve a terminologia real da console. Ausência de um registro numa busca não demonstra ausência de execução nem proteção completa.

Testes de prevenção precisam de um procedimento benigno recomendado oficialmente para o produto/versão, grupo e autorização do operador. Eles não estão incluídos como comandos nesta etapa. Malware real, desativação e evasão do sensor não fazem parte do laboratório.
