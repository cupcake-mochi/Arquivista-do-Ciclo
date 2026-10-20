"""Carteiro da Amiya: webhook da própria aplicação, com fallback explícito."""
from __future__ import annotations
import asyncio
import logging
import discord
from .config import ROOT

log = logging.getLogger(__name__)
MENTIONS = discord.AllowedMentions.none()

class Carteiro:
    def __init__(self, bot):
        self.bot = bot
        self.cache: dict[int, discord.Webhook] = {}
        self.locks: dict[int, asyncio.Lock] = {}
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
                hook = next((w for w in hooks if w.name == "Arquivista do Ciclo" and w.token
                    and ((w.user and w.user.id == self.bot.user.id) or w.application_id == self.bot.application_id)), None)
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
                # Interações só funcionam em webhook pertencente à aplicação.
                if view is not None and hook.application_id != self.bot.application_id:
                    raise ValueError("webhook sem associação à aplicação")
                # Foto da Amiya explícita: sem ela, o Discord pode mostrar o ícone do aplicativo.
                photo = self.bot.store.get("amiya_icon")
                message = await hook.send(**kwargs, username=self.bot.config.persona_name, wait=True,
                    **({"avatar_url": photo} if photo else {}),
                    **({"thread": thread} if thread else {}))
                break
            except discord.NotFound:
                self.cache.pop(getattr(base, "id", 0), None)
                if attempt == 0:
                    continue
                if embed:
                    self.decorate(embed)
                message = await channel.send(**kwargs)
                break
            except (discord.HTTPException, AttributeError, ValueError):
                # Sem permissão, limite de 15 webhooks no canal ou outra recusa: sai pela conta do bot.
                log.warning("Webhook não disponível no canal %s; usando a conta do Arquivista.", getattr(channel, "id", 0))
                if embed:
                    self.decorate(embed)
                message = await channel.send(**kwargs)
                break
        self.bot.store.remember(message.id)
        if view is not None and hasattr(view, "message"):
            view.message = message
        return message
