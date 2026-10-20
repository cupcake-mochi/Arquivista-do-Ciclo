"""Arquivo de aparências de um servidor, guardado no banco do bot.

Mesmas ações e códigos de erro da ponte do Apps Script (`list`, `get`, `create`...),
para as telas não precisarem saber de onde vêm os dados. Cada servidor só enxerga
os próprios cadastros: toda consulta é filtrada por `guild_id`.
"""
from __future__ import annotations
import hashlib
import json
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .domain import Actor, BridgeError, ERRORS, STATUSES, exact_key, normalized, public_record
from .store import Store

FIELDS = ("id", "owner_id", "appearance", "work", "server_name", "status", "justification",
          "image_url", "media_ref", "date", "revision")
MAX_PER_MEMBER = 200  # o mesmo teto de posições da planilha
MEDIA_REF = re.compile(r"^discord://(\d{17,20})/(\d{17,20})/(\d{17,20})/(\d{17,20})$")
URL = re.compile(r"^https://([^/?#\s]+)\S*$", re.I)

def fail(code: str, message: str | None = None):
    raise BridgeError(code, message or ERRORS.get(code, ERRORS["INTERNAL"]))

def text(value, limit: int, required: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", value):
        fail("INVALID")
    value = value.strip()
    if required and not value:
        fail("INVALID")
    return value

def url(value) -> str:
    # Mesma regra da ponte; a checagem completa (IP privado etc.) já roda no formulário.
    value = text(value or "", 1500)
    if not value:
        return ""
    m = URL.match(value)
    host = (m[1].lower().rstrip(".") if m else "")
    if (not m or "@" in host or ":" in host or "." not in host or re.fullmatch(r"[\d.]+", host)
            or re.search(r"(^|\.)(localhost|local|internal)$", host)
            or (host in ("discord.com", "discordapp.com") and "/api/webhooks/" in value)):
        fail("INVALID")
    return value

class Archive:
    def __init__(self, store: Store, guild_id: int | str, tz: str = "America/Sao_Paulo"):
        self.store, self.db, self.guild = store, store.db, str(guild_id)
        try:
            self.tz = ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError):
            self.tz = timezone.utc
    async def call(self, action: str, actor: Actor, data: dict | None = None, request_id: str | None = None) -> dict:
        # SQLite local responde em milissegundos; não precisa de thread separada.
        return self.run(action, actor, data or {}, request_id or str(uuid.uuid4()))
    def run(self, action: str, actor: Actor, d: dict, rid: str) -> dict:
        if action == "status":
            if not actor.staff: fail("FORBIDDEN")
            return self.status()
        if action == "list":
            owner = str(d.get("owner_id") or "")
            if owner and not owner.isdigit(): fail("INVALID")
            sql, args = "SELECT * FROM appearances WHERE guild_id=?", [self.guild]
            if owner:
                sql += " AND owner_id=?"; args.append(owner)
            if d.get("include_released") is not True:
                sql += " AND status<>'Liberado'"
            return {"records": [public_record(self.public(r)) for r in self.db.execute(sql, args)]}
        if action == "get":
            r = self.record(str(d.get("id", "")))
            if not actor.staff and r["owner_id"] != actor.id: fail("FORBIDDEN")
            return {"record": r}
        if action == "image":
            r = self.record(str(d.get("id", "")))
            if r["status"] == "Liberado" and not actor.staff and actor.id != r["owner_id"]: fail("NOT_FOUND")
            return {"url": r["image_url"], "media_ref": r["media_ref"]}
        if action == "refresh_image":
            # Link de anexo do Discord expira; só troca a URL, sem evento nem nova revisão.
            if not actor.staff: fail("FORBIDDEN")
            r = self.record(str(d.get("id", "")))
            if not r["media_ref"] or r["media_ref"] != d.get("media_ref"): fail("STALE")
            with self.db:
                self.db.execute("UPDATE appearances SET image_url=? WHERE guild_id=? AND id=?", (url(d.get("url")), self.guild, r["id"]))
            return {}
        if action == "history":
            if not actor.staff: fail("FORBIDDEN")
            return self.history(str(d.get("query") or ""))
        if action not in ("create", "edit", "change_status", "transfer", "remove"): fail("INVALID")
        if action in ("change_status", "transfer", "remove") and not actor.staff: fail("FORBIDDEN")
        return self.mutate(action, actor, d, rid)
    # ---------------- leituras
    def public(self, row) -> dict:
        r = dict(row)
        r["occupied"] = r["status"] != "Liberado"
        return r
    def record(self, record_id: str) -> dict:
        row = self.db.execute("SELECT * FROM appearances WHERE guild_id=? AND id=?", (self.guild, record_id)).fetchone()
        if not row: fail("NOT_FOUND")
        return {k: row[k] for k in FIELDS}
    def status(self) -> dict:
        one = lambda sql: self.db.execute(sql, (self.guild,)).fetchone()[0]
        return {"records": one("SELECT COUNT(*) FROM appearances WHERE guild_id=?"),
                "occupied": one("SELECT COUNT(*) FROM appearances WHERE guild_id=? AND status<>'Liberado'"),
                "members": one("SELECT COUNT(DISTINCT owner_id) FROM appearances WHERE guild_id=?"),
                "events": one("SELECT COUNT(*) FROM events WHERE guild_id=?"),
                "pending_notices": one("SELECT COUNT(*) FROM notices WHERE guild_id=? AND sent=0")}
    def history(self, query: str) -> dict:
        q = normalized(query)
        if len(q) > 200: fail("INVALID")
        found = []
        for row in self.db.execute("SELECT * FROM events WHERE guild_id=? ORDER BY seq DESC", (self.guild,)):
            e = self.event(row)
            if not q or any(r and (normalized(r.get("id")) == q or q in normalized(f"{r.get('appearance','')} {r.get('work','')}"))
                            for r in (e["before"], e["after"])):
                found.append(e)
                if len(found) > 200:
                    break
        return {"events": found[:200], "truncated": len(found) > 200}
    def event(self, row) -> dict:
        e = dict(row)
        e["before"] = json.loads(e["before"]) if e["before"] else None
        e["after"] = json.loads(e["after"]) if e["after"] else None
        return e
    # ---------------- gravações
    def fields(self, raw) -> dict:
        if not isinstance(raw, dict) or set(raw) - {"appearance", "server_name", "work", "image_url", "media_ref"}:
            fail("INVALID")
        media = raw.get("media_ref") or ""
        if media:
            m = MEDIA_REF.match(media) if isinstance(media, str) else None
            # A imagem precisa ter sido guardada num canal deste mesmo servidor.
            if not m or m[1] != self.guild: fail("INVALID")
        return {"appearance": text(raw.get("appearance"), 100, True), "work": text(raw.get("work"), 100, True),
                "server_name": text(raw.get("server_name") or "", 100), "image_url": url(raw.get("image_url") or ""),
                "media_ref": media}
    def room(self, owner_id: str) -> None:
        used = self.db.execute("SELECT COUNT(*) FROM appearances WHERE guild_id=? AND owner_id=? AND status<>'Liberado'",
                               (self.guild, owner_id)).fetchone()[0]
        if used >= MAX_PER_MEMBER:
            fail("CAPACITY", f"Esse membro já ocupa {MAX_PER_MEMBER} aparências neste servidor. Libere alguma antes de cadastrar outra.")
    def taken(self, r: dict) -> bool:
        if r["status"] == "Liberado":
            return False
        return bool(self.db.execute("SELECT 1 FROM appearances WHERE guild_id=? AND key=? AND id<>? AND status<>'Liberado'",
                                    (self.guild, exact_key(r["appearance"], r["work"]), r["id"])).fetchone())
    def mutate(self, action: str, actor: Actor, d: dict, rid: str) -> dict:
        digest = hashlib.sha256(json.dumps([action, self.guild, actor.id, actor.staff, d],
                                           ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        saved = self.db.execute("SELECT digest,result FROM requests WHERE guild_id=? AND request_id=?", (self.guild, rid)).fetchone()
        if saved:
            # Repetir a mesma confirmação devolve o resultado original sem gravar de novo.
            if saved["digest"] != digest: fail("REUSED_REQUEST")
            return json.loads(saved["result"])
        before = after = None
        if action == "create":
            owner = d.get("owner") or actor.wire()
            if not isinstance(owner, dict) or not str(owner.get("id", "")).isdigit(): fail("INVALID")
            owner_id = str(owner["id"])
            if not actor.staff and owner_id != actor.id: fail("FORBIDDEN")
            self.room(owner_id)
            after = {"id": "AP-" + str(uuid.uuid4()), "owner_id": owner_id, **self.fields(d.get("fields")),
                     "status": "Em preparação", "justification": "",
                     "date": datetime.now(self.tz).date().isoformat(), "revision": 1}
        else:
            before = self.record(str(d.get("id", "")))
            if not actor.staff and before["owner_id"] != actor.id: fail("FORBIDDEN")
            if d.get("revision") != before["revision"]: fail("STALE")
            after = dict(before)
            if action == "edit":
                patch = d.get("fields") or {}
                if not isinstance(patch, dict): fail("INVALID")
                if not actor.staff and any(k in patch for k in ("appearance", "work")): fail("FORBIDDEN")
                clear = patch.get("clear_image", False)
                if not isinstance(clear, bool): fail("INVALID")
                patch = {k: v for k, v in patch.items() if k != "clear_image"}
                merged = self.fields({**{k: before[k] for k in ("appearance", "work", "server_name", "image_url", "media_ref")}, **patch})
                if "image_url" in patch and "media_ref" not in patch:
                    merged["media_ref"] = ""
                after.update(merged)
                if clear:
                    after["image_url"] = after["media_ref"] = ""
            elif action == "change_status":
                if d.get("status") not in STATUSES: fail("INVALID")
                after["status"] = d["status"]
                after["justification"] = text(d.get("justification") or "", 2000)
            elif action == "transfer":
                owner = d.get("owner")
                if not isinstance(owner, dict) or not str(owner.get("id", "")).isdigit() or str(owner["id"]) == before["owner_id"]:
                    fail("INVALID")
                after["owner_id"] = str(owner["id"])
                if after["status"] != "Liberado":
                    self.room(after["owner_id"])
            elif action == "remove":
                after = None
        if after and self.taken(after): fail("DUPLICATE")
        changed = before is None or after is None or any(before[k] != after[k] for k in FIELDS if k != "revision")
        if changed and before and after:
            after["revision"] = before["revision"] + 1
        result = {"changed": changed, "record": after, "removed_id": "" if after else before["id"]}
        now = time.time()
        try:
            with self.db:
                if changed:
                    self.write(before, after, now)
                    self.log(action, rid, actor, before, after, "discord")
                self.db.execute("INSERT INTO requests VALUES(?,?,?,?,?)",
                                (self.guild, rid, digest, json.dumps(result, ensure_ascii=False), now))
        except sqlite3.IntegrityError:
            # Duas confirmações simultâneas da mesma aparência: o índice único decide.
            fail("DUPLICATE")
        return result
    def write(self, before, after, now) -> None:
        if after is None:
            self.db.execute("DELETE FROM appearances WHERE guild_id=? AND id=?", (self.guild, before["id"]))
            return
        key = exact_key(after["appearance"], after["work"])
        if before is None:
            self.db.execute("INSERT INTO appearances(id,guild_id,owner_id,appearance,work,key,server_name,status,justification,"
                            "image_url,media_ref,date,revision,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (after["id"], self.guild, after["owner_id"], after["appearance"], after["work"], key,
                             after["server_name"], after["status"], after["justification"], after["image_url"],
                             after["media_ref"], after["date"], after["revision"], now, now))
        else:
            self.db.execute("UPDATE appearances SET owner_id=?,appearance=?,work=?,key=?,server_name=?,status=?,justification=?,"
                            "image_url=?,media_ref=?,revision=?,updated=? WHERE guild_id=? AND id=?",
                            (after["owner_id"], after["appearance"], after["work"], key, after["server_name"], after["status"],
                             after["justification"], after["image_url"], after["media_ref"], after["revision"], now,
                             self.guild, after["id"]))
    def log(self, kind, rid, actor, before, after, source) -> None:
        """Auditoria e aviso no canal de histórico no mesmo commit da gravação."""
        event_id = "EV-" + str(uuid.uuid4())
        at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        cur = self.db.execute("INSERT INTO events(event_id,guild_id,request_id,at,kind,record_id,actor_id,source,before,after)"
                              " VALUES(?,?,?,?,?,?,?,?,?,?)",
                              (event_id, self.guild, rid, at, kind, (after or before)["id"], actor.id, source,
                               json.dumps(before, ensure_ascii=False) if before else None,
                               json.dumps(after, ensure_ascii=False) if after else None))
        if not self.store.guild(self.guild).get("log_channel"):
            return  # sem canal configurado não há aviso; ligar o canal depois não republica o passado
        r = after or before
        notice = {"seq": cur.lastrowid, "event_id": event_id, "at": at,
                  "kind": {"create": "created", "remove": "removed", "transfer": "transferred"}.get(kind, "updated"),
                  "appearance": r["appearance"], "work": r["work"], "owner_id": r["owner_id"],
                  "actor_id": actor.id, "source": source}
        self.db.execute("INSERT INTO notices(event_id,guild_id,seq,data) VALUES(?,?,?,?)",
                        (event_id, self.guild, cur.lastrowid, json.dumps(notice, ensure_ascii=False)))
