"""Leitura e validação de um arquivo existente; não concede permissões Google."""
from __future__ import annotations

import re
import hashlib
import json
import secrets
import time
import uuid
from dataclasses import dataclass
from urllib.parse import urlsplit

from . import importer, layout, pull
from .domain import UserError
from .google import DirectSheet, GoogleError
from .sheet import read_sheet, seal

AUTH_RANGE = "ARQUIVISTA_AUTORIZACAO"
TTL = 600
MAX_CELLS = 1_000_000
MAX_RECORDS = 5000


def spreadsheet_id(url: str) -> str:
    """Aceita somente a URL nativa do Sheets; o endereço nunca vira destino HTTP."""
    try:
        parsed = urlsplit(url.strip())
        match = re.fullmatch(r"/spreadsheets/d/([A-Za-z0-9_-]{10,200})(?:/edit|/view|/preview)?/?", parsed.path)
        valid = (parsed.scheme == "https" and parsed.netloc == "docs.google.com"
                 and not parsed.username and not parsed.password and match)
    except (ValueError, AttributeError):
        valid = False
    if not valid:
        raise UserError("Cole o link da planilha do Google Sheets. Não use link de pasta, XLSX ou Apps Script.")
    return match[1]


def sheet_records(model):
    """Lê todas as posições, inclusive cadastros ainda sem ID, sem modificar o arquivo."""
    blocks = model.blocks()
    if model.broken() or not blocks:
        raise UserError("A planilha precisa ter abas de membro válidas do Arquivista, sem linhas deslocadas.")
    owners, records = set(), []
    for block in blocks:
        if not layout.SNOWFLAKE.fullmatch(block.owner) or block.owner in owners:
            raise UserError("A planilha tem um responsável inválido ou abas repetidas para a mesma pessoa.")
        owners.add(block.owner)
        for n in range(1, block.slots + 1):
            values = pull.row_values(block, n)
            rid = block.cell(n, layout.ID)
            if not rid and not values["appearance"] and not values["work"]:
                continue
            owner = block.cell(n, layout.OWNER)
            revision = pull._revision(block.cell(n, layout.MARK)) if rid else 1
            if (owner and str(owner) != block.owner) or (rid and (revision is None or revision < 1)):
                raise UserError("Há IDs, responsáveis ou revisões inconsistentes na planilha. Corrija a estrutura antes de conectar.")
            records.append({"id": str(rid) if rid else "AP-" + str(uuid.uuid4()),
                            "owner_id": block.owner, "revision": revision, **values})
            if len(records) > MAX_RECORDS:
                raise UserError("A importação aceita até 5.000 cadastros por vez. Peça ao mantenedor uma migração acompanhada para arquivos maiores; nenhum dado foi importado.")
    checked, errors, warnings = importer.check({"format": importer.FORMAT, "version": 1, "records": records})
    if errors or warnings:
        # A confirmação nunca mostra conteúdo interno de outra pessoa como mensagem de erro.
        raise UserError("A planilha contém cadastros inválidos ou que exigem correção. Confira IDs, aparência, obra, situação, datas e links HTTPS antes de conectar.")
    return checked


