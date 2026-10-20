"""Planilha conectada: chave guardada cifrada e envio da fila bot→planilha.

A chave de cada planilha fica cifrada no banco com a chave mestra do bot (AC_MASTER_KEY,
ou derivada do token quando ela não existe). Só biblioteca padrão: fluxo HMAC-SHA256 em
modo contador + etiqueta HMAC (cifra, depois autentica), com chaves separadas para cada uso.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import logging
import os
import re

from . import layout
from .bridge import Bridge
from .domain import Actor, BridgeError, ERRORS

log = logging.getLogger(__name__)
SHEET_URL = re.compile(r"^https://script\.google\.com/macros/s/[A-Za-z0-9_-]{20,200}/exec$")
SHEET_KEY = re.compile(r"^[0-9a-f]{32,128}$")
BATCH = 50
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
    model = layout.load(st.get("sep") or ";", sheets, {x["sheetId"]: v for x, v in zip(members, values)})
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
    def actor(self) -> Actor:
        return Actor(str(self.bot.user.id) if self.bot.user else "0", "Arquivista", True)
    def bridge(self, guild_id: str, cfg: dict | None = None) -> Bridge:
        cfg = cfg or self.bot.store.guild(guild_id)
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
            try:
                await self.guild(guild_id)
            except Exception as exc:
                log.warning("Planilha do servidor %s: %s", guild_id, type(exc).__name__)
    async def guild(self, guild_id: str) -> None:
        store = self.bot.store
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
                requests, planned = model.plan(ops, BUDGET)
                if requests:
                    # Se a planilha mudou de tamanho ou de nome desde a leitura, o script recusa (CHANGED)
                    # e nada é aplicado; isso também torna seguro repetir uma gravação cuja resposta se perdeu.
                    await bridge.call("write", self.actor(), {"requests": requests, "expect": expect})
                data = {"results": planned}
            except (BridgeError, ValueError) as exc:
                code = getattr(exc, "code", "KEY")
                store.sheet_retry(guild_id, ids, code)
                store.set_guild(guild_id, sheet_error=code)
                return
            results = {x.get("id"): x.get("status") for x in data.get("results", []) if isinstance(x, dict)}
            for r in rows:
                if r["record_id"] not in results:
                    continue  # ficou para a próxima gravação (limite de tamanho); continua na fila como está
                status = results.get(r["record_id"])
                if status in ("ok", "stale"):
                    store.sheet_done(guild_id, r["record_id"], r["revision"])
                else:
                    # Dado que a planilha recusou não melhora com pressa: tenta de novo bem depois.
                    store.sheet_retry(guild_id, [r["record_id"]], status or "missing", long=True)
            store.set_guild(guild_id, sheet_error=None, sheet_ok=self.bot.now_text())
            if len(rows) < BATCH and len(results) == len(rows):
                return
