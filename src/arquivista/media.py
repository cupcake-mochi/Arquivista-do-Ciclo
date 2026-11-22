"""Anexos retidos em canal autorizado; sem baixar URLs arbitrárias no host."""
from __future__ import annotations
import io
import logging
import re
import time
import uuid
from urllib.parse import parse_qs, urlencode, urlsplit
import aiohttp
import discord
from .domain import Actor, UserError, valid_attachment
from .transport import MENTIONS

# Link de anexo do Discord vale ~24 h (parâmetro ex=, hora em hexadecimal). A planilha mostra a imagem
# pelo link, então ele é renovado antes de vencer; sem planilha, a galeria renova na hora de mostrar.
RENEW_BEFORE = 3 * 3600
RENEW_EVERY = 600
RENEW_BATCH = 40
# Link de anexo do Discord colado à mão (de outro canal) não tem mensagem guardada, então não dá para
# renovar. O bot "adota" a imagem: pega um link válido, baixa só do próprio Discord e reenvia no canal
# de imagens; dali em diante ela entra na renovação acima como qualquer anexo.
ADOPT_BATCH = 10
ADOPT_RETRY = 6 * 3600
MAX_BYTES = 8 * 1024 * 1024
DISCORD_FILE = re.compile(r"^https://(?:cdn\.discordapp\.com|media\.discordapp\.net)/(attachments|ephemeral-attachments)/"
                          r"(\d{15,22})/(\d{15,22})/([^/?#\s]+)(?:\?([^#\s]*))?$")
log = logging.getLogger(__name__)

class AdoptError(Exception):
    """Motivo curto (sem link nem token) para o log quando uma imagem colada não pôde ser guardada."""

def discord_file(url: str) -> tuple[str, int, int, str, dict] | None:
    """Partes de um link de anexo do Discord: tipo, canal, anexo, nome do arquivo e parâmetros."""
    m = DISCORD_FILE.match(url or "")
    if not m:
        return None
    query = {k: v[0] for k, v in parse_qs(m[5] or "").items() if v}
    return m[1], int(m[2]), int(m[3]), m[4], query

