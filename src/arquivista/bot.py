from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from .archive import Archive
from .config import Config, ROOT
from .domain import Actor, UserError, STAFF_ACTIONS, parse_prefix, ranked, public_record
from .media import Images
from .sheet import SheetSync
from .store import Store
from .transport import Carteiro, MENTIONS
from .views import Gate, FormLauncher, Picker, Paginator, Settings, private_reply, card, clean, channel_problem

log = logging.getLogger(__name__)
PUBLIC = frozenset(("ajuda", "aparencias", "minhas", "galeria", "consultar"))

HELP = """**Consultar o arquivo**
`AC:aparencias [@membro]` (`AC:ap`) — lista paginada.
`AC:minhas` (`AC:min`) — suas aparências.
`AC:galeria [nome] [@membro]` (`AC:gal`) — uma imagem por página.
`AC:consultar nome` (`AC:busca`) — busca aproximada; refine com a obra.

**Seu cadastro**
`AC:registrar` (`AC:reg`) — abrir formulário, revisar e confirmar.
`AC:editar nome` (`AC:ed`) — editar nome no servidor e imagem.
Pode anexar uma imagem à mensagem de registrar/editar, após a staff configurar o canal de imagens.

Também existem comandos de barra `/`. `ac:` e espaços depois de `AC:` são aceitos.
Não publique situação ou justificativa como argumentos: use o painel privado."""
STAFF_HELP = """

**Staff**
`AC:registrar @membro` — cadastrar para outra pessoa.
`AC:situacao nome` (`AC:sit`) — situação e justificativa internas.
`AC:transferir nome @membro` (`AC:tr`) — preservar identidade e data.
`AC:remover nome` (`AC:rm`) — remoção com confirmação e auditoria.
`AC:historico nome` (`AC:hist`) — histórico privado, inclusive removidos.
`AC:registrarhistorico` / `AC:desativarhistorico` — canal de notificações.
`AC:registrarimagens` / `AC:desativarimagens` — canal para preservar anexos.
`AC:status` (`AC:st`) — diagnóstico privado do arquivo deste servidor.

**Gerência do servidor**
`AC:configurar` (`AC:cfg`) — cargos de staff, canais e planilha.
"""

SHEET_ERRORS = {"AUTH": "a planilha recusou a chave ou a URL; conecte de novo no /configurar",
    "GUILD": "a planilha foi instalada com o ID de outro servidor; reinstale pelo menu Arquivista",
    "CLOCK": "o relógio da hospedagem está errado", "LOGIN": "a implantação do App da Web não está com acesso \"Qualquer pessoa\"",
    "BUSY": "a planilha demorou a responder; vou tentar de novo", "NOT_READY": "o script da planilha não foi instalado",
    "KEY": "a chave guardada não abre mais (o token do bot mudou?); conecte de novo no /configurar",
    "INVALID": "a planilha recusou o pedido; confira se o script está na versão nova", "INTERNAL": "erro dentro do script da planilha"}

