# Desafios disponíveis na etapa 1

O ambiente deve ser preparado primeiro por SETUP.md. Execute as investigações na VM de prática e use o notebook apenas para SSH/navegador. O painel é a área de submissão.

| ID | Objetivo | Pontos | Ambiente | Validação |
|---|---|---:|---|---|
| n1-arquivos | Encontrar arquivo dentro do container | 100 | Serviço files | Hash da flag recuperada |
| n1-logs | Recuperar mensagem de inicialização | 100 | Serviço logs | Hash da flag recuperada |
| n1-ambiente | Consultar variável de configuração | 100 | Serviço environment | Hash da flag recuperada |

As flags têm valor aleatório exclusivo por implantação. Não há uma resposta estática nesta documentação. Enunciados, conceitos, comandos de exploração e dicas estão no painel. A explicação de cada solução é liberada após sua conclusão no backend.

## Sequência sugerida

1. Confirme o contexto rootless e liste os containers do projeto.
2. Resolva o desafio de arquivos e compare imagem versus container.
3. Resolva o desafio de logs e identifique o processo principal.
4. Resolva o desafio de ambiente e explique o risco de ENV com segredo real.
5. Recrie apenas um serviço com reset.sh e confira que os outros continuam ativos.

As três imagens executam como UID/GID 10001; não precisam de rede, volumes do host, capabilities adicionais ou privilégio. O shell é usado somente no seu terminal via docker exec.

## Como usar as dicas

Cada clique libera a próxima dica e aplica desconto de 10 pontos antes da conclusão. As dicas já liberadas continuam disponíveis sem novo desconto. Após a conclusão, consultar dicas não altera os pontos ganhos. Um segundo envio correto registra outra tentativa, mas não soma pontos novamente.

## Reinício

**PRÁTICA, ctf:**

```bash
bash scripts/reset.sh files
# Alternativas: logs ou environment
```

Isso recria o container desse serviço usando a mesma imagem e a mesma flag. Não apaga progresso. Reset de pontuação é uma operação administrativa separada no controle, descrita no README.

## Limite da prova

Esta etapa valida a flag correta. Não prova que você usou um comando específico nem que não inspecionou uma camada alternativa. Você administra o daemon de prática e pode investigar livremente os dados fictícios do exercício.

O desafio obrigatório de publicação no Docker Hub terá outra validação: resolução do digest pelo registry, pull fresco e execução limitada. Ele está planejado e permanece bloqueado no painel nesta versão.
