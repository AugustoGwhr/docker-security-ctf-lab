"""API restrita, sem shell, subprocess, Docker socket ou acesso à VM de prática."""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from backend.catalog import public_catalog
from backend.store import LabError, Store


def load_store():
    flags = json.loads(Path(os.environ.get("FLAG_HASHES_FILE", "/run/secrets/flag_hashes")).read_text())
    return Store(os.environ.get("LAB_DATABASE", "/data/lab.sqlite3"), flags)


def make_handler(store, token):
    class Handler(BaseHTTPRequestHandler):
        server_version = "CTFLab/0.1"

        def log_message(self, fmt, *args):
            # Não registra headers, flags, corpo, token ou URLs com query strings.
            print(f"request method={self.command} status={args[1] if len(args) > 1 else 'unknown'}", flush=True)

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def reply(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def authorized(self):
            value = self.headers.get("Authorization", "")
            if not hmac.compare_digest(value.encode(), ("Bearer " + token).encode()):
                self.reply(401, {"error": "Não autorizado."})
                return False
            return True

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/health":
                self.reply(200, {"status": "ok", "version": "0.1.0-stage1"})
                return
            if not self.authorized():
                return
            try:
                if path == "/api/catalog":
                    result = public_catalog()
                elif path == "/api/state":
                    result = store.state()
                elif path.startswith("/api/solution/"):
                    result = store.solution(path.rsplit("/", 1)[-1])
                else:
                    raise LabError(404, "Endpoint desconhecido.")
                self.reply(200, result)
            except LabError as exc:
                self.reply(exc.status, {"error": str(exc)})

        def do_POST(self):
            if not self.authorized():
                return
            try:
                if self.headers.get_content_type() != "application/json":
                    raise LabError(415, "Content-Type deve ser application/json.")
                try:
                    size = int(self.headers.get("Content-Length", "-1"))
                except ValueError:
                    raise LabError(400, "Content-Length inválido.") from None
                if not 0 <= size <= 8192:
                    raise LabError(413, "Corpo ausente ou maior que 8192 bytes.")
                try:
                    payload = json.loads(self.rfile.read(size))
                except (ValueError, UnicodeDecodeError):
                    raise LabError(400, "JSON inválido.") from None
                if not isinstance(payload, dict) or not isinstance(payload.get("challenge"), str):
                    raise LabError(400, "Informe challenge como texto.")
                path = urlsplit(self.path).path
                if path == "/api/submit":
                    result = store.submit(payload["challenge"], payload.get("flag"))
                elif path == "/api/hint":
                    result = store.hint(payload["challenge"])
                else:
                    raise LabError(404, "Endpoint desconhecido.")
                self.reply(200, result)
            except LabError as exc:
                self.reply(exc.status, {"error": str(exc)})
            except (TimeoutError, OSError):
                self.close_connection = True

    return Handler


def main():
    token = Path(os.environ.get("API_TOKEN_FILE", "/run/secrets/api_token")).read_text().strip()
    if len(token) < 32:
        raise SystemExit("Token inválido; execute scripts/init_lab.py.")
    server = ThreadingHTTPServer((os.environ.get("API_BIND", "0.0.0.0"), int(os.environ.get("API_PORT", "8080"))), make_handler(load_store(), token))
    print("CTF API iniciada; sem acesso ao Docker.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
