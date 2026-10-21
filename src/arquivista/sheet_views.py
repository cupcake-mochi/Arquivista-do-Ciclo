"""Planilha pronta: e-mail e links aparecem somente no atendimento privado da gerência."""
import discord
from .idiomas import preparar_interface, tr
from .domain import UserError
from .google import GoogleError
from .views import LocalizedModal, GuardedView, SheetModal, card, private_reply
from .docs import SETUP_LINK

async def create_sheet(bot, i):
    if not bot.can_configure(i.user):
        return await private_reply(i, content=tr('Só quem pode gerenciar o servidor cria a planilha.'))
    row = bot.store.managed_sheet(i.guild_id)
    if not row or row["state"] == "awaiting_email":
        if not row and bot.store.guild(i.guild_id).get("sheet_url"):
            return await show_sheet(bot, i)
        if not bot.managed.ready:
            return await private_reply(i, content=str(GoogleError("GOOGLE_SETUP")))
        return await i.response.send_modal(preparar_interface(CreateSheetModal(bot, i.user.id)))
    await i.response.defer(ephemeral=True, thinking=True)
    try:
        url = await bot.managed.create(i.guild, i.user)
        await private_reply(i, embed=card(tr('Planilha do servidor'), tr('[Abrir planilha]({0})\n\nEsta é a planilha que já estava criada para o servidor. Ela está conectada; o que você editar nela chega ao bot em cerca de 5 minutos.').format(url)))
    except UserError as exc:
        await private_reply(i, content=str(exc))

async def show_sheet(bot, i):
    if not bot.can_configure(i.user):
        return await private_reply(i, content=tr('Só quem pode gerenciar o servidor acessa este painel.'))
    panel = SheetPanel(bot, i.user.id, i.guild)
    await private_reply(i, embed=panel.embed(), view=panel)

class CreateSheetModal(LocalizedModal):
    def __init__(self, bot, author_id):
        super().__init__(title=tr('Criar a planilha do servidor'), timeout=600)
        self.bot, self.author_id = bot, author_id
        self.email = discord.ui.TextInput(label=tr('E-mail Google de quem vai editar'), max_length=254,
            placeholder=tr('A planilha será privada e compartilhada com este e-mail.'))
        self.add_item(self.email)

    async def on_submit(self, i):
        if i.user.id != self.author_id or not self.bot.can_configure(i.user):
            return await private_reply(i, content=tr('Só quem pode gerenciar o servidor cria a planilha.'))
        await i.response.defer(ephemeral=True, thinking=True)
        try:
            url = await self.bot.managed.create(i.guild, i.user, str(self.email.value))
            await private_reply(i, embed=card(tr('Planilha pronta'), tr('[Abrir planilha]({0})\n\nDei acesso de editor ao e-mail informado. A planilha fica na conta do Arquivista.\nAbra sua aba para preencher uma ficha, ou cadastre pelo bot. Use `/planilha membro` e selecione um @membro para preparar outra aba.\n\nAs edições no Sheets chegam ao bot em cerca de 5 minutos. Estou enviando para a planilha os cadastros que já existiam. Compartilhe edição só com a staff.').format(url)))
        except UserError as exc:
            await private_reply(i, content=str(exc))

    async def on_error(self, i, error):
        await private_reply(i, content=tr('Não consegui confirmar se a planilha ficou pronta. Use /planilha criar novamente para continuar de onde parou.'))

class SheetPanel(GuardedView):
    def __init__(self, bot, author_id, guild):
        super().__init__(bot, author_id)
        self.guild = guild
        row = bot.store.managed_sheet(guild.id)
        cfg = bot.store.guild(guild.id)
        if row and row["state"] == "ready" and cfg.get("sheet_url") == row["url"]:
            self.add_item(discord.ui.Button(label=tr('Abrir planilha'), url=row["url"]))

    async def interaction_check(self, i):
        if not await super().interaction_check(i):
            return False
        if not self.bot.can_configure(i.user):
            await private_reply(i, content=tr('Seu acesso mudou. Só quem pode gerenciar o servidor configura a planilha.'))
            return False
        return True

    def embed(self):
        cfg = self.bot.store.guild(self.guild.id)
        status = tr('conectada') if cfg.get("sheet_url") else tr('não conectada')
        availability = tr('disponível') if self.bot.managed.ready else tr('aguardando ativação pelo mantenedor')
        return self.bot.carteiro.decorate(card(tr('Planilha do servidor'),
            tr('**Planilha:** {0}\n**Criação automática:** {1}\n\n**Criar ou retomar** abre um formulário privado para você informar o e-mail de quem vai editar. Se a planilha já existe, abre o mesmo arquivo.\n\n`/planilha membro` prepara uma aba vazia para um @membro selecionado do servidor. Você pode preencher as fichas na planilha ou pelo bot. As edições no Sheets chegam ao bot em cerca de 5 minutos.\nDê acesso de editor só à staff: quem edita a planilha pode mudar os cadastros do servidor.\n\n').format(status, availability) + SETUP_LINK))

    @discord.ui.button(label="Criar ou retomar", style=discord.ButtonStyle.primary)
    async def create(self, i, button):
        await create_sheet(self.bot, i)

    @discord.ui.button(label="Planilha antiga", style=discord.ButtonStyle.secondary)
    async def legacy(self, i, button):
        await i.response.send_modal(preparar_interface(SheetModal(self.bot, i.user.id, self.guild)))

    @discord.ui.button(label="Desconectar", style=discord.ButtonStyle.secondary)
    async def disconnect(self, i, button):
        async with self.bot.sheet_lock:
            self.bot.store.drop_sheet(self.guild.id)
        row = self.bot.store.managed_sheet(self.guild.id)
        reconnect = (tr('Use /planilha criar para reconectar o arquivo criado pelo Arquivista.') if row else
            tr('Para reconectar a planilha antiga, abra este painel novamente e use Planilha antiga com a URL e a chave da conexão.'))
        await private_reply(i, content=tr('Sincronização desligada. O arquivo e o acesso de edição continuam no Google. ') + reconnect)
