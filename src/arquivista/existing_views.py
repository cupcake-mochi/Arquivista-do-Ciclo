"""Importar cadastros para uma cópia independente, com confirmação privada."""
import discord

from .domain import UserError
from .existing_sheet import ExistingSheets
from .idiomas import preparar_interface, tr
from .views import GuardedView, LocalizedModal, card, clean, private_reply


async def open_existing(bot, interaction):
    if not interaction.guild_id or not bot.can_configure(interaction.user):
        return await private_reply(interaction, content=tr("Só quem pode gerenciar o servidor importa uma planilha existente."))
    await interaction.response.send_modal(preparar_interface(ExistingModal(bot)))


def preview(bot, request, summary):
    text = tr("**Origem:** {0}\n**Servidor de destino:** {1}\n**Cadastros a copiar:** {2}\n**Abas de membro na origem:** {3}\n**Editor da cópia:** {4}\n\nVou criar uma nova planilha do Arquivista neste servidor, com esses cadastros. O arquivo original, suas permissões e sua sincronização serão preservados.\n\nA cópia terá IDs novos e sincronização independente. Responsáveis e datas serão mantidos; o histórico anterior não será copiado. Imagens inseridas diretamente nas células e elementos fora dos campos de cadastro não são copiados.\n\nSomente a cópia nova receberá edição para o e-mail informado. Não vou misturar nem substituir cadastros existentes.").format(
        clean(request.title), request.guild_id, summary["records"], summary["members"], clean(request.email))
    return card(tr("Conferir importação"), text)


class ExistingModal(LocalizedModal):
    def __init__(self, bot):
        super().__init__(title=tr("Importar planilha existente"), timeout=600)
        self.bot = bot
        self.url = discord.ui.TextInput(label=tr("Link da planilha Google Sheets"),
            placeholder="https://docs.google.com/spreadsheets/d/.../edit", max_length=500)
        self.email = discord.ui.TextInput(label=tr("E-mail Google para editar a cópia"), max_length=254)
        self.add_item(self.url)
        self.add_item(self.email)

    async def on_submit(self, i):
        await i.response.defer(ephemeral=True, thinking=True)
        try:
            service = ExistingSheets(self.bot)
            request, identified = await service.begin(i.guild, i.user, self.url.value, self.email.value)
            if identified:
                summary = await service.inspect(i.guild, i.user, request)
                return await private_reply(i, embed=preview(self.bot, request, summary),
                    view=ExistingPanel(self.bot, request, confirmation=True))
            text = tr("É preciso confirmar a autorização para copiar os cadastros. Peça ao responsável que já pode editar o arquivo original para:\n\n1. Escolher uma célula vazia e colar o código abaixo.\n2. Em **Dados → Intervalos nomeados**, nomear apenas essa célula como **ARQUIVISTA_AUTORIZACAO**.\n3. Conferir o ID do servidor de destino no código antes de autorizar a cópia dos cadastros.\n\n```\n{0}\n```\nO código vale por 10 minutos e apenas para este arquivo, servidor e solicitante. Depois, escolha **Validar arquivo**. Não vou alterar o original nem seus acessos. O e-mail informado receberá edição apenas na nova cópia.").format(request.token)
            await private_reply(i, embed=card(tr("Autorizar o arquivo"), text), view=ExistingPanel(self.bot, request))
        except UserError as exc:
            await private_reply(i, content=str(exc))

    async def on_error(self, i, error):
        await private_reply(i, content=tr("Não consegui concluir a verificação. Abra /planilha importar novamente; se continuar, avise o mantenedor."))


class ExistingPanel(GuardedView):
    def __init__(self, bot, request, *, confirmation=False):
        super().__init__(bot, int(request.author_id), timeout=600)
        self.request = request
        if confirmation:
            self.remove_item(self.validate)
        else:
            self.remove_item(self.confirm)

    async def interaction_check(self, i):
        if not await super().interaction_check(i):
            return False
        if str(i.guild_id) != self.request.guild_id or not self.bot.can_configure(i.user):
            await private_reply(i, content=tr("Seu acesso mudou ou este painel pertence a outro servidor. Abra /planilha importar novamente."))
            return False
        return True

    async def close_panel(self):
        for item in self.children:
            item.disabled = True
        self.stop()
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Validar arquivo", style=discord.ButtonStyle.primary)
    async def validate(self, i, button):
        await i.response.defer(ephemeral=True, thinking=True)
        try:
            summary = await ExistingSheets(self.bot).inspect(i.guild, i.user, self.request)
            await self.close_panel()
            await private_reply(i, embed=preview(self.bot, self.request, summary),
                view=ExistingPanel(self.bot, self.request, confirmation=True))
        except UserError as exc:
            await private_reply(i, content=str(exc))

    @discord.ui.button(label="Importar e criar cópia", style=discord.ButtonStyle.success)
    async def confirm(self, i, button):
        await i.response.defer(ephemeral=True, thinking=True)
        try:
            await ExistingSheets(self.bot).confirm(i.guild, i.user, self.request)
            await self.close_panel()
            await private_reply(i, content=tr("Cópia criada e conectada neste servidor, com edição para o e-mail informado. O arquivo original e seus acessos foram preservados. Use /planilha abrir para consultar a nova planilha."))
        except UserError as exc:
            if self.request.started:
                await self.close_panel()
                row = self.bot.store.managed_sheet(i.guild_id)
                if row and row["state"] == "ready":
                    await private_reply(i, content=tr("Esta importação já foi concluída. Use /planilha abrir para consultar a cópia."))
                else:
                    await private_reply(i, content=tr("Os dados já foram importados, mas a criação ou o compartilhamento da cópia ainda não terminou. Use /planilha criar para retomar o mesmo arquivo, sem importar novamente.") + "\n" + str(exc))
            else:
                await private_reply(i, content=str(exc))

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel(self, i, button):
        await i.response.defer(ephemeral=True, thinking=True)
        try:
            async with self.bot.sheet_lock:
                self.request.check()
                self.request.used = True
            await self.close_panel()
            await private_reply(i, content=tr("Importação cancelada. O arquivo e os acessos Google foram preservados."))
        except UserError as exc:
            await private_reply(i, content=str(exc))
