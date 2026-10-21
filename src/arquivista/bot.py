from __future__ import annotations
import asyncio
import hashlib
import io
import json
import logging
import re
import time
from datetime import datetime

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from . import backup, __version__
from .archive import Archive
from .config import Config, ROOT
from .docs import DATA_LINKS, SETUP_LINK, SCRIPT_UPDATE
from .domain import Actor, UserError, STAFF_ACTIONS, find_work, parse_prefix, ranked, public_record, search_text, work_groups, work_key
from .importer import apply, check
from .media import Images
from .sheet import SheetSync
from .managed import ManagedSheets
from .google import GoogleError
from .store import Store
from .idiomas import preparar_interface, arvore_e_tradutor, preparar, definir, atual, tr, usar

ArvoreLocalizada, Tradutor = arvore_e_tradutor()
from .transport import Carteiro, MENTIONS
from .views import Confirm, Gate, Guide, RestoreConfirm, Picker, Paginator, RecordModal, Settings, backup_problem, private_reply, card, clean

log = logging.getLogger(__name__)
PUBLIC = frozenset(("ajuda", "guia", "aparencias", "minhas", "galeria", "consultar", "obra"))
SLASH = ("language","idioma","ajuda", "guia", "aparencias", "obra", "registrar", "editar", "situacao", "transferir", "remover", "limpar", "apelido", "historico", "configurar", "restaurar", "planilha", "diagnostico")

HELP = """**Consultar o arquivo**
`/aparencias` ou `AC:ap [aparência] [@membro]` — consulte a lista. Use **Ver em galeria** para ver as imagens.
`AC:min` — veja suas aparências. `AC:gal` — abra a galeria.
`/obra` ou `AC:obra [nome]` — busque pela obra. A busca aceita abreviações e pequenos erros de digitação. Sem nome, mostra as obras cadastradas.

`/guia` ou `AC:guia` — comece por aqui se for sua primeira vez.

**Seu cadastro**
`/registrar` ou `AC:reg` — preencha a ficha, confira os dados e confirme.
`/editar` ou `AC:ed aparência` — altere o nome do personagem no servidor ou a imagem.
`/remover` ou `AC:rm aparência` — remova um cadastro seu, com confirmação.

Os nomes completos também valem (`AC:registrar`, `AC:galeria`...). `ac:` minúsculo funciona.
Situação e justificativa não aparecem nas consultas públicas.""" + "\n\n" + DATA_LINKS
STAFF_HELP = """

**Equipe autorizada (staff)**
`AC:reg @membro` — cadastrar para outra pessoa.
`/situacao` ou `AC:sit aparência` — situação e justificativa internas.
`/transferir` ou `AC:tr aparência @membro` — mudar o responsável, mantendo o identificador do cadastro (ID) e a data.
`/remover` ou `AC:rm aparência` — a staff também pode remover cadastros de outras pessoas.
`/limpar` ou `AC:limpar @membro` — apagar todos os cadastros de alguém (vale o ID de quem já saiu; só `AC:limpar` lista quem saiu).
`/apelido` ou `AC:apelido JJK = Jujutsu Kaisen` — apelido de obra para a busca por obra. `AC:apelido -JJK` tira; `AC:apelido` lista.
`/historico` ou `AC:hist [aparência]` — histórico privado, inclusive removidos.
`/diagnostico` ou `AC:diag` — estado do arquivo, dos canais e da planilha.

**Gerência do servidor**
`/configurar` ou `AC:cfg` — escolha os cargos de staff, os canais e a frequência do backup; conecte a planilha.
`/language` ou `/idioma` — mude o idioma das respostas; exige gerência ou cargo de staff. Só planilhas novas usam o novo idioma. A configuração das Guias é independente.
`/restaurar` ou `AC:restaurar` com o arquivo de backup (.json) anexado — recupere os cadastros salvos. Confira o resumo antes de confirmar.
`/planilha criar` — informe seu e-mail Google em privado para receber a planilha pronta, com acesso de editor. Se ela já existe, abre o mesmo arquivo.
`/planilha abrir` ou `AC:planilha` — recupere o link e abra o painel da planilha.
`/planilha membro` — selecione um @membro do servidor para preparar a aba antes de preencher à mão.
""" + "\n" + SETUP_LINK

