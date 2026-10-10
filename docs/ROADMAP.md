# Plano de implementação e critérios de aceitação

Esta entrega corresponde à etapa 1 e adianta uma fatia mínima da interface e dos fundamentos para testar a arquitetura. As demais etapas permanecem planejadas. Cada conclusão futura depende de evidência de execução; não há selo automático de conclusão para módulo ausente.

| Etapa | Estado | Arquivos/entrega | Comprovação |
|---|---|---|---|
| 1. Arquitetura e base | Implementada, implantação nas suas VMs pendente | Compose controle/prática, backend, painel, scripts e docs | Testes locais; depois check_runtime em cada VM |
| 2. Linux, Docker e SSH | Roteiro e scripts entregues; execução manual pendente | SSH.md, SETUP.md, instalação/rootless | Acesso por chave, túnel, cgroups e portas restritas |
| 3. Interface e progresso | Núcleo individual implementado | ui/app.py, backend/store.py | Persistência, dicas, pontuação e histórico testados |
| 4. Docker e Docker Hub | 3 exercícios introdutórios implementados; build/Hub pendentes | Imagens geradas de fundamentos; próximos contexts Python | Publicação real, pull por digest e resposta HTTP em worker descartável |
| 5. Redes, volumes e Compose | Planejada | Python/PostgreSQL/Nginx e configuração com falha | Healthchecks e consultas reais; reset isolado |
| 6. Segurança de containers | Planejada | Hardening, camadas, SBOM/CVE e simulações | Inspeção de runtime, relatórios de scan e prova da correção |
| 7. Falcon | Preparação documentada; depende do tenant | Inventário, pacote, sensor, políticas e relatório | Estado local + host na console + correlação disponível |
| 8. Cenários integrados | Planejada | Cinco CTFs de Blue Team/DevSecOps | Rubricas e evidências por cenário |
| 9. Validação final | Parcial, apenas etapa 1 | Tests e check_runtime | Teste completo nas VMs; registry e Falcon autenticados |

## Nível 2: build e publicação obrigatória

Construir uma aplicação Python HTTP simples com resposta de desafio. O estudante escreve o Dockerfile, faz build, cria tag com seu namespace, autentica no Docker Hub, publica e baixa novamente a imagem no servidor.

Requisitos do verificador:

1. Receber apenas referência de repositório/tag ou digest, sem URL arbitrária e sem comando.
2. Validar namespace e nome, consultar o Docker Hub e resolver o digest.
3. Fazer pull em worker descartável com cache isolado.
4. Executar a imagem sem privileged, sem capabilities, sem mount de host, sem socket e com quotas.
5. Fazer requisição HTTP ao serviço pela rede privada do worker e conferir o contrato/challenge nonce.
6. Emitir uma flag específica desse desafio somente após comprovação, registrando digest e resultado.

Repositório público dedicado simplifica a primeira implementação. Repositório privado exige credencial read-only mantida no worker, separada do PAT de publicação do aluno.

Cache, multi-stage e buildx devem incluir comparação de resultado e manifestos. Multiarch com emulação pode demandar configuração adicional fora dos containers de desafio. ImageStreams pertencem ao OpenShift; oferecer um módulo opcional com cluster compatível, sem chamar uma imagem Docker de ImageStream.

## Nível 3: multicontainer

Criar ambiente Python/PostgreSQL/Nginx inicialmente com um erro de nome DNS ou rede. O aluno precisa produzir uma transação real, identificar a falha e aplicar a correção. Volumes terão dados fictícios, permissão conhecida e teste de persistência após recriação. `depends_on` não substitui verificação de readiness: usar healthcheck e uma aplicação que trate reconexão.

## Nível 4: segurança

Oferecer pares vulnerável/corrigido: root/non-root, capabilities, portas, bind mounts, camadas com credencial fictícia e versões de dependências. Explicar risco, observar configuração e aplicar mitigação. Trivy/Scout devem produzir relatórios com versão/data da base; severidade não é prova de explorabilidade. Gerar SBOM e distinguir identificação, priorização e correção.

Os exercícios de escape e Docker socket ficam simulados ou em VM adicional explicitamente descartável. Não introduzir uso privileged na VM principal como parte de um desafio automático.

## Nível 5: Falcon

Começar pelo inventário e pelo requisito de compatibilidade. Decidir método suportado depois de conhecer kernel, arquitetura, versão do sensor, tenant, região e licenças. Validar instalação local e confirmação da comunicação na console. Registrar observação mesmo quando um evento benigno não produz detecção.

A autenticação API é uma integração separada. Permissões dependem dos endpoints efetivamente necessários; não fornecer escopo amplo por conveniência. Instalação manual a partir da console não exige presumir que uma API key já existe. Seguir FALCON.md.

## Nível 6: cinco cenários integrados

| Cenário | Prova de conclusão |
|---|---|
| Imagem vulnerável | Dockerfile corrigido, scan contextualizado e digest publicado |
| Container mal configurado | Correção de rede/permissões, aplicação funcional e hardening em runtime |
| Investigação Falcon | Linha do tempo, vínculo host/container/processo e limitações das evidências |
| Pipeline DevSecOps | Build, scan, SBOM, gate de política, publicação e tratamento de falha |
| Incidente simulado | Origem, impacto, configurações contribuintes, contenção e relatório |

Investigações não devem ser aprovadas por uma palavra-chave isolada. Para relatos abertos, usar revisão humana ou uma rubrica que exponha o que é verificável automaticamente. Evidências sintéticas devem ser rotuladas; jamais apresentadas como exportação real do tenant.

## Pendências para a próxima fase

Configurar as duas VMs, executar os testes de runtime e informar apenas ambiente/requisitos não secretos. Preparar namespace Docker Hub exclusivo. Para o Falcon, trazer a matriz compatível e módulos disponíveis do tenant, sem enviar chave privada, PAT, client secret ou token de manutenção ao chat.
