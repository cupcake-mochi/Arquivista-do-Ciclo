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
from arquivista.domain import Actor, find_work, work_groups
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
            def get_guild(self, _): return object()
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


class PurgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Store(Path(self.tmp.name) / "d.sqlite")
        self.a = Archive(self.s, G1)
        self.staff, self.member = Actor("5" * 18, "staff", True), Actor(U1, "m", False)
    def tearDown(self):
        self.s.close(); self.tmp.cleanup()
    def run_(self, action, actor, data, rid=None):
        return asyncio.run(self.a.call(action, actor, data, rid))
    def make(self, owner, name):
        return self.run_("create", self.staff, {"owner": {"id": owner, "name": "x"}, "fields": {"appearance": name, "work": "Azur Lane"}})["record"]["id"]

    def test_purge_removes_all_of_one_member_and_keeps_audit(self):
        self.s.set_guild(G1, log_channel="7" * 18, sheet_url="https://script.google.com/macros/s/" + "a" * 30 + "/exec", sheet_key="x")
        mine = [self.make(U1, n) for n in ("Takao", "Atago", "Kaga")]
        other = self.make(U2, "Akagi")
        self.run_("change_status", self.staff, {"id": mine[2], "revision": 1, "status": "Liberado"})
        self.s.db.execute("UPDATE notices SET sent=1"); self.s.db.commit()
        data = {"owner_id": U1, "ids": sorted(mine)}
        with self.assertRaises(Exception) as ctx:
            self.run_("purge", self.member, data)
        self.assertEqual(ctx.exception.code, "FORBIDDEN")
        res = self.run_("purge", self.staff, data, "req-1")
        self.assertEqual(res, {"changed": True, "removed": 3})
        self.assertEqual([r["id"] for r in self.s.records(G1)], [other])
        # Um aviso só no canal de histórico; a auditoria guarda um evento por cadastro.
        notices = self.s.pending()
        self.assertEqual([n["data"].count('"purged"') for n in notices], [1])
        kinds = [r[0] for r in self.s.db.execute("SELECT kind FROM events WHERE record_id IN (?,?,?) ORDER BY seq", mine)]
        self.assertEqual(kinds.count("remove"), 3)
        # A planilha recebe uma limpeza por cadastro.
        ops = [r["payload"] for r in self.s.db.execute("SELECT payload FROM sheet_outbox WHERE guild_id=?", (G1,))]
        self.assertEqual(sum('"clear"' in o for o in ops), 3)
        # Repetir a mesma confirmação não apaga de novo nem duplica aviso.
        self.assertEqual(self.run_("purge", self.staff, data, "req-1"), res)
        self.assertEqual(len(self.s.pending()), 1)

    def test_purge_refuses_when_list_changed(self):
        first = self.make(U1, "Takao")
        self.make(U1, "Atago")  # cadastrado depois que a confirmação abriu
        with self.assertRaises(Exception) as ctx:
            self.run_("purge", self.staff, {"owner_id": U1, "ids": [first]})
        self.assertEqual(ctx.exception.code, "STALE")
        self.assertEqual(len(self.s.records(G1)), 2)
        with self.assertRaises(Exception) as ctx:
            self.run_("purge", self.staff, {"owner_id": "abc", "ids": [first]})
        self.assertEqual(ctx.exception.code, "INVALID")


