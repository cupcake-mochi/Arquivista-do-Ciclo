"""Pesquisa por nome, aparências parecidas (aviso) e recusas da planilha guardadas."""
import asyncio
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arquivista import layout, views
from arquivista.domain import near_names, ranked, same_work, similar_pairs, similar_to
from arquivista.store import Store


def rec(id, appearance, work="Arknights", owner="1", status="Em uso", server_name=""):
    return {"id": "AP-" + id, "appearance": appearance, "work": work, "owner_id": owner, "status": status, "server_name": server_name}


def names(records, query):
    return [r["appearance"] for r in ranked(records, query)]


class SearchTests(unittest.TestCase):
    R = [rec("2b000000", "Skadi", server_name="Katharina"), rec("2b000001", "Skadi Alter"), rec("00000002", "Skirk", "Genshin Impact"),
         rec("00000003", "Saria"), rec("00000004", "Sage", "Sonic", status="Liberado"), rec("00000005", "Savage"),
         rec("00000006", "Saga"), rec("00000007", "Ch'en"), rec("00000008", "SilverAsh"), rec("00000009", "Kafka", "Arknights"),
         rec("00000010", "Kafka", "Honkai Star Rail", status="Liberado"), rec("00000011", "Vladilena Milizé", "86", server_name="Bronya Rand"),
         rec("00000012", "博麗霊夢", "Touhou"), rec("00000013", "🐰", "AK"), rec("00000014", "Don Quixote", "Project Moon")]

    def test_exact_name_does_not_bring_look_alikes(self):
        self.assertEqual(names(self.R, "skadi"), ["Skadi", "Skadi Alter"])
        self.assertEqual(names(self.R, "Saga"), ["Saga"])

    def test_released_exact_match_comes_before_anything_similar(self):
        self.assertEqual(names(self.R, "Sage"), ["Sage"])
        self.assertEqual([r["status"] for r in ranked(self.R, "Kafka")], ["Em uso", "Liberado"])

    def test_piece_of_the_id_is_not_a_match(self):
        self.assertEqual(names(self.R, "2b"), [])
        self.assertEqual(names(self.R, "AP-2b000001"), ["Skadi Alter"])
        self.assertEqual(names(self.R, "ap-2b00"), ["Skadi", "Skadi Alter"])

    def test_server_name_is_searched(self):
        self.assertEqual(names(self.R, "Bronya Rand"), ["Vladilena Milizé"])
        self.assertEqual(names(self.R, "katharina"), ["Skadi"])

    def test_punctuation_accents_spaces_and_order(self):
        for q, want in (("chen", "Ch'en"), ("silver ash", "SilverAsh"), ("vladilena milize", "Vladilena Milizé"), ("Quixote Don", "Don Quixote")):
            self.assertEqual(names(self.R, q), [want], q)

    def test_typo_and_partial_name(self):
        self.assertEqual(names(self.R, "Skady")[0], "Skadi")
        self.assertEqual(names(self.R, "Don Quixotte"), ["Don Quixote"])
        self.assertEqual(names(self.R, "Quix"), ["Don Quixote"])

    def test_each_kind_of_match_drops_the_weaker_ones(self):
        R = [rec("30000001", "Skadi"), rec("30000002", "Skald"), rec("30000003", "Chen", "Skad")]
        self.assertEqual(names(R, "skad"), ["Skadi"])  # começo do nome: sem o erro de digitação nem a obra
        R = [rec("ab000001", "Takao"), rec("cd000001", "Ap Ab"), rec("cd000002", "AP-ab00 Copia")]
        self.assertEqual(names(R, "AP-ab00"), ["Takao"])       # ID: só o ID

    def test_work_narrows_and_work_alone_lists(self):
        self.assertEqual([r["work"] for r in ranked(self.R, "Kafka Honkai Star Rail")], ["Honkai Star Rail"])
        self.assertEqual(names(self.R, "Project Moon"), ["Don Quixote"])

    def test_other_scripts_and_emoji(self):
        self.assertEqual(names(self.R, "博麗霊夢"), ["博麗霊夢"])
        self.assertEqual(names(self.R, "🐰"), ["🐰"])

    def test_nothing_and_everything(self):
        self.assertEqual(names(self.R, "xyzabc"), [])
        self.assertEqual(len(names(self.R, "")), len(self.R))
        self.assertEqual(ranked(self.R, "")[-1]["status"], "Liberado")


