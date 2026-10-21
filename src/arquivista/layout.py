"""Montagem da planilha conectada: decide onde fica cada ficha e gera os pedidos da API do Sheets.

O script da planilha só confere a assinatura, lê e aplica os pedidos (apps_script/Planilha.gs).
Toda a forma da planilha mora aqui, então mudar o visual é só atualizar o bot.

Modelo em memória: para cada guia de membro, a grade de valores A:K (fórmulas como texto).
Cada função que gera pedidos também atualiza a grade, para o planejamento seguinte ver a
planilha como ela vai ficar. Linhas e colunas começam em 1, como na planilha.
"""
from __future__ import annotations
from .sheet_language import label, formula
import datetime as dt
import json
import re

VERSION = "2.0.0"
STEP, HEAD, WIDTH, FIRST_BLOCK = 20, 13, 11, 5
STATUSES = ("Em preparação", "Em uso", "Arquivado", "Liberado")
HEADERS = ("Nº", "Aparência", "Nome no servidor", "Obra de origem", "Situação", "Cadastro", "Imagem",
           "Link da imagem", "ID do registro", "ID Discord", "Revisão")
WIDTHS = (48, 160, 160, 140, 135, 100, 155, 225, 290, 180, 70)
# Colunas (1 = A). K guarda marcadores e revisões e fica escondida.
N, APPEARANCE, SERVER_NAME, WORK, STATUS, DATE, IMAGE, URL, ID, OWNER, MARK = range(1, 12)
RECORD_ID = re.compile(r"^AP-[0-9A-Za-z-]{8,64}$")
SNOWFLAKE = re.compile(r"^[0-9]{17,20}$")
BAD_TEXT = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class Invalid(Exception):
    """Operação recusada; não deixa pedido nenhum para trás."""


def rgb(r: float, g: float, b: float) -> dict:
    return {"red": r, "green": g, "blue": b}

INK, PURPLE, WHITE = rgb(0.2, 0.255, 0.326), rgb(0.322, 0.231, 0.384), rgb(1, 1, 1)
TITLE, HELP, HEADER = rgb(0.122, 0.165, 0.267), rgb(0.922, 0.933, 0.969), rgb(0.322, 0.227, 0.384)
VISOR, PICK, PICK_INK = rgb(0.925, 0.906, 0.949), rgb(1, 0.945, 0.827), rgb(0.184, 0.345, 0.557)
PHOTO, NAME, NOTE = rgb(0.937, 0.945, 0.961), rgb(0.969, 0.969, 0.98), rgb(0.976, 0.973, 1)
COLUMNS, SECTION, SLOT = rgb(0.204, 0.267, 0.365), rgb(0.922, 0.91, 0.953), rgb(0.878, 0.859, 0.929)
SLOT_INK, MEDIA, LABEL = rgb(0.31, 0.227, 0.4), rgb(0.961, 0.965, 0.976), rgb(0.898, 0.859, 0.949)
JUSTIFY, LINE, FRAME = rgb(0.984, 0.976, 1), rgb(0.796, 0.776, 0.855), rgb(0.541, 0.494, 0.639)
STATUS_COLORS = {"Em preparação": (rgb(1, 0.953, 0.867), rgb(0.557, 0.357, 0.075)),
                 "Em uso": (rgb(0.91, 0.957, 0.925), rgb(0.137, 0.416, 0.282)),
                 "Arquivado": (rgb(0.922, 0.914, 0.961), rgb(0.337, 0.271, 0.475)),
                 "Liberado": (rgb(0.918, 0.937, 0.973), rgb(0.212, 0.337, 0.471))}


class Tab:
    def __init__(self, name: str, sheet_id: int, grid: list[list], language="pt-BR"):
        self.language = language
        self.name, self.sheet_id, self.grid = name, sheet_id, grid


