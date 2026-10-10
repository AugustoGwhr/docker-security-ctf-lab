import concurrent.futures
import hashlib
import json
import secrets
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.catalog import ACTIVE_IDS, public_catalog
from backend.server import make_handler
from backend.store import LabError, Store
from scripts.init_lab import initialize
from scripts.provision_practice import read_contexts


def fixture(directory):
    flags = {cid: "CTF{" + secrets.token_hex(16) + "}" for cid in ACTIVE_IDS}
    hashes = {cid: hashlib.sha256(flag.encode()).hexdigest() for cid, flag in flags.items()}
    return Store(Path(directory) / "lab.sqlite3", hashes), flags


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store, self.flags = fixture(self.tmp.name)
        self.cid = "n1-arquivos"

    def test_wrong_flag_is_audited_but_not_stored(self):
        self.assertFalse(self.store.submit(self.cid, "wrong")["correct"])
        self.assertEqual(self.store.state()["score"], 0)
        with self.store.connect() as db:
            columns = [r[1] for r in db.execute("PRAGMA table_info(attempts)")]
            self.assertNotIn("flag", columns)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 1)

    def test_duplicate_correct_flag_awards_once(self):
        first = self.store.submit(self.cid, self.flags[self.cid])
        second = self.store.submit(self.cid, self.flags[self.cid])
        self.assertTrue(first["new_completion"])
        self.assertFalse(second["new_completion"])
        self.assertEqual(self.store.state()["score"], 100)
        self.assertEqual(len(self.store.state()["attempts"]), 2)

    def test_hints_are_progressive_and_reduce_points(self):
        self.assertEqual(len(self.store.hint(self.cid)["hints"]), 1)
        self.assertEqual(len(self.store.hint(self.cid)["hints"]), 2)
        self.assertEqual(self.store.submit(self.cid, self.flags[self.cid])["points"], 80)
        self.store.hint(self.cid)
        self.assertEqual(self.store.state()["score"], 80)

    def test_hint_penalty_stops_at_available_hints(self):
        for _ in range(5):
            result = self.store.hint(self.cid)
        self.assertEqual(result["penalty"], 30)
        self.assertEqual(result["remaining"], 0)
        self.assertEqual(self.store.submit(self.cid, self.flags[self.cid])["points"], 70)

    def test_solution_locked_until_complete(self):
        with self.assertRaises(LabError) as error:
            self.store.solution(self.cid)
        self.assertEqual(error.exception.status, 403)
        self.store.submit(self.cid, self.flags[self.cid])
        self.assertIn("explanation", self.store.solution(self.cid))

    def test_persistence_and_backup(self):
        self.store.submit(self.cid, self.flags[self.cid])
        reopened = Store(self.store.database, self.store.flag_hashes)
        self.assertEqual(reopened.state()["score"], 100)
        backup = Path(self.tmp.name) / "backup.sqlite3"
        self.store.backup(backup)
        self.assertEqual(Store(backup, self.store.flag_hashes).state()["score"], 100)

    def test_reset_is_scoped_and_preserves_audit(self):
        for cid in (self.cid, "n1-logs"):
            self.store.submit(cid, self.flags[cid])
        self.store.hint("n1-ambiente")
        self.store.reset(self.cid)
        state = self.store.state()
        self.assertEqual(state["score"], 100)
        self.assertIn("n1-logs", state["completions"])
        self.assertIn("n1-ambiente", state["hints"])
        self.assertEqual(len(state["attempts"]), 2)
        self.assertEqual(state["audit"][0]["event"], "reset_progress")

    def test_rate_limit_is_persistent_across_reopen(self):
        for _ in range(20):
            self.store.submit(self.cid, "wrong", now=1000)
        reopened = Store(self.store.database, self.store.flag_hashes)
        with self.assertRaises(LabError) as error:
            reopened.submit(self.cid, self.flags[self.cid], now=1001)
        self.assertEqual(error.exception.status, 429)
        self.assertTrue(reopened.submit(self.cid, self.flags[self.cid], now=1061)["correct"])

    def test_planned_challenge_rejected(self):
        with self.assertRaises(LabError) as error:
            self.store.submit("n2-hub", "text")
        self.assertEqual(error.exception.status, 409)

    def test_concurrent_completions_award_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.store.submit(self.cid, self.flags[self.cid]), range(8)))
        self.assertEqual(sum(r["new_completion"] for r in results), 1)
        self.assertEqual(self.store.state()["score"], 100)

    def test_seed_mismatch_fails_closed(self):
        changed = dict(self.store.flag_hashes)
        changed[self.cid] = "a" * 64
        with self.assertRaises(ValueError):
            Store(self.store.database, changed)

    def test_catalog_does_not_expose_answers_or_hints(self):
        for c in public_catalog()["challenges"]:
            self.assertNotIn("hints", c)
            self.assertNotIn("solution", c)
            self.assertNotIn("flag", c)


class APITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store, self.flags = fixture(self.tmp.name)
        self.token = secrets.token_urlsafe(48)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store, self.token))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def request(self, path, payload=None, auth=True, raw=None, content_type="application/json"):
        headers = {"Content-Type": content_type}
        if auth:
            headers["Authorization"] = "Bearer " + self.token
        data = raw if raw is not None else None if payload is None else json.dumps(payload).encode()
        req = Request(self.base + path, data=data, headers=headers, method="GET" if data is None else "POST")
        try:
            with urlopen(req, timeout=5) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_health_only_is_unauthenticated(self):
        self.assertEqual(self.request("/health", auth=False)[0], 200)
        self.assertEqual(self.request("/api/state", auth=False)[0], 401)
        self.assertEqual(self.request("/api/catalog", auth=False)[0], 401)

    def test_submission_state_and_solution_round_trip(self):
        self.assertEqual(self.request("/api/solution/n1-arquivos")[0], 403)
        code, result = self.request("/api/submit", {"challenge": "n1-arquivos", "flag": self.flags["n1-arquivos"]})
        self.assertEqual(code, 200)
        self.assertTrue(result["correct"])
        self.assertEqual(self.request("/api/state")[1]["score"], 100)
        self.assertEqual(self.request("/api/solution/n1-arquivos")[0], 200)

    def test_input_and_size_validation(self):
        self.assertEqual(self.request("/api/submit", raw=b"{bad")[0], 400)
        self.assertEqual(self.request("/api/submit", raw=b"[]")[0], 400)
        self.assertEqual(self.request("/api/submit", raw=b"x" * 8193)[0], 413)
        self.assertEqual(self.request("/api/submit", raw=b"{}", content_type="text/plain")[0], 415)
        self.assertEqual(self.request("/api/submit", {"challenge": "n1-arquivos", "flag": 3})[0], 400)
        self.assertEqual(self.request("/api/submit", {"challenge": "n1-arquivos", "flag": "x" * 257})[0], 400)

    def test_no_admin_or_command_endpoint(self):
        self.assertEqual(self.request("/api/exec", {"challenge": "n1-arquivos", "command": "id"})[0], 404)
        self.assertEqual(self.request("/api/reset", {"challenge": "n1-arquivos"})[0], 404)
        self.assertEqual(self.request("/api/state?token=ignored", auth=False)[0], 401)

    def test_planned_and_unknown(self):
        self.assertEqual(self.request("/api/submit", {"challenge": "n2-hub", "flag": "wrong"})[0], 409)
        self.assertEqual(self.request("/api/hint", {"challenge": "invalid"})[0], 404)


class ProvisionTest(unittest.TestCase):
    def test_init_is_private_idempotent_and_matches_contexts(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            self.assertTrue(initialize(base))
            hashes = json.loads((base / ".private/flag_hashes.json").read_text())
            before = (base / ".private/api_token").read_bytes()
            self.assertFalse(initialize(base))
            self.assertEqual(before, (base / ".private/api_token").read_bytes())
            self.assertEqual((base / ".private").stat().st_mode & 0o777, 0o700)
            self.assertEqual((base / ".env").stat().st_mode & 0o777, 0o600)
            seed = base / ".delivery/practice-seed.tar.gz"
            self.assertEqual(seed.stat().st_mode & 0o777, 0o600)
            contexts = read_contexts(seed)
            self.assertEqual(set(contexts), {"files", "logs", "environment"})
            import io, tarfile
            for service, cid in [("files", "n1-arquivos"), ("logs", "n1-logs"), ("environment", "n1-ambiente")]:
                with tarfile.open(fileobj=io.BytesIO(contexts[service])) as tar:
                    if service == "environment":
                        text = tar.extractfile("Dockerfile").read().decode()
                        flag = next(line.split("=", 1)[1] for line in text.splitlines() if line.startswith("ENV "))
                    else:
                        flag = tar.extractfile("flag.txt").read().decode().strip()
                    self.assertEqual(hashlib.sha256(flag.encode()).hexdigest(), hashes[cid])

    def test_partial_init_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / ".env").write_text("existing")
            with self.assertRaises(ValueError):
                initialize(directory)

    def test_private_directory_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as target:
            (Path(directory) / ".private").symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                initialize(directory)


if __name__ == "__main__":
    unittest.main()
