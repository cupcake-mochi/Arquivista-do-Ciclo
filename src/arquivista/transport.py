"""Carteiro da Amiya: webhook da própria aplicação, com fallback explícito."""
from __future__ import annotations
import asyncio
import logging
import discord
from .config import ROOT
from .idiomas import preparar_interface, tr

log = logging.getLogger(__name__)
MENTIONS = discord.AllowedMentions.none()

def reason(exc: Exception) -> str:
    """Motivo curto, sem o texto do erro: ele pode trazer o endereço do webhook."""
    if isinstance(exc, discord.HTTPException):
        return f"Discord {exc.status}/{exc.code}"
    return type(exc).__name__

class Carteiro:
    def __init__(self, bot):
        self.bot = bot
        self.cache: dict[int, discord.Webhook] = {}
        self.locks: dict[int, asyncio.Lock] = {}
        self.failed: dict[int, Exception] = {}  # canal -> por que a última mensagem saiu pela conta do bot
    def problem(self, channel) -> str | None:
        """Motivo para o /diagnostico; None se a última mensagem no canal saiu pelo webhook (ou se não houve)."""
        base = channel.parent if isinstance(channel, discord.Thread) else channel
        exc = self.failed.get(getattr(base, "id", 0))
        if exc is None:
            return None
        if getattr(exc, "code", 0) == 30007:
            return tr('limite de webhooks do canal atingido; apague um que não usa')
        if isinstance(exc, discord.Forbidden):
            return tr('o Discord negou a permissão')
        return tr('erro {0}').format(reason(exc))
    def fell_back(self, base, exc: Exception) -> None:
        self.failed[getattr(base, "id", 0)] = exc
        # AttributeError/ValueError é erro nosso: a mensagem ainda sai, então o registro precisa dizer onde foi.
        log.warning("Webhook não disponível no canal %s (%s); usando a conta do Arquivista.", getattr(base, "id", 0), reason(exc),
                    exc_info=None if isinstance(exc, discord.HTTPException) else exc)
    def icon(self) -> str | None:
        """Foto da Amiya: a do webhook que o bot criou com assets/amiya.png. Antes de existir um, a do bot."""
        return self.bot.store.get("amiya_icon") or (str(self.bot.user.display_avatar.url) if self.bot.user else None)
    def decorate(self, embed: discord.Embed) -> discord.Embed:
        avatar = self.icon()
        kwargs = {"name": f"{self.bot.config.persona_name} · Arquivista do Ciclo"}
        if avatar:
            kwargs["icon_url"] = avatar
        embed.set_author(**kwargs)
        return embed
    async def webhook(self, base) -> discord.Webhook:
        lock = self.locks.setdefault(base.id, asyncio.Lock())
        async with lock:
            if base.id not in self.cache:
                hooks = await base.webhooks()
                # Só o webhook criado pela própria conta: botão não funciona em webhook de outro dono.
                # (discord.Webhook não tem application_id; o dono é quem criou.)
                hook = next((w for w in hooks if w.name == "Arquivista do Ciclo" and w.token
                    and w.user and w.user.id == self.bot.user.id), None)
                photo = (ROOT / "assets/amiya.png").read_bytes()
                if hook is None:
                    hook = await base.create_webhook(name="Arquivista do Ciclo", avatar=photo, reason="Apresentação da Amiya nos comandos do Arquivista")
                avatar = hook.display_avatar if hook.avatar else None
                if avatar is None:
                    # Webhook sem foto aparece com o ícone do aplicativo (o do portal): põe a da Amiya.
                    # Guarda o webhook original, que tem o token de envio; do editado só vale a foto nova.
                    try:
                        edited = await hook.edit(avatar=photo, reason="Foto da Amiya")
                        avatar = edited.display_avatar if edited.avatar else None
                    except discord.HTTPException:
                        log.warning("Não consegui pôr a foto da Amiya no webhook do canal %s.", base.id)
                self.cache[base.id] = hook
                # Avatar de webhook fica num link fixo do Discord: serve de ícone da Amiya até nas respostas privadas.
                url = str(avatar.url) if avatar else ""
                if url and self.bot.store.get("amiya_icon") != url:
                    self.bot.store.set("amiya_icon", url)
            return self.cache[base.id]
    async def send(self, channel, *, content: str | None = None, embed: discord.Embed | None = None,
                   view: discord.ui.View | None = None):
        preparar_interface(view)
        thread = channel if isinstance(channel, discord.Thread) else None
        base = thread.parent if thread else channel
        kwargs = {"content": content, "embed": embed, "allowed_mentions": MENTIONS}
        if view is not None:
            kwargs["view"] = view
        for attempt in range(2):
            try:
                hook = await self.webhook(base)
                if embed:
                    self.decorate(embed)  # depois do webhook, que guarda a foto da Amiya na primeira vez
                # Foto da Amiya explícita: sem ela, o Discord pode mostrar o ícone do aplicativo.
                photo = self.bot.store.get("amiya_icon")
                message = await hook.send(**kwargs, username=self.bot.config.persona_name, wait=True,
                    **({"avatar_url": photo} if photo else {}),
                    **({"thread": thread} if thread else {}))
                self.failed.pop(base.id, None)
                break
            except discord.NotFound as exc:
                self.cache.pop(getattr(base, "id", 0), None)
                if attempt == 0:
                    continue
                self.fell_back(base, exc)
                if embed:
                    self.decorate(embed)
                message = await channel.send(**kwargs)
                break
            except (discord.HTTPException, AttributeError, ValueError) as exc:
                # Sem permissão, limite de 15 webhooks no canal ou outra recusa: sai pela conta do bot.
                self.fell_back(base, exc)
                if embed:
                    self.decorate(embed)
                message = await channel.send(**kwargs)
                break
        self.bot.store.remember(message.id)
        if view is not None and hasattr(view, "message"):
            view.message = message
        return message