class WorkTests(unittest.TestCase):
    def labels(self, works):
        return {g["label"]: g["names"] for g in work_groups(works)}

    def test_spellings_of_one_work_group_together(self):
        g = self.labels(["Arknights", "arknights", "Arknights Endfield", "Endfield", "arknighs", "Azur Lane",
                         "Honkai: Star Rail", "Honkai Star Rail", "HSR", "Umamusume", "Uma Musume Pretty Derby"])
        self.assertEqual(sorted(g["Arknights"]), ["Arknights", "Arknights Endfield", "Endfield", "arknighs"])
        self.assertEqual(sorted(g["Honkai Star Rail"]), ["HSR", "Honkai Star Rail"])
        self.assertIn("Uma Musume Pretty Derby", g["Umamusume"])
        self.assertEqual(g["Azur Lane"], ["Azur Lane"])

    def test_different_works_stay_apart(self):
        g = self.labels(["Love Live", "Live A Live", "Date A Live", "Persona 4", "Persona 5", "Genshin Impact",
                         "Honkai Impact 3rd", "Fate/stay night", "Fate/Grand Order", "Final Fantasy VII", "Dragon Quest"])
        self.assertEqual(len(g), 11)

    def test_staff_aliases_join_and_name_groups(self):
        aliases = {"JJK": "Jujutsu Kaisen", "AK": "Arknights", "FGO": "Fate/Grand Order"}
        groups = work_groups(["JJK", "jujutsu kaisen", "Arknights", "Endfield", "Arknights Endfield"], aliases)
        self.assertEqual([(g["label"], g["count"]) for g in groups], [("Arknights", 3), ("Jujutsu Kaisen", 2)])
        self.assertEqual(groups[1]["names"], ["Jujutsu Kaisen", "JJK"])
        self.assertEqual([g["label"] for g in find_work(groups, "ak")], ["Arknights"])
        self.assertEqual([g["label"] for g in find_work(groups, "jjk")], ["Jujutsu Kaisen"])
        self.assertEqual(find_work(groups, "fgo"), [])  # apelido sem cadastro usando não vira grupo vazio

    def test_alias_command(self):
        from arquivista.bot import Arquivista
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        s = Store(Path(tmp.name) / "d.sqlite"); self.addCleanup(s.close)
        class Bot: store = s
        run = lambda q: Arquivista.alias_command(Bot(), G1, q)
        self.assertIn("Nenhum apelido", run(""))
        self.assertIn("Jujutsu Kaisen", run("JJK = Jujutsu Kaisen"))
        run("jjk=Jujutsu Kaisen 0")  # mesma chave: troca
        self.assertEqual(s.aliases(G1), {"jjk": "Jujutsu Kaisen 0"})
        self.assertIn("jjk", run(""))
        for bad in ("JJK", "JJK =", "Arknights = arknights", "-nada"):
            with self.assertRaises(Exception, msg=bad):
                run(bad)
        self.assertIn("removido", run("- JJK"))
        self.assertEqual(s.aliases(G1), {})

    def test_search_reaches_whole_group(self):
        groups = work_groups(["Arknights", "Arknights Endfield", "Endfield", "Azur Lane"])
        for q in ("endfield", "ARKNIGHS", "ark", "arknights endfield"):
            self.assertEqual([g["label"] for g in find_work(groups, q)], ["Arknights"], q)
        self.assertEqual(find_work(groups, "nikke"), [])
        self.assertEqual(find_work(groups, "  "), [])


