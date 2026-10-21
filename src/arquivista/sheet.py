"""Planilha conectada: chave guardada cifrada e envio da fila bot→planilha.

A chave de cada planilha fica cifrada no banco com a chave mestra do bot (AC_MASTER_KEY,
ou derivada do token quando ela não existe). Só biblioteca padrão: fluxo HMAC-SHA256 em
modo contador + etiqueta HMAC (cifra, depois autentica), com chaves separadas para cada uso.
"""
from __future__ import annotations
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time

from . import layout, pull
from .bridge import Bridge
from .domain import Actor, BridgeError, ERRORS
from .store import sheet_upsert

log = logging.getLogger(__name__)
SHEET_URL = re.compile(r"^https://script\.google\.com/macros/s/[A-Za-z0-9_-]{20,200}/exec$")
SHEET_KEY = re.compile(r"^[0-9a-f]{32,128}$")
BATCH = 50
PULL_EVERY = 300  # de quanto em quanto tempo o bot procura edições feitas na planilha
REFUSED = {"DUPLICATE": "aparência e obra já ocupadas por outro cadastro", "CAPACITY": "o membro já está no limite de cadastros",
           "INVALID": "valor que o bot não aceita (situação fora da lista, link sem https, data ilegível ou campo obrigatório vazio)"}
# Pedidos de uma gravação, em bytes de JSON. O script aceita até 4 MB por chamada; um membro novo dá ~130 KB.
BUDGET = 2_500_000

async def read_sheet(bridge: Bridge, actor: Actor) -> tuple[layout.Model, list[dict]]:
    """Lê a planilha como o bot precisa: lista de guias, coluna K de todas e A:K das guias de membro.
    Devolve o modelo e o estado das guias de membro, que a gravação confere antes de aplicar."""
    st = await bridge.call("status", actor, {})
    if not str(st.get("version", "")).startswith("2."):
        raise BridgeError("OLD_SCRIPT", ERRORS["OLD_SCRIPT"])
    sheets = [x for x in st.get("sheets", []) if isinstance(x, dict)]
    async def read(ranges: list[str], step: int) -> list:
        out = []
        for i in range(0, len(ranges), step):
            out += (await bridge.call("read", actor, {"ranges": ranges[i:i + step]}))["values"]
        return out
    marks = await read([layout.a1(x["title"], f"K1:K{x['rows']}") for x in sheets], 400)
    members = [x for x, k in zip(sheets, marks) if layout.is_member_tab(k)]
    values = await read([layout.a1(x["title"], f"A1:K{x['rows']}") for x in members], 40)
    model = layout.load(st.get("sep") or ";", sheets, {x["sheetId"]: v for x, v in zip(members, values)}, language=getattr(bridge,"language","pt-BR"))
    return model, [{"sheetId": x["sheetId"], "rows": x["rows"], "title": x["title"]} for x in members]

def _keys(master: bytes) -> tuple[bytes, bytes]:
    return (hmac.new(master, b"arquivista:cifra", hashlib.sha256).digest(),
            hmac.new(master, b"arquivista:etiqueta", hashlib.sha256).digest())

