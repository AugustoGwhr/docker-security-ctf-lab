# Verificação local da adaptação Cloud

Verificado em 10/10/2026. Streamlit 1.65.0.

## Resultado

`python -m unittest discover -s tests -v`: **38 testes passaram**.

- 20 testes do backend: hashes, pontuação, dicas, persistência, limites e autenticação.
- 4 testes da interface original, incluindo processo Streamlit real com resposta HTTP 200 no health e na página inicial.
- 14 testes Cloud: configuração, modo de leitura, navegação, login/logout, hash de senha, compatibilidade com o servidor e bloqueio de redirecionamento para impedir encaminhamento de token.

A interface Cloud foi exercitada pelo AppTest do Streamlit. A conexão HTTPS externa foi simulada nos testes da interface; não foi validado um backend remoto. O bloqueio de redirecionamento foi verificado com servidores HTTP locais.

## Limites da verificação

Não houve upload ao GitHub nem deploy no Streamlit Community Cloud. Não foram conectados credenciais, VM, domínio, certificado ou API externa.

Não há Docker disponível neste ambiente de teste. Os containers e o provisionamento rootless precisam ser verificados nas VMs conforme SETUP.md. Publicar o portal sem Secrets permite apenas consultar o catálogo; validação de flags, pontuação e histórico dependem do backend.
