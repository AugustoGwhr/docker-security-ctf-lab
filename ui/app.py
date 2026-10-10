"""Interface single-user: executa somente chamadas HTTP de endpoints fixos."""
import hashlib
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backend.catalog import public_catalog
from ui.connection import BackendError, Settings, SettingsError, load_settings, password_matches, request_backend

st.set_page_config(page_title="Docker Security CTF Lab", page_icon="🛡️", layout="wide")
st.markdown("""<style>
.stApp {background: linear-gradient(125deg,#07111f,#101c2c)}
[data-testid="stMetric"] {background:#112438;border:1px solid #23445d;border-radius:12px;padding:18px}
h1,h2,h3 {letter-spacing:-.025em}
</style>""", unsafe_allow_html=True)


def api(path, payload=None):
    try:
        return request_backend(settings, path, payload)
    except BackendError as exc:
        st.error(str(exc))
        return None


def secret(key):
    try:
        return st.secrets.get(key, "")
    except (FileNotFoundError, KeyError):
        return ""


def cloud_login():
    fingerprint = hashlib.sha256(settings.password_hash.encode()).hexdigest()
    if st.session_state.get("portal_auth") == fingerprint:
        return
    st.subheader("Acessar o portal")
    now = time.time()
    attempts = [ts for ts in st.session_state.get("portal_attempts", []) if now - ts < 60]
    st.session_state["portal_attempts"] = attempts
    with st.form("portal_login", clear_on_submit=True):
        password = st.text_input("Senha do portal", type="password", max_chars=256)
        clicked = st.form_submit_button("Entrar", disabled=len(attempts) >= 5)
    if len(attempts) >= 5:
        st.warning("Aguarde um minuto antes de tentar novamente e atualize a página.")
    if clicked:
        if password_matches(password, settings.password_hash):
            st.session_state["portal_auth"] = fingerprint
            st.session_state["portal_attempts"] = []
            st.rerun()
        else:
            st.session_state["portal_attempts"].append(now)
            st.error("Senha incorreta.")
    st.stop()


