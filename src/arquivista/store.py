"""Estado operacional local; a auditoria canônica fica no Sheets privado."""
from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path

class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
          PRAGMA journal_mode=WAL;
          PRAGMA busy_timeout=5000;
          CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS outbox(event_id TEXT PRIMARY KEY,seq INTEGER NOT NULL,
            data TEXT NOT NULL,sent INTEGER NOT NULL DEFAULT 0,tries INTEGER NOT NULL DEFAULT 0,
            next_try REAL NOT NULL DEFAULT 0,message_id TEXT,channel_id TEXT);
          CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,created REAL NOT NULL);
        ''')
        self.db.commit()
    def get(self, key: str, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default
    def set(self, key: str, value):
        with self.db:
            self.db.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                            (key, json.dumps(value, ensure_ascii=False)))
    def ingest(self, events: list[dict], cursor: int) -> None:
        """Cursor e fila no mesmo commit: reiniciar não pula um evento observado."""
        with self.db:
            self.db.executemany("INSERT OR IGNORE INTO outbox(event_id,seq,data) VALUES(?,?,?)",
                                [(e["event_id"], e["seq"], json.dumps(e, ensure_ascii=False)) for e in events])
            self.db.execute("INSERT INTO settings VALUES('cursor',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(cursor),))
    def pending(self) -> list[dict]:
        rows = self.db.execute("SELECT * FROM outbox WHERE sent=0 AND next_try<=? ORDER BY seq LIMIT 20", (time.time(),)).fetchall()
        return [dict(r) for r in rows]
    def delivered(self, event_id: str, message_id: str = "", channel_id: str = "") -> None:
        with self.db:
            self.db.execute("UPDATE outbox SET sent=1,message_id=?,channel_id=? WHERE event_id=?", (message_id, channel_id, event_id))
    def attempt(self, event_id: str) -> None:
        # Persistir ANTES da chamada externa permite reconhecer uma tentativa interrompida.
        with self.db:
            self.db.execute("UPDATE outbox SET tries=tries+1 WHERE event_id=?", (event_id,))
    def failed(self, event_id: str, tries: int) -> None:
        delay = min(3600, 15 * 2 ** min(tries, 8))
        with self.db:
            self.db.execute("UPDATE outbox SET next_try=? WHERE event_id=?", (time.time()+delay, event_id))
    def remember(self, message_id: int) -> None:
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO messages VALUES(?,?)", (str(message_id), time.time()))
            self.db.execute("DELETE FROM messages WHERE created<?", (time.time()-7*86400,))
    def is_ours(self, message_id: int) -> bool:
        return bool(self.db.execute("SELECT 1 FROM messages WHERE id=?", (str(message_id),)).fetchone())
    def close(self):
        self.db.close()
