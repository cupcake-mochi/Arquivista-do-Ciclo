"""Montagem da planilha pelo bot, contra a planilha simulada (tests/sheet_sim.py).

Cada rodada faz o caminho real: lê pelo script simulado, planeja, grava e confere que o
modelo do bot bate com a grade resultante.
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from arquivista import layout
from arquivista.domain import BridgeError
from arquivista.sheet import read_sheet
from sheet_sim import FakeSheet

A, B = "111111111111111111", "222222222222222222"
NAMES = {A: "mizuki_sama", B: "takao"}


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.serial = 0
        self.sheet = FakeSheet()
    def rec(self, owner, **extra):
        self.serial += 1
        r = {"id": "AP-00000000-0000-0000-0000-%012d" % self.serial, "owner_id": owner,
             "owner_name": NAMES.get(owner, "membro_" + owner[-2:]), "appearance": f"Personagem {self.serial}", "work": "Obra",
             "server_name": "", "status": "Em uso", "justification": "", "image_url": "", "date": "2026-10-20", "revision": 1}
        r.update(extra)
        return r
    def run_ops(self, ops, budget=None):
        model, expect = asyncio.run(read_sheet(self.sheet, None))
        requests, results = model.plan(ops, budget)
        if requests:
            asyncio.run(self.sheet.call("write", None, {"requests": requests, "expect": expect}))
        for t in model.tabs:
            self.assertEqual(self.sheet.grids[t.sheet_id], t.grid, "modelo diferente da planilha em " + t.name)
            self.assertEqual(self.sheet.title(t.sheet_id), t.name)
        return model, requests, results
    def model(self):
        return asyncio.run(read_sheet(self.sheet, None))[0]

    def test_first_record_creates_tab_named_by_username(self):
        r = self.rec(A, justification="teste", image_url="https://exemplo.com/a.png")
        m, _, res = self.run_ops([up(r)])
        self.assertEqual(res, [{"id": r["id"], "status": "ok"}])
        self.assertEqual(m.tabs[0].name, "mizuki_sama")
        b = m.blocks()[0]
        loc = m.find(r["id"])
        self.assertEqual((b.owner, b.slots, b.start, loc[2]), (A, 20, 5, 1))
        line = m.tabs[0].grid[loc[1] - 1]
        self.assertEqual(line[1:6], [r["appearance"], "", "Obra", "Em uso", 46315])
        self.assertEqual(line[7:11], ["https://exemplo.com/a.png", r["id"], A, 1])
        self.assertEqual(m.tabs[0].grid[loc[1] + 1][1], "teste")
        self.assertEqual(m.tabs[0].grid[b.start - 1][0], "mizuki_sama")
        self.assertRegex(line[6], r'^=IF\(H\d+="";"";IFERROR\(IMAGE\(H\d+\);""\)\)$')

    def test_formula_separator(self):
        self.assertEqual(layout.Model(";").f('=IF(A1="a,b",1,2)'), '=IF(A1="a,b";1;2)')
        self.assertEqual(layout.Model(",").f("=IF(A1,1,2)"), "=IF(A1,1,2)")

    def test_revisions(self):
        r = self.rec(A)
        m, _, _ = self.run_ops([up(r)])
        row = m.find(r["id"])[1]
        _, req, res = self.run_ops([up(r)])
        self.assertEqual((res[0]["status"], req), ("ok", []))
        m, _, _ = self.run_ops([up(dict(r, revision=3, status="Arquivado"))])
        self.assertEqual(m.find(r["id"])[1], row)
        self.assertEqual(m.tabs[0].grid[row - 1][4], "Arquivado")
        m, _, res = self.run_ops([up(dict(r, revision=2, status="Em uso"))])
        self.assertEqual(res[0]["status"], "stale")
        self.assertEqual(m.tabs[0].grid[row - 1][4], "Arquivado")

    def test_block_grows_without_touching_other_tabs(self):
        first = self.rec(B)
        m, _, _ = self.run_ops([up(self.rec(A)), up(first)])
        before = m.block_of(B).start
        m, _, _ = self.run_ops([up(self.rec(A)) for _ in range(17)])
        a, b = m.block_of(A), m.block_of(B)
        self.assertEqual((a.slots, a.used()), (40, 18))
        self.assertEqual(b.start, before)
        self.assertEqual(m.find(first["id"])[0].owner, B)
        for n in range(1, 41):
            self.assertEqual(a.cell(n, layout.N), n)
        # As fórmulas do visor apontam até o rodapé, que desce junto com a inserção.
        self.assertIn(f"A{a.start + 13}:A{a.start + 13 + 80}", m.tabs[0].grid[a.start - 1][5])

    def test_transfer_and_clear(self):
        r = self.rec(A)
        m, _, _ = self.run_ops([up(r), up(self.rec(B))])
        old = m.find(r["id"])[1]
        m, _, _ = self.run_ops([up(dict(r, owner_id=B, owner_name="takao", revision=2))])
        b, _, n = m.find(r["id"])
        self.assertEqual((b.owner, n, b.tab.name), (B, 2, "takao"))
        self.assertEqual(m.tabs[0].grid[old - 1][1:6], ["", "", "", "", ""])
        m, _, res = self.run_ops([{"op": "clear", "id": r["id"], "revision": 3}])
        self.assertEqual(res[0]["status"], "ok")
        self.assertIsNone(m.find(r["id"]))
        _, req, res = self.run_ops([{"op": "clear", "id": r["id"], "revision": 3}])
        self.assertEqual((res[0]["status"], req), ("ok", []))

    def test_image_refresh_same_revision(self):
        r = self.rec(A, image_url="https://cdn.discordapp.com/a.png?ex=1")
        self.run_ops([up(r)])
        m, req, res = self.run_ops([{"op": "image", "id": r["id"], "revision": 1, "image_url": "https://cdn.discordapp.com/a.png?ex=2"}])
        row = m.find(r["id"])[1]
        self.assertEqual((res[0]["status"], len(req)), ("ok", 1))
        self.assertEqual(m.tabs[0].grid[row - 1][7], "https://cdn.discordapp.com/a.png?ex=2")
        m, _, res = self.run_ops([{"op": "image", "id": r["id"], "revision": 2, "image_url": "https://cdn.discordapp.com/a.png?ex=3"}])
        self.assertEqual(res[0]["status"], "stale")

    def test_each_person_gets_own_tab(self):
        m, _, _ = self.run_ops([up(self.rec("1000000000000000%02d" % i)) for i in range(21)])
        self.assertEqual(len(m.tabs), 21)
        self.assertEqual(m.tabs[20].name, "membro_20")
        for t in m.tabs:
            own = [b for b in m.blocks() if b.tab is t]
            self.assertEqual((len(own), own[0].start), (1, 5))

    def test_duplicate_names_and_no_name(self):
        self.sheet.add_plain("Takao", 7, [["notas da staff"]])  # guia que o dono da planilha criou
        m, _, _ = self.run_ops([up(self.rec(B)), up(self.rec("333333333333333333", owner_name="takao")),
                                up(self.rec("444444444444444444", owner_name=""))])
        self.assertEqual([t.name for t in m.tabs], ["takao (2)", "takao (3)", "Membro 444444444444444444"])
        self.assertEqual(self.sheet.grids[7][0][0], "notas da staff")

    def test_username_change_renames_tab(self):
        r = self.rec(A)
        self.run_ops([up(r), up(self.rec(B))])
        m, req, _ = self.run_ops([up(self.rec(A, owner_name="kaltsits"))])
        renames = [q["updateSheetProperties"]["properties"] for q in req if "updateSheetProperties" in q]
        self.assertEqual(renames, [{"sheetId": m.tabs[0].sheet_id, "title": "kaltsits"}])
        self.assertEqual(m.tabs[0].grid[4][0], "kaltsits")
        # Mesmo registro reenviado igual (sincronização completa) ainda conserta o nome, sem regravar a linha.
        _, req, _ = self.run_ops([up(dict(r, owner_name="kaltsits2"))])
        self.assertEqual([next(iter(q)) for q in req], ["updateCells", "updateSheetProperties"])
        # Sem nome (membro saiu do servidor): mantém o que tinha.
        _, req, _ = self.run_ops([up(self.rec(A, owner_name=""))])
        self.assertFalse(any("updateSheetProperties" in q for q in req))
        self.assertEqual(self.model().tabs[0].name, "kaltsits2")

    def test_legacy_single_block_tab_is_renamed(self):
        r = self.rec(A)
        self.run_ops([up(r)])
        self.sheet.meta[0]["title"] = "FICHAS 1–20"  # guia criada pelo script 1.0
        m, _, _ = self.run_ops([up(dict(r, owner_name="kal'tsits"))])
        self.assertEqual(self.sheet.meta[0]["title"], "kal'tsits")
        _, req, _ = self.run_ops([up(dict(r, owner_name="kal'tsits"))])  # nome com aspas é lido de volta
        self.assertEqual(req, [])

    def test_invalid_op_is_isolated(self):
        good = self.rec(A)
        m, _, res = self.run_ops([up(self.rec(A, status="Qualquer")), up(self.rec(A, image_url="http://x.com")),
                                  up(self.rec(A, date="2026-13-01")), up(good), {"op": "outra"}])
        self.assertEqual([x["status"] for x in res], ["invalid", "invalid", "invalid", "ok", "invalid"])
        self.assertEqual(m.blocks()[0].used(), 1)

    def test_budget_splits_large_batches(self):
        ops = [up(self.rec("1000000000000000%02d" % i)) for i in range(5)]
        m, req, res = self.run_ops(ops, budget=200_000)
        self.assertEqual(len(res), 2)  # cada membro novo dá ~100 KB; o resto fica para a próxima gravação
        m, _, res = self.run_ops(ops[2:], budget=200_000)
        m, _, res = self.run_ops(ops[4:], budget=200_000)
        self.assertEqual(len(m.tabs), 5)

    def test_changed_sheet_refuses_write(self):
        model, expect = asyncio.run(read_sheet(self.sheet, None))
        self.run_ops([up(self.rec(A))])
        model, expect = asyncio.run(read_sheet(self.sheet, None))
        requests, _ = model.plan([up(self.rec(A))])
        self.sheet.grids[model.tabs[0].sheet_id].append([""] * 11)  # alguém acrescentou uma linha à mão
        with self.assertRaises(BridgeError) as ctx:
            asyncio.run(self.sheet.call("write", None, {"requests": requests, "expect": expect}))
        self.assertEqual(ctx.exception.code, "CHANGED")

    def test_old_script_is_reported(self):
        self.sheet.version = "1.1.1"
        with self.assertRaises(BridgeError) as ctx:
            asyncio.run(read_sheet(self.sheet, None))
        self.assertEqual(ctx.exception.code, "OLD_SCRIPT")

    def test_real_sheet_scenario(self):
        # Gera o arquivo usado para conferir formatação e fórmulas numa planilha do Google.
        ops = [up(self.rec(A, appearance="Takao", work="Azur Lane", server_name="Takao", justification="Aprovada pela staff.",
                           image_url="https://i.pinimg.com/736x/86/b4/a4/86b4a43271945151a9f2e2dc904c6daf.jpg")),
               up(self.rec(B, status="Em preparação", date=None))]
        ops += [up(self.rec(B)) for _ in range(17)]
        ops.append(up(self.rec(A, appearance="Takao", work="Azur Lane")))
        _, req, _ = self.run_ops(ops)
        import os
        if os.environ.get("PLANILHA_CENARIO"):
            Path(os.environ["PLANILHA_CENARIO"]).write_text(json.dumps(req, ensure_ascii=False))


def up(r):
    return {"op": "upsert", "record": r}


if __name__ == "__main__":
    unittest.main()
