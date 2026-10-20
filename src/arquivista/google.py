"""API Google da conta do Arquivista. Só recebe URLs fixas; nunca registra respostas ou tokens."""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field
from urllib.parse import quote
import aiohttp
from .domain import BridgeError

DRIVE = "https://www.googleapis.com/drive/v3/files"
SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
SCOPE = "https://www.googleapis.com/auth/drive.file"
ALLOWED = frozenset(("addSheet", "updateSheetProperties", "updateDimensionProperties", "appendDimension",
    "insertDimension", "addDimensionGroup", "deleteDimensionGroup", "updateDimensionGroup", "updateCells",
    "repeatCell", "mergeCells", "updateBorders", "addConditionalFormatRule", "setDataValidation"))

@dataclass(frozen=True)
class GoogleConfig:
    client_id: str = field(default="", repr=False)
    client_secret: str = field(default="", repr=False)
    refresh_token: str = field(default="", repr=False)

    @property
    def ready(self):
        return bool(self.client_id and self.client_secret and self.refresh_token)

class GoogleError(BridgeError):
    def __init__(self, code, *, uncertain=False):
        messages = {
            "GOOGLE_SETUP": "A criação automática ainda não foi ativada pelo mantenedor do Arquivista. O cadastro pelo bot continua funcionando.",
            "GOOGLE_AUTH": "A conta Google do Arquivista precisa ser reconectada pelo mantenedor.",
            "GOOGLE_ACCESS": "O Google recusou o acesso. Confira as permissões da planilha; se continuar, avise o mantenedor.",
            "GOOGLE_STORAGE": "A conta Google do Arquivista está sem espaço para criar planilhas. Avise o mantenedor.",
            "GOOGLE_MISSING": "A planilha não foi encontrada. Confira se foi removida ou se o Arquivista perdeu o acesso.",
            "GOOGLE_INVALID": "O Google recusou os dados. Confira o e-mail informado e tente novamente.",
            "GOOGLE_LOCALE": "A localidade da planilha mudou. Em Arquivo > Configurações, escolha Brasil para retomar a sincronização.",
            "BUSY": "O Google demorou ou atingiu o limite de pedidos. Tente novamente em alguns minutos.",
        }
        super().__init__(code, messages.get(code, "Não consegui concluir a operação no Google. Avise o mantenedor."))
        self.uncertain = uncertain

class GoogleAPI:
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot.config, "google", GoogleConfig())
        self.token = ""
        self.expires = 0
        self.lock = asyncio.Lock()

    async def access_token(self):
        if not self.config.ready:
            raise GoogleError("GOOGLE_SETUP")
        async with self.lock:
            if self.token and self.expires > time.monotonic():
                return self.token
            try:
                async with self.bot.session.post("https://oauth2.googleapis.com/token", data={
                    "client_id": self.config.client_id, "client_secret": self.config.client_secret,
                    "refresh_token": self.config.refresh_token, "grant_type": "refresh_token"},
                    timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        raise GoogleError("BUSY" if response.status == 429 or response.status >= 500 else "GOOGLE_AUTH")
                    data = await response.json()
                    self.token = data["access_token"]
                    self.expires = time.monotonic() + max(0, int(data.get("expires_in", 3600)) - 60)
                    return self.token
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError):
                raise GoogleError("BUSY") from None

    async def request(self, method, url, *, body=None, params=None):
        # Os caminhos são montados pelo programa, e o token nunca segue um redirecionamento.
        if not (url == DRIVE or url.startswith(DRIVE + "/") or url.startswith(SHEETS + "/")):
            raise ValueError("destino Google inválido")
        for attempt in range(2):
            token = await self.access_token()
            try:
                async with self.bot.session.request(method, url, json=body, params=params,
                        headers={"Authorization": "Bearer " + token}, allow_redirects=False,
                        timeout=aiohttp.ClientTimeout(total=90)) as response:
                    if response.status == 401 and attempt == 0:
                        self.expires = 0
                        continue
                    if response.status == 401:
                        raise GoogleError("GOOGLE_AUTH")
                    if response.status == 404:
                        raise GoogleError("GOOGLE_MISSING")
                    if response.status == 403:
                        try:
                            failure = await response.json()
                            reasons = {e.get("reason") for e in failure.get("error", {}).get("errors", [])}
                        except (aiohttp.ClientError, ValueError, AttributeError):
                            reasons = set()
                        if "storageQuotaExceeded" in reasons:
                            raise GoogleError("GOOGLE_STORAGE")
                        if reasons & {"rateLimitExceeded", "userRateLimitExceeded", "sharingRateLimitExceeded"}:
                            raise GoogleError("BUSY")
                        raise GoogleError("GOOGLE_ACCESS")
                    if response.status == 429 or response.status >= 500:
                        raise GoogleError("BUSY", uncertain=method != "GET")
                    if not 200 <= response.status < 300:
                        raise GoogleError("GOOGLE_INVALID")
                    return await response.json() if response.status != 204 else {}
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                raise GoogleError("BUSY", uncertain=method != "GET") from None

    async def find_created(self, request_id):
        # UUID criado pelo bot e persistido antes de criar o arquivo. Não usa texto do usuário na busca.
        data = await self.request("GET", DRIVE, params={"q":
            "trashed=false and appProperties has { key='arquivista_request' and value='" + request_id + "' }",
            "fields": "files(id,webViewLink)", "pageSize": "2"})
        files = data.get("files", [])
        if len(files) > 1:
            raise GoogleError("INTERNAL")
        return files[0] if files else None

    async def create_file(self, title, request_id, guild_id):
        return await self.request("POST", DRIVE, body={"name": title[:150],
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "appProperties": {"arquivista_request": request_id, "arquivista_guild": str(guild_id)}},
            params={"fields": "id,webViewLink"})

    async def share_editor(self, file_id, email):
        url = DRIVE + "/" + quote(file_id, safe="") + "/permissions"
        page = None
        while True:
            params = {"fields": "permissions(type,emailAddress,role),nextPageToken", "pageSize": "100"}
            if page:
                params["pageToken"] = page
            data = await self.request("GET", url, params=params)
            if any(p.get("type") == "user" and p.get("emailAddress", "").lower() == email.lower()
                   and p.get("role") in ("owner", "writer") for p in data.get("permissions", [])):
                return
            page = data.get("nextPageToken")
            if not page:
                break
        await self.request("POST", url, body={"type": "user", "role": "writer", "emailAddress": email},
                           params={"sendNotificationEmail": "false", "fields": "id"})