class Arquivista(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True
        # Sem Presence Intent ou lista completa de membros: resolução é sob demanda.
        super().__init__(command_prefix="AC:", intents=intents, help_command=None,
                         allowed_mentions=MENTIONS, max_messages=300)
        self.config = config
        self.store = Store(config.db_path)
        self.carteiro = Carteiro(self)
        self.images = Images(self)
        self.session: aiohttp.ClientSession | None = None
        self.notice_lock = asyncio.Lock()
        self.sheets = SheetSync(self)
        self.sheet_lock = asyncio.Lock()
        self.last_use: dict[int, float] = {}
        self.last_mention: dict[int, float] = {}
        self.last_sync: str | None = None
        self.sync_problem: str | None = None
        self.avatar_checked = False
        install_slash_commands(self)
    async def setup_hook(self):
        self.session = aiohttp.ClientSession(headers={"User-Agent":"ArquivistaDoCiclo/0.2"})
        if self.config.dev_guild_id:
            # Servidor de testes: comandos só nele e na hora. Sem ele, valem em todos (o Discord leva até 1 h).
            if self.store.adopt_legacy(self.config.dev_guild_id, self.config.legacy_staff_roles):
                log.info("Configuração da v0.2 levada para o servidor %s.", self.config.dev_guild_id)
            guild = discord.Object(id=self.config.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        self.worker.change_interval(seconds=self.config.poll_seconds)
        self.worker.start()
    async def on_ready(self):
        log.info("Arquivista conectado em %d servidor(es).", len(self.guilds))
        if self.avatar_checked:
            return
        self.avatar_checked = True
        if self.config.configure_avatar:
            data = (ROOT / "assets" / "amiya.png").read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if self.store.get("avatar_hash") != digest:
                try:
                    await self.user.edit(avatar=data)
                    self.store.set("avatar_hash", digest)
                except discord.HTTPException:
                    log.warning("Não foi possível atualizar o avatar automaticamente. Ajuste-o no Developer Portal.")
        await self.change_presence(activity=discord.Game(name="AC:ajuda · arquivos do Ciclo"))
    def archive(self, guild_id: int) -> Archive:
        if not guild_id:
            raise UserError("Use este comando dentro de um servidor.")
        return Archive(self.store, guild_id, self.config.timezone)
    def can_configure(self, member) -> bool:
        guild = getattr(member, "guild", None)
        perms = getattr(member, "guild_permissions", None)
        return bool(guild and perms and (member.id == guild.owner_id or perms.administrator or perms.manage_guild))
    def is_staff_member(self, member) -> bool:
        guild = getattr(member, "guild", None)
        if not guild or not hasattr(member, "roles"):
            return False
        roles = set(self.store.guild(guild.id)["staff_roles"])
        return self.can_configure(member) or any(str(role.id) in roles for role in member.roles)
    async def actor(self, user_id: int | str, guild_id: int | None) -> Actor:
        guild = self.get_guild(guild_id) if guild_id else None
        if not guild:
            raise UserError("Não encontrei este servidor. Confira se o Arquivista ainda está nele.")
        try:
            # Revalida no Discord em vez de confiar em um painel aberto antes da remoção de um cargo.
            member = await guild.fetch_member(int(user_id))
        except (discord.NotFound, ValueError, TypeError):
            raise UserError("Essa pessoa não foi encontrada neste servidor.") from None
        return Actor(str(member.id), member.display_name, self.is_staff_member(member))
    def service_actor(self) -> Actor:
        return Actor(str(self.user.id), "Arquivista · sincronização", True)
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.webhook_id or not message.guild:
            return
        parsed = parse_prefix(message.content)
        if parsed:
            action, query, member_id = parsed
            attachment = message.attachments[0] if message.attachments else None
            await self.run_action(message, action, query, member_id, attachment)
            return
        is_reply = message.reference and message.reference.message_id and self.store.is_ours(message.reference.message_id)
        if any(user.id == self.user.id for user in message.mentions) or is_reply:
            now = time.monotonic()
            if now-self.last_mention.get(message.author.id, -1000) < 8:
                return
            self.last_mention[message.author.id] = now
            await self.carteiro.send(message.channel, embed=card("Amiya · Arquivista do Ciclo",
                "Estou aqui. Posso consultar as aparências do arquivo ou ajudar com seu cadastro.\n\n"
                "Use **AC:ajuda**, **AC:galeria** ou **AC:registrar**. Você também pode usar os comandos de barra."))
    async def reply_public(self, source, *, embed, view=None):
        interaction = source if isinstance(source, discord.Interaction) else None
        if interaction and not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=True)
        result = await self.carteiro.send(source.channel, embed=embed, view=view)
        if interaction:
            await interaction.edit_original_response(content="Apresentei o arquivo pela Amiya neste canal.", allowed_mentions=MENTIONS)
        return result
    async def failure(self, source, error):
        text = str(error) if isinstance(error,UserError) else "Não consegui concluir essa etapa. A staff pode conferir o diagnóstico; não presuma que uma gravação foi confirmada."
        if isinstance(source,discord.Interaction):
            await private_reply(source,content=text)
        else:
            await self.carteiro.send(source.channel,embed=card("Amiya · Atenção",text))
        if not isinstance(error,UserError):
            log.warning("Falha de comando: %s",type(error).__name__)
    async def run_action(self, source, action, query="", member_id=None, attachment=None):
        user = source.user if isinstance(source,discord.Interaction) else source.author
        gid = source.guild_id if isinstance(source,discord.Interaction) else source.guild.id
        if not gid:
            return
        try:
            now=time.monotonic()
            if now-self.last_use.get(user.id,-1000)<2:
                raise UserError("Aguarde dois segundos antes de abrir outro comando.")
            self.last_use[user.id]=now
            if action=="unknown":
                raise UserError("Não reconheci esse comando. Use AC:ajuda para abrir o índice.")
            if isinstance(source,discord.Interaction) and not source.response.is_done():
                await source.response.defer(ephemeral=True,thinking=True)
            actor=await self.actor(user.id,gid)
            if action in STAFF_ACTIONS and not actor.staff:
                raise UserError("Esse comando é exclusivo da staff.")
            if action not in PUBLIC:
                if action=="transferir" and not member_id:
                    raise UserError("Use AC:transferir nome da aparência @responsável.")
                if action in ("editar","situacao","transferir","remover") and not query.strip():
                    raise UserError("Informe o nome da aparência depois do comando. O bot apresentará opções quando houver mais de uma.")
                if isinstance(source,discord.Interaction):
                    await self.open_private(source,action,query,member_id,attachment)
                else:
                    gate=Gate(self,user.id,action,query,member_id,attachment)
                    await self.reply_public(source,embed=card("Amiya · Atendimento", "Abra o painel para continuar. As informações internas não serão publicadas neste canal."),view=gate)
                return
            if action=="ajuda":
                await self.reply_public(source,embed=card("Índice do Arquivista",HELP+(STAFF_HELP if actor.staff else "")))
                return
            owner_id=str(user.id) if action=="minhas" else (str(member_id) if member_id else "")
            # Consultar mostra somente registros ocupados. Ausência não prova nome não padronizado.
            data=await self.archive(gid).call("list",actor,{"owner_id":owner_id,"include_released":False})
            records=ranked([public_record(r) for r in data["records"]],query)
            mode="gallery" if action in ("galeria","consultar") else "list"
            view=Paginator(self,user.id,records,mode,actor=actor,guild_id=gid)
            await self.reply_public(source,embed=await view.embed(),view=view if records else None)
        except Exception as exc:
            await self.failure(source,exc)
    async def open_private(self, i, action, query="", member_id=None, attachment=None):
        try:
            actor=await self.actor(i.user.id,i.guild_id)
            archive=self.archive(i.guild_id)
            if action in STAFF_ACTIONS and not actor.staff:
                raise UserError("Esse comando é exclusivo da staff.")
            if action=="configurar":
                if not self.can_configure(i.user):
                    raise UserError("Só quem pode gerenciar o servidor configura o Arquivista.")
                v=Settings(self,i.user.id,i.guild)
                await private_reply(i,embed=v.embed(),view=v)
            elif action=="registrar":
                owner=await self.actor(member_id,i.guild_id) if member_id else actor
                if owner.id!=actor.id and not actor.staff:
                    raise UserError("Você pode cadastrar para si. Apenas a staff cadastra para terceiros.")
                v=FormLauncher(self,i.user.id,"create",owner={"id":owner.id,"name":owner.name},attachment=attachment)
                await private_reply(i,embed=self.carteiro.decorate(card("Nova aparência",f"Responsável: <@{owner.id}>.\nPreencha os dados, revise e confirme. Vou conferir a disponibilidade antes de salvar.")),view=v)
            elif action in ("editar","situacao","transferir","remover"):
                data=await archive.call("list",actor,{"owner_id":"" if actor.staff else actor.id,"include_released":True})
                records=ranked(data["records"],query,limit=250)
                if not records:
                    raise UserError("Não encontrei um cadastro correspondente que você possa gerenciar.")
                v=Picker(self,i.user.id,records,action,member_id,attachment)
                await private_reply(i,content=f"Encontrei {len(records)} opção(ões). Selecione pela aparência e obra; nenhuma alteração foi feita.",view=v)
            elif action=="historico":
                data=await archive.call("history",actor,{"query":query})
                v=Paginator(self,i.user.id,data["events"],"history",actor=actor,guild_id=i.guild_id)
                await private_reply(i,content="Exibindo os eventos mais recentes; a auditoria original foi preservada." if data.get("truncated") else None,embed=await v.embed(),view=v if data["events"] else None)
            elif action=="status":
                data=await archive.call("status",actor)
                cfg=self.store.guild(i.guild_id)
                channel=lambda c:f"<#{c}>" if c else "não configurado"
                body=(f"**Cadastros:** {data['records']} ({data['occupied']} ocupando aparência)\n**Membros com cadastro:** {data['members']}\n"
                      f"**Eventos na auditoria:** {data['events']}\n**Avisos esperando envio:** {data['pending_notices']}\n"
                      f"**Canal de histórico:** {channel(cfg['log_channel'])}\n**Canal de imagens:** {channel(cfg['image_channel'])}\n"
                      f"**Cargos de staff:** {', '.join(f'<@&{r}>' for r in cfg['staff_roles']) or 'só dono e quem gerencia o servidor'}\n"
                      f"**Último envio de avisos:** {self.last_sync or 'ainda não realizado'}\n**Situação operacional:** {self.sync_problem or 'sem erro registrado nesta sessão'}")
                if cfg.get("sheet_url"):
                    queued,bad=self.store.sheet_pending(i.guild_id)
                    body+=(f"\n**Planilha:** conectada · {queued} mudança(s) esperando envio"+(f", {bad} recusada(s) pela planilha" if bad else "")+
                           f"\n**Último envio para a planilha:** {cfg.get('sheet_ok') or 'ainda não realizado'}"+
                           (f"\n**Último erro da planilha:** {SHEET_ERRORS.get(cfg['sheet_error'],cfg['sheet_error'])}" if cfg.get("sheet_error") else ""))
                else:
                    body+="\n**Planilha:** não conectada"
                await private_reply(i,embed=self.carteiro.decorate(card("Diagnóstico privado",body)))
            elif action in ("registrar_historico","registrar_imagens"):
                channel=i.channel
                if not isinstance(channel,(discord.TextChannel,discord.Thread)):
                    raise UserError("Use um canal de texto ou um tópico deste servidor.")
                problem=channel_problem(channel,images=action=="registrar_imagens")
                if problem:
                    raise UserError(problem)
                if action=="registrar_historico":
                    self.store.set_guild(i.guild_id,log_channel=channel.id)
                    message="Este canal receberá os próximos cadastros e alterações. Situação, justificativa e nome interno não aparecem nas notificações públicas. Não vou republicar o passado."
                else:
                    self.store.set_guild(i.guild_id,image_channel=channel.id)
                    message="Este canal preservará as imagens anexadas nos futuros cadastros. Não apague essas mensagens: elas são a fonte recuperável dos arquivos."
                await private_reply(i,embed=self.carteiro.decorate(card("Canal configurado",message)))
            elif action in ("desativar_historico","desativar_imagens"):
                self.store.set_guild(i.guild_id,**{"log_channel" if action=="desativar_historico" else "image_channel":None})
                await private_reply(i,content="Configuração desativada. Nenhum registro histórico ou arquivo antigo foi apagado.")
            else:
                raise UserError("Operação não reconhecida.")
        except Exception as exc:
            await self.failure(i,exc)
    @tasks.loop(seconds=90)
    async def worker(self):
        # Rede de segurança: cada gravação já pede o envio na hora; aqui saem as retentativas.
        await self.deliver_events()
        await self.sync_sheets()
    @worker.before_loop
    async def before_worker(self):
        await self.wait_until_ready()
    def notify_soon(self):
        loop=asyncio.get_running_loop()
        loop.create_task(self.deliver_events())
        loop.create_task(self.sync_sheets())
    def now_text(self)->str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    async def sync_sheets(self):
        if self.sheet_lock.locked():
            return  # o envio em andamento pega o que entrou na fila
        async with self.sheet_lock:
            await self.sheets.run()
    async def deliver_events(self):
        if self.notice_lock.locked():
            return  # já tem um envio rodando; ele pega os avisos novos
        async with self.notice_lock:
            try:
                await self.deliver_pending()
                self.last_sync=datetime.now().astimezone().isoformat(timespec="seconds")
                self.sync_problem=None
            except Exception as exc:
                self.sync_problem="Falha ao enviar avisos de histórico; verifique os registros da hospedagem."
                log.warning("Falha nos avisos: %s",type(exc).__name__)
    async def deliver_pending(self):
        for row in self.store.pending():
            event=json.loads(row["data"])
            channel_id=self.store.guild(row["guild_id"]).get("log_channel")
            if not channel_id:
                self.store.delivered(event["event_id"])  # canal desligado depois do evento
                continue
            try:
                self.store.attempt(event["event_id"])
                channel=self.get_channel(int(channel_id)) or await self.fetch_channel(int(channel_id))
                if not getattr(channel,"guild",None) or str(channel.guild.id)!=row["guild_id"]:
                    raise UserError("Canal de histórico fora do servidor do evento.")
                # Recuperação do pequeno intervalo entre Discord aceitar e SQLite confirmar.
                found=None
                if row["tries"]:
                    try:
                        await self.carteiro.webhook(channel.parent if isinstance(channel,discord.Thread) else channel)
                    except (discord.HTTPException,AttributeError):
                        pass
                    async for old in channel.history(limit=100):
                        if (old.author.id==self.user.id or self.store.is_ours(old.id) or
                            (old.webhook_id and old.webhook_id in {w.id for w in self.carteiro.cache.values()})):
                            if any(str(e.footer.text or "")==f"Evento {event['event_id']}" for e in old.embeds):
                                found=old
                                break
                if found is None:
                    titles={"created":"Aparência registrada","removed":"Cadastro removido","transferred":"Responsável alterado","updated":"Cadastro atualizado"}
                    actor=f"<@{event['actor_id']}>" if event.get("actor_id") else "Planilha; autor não identificado"
                    e=card(titles.get(event["kind"],"Cadastro atualizado"),
                        f"**Aparência:** {clean(event['appearance'],200)}\n**Obra:** {clean(event['work'],200)}\n**Responsável:** <@{event['owner_id']}>\n**Registro da alteração:** {actor}")
                    e.set_footer(text=f"Evento {event['event_id']}")
                    try:e.timestamp=datetime.fromisoformat(event["at"].replace("Z","+00:00"))
                    except ValueError:pass
                    found=await self.carteiro.send(channel,embed=e)
                self.store.delivered(event["event_id"],str(found.id),str(channel.id))
            except Exception as exc:
                self.store.failed(event["event_id"],row["tries"])
                log.warning("Notificação pendente %s: %s",event["event_id"],type(exc).__name__)
    async def close(self):
        self.worker.cancel()
        if self.session:
            await self.session.close()
        self.store.close()
        await super().close()


def install_slash_commands(bot):
    """As duas entradas usam o mesmo run_action e as mesmas permissões."""
    @bot.tree.command(name="ajuda",description="Abra o índice de comandos da Amiya.")
    @app_commands.guild_only()
    async def ajuda(i:discord.Interaction):await bot.run_action(i,"ajuda")
    @bot.tree.command(name="aparencias",description="Lista paginada de aparência e responsável.")
    @app_commands.guild_only()
    async def aparencias(i:discord.Interaction,membro:discord.Member|None=None):await bot.run_action(i,"aparencias",member_id=membro.id if membro else None)
    @bot.tree.command(name="minhas",description="Consulte suas próprias aparências.")
    @app_commands.guild_only()
    async def minhas(i:discord.Interaction):await bot.run_action(i,"minhas")
    @bot.tree.command(name="galeria",description="Veja as imagens; filtre por pessoa ou nome aproximado.")
    @app_commands.guild_only()
    async def galeria(i:discord.Interaction,nome:str="",membro:discord.Member|None=None):await bot.run_action(i,"galeria",nome,membro.id if membro else None)
    @bot.tree.command(name="consultar",description="Procure uma aparência ocupada pelo nome e pela obra.")
    @app_commands.guild_only()
    async def consultar(i:discord.Interaction,nome:str,obra:str=""):await bot.run_action(i,"consultar",f"{nome} {obra}".strip())
    @bot.tree.command(name="registrar",description="Cadastre uma aparência para si; staff também cadastra para terceiros.")
    @app_commands.guild_only()
    async def registrar(i:discord.Interaction,membro:discord.Member|None=None,imagem:discord.Attachment|None=None):await bot.run_action(i,"registrar",member_id=membro.id if membro else None,attachment=imagem)
    @bot.tree.command(name="editar",description="Altere um cadastro permitido em formulário privado.")
    @app_commands.guild_only()
    async def editar(i:discord.Interaction,personagem:str,imagem:discord.Attachment|None=None):await bot.run_action(i,"editar",personagem,attachment=imagem)
    @bot.tree.command(name="situacao",description="Staff: altere situação e justificativa internas.")
    @app_commands.guild_only()
    async def situacao(i:discord.Interaction,personagem:str):await bot.run_action(i,"situacao",personagem)
    @bot.tree.command(name="transferir",description="Staff: transfira a aparência preservando ID e data.")
    @app_commands.guild_only()
    async def transferir(i:discord.Interaction,personagem:str,membro:discord.Member):await bot.run_action(i,"transferir",personagem,membro.id)
    @bot.tree.command(name="remover",description="Staff: remova o cadastro com confirmação e auditoria.")
    @app_commands.guild_only()
    async def remover(i:discord.Interaction,personagem:str):await bot.run_action(i,"remover",personagem)
    @bot.tree.command(name="historico",description="Staff: consulte o histórico detalhado em privado.")
    @app_commands.guild_only()
    async def historico(i:discord.Interaction,personagem:str=""):await bot.run_action(i,"historico",personagem)
    @bot.tree.command(name="registrar_historico",description="Staff: use este canal para futuras notificações públicas.")
    @app_commands.guild_only()
    async def registrar_historico(i:discord.Interaction):await bot.run_action(i,"registrar_historico")
    @bot.tree.command(name="desativar_historico",description="Staff: desative notificações sem apagar a auditoria.")
    @app_commands.guild_only()
    async def desativar_historico(i:discord.Interaction):await bot.run_action(i,"desativar_historico")
    @bot.tree.command(name="registrar_imagens",description="Staff: preserve neste canal as imagens anexadas ao cadastro.")
    @app_commands.guild_only()
    async def registrar_imagens(i:discord.Interaction):await bot.run_action(i,"registrar_imagens")
    @bot.tree.command(name="desativar_imagens",description="Staff: pare novos uploads sem apagar os arquivos existentes.")
    @app_commands.guild_only()
    async def desativar_imagens(i:discord.Interaction):await bot.run_action(i,"desativar_imagens")
    @bot.tree.command(name="configurar",description="Gerência: cargos de staff e canais do Arquivista neste servidor.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def configurar(i:discord.Interaction):await bot.run_action(i,"configurar")
    @bot.tree.command(name="status",description="Staff: diagnóstico privado da ponte e do histórico.")
    @app_commands.guild_only()
    async def status(i:discord.Interaction):await bot.run_action(i,"status")
    @bot.tree.error
    async def error(i:discord.Interaction,error:app_commands.AppCommandError):
        await bot.failure(i,error)

class Redact(logging.Filter):
    def __init__(self,*secrets):
        super().__init__();self.secrets=[x for x in secrets if x]
    def filter(self,record):
        msg=record.getMessage()
        for value in self.secrets:msg=msg.replace(value,"[SEGREDO OCULTO]")
        record.msg,record.args=msg,()
        return True

def main():
    try:config=Config.load()
    except (ValueError,OSError) as exc:raise SystemExit(str(exc)) from None
    handler=logging.StreamHandler()
    handler.addFilter(Redact(config.token))
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO,handlers=[handler])
    Arquivista(config).run(config.token,log_handler=None)
