"""Backup periódico de um servidor: o arquivo que o importar.py lê de volta e, se o servidor
tiver planilha, uma planilha .xlsx com uma guia por membro, gerada a partir do banco do bot.

O .xlsx é montado à mão (zip + XML) para não depender de biblioteca. É uma cópia de leitura
dos dados; a formatação da planilha conectada (blocos, visor, cores) não vai junto.
"""
from __future__ import annotations
from .sheet_language import label
import io
import json
import re
import zipfile
from datetime import date, datetime, timezone
from xml.sax.saxutils import escape

from .importer import FORMAT

INTERVALS = {6: "a cada 6 horas", 12: "a cada 12 horas", 24: "todo dia", 72: "a cada 3 dias", 168: "toda semana"}
FIELDS = ("id", "owner_id", "appearance", "work", "server_name", "status", "justification", "image_url", "date",
          "media_ref", "revision")
COLUMNS = (("Aparência", "appearance", 28), ("Nome no servidor", "server_name", 28), ("Obra de origem", "work", 24),
           ("Situação", "status", 15), ("Cadastro", "date", 12), ("Justificativa", "justification", 40),
           ("Link da imagem", "image_url", 30), ("ID do registro", "id", 42), ("ID Discord", "owner_id", 21))
BAD_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def export_json(guild_id: str, records: list[dict]) -> bytes:
    """Mesmo formato do exportarParaArquivista: restaura com `python importar.py arquivo.json --servidor ID`."""
    data = {"format": FORMAT, "version": 1, "guild_id": str(guild_id),
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "records": [{k: r.get(k) for k in FIELDS} for r in records]}
    return json.dumps(data, ensure_ascii=False, indent=1).encode()


def _sheet_name(name: str, taken: set[str]) -> str:
    # Excel: até 31 caracteres, sem : \ / ? * [ ], sem repetir (maiúsculas não contam).
    base = re.sub(r"[:\\/?*\[\]]", "", BAD_XML.sub("", name)).strip().strip("'")[:28] or "Membro"
    out, i = base, 2
    while out.lower() in taken:
        out, i = f"{base[:26]} ({i})", i + 1
    taken.add(out.lower())
    return out


def _cell(ref: str, value) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}"><v>{value}</v></c>'
    text = escape(BAD_XML.sub("", str(value or "")))
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>' if text else ""


def _sheet_xml(rows: list[list]) -> str:
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, (_, _, w) in enumerate(COLUMNS, 1))
    body = []
    for n, row in enumerate(rows, 1):
        cells = "".join(_cell(f"{chr(65 + j)}{n}", v) for j, v in enumerate(row))
        body.append(f'<row r="{n}">{cells}</row>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            f'<cols>{cols}</cols><sheetData>{"".join(body)}</sheetData></worksheet>')


def workbook(records: list[dict], names: dict[str, str], language="pt-BR") -> bytes:
    """Uma guia por membro (nome de usuário), na ordem dos cadastros. names: owner_id -> nome."""
    by_owner: dict[str, list[dict]] = {}
    for r in records:
        by_owner.setdefault(r["owner_id"], []).append(r)
    taken: set[str] = set()
    sheets = []
    for owner, items in by_owner.items():
        rows = [[label(c[0],language) for c in COLUMNS]]
        for r in items:
            line = []
            for _, key, _ in COLUMNS:
                v = r.get(key) or ""
                if key == "date" and v:
                    v = date.fromisoformat(v).strftime("%Y-%m-%d" if language=="en" else "%d/%m/%Y")
                if key == "status":v=label(v,language)
                line.append(v)
            rows.append(line)
        sheets.append((_sheet_name(names.get(owner) or f"Member {owner}" if language=="en" else names.get(owner) or f"Membro {owner}", taken), rows))
    if not sheets:
        sheets.append(("No records" if language=="en" else "Sem cadastros", [[label(c[0],language) for c in COLUMNS]]))
    ns = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                      for i in range(1, len(sheets) + 1)) + '</Types>',
        "_rels/.rels": f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {ns}>'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
            + "".join(f'<sheet name="{escape(name, {chr(34): "&quot;"})}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _) in enumerate(sheets, 1))
            + '</sheets></workbook>',
        "xl/_rels/workbook.xml.rels": f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships {ns}>'
            + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                      for i in range(1, len(sheets) + 1)) + '</Relationships>',
    }
    for i, (_, rows) in enumerate(sheets, 1):
        files[f"xl/worksheets/sheet{i}.xml"] = _sheet_xml(rows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path, text in files.items():
            z.writestr(path, text)
    return buf.getvalue()