# Guia em páginas (AC:guia). As duas últimas só aparecem para a staff.
GUIDE = (
    ("O que é o arquivo",
     "Aqui fica registrado quem usa cada **aparência**: o personagem (ou a pessoa) que você usa no servidor, junto com a **obra** de onde ele vem.\n\n"
     "A combinação de aparência e obra só pode estar ocupada por uma pessoa de cada vez. Consulte a lista antes de escolher; ao salvar, eu confiro se já existe um cadastro.\n\n"
     "**AC:** é o prefixo dos comandos da **Arquivista do Ciclo**. Use **Próxima** para continuar.\n\n" + DATA_LINKS),
    ("Como consultar aparências",
     "`AC:ap Takao` ou `/aparencias` — busque pelo nome e veja quem usa a aparência. Pequenos erros de digitação também são aceitos.\n"
     "`AC:gal` — o mesmo, mas uma por página, com imagem.\n"
     "`AC:obra arknights` ou `/obra` — tudo de uma obra, juntando jeitos diferentes de escrever o nome.\n"
     "`AC:ap @membro` — as aparências de alguém. `AC:min` — as suas.\n\n"
     "Se não encontrar, tente também o nome da obra: a aparência pode ter sido cadastrada com outra grafia."),
    ("Como cadastrar sua aparência",
     "`AC:reg` ou `/registrar` abre um formulário com:\n"
     "• **Aparência** — o nome do personagem;\n• **Obra** — de onde ele vem;\n"
     "• **Nome no servidor** (opcional) — como o seu personagem se chama aqui; aparece na lista e na galeria;\n"
     "• **Imagem** — cole um link direto da imagem que comece com `https://` ou anexe a imagem à mensagem do comando antes de abrir o formulário.\n\n"
     "Depois, confira os dados numa mensagem que só você vê, escolha a situação e clique em **Confirmar e salvar**. Se não escolher, fica **Em preparação**. Se a aparência estiver ocupada, eu aviso sem salvar outro cadastro."),
    ("Como editar ou remover seu cadastro",
     "`AC:ed nome` ou `/editar` — muda o nome no servidor ou a imagem. Para tirar a imagem, escreva `-` no campo.\n\n"
     "`/remover` ou `AC:rm nome` — remove um cadastro seu, depois da sua confirmação. A aparência fica livre e o histórico continua guardado para a equipe autorizada (staff).\n\n"
     "Depois do cadastro, só a staff pode mudar a aparência, a obra ou a situação. Editar ou remover cadastros de outras pessoas também exige staff."),
    ("O que cada situação significa",
     "**Em preparação** — reservada, ainda sendo montada.\n**Em uso** — sendo usada.\n"
     "**Arquivado** — fora de uso, mas continua ocupada.\n**Liberado** — livre para outra pessoa.\n\n"
     "A situação e a justificativa ficam só nos painéis privados; as listas públicas não mostram."),
    ("Ações da equipe autorizada",
     "`AC:sit nome` — situação e justificativa. `AC:tr nome @membro` — muda o dono.\n"
     "`AC:rm nome` — remove um cadastro. `AC:limpar @membro` — apaga todos de alguém (vale o ID de quem saiu).\n"
     "`AC:apelido JJK = Jujutsu Kaisen` — apelido de obra para a busca.\n"
     "`AC:hist` — mudanças recentes, inclusive de cadastros removidos. `AC:diag` — veja se o bot e a planilha estão funcionando.\n\n"
     "**ID** é o número ou código que identifica um cadastro ou uma conta do Discord. "
     "**Staff** é a equipe autorizada a cuidar dos cadastros.\n\n"
     "Antes de transferir, remover ou mudar a situação, confira a ficha selecionada e confirme. O histórico do cadastro fica guardado."),
    ("Configurar o servidor e a planilha",
     "`/configurar` (dono, Administrador ou Gerenciar Servidor):\n"
     "• cargos de staff;\n• canal de histórico (avisos de cada mudança);\n• canal de imagens (guarda os anexos);\n"
     "• planilha para editar as fichas pelo Google Sheets;\n• backup automático num canal só da staff.\n\n"
     "Use `/planilha criar` e informe seu e-mail Google no formulário privado. Você recebe o arquivo pronto e pode editá-lo. "
     "Para abrir novamente, use `/planilha abrir` ou `AC:planilha`.\n"
     "Quer uma aba para outra pessoa? Use `/planilha membro` e selecione o @membro do servidor. "
     "Preencha as posições prontas; as edições no Sheets chegam ao bot em cerca de 5 minutos. Compartilhe edição só com a staff.\n\n"
     "Em **Backup**, escolha o canal e a frequência. **Fazer backup agora** envia uma cópia na hora. Para recuperar os cadastros, anexe o arquivo de backup `.json` ao `/restaurar`. JSON é o formato desse arquivo de dados; guarde-o sem editar o conteúdo.\n\n"
     "Use `/language` ou `/idioma` para escolher português ou inglês. A staff também pode mudar o idioma. Os arquivos já criados mantêm a língua original; só planilhas novas usam a língua escolhida. Essa opção é independente do idioma das Guias.\n\n"
     "Para as mensagens saírem com a foto da Amiya, o bot precisa da permissão **Gerenciar Webhooks**.\n\n" + SETUP_LINK),
)
STAFF_PAGES = 2

SHEET_ERRORS = {"AUTH": "a planilha recusou a chave ou a URL; conecte de novo no /configurar",
    "GUILD": "a planilha foi instalada com o ID de outro servidor; reinstale pelo menu Arquivista",
    "CLOCK": "o relógio da hospedagem está errado", "LOGIN": "a implantação do App da Web não está com acesso \"Qualquer pessoa\"",
    "BUSY": "a planilha demorou a responder; vou tentar de novo", "NOT_READY": "o script da planilha não foi instalado",
    "KEY": "a chave guardada não abre mais (o token do bot mudou?); conecte de novo no /configurar",
    "INVALID": "a planilha recusou o pedido; confira se o script está na versão nova",
    "OLD_SCRIPT": SCRIPT_UPDATE,
    "OLD_BOT": "o script da planilha é mais novo que o bot; atualize o bot",
    "CHANGED": "a planilha mudou enquanto eu gravava; vou tentar de novo", "INTERNAL": "erro na integração da planilha; avise o mantenedor"}
with usar('pt-BR'):
    SHEET_ERRORS.update({code: str(GoogleError(code)) for code in
        ("GOOGLE_SETUP", "GOOGLE_AUTH", "GOOGLE_ACCESS", "GOOGLE_MISSING", "GOOGLE_LOCALE", "GOOGLE_INVALID", "GOOGLE_STORAGE")})