class Block:
    def __init__(self, tab: Tab, owner: str, start: int, end: int):
        self.tab, self.owner, self.start, self.end = tab, owner, start, end
        self.slots = (end - start - HEAD) // 4
    def row(self, n: int) -> int:
        return self.start + HEAD + 4 * (n - 1)
    def cell(self, n: int, col: int):
        return self.tab.grid[self.row(n) - 1][col - 1]
    def used(self) -> int:
        return sum(1 for n in range(1, self.slots + 1) if self.cell(n, ID))
    def free(self, n: int) -> bool:
        # Linha preenchida à mão (sem ID ainda) não é posição livre: o bot vai cadastrar ali.
        return not self.cell(n, ID) and not str(self.cell(n, APPEARANCE) or "").strip()


class Model:
    """Planilha como o bot a enxerga: separador das fórmulas, guias de membro e nomes de todas as guias."""
    def __init__(self, sep: str = ";", tabs: list[Tab] | None = None, names: list[str] | None = None, next_sheet_id: int = 1000, language="pt-BR"):
        self.language = language
        self.sep, self.tabs, self.names, self.next_sheet_id = sep, tabs or [], names or [], next_sheet_id
        self.req: list[dict] = []

    # ---------- utilitários ----------
    def label(self, text):
        return label(text,self.language)

    def f(self, text: str) -> str:
        """Fórmulas são escritas com vírgula e convertidas para o separador da planilha (pt-BR usa ;)."""
        text = formula(text,self.language)
        if self.sep == ",":
            return text
        out, quoted = [], False
        for ch in text:
            if ch == '"':
                quoted = not quoted
            out.append(self.sep if not quoted and ch == "," else ch)
        return "".join(out)
    def set(self, tab: Tab, row: int, col: int, values: list) -> None:
        """Grava valores numa linha e mantém o modelo igual ao que a planilha vai ficar."""
        self.req.append({"updateCells": {"start": {"sheetId": tab.sheet_id, "rowIndex": row - 1, "columnIndex": col - 1},
                                         "rows": [{"values": [_cell(v) for v in values]}], "fields": "userEnteredValue"}})
        line = tab.grid[row - 1]
        for j, v in enumerate(values):
            line[col - 1 + j] = v["f"] if isinstance(v, dict) else ("" if v is None else v)
    def grow(self, tab: Tab, rows: int) -> None:
        if len(tab.grid) >= rows:
            return
        n, start = rows - len(tab.grid), len(tab.grid)
        last = str(tab.grid[start - 1][MARK - 1] or "") if tab.grid else ""
        self.req.append({"appendDimension": {"sheetId": tab.sheet_id, "dimension": "ROWS", "length": n}})
        # No Sheets, linhas acrescentadas entram no grupo da última linha. Quando ela é o rodapé
        # de um bloco, o grupo dele engoliria o bloco novo: tira as linhas novas desse grupo.
        if last.startswith("FIM:"):
            self.req.append({"deleteDimensionGroup": {"range": {"sheetId": tab.sheet_id, "dimension": "ROWS", "startIndex": start, "endIndex": start + n}}})
        tab.grid.extend(_empty(n))
    def insert(self, tab: Tab, before: int, n: int) -> None:
        self.req.append({"insertDimension": {"range": {"sheetId": tab.sheet_id, "dimension": "ROWS", "startIndex": before - 1,
                                                       "endIndex": before - 1 + n}, "inheritFromBefore": False}})
        tab.grid[before - 1:before - 1] = _empty(n)

    # ---------- leitura do modelo ----------
    def blocks(self) -> list[Block]:
        """Blocos lidos dos marcadores da coluna K: BLOCO:<id> no cabeçalho e FIM:<id> no rodapé."""
        out = []
        for tab in self.tabs:
            open_ = None
            for i, line in enumerate(tab.grid):
                k = str(line[MARK - 1] or "")
                if k.startswith("BLOCO:"):
                    open_ = (k[6:], i + 1)
                elif k.startswith("FIM:") and open_ and k[4:] == open_[0]:
                    slots = (i + 1 - open_[1] - HEAD) / 4
                    if slots == int(slots) and slots > 0:
                        out.append(Block(tab, open_[0], open_[1], i + 1))
                    open_ = None
        return out
    def broken(self) -> dict[str, str]:
        """Donos cujo bloco não fecha (linha inserida ou apagada à mão no meio): dono -> nome da guia.
        O bot não grava nesses blocos nem cria outro, para não duplicar a pessoa numa guia nova."""
        out = {}
        for tab in self.tabs:
            for line in tab.grid:
                k = str(line[MARK - 1] or "")
                if k.startswith("BLOCO:"):
                    out[k[6:]] = tab.name
        for b in self.blocks():
            out.pop(b.owner, None)
        return out
    def block_of(self, owner: str) -> Block | None:
        return next((b for b in self.blocks() if b.owner == owner), None)
    def find(self, record_id: str) -> tuple[Block, int, int] | None:
        for b in self.blocks():
            for n in range(1, b.slots + 1):
                if b.cell(n, ID) == record_id:
                    return b, b.row(n), n
        return None
    def records(self) -> int:
        return sum(b.used() for b in self.blocks())

    # ---------- estrutura: guia, bloco de membro e posições ----------
    def tab_name(self, name: str, owner: str, current: str | None = None) -> str:
        """Nome de usuário do dono, com (2), (3)... se já existir outra guia com ele."""
        base = re.sub(r"[\x00-\x1f]", "", str(name or (("Member " if self.language == "en" else "Membro ") + owner))).strip()[:90] or (("Member " if self.language == "en" else "Membro ") + owner)
        # O Sheets não aceita duas guias com o mesmo nome, nem só mudando maiúsculas.
        taken = lambda n: any(x.lower() == n.lower() and x != current for x in self.names)
        out, i = base, 2
        while taken(out):
            out, i = f"{base} ({i})", i + 1
        return out
    def new_tab(self, name: str, owner: str) -> Tab:
        sid = self.next_sheet_id
        self.next_sheet_id += 1
        tab = Tab(self.tab_name(name, owner), sid, _empty(FIRST_BLOCK), self.language)
        self.names.append(tab.name)
        req = self.req
        req.append({"addSheet": {"properties": {"sheetId": sid, "title": tab.name,
            "gridProperties": {"rowCount": FIRST_BLOCK, "columnCount": WIDTH, "frozenRowCount": 3, "hideGridlines": True}}}})
        for i, px in enumerate(WIDTHS):
            req.append({"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                                                      "properties": {"pixelSize": px}, "fields": "pixelSize"}})
        req.append({"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": MARK - 1, "endIndex": MARK},
                                                  "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
        self.tabs.append(tab)
        self.set(tab, 1, 1, [self.label('CATÁLOGO DE APARÊNCIAS')])
        self.set(tab, 2, 1, [self.label('Edite as fichas aqui ou pelo bot. As mudanças chegam ao Discord em cerca de 5 minutos. Use + / − para ver as justificativas. Em vermelho: aparência e obra repetidas nas fichas deste membro.')])
        self.set(tab, 3, 1, [self.label('Escolha o número da ficha para vê-la no visor. A aba começa com 20 posições e ganha mais 20 quando restam duas livres.')])
        for r in (1, 2, 3):
            _merge(req, sid, r, r, 1, 10)
        _format(req, sid, 1, 1, 1, 10, bg=TITLE, ink=WHITE, bold=True, size=16)
        _format(req, sid, 2, 3, 1, 10, bg=HELP)
        _height(req, sid, 1, 1, 44); _height(req, sid, 2, 3, 32); _height(req, sid, 4, 4, 12)
        # Uma regra por coluna para a guia inteira, no lugar de milhares de pedaços.
        status = {"sheetId": sid, "startRowIndex": FIRST_BLOCK - 1, "startColumnIndex": STATUS - 1, "endColumnIndex": STATUS}
        for s in STATUSES:
            bg, ink = STATUS_COLORS[s]
            req.append({"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [status], "booleanRule": {
                "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": self.label(s)}]},
                "format": {"backgroundColor": bg, "textFormat": {"bold": True, "foregroundColor": ink}}}}}})
        r = FIRST_BLOCK
        req.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [{"sheetId": sid, "startRowIndex": r - 1, "startColumnIndex": APPEARANCE - 1, "endColumnIndex": APPEARANCE}],
            "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": self.f(
                f'=AND($I{r}<>"",$E{r}<>"Liberado",COUNTIFS($B:$B,$B{r},$D:$D,$D{r},$E:$E,"<>Liberado",$I:$I,"<>")>1)')}]},
                "format": {"backgroundColor": rgb(0.992, 0.882, 0.882), "textFormat": {"bold": True, "foregroundColor": rgb(0.6, 0.098, 0.129)}}}}}})
        return tab
    def slots(self, tab: Tab, first: int, start_n: int, count: int) -> None:
        req, sid = self.req, tab.sheet_id
        for i in range(count):
            n, r = start_n + i, first + 4 * i
            self.set(tab, r, N, [n])
            self.set(tab, r, IMAGE, [{"f": self.f(f'=IF(H{r}="","",IFERROR(IMAGE(H{r}),""))')}])
            self.set(tab, r + 1, APPEARANCE, [self.label('JUSTIFICATIVA / OBSERVAÇÃO   ·   só para a staff')])
            # Imagem e link só nas 2 linhas sempre visíveis: mesclar com as linhas recolhidas faz a imagem passar por cima.
            _merge(req, sid, r, r + 3, 1, 1); _merge(req, sid, r, r + 1, 7, 7); _merge(req, sid, r, r + 1, 8, 8)
            _merge(req, sid, r + 1, r + 1, 2, 6); _merge(req, sid, r + 2, r + 3, 2, 6)
            _group(req, sid, r + 2, r + 3, 2, True)
        last = first + 4 * count - 1
        _format(req, sid, first, last, 1, 1, bg=SLOT, ink=SLOT_INK, bold=True, size=11, h="CENTER", v="TOP")
        _format(req, sid, first, last, 7, 7, bg=MEDIA, h="CENTER")
        _format(req, sid, first, last, 8, 8, bg=MEDIA, size=9, wrap="CLIP")
        _format(req, sid, first, last, 9, 11, wrap="CLIP")
        _height(req, sid, first, last, 32)
        for i in range(count):
            r = first + 4 * i
            _format(req, sid, r, r, 2, 2, bold=True, ink=PURPLE)
            _format(req, sid, r, r, 3, 5)
            _format(req, sid, r, r, 6, 6, h="CENTER", date=True, language=self.language)
            _format(req, sid, r + 1, r + 1, 2, 6, bg=LABEL, ink=SLOT_INK, bold=True, size=9)
            _format(req, sid, r + 2, r + 3, 2, 6, bg=JUSTIFY, v="TOP")
        for i in range(count):
            r = first + 4 * i
            _border(req, sid, r, r, 1, 10, True)       # linha da ficha, célula por célula
            _border(req, sid, r, r + 3, 1, 10, False)  # contorno da posição inteira
        req.append({"setDataValidation": {"range": _range(sid, first, last, STATUS, STATUS), "rule": {"condition": {"type": "ONE_OF_LIST",
            "values": [{"userEnteredValue": self.label(s)} for s in STATUSES]}, "strict": True, "showCustomUi": True}}})
        # A validação vale para a coluna toda do trecho; as linhas de justificativa não usam E/F.
        req.append({"setDataValidation": {"range": _range(sid, first, last, DATE, DATE), "rule": {"condition": {"type": "DATE_IS_VALID"}, "strict": True}}})
    def new_block(self, owner: str, name: str) -> Block:
        # Uma guia por membro, com o nome de usuário dele.
        tab, s = self.new_tab(name, owner), FIRST_BLOCK
        a = s + HEAD
        z = a + 4 * STEP
        req, sid = self.req, tab.sheet_id
        self.grow(tab, z)
        A, at = f"A{a}:A{z}", (lambda col: f"{col}{a}:{col}{z}")
        M = f"MATCH(F{s + 1},{A},0)"
        pick = lambda col: f"INDEX({at(col)},{M})"
        f = self.f
        self.set(tab, s, 1, [name or (("Member " if self.language == "en" else "Membro ") + owner)])
        self.set(tab, s, 6, [{"f": f(f'=COUNTIFS({A},">=1",{at("I")},"<>")&" / "&MAX({A})')}])
        self.set(tab, s, MARK, ["BLOCO:" + owner])
        self.set(tab, s + 1, 1, [self.label('VISOR DO PERSONAGEM · consulta')])
        self.set(tab, s + 1, 5, [self.label('Escolher nº'), 1])
        self.set(tab, s + 2, 1, [{"f": f(f'=IFERROR({pick("G")},"")')}])
        self.set(tab, s + 2, 3, [{"f": f(f'=IFERROR(IF({pick("B")}="","Nenhuma aparência nesta posição",IF({pick("C")}="",{pick("B")},{pick("C")})),"Escolha uma posição válida")')}])
        self.set(tab, s + 4, 3, [{"f": f(f'=IFERROR("Aparência: "&{pick("B")},"")')}])
        self.set(tab, s + 5, 3, [{"f": f(f'=IFERROR("Obra: "&{pick("D")},"")')}])
        self.set(tab, s + 6, 3, [{"f": f(f'=IFERROR("Situação: "&{pick("E")},"")')}])
        self.set(tab, s + 7, 3, [{"f": f(f'=IFERROR("Cadastro: "&IF({pick("F")}="","não informado",TEXT({pick("F")},"dd/mm/yyyy")),"")')}])
        self.set(tab, s + 8, 3, [self.label('OBSERVAÇÃO / JUSTIFICATIVA · leitura')])
        self.set(tab, s + 9, 3, [{"f": f(f'=IFERROR(IF(INDEX({at("B")},{M}+2)="","Sem observação / justificativa.",INDEX({at("B")},{M}+2)),"")')}])
        self.set(tab, s + 11, 1, [self.label(h) for h in HEADERS])
        self.set(tab, s + 12, 1, [self.label('POSIÇÕES   ·   abra o + ao lado de cada ficha para ver a justificativa')])
        self.set(tab, z, MARK, ["FIM:" + owner])
        _merge(req, sid, s, s, 1, 5); _merge(req, sid, s, s, 6, 7); _merge(req, sid, s + 1, s + 1, 1, 4); _merge(req, sid, s + 1, s + 1, 6, 7)
        _merge(req, sid, s + 2, s + 9, 1, 2); _merge(req, sid, s + 2, s + 3, 3, 7)
        for r in range(s + 4, s + 10):
            _merge(req, sid, r, r, 3, 7)
        _merge(req, sid, s + 12, s + 12, 1, 7)
        _format(req, sid, s, s, 1, 7, bg=HEADER, ink=WHITE, bold=True, size=12)
        _format(req, sid, s + 1, s + 1, 1, 5, bg=VISOR, ink=PURPLE, bold=True)
        _format(req, sid, s + 1, s + 1, 6, 7, bg=PICK, ink=PICK_INK, bold=True, size=12, h="CENTER")
        _format(req, sid, s + 2, s + 9, 1, 2, bg=PHOTO, size=11, h="CENTER")
        _format(req, sid, s + 2, s + 3, 3, 7, bg=NAME, ink=PURPLE, bold=True, size=13)
        _format(req, sid, s + 4, s + 7, 3, 7, size=11)
        _format(req, sid, s + 8, s + 8, 3, 7, bg=VISOR, ink=PURPLE, bold=True)
        _format(req, sid, s + 9, s + 9, 3, 7, bg=NOTE, size=11, v="TOP")
        _format(req, sid, s + 11, s + 11, 1, 10, bg=COLUMNS, ink=WHITE, bold=True)
        _format(req, sid, s + 12, s + 12, 1, 7, bg=SECTION, ink=PURPLE, bold=True, size=9)
        _border(req, sid, s, s + 9, 1, 7, False)
        _border(req, sid, s + 1, s + 1, 1, 7, False)
        _border(req, sid, s + 11, s + 11, 1, 10, True)
        _height(req, sid, s, s, 44); _height(req, sid, s + 1, s + 8, 32); _height(req, sid, s + 9, s + 9, 96)
        _height(req, sid, s + 10, s + 10, 12); _height(req, sid, s + 11, s + 11, 44); _height(req, sid, s + 12, s + 12, 32); _height(req, sid, z, z, 24)
        req.append({"setDataValidation": {"range": _range(sid, s + 1, s + 1, 6, 6), "rule": {"condition": {"type": "NUMBER_BETWEEN",
            "values": [{"userEnteredValue": "1"}, {"userEnteredValue": "10000"}]}, "strict": True, "inputMessage": self.label('Número da posição que o visor mostra.')}}})
        # O grupo do bloco vem antes dos grupos das posições (que ficam no nível 2) e inclui o
        # rodapé, então as linhas inseridas antes dele na expansão entram no grupo.
        _group(req, sid, s + 1, z, 1, False)
        self.slots(tab, a, 1, STEP)
        return self.block_of(owner)
    def expand(self, b: Block) -> Block:
        footer, start_n = b.end, b.slots + 1
        self.insert(b.tab, footer, 4 * STEP)
        self.slots(b.tab, footer, start_n, STEP)
        return self.block_of(b.owner)

    # ---------- mudanças vindas do bot ----------
    def clear_slot(self, b: Block, row: int) -> None:
        self.set(b.tab, row, APPEARANCE, ["", "", "", "", ""])
        self.set(b.tab, row, URL, ["", "", "", ""])
        self.set(b.tab, row + 2, APPEARANCE, [""])
    def owner_name(self, b: Block, name: str) -> None:
        """Nome do dono no cabeçalho e no título da guia (só quando a guia é dele sozinho). Vazio = o bot não achou o membro."""
        if not name:
            return
        if b.tab.grid[b.start - 1][0] != name:
            self.set(b.tab, b.start, 1, [name])
        if sum(1 for x in self.blocks() if x.tab is b.tab) != 1:
            return  # guia antiga com vários membros fica como está
        title = self.tab_name(name, b.owner, b.tab.name)
        if title == b.tab.name:
            return
        self.req.append({"updateSheetProperties": {"properties": {"sheetId": b.tab.sheet_id, "title": title}, "fields": "title"}})
        self.names = [title if x == b.tab.name else x for x in self.names]
        b.tab.name = title
    def upsert(self, op: dict) -> str:
        r = record(op.get("record"))
        if r["owner_id"] in self.broken():
            return "broken"
        mine = self.block_of(r["owner_id"])
        if mine:
            self.owner_name(mine, r["owner_name"])
        loc = self.find(r["id"])
        if loc:
            stored = _num(loc[0].tab.grid[loc[1] - 1][MARK - 1])
            if stored > r["revision"]:
                return "stale"
            if stored == r["revision"] and op.get("force") is not True:
                return "ok"  # force: desfaz uma edição feita na planilha que o bot recusou
            if loc[0].owner != r["owner_id"]:
                self.clear_slot(loc[0], loc[1])
                loc = None
        b = self.block_of(r["owner_id"]) or self.new_block(r["owner_id"], r["owner_name"])
        slot = op.get("slot")
        if not loc and _int(slot) and b.owner == r["owner_id"] and 1 <= slot <= b.slots and not b.cell(slot, ID):
            loc = (b, b.row(slot), slot)  # cadastro que alguém digitou na planilha: fica na linha onde foi digitado
        if not loc:
            n = next((i for i in range(1, b.slots + 1) if b.free(i)), 0)
            if not n:
                b = self.expand(b)
                n = b.slots - STEP + 1
            loc = (b, b.row(n), n)
        tab, row = loc[0].tab, loc[1]
        self.set(tab, row, APPEARANCE, [r["appearance"], r["server_name"], r["work"], self.label(r["status"]), r["date"]])
        self.set(tab, row, URL, [r["image_url"], r["id"], r["owner_id"], r["revision"]])
        self.set(tab, row + 2, APPEARANCE, [r["justification"]])
        # Como a expansão por edição: perto do fim (2 posições livres), o bloco ganha mais 20.
        b = self.block_of(r["owner_id"])
        if sum(b.free(i) for i in range(1, b.slots + 1)) <= 2:
            self.expand(b)
        return "ok"
    def clear(self, op: dict) -> str:
        if not _valid_id(op.get("id")) or not _int(op.get("revision")):
            raise Invalid
        loc = self.find(op["id"])
        if not loc:
            return "ok"
        if _num(loc[0].tab.grid[loc[1] - 1][MARK - 1]) > op["revision"]:
            return "stale"
        self.clear_slot(loc[0], loc[1])
        return "ok"
    def image(self, op: dict) -> str:
        # Link de anexo do Discord expira e o bot renova: troca só o link, na mesma revisão.
        if not _valid_id(op.get("id")) or not _int(op.get("revision")):
            raise Invalid
        url = _url(op.get("image_url") or "")
        loc = self.find(op["id"])
        if not loc:
            return "ok"
        b, row, _ = loc
        if _num(b.tab.grid[row - 1][MARK - 1]) != op["revision"]:
            return "stale"
        if b.tab.grid[row - 1][URL - 1] != url:
            self.set(b.tab, row, URL, [url])
        return "ok"
    def plan(self, ops: list, budget: int | None = None) -> tuple[list[dict], list[dict]]:
        """Planeja as operações em ordem. Com budget (bytes de JSON), para quando os pedidos passam
        do limite; as operações que ficaram de fora não aparecem nos resultados e vão na próxima rodada."""
        self.req, results, size, counted = [], [], 0, 0
        for op in ops:
            op_id = (op.get("id") or (op.get("record") or {}).get("id") or "") if isinstance(op, dict) else ""
            mark = len(self.req)
            try:
                # A validação acontece antes de qualquer mudança, então uma operação inválida não deixa resto.
                kind = op.get("op") if isinstance(op, dict) else None
                if kind == "upsert":
                    status = self.upsert(op)
                elif kind == "clear":
                    status = self.clear(op)
                elif kind == "image":
                    status = self.image(op)
                else:
                    raise Invalid
            except Invalid:
                del self.req[mark:]
                status = "invalid"
            results.append({"id": op_id, "status": status})
            if budget is not None:
                size += len(json.dumps(self.req[counted:], ensure_ascii=False, separators=(",", ":")))
                counted = len(self.req)
                if size >= budget:
                    break
        return self.req, results


