"""Anexos retidos em canal autorizado; sem baixar URLs arbitrárias no host."""
from __future__ import annotations
import io
import time
import uuid
from urllib.parse import parse_qs, urlsplit
import discord
from .domain import Actor, UserError, valid_attachment
from .transport import MENTIONS

# Link de anexo do Discord vale ~24 h (parâmetro ex=, hora em hexadecimal). A planilha mostra a imagem
# pelo link, então ele é renovado antes de vencer; sem planilha, a galeria renova na hora de mostrar.
RENEW_BEFORE = 3 * 3600
RENEW_EVERY = 600
RENEW_BATCH = 40

def expires(url: str) -> float | None:
    """Quando o link de anexo do Discord vence; None se não tiver prazo."""
    try:
        return float(int(parse_qs(urlsplit(url).query)["ex"][0], 16))
    except (KeyError, ValueError, IndexError):
        return None

class Images:
    def __init__(self, bot):
        self.bot = bot
        self.cache: dict[str, tuple[float, str]] = {}
        self.next_renew = 0.0
        self.gave_up: dict[str, float] = {}  # mensagem apagada etc.: tenta de novo só bem depois
    async def renew(self) -> int:
        """Renova os links que vencem logo, nos servidores com planilha. Poucos por vez, para não pesar no Discord."""
        if time.time() < self.next_renew:
            return 0
        self.next_renew = time.time() + RENEW_EVERY
        due = []
        for r in self.bot.store.renewable():
            end = expires(r["image_url"])
            if self.gave_up.get(f"{r['guild_id']}/{r['id']}", 0) > time.time() or not self.bot.get_guild(int(r["guild_id"])):
                continue
            if end is not None and end - time.time() < RENEW_BEFORE:
                due.append((end, r))
        due.sort(key=lambda x: x[0])
        done = 0
        for _, r in due[:RENEW_BATCH]:
            key = f"{r['guild_id']}/{r['id']}"
            self.cache.pop(key, None)
            url = await self.resolve(r["id"], self.bot.service_actor(), int(r["guild_id"]))
            if url and url != r["image_url"]:
                done += 1
            else:
                self.gave_up[key] = time.time() + 6 * 3600
        if len(due) > RENEW_BATCH:
            self.next_renew = 0.0  # ainda tem fila: continua na próxima volta
        return done
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
