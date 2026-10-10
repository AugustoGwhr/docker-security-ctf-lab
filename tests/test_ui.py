"""Teste do Streamlit contra backend HTTP real, com flags temporárias."""
import hashlib
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

from streamlit.testing.v1 import AppTest
from backend.catalog import ACTIVE_IDS
from backend.server import make_handler
from backend.store import Store

ROOT = Path(__file__).resolve().parent.parent


class UITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = {cid: "CTF{" + secrets.token_hex(16) + "}" for cid in ACTIVE_IDS}
        hashes = {cid: hashlib.sha256(flag.encode()).hexdigest() for cid, flag in self.flags.items()}
        self.store = Store(Path(self.tmp.name) / "lab.sqlite3", hashes)
        token = secrets.token_urlsafe(48)
        token_file = Path(self.tmp.name) / "token"
        token_file.write_text(token)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store, token))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.env = patch.dict(os.environ, {"LAB_API_URL": f"http://127.0.0.1:{self.server.server_port}", "API_TOKEN_FILE": str(token_file)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def app(self):
        result = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=30).run()
        self.assertEqual(len(result.exception), 0)
        return result

    def click(self, app, label):
        button = next(b for b in app.button if b.label == label)
        button.click().run()
        self.assertEqual(len(app.exception), 0)

    def test_dashboard_and_all_navigation_pages(self):
        app = self.app()
        self.assertEqual(app.metric[0].value, "0 / 300")
        for page in ["Acesso SSH", "Estado do laboratório", "Segurança Docker", "CrowdStrike Falcon", "Plano de implementação", "Desafios", "Dashboard"]:
            app.sidebar.radio[0].set_value(page).run()
            self.assertEqual(len(app.exception), 0, page)

    def test_hint_flag_award_and_solution(self):
        app = self.app()
        app.sidebar.radio[0].set_value("Desafios").run()
        self.click(app, "Consultar próxima dica")
        self.assertEqual(len(self.store.state()["hints"]["n1-arquivos"]), 1)
        app.text_input[0].set_value("incorrect")
        self.click(app, "Validar flag")
        self.assertEqual(self.store.state()["score"], 0)
        app.text_input[0].set_value(self.flags["n1-arquivos"])
        self.click(app, "Validar flag")
        self.assertEqual(self.store.state()["score"], 90)
        self.assertTrue(any("Explicação técnica" in exp.label for exp in app.expander))
        app.sidebar.radio[0].set_value("Dashboard").run()
        self.assertEqual(app.metric[0].value, "90 / 300")

    def test_planned_module_has_no_submission(self):
        app = self.app()
        app.sidebar.radio[0].set_value("Desafios").run()
        app.selectbox[0].set_value("2").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.text_input), 0)
        self.assertFalse(any(b.label == "Validar flag" for b in app.button))

    def test_streamlit_process_serves_health_and_bootstrap(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        log_path = Path(self.tmp.name) / "streamlit-process.log"
        with log_path.open("w") as log:
            process = subprocess.Popen([
                sys.executable, "-m", "streamlit", "run", "ui/app.py",
                "--server.address=127.0.0.1", f"--server.port={port}",
                "--server.headless=true",
            ], cwd=ROOT, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        self.fail("Streamlit falhou ao iniciar: " + log_path.read_text()[-1500:])
                    try:
                        with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2) as response:
                            self.assertEqual(response.status, 200)
                            self.assertEqual(response.read().strip(), b"ok")
                        with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                            self.assertEqual(response.status, 200)
                        break
                    except OSError:
                        time.sleep(0.2)
                else:
                    self.fail("Streamlit não ficou disponível em 30 segundos")
            finally:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
