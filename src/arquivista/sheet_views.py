"""Planilha pronta: e-mail e links aparecem somente no atendimento privado da gerência."""
import discord
from .domain import UserError
from .google import GoogleError
from .views import GuardedView, SheetModal, card, private_reply
from .docs import SETUP_LINK

async def create_sheet(bot, i):
    if not bot.can_configure(i.user):
        return await private_reply(i, content="Só quem pode gerenciar o servidor cria a planilha.")
    row = bot.store.managed_sheet(i.guild_id)
    if not row or row["state"] == "awaiting_email":
        if not row and bot.store.guild(i.guild_id).get("sheet_url"):
            return await show_sheet(bot, i)
        if not bot.managed.ready:
            return await private_reply(i, content=str(GoogleError("GOOGLE_SETUP")))
        return await i.response.send_modal(CreateSheetModal(bot, i.user.id))
    await i.response.defer(ephemeral=True, thinking=True)
    try:
        url = await bot.managed.create(i.guild, i.user)
        await private_reply(i, embed=card("Planilha do servidor", f"[Abrir planilha]({url})\n\n"
            "A planilha foi reutilizada e está conectada. Edições nela voltam ao bot em cerca de 5 minutos."))
    except UserError as exc:
        await private_reply(i, content=str(exc))

async def show_sheet(bot, i):
    if not bot.can_configure(i.user):
        return await private_reply(i, content="Só quem pode gerenciar o servidor acessa este painel.")
    panel = SheetPanel(bot, i.user.id, i.guild)
    await private_reply(i, embed=panel.embed(), view=panel)

class CreateSheetModal(discord.ui.Modal):
    def __init__(self, bot, author_id):
        super().__init__(title="Criar planilha · acesso de editor", timeout=600)
        self.bot, self.author_id = bot, author_id
        self.email = discord.ui.TextInput(label="E-mail Google que receberá edição", max_length=254,
            placeholder="A planilha será privada e compartilhada com este e-mail.")
        self.add_item(self.email)

    async def on_submit(self, i):
        if i.user.id != self.author_id or not self.bot.can_configure(i.user):
            return await private_reply(i, content="Só quem pode gerenciar o servidor cria a planilha.")
        await i.response.defer(ephemeral=True, thinking=True)
        try:
            url = await self.bot.managed.create(i.guild, i.user, str(self.email.value))
            await private_reply(i, embed=card("Planilha pronta", f"[Abrir planilha]({url})\n\n"
                "O e-mail informado recebeu edição. A planilha pertence à conta do Arquivista.\n"
                "Você já pode preencher uma posição na sua aba ou cadastrar pelo bot. "
                "Use `/planilha membro` e selecione um @membro para preparar outra aba.\n\n"
                "As edições feitas no Sheets entram no bot em cerca de 5 minutos. Os cadastros que já existem estão na fila de envio. "
                "Compartilhe edição só com a staff."))
        except UserError as exc:
            await private_reply(i, content=str(exc))

    async def on_error(self, i, error):
        await private_reply(i, content="Não consegui confirmar a criação. Use /planilha criar novamente para retomar o mesmo pedido.")

class SheetPanel(GuardedView):
    def __init__(self, bot, author_id, guild):
        super().__init__(bot, author_id)
        self.guild = guild
        row = bot.store.managed_sheet(guild.id)
        cfg = bot.store.guild(guild.id)
        if row and row["state"] == "ready" and cfg.get("sheet_url") == row["url"]:
            self.add_item(discord.ui.Button(label="Abrir planilha", url=row["url"]))

    async def interaction_check(self, i):
        if not await super().interaction_check(i):
            return False
        if not self.bot.can_configure(i.user):
            await private_reply(i, content="Seu acesso mudou. Só quem pode gerenciar o servidor configura a planilha.")
            return False
        return True

    def embed(self):
        cfg = self.bot.store.guild(self.guild.id)
        status = "conectada" if cfg.get("sheet_url") else "não conectada"
        availability = "disponível" if self.bot.managed.ready else "aguardando ativação pelo mantenedor"
        return self.bot.carteiro.decorate(card("Planilha do servidor",
            f"**Planilha:** {status}\n**Criação automática:** {availability}\n\n"
            "**Criar ou retomar** prepara a planilha e concede edição ao e-mail Google informado, em privado. "
            "Se ela já existe, o comando reutiliza o arquivo.\n\n"
            "`/planilha membro` prepara uma aba vazia para um @membro selecionado do servidor. "
            "O que for preenchido aqui ou no bot sincroniza nos dois sentidos; edições do Sheets entram em cerca de 5 minutos.\n"
            "Somente a staff deve receber edição, pois ela permite mudar os cadastros.\n\n" + SETUP_LINK))

    @discord.ui.button(label="Criar ou retomar", style=discord.ButtonStyle.primary)
    async def create(self, i, button):
        await create_sheet(self.bot, i)

    @discord.ui.button(label="Planilha antiga", style=discord.ButtonStyle.secondary)
    async def legacy(self, i, button):
        await i.response.send_modal(SheetModal(self.bot, i.user.id, self.guild))

    @discord.ui.button(label="Desconectar", style=discord.ButtonStyle.secondary)
    async def disconnect(self, i, button):
        async with self.bot.sheet_lock:
            self.bot.store.drop_sheet(self.guild.id)
        row = self.bot.store.managed_sheet(self.guild.id)
        reconnect = ("Use /planilha criar para reconectar o arquivo criado pelo Arquivista." if row else
            "Para reconectar a planilha antiga, abra este painel novamente e use Planilha antiga com a URL e a chave da conexão.")
        await private_reply(i, content="Sincronização desligada. O arquivo e o acesso de edição continuam no Google. " + reconnect)
