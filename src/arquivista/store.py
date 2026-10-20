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
  -- Fila bot→planilha: uma linha por cadastro, sempre com a última versão (a mais nova substitui).
  CREATE TABLE IF NOT EXISTS sheet_outbox(guild_id TEXT NOT NULL,record_id TEXT NOT NULL,revision INTEGER NOT NULL,
    payload TEXT NOT NULL,tries INTEGER NOT NULL DEFAULT 0,next_try REAL NOT NULL DEFAULT 0,error TEXT,
    PRIMARY KEY(guild_id,record_id));
'''
# Colunas acrescentadas depois da primeira versão do banco; ALTER TABLE preserva o que já existe.
COLUMNS = {"guilds": (("sheet_url", "TEXT"), ("sheet_key", "TEXT"), ("sheet_error", "TEXT"), ("sheet_ok", "TEXT"),
                      ("backup_channel", "TEXT"), ("backup_hours", "INTEGER"), ("backup_next", "REAL"), ("backup_error", "TEXT"))}

SHEET_FIELDS = ("id", "owner_id", "appearance", "work", "server_name", "status", "justification", "image_url", "date", "revision")

def sheet_upsert(record: dict) -> dict:
    """Pedido da planilha para um cadastro. media_ref fica no banco; a planilha só precisa do link."""
    return {"op": "upsert", "record": {k: record[k] for k in SHEET_FIELDS}}

class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        for table, columns in COLUMNS.items():
            have = {r[1] for r in self.db.execute(f"PRAGMA table_info({table})")}
            for name, kind in columns:
                if name not in have:
                    self.db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")
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
            return {"guild_id": str(guild_id), "staff_roles": [], "log_channel": None, "image_channel": None,
                    "sheet_url": None, "sheet_key": None, "sheet_error": None, "sheet_ok": None,
                    "backup_channel": None, "backup_hours": None, "backup_next": None, "backup_error": None}
        data = dict(row)
        data["staff_roles"] = [str(x) for x in json.loads(data["staff_roles"])]
        return data
    def set_guild(self, guild_id: int | str, **fields) -> None:
        allowed = {"staff_roles", "log_channel", "image_channel", "sheet_url", "sheet_key", "sheet_error", "sheet_ok",
                   "backup_channel", "backup_hours", "backup_next", "backup_error"}
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
    # ---- fila bot→planilha
    def queue_sheet(self, guild_id: str, record_id: str, revision: int, op: dict) -> None:
        """Sem commit: roda dentro da transação da gravação do cadastro."""
        self.db.execute("INSERT OR REPLACE INTO sheet_outbox(guild_id,record_id,revision,payload) VALUES(?,?,?,?)",
                        (str(guild_id), record_id, revision, json.dumps(op, ensure_ascii=False)))
    def queue_full_sync(self, guild_id: str) -> int:
        """Planilha recém-conectada: manda todos os cadastros do servidor."""
        rows = self.db.execute("SELECT * FROM appearances WHERE guild_id=? ORDER BY created", (str(guild_id),)).fetchall()
        with self.db:
            for r in rows:
                self.queue_sheet(guild_id, r["id"], r["revision"], sheet_upsert(dict(r)))
        return len(rows)
    # ---- backup periódico
    def backup_due(self) -> list[str]:
        rows = self.db.execute("SELECT guild_id FROM guilds WHERE backup_channel IS NOT NULL AND COALESCE(backup_next,0)<=?",
                               (time.time(),)).fetchall()
        return [r[0] for r in rows]
    def records(self, guild_id: str) -> list[dict]:
        rows = self.db.execute("SELECT * FROM appearances WHERE guild_id=? ORDER BY owner_id,created", (str(guild_id),)).fetchall()
        return [dict(r) for r in rows]
    def sheet_due(self) -> list[str]:
        rows = self.db.execute("SELECT DISTINCT o.guild_id FROM sheet_outbox o JOIN guilds g ON g.guild_id=o.guild_id "
                               "WHERE o.next_try<=? AND g.sheet_url IS NOT NULL", (time.time(),)).fetchall()
        return [r[0] for r in rows]
    def sheet_batch(self, guild_id: str, limit: int = 50) -> list[dict]:
        # rowid crescente = ordem das mudanças (INSERT OR REPLACE dá rowid novo à versão mais recente).
        rows = self.db.execute("SELECT * FROM sheet_outbox WHERE guild_id=? AND next_try<=? ORDER BY rowid LIMIT ?",
                               (str(guild_id), time.time(), limit)).fetchall()
        return [dict(r) for r in rows]
    def sheet_done(self, guild_id: str, record_id: str, revision: int) -> None:
        # Só apaga se nada mais novo entrou na fila enquanto o envio estava em andamento.
        with self.db:
            self.db.execute("DELETE FROM sheet_outbox WHERE guild_id=? AND record_id=? AND revision=?",
                            (str(guild_id), record_id, revision))
    def sheet_retry(self, guild_id: str, record_ids: list[str], error: str | None = None, long: bool = False) -> None:
        with self.db:
            for rid in record_ids:
                row = self.db.execute("SELECT tries FROM sheet_outbox WHERE guild_id=? AND record_id=?", (str(guild_id), rid)).fetchone()
                if not row:
                    continue
                delay = 6 * 3600 if long else min(3600, 30 * 2 ** min(row[0], 7))
                self.db.execute("UPDATE sheet_outbox SET tries=tries+1,next_try=?,error=? WHERE guild_id=? AND record_id=?",
                                (time.time() + delay, error, str(guild_id), rid))
    def sheet_pending(self, guild_id: str) -> tuple[int, int]:
        """(na fila, com erro de dado que não vai resolver sozinho)."""
        total = self.db.execute("SELECT COUNT(*) FROM sheet_outbox WHERE guild_id=?", (str(guild_id),)).fetchone()[0]
        bad = self.db.execute("SELECT COUNT(*) FROM sheet_outbox WHERE guild_id=? AND error='invalid'", (str(guild_id),)).fetchone()[0]
        return total, bad
    def drop_sheet(self, guild_id: str) -> None:
        with self.db:
            self.db.execute("DELETE FROM sheet_outbox WHERE guild_id=?", (str(guild_id),))
            self.db.execute("UPDATE guilds SET sheet_url=NULL,sheet_key=NULL,sheet_error=NULL,sheet_ok=NULL WHERE guild_id=?", (str(guild_id),))
    # ---- mensagens da própria Amiya (respostas a ela recebem a saudação)
    def remember(self, message_id: int) -> None:
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO messages VALUES(?,?)", (str(message_id), time.time()))
            self.db.execute("DELETE FROM messages WHERE created<?", (time.time()-7*86400,))
    def is_ours(self, message_id: int) -> bool:
        return bool(self.db.execute("SELECT 1 FROM messages WHERE id=?", (str(message_id),)).fetchone())
    def close(self):
        self.db.close()