def record(r) -> dict:
    if not isinstance(r, dict) or not _valid_id(r.get("id")) or not _snowflake(r.get("owner_id")):
        raise Invalid
    if r.get("status") not in STATUSES or not _int(r.get("revision")) or r["revision"] < 1:
        raise Invalid
    return {"id": r["id"], "owner_id": r["owner_id"], "owner_name": _text(r.get("owner_name") or "", 100),
            "appearance": _text(r.get("appearance"), 100), "work": _text(r.get("work"), 100),
            "server_name": _text(r.get("server_name") or "", 100), "status": r["status"],
            "justification": _text(r.get("justification") or "", 2000), "image_url": _url(r.get("image_url") or ""),
            "date": _serial(r.get("date")), "revision": r["revision"]}

def load(sep: str, sheets: list[dict], values: dict[int, list[list]], language="pt-BR") -> Model:
    """Monta o modelo a partir do que o script devolveu: todas as guias e os valores A:K das guias de membro."""
    m = Model(sep, language=language, names=[s["title"] for s in sheets], next_sheet_id=max([1000] + [s["sheetId"] + 1 for s in sheets]))
    for s in sheets:
        if s["sheetId"] not in values:
            continue
        rows = values[s["sheetId"]]
        grid = []
        for i in range(s["rows"]):
            line = list(rows[i][:WIDTH]) if i < len(rows) else []
            grid.append(line + [""] * (WIDTH - len(line)))
        m.tabs.append(Tab(s["title"], s["sheetId"], grid, language))
    return m