def fingerprint(model):
    raw = [[t.sheet_id, t.name, t.grid] for t in model.tabs]
    return hashlib.sha256(json.dumps(raw, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


@dataclass
class Connection:
    guild_id: str
    author_id: str
    file_id: str
    token: str
    expires: float
    email: str = ""
    title: str = ""
    language: str = "pt-BR"
    records: list | None = None
    sheet_digest: str = ""
    db_digest: str = ""
    used: bool = False
    started: bool = False

    @property
    def url(self):
        return "https://docs.google.com/spreadsheets/d/" + self.file_id + "/edit"

    def check(self):
        if self.used or time.monotonic() >= self.expires:
            raise UserError("Este pedido expirou ou já foi confirmado. Se a importação já começou, use /planilha criar para retomar a cópia; caso contrário, abra /planilha importar novamente.")


class ExistingSheets:
    """Importação confirmada para um arquivo novo; origem somente de leitura."""
    def __init__(self, bot):
        self.bot = bot

    async def manager(self, guild, member, request=None):
        managed = self.bot.managed
        managed.require_manager(guild, member)
        actual = await managed.member(guild, member)
        managed.require_manager(guild, actual)
        if request and (str(guild.id) != request.guild_id or str(actual.id) != request.author_id):
            raise UserError("Esta conexão pertence a outra pessoa ou servidor. Abra seu próprio comando.")
        if request:
            request.check()
        return actual

    def available(self, guild_id):
        store = self.bot.store
        if store.guild(guild_id).get("sheet_url") or store.managed_sheet(guild_id):
            raise UserError("Este servidor já tem uma planilha cadastrada. Use /planilha abrir ou /planilha criar para retomá-la. A importação não substitui arquivos existentes.")
        if store.records(guild_id):
            raise UserError("Este servidor já tem cadastros. A importação exige um servidor vazio para não misturar ou substituir dados. Faça backup e concilie os cadastros antes de importar.")

    async def metadata(self, request):
        try:
            meta = await self.bot.managed.api.file_info(request.file_id)
        except GoogleError as exc:
            if exc.code in ("GOOGLE_ACCESS", "GOOGLE_MISSING"):
                raise UserError("O Arquivista não tem acesso autorizado a esse arquivo. O responsável precisa permitir o acesso desse arquivo ao aplicativo Google; apenas colar o link ou deixá-lo público não autoriza a conexão. Consulte o guia do mantenedor.") from None
            raise
        if meta.get("trashed") or meta.get("mimeType") != "application/vnd.google-apps.spreadsheet":
            raise UserError("O arquivo precisa ser uma planilha nativa do Google Sheets fora da lixeira.")
        if not meta.get("isAppAuthorized") or not meta.get("capabilities", {}).get("canCopy"):
            raise UserError("O aplicativo do Arquivista precisa ter acesso autorizado ao arquivo e permissão de copiar seu conteúdo. Não é necessário conceder edição no original ao solicitante.")
        return meta

    async def begin(self, guild, member, url, email):
        member = await self.manager(guild, member)
        from .managed import valid_email
        email = valid_email(email)
        file_id = spreadsheet_id(url)
        async with self.bot.sheet_lock:
            self.available(guild.id)
            if not self.bot.managed.ready:
                raise GoogleError("GOOGLE_SETUP")
            request = Connection(str(guild.id), str(member.id), file_id,
                "AC-" + str(guild.id) + "-" + secrets.token_urlsafe(24), time.monotonic() + TTL, email=email)
            meta = await self.metadata(request)
            return request, await self.source_manager(request, meta)

    async def source_manager(self, request, meta):
        bound = meta.get("appProperties", {}).get("arquivista_guild")
        if not bound or not str(bound).isdigit():
            return False
        source = self.bot.get_guild(int(bound))
        if source is None or str(source.id) != str(bound):
            return False
        try:
            member = source.get_member(int(request.author_id))
            if member is None:
                return False
            member = await self.bot.managed.member(source, member)
            self.bot.managed.require_manager(source, member)
        except UserError:
            return False
        return True

    async def authorize(self, request, meta):
        if await self.source_manager(request, meta):
            return
        api = self.bot.managed.api
        sheet = DirectSheet(api, request.file_id)
        info = await api.request("GET", sheet.url, params={"fields": "namedRanges(name,range)"})
        ranges = [r.get("range", {}) for r in info.get("namedRanges", []) if r.get("name") == AUTH_RANGE]
        if (len(ranges) != 1 or ranges[0].get("endRowIndex", 0) - ranges[0].get("startRowIndex", 0) != 1
                or ranges[0].get("endColumnIndex", 0) - ranges[0].get("startColumnIndex", 0) != 1):
            raise UserError("Peça ao responsável pelo arquivo para criar o intervalo nomeado ARQUIVISTA_AUTORIZACAO em uma única célula vazia e colar o código deste painel. Depois, escolha Validar arquivo.")
        values = await sheet.values([AUTH_RANGE])
        if values != [[[request.token]]]:
            raise UserError("O código de autorização não confere. O responsável pelo arquivo precisa colar o código atual no intervalo ARQUIVISTA_AUTORIZACAO.")

    def db_digest(self, guild_id):
        data = self.bot.store.records(guild_id)
        return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    async def inspect(self, guild, member, request):
        await self.manager(guild, member, request)
        async with self.bot.sheet_lock:
            request.check()
            self.available(guild.id)
            meta = await self.metadata(request)
            await self.authorize(request, meta)
            sheet = DirectSheet(self.bot.managed.api, request.file_id)
            props = await sheet.metadata()
            sheets = props.get("sheets", [])
            if len(sheets) > 200 or sum(s.get("properties", {}).get("gridProperties", {}).get("rowCount", 0) * layout.WIDTH for s in sheets) > MAX_CELLS:
                raise UserError("A planilha excede o tamanho permitido para importação pelo Discord. Peça ao mantenedor uma migração acompanhada; nenhum dado foi importado.")
            locale = props.get("properties", {}).get("locale")
            if locale not in ("pt_BR", "en_US"):
                raise UserError("A planilha precisa manter uma localidade compatível: Brasil ou Estados Unidos. O comando não altera o idioma do arquivo.")
            request.language = "en" if locale == "en_US" else "pt-BR"
            sheet = DirectSheet(self.bot.managed.api, request.file_id, request.language)
            model, _ = await read_sheet(sheet, self.bot.sheets.actor())
            records = sheet_records(model)
            request.records, request.sheet_digest, request.db_digest = records, fingerprint(model), self.db_digest(guild.id)
            request.title = meta.get("name") or "Google Sheets"
            return {"records": len(records), "members": len(model.blocks()), "existing": 0}

    async def confirm(self, guild, member, request):
        await self.manager(guild, member, request)
        async with self.bot.sheet_lock:
            request.check()
            self.available(guild.id)
            if request.records is None or self.db_digest(guild.id) != request.db_digest:
                raise UserError("Os cadastros mudaram ou falta validar o arquivo. Abra /planilha importar novamente.")
            meta = await self.metadata(request)
            await self.authorize(request, meta)
            sheet = DirectSheet(self.bot.managed.api, request.file_id, request.language)
            model, _ = await read_sheet(sheet, self.bot.sheets.actor())
            if fingerprint(model) != request.sheet_digest:
                raise UserError("A planilha mudou depois da prévia. Abra /planilha importar novamente para conferir a versão atual.")
            await self.manager(guild, member, request)
            self.available(guild.id)
            if self.db_digest(guild.id) != request.db_digest:
                raise UserError("Os cadastros mudaram ou falta validar o arquivo. Abra /planilha importar novamente.")
            # Cada servidor recebe registros próprios; nunca compartilha os IDs da origem.
            records = [{**r, "id": "AP-" + str(uuid.uuid4()), "revision": 1, "media_ref": ""}
                       for r in request.records]
            store = self.bot.store
            with store.db:
                importer.apply(store, guild.id, records, str(member.id), transaction=False)
                store.db.execute("INSERT INTO managed_sheets(guild_id,request_id,editor,state,updated,language) "
                    "VALUES(?,?,?,'pending',?,?)", (str(guild.id), str(uuid.uuid4()),
                    seal(self.bot.config.master_key, request.email), time.time(),
                    store.guild(guild.id).get("language", "pt-BR")))
            # Persistido antes de chamar o Google: uma queda retoma pelo /planilha criar,
            # sem importar novamente ou duplicar o arquivo. Nunca escreve na origem.
            request.used = True
            request.started = True
        return await self.bot.managed.create(guild, member)

