"""Anexos retidos em canal autorizado; sem baixar URLs arbitrárias no host."""
from __future__ import annotations
import io
import time
import uuid
import discord
from .domain import Actor, UserError, valid_attachment
from .transport import MENTIONS

class Images:
    def __init__(self, bot):
        self.bot = bot
        self.cache: dict[str, tuple[float, str]] = {}
    async def save(self, attachment: discord.Attachment) -> dict[str, str]:
        cid = self.bot.store.get("image_channel")
        if not cid:
            raise UserError("Para usar anexos, a staff precisa definir um canal com AC:registrarimagens. Por enquanto, use um link direto.")
        if attachment.size > 8 * 1024 * 1024:
            raise UserError("Envie uma imagem de até 8 MB.")
        channel = self.bot.get_channel(int(cid)) or await self.bot.fetch_channel(int(cid))
        if not getattr(channel, "guild", None) or channel.guild.id != self.bot.config.guild_id:
            raise UserError("O canal de imagens configurado não está disponível neste servidor.")
        data = await attachment.read()
        ext = valid_attachment(data)
        message = await channel.send("Imagem preservada pelo Arquivista do Ciclo.",
            file=discord.File(io.BytesIO(data), filename=f"aparencia-{uuid.uuid4().hex}{ext}"),
            allowed_mentions=MENTIONS)
        item = message.attachments[0]
        return {"image_url": item.url,
                "media_ref": f"discord://{channel.guild.id}/{channel.id}/{message.id}/{item.id}"}
    async def resolve(self, record_id: str, actor: Actor) -> str:
        old = self.cache.get(record_id)
        if old and old[0] > time.monotonic():
            return old[1]
        try:
            result = await self.bot.bridge.call("image", actor, {"id": record_id})
            url = result.get("url", "")
            ref = result.get("media_ref", "")
            if ref:
                guild_id, channel_id, message_id, attachment_id = ref[len("discord://"):].split("/")
                if int(guild_id) != self.bot.config.guild_id:
                    return ""
                channel = self.bot.get_channel(int(channel_id)) or await self.bot.fetch_channel(int(channel_id))
                message = await channel.fetch_message(int(message_id))
                if message.author.id != self.bot.user.id:
                    return ""
                image = next((a for a in message.attachments if str(a.id) == attachment_id), None)
                if not image:
                    return ""
                url = image.url
                if url != result.get("url"):
                    await self.bot.bridge.call("refresh_image", self.bot.service_actor(),
                        {"id": record_id, "media_ref": ref, "url": url})
            if not url.startswith("https://"):
                return ""
            self.cache[record_id] = (time.monotonic() + (300 if ref else 45), url)
            return url
        except (discord.HTTPException, UserError, ValueError, AttributeError):
            return ""
