"""Catálogo didático. Não contém flags nem respostas estáticas."""

LEVELS = {
    1: "Fundamentos de Docker",
    2: "Dockerfile, Build e Docker Hub",
    3: "Redes, Volumes e Compose",
    4: "Segurança de Containers",
    5: "CrowdStrike Falcon",
    6: "Blue Team e DevSecOps",
}

CHALLENGES = [
    {
        "id": "n1-arquivos", "level": 1, "title": "Um arquivo dentro do container",
        "points": 100, "status": "ready", "difficulty": "Fácil",
        "objective": "Identificar um container, entrar nele e localizar a flag em seu filesystem.",
        "theory": "Imagem é o modelo de filesystem e configuração. Container é uma instância dessa imagem. docker ps lista containers em execução; docker exec cria um processo em uma instância existente.",
        "instructions": "Na VM de prática, como ctf, liste os containers do projeto docker-ctf-practice. Identifique o serviço files e investigue seus diretórios. A flag está em um arquivo legível dentro do container. Submeta o valor completo no painel. Não é preciso instalar ferramentas nem mudar permissões.",
        "commands": "# SERVIDOR DE PRÁTICA, usuário ctf\ndocker ps --filter label=com.docker.compose.project=docker-ctf-practice\ndocker images\ndocker inspect <ID_DO_CONTAINER>\ndocker exec -it <ID_DO_CONTAINER> sh\n# DENTRO DO CONTAINER\npwd\nls /",
        "hints": ["Use docker exec para abrir um shell no serviço files.", "O diretório /challenge merece atenção.", "Leia o arquivo flag que está nesse diretório."],
        "solution": "Use docker exec <ID> cat /challenge/flag. COPY inseriu esse arquivo na imagem no provisionamento, sem expor uma flag no código distribuído. A camada permanece disponível mesmo se o container for recriado. Controle do daemon permite inspecionar as imagens; isto é uma prática individual, não uma competição contra o administrador.",
    },
    {
        "id": "n1-logs", "level": 1, "title": "A pista nos logs",
        "points": 100, "status": "ready", "difficulty": "Fácil",
        "objective": "Encontrar uma mensagem de inicialização em stdout.",
        "theory": "docker logs consulta stdout e stderr capturados pelo driver de logs. Um processo pode registrar dados na inicialização e depois permanecer ativo sem produzir novas mensagens.",
        "instructions": "Na VM de prática, encontre o serviço logs. A aplicação escreveu a flag quando iniciou. Recupere a mensagem sem reiniciar os outros serviços. Depois, identifique o processo principal pelo inspect ou pelo docker top.",
        "commands": "# SERVIDOR DE PRÁTICA, usuário ctf\ndocker ps --filter label=com.docker.compose.service=logs\ndocker top <ID_DO_CONTAINER>\ndocker logs --help",
        "hints": ["A saída está no driver de logs, não em um servidor web.", "docker logs pode mostrar mensagens produzidas antes de você se conectar.", "Use docker logs <ID_DO_CONTAINER>."],
        "solution": "docker logs <ID> mostra a flag emitida no início. docker top <ID> mostra o processo sleep que mantém a instância ativa. Em aplicações reais, registrar segredos em stdout pode expô-los ao operador e à plataforma de observabilidade.",
    },
    {
        "id": "n1-ambiente", "level": 1, "title": "Configuração e variáveis",
        "points": 100, "status": "ready", "difficulty": "Fácil",
        "objective": "Consultar configuração de ambiente e explicar por que ENV não guarda segredos.",
        "theory": "ENV define valores disponíveis para processos e para a inspeção da imagem/container. Não constitui um cofre. Administradores do daemon podem recuperar esses valores.",
        "instructions": "Na VM de prática, identifique o serviço environment. Descubra a variável de treinamento e recupere a flag por inspeção ou por um processo dentro do container. Não altere o ambiente do painel.",
        "commands": "# SERVIDOR DE PRÁTICA, usuário ctf\ndocker ps --filter label=com.docker.compose.service=environment\ndocker inspect --help\ndocker exec <ID_DO_CONTAINER> env",
        "hints": ["A configuração do container inclui uma lista chamada Env.", "CTF_TRAINING_FLAG é uma variável apenas deste exercício.", "docker inspect --format '{{json .Config.Env}}' <ID> mostra as variáveis."],
        "solution": "Recupere CTF_TRAINING_FLAG usando inspect ou env. A flag foi criada no provisionamento. O uso de ENV é intencionalmente didático. Tokens de Docker Hub e Falcon devem ficar fora das imagens e dos arquivos versionados.",
    },
]

