# Segurança e modelo de confiança

## Fronteiras

| Área | Acesso | Dados/autoridade |
|---|---|---|
| Notebook estudante | SSH com ctf_lab | Shell na prática e túnel ao painel |
| Controle operador | SSH com ctf_admin | Configuração, hashes, token e banco |
| Conta ctfview | Túnel a 127.0.0.1:8501 | Sem shell, sem Docker |
| Streamlit | HTTP interno autenticado | Enunciados, flags submetidas e progresso |
| API | Rede interna Compose | Verifica hashes e grava SQLite; sem Docker |
| Prática ctf | Daemon rootless próprio | Administração dos containers de exercício |

Rootless reduz a autoridade do daemon ao usuário que o executa. Não é uma VM nem uma garantia contra falhas do kernel. A separação de VMs protege a base do painel de configurações inseguras do ambiente de prática.

O controle não possui conexão, token ou socket que permita executar comandos na prática. A UI não tem caixa de shell nem qualquer endpoint genérico de execução. O backend restringe os caminhos HTTP a catálogo, progresso, submissão, dica e explicação. Operações administrativas são locais.

## Controles implementados

- Usuário de aplicação 10001, filesystem somente leitura e no-new-privileges.
- Remoção de todas as capabilities; sem privileged e sem host network/PID.
- Limites de CPU, memória e processos com verificação dos controllers.
- Containers de prática sem rede e sem mount de dados do host.
- UI publicada apenas na interface loopback do controle; API sem publicação.
- Autenticação SSH para o painel; API com token aleatório em secret.
- Hashes de flags só no backend; valores em seed privado e imagens de exercício.
- Banco transacional; pontos concedidos uma única vez mesmo com concorrência.
- Limite de 20 tentativas por minuto, corpo HTTP de até 8192 bytes e flags de até 256 caracteres.
- Logs de API sem corpo/headers; histórico sem o texto das flags.
- Reset e cleanup restritos ao projeto e serviço, sem docker system prune.

Docker Compose secrets locais são arquivos montados, não um cofre criptográfico. O operador deve proteger `.private`, `.delivery`, `.env`, backups e a conta do daemon. Montar um Docker socket como read-only não o transforma em API somente leitura; ele não é montado em nenhum serviço desta entrega.

O estudante que controla o daemon de prática controla suas próprias imagens. Os segredos **do laboratório** são fictícios. Não use dados de clientes, tokens reais ou volumes pessoais nos desafios.

## Limitações relevantes

Esta implantação é individual e não tem login web próprio. A autenticação é o acesso por chave ao túnel SSH. Se várias pessoas usarem o mesmo painel, compartilharão o progresso. A API usa HTTP sobre rede interna local, sem TLS entre containers; não exponha essa rede em redes externas. O servidor HTTP padrão Python é usado neste laboratório restrito; uma implantação pública precisaria de servidor/reverse proxy e autenticação apropriados.

Quem administra o controle pode recuperar ou modificar respostas e pontos. Não há resistência a um operador malicioso nem verificação independente de atividade na primeira etapa.

A conta ctf pode ignorar as receitas de hardening ao criar seus próprios containers. Por isso a VM é dedicada, sem dados sensíveis e descartável. Os limites dos três containers não são quotas para todos os builds/containers que o estudante decidir criar. Para um laboratório multiusuário, estabeleça limites e isolamento por VM também no hypervisor/cloud.

## Exercícios de risco elevado nas etapas seguintes

Privileged, socket Docker e escape serão ensinados inicialmente com artefatos sintéticos ou diagramas, sem montar socket real em um container vulnerável. Se for necessário testar uma configuração com impacto no host, ela pertence a uma terceira VM descartável, sem credenciais de controle, sem dados reais e com snapshot anterior.

Namespaces, cgroups, seccomp e AppArmor terão verificações próprias. Não atribua proteção apenas à existência de um campo no YAML: confira o resultado em runtime. Testes do Falcon não devem desativar o sensor nem tentar evadir políticas.

## Evolução do verificador

O módulo futuro de validação de Docker Hub deve operar em ambiente descartável, com jobs allowlist, tempo de execução limitado, limite de saída, política de rede e nenhum campo de comando arbitrário. Ele não deve compartilhar o daemon do controle. Um digest informado pelo aluno não é prova de publicação: o serviço precisa consultá-lo no registry e realizar pull/execução sob sua própria autoridade.

A ausência desse verificador está explícita no painel. Não aceite respostas textuais como prova de publicação real.