def is_member_tab(column_k: list[list]) -> bool:
    """Guia de membro = tem o marcador BLOCO: na coluna K."""
    return any(str(line[0] if line else "").startswith("BLOCO:") for line in column_k)

def a1(title: str, cells: str) -> str:
    return "'" + title.replace("'", "''") + "'!" + cells


# ---------- pedidos de formatação ----------
def _empty(n: int) -> list[list]:
    return [[""] * WIDTH for _ in range(n)]

def _cell(v) -> dict:
    if v is None or v == "":
        return {}
    if isinstance(v, dict):
        return {"userEnteredValue": {"formulaValue": v["f"]}}
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return {"userEnteredValue": {"numberValue": v}}
    return {"userEnteredValue": {"stringValue": str(v)}}

def _range(sid: int, r1: int, r2: int, c1: int, c2: int) -> dict:
    return {"sheetId": sid, "startRowIndex": r1 - 1, "endRowIndex": r2, "startColumnIndex": c1 - 1, "endColumnIndex": c2}

def _format(req: list, sid: int, r1: int, r2: int, c1: int, c2: int, *, bg=None, ink=None, bold=False, size=10,
            h="LEFT", v="MIDDLE", wrap="WRAP", date=False, language="pt-BR") -> None:
    fmt = {"textFormat": {"fontFamily": "Arial", "fontSize": size, "bold": bold, "foregroundColor": ink or INK},
           "backgroundColor": bg or WHITE, "verticalAlignment": v, "horizontalAlignment": h, "wrapStrategy": wrap}
    if date:
        fmt["numberFormat"] = {"type": "DATE", "pattern": "yyyy-mm-dd" if language == "en" else "dd/mm/yyyy"}
    req.append({"repeatCell": {"range": _range(sid, r1, r2, c1, c2), "cell": {"userEnteredFormat": fmt}, "fields": "userEnteredFormat"}})

