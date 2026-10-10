# Publicação do portal no Streamlit Community Cloud

O frontend está adaptado ao Streamlit Cloud. A VM Linux continua responsável pelos containers, Falcon e backend persistente. Esta versão permite publicar primeiro o portal em modo de leitura e conectar o backend depois.

## Fase 1 — portal e enunciados

Use o repositório `AugustoGwhr/docker-security-ctf-lab` e envie os arquivos deste pacote extraídos, preservando as pastas. `streamlit_app.py` e `requirements.txt` devem ficar na raiz do repositório. Não envie o ZIP como substituto do código.

No Streamlit Cloud, selecione:

| Campo | Valor |
|---|---|
| Repository | AugustoGwhr/docker-security-ctf-lab |
| Branch | main, se essa for a branch criada |
| Main file path | streamlit_app.py |
| Python, em Advanced settings | 3.12 |

Nesta fase, os Secrets podem ficar vazios. O portal inicia com dashboard, enunciados e documentação. Pontuação e histórico mostram **Backend pendente**; o formulário de flags e as dicas pontuadas não são habilitados. Não há armazenamento simulado, flag fixa ou conclusão fictícia.

Se o repositório é privado, autorize o Streamlit a acessá-lo na conexão com GitHub. Confira também a privacidade e os usuários autorizados do aplicativo no serviço; a privacidade do código e a do app são configurações distintas.

## Fase 2 — conexão real ao backend

Prepare as VMs conforme SETUP.md. O backend deve manter o banco SQLite e os hashes gerados, e ficar acessível pelo frontend em uma URL HTTPS autenticada. Não use `http://api:8080`, localhost ou endereço privado inacessível ao Streamlit Cloud.

O Compose entregue mantém o backend privado por padrão. **Ele não publica automaticamente a API na Internet.** Antes de conectar o portal, configure o método de acesso HTTPS no servidor: reverse proxy com TLS ou túnel gerenciado apropriado, mantendo autenticação por token na API. O projeto não inclui nem configura esse serviço, domínio ou certificado. A orientação depende da sua VM, rede e domínio disponíveis. Não abra o Docker socket nem exponha a porta do daemon.

Use a URL HTTPS final, sem redirecionamento. O token continua obrigatório para todas as rotas de dados. O `/health` contém somente status/versão. Não remova a autenticação do backend para fazer o portal conectar.

### Senha do portal

Esta é uma instalação individual. Antes de habilitar o backend, configure uma senha adicional do portal. No **NOTEBOOK**, dentro do projeto, com Python disponível:

```bash
python scripts/create_portal_password.py
```

O programa pede uma senha de 12 a 256 caracteres e sua confirmação, sem exibi-la. Produz somente a linha de hash PBKDF2 para cadastrar nos Secrets. Guarde a senha localmente; não publique a linha de hash no código. O frontend guarda o estado de login por sessão e bloqueia novas tentativas dessa sessão após cinco erros por minuto. Isso não é autenticação multiusuário ou SSO.

### Secrets do Streamlit

Na configuração do aplicativo, cadastre fora do GitHub:

```toml
LAB_API_URL = "https://ENDERECO_REAL_DO_BACKEND"
LAB_API_TOKEN = "TOKEN_REAL_GERADO_PELO_BACKEND"
PORTAL_PASSWORD_HASH = "LINHA_DE_HASH_GERADA_PELO_SCRIPT"
```

O token é o conteúdo de `.private/api_token` na VM de controle. Não gere outro token no frontend nem use CID Falcon/Docker Hub PAT nesse campo. Nenhum desses valores vem preenchido no pacote.

O frontend exige HTTPS e senha válida para conectar. Tokens não são enviados ao navegador nem incluídos nos logs do projeto. Redirecionamentos HTTP são recusados para evitar encaminhar Authorization a outro endereço. Sem configuração completa, o app mantém somente o catálogo educacional.

Depois de salvar os Secrets e reiniciar o app, a tela pede a senha. Com o backend acessível, o painel exibe o progresso real e habilita as flags. O backend não verifica o daemon de prática nesta etapa: confira separadamente o provisionamento dos três exercícios e execute check_runtime.py em cada VM.

## Fase 3 — estudar no laboratório

Abra o portal pela URL do Streamlit. Conecte-se por SSH à VM de prática para executar Docker. Recupere a flag no exercício e submeta no portal. O backend de controle verifica o hash e persiste tentativas/pontos. Dados persistentes permanecem na VM, não no filesystem temporário do Streamlit Cloud.

## Desenvolvimento local e opção servidor

Na raiz do projeto, `streamlit run streamlit_app.py` inicia o modo Cloud local. Sem Secrets, abre o catálogo em leitura. Para configurar Secrets localmente, use `.streamlit/secrets.toml`; esse arquivo está no .gitignore e deve permanecer fora do repositório.

O Compose e `ui/app.py` continuam usando modo servidor com o token montado por arquivo. Para forçar esse modo ao usar o entrypoint raiz, defina `LAB_DEPLOYMENT=server` no ambiente. Veja SERVER_README.md para o roteiro do pacote inicial de servidor.

## Limitações

- Uma instância = um estudante; não há contas/pontuação separadas por usuário.
- Backend HTTPS, VMs e credenciais não foram conectados nesta adaptação.
- Os demais níveis continuam planejados; publicar o portal não os implementa.
- Sem backend, navegar funciona, mas não há validação ou persistência de progresso.
- GitHub/Streamlit não executam os desafios Docker por meio deste frontend.

## Fontes oficiais

- [Publicar app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Dependências reconhecidas](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Secrets no Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
