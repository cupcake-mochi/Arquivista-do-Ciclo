"""Importação de um arquivo exportado da Planilha Aparências para o banco de um servidor.

Preserva ID, responsável, data (inclusive vazia) e situação. Não inventa histórico:
cada cadastro ganha um único evento `import`, e a auditoria do banco começa aí.
"""
from __future__ import annotations
from contextlib import nullcontext
import json
import re
import time
import uuid
from datetime import date, datetime, timedelta, timezone

from .domain import STATUSES, exact_key
from .store import Store, sheet_upsert

FORMAT = "arquivista-export"
ID = re.compile(r"^AP-[0-9a-fA-F-]{8,64}$")
SNOWFLAKE = re.compile(r"^\d{17,20}$")
SHEETS_EPOCH = date(1899, 12, 30)
LIMITS = {"appearance": 100, "work": 100, "server_name": 100, "justification": 2000, "image_url": 1500}

def as_date(value):
    """Número de série do Sheets ou texto AAAA-MM-DD; vazio continua vazio."""
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError
    if isinstance(value, (int, float)):
        return (SHEETS_EPOCH + timedelta(days=int(value))).isoformat()
    return date.fromisoformat(str(value)[:10]).isoformat()

def check(data: dict) -> tuple[list[dict], list[str], list[str]]:
    """Valida o arquivo inteiro. Devolve (cadastros, erros, avisos); com erro, nada é gravado."""
    errors, warnings, records = [], [], []
    if not isinstance(data, dict) or data.get("format") != FORMAT or data.get("version") != 1:
        return [], ["O arquivo não é uma exportação do Arquivista (format/version)."], []
    raw = data.get("records")
    if not isinstance(raw, list):
        return [], ["O arquivo não tem a lista de cadastros."], []
    seen, taken = set(), {}
    for n, r in enumerate(raw, 1):
        where = f"cadastro {n}"
        if not isinstance(r, dict):
            errors.append(f"{where}: formato inválido."); continue
        rid = str(r.get("id") or "").strip()
        where = f"{where} ({rid or 'sem ID'})"
        out = {"id": rid, "owner_id": str(r.get("owner_id") or "").strip()}
        for key, limit in LIMITS.items():
            value = r.get(key) or ""
            if not isinstance(value, str):
                value = str(value)
            value = value.replace(" ", " ").strip()
            if len(value) > limit:
                warnings.append(f"{where}: {key} com {len(value)} caracteres (o bot aceita até {limit} em novas edições).")
            out[key] = value
        out["status"] = str(r.get("status") or "").strip()
        # Backup do próprio bot traz o anexo guardado (para renovar o link) e a revisão (para a planilha).
        media = r.get("media_ref") or ""
        out["media_ref"] = media if isinstance(media, str) and re.fullmatch(r"discord://\d{17,20}/\d{17,20}/\d{17,20}/\d{17,20}", media) else ""
        rev = r.get("revision")
        out["revision"] = rev if isinstance(rev, int) and not isinstance(rev, bool) and rev >= 1 else 1
        if not ID.match(rid):
            errors.append(f"{where}: ID ausente ou fora do formato AP-…. Rode a revisão de IDs na planilha antes de exportar.")
        elif rid in seen:
            errors.append(f"{where}: ID repetido no arquivo.")
        seen.add(rid)
        if not SNOWFLAKE.match(out["owner_id"]):
            errors.append(f"{where}: responsável sem ID do Discord válido.")
        if not out["appearance"] or not out["work"]:
            errors.append(f"{where}: aparência e obra são obrigatórias.")
        if out["status"] not in STATUSES:
            errors.append(f"{where}: situação '{out['status']}' desconhecida.")
        if out["image_url"] and not out["image_url"].lower().startswith("https://"):
            warnings.append(f"{where}: imagem sem link HTTPS; importada sem imagem.")
            out["image_url"] = ""
        try:
            out["date"] = as_date(r.get("date"))
        except (ValueError, TypeError, OverflowError):
            errors.append(f"{where}: data inválida ({r.get('date')!r}).")
            out["date"] = None
        if out["appearance"] and out["work"] and out["status"] != "Liberado":
            key = exact_key(out["appearance"], out["work"])
            if key in taken:
                errors.append(f"{where}: '{out['appearance']}' de '{out['work']}' ocupada também por {taken[key]}. "
                              "Libere, arquive com outra grafia ou remova uma delas na planilha.")
            else:
                taken[key] = rid or where
        records.append(out)
    return records, errors, warnings

