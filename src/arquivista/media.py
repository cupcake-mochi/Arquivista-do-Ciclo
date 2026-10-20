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
    async def save(self, attachment: discord.Attachment, guild_id: int) -> dict[str, str]:
        cid = self.bot.store.guild(guild_id).get("image_channel")
        if not cid:
            raise UserError("Para usar anexos, a staff precisa escolher um canal de imagens no /configurar. Por enquanto, use um link direto.")
        if attachment.size > 8 * 1024 * 1024:
            raise UserError("Envie uma imagem de até 8 MB.")
        channel = self.bot.get_channel(int(cid)) or await self.bot.fetch_channel(int(cid))
        if not getattr(channel, "guild", None) or channel.guild.id != guild_id:
            raise UserError("O canal de imagens configurado não está disponível neste servidor.")
        data = await attachment.read()
        ext = valid_attachment(data)
        message = await channel.send("Imagem preservada pelo Arquivista do Ciclo.",
            file=discord.File(io.BytesIO(data), filename=f"aparencia-{uuid.uuid4().hex}{ext}"),
            allowed_mentions=MENTIONS)
        item = message.attachments[0]
        return {"image_url": item.url,
                "media_ref": f"discord://{channel.guild.id}/{channel.id}/{message.id}/{item.id}"}
    async def resolve(self, record_id: str, actor: Actor, guild_id: int) -> str:
        key = f"{guild_id}/{record_id}"
        old = self.cache.get(key)
        if old and old[0] > time.monotonic():
            return old[1]
        try:
            archive = self.bot.archive(guild_id)
            result = await archive.call("image", actor, {"id": record_id})
            url = result.get("url", "")
            ref = result.get("media_ref", "")
            if ref:
                ref_guild, channel_id, message_id, attachment_id = ref[len("discord://"):].split("/")
                if int(ref_guild) != int(guild_id):
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
                    await archive.call("refresh_image", self.bot.service_actor(),
                        {"id": record_id, "media_ref": ref, "url": url})
            if not url.startswith("https://"):
                return ""
            self.cache[key] = (time.monotonic() + (300 if ref else 45), url)
            return url
        except (discord.HTTPException, UserError, ValueError, AttributeError):
            return ""
