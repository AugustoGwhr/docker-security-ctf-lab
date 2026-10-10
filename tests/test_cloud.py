import json
import os
import secrets
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from backend.catalog import public_catalog
from scripts.create_portal_password import encode_password
from ui.connection import BackendError, Settings, SettingsError, load_settings, password_matches, request_backend

ROOT = Path(__file__).resolve().parent.parent
TEST_PASSWORD = "senha_apenas_para_testes_123!"
TEST_HASH = encode_password(TEST_PASSWORD)


class SettingsTest(unittest.TestCase):
    def settings(self, values):
        return load_settings(lambda key: values.get(key, ""), {"LAB_DEPLOYMENT": "cloud"})

    def full(self):
        return {"LAB_API_URL": "https://backend.example.test", "LAB_API_TOKEN": secrets.token_urlsafe(48), "PORTAL_PASSWORD_HASH": TEST_HASH}

    def test_cloud_empty_is_read_only(self):
        self.assertFalse(self.settings({}).ready)

    def test_cloud_valid_is_ready(self):
        settings = self.settings(self.full())
        self.assertTrue(settings.ready)
        self.assertEqual(settings.mode, "cloud")

    def test_cloud_requires_url_and_token_together(self):
        with self.assertRaises(SettingsError):
            self.settings({"LAB_API_URL": "https://backend.example.test"})

    def test_cloud_requires_password_before_connecting(self):
        values = self.full()
        values.pop("PORTAL_PASSWORD_HASH")
        with self.assertRaises(SettingsError):
            self.settings(values)

    def test_cloud_rejects_non_https_and_loopback(self):
        for url in ("http://backend.example.test", "https://localhost", "https://127.0.0.1", "https://api", "https://backend.example.test/?token=secret", "https://user:password@backend.example.test"):
            with self.subTest(url=url), self.assertRaises(SettingsError):
                self.settings({**self.full(), "LAB_API_URL": url})

    def test_cloud_rejects_invalid_hash_and_token(self):
        with self.assertRaises(SettingsError):
            self.settings({**self.full(), "PORTAL_PASSWORD_HASH": "invalid"})
        with self.assertRaises(SettingsError):
            self.settings({**self.full(), "LAB_API_TOKEN": "short"})

    def test_password_hash_correct_wrong_and_salts(self):
        self.assertTrue(password_matches(TEST_PASSWORD, TEST_HASH))
        self.assertFalse(password_matches("wrong", TEST_HASH))
        self.assertNotEqual(encode_password(TEST_PASSWORD), TEST_HASH)

    def test_server_mode_reads_file_and_remains_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            token = secrets.token_urlsafe(48)
            path.write_text(token)
            settings = load_settings(lambda key: "", {"API_TOKEN_FILE": str(path), "LAB_API_URL": "http://api:8080"})
            self.assertEqual(settings.token, token)
            self.assertEqual(settings.url, "http://api:8080")

    def test_no_backend_request_when_unconfigured(self):
        with self.assertRaises(BackendError):
            request_backend(Settings("cloud"), "/api/state")

    def test_redirect_does_not_forward_token(self):
        destinations = []
        class Destination(BaseHTTPRequestHandler):
            def do_GET(self):
                destinations.append(self.headers.get("Authorization"))
                self.send_response(200); self.end_headers(); self.wfile.write(b"{}")
            def log_message(self, *args):
                pass
        target = ThreadingHTTPServer(("127.0.0.1", 0), Destination)
        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{target.server_port}/capture")
                self.end_headers()
            def log_message(self, *args):
                pass
        redirect = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
        threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in (target, redirect)]
        for thread in threads:
            thread.start()
        try:
            settings = Settings("server", f"http://127.0.0.1:{redirect.server_port}", secrets.token_urlsafe(48))
            with self.assertRaises(BackendError):
                request_backend(settings, "/api/state")
            self.assertEqual(destinations, [])
        finally:
            for server in (target, redirect):
                server.shutdown(); server.server_close()
            for thread in threads:
                thread.join(timeout=3)


class CloudUITest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"LAB_DEPLOYMENT": "cloud"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def app(self, values=None):
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
        app.secrets.clear()
        if values:
            app.secrets.update(values)
        app.run()
        self.assertEqual(len(app.exception), 0)
        return app

    def click(self, app, label):
        next(b for b in app.button if b.label == label).click().run()
        self.assertEqual(len(app.exception), 0)

    def test_cloud_root_starts_without_secrets_and_all_pages_work(self):
        app = self.app()
        self.assertEqual(app.metric[0].value, "Backend pendente")
        for page in ["Desafios", "Acesso SSH", "Estado do laboratório", "Segurança Docker", "CrowdStrike Falcon", "Plano de implementação", "Configuração Cloud", "Dashboard"]:
            app.sidebar.radio[0].set_value(page).run()
            self.assertEqual(len(app.exception), 0, page)

    def test_cloud_read_only_has_no_flag_submission_or_hints(self):
        app = self.app()
        app.sidebar.radio[0].set_value("Desafios").run()
        self.assertEqual(len(app.text_input), 0)
        self.assertFalse(any(b.label in {"Validar flag", "Consultar próxima dica"} for b in app.button))
        self.assertEqual(len(app.selectbox[1].options), 4)

    def test_partial_config_is_read_only_and_has_no_traceback(self):
        app = self.app({"LAB_API_URL": "https://backend.example.test"})
        self.assertEqual(app.metric[0].value, "Backend pendente")
        self.assertTrue(app.warning)

    def test_login_prevents_backend_calls_and_logout_works(self):
        values = {"LAB_API_URL": "https://backend.example.test", "LAB_API_TOKEN": secrets.token_urlsafe(48), "PORTAL_PASSWORD_HASH": TEST_HASH}
        fixture = {"score": 0, "max_score": 300, "completed": 0, "total": 3, "achievements": [], "attempts": [], "completions": {}, "hints": {}, "audit": []}
        def response(settings, path, payload=None):
            return public_catalog() if path == "/api/catalog" else fixture
        with patch("ui.connection.request_backend", side_effect=response) as backend:
            app = self.app(values)
            self.assertEqual(backend.call_count, 0)
            app.text_input[0].set_value("wrong")
            self.click(app, "Entrar")
            self.assertEqual(backend.call_count, 0)
            app.text_input[0].set_value(TEST_PASSWORD)
            self.click(app, "Entrar")
            self.assertGreaterEqual(backend.call_count, 2)
            self.assertEqual(app.metric[0].value, "0 / 300")
            self.click(app, "Sair")
            self.assertTrue(any(b.label == "Entrar" for b in app.button))
            self.assertEqual(len(app.metric), 0)


if __name__ == "__main__":
    unittest.main()