def summary(records: list[dict]) -> dict:
    by_status = {s: 0 for s in STATUSES}
    for r in records:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    return {"records": len(records), "members": len({r["owner_id"] for r in records}),
            "without_date": sum(1 for r in records if not r["date"]),
            "with_image": sum(1 for r in records if r["image_url"]), "status": by_status}

def apply(store: Store, guild_id: int | str, records: list[dict], actor_id: str = "", replace: bool = False, *, transaction: bool = True) -> int:
    """Grava tudo numa transação. Sem replace, recusa servidor que já tem cadastros, pra não misturar fontes.
    Com replace (restaurar backup pelo Discord), apaga os cadastros atuais do servidor no mesmo commit;
    a auditoria deles fica, com um evento de remoção cada, e a planilha conectada recebe a limpeza."""
    guild = str(guild_id)
    db = store.db
    if not replace and db.execute("SELECT 1 FROM appearances WHERE guild_id=? LIMIT 1", (guild,)).fetchone():
        raise ValueError("Este servidor já tem cadastros no banco. A importação só roda num servidor vazio.")
    clash = db.execute(f"SELECT id FROM appearances WHERE guild_id<>? AND id IN ({','.join('?'*len(records))})",
                       [guild] + [r["id"] for r in records]).fetchone() if records else None
    if clash:
        raise ValueError(f"O ID {clash[0]} já existe em outro servidor do banco. A planilha foi importada em outro lugar?")
    for r in records:
        if r.get("media_ref") and r["media_ref"].split("/")[2] != guild:
            r["media_ref"] = ""  # anexo de outro servidor: o bot daqui não consegue renovar o link
    now = time.time()
    at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    rid = "import-" + str(uuid.uuid4())
    connected = bool(store.guild(guild).get("sheet_url"))
    with db if transaction else nullcontext():
        if replace:
            fields = ("id", "owner_id", "appearance", "work", "server_name", "status", "justification", "image_url",
                      "media_ref", "date", "revision")
            by_id = {r["id"]: r for r in records}
            keep = set(by_id)
            for old in db.execute("SELECT * FROM appearances WHERE guild_id=?", (guild,)).fetchall():
                before = {k: old[k] for k in fields}
                db.execute("INSERT INTO events(event_id,guild_id,request_id,at,kind,record_id,actor_id,source,before,after)"
                           " VALUES(?,?,?,?,'remove',?,?,'restauração',?,NULL)",
                           ("EV-" + str(uuid.uuid4()), guild, rid, at, old["id"], actor_id, json.dumps(before, ensure_ascii=False)))
                if connected and old["id"] not in keep:
                    rev = old["revision"] + 1
                    store.queue_sheet(guild, old["id"], rev, {"op": "clear", "id": old["id"], "revision": rev})
                # Revisão sempre sobe: a planilha só aceita versão mais nova que a que já mostra.
                if old["id"] in by_id:
                    by_id[old["id"]]["revision"] = max(by_id[old["id"]].get("revision", 1), old["revision"] + 1)
            db.execute("DELETE FROM appearances WHERE guild_id=?", (guild,))
        for r in records:
            db.execute("INSERT INTO appearances(id,guild_id,owner_id,appearance,work,key,server_name,status,justification,"
                       "image_url,media_ref,date,revision,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (r["id"], guild, r["owner_id"], r["appearance"], r["work"], exact_key(r["appearance"], r["work"]),
                        r["server_name"], r["status"], r["justification"], r["image_url"], r.get("media_ref", ""), r["date"],
                        r.get("revision", 1), now, now))
            after = {**{k: r[k] for k in ("id", "owner_id", "appearance", "work", "server_name", "status",
                                          "justification", "image_url", "date")},
                     "media_ref": r.get("media_ref", ""), "revision": r.get("revision", 1)}
            if connected:
                store.queue_sheet(guild, r["id"], after["revision"], sheet_upsert(after))
            # Sem aviso no canal de histórico: importar não é cadastro novo.
            db.execute("INSERT INTO events(event_id,guild_id,request_id,at,kind,record_id,actor_id,source,before,after)"
                       " VALUES(?,?,?,?,'import',?,?,'importação',NULL,?)",
                       ("EV-" + str(uuid.uuid4()), guild, rid, at, r["id"], actor_id, json.dumps(after, ensure_ascii=False)))
    return len(records)
