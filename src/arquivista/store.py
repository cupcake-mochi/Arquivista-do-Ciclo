"""Banco local (SQLite/WAL): cadastros, auditoria e configuração de cada servidor."""
from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path

SCHEMA = '''
  PRAGMA journal_mode=WAL;
  PRAGMA busy_timeout=5000;
  PRAGMA foreign_keys=ON;
  CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,created REAL NOT NULL);
  CREATE TABLE IF NOT EXISTS guilds(guild_id TEXT PRIMARY KEY,
    staff_roles TEXT NOT NULL DEFAULT '[]',log_channel TEXT,image_channel TEXT,
    created REAL NOT NULL,updated REAL NOT NULL);
  CREATE TABLE IF NOT EXISTS appearances(id TEXT PRIMARY KEY,guild_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,appearance TEXT NOT NULL,work TEXT NOT NULL,key TEXT NOT NULL,
    server_name TEXT NOT NULL DEFAULT '',status TEXT NOT NULL,justification TEXT NOT NULL DEFAULT '',
    image_url TEXT NOT NULL DEFAULT '',media_ref TEXT NOT NULL DEFAULT '',date TEXT,
    revision INTEGER NOT NULL DEFAULT 1,created REAL NOT NULL,updated REAL NOT NULL);
  CREATE INDEX IF NOT EXISTS appearances_owner ON appearances(guild_id,owner_id);
  -- Aparência + obra ocupada uma vez por servidor; Liberado não ocupa (Arquivado ocupa).
  CREATE UNIQUE INDEX IF NOT EXISTS appearances_taken ON appearances(guild_id,key) WHERE status<>'Liberado';
  CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,
    guild_id TEXT NOT NULL,request_id TEXT NOT NULL DEFAULT '',at TEXT NOT NULL,kind TEXT NOT NULL,
    record_id TEXT NOT NULL,actor_id TEXT NOT NULL DEFAULT '',source TEXT NOT NULL,
    before TEXT,after TEXT);
  CREATE INDEX IF NOT EXISTS events_guild ON events(guild_id,seq);
  CREATE TABLE IF NOT EXISTS requests(guild_id TEXT NOT NULL,request_id TEXT NOT NULL,
    digest TEXT NOT NULL,result TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(guild_id,request_id));
  CREATE TABLE IF NOT EXISTS notices(event_id TEXT PRIMARY KEY,guild_id TEXT NOT NULL,seq INTEGER NOT NULL,
    data TEXT NOT NULL,sent INTEGER NOT NULL DEFAULT 0,tries INTEGER NOT NULL DEFAULT 0,
    next_try REAL NOT NULL DEFAULT 0,message_id TEXT,channel_id TEXT);
'''

class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()
    # ---- valores globais do processo (ex.: hash do avatar)
    def get(self, key: str, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default
    def set(self, key: str, value):
        with self.db:
            self.db.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                            (key, json.dumps(value, ensure_ascii=False)))
    # ---- configuração por servidor
    def guild(self, guild_id: int | str) -> dict:
        row = self.db.execute("SELECT * FROM guilds WHERE guild_id=?", (str(guild_id),)).fetchone()
        if not row:
            return {"guild_id": str(guild_id), "staff_roles": [], "log_channel": None, "image_channel": None}
        data = dict(row)
        data["staff_roles"] = [str(x) for x in json.loads(data["staff_roles"])]
        return data
    def set_guild(self, guild_id: int | str, **fields) -> None:
        allowed = {"staff_roles", "log_channel", "image_channel"}
        if not fields or set(fields) - allowed:
            raise ValueError("campo de servidor desconhecido")
        if "staff_roles" in fields:
            fields["staff_roles"] = json.dumps(sorted({str(x) for x in fields["staff_roles"]}))
        now = time.time()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO guilds(guild_id,created,updated) VALUES(?,?,?)", (str(guild_id), now, now))
            sets = ",".join(f"{k}=?" for k in fields)
            self.db.execute(f"UPDATE guilds SET {sets},updated=? WHERE guild_id=?",
                            (*[None if v is None else str(v) if k != "staff_roles" else v for k, v in fields.items()], now, str(guild_id)))
    def adopt_legacy(self, guild_id: int, staff_roles) -> bool:
        """v0.2 (um servidor só) guardava canais em settings e cargos no .env: leva para o servidor uma única vez."""
        if self.db.execute("SELECT 1 FROM guilds WHERE guild_id=?", (str(guild_id),)).fetchone():
            return False
        self.set_guild(guild_id, staff_roles=list(staff_roles),
                       log_channel=self.get("log_channel"), image_channel=self.get("image_channel"))
        return True
    # ---- notificações no canal de histórico (fila durável)
    def pending(self) -> list[dict]:
        rows = self.db.execute("SELECT * FROM notices WHERE sent=0 AND next_try<=? ORDER BY seq LIMIT 20", (time.time(),)).fetchall()
        return [dict(r) for r in rows]
    def delivered(self, event_id: str, message_id: str = "", channel_id: str = "") -> None:
        with self.db:
            self.db.execute("UPDATE notices SET sent=1,message_id=?,channel_id=? WHERE event_id=?", (message_id, channel_id, event_id))
    def attempt(self, event_id: str) -> None:
        # Persistir ANTES da chamada externa permite reconhecer uma tentativa interrompida.
        with self.db:
            self.db.execute("UPDATE notices SET tries=tries+1 WHERE event_id=?", (event_id,))
    def failed(self, event_id: str, tries: int) -> None:
        delay = min(3600, 15 * 2 ** min(tries, 8))
        with self.db:
            self.db.execute("UPDATE notices SET next_try=? WHERE event_id=?", (time.time()+delay, event_id))
    # ---- mensagens da própria Amiya (respostas a ela recebem a saudação)
    def remember(self, message_id: int) -> None:
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO messages VALUES(?,?)", (str(message_id), time.time()))
            self.db.execute("DELETE FROM messages WHERE created<?", (time.time()-7*86400,))
    def is_ours(self, message_id: int) -> bool:
        return bool(self.db.execute("SELECT 1 FROM messages WHERE id=?", (str(message_id),)).fetchone())
    def close(self):
        self.db.close()
