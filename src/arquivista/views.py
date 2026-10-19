from __future__ import annotations
import asyncio
import logging
import uuid
from typing import Callable, Awaitable
import discord
from .domain import UserError, BridgeError, STAFF_ACTIONS, STATUSES, safe_image_url
from .transport import MENTIONS

log = logging.getLogger(__name__)

def clean(value, limit=1000):
    # Conteúdo de usuários nunca produz pings, links mascarados ou formatação de staff.
    return discord.utils.escape_markdown(discord.utils.escape_mentions(str(value or "")))[:limit]

def card(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(title=title, description=description, colour=0x559EA6)

async def private_reply(interaction: discord.Interaction, *, content=None, embed=None, view=None):
    kwargs = {"content": content, "embed": embed, "allowed_mentions": MENTIONS}
    if view is not None:
        kwargs["view"] = view
    if interaction.response.is_done():
        message = await interaction.followup.send(**kwargs, ephemeral=True, wait=True)
    else:
        await interaction.response.send_message(**kwargs, ephemeral=True)
        message = await interaction.original_response()
    if view is not None and hasattr(view, "message"):
        view.message = message
    return message

class GuardedView(discord.ui.View):
    def __init__(self, bot, author_id: int, *, timeout=300):
        super().__init__(timeout=timeout)
        self.bot, self.author_id, self.message = bot, author_id, None
        self.requires_staff = False
    async def interaction_check(self, i: discord.Interaction) -> bool:
        if i.user.id != self.author_id or i.guild_id != self.bot.config.guild_id:
            await private_reply(i, content="Este painel pertence a outra pessoa. Abra seu próprio comando.")
            return False
        if self.requires_staff and not self.bot.is_staff_member(i.user):
            await private_reply(i, content="Esse acesso é exclusivo da staff. Seu cargo foi alterado; abra um novo atendimento.")
            return False
        return True
    async def on_timeout(self):
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
    async def on_error(self, interaction, error, item):
        message = str(error) if isinstance(error, UserError) else "O painel não conseguiu concluir essa etapa. Abra novamente ou consulte a staff."
        log.warning("Falha de painel: %s", type(error).__name__)
        await private_reply(interaction, content=message)

class Gate(GuardedView):
    def __init__(self, bot, user_id, action, query="", member_id=None, attachment=None):
        super().__init__(bot, user_id)
        self.action, self.query, self.member_id, self.attachment = action, query, member_id, attachment
        self.requires_staff = action in STAFF_ACTIONS
    @discord.ui.button(label="Abrir painel privado", style=discord.ButtonStyle.primary)
    async def open_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.bot.open_private(interaction, self.action, self.query, self.member_id, self.attachment)

class Paginator(GuardedView):
    def __init__(self, bot, user_id, records, mode="list", *, actor=None):
        super().__init__(bot, user_id)
        self.records, self.mode, self.page, self.actor = records, mode, 0, actor
        self.per_page = 1 if mode in ("gallery", "history") else 15
        self.requires_staff = mode == "history"
        self.mutex = asyncio.Lock()
    @property
    def pages(self):
        return max(1, (len(self.records)+self.per_page-1)//self.per_page)
    async def embed(self):
        self.previous.disabled = self.page == 0
        self.next.disabled = self.page >= self.pages-1
        if not self.records:
            e = card("Arquivo de aparências", "Não encontrei resultados para esta consulta. Não encontrar um nome parecido não garante disponibilidade: o cadastro faz a conferência final.")
        elif self.mode == "history":
            event = self.records[self.page]
            e = card("Histórico interno", f"**{clean(event.get('kind'))}** · {clean(event.get('at'))}")
            e.add_field(name="Origem", value=clean(event.get("source")), inline=True)
            e.add_field(name="Autor", value=f"<@{event['actor_id']}>" if event.get("actor_id") else "Planilha; autor não identificado", inline=True)
            labels = {"appearance":"Aparência", "work":"Obra", "server_name":"Nome no servidor", "status":"Situação", "justification":"Justificativa", "owner_id":"Responsável", "image_url":"Imagem", "date":"Data"}
            before, after = event.get("before") or {}, event.get("after") or {}
            changes = []
            for key, label in labels.items():
                if before.get(key) != after.get(key):
                    changes.append(f"**{label}:** {clean(before.get(key) or '—',160)} → {clean(after.get(key) or '—',160)}")
            e.description += "\n\n" + ("\n".join(changes)[:3200] or "Alteração registrada na imagem ou em metadados do cadastro.")
        elif self.mode == "gallery":
            r = self.records[self.page]
            e = card(clean(r["appearance"], 200), f"**Obra:** {clean(r['work'],200)}\n**Responsável:** <@{r['owner_id']}>")
            url = await self.bot.images.resolve(r["id"], self.actor)
            if url:
                e.set_image(url=url)
            else:
                e.add_field(name="Imagem", value="Sem imagem disponível no momento.", inline=False)
        else:
            chunk = self.records[self.page*self.per_page:(self.page+1)*self.per_page]
            lines = [f"**{self.page*self.per_page+j+1}. {clean(r['appearance'],110)}** · <@{r['owner_id']}>" for j,r in enumerate(chunk)]
            e = card("Arquivo de aparências", "\n".join(lines))
        e.set_footer(text=f"Página {self.page+1}/{self.pages} · {len(self.records)} resultado(s) · abra outro comando para atualizar")
        return self.bot.carteiro.decorate(e)
    async def turn(self, i, delta):
        await i.response.defer()
        async with self.mutex:
            self.page = max(0, min(self.pages-1, self.page+delta))
            await i.edit_original_response(embed=await self.embed(), view=self, allowed_mentions=MENTIONS)
    @discord.ui.button(label="Anterior", style=discord.ButtonStyle.secondary)
    async def previous(self, i: discord.Interaction, b: discord.ui.Button):
        await self.turn(i, -1)
    @discord.ui.button(label="Próxima", style=discord.ButtonStyle.secondary)
    async def next(self, i: discord.Interaction, b: discord.ui.Button):
        await self.turn(i, 1)

class Picker(GuardedView):
    def __init__(self, bot, user_id, records, action, member_id=None, attachment=None):
        super().__init__(bot, user_id)
        self.records, self.action, self.member_id, self.attachment = records, action, member_id, attachment
        self.requires_staff = action in STAFF_ACTIONS
        self.page = 0
        self.select = discord.ui.Select(placeholder="Escolha a aparência e a obra corretas", min_values=1, max_values=1, row=0)
        self.select.callback = self.choose
        self.add_item(self.select)
        self.options()
    def options(self):
        chunk = self.records[self.page*25:(self.page+1)*25]
        self.select.options = [discord.SelectOption(label=f"{r['appearance']} · {r['work']}"[:100],
            description=f"Responsável: {r['owner_id']}", value=r["id"]) for r in chunk]
        self.back.disabled = self.page == 0
        self.more.disabled = (self.page+1)*25 >= len(self.records)
    async def choose(self, i):
        await i.response.defer(ephemeral=True, thinking=True)
        actor = await self.bot.actor(i.user.id)
        if self.action in STAFF_ACTIONS and not actor.staff:
            raise UserError("Esta operação é reservada à staff.")
        data = await self.bot.bridge.call("get", actor, {"id": self.select.values[0]})
        record = data["record"]
        if self.action == "editar":
            v = FormLauncher(self.bot, self.author_id, "edit", record=record, attachment=self.attachment)
            await private_reply(i, content="Abra o formulário para alterar os campos permitidos.", view=v)
        elif self.action == "situacao":
            v = StatusPicker(self.bot, self.author_id, record)
            await private_reply(i, content="Escolha a situação interna. Arquivar não libera a aparência.", view=v)
        elif self.action == "transferir":
            target = await self.bot.actor(self.member_id)
            payload = {"id": record["id"], "revision": record["revision"], "owner": {"id":target.id,"name":target.name}}
            v = Confirm(self.bot, self.author_id, "transfer", payload)
            await private_reply(i, embed=self.bot.carteiro.decorate(card("Confirmar transferência", f"**{clean(record['appearance'])}** será transferida para <@{target.id}>. O ID e a data original serão preservados.")), view=v)
        elif self.action == "remover":
            v = Confirm(self.bot, self.author_id, "remove", {"id": record["id"], "revision": record["revision"]})
            await private_reply(i, embed=self.bot.carteiro.decorate(card("Confirmar remoção", f"Remover **{clean(record['appearance'])}**, de **{clean(record['work'])}**?\nIsso apaga o cadastro ativo, mas preserva a auditoria. Para manter a aparência ocupada, use Arquivado.")), view=v)
    @discord.ui.button(label="Anteriores", row=1)
    async def back(self, i: discord.Interaction, b: discord.ui.Button):
        self.page = max(0, self.page-1); self.options()
        await i.response.edit_message(view=self)
    @discord.ui.button(label="Mais resultados", row=1)
    async def more(self, i: discord.Interaction, b: discord.ui.Button):
        self.page = min((len(self.records)-1)//25, self.page+1); self.options()
        await i.response.edit_message(view=self)

class FormLauncher(GuardedView):
    def __init__(self, bot, user_id, mode, *, record=None, owner=None, attachment=None):
        super().__init__(bot, user_id)
        self.mode, self.record, self.owner, self.attachment = mode, record, owner, attachment
    @discord.ui.button(label="Preencher ficha", style=discord.ButtonStyle.primary)
    async def launch(self, i: discord.Interaction, b: discord.ui.Button):
        # Nenhuma consulta lenta antes de enviar o modal: usa membro da interação;
        # a autorização é revalidada por REST no envio e na confirmação.
        staff = self.bot.is_staff_member(i.user)
        await i.response.send_modal(RecordModal(self.bot, self.author_id, self.mode, staff=staff,
            record=self.record, owner=self.owner, attachment=self.attachment))

class RecordModal(discord.ui.Modal):
    def __init__(self, bot, user_id, mode, *, staff=False, record=None, owner=None, attachment=None):
        super().__init__(title="Amiya · Cadastro de aparência", timeout=600)
        self.bot, self.author_id, self.mode, self.record, self.owner, self.attachment = bot, user_id, mode, record or {}, owner, attachment
        self.fields: dict[str, discord.ui.TextInput] = {}
        definitions = [("appearance","Aparência original",100,True),("work","Obra de origem",100,True)] if mode=="create" or staff else []
        definitions += [("server_name","Nome no servidor",100,False),("image_url","Link HTTPS da imagem (opcional)",1500,False)]
        for key,label,limit,required in definitions:
            item = discord.ui.TextInput(label=label, max_length=limit, required=required,
                default=str(self.record.get(key) or ""), placeholder="Digite - para remover a imagem" if key=="image_url" else None)
            self.fields[key] = item
            self.add_item(item)
    async def on_submit(self, i: discord.Interaction):
        if i.user.id != self.author_id or i.guild_id != self.bot.config.guild_id:
            return await private_reply(i, content="Este formulário não pertence a você.")
        await i.response.defer(ephemeral=True, thinking=True)
        try:
            actor = await self.bot.actor(i.user.id)
            fields = {k:str(v.value).strip() for k,v in self.fields.items()}
            remove_image = fields.get("image_url")=="-"
            fields["image_url"] = "" if remove_image else safe_image_url(fields.get("image_url", ""))
            if self.mode=="edit":
                fields = {k:v for k,v in fields.items() if v!=str(self.record.get(k) or "") or (k=="image_url" and remove_image)}
                if remove_image:
                    fields["clear_image"] = True
                if not actor.staff and any(k in fields for k in ("appearance","work")):
                    raise UserError("Somente a staff pode mudar a identidade da aparência ou da obra.")
                payload = {"id":self.record["id"],"revision":self.record["revision"],"fields":fields}
            else:
                owner = self.owner or {"id":actor.id,"name":actor.name}
                if owner["id"]!=actor.id and not actor.staff:
                    raise UserError("Somente a staff cadastra para outra pessoa.")
                payload = {"fields":fields,"owner":owner}
            view = Confirm(self.bot,self.author_id,self.mode,payload,attachment=self.attachment)
            title = "Revisar antes de salvar"
            display = {**self.record,**fields}
            body = f"**Aparência:** {clean(display.get('appearance'))}\n**Obra:** {clean(display.get('work'))}\n**Nome no servidor:** {clean(display.get('server_name') or 'não informado')}"
            if self.attachment:
                body += "\nA imagem anexada será preservada no canal configurado ao confirmar."
            await private_reply(i,embed=self.bot.carteiro.decorate(card(title,body)),view=view)
        except UserError as exc:
            await private_reply(i,content=str(exc))
    async def on_error(self,i,error):
        await private_reply(i,content="Não consegui abrir a confirmação. Confira os campos e tente novamente.")

class StatusPicker(GuardedView):
    def __init__(self,bot,user_id,record):
        super().__init__(bot,user_id)
        self.record = record
        self.requires_staff = True
        self.select = discord.ui.Select(placeholder="Situação interna", options=[discord.SelectOption(label=s,value=s,default=s==record["status"]) for s in STATUSES])
        self.select.callback = self.choose
        self.add_item(self.select)
    async def choose(self,i):
        if not self.bot.is_staff_member(i.user):
            return await private_reply(i,content="Somente a staff pode alterar a situação.")
        await i.response.send_modal(StatusModal(self.bot,self.author_id,self.record,self.select.values[0]))

class StatusModal(discord.ui.Modal):
    def __init__(self,bot,user_id,record,status):
        super().__init__(title="Amiya · Observação interna")
        self.bot,self.author_id,self.record,self.status=bot,user_id,record,status
        self.text=discord.ui.TextInput(label="Observação / justificativa (interna)",style=discord.TextStyle.paragraph,required=False,max_length=2000,default=record.get("justification", ""))
        self.add_item(self.text)
    async def on_submit(self,i):
        if i.user.id!=self.author_id or i.guild_id!=self.bot.config.guild_id:
            return await private_reply(i,content="Este formulário não pertence a você.")
        await i.response.defer(ephemeral=True,thinking=True)
        actor=await self.bot.actor(i.user.id)
        if not actor.staff:
            return await private_reply(i,content="Somente a staff pode alterar a situação.")
        payload={"id":self.record["id"],"revision":self.record["revision"],"status":self.status,"justification":str(self.text.value).strip()}
        view=Confirm(self.bot,self.author_id,"change_status",payload)
        body=f"**{clean(self.record['appearance'])}** → **{self.status}**."
        body+="\nIsso permitirá que outra pessoa registre a aparência." if self.status=="Liberado" else "\nA aparência continua ocupada."
        await private_reply(i,embed=self.bot.carteiro.decorate(card("Confirmar situação interna",body)),view=view)
    async def on_error(self,i,error):
        await private_reply(i,content=str(error) if isinstance(error,UserError) else "Falha ao preparar a alteração. Nenhuma confirmação foi enviada.")

class Confirm(GuardedView):
    def __init__(self,bot,user_id,action,payload,attachment=None):
        super().__init__(bot,user_id,timeout=600)
        self.action,self.payload,self.attachment=action,payload,attachment
        self.requires_staff=action in ("change_status","transfer","remove")
        self.request_id=str(uuid.uuid4())
        self.busy=False
        self.completed=False
        if action=="remove":
            self.confirm.style=discord.ButtonStyle.danger
            self.confirm.label="Confirmar remoção"
    @discord.ui.button(label="Confirmar e salvar",style=discord.ButtonStyle.success)
    async def confirm(self,i:discord.Interaction,b:discord.ui.Button):
        if self.completed:
            return await private_reply(i,content="Esta confirmação já foi concluída.")
        if self.busy:
            return await private_reply(i,content="Ainda estou conferindo esta mesma confirmação. Aguarde.")
        self.busy=True
        await i.response.defer(ephemeral=True,thinking=True)
        try:
            actor=await self.bot.actor(i.user.id)
            if self.action in ("change_status","transfer","remove") and not actor.staff:
                raise UserError("Você não tem mais autorização para essa operação.")
            if self.attachment:
                media=await self.bot.images.save(self.attachment)
                self.payload.setdefault("fields",{}).update(media)
                self.attachment=None  # retentar não faz outro upload
            result=await self.bot.bridge.call(self.action,actor,self.payload,self.request_id)
            self.completed=True
            for item in self.children:
                item.disabled=True
            if self.message:
                try: await self.message.edit(view=self)
                except discord.HTTPException: pass
            text="Registro removido; o histórico foi preservado." if self.action=="remove" else "Salvo no arquivo. Vou manter os registros organizados."
            if not result.get("changed",True):
                text="Os dados já estavam assim. Não criei um evento de alteração desnecessário."
            await private_reply(i,embed=self.bot.carteiro.decorate(card("Amiya · Confirmação",text)))
            self.stop()
        except UserError as exc:
            if isinstance(exc,BridgeError) and exc.code in ("BUSY","INTERNAL"):
                self.confirm.label="Tentar a mesma confirmação"
            await private_reply(i,content=str(exc))
        finally:
            self.busy=False
    @discord.ui.button(label="Cancelar",style=discord.ButtonStyle.secondary)
    async def cancel(self,i:discord.Interaction,b:discord.ui.Button):
        if self.busy:
            return await private_reply(i,content="O salvamento já começou. Aguarde a confirmação antes de continuar.")
        self.completed=True
        for child in self.children:
            child.disabled=True
        await i.response.edit_message(content="Cancelado. Nenhum novo pedido de gravação foi enviado.",view=self)
        self.stop()