def original_url(url: str) -> str:
    """O mesmo anexo no endereço do arquivo original (sem redimensionar), com a assinatura que tiver."""
    kind, channel, attachment, name, query = discord_file(url)
    sign = {k: query[k] for k in ("ex", "is", "hm") if k in query}
    return f"https://cdn.discordapp.com/{kind}/{channel}/{attachment}/{name}" + ("?" + urlencode(sign) if sign else "")

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
        self.next_adopt = 0.0
        self.adopt_failed: dict[str, tuple[float, str]] = {}  # "guild/anexo" -> (tenta de novo depois de, motivo)
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
    # ---------- links do Discord colados à mão ----------
    def adopt_pending(self, guild_id) -> tuple[int, int]:
        """(esperando cópia, sem conseguir copiar) entre as imagens coladas deste servidor."""
        now, waiting, failed = time.time(), 0, 0
        for r in self.bot.store.adoptable(guild_id):
            parts = discord_file(r["image_url"])
            if not parts:
                continue
            until = self.adopt_failed.get(f"{r['guild_id']}/{parts[2]}", (0, ""))[0]
            failed += until > now
            waiting += until <= now
        return waiting, failed
    async def adopt(self) -> int:
        """Guarda no canal de imagens as imagens coladas por link do Discord. Poucas por vez."""
        if time.time() < self.next_adopt:
            return 0
        self.next_adopt = time.time() + RENEW_EVERY
        groups: dict[str, list[dict]] = {}
        for r in self.bot.store.adoptable():
            parts = discord_file(r["image_url"])
            if not parts or not self.bot.get_guild(int(r["guild_id"])):
                continue
            key = f"{r['guild_id']}/{parts[2]}"  # o mesmo anexo em dois cadastros sobe uma vez só
            if self.adopt_failed.get(key, (0, ""))[0] > time.time():
                continue
            groups.setdefault(key, []).append(r)
        if not groups:
            return 0
        batch = list(groups.items())[:ADOPT_BATCH]
        if len(groups) > ADOPT_BATCH:
            self.next_adopt = 0.0  # ainda tem fila: continua na próxima volta
        stale = [original_url(rows[0]["image_url"]) for _, rows in batch
                 if (expires(rows[0]["image_url"]) or 0) - time.time() < 600]
        fresh = await self.refresh_urls(stale)
        done, failed = 0, []
        for key, rows in batch:
            guild_id = int(rows[0]["guild_id"])
            try:
                saved = await self.save_bytes(await self.fetch_pasted(rows[0]["image_url"], fresh), guild_id)
                archive = self.bot.archive(guild_id)
                for r in rows:
                    try:
                        await archive.call("adopt_image", self.bot.service_actor(), {
                            "id": r["id"], "old_url": r["image_url"], **saved})
                        done += 1
                    except UserError:
                        pass  # o link mudou enquanto a imagem subia: a próxima volta vê o novo
                self.adopt_failed.pop(key, None)
            except (AdoptError, UserError, discord.HTTPException, aiohttp.ClientError, TimeoutError, ValueError) as exc:
                reason = str(exc) if isinstance(exc, (AdoptError, UserError)) else type(exc).__name__
                self.adopt_failed[key] = (time.time() + ADOPT_RETRY, reason)
                failed.append(reason)
        tail = (" (" + "; ".join(sorted(set(failed)))[:300] + ")") if failed else ""
        log.info("Imagens coladas do Discord: %s guardadas, %s sem sucesso%s", done, len(failed), tail)
        return done
    async def refresh_urls(self, urls: list[str]) -> dict[int, str]:
        """Link novo para anexos vencidos (o mesmo pedido que o app do Discord faz). Por ID do anexo."""
        if not urls:
            return {}
        try:
            data = await self.bot.http.request(discord.http.Route("POST", "/attachments/refresh-urls"),
                                               json={"attachment_urls": urls})
        except discord.HTTPException as exc:
            log.warning("Discord recusou renovar links colados: HTTP %s (código %s)", exc.status, getattr(exc, "code", 0))
            return {}
        out = {}
        for item in (data or {}).get("refreshed_urls") or []:
            new = item.get("refreshed") if isinstance(item, dict) else None
            parts = discord_file(new) if isinstance(new, str) else None
            if parts and "hm" in parts[4]:
                out[parts[2]] = new
        if len(out) < len(urls):
            log.info("Renovação de links colados: %s de %s devolvidos", len(out), len(urls))
        return out
    async def fetch_pasted(self, url: str, fresh: dict[int, str]) -> bytes:
        kind, channel, attachment, _, _ = discord_file(url)
        candidates = [fresh[attachment]] if attachment in fresh else []
        if (expires(url) or 0) - time.time() > 60:
            candidates.append(url)
        if not candidates:
            found = await self.from_message(channel, attachment)
            if found:
                candidates.append(found)
        if not candidates:
            raise AdoptError("link vencido e sem renovação")
        last = "sem resposta"
        for link in candidates:
            for src in dict.fromkeys((original_url(link), link)):  # original primeiro; o redimensionado se o original não servir
                try:
                    return await self.download(src)
                except AdoptError as exc:
                    # Guarda o motivo mais útil: "não é imagem" diz mais que o 404 da segunda tentativa.
                    if last == "sem resposta" or not str(exc).startswith("download HTTP"):
                        last = str(exc)
        raise AdoptError(last)
    async def from_message(self, channel_id: int, attachment_id: int) -> str:
        """Plano B: acha a mensagem original pelo horário do anexo, se o bot enxerga o canal."""
        channel = self.bot.get_channel(channel_id)
        if channel is None or not hasattr(channel, "history"):
            return ""
        try:
            async for message in channel.history(around=discord.Object(attachment_id), limit=50):
                for a in message.attachments:
                    if a.id == attachment_id:
                        return a.url
        except discord.HTTPException:
            return ""
        return ""
    async def download(self, url: str) -> bytes:
        if not discord_file(url):
            raise AdoptError("endereço fora do Discord")
        timeout = aiohttp.ClientTimeout(total=30)
        async with self.bot.session.get(url, allow_redirects=False, timeout=timeout) as resp:
            if resp.status != 200:
                raise AdoptError(f"download HTTP {resp.status}")
            if (resp.content_length or 0) > MAX_BYTES:
                raise AdoptError("imagem maior que 8 MB")
            data = bytearray()
            async for chunk in resp.content.iter_chunked(65536):
                data += chunk
                if len(data) > MAX_BYTES:
                    raise AdoptError("imagem maior que 8 MB")
        try:
            valid_attachment(bytes(data))
        except UserError:
            raise AdoptError("não é PNG, JPEG, GIF nem WebP") from None
        return bytes(data)
    async def save(self, attachment: discord.Attachment, guild_id: int) -> dict[str, str]:
        if not self.bot.store.guild(guild_id).get("image_channel"):
            raise UserError("Para usar anexos, a staff precisa escolher um canal de imagens no /configurar. Por enquanto, use um link direto.")
        if attachment.size > MAX_BYTES:
            raise UserError("Envie uma imagem de até 8 MB.")
        return await self.save_bytes(await attachment.read(), guild_id)
    async def save_bytes(self, data: bytes, guild_id: int) -> dict[str, str]:
        cid = self.bot.store.guild(guild_id).get("image_channel")
        if not cid:
            raise UserError("Para usar anexos, a staff precisa escolher um canal de imagens no /configurar. Por enquanto, use um link direto.")
        channel = self.bot.get_channel(int(cid)) or await self.bot.fetch_channel(int(cid))
        if not getattr(channel, "guild", None) or channel.guild.id != guild_id:
            raise UserError("O canal de imagens configurado não está disponível neste servidor.")
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