class PullTests(unittest.TestCase):
    """Edição feita à mão na planilha voltando para o banco, contra a planilha simulada."""
    def setUp(self):
        from arquivista.config import Config
        from arquivista.sheet import SheetSync, seal
        sys.path.insert(0, str(ROOT / "tests"))
        from sheet_sim import FakeSheet
        self.tmp = tempfile.TemporaryDirectory()
        self.s = s = Store(Path(self.tmp.name) / "d.sqlite")
        s.set_guild(G1, log_channel="7" * 18, sheet_url="https://script.google.com/macros/s/" + "a" * 30 + "/exec",
                    sheet_key=seal(b"k" * 32, "f" * 64))
        class Member: name = "mizuki_sama"
        class Guild:
            def get_member(self, _): return Member()
        class Bot:
            store = s; config = Config("T", Path("x"), master_key=b"k" * 32); session = None
            class user: id = 999999999999999999
            def get_guild(self, _): return Guild()
            def now_text(self): return "agora"
            def archive(self, gid): return Archive(s, gid)
        self.sync = SheetSync(Bot())
        self.sheet = FakeSheet()
        self.sync.bridge = lambda gid, cfg=None: self.sheet
        self.a = Archive(s, G1)
        self.ids = [asyncio.run(self.a.call("create", Actor(U1, "m"), {"fields": {"appearance": n, "work": "Azur Lane"}}))["record"]["id"]
                    for n in ("Takao", "Atago")]
        asyncio.run(self.sync.run())
        self.assertEqual(self.s.sheet_pending(G1), (0, 0))
    def tearDown(self):
        self.s.close(); self.tmp.cleanup()
    def cell(self, rid, col, value=None, below=0):
        from arquivista import layout
        grid = self.grid()
        row = next(i for i, line in enumerate(grid) if line[layout.ID - 1] == rid) + below
        if value is not None:
            grid[row][col - 1] = value
        return grid[row][col - 1]
    def grid(self):
        return next(iter(self.sheet.grids.values()))
    def pull(self):
        n = asyncio.run(self.sync.pull(G1))
        asyncio.run(self.sync.run())  # devolve a linha regravada para a planilha
        return n
    def rec(self, rid):
        return self.a.record(rid)

    def test_edit_in_sheet_reaches_bot_with_unknown_author(self):
        from arquivista import layout
        self.cell(self.ids[0], layout.SERVER_NAME, "Takao do Mizuki")
        self.cell(self.ids[0], layout.STATUS, "Em uso")
        self.cell(self.ids[0], layout.APPEARANCE, "Aprovada na call.", below=2)
        self.s.db.execute("UPDATE notices SET sent=1"); self.s.db.commit()
        self.assertEqual(self.pull(), 1)
        r = self.rec(self.ids[0])
        self.assertEqual((r["server_name"], r["status"], r["justification"], r["revision"]),
                         ("Takao do Mizuki", "Em uso", "Aprovada na call.", 2))
        self.assertEqual(self.cell(self.ids[0], layout.MARK), 2)  # a planilha recebeu a revisão nova
        ev = self.s.db.execute("SELECT actor_id,source FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        self.assertEqual(tuple(ev), ("", "planilha"))
        self.assertEqual(len(self.s.pending()), 1)  # aviso no canal de histórico
        self.assertEqual(self.pull(), 0)  # nada mais a trazer

    def test_refused_edit_is_undone_in_sheet(self):
        from arquivista import layout
        self.cell(self.ids[1], layout.APPEARANCE, "Takao")  # repetiria Takao + Azur Lane
        self.cell(self.ids[0], layout.STATUS, "Qualquer")
        self.assertEqual(self.pull(), 0)
        self.assertEqual(self.cell(self.ids[1], layout.APPEARANCE), "Atago")
        self.assertEqual(self.cell(self.ids[0], layout.STATUS), "Em preparação")
        self.assertIn("já ocupadas", self.s.guild(G1)["sheet_note"])
        self.assertEqual(self.rec(self.ids[1])["revision"], 1)

    def test_row_typed_in_empty_slot_becomes_record_there(self):
        from arquivista import layout
        grid = self.grid()
        row = next(i for i, line in enumerate(grid) if line[layout.ID - 1] == self.ids[1]) + 8  # posição 4, pulando a 3
        grid[row][layout.APPEARANCE - 1] = "Kaga"; grid[row][layout.WORK - 1] = "Azur Lane"
        self.assertEqual(self.pull(), 1)
        new = [r for r in self.s.records(G1) if r["appearance"] == "Kaga"]
        self.assertEqual((len(new), new[0]["owner_id"], new[0]["status"]), (1, U1, "Em preparação"))
        grid = self.grid()  # a planilha simulada troca a grade inteira a cada gravação
        self.assertEqual(grid[row][layout.ID - 1], new[0]["id"])  # na linha onde foi digitado
        self.assertEqual(self.pull(), 0)
        grid = self.grid()
        # Cadastro novo pelo bot não pisa numa linha digitada que ainda não foi lida.
        grid[row - 4][layout.APPEARANCE - 1] = "Akagi"; grid[row - 4][layout.WORK - 1] = "Azur Lane"
        asyncio.run(self.a.call("create", Actor(U1, "m"), {"fields": {"appearance": "Shoukaku", "work": "Azur Lane"}}))
        asyncio.run(self.sync.run())
        self.assertEqual(self.grid()[row - 4][layout.APPEARANCE - 1], "Akagi")
        self.assertEqual(self.pull(), 1)
        self.assertEqual(sorted(r["appearance"] for r in self.s.records(G1)), ["Akagi", "Atago", "Kaga", "Shoukaku", "Takao"])

    def test_row_deleted_by_hand_comes_back(self):
        from arquivista import layout
        grid = self.grid()
        row = next(i for i, line in enumerate(grid) if line[layout.ID - 1] == self.ids[0])
        for c in (layout.APPEARANCE, layout.WORK, layout.STATUS, layout.ID, layout.OWNER, layout.MARK):
            grid[row][c - 1] = ""
        self.pull()
        self.assertTrue(any(line[layout.ID - 1] == self.ids[0] for line in self.grid()))
        self.assertIn("/remover", self.s.guild(G1)["sheet_note"])
        self.assertEqual(len(self.s.records(G1)), 2)

    def test_sheet_edit_survives_discord_change_before_pull(self):
        from arquivista import layout
        self.cell(self.ids[0], layout.APPEARANCE, "Aprovada na call.", below=2)  # justificativa, pela planilha
        self.cell(self.ids[0], layout.SERVER_NAME, "pela planilha")
        asyncio.run(self.a.call("edit", Actor(U1, "m"), {"id": self.ids[0], "revision": 1, "fields": {"server_name": "pelo discord"}}))
        asyncio.run(self.sync.run())  # grava antes da leitura de 5 em 5 minutos
        r = self.rec(self.ids[0])
        self.assertEqual((r["justification"], r["server_name"]), ("Aprovada na call.", "pelo discord"))
        self.assertEqual(self.cell(self.ids[0], layout.APPEARANCE, below=2), "Aprovada na call.")
        self.assertEqual(self.cell(self.ids[0], layout.SERVER_NAME), "pelo discord")
        self.assertEqual(self.s.sheet_pending(G1), (0, 0))

    def test_pull_waits_while_writes_are_failing(self):
        from arquivista import layout
        grid = self.grid()
        row = next(i for i, line in enumerate(grid) if line[layout.ID - 1] == self.ids[1]) + 4
        grid[row][layout.APPEARANCE - 1] = "Kaga"; grid[row][layout.WORK - 1] = "Azur Lane"
        from arquivista.domain import BridgeError
        self.sheet.fail = None
        real = self.sheet.call
        async def no_write(action, actor, data):
            if action == "write":
                raise BridgeError("INTERNAL", "x")
            return await real(action, actor, data)
        self.sheet.call = no_write
        self.assertEqual(asyncio.run(self.sync.pull(G1)), 1)
        asyncio.run(self.sync.run())  # gravação falha e entra em espera
        self.assertEqual(asyncio.run(self.sync.pull(G1)), 0)  # não importa a mesma linha de novo
        self.assertEqual(sum(r["appearance"] == "Kaga" for r in self.s.records(G1)), 1)

    def test_row_inserted_in_block_stops_writes_without_new_tab(self):
        from arquivista import layout
        grid = self.grid()
        sid = next(iter(self.sheet.grids))
        grid.insert(20, [""] * 11); self.sheet.depths[sid].insert(20, 0)  # linha inserida à mão no meio das fichas
        asyncio.run(self.a.call("edit", Actor(U1, "m"), {"id": self.ids[0], "revision": 1, "fields": {"server_name": "x"}}))
        asyncio.run(self.sync.run())
        self.assertEqual(len(self.sheet.meta), 1)  # não criou outra guia para a mesma pessoa
        self.s.db.execute("UPDATE sheet_outbox SET next_try=0"); self.s.db.commit()
        self.sync.next_pull.clear()
        asyncio.run(self.sync.pull(G1))
        self.assertIn("Ctrl+Z", self.s.guild(G1)["sheet_note"])
        self.assertEqual(len(self.s.records(G1)), 2)

    def test_discord_change_waiting_wins_over_sheet(self):
        from arquivista import layout
        self.cell(self.ids[0], layout.SERVER_NAME, "pela planilha")
        asyncio.run(self.a.call("edit", Actor(U1, "m"), {"id": self.ids[0], "revision": 1, "fields": {"server_name": "pelo discord"}}))
        self.assertEqual(asyncio.run(self.sync.pull(G1)), 0)  # fila primeiro
        asyncio.run(self.sync.run())
        self.assertEqual(self.pull(), 0)
        self.assertEqual(self.rec(self.ids[0])["server_name"], "pelo discord")
        self.assertEqual(self.cell(self.ids[0], layout.SERVER_NAME), "pelo discord")


class DepartedTests(unittest.TestCase):
    def test_lists_owners_who_left(self):
        from arquivista.bot import Arquivista
        import discord
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        s = Store(Path(tmp.name) / "d.sqlite"); self.addCleanup(s.close)
        a = Archive(s, G1)
        for owner, name in ((U1, "Takao"), (U2, "Atago"), (U2, "Kaga")):
            asyncio.run(a.call("create", Actor("5" * 18, "s", True), {"owner": {"id": owner, "name": "x"}, "fields": {"appearance": name, "work": "Azur Lane"}}))
        class Resp: status = 404; reason = "x"
        class Guild:
            id = int(G1)
            def get_member(self, uid): return object() if str(uid) == U1 else None
            async def fetch_member(self, uid): raise discord.NotFound(Resp(), "x")
        class Bot: store = s
        text = asyncio.run(Arquivista.departed(Bot(), Guild()))
        self.assertIn(f"`{U2}` · 2 cadastro(s)", text); self.assertNotIn(U1, text)


class AmiyaPhotoTests(unittest.TestCase):
    def test_webhook_without_photo_gets_amiya_and_messages_use_it(self):
        from arquivista.transport import Carteiro
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        s = Store(Path(tmp.name) / "d.sqlite"); self.addCleanup(s.close)
        sent, edits = [], []
        class Avatar:
            def __init__(self, url): self.url = url
        class Hook:
            name, token, application_id, avatar = "Arquivista do Ciclo", "t", 5, None
            class user: id = 1
            display_avatar = Avatar("https://cdn.discordapp.com/embed/avatars/0.png")
            async def edit(self, **kw):
                edits.append(kw)
                class Edited: avatar = "abc"; display_avatar = Avatar("https://cdn.discordapp.com/avatars/9/abc.png")
                return Edited()
            async def send(self, **kw):
                sent.append(kw)
                class M: id = 77
                return M()
        hook = Hook()
        class Channel:
            id = 3
            async def webhooks(self): return [hook]
        class Bot:
            store = s; application_id = 5
            class user:
                id = 1
                class display_avatar: url = "https://cdn.discordapp.com/avatars/1/portal.png"
            class config: persona_name = "Amiya"
        c = Carteiro(Bot())
        import discord
        asyncio.run(c.send(Channel(), embed=discord.Embed(title="x")))
        self.assertEqual(len(edits), 1)
        self.assertEqual(sent[0]["avatar_url"], "https://cdn.discordapp.com/avatars/9/abc.png")
        self.assertEqual(sent[0]["username"], "Amiya")
        self.assertEqual(sent[0]["embed"].author.icon_url, "https://cdn.discordapp.com/avatars/9/abc.png")


if __name__ == "__main__":
    unittest.main()
