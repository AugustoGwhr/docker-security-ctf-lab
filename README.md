# Docker Security CTF Lab — portal Streamlit Cloud

Versão adaptada do projeto inicial para o repositório **AugustoGwhr/docker-security-ctf-lab**.

## Publicar primeiro o portal

Envie os arquivos extraídos para a raiz do repositório GitHub. No Streamlit Community Cloud, escolha o repositório e o arquivo **streamlit_app.py**. Selecione Python **3.12** em Advanced settings.

`requirements.txt` fixa a versão Streamlit testada. O arquivo `streamlit_app.py` inicia o modo Cloud; a lógica da interface permanece em `ui/app.py`.

Sem Secrets, a aplicação abre com o catálogo, níveis, enunciados e documentação. Pontuação/histórico indicam **Backend pendente**. Não há validação de flags nem progresso fictício nessa fase.

## Conectar o laboratório depois

O backend permanece na VM Linux, com banco persistente, token e hashes. Os containers de exercício permanecem numa VM de prática. Depois de configurar acesso HTTPS ao backend, cadastre URL, token e hash da senha do portal nos Secrets do Streamlit. Veja **[docs/CLOUD.md](docs/CLOUD.md)**.

A configuração do servidor entregue mantém a API privada. Publicar o portal não abre uma API pública nem configura TLS/domínio automaticamente. Essa conexão será preparada de acordo com sua infraestrutura.

| Componente | Responsabilidade |
|---|---|
| Streamlit Cloud | Portal, catálogo e frontend de submissão quando conectado |
| Backend Linux | Hashes, SQLite, tentativas, dicas e pontos |
| VM de prática | Docker rootless e três desafios introdutórios |
| Notebook | Navegador e terminal SSH |

## Arquivos principais

- `streamlit_app.py`: entrypoint Cloud.
- `requirements.txt`: dependências reconhecidas pelo Cloud.
- `ui/app.py`: interface.
- `ui/connection.py`: configuração e transporte do backend.
- `backend/`: backend inicial e catálogo didático.
- `docs/CLOUD.md`: publicação e conexão.
- `scripts/create_portal_password.py`: cria localmente o hash da senha do portal.
- `compose.yaml`, `practice/compose.yaml`: alternativa servidor e ambiente de prática.

O catálogo lê enunciados locais. Somente o backend conectado fornece progresso real. As respostas das flags nunca estão no código distribuído; valores aleatórios são gerados no provisionamento da VM.

## Opção servidor Linux

A opção original de hospedar UI/API na VM com SSH continua disponível. Consulte [docs/SERVER_README.md](docs/SERVER_README.md), [docs/SETUP.md](docs/SETUP.md) e [docs/SSH.md](docs/SSH.md).

## Testar

```bash
python -m venv .venv
# Linux: source .venv/bin/activate
# Windows/PowerShell: .venv/Scripts/Activate.ps1
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Resultados e limitações em [docs/CLOUD_TEST_RESULTS.md](docs/CLOUD_TEST_RESULTS.md). Esta adaptação não realizou upload no seu GitHub nem deployment no seu Streamlit.

Não envie `.env`, `.private`, `.delivery`, chaves, arquivos de banco ou `.streamlit/secrets.toml` ao GitHub. O pacote de upload contém apenas código e exemplos sem valores reais.