PLANNED = [
    (1, "n1-ciclo", "Ciclo de vida e processos", 100, "start, stop, restart e PID 1"),
    (2, "n2-build", "Aplicação Python e Dockerfile", 200, "FROM, COPY, WORKDIR, USER, CMD e ENTRYPOINT"),
    (2, "n2-hub", "Do código ao Docker Hub", 200, "build, login, tag, push, pull e execução por digest"),
    (2, "n2-buildx", "Cache, multi-stage e arquiteturas", 350, "buildx e inspeção de manifest lists"),
    (2, "n2-imagestream", "ImageStream: módulo OpenShift opcional", 200, "Objeto OpenShift, não recurso do Docker Engine"),
    (3, "n3-rede", "DNS e comunicação entre serviços", 200, "bridge, rede interna e diagnóstico"),
    (3, "n3-volume", "Persistência e permissões", 200, "volume nomeado, bind mount e UID/GID"),
    (3, "n3-compose", "Python, PostgreSQL e Nginx", 350, "healthchecks e correção de ambiente multicontainer"),
    (4, "n4-hardening", "Usuário, capabilities e filesystem", 350, "non-root, cap_drop, read_only e no-new-privileges"),
    (4, "n4-camadas", "Credenciais em camadas", 350, "Segredo fictício removido em camada posterior"),
    (4, "n4-isolamento", "Namespaces, cgroups e políticas", 350, "seccomp, AppArmor e limites efetivos"),
    (4, "n4-sbom", "SBOM, CVEs e atualização", 350, "Trivy/Scout, contexto e correção verificável"),
    (4, "n4-socket", "Privileged, socket e escape simulado", 350, "Evidências sintéticas; sem escape no servidor"),
    (5, "n5-requisitos", "Falcon: inventário e compatibilidade", 350, "SO, kernel, arquitetura, versão, tenant e licença"),
    (5, "n5-sensor", "Sensor: instalação e conectividade", 350, "Pacote oficial, CID e confirmação na console"),
    (5, "n5-telemetria", "Correlacionar eventos benignos", 350, "UTC, host, container, PID e disponibilidade de eventos"),
    (5, "n5-politicas", "Detecção, prevenção e investigação", 350, "Sem presumir alerta para todo comando"),
    (6, "n6-imagem", "CTF integrado: imagem vulnerável", 500, "Analisar, corrigir e publicar versão segura"),
    (6, "n6-config", "CTF integrado: configuração", 500, "Rede, permissões e regressão"),
    (6, "n6-falcon", "CTF integrado: investigação Falcon", 500, "Evidências reais ou sintéticas claramente identificadas"),
    (6, "n6-pipeline", "Pipeline DevSecOps", 500, "Build, scan, SBOM, políticas e publicação"),
    (6, "n6-incidente", "Incidente simulado", 500, "Linha do tempo, origem, impacto e resposta"),
]

for level, cid, title, points, topic in PLANNED:
    CHALLENGES.append({
        "id": cid, "level": level, "title": title, "points": points,
        "status": "planned", "difficulty": "Especialista" if points == 500 else "Avançado" if points == 350 else "Intermediário" if points == 200 else "Fácil",
        "objective": topic,
        "theory": "Módulo planejado no roteiro de implementação. Não participa do progresso desta entrega.",
        "instructions": "O ambiente e o verificador deste módulo ainda não foram implementados.",
        "commands": "", "hints": [], "solution": "",
    })

INDEX = {c["id"]: c for c in CHALLENGES}
ACTIVE_IDS = {c["id"] for c in CHALLENGES if c["status"] == "ready"}


def public_catalog():
    return {
        "levels": LEVELS,
        "challenges": [dict(
            **{k: v for k, v in c.items() if k not in {"hints", "solution"}},
            hints_available=len(c["hints"]),
        ) for c in CHALLENGES],
    }
