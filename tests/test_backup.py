"""Backup periódico: arquivo restaurável pelo importar.py, planilha .xlsx e agenda por servidor."""
from __future__ import annotations
import asyncio
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arquivista import backup
from arquivista.archive import Archive
from arquivista.domain import Actor
from arquivista.importer import apply, check
from arquivista.store import Store

G1, G2 = "111111111111111111", "222222222222222222"
U1, U2 = "333333333333333333", "444444444444444444"


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Store(Path(self.tmp.name) / "data.sqlite")
        a = Archive(self.s, G1)
        for owner, name, work in ((U1, "Takao", "Azur Lane"), (U1, "Amiya <&\"'>", "Arknights"), (U2, "Lucia", "PGR")):
            asyncio.run(a.call("create", Actor(owner, "x", True), {"fields": {"appearance": name, "work": work, "server_name": "Nome &quot; aqui"}}))
    def tearDown(self):
        self.s.close(); self.tmp.cleanup()

    def test_json_restores_with_importer(self):
        records = self.s.records(G1)
        data = json.loads(backup.export_json(G1, records))
        ok, errors, _ = check(data)
        self.assertEqual(errors, [])
        self.assertEqual(len(ok), 3)
        other = Store(Path(self.tmp.name) / "novo.sqlite")
        try:
            self.assertEqual(apply(other, G1, ok), 3)
            self.assertEqual({r["appearance"] for r in other.records(G1)}, {r["appearance"] for r in records})
        finally:
            other.close()

    def test_workbook_is_valid_xlsx_with_one_tab_per_member(self):
        data = backup.workbook(self.s.records(G1), {U1: "mizuki_sama", U2: "mizuki_sama"})
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                ET.fromstring(z.read(name))  # XML bem formado em todas as partes
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            self.assertEqual([s.get("name") for s in wb.find("m:sheets", ns)], ["mizuki_sama", "mizuki_sama (2)"])
            sheet = z.read("xl/worksheets/sheet1.xml").decode()
            self.assertIn("Amiya &lt;&amp;\"'&gt;", sheet)
        self.assertTrue(backup.workbook([], {}))  # servidor vazio ainda gera um arquivo válido

    def test_sheet_name_rules(self):
        taken = set()
        self.assertEqual(backup._sheet_name("a/b:c*?[x]", taken), "abcx")
        self.assertEqual(backup._sheet_name("ABCX", taken), "ABCX (2)")
        self.assertLessEqual(len(backup._sheet_name("x" * 60, taken)), 31)

    def test_due_schedule(self):
        self.assertEqual(self.s.backup_due(), [])
        self.s.set_guild(G1, backup_channel="5" * 18, backup_hours=24, backup_next=time.time() - 1)
        self.s.set_guild(G2, backup_channel="6" * 18, backup_hours=6, backup_next=time.time() + 100)
        self.assertEqual(self.s.backup_due(), [G1])
        g = self.s.guild(G1)
        self.assertEqual(g["backup_hours"], 24)
        self.assertIsInstance(g["backup_next"], float)


if __name__ == "__main__":
    unittest.main()
