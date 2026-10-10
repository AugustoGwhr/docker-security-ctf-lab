"""Configuração e transporte HTTP; não executa comandos nem acessa Docker."""
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SettingsError(ValueError):
    pass


class BackendError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    mode: str
    url: str = ""
    token: str = ""
    password_hash: str = ""

    @property
    def ready(self):
        return bool(self.url and self.token)


def parse_password_hash(value):
    try:
        algorithm, rounds, salt, digest = value.split("$")
        if algorithm != "pbkdf2_sha256" or int(rounds) != 600000:
            raise ValueError()
        if len(salt) != 32 or len(digest) != 64:
            raise ValueError()
        return int(rounds), bytes.fromhex(salt), bytes.fromhex(digest)
    except (ValueError, AttributeError):
        raise SettingsError("PORTAL_PASSWORD_HASH inválido. Use scripts/create_portal_password.py.") from None


def password_matches(password, encoded):
    rounds, salt, expected = parse_password_hash(encoded)
    if not isinstance(password, str) or not password or len(password) > 256:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return hmac.compare_digest(actual, expected)


def load_settings(secret, env=None):
    env = os.environ if env is None else env
    mode = env.get("LAB_DEPLOYMENT", "server")
    if mode not in {"cloud", "server"}:
        raise SettingsError("LAB_DEPLOYMENT deve ser cloud ou server.")
    if mode == "server":
        try:
            token = Path(env.get("API_TOKEN_FILE", "/run/secrets/api_token")).read_text().strip()
        except OSError:
            raise SettingsError("Configuração do servidor ausente. Execute scripts/init_lab.py e inicie o Compose.") from None
        if len(token) < 32:
            raise SettingsError("Token do backend inválido.")
        return Settings(mode, env.get("LAB_API_URL", "http://api:8080").rstrip("/"), token)
    values = {key: secret(key) for key in ("LAB_API_URL", "LAB_API_TOKEN", "PORTAL_PASSWORD_HASH")}
    if any(not isinstance(value, str) for value in values.values()):
        raise SettingsError("Os Secrets do portal devem ser valores de texto.")
    url = values["LAB_API_URL"].strip().rstrip("/")
    token = values["LAB_API_TOKEN"].strip()
    password_hash = values["PORTAL_PASSWORD_HASH"].strip()
    if password_hash:
        parse_password_hash(password_hash)
    if bool(url) != bool(token):
        raise SettingsError("Configure LAB_API_URL e LAB_API_TOKEN juntos. O catálogo permanece acessível sem conexão.")
    if url:
        try:
            parsed = urlsplit(url)
            _ = parsed.port
        except ValueError:
            raise SettingsError("LAB_API_URL inválida.") from None
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise SettingsError("LAB_API_URL precisa ser uma URL HTTPS, sem credenciais, query ou fragmento.")
        if parsed.hostname.lower() in {"api", "localhost", "127.0.0.1", "::1"}:
            raise SettingsError("Use o endereço HTTPS do backend no servidor, acessível pelo Streamlit Cloud.")
        if len(token) < 32:
            raise SettingsError("LAB_API_TOKEN deve ser o token completo do backend.")
        if not password_hash:
            raise SettingsError("Configure PORTAL_PASSWORD_HASH antes de conectar o backend ao portal Cloud.")
    return Settings(mode, url, token, password_hash)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Evita enviar Authorization para outro endereço por redirect.
        return None


def request_backend(settings, path, payload=None):
    if not settings.ready:
        raise BackendError("Backend ainda não configurado.")
    req = Request(settings.url + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + settings.token, "Content-Type": "application/json"},
        method="GET" if payload is None else "POST")
    try:
        with build_opener(NoRedirect()).open(req, timeout=10) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise BackendError("Resposta inesperada do backend.")
        return result
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            raise BackendError("O backend redirecionou a conexão. Configure a URL HTTPS final, sem redirects.") from None
        try:
            message = json.load(exc).get("error", "O backend recusou a operação.")
        except (ValueError, OSError, AttributeError):
            message = "O backend recusou a operação."
        raise BackendError(message) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise BackendError("Backend indisponível. Confira a conexão, os Secrets e o serviço no servidor.") from None