class Arquivista(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True
        # Sem Presence Intent ou lista completa de membros: resolução é sob demanda.
        super().__init__(command_prefix="AC:", intents=intents, help_command=None,
                         allowed_mentions=MENTIONS, max_messages=300, tree_cls=ArvoreLocalizada)
        self.config = config
        self.store = Store(config.db_path)
        self.carteiro = Carteiro(self)
        self.images = Images(self)
        self.session: aiohttp.ClientSession | None = None
        self.notice_lock = asyncio.Lock()
        self.sheets = SheetSync(self)
        self.managed = ManagedSheets(self)
        self.sheet_lock = asyncio.Lock()
        self.last_use: dict[int, float] = {}
        self.last_mention: dict[int, float] = {}
        self.last_sync: str | None = None
        self.sync_problem: str | None = None
        self.avatar_checked = False
        self.background: set[asyncio.Task] = set()
        self.add_listener(self.expired_panel, "on_interaction")
        install_slash_commands(self)
    async def setup_hook(self):
        await self.tree.set_translator(Tradutor())
        self.session = aiohttp.ClientSession(headers={"User-Agent":f"ArquivistaDoCiclo/{__version__}"})
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
    async def expired_panel(self, i: discord.Interaction):
        """Botão de um painel aberto antes do bot reiniciar: ninguém mais escuta, e o Discord mostraria
        "Esta interação falhou". Se nada respondeu em 2,5 s, avisa para abrir o comando de novo."""
        if i.type != discord.InteractionType.component:
            return
        await asyncio.sleep(2.5)
        if i.response.is_done():
            return
        try:
            await i.response.send_message(tr('Este painel expirou. Isso acontece após uma atualização ou um tempo sem uso. Abra o comando novamente.'),
                                          ephemeral=True)
        except discord.HTTPException:
            pass  # o painel respondeu no meio tempo
    def archive(self, guild_id: int) -> Archive:
        if not guild_id:
            raise UserError(tr('Use este comando dentro de um servidor.'))
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
    async def change_language(self, i, language=None):
        if not i.guild_id or getattr(getattr(i.user,"guild",None),"id",None) != i.guild_id or not self.is_staff_member(i.user):
            text="You need Manage Server or a configured staff role." if i.guild_id and self.store.guild(i.guild_id).get("language")=="en" else "Você precisa de Gerenciar servidor ou de um cargo de staff configurado."
            return await private_reply(i,content=text)
        if language is not None:
            self.store.set_guild(i.guild_id,language=language)
        language=self.store.guild(i.guild_id).get("language","pt-BR")
        definir(language)
        text=("Server language: **English**. New spreadsheets will be created in English. Existing files keep their original language and are not reformatted. This setting does not change the Guides bot." if language=="en" else
              "Idioma do servidor: **Português do Brasil**. Novas planilhas serão criadas em português. Arquivos existentes conservam o idioma original e não são reformatados. Esta opção não muda as Guias.")
        return await private_reply(i,content=text)

    async def actor(self, user_id: int | str, guild_id: int | None) -> Actor:
        guild = self.get_guild(guild_id) if guild_id else None
        if not guild:
            raise UserError(tr('Não encontrei este servidor. Confira se o Arquivista ainda está nele.'))
        try:
            # Revalida no Discord em vez de confiar em um painel aberto antes da remoção de um cargo.
            member = await guild.fetch_member(int(user_id))
        except (discord.NotFound, ValueError, TypeError):
            raise UserError(tr('Essa pessoa não foi encontrada neste servidor.')) from None
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
        # O conteúdo precisa mencionar a conta ou o cargo automático deste bot.
        # Cargos genéricos, @everyone e @here não são chamados para a Amiya.
        direct = (any(user.id == self.user.id for user in message.mentions)
                  and re.search(rf"<@!?{self.user.id}>", message.content) is not None)
        own_role = any(role.tags and role.tags.bot_id == self.user.id
                       and f"<@&{role.id}>" in message.content for role in message.role_mentions)
        is_reply = (not message.mention_everyone and message.reference and message.reference.message_id
                    and self.store.is_ours(message.reference.message_id))
        if direct or own_role or is_reply:
            preparar(self,message.guild.id)
            now = time.monotonic()
            if now-self.last_mention.get(message.author.id, -1000) < 8:
                return
            self.last_mention[message.author.id] = now
            await self.carteiro.send(message.channel, embed=card("Amiya · Arquivista do Ciclo",
                tr('Estou aqui. Posso consultar as aparências do arquivo ou ajudar com seu cadastro.\n\nUse **AC:ajuda**, **AC:gal** ou **AC:reg**, ou os comandos de barra.')))
    async def reply_public(self, source, *, embed, view=None):
        interaction = source if isinstance(source, discord.Interaction) else None
        if interaction and not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=True)
        result = await self.carteiro.send(source.channel, embed=embed, view=view)
        if interaction:
            try:
                await interaction.delete_original_response()  # a resposta é a mensagem da Amiya no canal
            except discord.HTTPException:
                pass
        return result
    async def failure(self, source, error):
        text = str(error) if isinstance(error,UserError) else tr("Não consegui confirmar se a alteração foi salva. Confira a ficha antes de tentar de novo; a staff pode consultar o /diagnostico.")
        if isinstance(source,discord.Interaction):
            await private_reply(source,content=text)
        else:
            await self.carteiro.send(source.channel,embed=card(tr('Amiya · Atenção'),text))
        if not isinstance(error,UserError):
            log.warning("Falha de comando: %s",type(error).__name__)
    async def run_action(self, source, action, query="", member_id=None, attachment=None, mode=None):
        user = source.user if isinstance(source,discord.Interaction) else source.author
        gid = source.guild_id if isinstance(source,discord.Interaction) else source.guild.id
        if not gid:
            return
        preparar(self,gid)
        try:
            now=time.monotonic()
            if now-self.last_use.get(user.id,-1000)<2:
                raise UserError(tr('Aguarde dois segundos antes de abrir outro comando.'))
            self.last_use[user.id]=now
            if action=="unknown":
                raise UserError(tr('Não reconheci esse comando. Use AC:ajuda para abrir o índice.'))
            if isinstance(source,discord.Interaction) and not source.response.is_done():
                await source.response.defer(ephemeral=True,thinking=True)
            actor=await self.actor(user.id,gid)
            if action in STAFF_ACTIONS and not actor.staff:
                raise UserError(tr('Esse comando é exclusivo da staff.'))
            if action not in PUBLIC:
                if action=="transferir" and not member_id:
                    raise UserError(tr('Use AC:tr aparência @responsável.'))
                if action=="limpar":
                    member_id=member_id or (query.strip() if re.fullmatch(r"\d{17,20}",query.strip()) else None)
                    if not member_id and query.strip():
                        raise UserError(tr('Use AC:limpar @membro ou AC:limpar ID. Só AC:limpar lista quem tem cadastro e saiu do servidor.'))
                    query=""
                if action in ("editar","situacao","transferir","remover") and not query.strip():
                    raise UserError(tr('Informe o nome da aparência depois do comando. O bot apresentará opções quando houver mais de uma.'))
                if isinstance(source,discord.Interaction):
                    await self.open_private(source,action,query,member_id,attachment)
                else:
                    gate=Gate(self,user.id,action,query,member_id,attachment)
                    await self.reply_public(source,embed=card(tr('Amiya · Atendimento'), tr('Clique abaixo para continuar em privado. Só você verá o formulário e as respostas.')),view=gate)
                return
            if action=="guia":
                from . import guide_en
                guide=guide_en.GUIDE if atual()=="en" else GUIDE
                pages=guide if actor.staff else guide[:-STAFF_PAGES]
                view=Guide(self,user.id,pages)
                await self.reply_public(source,embed=view.embed(),view=view)
                return
            if action=="ajuda":
                from . import guide_en
                help_text=guide_en.HELP+(guide_en.STAFF_HELP if actor.staff else "") if atual()=="en" else HELP+(STAFF_HELP if actor.staff else "")
                await self.reply_public(source,embed=card(tr("Comandos da Arquivista"),help_text))
                return
            if action=="obra":
                data=await self.archive(gid).call("list",actor,{"owner_id":"","include_released":False})
                records=[public_record(r) for r in data["records"]]
                groups=await asyncio.to_thread(work_groups,[r["work"] for r in records],self.store.aliases(gid))
                if not query.strip():
                    view=Paginator(self,user.id,groups,"works",actor=actor,guild_id=gid)
                else:
                    found=find_work(groups,query)
                    keys={k for g in found for k in g["keys"]}
                    records=sorted((r for r in records if work_key(r["work"]) in keys),
                                   key=lambda r:(search_text(r["appearance"]),search_text(r["work"])))
                    title=tr('Obra: ')+" · ".join(g["label"] for g in found[:3]) if found else tr('Obra: ')+query
                    view=Paginator(self,user.id,records,"gallery" if mode=="galeria" else "list",actor=actor,guild_id=gid,title=title)
                await self.reply_public(source,embed=await view.embed(),view=view if view.records else None)
                return
            owner_id=str(user.id) if action=="minhas" else (str(member_id) if member_id else "")
            # Consultar mostra somente registros ocupados. Ausência não prova nome não padronizado.
            data=await self.archive(gid).call("list",actor,{"owner_id":owner_id,"include_released":False})
            records=ranked([public_record(r) for r in data["records"]],query)
            mode="gallery" if action in ("galeria","consultar") else "list"
            owner=None
            if owner_id:
                guild=self.get_guild(int(gid))
                owner=guild.get_member(int(owner_id)) if guild else None
                if guild and owner is None:
                    try:
                        owner=await guild.fetch_member(int(owner_id))
                    except discord.HTTPException:
                        owner=None
            view=Paginator(self,user.id,records,mode,actor=actor,guild_id=gid,owner=owner)
            await self.reply_public(source,embed=await view.embed(),view=view if records else None)
        except Exception as exc:
            await self.failure(source,exc)
    async def open_register(self, i: discord.Interaction, member=None, attachment=None, *, owner_id=None, limit=True):
        """Abre o formulário de cadastro como primeira resposta (o Discord só deixa abrir formulário assim).
        Nada lento antes do modal; o envio e a confirmação revalidam a permissão pelo Discord."""
        if limit:
            now=time.monotonic()
            if now-self.last_use.get(i.user.id,-1000)<2:
                return await private_reply(i,content=tr('Aguarde dois segundos antes de abrir outro comando.'))
            self.last_use[i.user.id]=now
        staff=self.is_staff_member(i.user)
        oid=str(member.id) if member else str(owner_id or i.user.id)
        if oid!=str(i.user.id) and not staff:
            return await private_reply(i,content=tr('Você pode cadastrar para si. Apenas a staff cadastra para outra pessoa.'))
        name=member.display_name if member else (i.user.display_name if oid==str(i.user.id) else "")
        uploads=bool(i.guild_id and self.store.guild(i.guild_id).get("image_channel"))
        await i.response.send_modal(preparar_interface(RecordModal(self,i.user.id,"create",staff=staff,owner={"id":oid,"name":name},
            attachment=attachment,uploads=uploads)))
    async def open_restore(self, i, attachment) -> None:
        """Confere o .json do backup e mostra o que vai mudar; grava só na confirmação."""
        if attachment is None or not attachment.filename.lower().endswith(".json"):
            raise UserError(tr('Anexe o arquivo .json do backup ao comando.'))
        if attachment.size > 25*1024*1024:
            raise UserError(tr('Arquivo grande demais para um backup do Arquivista.'))
        try:
            data=json.loads(await attachment.read())
        except (ValueError,discord.HTTPException):
            raise UserError(tr('Não consegui ler o arquivo. Use o .json que o backup mandou, sem editar.')) from None
        records,errors,warnings=check(data)
        if errors:
            raise UserError(tr('Não consegui usar este backup. Nada foi alterado:\n')+"\n".join("• "+clean(e,180) for e in errors[:8])+
                            (tr('\n… e mais {0}').format(len(errors)-8) if len(errors)>8 else ""))
        current=len(self.store.records(i.guild_id))
        other=str(data.get("guild_id") or "")!=str(i.guild_id)
        when=clean(str(data.get("exported_at") or tr('data desconhecida'))[:19].replace("T"," "),40)
        text=(tr('Backup de **{0}**.\n**Cadastros:** {1} · **Membros:** {2}\n\n').format(when, len(records), len({r['owner_id'] for r in records}))
              +(tr('Isso **substitui todos os cadastros atuais deste servidor** (total: {0}). O histórico continua no /historico.\n').format(current) if current else "")
              +(tr('A planilha conectada será regravada com o backup.\n') if self.store.guild(i.guild_id).get("sheet_url") else "")
              +(tr('\n**Atenção:** esse backup é de outro servidor.\n') if other else "")
              +(tr('\nAvisos ({0}): ').format(len(warnings))+clean("; ".join(warnings[:3]),400) if warnings else ""))
        v=RestoreConfirm(self,i.user.id,records)
        await private_reply(i,embed=self.carteiro.decorate(card(tr('Restaurar backup'),text)),view=v)
    def restore(self, gid, records, actor_id) -> int:
        n=apply(self.store,gid,records,actor_id,replace=True)
        self.notify_soon()
        return n
    async def departed(self, guild) -> str:
        """Donos de cadastro que não estão mais no servidor, com o ID para o /limpar."""
        counts={}
        for r in self.store.records(guild.id):
            counts[r["owner_id"]]=counts.get(r["owner_id"],0)+1
        gone,checked=[],0
        for owner,n in sorted(counts.items(),key=lambda x:-x[1]):
            if checked>=150:
                break
            checked+=1
            if guild.get_member(int(owner)):
                continue
            try:
                await guild.fetch_member(int(owner))
            except discord.NotFound:
                gone.append(tr('<@{0}> · `{1}` · Cadastros: {2}').format(owner, owner, n))
            except discord.HTTPException:
                pass
        if not gone:
            return tr('Todo mundo com cadastro ainda está no servidor.')+(tr(' (conferi os 150 com mais cadastros)') if checked<len(counts) else "")
        text="\n".join(gone[:40])
        return text+tr('\n\nPara apagar: `AC:limpar ID` ou `/limpar id:`. O histórico fica.')
    def alias_command(self, gid, query: str) -> str:
        """`JJK = Jujutsu Kaisen` cadastra, `-JJK` tira, vazio lista. Só a staff chega aqui."""
        query=query.strip()
        aliases=self.store.aliases(gid)
        if not query:
            if not aliases:
                return (tr('Nenhum apelido cadastrado. A busca por obra já junta grafias parecidas sozinha; apelido serve pro que não se parece, tipo `AC:apelido JJK = Jujutsu Kaisen`.'))
            lines=[f"**{clean(a,60)}** → {clean(w,80)}" for a,w in aliases.items()]
            text,shown="",0
            for line in lines:
                if len(text)+len(line)>3800:
                    break
                text+=("\n" if text else "")+line;shown+=1
            return text+(tr('\n… e mais {0}').format(len(lines)-shown) if shown<len(lines) else "")
        if query.startswith("-"):
            alias=query[1:].strip()
            if not self.store.drop_alias(gid,work_key(alias)):
                raise UserError(tr('Esse apelido não está cadastrado. Use AC:apelido para ver a lista.'))
            return tr('Apelido **{0}** removido.').format(clean(alias,60))
        if "=" not in query:
            raise UserError(tr('Use AC:apelido JJK = Jujutsu Kaisen para cadastrar, AC:apelido -JJK para tirar ou só AC:apelido para listar.'))
        alias,work=(x.strip() for x in query.split("=",1))
        if not alias or not work or len(alias)>100 or len(work)>100 or not work_key(alias) or not work_key(work):
            raise UserError(tr('Escreva o apelido e o nome da obra, cada um com até 100 caracteres.'))
        if work_key(alias)==work_key(work):
            raise UserError(tr('O apelido é igual ao nome da obra; a busca já acha.'))
        if work_key(alias) not in {work_key(a) for a in aliases} and len(aliases)>=500:
            raise UserError(tr('Este servidor já tem 500 apelidos. Tire algum antes.'))
        self.store.set_alias(gid,work_key(alias),alias,work)
        return tr('Pronto: **{0}** agora acha **{1}** no `/obra`, e o grupo aparece com esse nome.').format(clean(alias,60), clean(work,80))
    async def open_private(self, i, action, query="", member_id=None, attachment=None):
        try:
            actor=await self.actor(i.user.id,i.guild_id)
            archive=self.archive(i.guild_id)
            if action in STAFF_ACTIONS and not actor.staff:
                raise UserError(tr('Esse comando é exclusivo da staff.'))
            if action=="planilha":
                from .sheet_views import show_sheet
                await show_sheet(self,i)
            elif action=="configurar":
                if not self.can_configure(i.user):
                    raise UserError(tr('Só quem pode gerenciar o servidor configura o Arquivista.'))
                v=Settings(self,i.user.id,i.guild)
                await private_reply(i,embed=v.embed(),view=v)
            elif action=="restaurar":
                if not self.can_configure(i.user):
                    raise UserError(tr('Só quem pode gerenciar o servidor restaura um backup.'))
                await self.open_restore(i,attachment)
            elif action in ("editar","situacao","transferir","remover"):
                data=await archive.call("list",actor,{"owner_id":"" if actor.staff else actor.id,"include_released":True})
                records=ranked(data["records"],query,limit=250)
                if not records:
                    raise UserError(tr('Não encontrei um cadastro correspondente que você possa gerenciar.'))
                v=Picker(self,i.user.id,records,action,member_id,attachment)
                await private_reply(i,content=tr('Selecione a aparência e a obra na lista abaixo. Resultados: **{0}**.').format(len(records)),view=v)
            elif action=="apelido":
                await private_reply(i,embed=self.carteiro.decorate(card(tr('Apelidos de obra'),self.alias_command(i.guild_id,query))))
            elif action=="limpar" and not member_id:
                await private_reply(i,embed=self.carteiro.decorate(card(tr('Quem saiu do servidor'),await self.departed(i.guild))))
            elif action=="limpar":
                data=await archive.call("list",actor,{"owner_id":str(member_id),"include_released":True})
                records=data["records"]
                if not records:
                    raise UserError(tr('Esse membro não tem nenhum cadastro neste servidor.'))
                names="\n".join(f"• {clean(r['appearance'],80)} · {clean(r['work'],60)}" for r in records[:15])
                if len(records)>15:
                    names+=tr('\n… e mais {0}').format(len(records)-15)
                v=Confirm(self,i.user.id,"purge",{"owner_id":str(member_id),"ids":sorted(r["id"] for r in records)})
                await private_reply(i,embed=self.carteiro.decorate(card(tr('Confirmar limpeza'),
                    tr('Apagar **todos os cadastros** de <@{0}> (total: **{1}**)?\n\n{2}\n\nAs aparências ficam livres e as fichas saem da planilha. As mudanças anteriores continuam no /historico.').format(member_id, len(records), names))),view=v)
            elif action=="historico":
                data=await archive.call("history",actor,{"query":query})
                v=Paginator(self,i.user.id,data["events"],"history",actor=actor,guild_id=i.guild_id)
                await private_reply(i,content=tr('Esta consulta mostra até 200 mudanças recentes. As anteriores continuam guardadas no banco.') if data.get("truncated") else None,embed=await v.embed(),view=v if data["events"] else None)
            elif action=="diagnostico":
                data=await archive.call("status",actor)
                cfg=self.store.guild(i.guild_id)
                channel=lambda c:f"<#{c}>" if c else tr('não configurado')
                body=(tr('**Versão do Arquivista:** {0}\n**Cadastros:** {1} ({2} ocupando aparência)\n**Membros com cadastro:** {3}\n**Eventos na auditoria:** {4}\n**Avisos esperando envio:** {5}\n**Canal de histórico:** {6}\n**Canal de imagens:** {7}\n**Cargos de staff:** {8}\n**Último envio de avisos:** {9}\n**Funcionamento:** {10}').format(__version__, data['records'], data['occupied'], data['members'], data['events'], data['pending_notices'], channel(cfg['log_channel']), channel(cfg['image_channel']), ', '.join(f'<@&{r}>' for r in cfg['staff_roles']) or tr('só dono e quem gerencia o servidor'), self.last_sync or tr('ainda não realizado'), self.sync_problem or tr('sem erro registrado nesta sessão')))
                me=getattr(i.guild,"me",None);here=i.channel
                hooks=bool(me and here is not None and hasattr(here,"permissions_for") and here.permissions_for(me).manage_webhooks)
                body+=tr('\n**Amiya neste canal:** ')+(tr('com a foto dela') if hooks else tr('sai com o ícone do bot; dê ao bot a permissão Gerenciar Webhooks'))
                if cfg.get("sheet_url"):
                    queued,bad=self.store.sheet_pending(i.guild_id)
                    body+=(tr('\n**Planilha:** conectada · envios pendentes: {0}').format(queued)+(tr(', recusados pela planilha: {0}').format(bad) if bad else "")+
                           tr('\n**Último envio para a planilha:** {0}').format(cfg.get('sheet_ok') or tr('ainda não realizado'))+
                           (tr('\n**Último erro da planilha:** {0}').format(tr(SHEET_ERRORS.get(cfg['sheet_error'],cfg['sheet_error']))) if cfg.get("sheet_error") else "")+
                           (tr('\n**Edição da planilha que não entrou:** {0}').format(clean(cfg['sheet_note'],900)) if cfg.get("sheet_note") else ""))
                else:
                    body+=tr('\n**Planilha:** não conectada')
                body+=tr('\n**Criação automática de planilhas:** ')+(tr("ativada") if self.managed.ready else tr('aguardando ativação pelo mantenedor'))
                if cfg.get("backup_channel"):
                    nxt=cfg.get("backup_next")
                    body+=(tr('\n**Backup:** <#{0}> · {1}').format(cfg['backup_channel'], tr(backup.INTERVALS.get(cfg.get('backup_hours') or 24,'todo dia')))+
                           (tr(' · próximo <t:{0}:R>').format(int(nxt)) if nxt else "")+
                           (tr('\n**Último erro do backup:** {0}').format(cfg['backup_error']) if cfg.get("backup_error") else ""))
                else:
                    body+=tr('\n**Backup:** desligado')
                await private_reply(i,embed=self.carteiro.decorate(card(tr('Diagnóstico privado'),body)))
            else:
                raise UserError(tr('Operação não reconhecida.'))
        except Exception as exc:
            await self.failure(i,exc)
    @tasks.loop(seconds=90)
    async def worker(self):
        # Rede de segurança: cada gravação já pede o envio na hora; aqui saem as retentativas.
        # Cada etapa protegida: um erro inesperado numa não para o laço (tasks.loop morre com exceção).
        for name,stage in (("avisos",self.deliver_events),("planilha",self.sync_sheets),("backup",self.run_backups),("imagens",self.images.renew)):
            try:
                if await stage() and name=="imagens":
                    self.notify_soon()
            except Exception as exc:
                log.warning("Etapa %s: %s", name, type(exc).__name__)
    @worker.before_loop
    async def before_worker(self):
        await self.wait_until_ready()
    def notify_soon(self):
        # Guarda as tarefas até terminarem; sem referência o asyncio pode descartá-las no meio.
        for coro in (self.deliver_events(),self.sync_sheets()):
            task=asyncio.get_running_loop().create_task(coro)
            self.background.add(task);task.add_done_callback(self.background.discard)
    def now_text(self)->str:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    async def sync_sheets(self):
        if self.sheet_lock.locked():
            return  # o envio em andamento pega o que entrou na fila
        async with self.sheet_lock:
            await self.sheets.run()
            if await self.sheets.pull_due():
                # Edição vinda da planilha: aviso no histórico e a linha regravada com a nova revisão.
                await self.deliver_events()
                await self.sheets.run()
    async def run_backups(self):
        for gid in self.store.backup_due():
            if not self.get_guild(int(gid)):
                continue  # o bot saiu do servidor
            try:
                await self.send_backup(gid)
            except Exception as exc:
                log.warning("Backup do servidor %s: %s", gid, type(exc).__name__)
                cfg=self.store.guild(gid)
                # Tenta de novo em 30 min, sem empurrar o horário normal para longe.
                self.store.set_guild(gid,backup_error=str(exc)[:200] if isinstance(exc,UserError) else tr('não consegui enviar o arquivo'),
                                     backup_next=time.time()+min(1800,(cfg.get("backup_hours") or 24)*3600))
    async def send_backup(self, gid: str, channel=None) -> None:
        preparar(self,gid)
        """Manda o backup no canal configurado (ou no informado). Erro de configuração vira UserError com o motivo."""
        cfg=self.store.guild(gid)
        channel=channel or self.get_channel(int(cfg["backup_channel"] or 0))
        problem=backup_problem(channel,cfg["staff_roles"])
        if problem:
            raise UserError(problem)
        records=self.store.records(gid)
        stamp=datetime.now().astimezone()
        name=f"arquivista-{stamp:%Y-%m-%d-%H%M}"
        files=[discord.File(io.BytesIO(backup.export_json(gid,records)),filename=name+".json")]
        if cfg.get("sheet_url"):
            names={o:await self.sheets.owner_name(gid,o) for o in {r["owner_id"] for r in records}}
            files.append(discord.File(io.BytesIO(backup.workbook(records,names,cfg.get("language","pt-BR"))),filename=name+".xlsx"))
        text=(tr('Cadastros: **{0}** · Membros: **{1}**.\n\nPara recuperar os cadastros, anexe o `.json` ao `/restaurar`').format(len(records), len({r['owner_id'] for r in records}))+
              (tr('. O `.xlsx` permite consultar os cadastros por membro, cada um na sua aba.') if cfg.get("sheet_url") else ".")+
              tr('\n\nOs arquivos incluem justificativas e nomes dos personagens no servidor. Mantenha este canal só para a staff.'))
        await channel.send(embed=self.carteiro.decorate(card(tr('Backup do arquivo'),text)),files=files,allowed_mentions=discord.AllowedMentions.none())
        hours=cfg.get("backup_hours") or 24
        self.store.set_guild(gid,backup_error=None,backup_next=time.time()+hours*3600)
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
            preparar(self,row["guild_id"])
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
                    actor=f"<@{event['actor_id']}>" if event.get("actor_id") else tr('Planilha; autor não identificado')
                    if event["kind"]=="purged":
                        e=card(tr('Cadastros de um membro apagados'),
                            tr('**Membro:** <@{0}>\n**Cadastros apagados:** {1}\n**Registro da alteração:** {2}').format(event['owner_id'], event['count'], actor))
                    else:
                        e=card(tr(titles.get(event["kind"],"Cadastro atualizado")),
                            tr('**Aparência:** {0}\n**Obra:** {1}\n**Responsável:** <@{2}>\n**Registro da alteração:** {3}').format(clean(event['appearance'],200), clean(event['work'],200), event['owner_id'], actor))
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
    @bot.tree.command(name="language",description="Set the server language. New spreadsheets use this language.")
    @app_commands.guild_only()
    @app_commands.choices(language=[app_commands.Choice(name="English",value="en"),app_commands.Choice(name="Português do Brasil",value="pt-BR")])
    async def language(i:discord.Interaction,language:str|None=None):
        await bot.change_language(i,language)
    @bot.tree.command(name="idioma",description="Escolher idioma do servidor e das novas planilhas.")
    @app_commands.guild_only()
    @app_commands.choices(idioma=[app_commands.Choice(name="Português do Brasil",value="pt-BR"),app_commands.Choice(name="English",value="en")])
    async def idioma(i:discord.Interaction,idioma:str|None=None):
        await bot.change_language(i,idioma)
    @bot.tree.command(name="ajuda",description="Índice de comandos da Amiya.")
    @app_commands.guild_only()
    async def ajuda(i:discord.Interaction):await bot.run_action(i,"ajuda")
    @bot.tree.command(name="guia",description="Passo a passo de como o arquivo de aparências funciona.")
    @app_commands.guild_only()
    async def guia(i:discord.Interaction):await bot.run_action(i,"guia")
    @bot.tree.command(name="aparencias",description="Consulte as aparências: busque pelo nome, filtre por membro, veja em lista ou galeria.")
    @app_commands.guild_only()
    @app_commands.describe(aparencia="Nome da aparência (aproximado vale); pode incluir a obra",membro="Só as de um membro",modo="Lista ou galeria de imagens")
    @app_commands.choices(modo=[app_commands.Choice(name="lista",value="lista"),app_commands.Choice(name="galeria",value="galeria")])
    async def aparencias(i:discord.Interaction,aparencia:str="",membro:discord.Member|None=None,modo:str="lista"):
        await bot.run_action(i,"galeria" if modo=="galeria" else "aparencias",aparencia,membro.id if membro else None)
    @bot.tree.command(name="obra",description="Aparências de uma obra, juntando grafias parecidas; sem nome, lista as obras.")
    @app_commands.guild_only()
    @app_commands.describe(nome="Nome da obra (aproximado vale: arknights também acha Endfield)",modo="Lista ou galeria de imagens")
    @app_commands.choices(modo=[app_commands.Choice(name="lista",value="lista"),app_commands.Choice(name="galeria",value="galeria")])
    async def obra(i:discord.Interaction,nome:str="",modo:str="lista"):
        await bot.run_action(i,"obra",nome,mode=modo)
    @bot.tree.command(name="registrar",description="Cadastre uma aparência; staff também cadastra para outra pessoa.")
    @app_commands.guild_only()
    async def registrar(i:discord.Interaction,membro:discord.Member|None=None):await bot.open_register(i,membro)
    @bot.tree.command(name="editar",description="Altere nome no servidor ou imagem de um cadastro seu.")
    @app_commands.guild_only()
    async def editar(i:discord.Interaction,aparencia:str):await bot.run_action(i,"editar",aparencia)
    @bot.tree.command(name="situacao",description="Staff: altere situação e justificativa internas.")
    @app_commands.guild_only()
    async def situacao(i:discord.Interaction,aparencia:str):await bot.run_action(i,"situacao",aparencia)
    @bot.tree.command(name="transferir",description="Staff: mude o responsável, mantendo ID e data.")
    @app_commands.guild_only()
    async def transferir(i:discord.Interaction,aparencia:str,membro:discord.Member):await bot.run_action(i,"transferir",aparencia,membro.id)
    @bot.tree.command(name="remover",description="Remova um cadastro seu; staff também pode remover de outras pessoas.")
    @app_commands.guild_only()
    async def remover(i:discord.Interaction,aparencia:str):await bot.run_action(i,"remover",aparencia)
    @bot.tree.command(name="limpar",description="Staff: apague todos os cadastros de um membro, com confirmação.")
    @app_commands.guild_only()
    @app_commands.describe(membro="Quem ainda está no servidor",id="ID do Discord, para quem já saiu (vazio: lista quem saiu)")
    async def limpar(i:discord.Interaction,membro:discord.User|None=None,id:str=""):
        await bot.run_action(i,"limpar",id,membro.id if membro else None)
    @bot.tree.command(name="apelido",description="Staff: apelido de obra para a busca por obra (JJK = Jujutsu Kaisen).")
    @app_commands.guild_only()
    @app_commands.describe(acao="Cadastrar, tirar ou ver a lista",apelido="Como as pessoas escrevem (JJK)",obra="Nome da obra (Jujutsu Kaisen)")
    @app_commands.choices(acao=[app_commands.Choice(name="cadastrar",value="cadastrar"),app_commands.Choice(name="tirar",value="tirar"),
                                app_commands.Choice(name="lista",value="lista")])
    async def apelido(i:discord.Interaction,acao:str="lista",apelido:str="",obra:str=""):
        query={"cadastrar":f"{apelido} = {obra}","tirar":"-"+apelido}.get(acao,"")
        await bot.run_action(i,"apelido",query)
    @bot.tree.command(name="historico",description="Staff: histórico detalhado em privado.")
    @app_commands.guild_only()
    async def historico(i:discord.Interaction,aparencia:str=""):await bot.run_action(i,"historico",aparencia)
    @bot.tree.command(name="configurar",description="Gerência: cargos de staff, canais e planilha do Arquivista.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def configurar(i:discord.Interaction):await bot.run_action(i,"configurar")
    @bot.tree.command(name="restaurar",description="Gerência: volta o arquivo para um backup (.json), com confirmação.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(arquivo="O .json que o backup mandou")
    async def restaurar(i:discord.Interaction,arquivo:discord.Attachment):await bot.run_action(i,"restaurar",attachment=arquivo)
    planilha = app_commands.Group(name="planilha", description=tr('Planilha pronta e edição manual conectada ao arquivo.'),
        guild_only=True, default_permissions=discord.Permissions(manage_guild=True))
    @planilha.command(name="criar",description="Cria a planilha pronta e dá edição ao e-mail informado em privado.")
    async def planilha_criar(i:discord.Interaction):
        from .sheet_views import create_sheet
        await create_sheet(bot,i)
    @planilha.command(name="abrir",description="Abre o painel privado da planilha deste servidor.")
    async def planilha_abrir(i:discord.Interaction):
        from .sheet_views import show_sheet
        await show_sheet(bot,i)
    @planilha.command(name="membro",description="Prepara uma aba vazia para preencher manualmente; selecione um @membro válido.")
    @app_commands.describe(membro="Selecione um membro deste servidor pelo @; não aceita nick como texto.")
    async def planilha_membro(i:discord.Interaction,membro:discord.Member):
        if not bot.can_configure(i.user):
            return await private_reply(i,content=tr('Só quem pode gerenciar o servidor prepara as abas.'))
        await i.response.defer(ephemeral=True,thinking=True)
        try:
            url=await bot.managed.prepare_member(i.guild,i.user,membro)
            row=bot.store.managed_sheet(i.guild_id)
            link=tr('[Abrir planilha]({0})').format(url) if row and row["url"]==url else tr('Abra a planilha já conectada ao servidor.')
            await private_reply(i,content=tr('A aba de <@{0}> está preparada. {1}\nPreencha uma posição vazia; a sincronização lê as edições em cerca de 5 minutos.').format(membro.id, link))
        except UserError as exc:
            await private_reply(i,content=str(exc))
    bot.tree.add_command(planilha)
    @bot.tree.command(name="diagnostico",description="Staff: estado do arquivo, dos canais e da planilha.")
    @app_commands.guild_only()
    async def diagnostico(i:discord.Interaction):await bot.run_action(i,"diagnostico")
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
