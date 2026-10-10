# Verificação desta entrega

Data: 10/10/2026. Ambiente local de validação: Linux, Python 3.12.14, Streamlit 1.65.0.

| Grupo | Resultado observado |
|---|---|
| Backend/API/provisionamento | 20 testes aprovados, unittest |
| Interface e processo Streamlit | 4 testes aprovados, AppTest + HTTP real |
| Python | Todos os arquivos passaram por parsing/compilação |
| Bash | Todos os scripts passaram por bash -n |
| YAML/TOML | Parsing aprovado e invariantes de hardening conferidas |

Total automatizado: **24 testes aprovados**.

Os testes cobrem erro/acerto de flag, dicas e descontos, recompensa única, concorrência, persistência, backup, reset com histórico preservado, rate limit persistente, seed divergente, bloqueio de módulos planejados, autenticação HTTP, limites de entrada e ausência de endpoints de shell/admin.

O provisionamento foi testado com seeds temporários: geração exclusiva, idempotência, modos de arquivo, validação de symlinks e correspondência dos hashes aos contexts. Os valores temporários não foram incluídos no pacote.

Os testes Streamlit executaram as páginas, navegaram entre elas, enviaram flag errada/correta, consumiram dica, observaram a pontuação e a liberação de explicação. Um processo Streamlit real respondeu HTTP 200 no healthcheck e na página inicial. Isso valida inicialização e lógica da UI; não equivale a revisão visual em diferentes navegadores/tamanhos de tela.

Foram corrigidos antes da entrega: uma mudança de rótulo de selectbox que afetava navegação após conclusão e a configuração explícita de developmentMode para inicialização fora de site-packages.

## Verificações ainda necessárias nas suas VMs

Não havia Docker Engine/daemon disponível no ambiente de validação. **Não foram executados** build das imagens, docker compose config, inicialização Compose, inspeção de cgroups em containers, instalação Ubuntu/rootless, SSH remoto ou testes de firewall nas VMs.

Parsing YAML e inspeção estática não comprovam que o Docker aplicou as opções em runtime. Depois da instalação, execute:

```bash
# CONTROLE, ctfctl
docker compose -p docker-ctf-control config --quiet
bash scripts/start.sh
python3 scripts/check_runtime.py control

# PRÁTICA, ctf, após provisionamento administrativo
docker compose -p docker-ctf-practice -f practice/compose.yaml config --quiet
python3 scripts/check_runtime.py practice
```

Os scripts acima verificam containers ativos, usuário, filesystem, capabilities, no-new-privileges, portas, ausência de socket montado, healthchecks do controle e valores reais de memory.max/pids.max/cpu.max. Erros devem ser resolvidos antes de iniciar a jornada.

Docker Hub e Falcon não foram acessados com credenciais. Não há alegação de publicação de imagem, compatibilidade de sensor com um kernel específico, comunicação com tenant ou detecção observada. Esses módulos estão planejados no painel e no ROADMAP.
