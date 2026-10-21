"""Criação retomável de uma planilha privada por servidor, sem instalar Apps Script."""
from __future__ import annotations
from .sheet_language import label
import re
import uuid
import discord
from .domain import UserError
from .google import GoogleAPI, GoogleError, DirectSheet
from .sheet import read_sheet, seal, unseal

def valid_email(value):
    value = value.strip()
    if len(value) > 254 or value.count("@") != 1:
        raise UserError("Informe um e-mail Google válido, sem espaços, para receber a edição da planilha.")
    local, domain = value.rsplit("@", 1)
    labels = domain.split(".")
    if (not local or len(local) > 64 or local.startswith(".") or local.endswith(".") or ".." in local
            or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+", local)
            or len(labels) < 2 or any(not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", p) for p in labels)):
        raise UserError("Informe um e-mail Google válido, sem espaços, para receber a edição da planilha.")
    return local + "@" + domain.lower()

class ManagedSheets:
    def __init__(self, bot):
        self.bot = bot
        self.api = GoogleAPI(bot)

    @property
    def ready(self):
        return self.api.config.ready

    def require_manager(self, guild, manager):
        if not guild or getattr(getattr(manager, "guild", None), "id", None) != guild.id or not self.bot.can_configure(manager):
            raise UserError("Só o dono ou quem pode gerenciar este servidor configura a planilha.")

    async def member(self, guild, member):
        # O comando usa discord.Member; a checagem extra impede ID/nick inventado e membro de outro servidor.
        if not isinstance(member, discord.Member) or member.guild.id != guild.id:
            raise UserError("Selecione um membro válido deste servidor pelo campo de @menção.")
        try:
            return await guild.fetch_member(member.id)
        except discord.NotFound:
            raise UserError("Essa pessoa não está mais no servidor. Selecione outro membro pelo campo de @menção.") from None
        except discord.HTTPException:
            raise UserError("Não consegui confirmar esse membro no Discord. Tente novamente; nenhuma aba foi criada.") from None

    async def create(self, guild, manager, email=None):
        self.require_manager(guild, manager)
        manager = await self.member(guild, manager)
        self.require_manager(guild, manager)
        async with self.bot.sheet_lock:
            cfg = self.bot.store.guild(guild.id)
            row = self.bot.store.managed_sheet(guild.id)
            if cfg.get("sheet_url") and (not row or cfg["sheet_url"] != row["url"]):
                raise UserError("Este servidor já tem uma planilha conectada pelo método anterior. Ela continua funcionando; a criação não substitui esse arquivo.")
            if not self.ready:
                raise GoogleError("GOOGLE_SETUP")
            if not row:
                email = valid_email(email or "")
                row = self.bot.store.begin_managed_sheet(guild.id, str(uuid.uuid4()), seal(self.bot.config.master_key, email), cfg.get("language","pt-BR"))
            elif row["state"] == "awaiting_email":
                email = valid_email(email or "")
                self.bot.store.update_managed_sheet(guild.id, editor=seal(self.bot.config.master_key, email), state="sharing")
                row = self.bot.store.managed_sheet(guild.id)
            if not row["file_id"]:
                found = await self.api.find_created(row["request_id"])
                if not found:
                    if row["state"] == "creating":
                        raise UserError("O Google ainda não confirmou a criação anterior. Tente /planilha criar novamente em alguns minutos. Se persistir, avise o mantenedor; não vou criar outro arquivo enquanto houver dúvida.")
                    self.bot.store.update_managed_sheet(guild.id, state="creating")
                    try:
                        found = await self.api.create_file("Arquivista · " + guild.name, row["request_id"], guild.id)
                    except GoogleError as exc:
                        if not exc.uncertain:
                            self.bot.store.update_managed_sheet(guild.id, state="pending")
                        raise
                # Persiste o ID antes de formatar/compartilhar: qualquer erro posterior retoma o mesmo arquivo.
                file_id, url = found.get("id"), found.get("webViewLink")
                if not file_id or not url or not re.fullmatch(r"https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]+(?:/.*)?", url):
                    raise GoogleError("INTERNAL", uncertain=True)
                self.bot.store.update_managed_sheet(guild.id, file_id=file_id, url=url, state="initializing")
                row = self.bot.store.managed_sheet(guild.id)
            sheet = DirectSheet(self.api, row["file_id"], row.get("language","pt-BR"))
            if row["state"] != "ready":
                if row["state"] != "sharing":
                    await self.initialize(sheet, guild, manager)
                    # O compartilhamento pode ter sido aceito mesmo se a resposta se perder.
                    # A partir daqui alguém já pode editar/reordenar abas: nunca inicialize de novo.
                    self.bot.store.update_managed_sheet(guild.id, state="sharing")
                try:
                    email = unseal(self.bot.config.master_key, row["editor"])
                except ValueError:
                    raise UserError("Não consegui ler o e-mail guardado. A chave mestra do Arquivista pode ter mudado; avise o mantenedor para recuperar a chave anterior. O arquivo foi preservado.") from None
                try:
                    await self.api.share_editor(row["file_id"], email)
                except GoogleError as exc:
                    if exc.code == "GOOGLE_INVALID" and not exc.uncertain:
                        self.bot.store.update_managed_sheet(guild.id, state="awaiting_email")
                        raise UserError("O Google recusou o e-mail de edição. Use /planilha criar novamente e confira o e-mail da conta Google; vou reutilizar o arquivo já criado.") from None
                    raise
                self.bot.store.update_managed_sheet(guild.id, state="ready")
            else:
                # Reutilizar o comando nunca compartilha com outro e-mail e não cria outro arquivo.
                await sheet.metadata()
            if not cfg.get("sheet_url"):
                self.bot.store.set_guild(guild.id, sheet_url=row["url"], sheet_key=None, sheet_error=None)
                self.bot.store.queue_full_sync(str(guild.id))
            self.bot.notify_soon()
            return row["url"]

    async def initialize(self, sheet, guild, manager):
        meta = await sheet.metadata()
        properties = {"locale": sheet.locale, "timeZone": self.bot.config.timezone}
        # IMAGE precisa dessa liberação por arquivo. O Google não permite revogá-la pela API;
        # configure apenas o arquivo novo e omita o campo quando já estiver habilitado numa retomada.
        if not meta.get("properties", {}).get("importFunctionsExternalUrlAccessAllowed"):
            properties["importFunctionsExternalUrlAccessAllowed"] = True
        first = meta["sheets"][0]["properties"]
        sid = first["sheetId"]
        # Na fase de inicialização ninguém recebeu acesso ainda. O conteúdo pode ser repetido após uma queda.
        instructions = [
            [label("ARQUIVISTA DO CICLO · ",sheet.language) + guild.name],
            ["Esta planilha pertence à conta do Arquivista. O e-mail informado no Discord recebe acesso de editor."],
            ["Você pode preencher as fichas aqui ou pelo bot. O que mudar em um aparece no outro."],
            ["Abra a aba de um membro e preencha uma posição vazia com Aparência, Obra e Situação."],
            ["Para abrir uma aba para outra pessoa, use /planilha membro no Discord e selecione o @membro."],
            ["Campos editáveis: aparência, nome no servidor, obra, situação, data, link da imagem e justificativa."],
            ["Use as posições prontas. Não apague nem insira linhas; preserve as colunas de identificação e as fórmulas."],
            ["O que você editar aqui chega ao bot em cerca de 5 minutos. Se algum dado for recusado, veja o motivo no /diagnostico."],
            ["Para remover um cadastro, use /remover no Discord. Limpar uma linha não apaga o cadastro do bot."],
            ["Compartilhe edição somente com a staff: quem edita a planilha pode alterar os cadastros do servidor."],
        ]
        instructions = [[label(row[0],sheet.language)] for row in instructions]
        await self.api.request("POST", sheet.url + ":batchUpdate", body={"requests": [
            {"updateSpreadsheetProperties": {"properties": properties, "fields": ",".join(properties)}},
            {"updateSheetProperties": {"properties": {"sheetId": sid, "title": label("COMECE AQUI",sheet.language),
                "gridProperties": {"rowCount": max(30, first["gridProperties"]["rowCount"]), "columnCount": max(11, first["gridProperties"]["columnCount"])}},
                "fields": "title,gridProperties.rowCount,gridProperties.columnCount"}},
            {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 850}, "fields": "pixelSize"}},
            {"updateCells": {"start": {"sheetId": sid, "rowIndex": 0, "columnIndex": 0}, "rows": [
                {"values": [{"userEnteredValue": {"stringValue": r[0]}, "userEnteredFormat": {"wrapStrategy": "WRAP"}}]} for r in instructions],
                "fields": "userEnteredValue,userEnteredFormat"}},
        ]})
        await self.add_member(sheet, guild, manager)

    async def add_member(self, sheet, guild, member):
        actual = await self.member(guild, member)
        model, expect = await read_sheet(sheet, self.bot.sheets.actor())
        if str(actual.id) in model.broken():
            raise UserError("A aba desse membro ganhou ou perdeu linhas. Corrija a estrutura existente antes de preparar outra.")
        if not model.block_of(str(actual.id)):
            model.new_block(str(actual.id), actual.name)
            await sheet.call("write", self.bot.sheets.actor(), {"requests": model.req, "expect": expect})

    async def prepare_member(self, guild, manager, member):
        self.require_manager(guild, manager)
        manager = await self.member(guild, manager)
        self.require_manager(guild, manager)
        # Valida antes de acessar ou alterar o Google.
        await self.member(guild, member)
        async with self.bot.sheet_lock:
            cfg = self.bot.store.guild(guild.id)
            if not cfg.get("sheet_url"):
                raise UserError("Crie e conecte a planilha primeiro com /planilha criar.")
            sheet = self.bot.sheets.bridge(str(guild.id), cfg)
            await self.add_member(sheet, guild, member)
            return cfg["sheet_url"]
