"""Planilha simulada para os testes: grade de valores + nível de agrupamento de cada linha.

Imita o Sheets real onde o layout depende dele: linhas acrescentadas no fim herdam o nível
da última linha (o grupo do último bloco se estende), linhas inseridas herdam o da linha
seguinte, e updateDimensionGroup exige um grupo exato naquele nível. Formatação, mesclagens
e bordas não são simuladas; isso é conferido numa planilha real (docs/TESTES.md).
"""
from __future__ import annotations
import copy
import re

from arquivista.domain import BridgeError

ALLOWED = {"addSheet", "updateSheetProperties", "updateDimensionProperties", "appendDimension", "insertDimension",
           "addDimensionGroup", "deleteDimensionGroup", "updateDimensionGroup", "updateCells", "repeatCell", "mergeCells",
           "updateBorders", "addConditionalFormatRule", "setDataValidation"}


def _blank() -> list:
    return [""] * 11


class FakeSheet:
    """Faz o papel do script 2.x: status, read e write, com a mesma conferência de 'expect'."""
    def __init__(self, sep: str = ";", version: str = "2.0.0"):
        self.sep, self.version = sep, version
        self.meta: list[dict] = []          # [{title, sheetId}] na ordem das guias
        self.grids: dict[int, list[list]] = {}
        self.depths: dict[int, list[int]] = {}
        self.calls: list[tuple[str, dict]] = []
        self.writes = 0
        self.fail: BridgeError | None = None

    def add_plain(self, title: str, sheet_id: int, rows: list[list]) -> None:
        """Guia criada por fora do bot (ex.: a do dono da planilha)."""
        self.meta.append({"title": title, "sheetId": sheet_id})
        self.grids[sheet_id] = [list(r) + [""] * (11 - len(r)) for r in rows]
        self.depths[sheet_id] = [0] * len(rows)

    async def call(self, action: str, actor, data: dict) -> dict:
        self.calls.append((action, data))
        if self.fail:
            raise self.fail
        if action == "status":
            return {"version": self.version, "sep": self.sep,
                    "sheets": [{"title": m["title"], "sheetId": m["sheetId"], "rows": len(self.grids[m["sheetId"]])} for m in self.meta]}
        if action == "read":
            return {"values": [self.read(r) for r in data["ranges"]]}
        if action == "write":
            for e in data["expect"]:
                m = next((x for x in self.meta if x["sheetId"] == e["sheetId"]), None)
                if not m or m["title"] != e["title"] or len(self.grids[e["sheetId"]]) != e["rows"]:
                    raise BridgeError("CHANGED", "mudou")
            assert all(len(q) == 1 and next(iter(q)) in ALLOWED for q in data["requests"]), "pedido fora da lista do script"
            self.apply(data["requests"])
            self.writes += 1
            return {}
        raise BridgeError("INVALID", "ação")

    def read(self, a1: str) -> list[list]:
        cut = a1.rindex("'!")
        title, cells = a1[1:cut].replace("''", "'"), a1[cut + 2:]
        m = next(x for x in self.meta if x["title"] == title)
        g = self.grids[m["sheetId"]]
        first, last, rows = re.fullmatch(r"([A-K])1:([A-K])(\d+)", cells).groups()
        assert int(rows) == len(g)
        a, z = ord(first) - 65, ord(last) - 64
        out = [list(line[a:z]) for line in g]
        # Como a API: tira células vazias do fim de cada linha e linhas vazias do fim.
        for line in out:
            while line and line[-1] == "":
                line.pop()
        while out and not out[-1]:
            out.pop()
        return out

    def _group_at(self, d: list[int], start: int, end: int, depth: int) -> bool:
        # Grupo de nível depth = trecho máximo de linhas com nível >= depth.
        if start >= end or any(x < depth for x in d[start:end]):
            return False
        return (start == 0 or d[start - 1] < depth) and (end == len(d) or d[end] < depth)

    def apply(self, requests: list[dict]) -> None:
        # Uma batch do Sheets é atômica: aplica numa cópia e só troca se tudo deu certo.
        grids, depths, meta = copy.deepcopy(self.grids), copy.deepcopy(self.depths), copy.deepcopy(self.meta)
        for q in requests:
            (kind, v), = q.items()
            if kind == "addSheet":
                p = v["properties"]
                assert p["sheetId"] not in grids and all(m["title"].lower() != p["title"].lower() for m in meta), "guia repetida"
                meta.append({"title": p["title"], "sheetId": p["sheetId"]})
                grids[p["sheetId"]] = [_blank() for _ in range(p["gridProperties"]["rowCount"])]
                depths[p["sheetId"]] = [0] * p["gridProperties"]["rowCount"]
            elif kind == "updateSheetProperties":
                p = v["properties"]
                assert all(m["title"].lower() != p["title"].lower() for m in meta if m["sheetId"] != p["sheetId"]), "nome repetido"
                next(m for m in meta if m["sheetId"] == p["sheetId"])["title"] = p["title"]
            elif kind == "appendDimension":
                g, d = grids[v["sheetId"]], depths[v["sheetId"]]
                last = d[-1] if d else 0
                for _ in range(v["length"]):
                    g.append(_blank()); d.append(last)
            elif kind == "insertDimension":
                r = v["range"]; g, d = grids[r["sheetId"]], depths[r["sheetId"]]
                n = r["endIndex"] - r["startIndex"]
                inherit = d[r["startIndex"]] if r["startIndex"] < len(d) else 0
                g[r["startIndex"]:r["startIndex"]] = [_blank() for _ in range(n)]
                d[r["startIndex"]:r["startIndex"]] = [inherit] * n
            elif kind == "addDimensionGroup":
                r = v["range"]; d = depths[r["sheetId"]]
                for i in range(r["startIndex"], r["endIndex"]):
                    d[i] += 1
            elif kind == "deleteDimensionGroup":
                r = v["range"]; d = depths[r["sheetId"]]
                assert all(x > 0 for x in d[r["startIndex"]:r["endIndex"]]), "deleteDimensionGroup sem grupo"
                for i in range(r["startIndex"], r["endIndex"]):
                    d[i] -= 1
            elif kind == "updateDimensionGroup":
                g = v["dimensionGroup"]; r = g["range"]
                assert self._group_at(depths[r["sheetId"]], r["startIndex"], r["endIndex"], g["depth"]), \
                    f"updateDimensionGroup sem grupo exato no nível {g['depth']} em {r['startIndex']}:{r['endIndex']}"
            elif kind == "updateCells":
                s = v["start"]; g = grids[s["sheetId"]]
                assert s["rowIndex"] < len(g), "escrita fora da grade"
                for i, row in enumerate(v["rows"]):
                    for j, c in enumerate(row["values"]):
                        assert s["columnIndex"] + j < 11, "escrita fora das colunas A:K"
                        u = c.get("userEnteredValue", {})
                        g[s["rowIndex"] + i][s["columnIndex"] + j] = u.get("formulaValue", u.get("numberValue", u.get("stringValue", "")))
        self.grids, self.depths, self.meta = grids, depths, meta

    def title(self, sheet_id: int) -> str:
        return next(m["title"] for m in self.meta if m["sheetId"] == sheet_id)