def _border(req: list, sid: int, r1: int, r2: int, c1: int, c2: int, inner: bool) -> None:
    """Contorno mais escuro em volta e linhas claras dentro (só com inner). Vem depois do _format, que apaga bordas."""
    frame, line = {"style": "SOLID", "color": FRAME}, {"style": "SOLID", "color": LINE}
    q = {"range": _range(sid, r1, r2, c1, c2), "top": frame, "bottom": frame, "left": frame, "right": frame}
    if inner:
        q["innerHorizontal"], q["innerVertical"] = line, line
    req.append({"updateBorders": q})

def _merge(req: list, sid: int, r1: int, r2: int, c1: int, c2: int) -> None:
    req.append({"mergeCells": {"range": _range(sid, r1, r2, c1, c2), "mergeType": "MERGE_ALL"}})

def _height(req: list, sid: int, r1: int, r2: int, px: int) -> None:
    req.append({"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "ROWS", "startIndex": r1 - 1, "endIndex": r2},
                                              "properties": {"pixelSize": px}, "fields": "pixelSize"}})

def _group(req: list, sid: int, r1: int, r2: int, depth: int, collapsed: bool) -> None:
    rng = {"sheetId": sid, "dimension": "ROWS", "startIndex": r1 - 1, "endIndex": r2}
    req.append({"addDimensionGroup": {"range": rng}})
    if collapsed:
        req.append({"updateDimensionGroup": {"dimensionGroup": {"range": rng, "depth": depth, "collapsed": True}, "fields": "collapsed"}})


# ---------- validação ----------
def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)

def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0

def _valid_id(v) -> bool:
    return isinstance(v, str) and bool(RECORD_ID.match(v))

def _snowflake(v) -> bool:
    return isinstance(v, str) and bool(SNOWFLAKE.match(v))

def _text(v, limit: int) -> str:
    if not isinstance(v, str) or len(v) > limit or BAD_TEXT.search(v):
        raise Invalid
    return v.strip()

def _url(v) -> str:
    url = _text(v, 1500)
    if url and not url.lower().startswith("https://"):
        raise Invalid
    return url

def _serial(iso) -> int | str:
    if iso in (None, ""):
        return ""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(iso))
    if not m:
        raise Invalid
    try:
        return (dt.date(int(m[1]), int(m[2]), int(m[3])) - dt.date(1970, 1, 1)).days + 25569
    except ValueError:
        raise Invalid from None