def _stream(key: bytes, nonce: bytes, size: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < size:
        out += hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        counter += 1
    return bytes(out[:size])

def seal(master: bytes, text: str) -> str:
    enc, mac = _keys(master)
    nonce, data = os.urandom(16), text.encode()
    body = bytes(a ^ b for a, b in zip(data, _stream(enc, nonce, len(data))))
    tag = hmac.new(mac, nonce + body, hashlib.sha256).digest()
    return "v1." + ".".join(base64.urlsafe_b64encode(x).decode() for x in (nonce, body, tag))

def unseal(master: bytes, sealed: str) -> str:
    """Erro (ValueError) quando a chave mestra mudou ou o valor foi adulterado."""
    try:
        version, *parts = sealed.split(".")
        nonce, body, tag = (base64.urlsafe_b64decode(p) for p in parts)
    except (ValueError, AttributeError):
        raise ValueError("chave da planilha ilegível") from None
    enc, mac = _keys(master)
    if version != "v1" or not hmac.compare_digest(tag, hmac.new(mac, nonce + body, hashlib.sha256).digest()):
        raise ValueError("chave da planilha ilegível")
    return bytes(a ^ b for a, b in zip(body, _stream(enc, nonce, len(body)))).decode()

class SheetSync:
    """Envia a fila de cada servidor com planilha. Um envio por vez; a ordem da fila é a das mudanças."""
    def __init__(self, bot):
        self.bot = bot
        self.names: dict[tuple[str, str], str] = {}
        self.next_pull: dict[str, float] = {}
    def actor(self) -> Actor:
        return Actor(str(self.bot.user.id) if self.bot.user else "0", "Arquivista", True)
    def bridge(self, guild_id: str, cfg: dict | None = None) -> Bridge:
        cfg = cfg or self.bot.store.guild(guild_id)
        managed = self.bot.store.managed_sheet(guild_id)
        if managed and cfg.get("sheet_url") == managed["url"] and managed["file_id"]:
            from .google import DirectSheet
            return DirectSheet(self.bot.managed.api, managed["file_id"], managed.get("language","pt-BR"))
        return Bridge(self.bot.session, cfg["sheet_url"], unseal(self.bot.config.master_key, cfg["sheet_key"]), int(guild_id))
    async def owner_name(self, guild_id: str, owner_id: str) -> str:
        key = (guild_id, owner_id)
        if key not in self.names:
            guild = self.bot.get_guild(int(guild_id))
            member = guild.get_member(int(owner_id)) if guild else None
            if guild and member is None:
                try:
                    member = await guild.fetch_member(int(owner_id))
                except Exception:
                    member = None
            # Sem nome (saiu do servidor, erro de rede): a planilha mantém o que já tem.
            self.names[key] = member.name[:100] if member else ""
        return self.names[key]
    async def run(self) -> None:
        for guild_id in self.bot.store.sheet_due():
            if not self.bot.get_guild(int(guild_id)):
                continue  # o bot saiu do servidor: os dados ficam, mas não mexe mais na planilha
            try:
                await self.guild(guild_id)
            except Exception as exc:
                log.warning("Planilha do servidor %s: %s", guild_id, type(exc).__name__)
    async def pull_due(self) -> int:
        """Procura edições feitas na planilha nos servidores em que já deu a hora. Devolve quantas entraram."""
        total, now = 0, time.time()
        for guild_id in self.bot.store.sheet_guilds():
            if self.next_pull.get(guild_id, 0) > now or not self.bot.get_guild(int(guild_id)):
                continue
            self.next_pull[guild_id] = now + PULL_EVERY
            try:
                total += await self.pull(guild_id)
            except Exception as exc:
                self.next_pull[guild_id] = now + 3 * PULL_EVERY
                code = getattr(exc, "code", None) or ("KEY" if isinstance(exc, ValueError) else "INTERNAL")
                self.bot.store.set_guild(guild_id, sheet_error=code)
                log.warning("Leitura da planilha do servidor %s: %s", guild_id, type(exc).__name__)
        return total
    async def pull(self, guild_id: str) -> int:
        store = self.bot.store
        queued, bad = store.sheet_pending(guild_id)
        if queued > bad:
            # Primeiro a fila do bot vai para a planilha (inclusive a que está esperando outra tentativa);
            # ler antes importaria de novo uma linha digitada cujo ID ainda não foi gravado.
            return 0
        model, _ = await read_sheet(self.bridge(guild_id), self.actor())
        archive = self.bot.archive(int(guild_id))
        records = {r["id"]: r for r in store.records(guild_id)}
        found, lost = await asyncio.to_thread(pull.changes, model, records, store.sheet_queued(guild_id))
        applied, notes = 0, []
        for change in found:
            result = archive.from_sheet(change)
            if result == "ok":
                applied += 1
                continue
            if result in ("same", "STALE", "NOT_FOUND"):
                continue  # mudou no Discord no meio da leitura: a versão do bot vai por cima
            notes.append(f"{change.get('appearance') or 'linha sem nome'} (guia {change['tab']}): {REFUSED.get(result, result)}")
            if change["id"]:
                # Desfaz na planilha: regrava a linha com o que está no banco, na mesma revisão.
                r = archive.record(change["id"])
                with store.db:
                    store.queue_sheet(guild_id, r["id"], r["revision"], {**sheet_upsert(r), "force": True})
        for owner, tab in model.broken().items():
            notes.append(f"a guia {tab} ganhou ou perdeu uma linha no meio das fichas; desfaça (Ctrl+Z) para o bot voltar a atualizar essa pessoa")
        if lost:
            # Linha apagada à mão na planilha volta: para apagar um cadastro, use /remover.
            with store.db:
                for rid in lost:
                    store.queue_sheet(guild_id, rid, records[rid]["revision"], sheet_upsert(records[rid]))
            notes.append(f"Recoloquei as fichas apagadas manualmente na planilha (total: {len(lost)}). Para remover um cadastro, use /remover no Discord.")
        note = "; ".join(notes)[:900] or None
        if note != store.guild(guild_id).get("sheet_note"):
            store.set_guild(guild_id, sheet_note=note)
        store.set_guild(guild_id, sheet_error=None)
        return applied + len(lost)
    async def guild(self, guild_id: str) -> None:
        store = self.bot.store
        rescued: set[str] = set()
        while True:
            rows = store.sheet_batch(guild_id, BATCH)
            if not rows:
                return
            ops = []
            for r in rows:
                op = json.loads(r["payload"])
                if op["op"] == "upsert":
                    op["record"]["owner_name"] = await self.owner_name(guild_id, op["record"]["owner_id"])
                ops.append(op)
            ids = [r["record_id"] for r in rows]
            try:
                bridge = self.bridge(guild_id)
                model, expect = await read_sheet(bridge, self.actor())
                # Edição feita na planilha num cadastro que também mudou no Discord: entra antes de gravar
                # por cima. Depois disso a fila mudou, então lê de novo.
                archive = self.bot.archive(int(guild_id))
                records = {r["id"]: r for r in store.records(guild_id)}
                fixes = [c for c in pull.rescued(model, records, store.sheet_queued(guild_id), archive.version)
                         if c["id"] not in rescued]
                rescued.update(c["id"] for c in fixes)
                if [c for c in fixes if archive.from_sheet(c) == "ok"]:
                    continue
                requests, planned = await asyncio.to_thread(model.plan, ops, BUDGET)
                if requests:
                    # Se a planilha mudou de tamanho ou de nome desde a leitura, o script recusa (CHANGED)
                    # e nada é aplicado; isso também torna seguro repetir uma gravação cuja resposta se perdeu.
                    await bridge.call("write", self.actor(), {"requests": requests, "expect": expect})
                data = {"results": planned}
            except Exception as exc:
                # Erro inesperado também espera e aparece no diagnóstico, em vez de tentar de novo a cada volta.
                code = getattr(exc, "code", None) or ("KEY" if isinstance(exc, ValueError) else "INTERNAL")
                if not isinstance(exc, (BridgeError, ValueError)):
                    log.warning("Planilha do servidor %s: %s", guild_id, type(exc).__name__)
                store.sheet_retry(guild_id, ids, code)
                store.set_guild(guild_id, sheet_error=code)
                return
            results = {x.get("id"): x.get("status") for x in data.get("results", []) if isinstance(x, dict)}
            for r in rows:
                if r["record_id"] not in results:
                    continue  # ficou para a próxima gravação (limite de tamanho); continua na fila como está
                status = results.get(r["record_id"])
                if status == "broken":
                    store.sheet_retry(guild_id, [r["record_id"]], "broken")  # espera a guia ser consertada
                    continue
                if status in ("ok", "stale"):
                    store.sheet_done(guild_id, r["record_id"], r["revision"])
                else:
                    # Dado que a planilha recusou não melhora com pressa: tenta de novo bem depois.
                    store.sheet_retry(guild_id, [r["record_id"]], status or "missing", long=True)
            store.set_guild(guild_id, sheet_error=None, sheet_ok=self.bot.now_text())
            if len(rows) < BATCH and len(results) == len(rows):
                return
