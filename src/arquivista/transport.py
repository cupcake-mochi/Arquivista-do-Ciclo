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
    def decorate(self, embed: discord.Embed) -> discord.Embed:
        avatar = str(self.bot.user.display_avatar.url) if self.bot.user else None
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
                if hook is None:
                    hook = await base.create_webhook(name="Arquivista do Ciclo", avatar=(ROOT / "assets/amiya.png").read_bytes(), reason="Apresentação da Amiya nos comandos do Arquivista")
                self.cache[base.id] = hook
            return self.cache[base.id]
    async def send(self, channel, *, content: str | None = None, embed: discord.Embed | None = None,
                   view: discord.ui.View | None = None):
        if embed:
            self.decorate(embed)
        thread = channel if isinstance(channel, discord.Thread) else None
        base = thread.parent if thread else channel
        kwargs = {"content": content, "embed": embed, "allowed_mentions": MENTIONS}
        if view is not None:
            kwargs["view"] = view
        for attempt in range(2):
            try:
                hook = await self.webhook(base)
                # Interações só funcionam em webhook pertencente à aplicação.
                if view is not None and hook.application_id != self.bot.application_id:
                    raise ValueError("webhook sem associação à aplicação")
                message = await hook.send(**kwargs, username=self.bot.config.persona_name,
                    avatar_url=str(self.bot.user.display_avatar.url), wait=True,
                    **({"thread": thread} if thread else {}))
                break
            except discord.NotFound:
                self.cache.pop(getattr(base, "id", 0), None)
                if attempt == 0:
                    continue
                message = await channel.send(**kwargs)
                break
            except (discord.Forbidden, AttributeError, ValueError):
                log.warning("Webhook não disponível no canal %s; usando a conta do Arquivista.", getattr(channel, "id", 0))
                message = await channel.send(**kwargs)
                break
        self.bot.store.remember(message.id)
        if view is not None and hasattr(view, "message"):
            view.message = message
        return message
