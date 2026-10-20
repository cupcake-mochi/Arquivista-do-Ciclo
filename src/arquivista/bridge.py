"""Cliente autenticado do Web App. Retentativas reutilizam o mesmo request_id."""
from __future__ import annotations
import asyncio
import json
import random
import uuid
from urllib.parse import urlsplit
import aiohttp
from .domain import Actor, BridgeError, ERRORS, signed_envelope


class Bridge:
    def __init__(self, session: aiohttp.ClientSession, url: str, secret: str, guild_id: int):
        self.session, self.url, self.secret, self.guild = session, url, secret, str(guild_id)
    async def call(self, action: str, actor: Actor, data: dict | None = None,
                   request_id: str | None = None) -> dict:
        rid = request_id or str(uuid.uuid4())
        for attempt in range(3):
            envelope = signed_envelope(self.secret, action, data or {}, self.guild, actor, rid)
            try:
                # ContentService redireciona POST para uma leitura GET no googleusercontent.
                url, method, payload = self.url, "POST", envelope
                for _ in range(4):
                    host = (urlsplit(url).hostname or "").lower()
                    if host == "accounts.google.com":
                        raise BridgeError("LOGIN", ERRORS["LOGIN"])
                    if not (host == "script.google.com" or host.endswith(".googleusercontent.com")):
                        raise BridgeError("AUTH", ERRORS["AUTH"])
                    async with self.session.request(method, url, json=payload if method == "POST" else None,
                            allow_redirects=False, timeout=aiohttp.ClientTimeout(total=110)) as response:
                        if response.status in (301, 302, 303):
                            url = response.headers.get("Location", "")
                            method, payload = "GET", None
                            continue
                        if response.status in (429, 500, 502, 503, 504):
                            raise BridgeError("BUSY", ERRORS["BUSY"])
                        if response.status in (401, 403):
                            raise BridgeError("LOGIN", ERRORS["LOGIN"])
                        if response.status != 200:
                            raise BridgeError("AUTH", ERRORS["AUTH"])
                        raw = await response.content.read(12 * 1024 * 1024 + 1)
                        if len(raw) > 12 * 1024 * 1024:
                            raise BridgeError("INTERNAL", ERRORS["INTERNAL"])
                        try:
                            result = json.loads(raw)
                        except (ValueError, UnicodeDecodeError):
                            raise BridgeError("AUTH", "A ponte retornou uma página em vez de dados. Confira a implantação /exec e o acesso ao Web App.") from None
                        if not result.get("ok"):
                            code = str(result.get("code", "INTERNAL"))
                            raise BridgeError(code, ERRORS.get(code, ERRORS["INTERNAL"]))
                        return result.get("data", {})
                raise BridgeError("AUTH", ERRORS["AUTH"])
            except (aiohttp.ClientError, asyncio.TimeoutError, BridgeError) as exc:
                if isinstance(exc, BridgeError) and exc.code != "BUSY":
                    raise
                if attempt == 2:
                    # O servidor pode ter concluído mesmo que a resposta se perca.
                    raise BridgeError("BUSY", "Não recebi a confirmação a tempo. Use Tentar novamente nesta mesma confirmação; ela não duplica o pedido.") from None
                await asyncio.sleep(2 ** attempt + random.random())
        raise BridgeError("INTERNAL", ERRORS["INTERNAL"])
