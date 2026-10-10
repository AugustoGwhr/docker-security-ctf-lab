"""SQLite transacional: pontuação, dicas e auditoria sem armazenar flags submetidas."""
import hashlib
import hmac
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from backend.catalog import ACTIVE_IDS, INDEX


class LabError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Store:
    def __init__(self, database, flag_hashes):
        self.database = str(database)
        self.flag_hashes = flag_hashes
        if set(flag_hashes) != ACTIVE_IDS:
            raise ValueError("Conjunto de hashes não corresponde aos desafios ativos; execute init_lab.py.")
        if any(not isinstance(v, str) or len(v) != 64 or any(x not in '0123456789abcdef' for x in v) for v in flag_hashes.values()):
            raise ValueError("Hashes SHA-256 inválidos.")
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY, challenge TEXT NOT NULL,
                    timestamp REAL NOT NULL, success INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS attempt_time ON attempts(timestamp);
                CREATE TABLE IF NOT EXISTS completions (
                    challenge TEXT PRIMARY KEY, points INTEGER NOT NULL,
                    timestamp REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS hints (
                    challenge TEXT NOT NULL, number INTEGER NOT NULL,
                    timestamp REAL NOT NULL, PRIMARY KEY(challenge, number));
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY, challenge TEXT NOT NULL,
                    event TEXT NOT NULL, timestamp REAL NOT NULL);
            """)
            signature = hashlib.sha256(str(sorted(flag_hashes.items())).encode()).hexdigest()
            db.execute("CREATE TABLE IF NOT EXISTS metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
            old = db.execute("SELECT value FROM metadata WHERE name='seed' ").fetchone()
            if old and old[0] != signature:
                raise ValueError("Seed mudou com progresso existente. Restaure a configuração original ou inicie uma implantação separada.")
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('seed', ?)", (signature,))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def challenge(cid):
        if cid not in INDEX:
            raise LabError(404, "Desafio desconhecido.")
        if cid not in ACTIVE_IDS:
            raise LabError(409, "Módulo planejado; a validação ainda não está disponível.")
        return INDEX[cid]

    def submit(self, cid, flag, now=None):
        c = self.challenge(cid)
        if not isinstance(flag, str) or len(flag) > 256:
            raise LabError(400, "Envie uma flag de até 256 caracteres.")
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT COUNT(*) FROM attempts WHERE timestamp > ?", (now - 60,)).fetchone()[0]
            if count >= 20:
                raise LabError(429, "Limite de 20 tentativas por minuto. Aguarde e revise as dicas.")
            digest = hashlib.sha256(flag.strip().encode()).hexdigest()
            correct = hmac.compare_digest(digest, self.flag_hashes[cid])
            db.execute("INSERT INTO attempts(challenge,timestamp,success) VALUES (?,?,?)", (cid, now, int(correct)))
            if not correct:
                return {"correct": False, "message": "Flag incorreta. Confira o desafio e copie o valor completo, incluindo CTF{...}."}
            completed = db.execute("SELECT points FROM completions WHERE challenge=?", (cid,)).fetchone()
            if completed:
                return {"correct": True, "points": completed[0], "new_completion": False, "message": "Desafio já concluído; a pontuação foi preservada."}
            hint_count = db.execute("SELECT COUNT(*) FROM hints WHERE challenge=?", (cid,)).fetchone()[0]
            points = max(c["points"] // 2, c["points"] - hint_count * 10)
            db.execute("INSERT INTO completions VALUES (?,?,?)", (cid, points, now))
            return {"correct": True, "points": points, "new_completion": True, "message": f"Desafio concluído! +{points} pontos."}

    def hint(self, cid):
        c = self.challenge(cid)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT COUNT(*) FROM hints WHERE challenge=?", (cid,)).fetchone()[0]
            complete = db.execute("SELECT 1 FROM completions WHERE challenge=?", (cid,)).fetchone()
            if complete:
                return {"hints": c["hints"], "remaining": 0, "penalty": 0, "message": "Concluído: dicas liberadas sem alterar pontos."}
            if count < len(c["hints"]):
                db.execute("INSERT INTO hints VALUES (?,?,?)", (cid, count + 1, time.time()))
                count += 1
            return {"hints": c["hints"][:count], "remaining": len(c["hints"]) - count, "penalty": count * 10}

    def state(self):
        with self.connect() as db:
            completions = {r["challenge"]: dict(r) for r in db.execute("SELECT * FROM completions")}
            hints = {r["challenge"]: INDEX[r["challenge"]]["hints"][:r["n"]] for r in db.execute("SELECT challenge, COUNT(*) AS n FROM hints GROUP BY challenge")}
            attempts = [dict(r) for r in db.execute("SELECT challenge, timestamp, success FROM attempts ORDER BY id DESC LIMIT 100")]
            resets = [dict(r) for r in db.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 20")]
        n = len(completions)
        return {
            "completions": completions, "hints": hints, "attempts": attempts,
            "audit": resets, "score": sum(c["points"] for c in completions.values()),
            "completed": n, "total": len(ACTIVE_IDS),
            "max_score": sum(INDEX[c]["points"] for c in ACTIVE_IDS),
            "achievements": (["Primeira flag"] if n else []) + (["Fundamentos iniciais concluídos"] if n == len(ACTIVE_IDS) else []),
        }

    def solution(self, cid):
        c = self.challenge(cid)
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM completions WHERE challenge=?", (cid,)).fetchone():
                raise LabError(403, "A explicação completa é liberada após a conclusão.")
        return {"explanation": c["solution"]}

    def reset(self, cid):
        self.challenge(cid)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM completions WHERE challenge=?", (cid,))
            db.execute("DELETE FROM hints WHERE challenge=?", (cid,))
            db.execute("INSERT INTO audit(challenge,event,timestamp) VALUES (?,?,?)", (cid, "reset_progress", time.time()))

    def backup(self, destination):
        if Path(destination).resolve() == Path(self.database).resolve():
            raise ValueError("O backup deve ter um caminho diferente do banco.")
        with self.connect() as source, sqlite3.connect(destination) as target:
            source.backup(target)