class DirectSheet:
    """A mesma interface status/read/write da ponte antiga, usando Sheets API."""
    def __init__(self, api, file_id):
        self.api, self.file_id = api, file_id
        self.url = SHEETS + "/" + quote(file_id, safe="")
        self.reads = []

    async def metadata(self):
        return await self.api.request("GET", self.url, params={
            "fields": "properties(locale),sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))"})

    async def values(self, ranges):
        if not ranges:
            return []
        # POST evita URLs enormes quando há centenas de abas e nomes longos.
        data = await self.api.request("POST", self.url + "/values:batchGetByDataFilter", body={
            "dataFilters": [{"a1Range": r} for r in ranges], "valueRenderOption": "FORMULA", "majorDimension": "ROWS"})
        matched = {f["a1Range"]: r.get("valueRange", {}).get("values", [])
                   for r in data.get("valueRanges", []) for f in r.get("dataFilters", []) if "a1Range" in f}
        if any(r not in matched for r in ranges):
            raise GoogleError("INTERNAL")
        return [matched[r] for r in ranges]

    async def call(self, action, actor=None, data=None):
        data = data or {}
        if action == "status":
            self.reads = []
            meta = await self.metadata()
            # As fórmulas produzidas pelo layout usam a localidade definida na criação.
            locale = meta.get("properties", {}).get("locale", "pt_BR")
            if locale != "pt_BR":
                raise GoogleError("GOOGLE_LOCALE")
            return {"version": "2.direct", "sep": ";", "sheets": [
                {"sheetId": x["properties"]["sheetId"], "title": x["properties"]["title"],
                 "rows": x["properties"]["gridProperties"]["rowCount"]} for x in meta.get("sheets", [])]}
        if action == "read":
            result = await self.values(data["ranges"])
            self.reads.append((list(data["ranges"]), result))
            return {"values": result}
        if action != "write":
            raise GoogleError("GOOGLE_INVALID")
        requests = data["requests"]
        if any(len(r) != 1 or next(iter(r)) not in ALLOWED for r in requests):
            raise GoogleError("GOOGLE_INVALID")
        meta = await self.metadata()
        if meta.get("properties", {}).get("locale", "pt_BR") != "pt_BR":
            raise GoogleError("GOOGLE_LOCALE")
        current = {x["properties"]["sheetId"]: x["properties"] for x in meta.get("sheets", [])}
        for e in data.get("expect", []):
            p = current.get(e["sheetId"])
            if not p or p["title"] != e["title"] or p["gridProperties"]["rowCount"] != e["rows"]:
                raise BridgeError("CHANGED", "A estrutura da planilha mudou. Vou ler de novo antes de gravar.")
        # Revalida o que foi lido para não sobrescrever uma edição feita enquanto montávamos o lote.
        for ranges, old in self.reads:
            if await self.values(ranges) != old:
                raise BridgeError("CHANGED", "A planilha recebeu uma edição. Vou ler de novo antes de gravar.")
        if requests:
            await self.api.request("POST", self.url + ":batchUpdate", body={"requests": requests})
        self.reads = []
        return {}