def utc(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")


def documentation(name):
    root = Path(__file__).resolve().parent.parent
    st.markdown((root / "docs" / name).read_text())


st.title("🛡️ Docker Security CTF Lab")
try:
    settings = load_settings(secret)
except SettingsError as exc:
    st.warning(str(exc))
    settings = Settings(os.environ.get("LAB_DEPLOYMENT", "server"))
if settings.mode == "cloud" and settings.password_hash:
    cloud_login()
st.caption("Portal Cloud · prática individual · containers na VM Linux" if settings.mode == "cloud" else "Etapa 1 · prática individual · comandos no terminal SSH · flags verificadas no backend")
catalog = public_catalog()
state = None
if settings.ready:
    catalog = api("/api/catalog") or catalog
    state = api("/api/state")
catalog["levels"] = {str(k): v for k, v in catalog["levels"].items()}
if not state:
    st.info("Portal em modo de leitura. Enunciados e documentação disponíveis; validação, pontuação e histórico aguardam a conexão ao backend do laboratório.")

with st.sidebar:
    st.subheader("Jornada de aprendizagem")
    pages = ["Dashboard", "Desafios", "Acesso SSH", "Estado do laboratório", "Segurança Docker", "CrowdStrike Falcon", "Plano de implementação"]
    if settings.mode == "cloud":
        pages.append("Configuração Cloud")
    page = st.radio("Navegação", pages)
    st.divider()
    st.caption("Uma instância = um estudante. Portal e VM de prática são componentes separados." if settings.mode == "cloud" else "Uma instância = um estudante. O acesso ao painel usa a autenticação SSH.")
    if st.button("Atualizar painel"):
        st.rerun()
    if settings.mode == "cloud" and settings.password_hash and st.button("Sair"):
        st.session_state.pop("portal_auth", None)
        st.rerun()

if page == "Dashboard":
    a, b, c = st.columns(3)
    a.metric("Pontuação", f'{state["score"]} / {state["max_score"]}' if state else "Backend pendente")
    b.metric("Concluídos", f'{state["completed"]} / {state["total"]}' if state else "Backend pendente")
    c.metric("Níveis no roteiro", 6)
    if state:
        st.progress(state["completed"] / state["total"])
        st.caption("O progresso considera apenas os três desafios implementados nesta etapa.")
    if state and state["achievements"]:
        st.success(" · ".join(state["achievements"]))
    st.subheader("Níveis")
    st.dataframe([{
        "Nível": f'{n} — {name}',
        "Implementados na etapa 1": sum(x["status"] == "ready" and str(x["level"]) == n for x in catalog["challenges"]),
        "Planejados": sum(x["status"] == "planned" and str(x["level"]) == n for x in catalog["challenges"]),
    } for n, name in catalog["levels"].items()], hide_index=True, width="stretch")
    st.info("Comece na página Acesso SSH. Na VM de prática, investigue os containers; no painel, envie apenas a flag.")
    st.subheader("Últimas tentativas")
    rows = [{"Data": utc(x["timestamp"]), "Desafio": x["challenge"], "Resultado": "Correta" if x["success"] else "Incorreta"} for x in state["attempts"]] if state else []
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.write("Ainda não há tentativas." if state else "Conecte o backend para consultar o histórico real.")

elif page == "Desafios":
    level = st.selectbox("Nível", list(catalog["levels"]), format_func=lambda n: f'{n} — {catalog["levels"][n]}')
    choices = [c for c in catalog["challenges"] if str(c["level"]) == level]
    cid = st.selectbox("Desafio", [c["id"] for c in choices], format_func=lambda value: next(c["title"] + (" · planejado" if c["status"] == "planned" else "") for c in choices if c["id"] == value))
    challenge = next(c for c in choices if c["id"] == cid)
    st.subheader(challenge["title"])
    st.caption(f'{challenge["difficulty"]} · {challenge["points"]} pontos · {challenge["id"]}')
    if state and cid in state["completions"]:
        st.success(f'Concluído · {state["completions"][cid]["points"]} pontos registrados')
    st.write(challenge["objective"])
    st.markdown(challenge["theory"])
    if challenge["status"] != "ready":
        st.info(challenge["instructions"])
        st.stop()
    st.markdown(challenge["instructions"])
    st.code(challenge["commands"], language="bash")
    if not state:
        st.warning("A submissão de flags será habilitada quando o backend estiver conectado e os exercícios provisionados na VM.")
        st.stop()
    with st.form("submit_" + cid, clear_on_submit=True):
        flag = st.text_input("Flag encontrada", placeholder="CTF{...}", max_chars=256, type="password")
        submitted = st.form_submit_button("Validar flag")
    if submitted:
        result = api("/api/submit", {"challenge": cid, "flag": flag})
        if result:
            (st.success if result["correct"] else st.error)(result["message"])
            if result["correct"]:
                state = api("/api/state") or state
    st.caption("Cada nova dica consultada antes da conclusão reduz a recompensa em 10 pontos.")
    if st.button("Consultar próxima dica", key="hint_" + cid):
        result = api("/api/hint", {"challenge": cid})
        if result:
            state["hints"][cid] = result["hints"]
    for number, hint in enumerate(state["hints"].get(cid, []), 1):
        st.info(f"Dica {number}: {hint}")
    if cid in state["completions"]:
        result = api("/api/solution/" + cid)
        if result:
            with st.expander("Explicação técnica após a conclusão", expanded=True):
                st.write(result["explanation"])

elif page == "Estado do laboratório":
    if state:
        st.success("Backend acessível e banco de progresso inicializado.")
    else:
        st.warning("Backend pendente ou indisponível. Não há verificação de containers realizada pelo portal.")
    st.write("A interface não consulta o daemon Docker nesta etapa. O estado dos containers deve ser consultado na VM correspondente pelo SSH.")
    st.code("# CONTROLE, usuário ctfctl\ndocker compose -p docker-ctf-control ps\ndocker compose -p docker-ctf-control logs --tail 50\n\n# PRÁTICA, usuário ctf\ndocker compose -p docker-ctf-practice -f practice/compose.yaml ps\ndocker info", language="bash")
    st.write("Validação atual: comparação de hash da flag. Verificação de imagem publicada e de estado real de containers pertence às próximas etapas.")
    if state and state["audit"]:
        st.dataframe([{**r, "timestamp": utc(r["timestamp"])} for r in state["audit"]], hide_index=True)

elif page == "Acesso SSH":
    if settings.mode == "cloud":
        st.info("Na implantação Cloud, abra o portal pela URL do aplicativo. Use SSH para administrar a VM de prática. O roteiro abaixo também documenta a alternativa de hospedar o painel no servidor com túnel SSH.")
    documentation("SSH.md")
elif page == "Segurança Docker":
    documentation("SECURITY.md")
elif page == "CrowdStrike Falcon":
    documentation("FALCON.md")
elif page == "Plano de implementação":
    documentation("ROADMAP.md")
elif page == "Configuração Cloud":
    documentation("CLOUD.md")
