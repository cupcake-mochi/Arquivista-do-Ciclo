"""Renovação dos links de imagem, limpeza de membro e busca por obra."""
from __future__ import annotations
import asyncio
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arquivista import media
from arquivista.archive import Archive
from arquivista.domain import Actor
from arquivista.store import Store

G1 = "111111111111111111"
U1, U2 = "333333333333333333", "444444444444444444"


def cdn(ex: float) -> str:
    return f"https://cdn.discordapp.com/attachments/1/2/a.png?ex={int(ex):x}&is=0&hm=abc"


class RenewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Store(Path(self.tmp.name) / "d.sqlite")
        self.a = Archive(self.s, G1)
    def tearDown(self):
        self.s.close(); self.tmp.cleanup()

    def test_expires_parses_discord_links(self):
        self.assertEqual(media.expires(cdn(1760000000)), 1760000000.0)
        self.assertIsNone(media.expires("https://i.pinimg.com/a.jpg"))

    def test_renews_only_expiring_attachments_in_sheet_servers(self):
        ref = lambda n: f"discord://{G1}/1{'0'*17}/{n}{'0'*17}/1{'0'*17}"
        soon = self.call(U1, "Takao", cdn(time.time() + 600), ref(1))
        later = self.call(U1, "Atago", cdn(time.time() + 20 * 3600), ref(2))
        self.call(U1, "Kaga", "https://i.pinimg.com/a.jpg", "")
        asked = []
        store = self.s
        class Bot:
            def service_actor(self): return Actor("9" * 18, "svc", True)
        bot = Bot(); bot.store = store
        images = media.Images(bot)
        async def resolve(rid, actor, gid):
            asked.append(rid); return cdn(time.time() + 86400)
        images.resolve = resolve
        self.assertEqual(asyncio.run(images.renew()), 0)  # sem planilha conectada, não renova
        images.next_renew = 0
        self.s.set_guild(G1, sheet_url="https://script.google.com/macros/s/" + "a" * 30 + "/exec", sheet_key="x")
        self.assertEqual(asyncio.run(images.renew()), 1)
        self.assertEqual(asked, [soon])
        self.assertEqual(asyncio.run(images.renew()), 0)  # só de 10 em 10 minutos
        # Mensagem apagada: desiste por um tempo em vez de tentar a cada volta.
        images.next_renew = 0
        async def gone(rid, actor, gid): asked.append(rid); return ""
        images.resolve = gone
        asked.clear()
        self.s.db.execute("UPDATE appearances SET image_url=? WHERE id=?", (cdn(time.time() + 60), soon)); self.s.db.commit()
        asyncio.run(images.renew()); images.next_renew = 0; asyncio.run(images.renew())
        self.assertEqual(asked, [soon])
        self.assertNotIn(later, asked)

    def call(self, owner, name, url, ref):
        fields = {"appearance": name, "work": "Azur Lane", "image_url": url}
        if ref:
            fields["media_ref"] = ref
        return asyncio.run(self.a.call("create", Actor(owner, "x", True), {"fields": fields}))["record"]["id"]


if __name__ == "__main__":
    unittest.main()