class SimilarTests(unittest.TestCase):
    def test_names(self):
        for a, b in (("Don Quixote", "Don Quixotee"), ("Ch'en", "Chen"), ("Silver Ash", "SilverAsh"), ("Vladilena Milizé", "milize vladilena"),
                     ("Dr. Eggman", "Dr.Eggmaa'n")):
            self.assertTrue(near_names(a, b), (a, b))
        for a, b in (("Skadi", "Skadi Alter"), ("Mizuki", "Fumizuki"), ("Zeta marionete", "Eta marionete"), ("Android17", "Android18"),
                     ("Seele", "Saria"), ("", "")):
            self.assertFalse(near_names(a, b), (a, b))

    def test_work_uses_aliases(self):
        self.assertTrue(same_work("Wuthering Waves", "Whutering Waves"))
        self.assertFalse(same_work("Arknights", "Honkai Star Rail"))
        self.assertFalse(same_work("JJK", "Feiticeiros"))
        self.assertTrue(same_work("JJK", "Feiticeiros", {"Feiticeiros": "JJK"}))
        self.assertFalse(same_work("东方", "原神"))

    def test_pairs(self):
        R = [rec("1", "Don Quixote", "Project Moon"), rec("2", "Don Quixotee", "Project Moon"),
             rec("3", "Rover", "Wuthering Waves"), rec("4", "Rover", "Whutering Waves", "2"),
             rec("5", "Kafka", "Arknights"), rec("6", "Kafka", "Honkai Star Rail", "2"),
             rec("7", "Noa", "Blue Archive"), rec("8", "Noa", "Blue Archives", "2", "Liberado"),
             rec("9", "Vergil", "Devil May Cry"), rec("10", "Vergil (Genderbend)", "Devil May Cry Series", "2"),
             rec("11", "Skadi"), rec("12", "Skadi Alter"), rec("13", "Ace"), rec("14", "Ace Nobre", owner="2")]
        sure, look = similar_pairs(R)
        ids = lambda ps: [tuple(r["id"][3:] for r in p) for p in ps]
        self.assertEqual(ids(sure), [("1", "2"), ("3", "4")])
        self.assertEqual(ids(look), [("9", "10")])  # mesmo dono e nome curto demais ficam de fora
        self.assertEqual([r["id"] for r in similar_to(rec("99", "don quixote", "project moon"), R)], ["AP-1", "AP-2"])
        self.assertEqual([r["id"] for r in similar_to(R[0], R)], ["AP-2"])  # não aponta para si mesmo

    def test_big_server_is_quick(self):
        R = [rec(str(n), f"Pessoa{chr(97 + n % 26)}{chr(97 + n // 26 % 26)} Nome{chr(97 + n // 676)}", owner=str(n % 9)) for n in range(1600)]
        t = time.time()
        similar_pairs(R)
        self.assertLess(time.time() - t, 60)  # pior caso de propósito: todos com as mesmas iniciais

    def test_warning_text(self):
        taken = rec("1", "Takao", "Azur Lane", "7")
        self.assertEqual(views.similar_warning({"appearance": "x", "work": "y"}, []), "")
        self.assertIn("já estão ocupadas", views.similar_warning({"appearance": "takao", "work": "azur  lane"}, [taken]))
        text = views.similar_warning({"appearance": "Takaoo", "work": "Azur Lane"}, [taken])
        self.assertIn("Parece repetida", text)
        self.assertIn("<@7>", text)

    def submit(self, mode, record=None, staff=True, **values):
        """Envia o formulário de verdade contra um arquivo em SQLite; devolve o texto da revisão."""
        from arquivista.archive import Archive
        from arquivista.domain import Actor
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                store = Store(Path(tmp) / "a.db")
                try:
                    archive = Archive(store, "1" * 18, "America/Sao_Paulo")
                    for n, (name, work) in enumerate((("Takao", "Azur Lane"), ("Yamashiro", "Azur Lane"))):
                        await archive.call("create", Actor("7" * 18, "Ana", True), {"fields": {"appearance": name, "work": work}, "owner": {"id": "7" * 18, "name": "Ana"}})
                    rows = (await archive.call("list", Actor("7" * 18, "Ana", True), {"owner_id": "", "include_released": True}))["records"]
                    mine = next((r for r in rows if r["appearance"] == record), None)
                    if mine: mine = {**mine, "revision": 1}
                    async def actor(*_): return Actor("7" * 18, "Ana", staff)
                    bot = SimpleNamespace(actor=actor, archive=lambda g: archive, store=store, carteiro=SimpleNamespace(decorate=lambda e: e))
                    modal = views.RecordModal(bot, 5, mode, staff=staff, record=mine)
                    for key, value in values.items():
                        modal.fields[key]._value = value
                    for key, item in modal.fields.items():
                        if key not in values: item._value = str((mine or {}).get(key) or "")
                    sent = []
                    async def reply(i, **kw): sent.append(kw)
                    async def defer(**kw): pass
                    old, views.private_reply = views.private_reply, reply
                    try:
                        await modal.on_submit(SimpleNamespace(user=SimpleNamespace(id=5), guild_id=1, response=SimpleNamespace(defer=defer)))
                    finally:
                        views.private_reply = old
                    return sent[0]["embed"].description
                finally:
                    store.close()
        return asyncio.run(run())

    def test_form_warns_before_saving(self):
        self.assertIn("Parece repetida", self.submit("create", appearance="Takaoo", work="Azur Lane"))
        self.assertIn("já estão ocupadas", self.submit("create", staff=False, appearance="takao", work="azur lane"))
        self.assertNotIn("⚠️", self.submit("create", appearance="Belfast", work="Azur Lane"))
        # Editar só o nome no servidor não avisa; mudar a aparência avisa, sem apontar o próprio cadastro.
        self.assertNotIn("⚠️", self.submit("edit", "Takao", server_name="Rin"))
        self.assertNotIn("⚠️", self.submit("edit", "Takao", appearance="Takaoo"))
        self.assertIn("Yamashiro", self.submit("edit", "Takao", appearance="Yamashirro").split("⚠️")[1])

    def test_list_shows_the_work_and_fits(self):
        async def run():
            bot = SimpleNamespace(carteiro=SimpleNamespace(decorate=lambda e: e))
            v = views.Paginator(bot, 1, [rec(str(n), "A" * 100, "B" * 100, "1" * 19, "Em preparação", "C" * 100) for n in range(12)])
            return (await v.embed()).description
        text = asyncio.run(run())
        self.assertIn("B" * 50, text)
        self.assertLessEqual(len(text), 4096)

    def test_field_fits_discord(self):
        text = views.field_list(["x" * 100] * 40)
        self.assertLessEqual(len(text), 1024)
        self.assertIn("… e mais", text)


class RefusalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Store(Path(self.tmp.name) / "d.sqlite")

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def test_kept_for_a_week_and_new_only_once(self):
        self.assertTrue(self.s.refusal("1", "k", "Takao"))
        self.assertFalse(self.s.refusal("1", "k", "Takao"))
        self.assertEqual([r["text"] for r in self.s.refusals("1")], ["Takao"])
        self.assertEqual(self.s.refusals("2"), [])
        self.s.db.execute("UPDATE sheet_refusals SET last=?", (time.time() - 3600,))
        self.s.db.commit()
        self.assertTrue(self.s.refusal("1", "k", "Takao"))  # alguém tentou de novo depois
        self.s.db.execute("UPDATE sheet_refusals SET last=?", (time.time() - 8 * 86400,))
        self.s.db.commit()
        self.assertEqual(self.s.refusals("1"), [])


class DiagnosticTests(unittest.TestCase):
    def test_fields_list_pairs_and_refusals_within_discord_limits(self):
        from arquivista.bot import Arquivista
        records = []
        for n in range(60):
            base = "Nome" + chr(97 + n % 26) * 5 + chr(97 + n // 26) * 5
            records += [rec(f"a{n}", base, "Obra " + "x" * 40, "1" * 19), rec(f"b{n}", base + "!", "Obra " + "x" * 40, "2" * 19)]
        now = time.time()
        bot = SimpleNamespace(store=SimpleNamespace(records=lambda g: records, aliases=lambda g: {}, refusals=lambda g: [
            {"text": "Takao (guia ana): já ocupada; a ficha voltou para Atago", "last": now}, {"text": "Kaga (guia ana): já ocupada", "last": now}]))
        e = views.card("Diagnóstico privado", "x" * 2800)
        asyncio.run(Arquivista.diagnose_names(bot, e, 1, {"sheet_note": "Kaga (guia ana): já ocupada"}))
        self.assertEqual(e.fields[0].name, "Possíveis repetidos: 60")
        self.assertIn("… e mais", e.fields[0].value)
        self.assertIn("recusadas em 7 dias: 1", e.fields[-1].name)  # a que ainda está na planilha já aparece acima
        self.assertIn("Atago", e.fields[-1].value)
        self.assertTrue(all(len(f.value) <= 1024 for f in e.fields))
        self.assertLessEqual(len(e), 6000)

    def test_nothing_found(self):
        from arquivista.bot import Arquivista
        bot = SimpleNamespace(store=SimpleNamespace(records=lambda g: [], aliases=lambda g: {}, refusals=lambda g: []))
        e = views.card("Diagnóstico privado", "x")
        asyncio.run(Arquivista.diagnose_names(bot, e, 1, {}))
        self.assertEqual([(f.name, f.value) for f in e.fields], [("Possíveis repetidos: 0", "Nenhum.")])


class OrangeTests(unittest.TestCase):
    def model(self):
        m = layout.Model(";")
        m.new_block("1" * 18, "ana")
        m.new_block("2" * 18, "bia")
        m.req = []
        return m

    def rules(self, m):
        return [q["addConditionalFormatRule"] for q in m.req if "addConditionalFormatRule" in q]

    def test_rule_on_every_tab_below_red_and_list_in_index(self):
        m = self.model()
        m.upkeep(flagged=["AP-a", "AP-b"])
        rules = self.rules(m)
        self.assertEqual([r["index"] for r in rules], [0, 0, 1, 1])
        self.assertIn("COUNTIF(INDIRECT(\"'Índice (bot)'!B:B\");$I5)", rules[2]["rule"]["booleanRule"]["condition"]["values"][0]["userEnteredValue"])
        cells = [q["updateCells"] for q in m.req if "updateCells" in q and q["updateCells"]["start"]["sheetId"] == m.index["sheet_id"]]
        flagged = next(c for c in cells if c["start"]["columnIndex"] == 1)
        self.assertEqual([r["values"][0]["userEnteredValue"]["stringValue"] for r in flagged["rows"]], ["AP-a", "AP-b"])
        m.req = []
        m.upkeep(flagged=["AP-a", "AP-b"])
        self.assertEqual(m.req, [])  # nada mudou: nenhuma gravação
        m.upkeep()
        self.assertEqual(m.req, [])  # sem lista: deixa como está
        m.upkeep(flagged=["AP-a"])
        flagged = next(q["updateCells"] for q in m.req if q["updateCells"]["start"]["columnIndex"] == 1)
        self.assertEqual(len(flagged["rows"]), 2)
        self.assertNotIn("AP-b", str(m.req))
        self.assertFalse(self.rules(m))
        m.req = []
        m.new_block("3" * 18, "cleo")
        self.assertEqual(sum("B:B" in str(r) for r in self.rules(m)), 1)  # guia nova já nasce com o laranja

    def test_sheet_from_131_gets_orange_once(self):
        m = self.model()
        m.upkeep()
        m.index.update(orange=False, flags="")
        for t in m.tabs:
            t.grid[1][0] = layout.HELP_RED
        m.req = []
        m.upkeep(flagged=[])
        self.assertEqual([r["index"] for r in self.rules(m)], [1, 1])
        self.assertTrue(all(t.grid[1][0] == layout.HELP_TEXT for t in m.tabs))
        self.assertLessEqual({next(iter(q)) for q in m.req}, {"addConditionalFormatRule", "updateCells"})
        m.req = []
        m.upkeep(flagged=[])
        self.assertEqual(m.req, [])


if __name__ == "__main__":
    unittest.main()
