"""Planilha → bot: o que a staff mudou à mão na planilha conectada volta para o banco.

O bot lê a planilha de tempos em tempos (a mesma leitura que faz antes de gravar) e compara cada
linha com o banco. Linha com ID e mesma revisão do banco, mas com outro valor, é uma edição feita
na planilha; linha digitada numa posição vazia, sem ID, é um cadastro novo do dono daquela guia.
Cadastro com mudança esperando ir para a planilha fica de fora: a versão do bot vai por cima.
Edição que o bot recusa (aparência repetida, situação que não existe...) é desfeita na planilha.
"""
from __future__ import annotations
import datetime as dt
import re

from . import layout

FIELDS = ("appearance", "server_name", "work", "status", "justification", "image_url", "date")
EPOCH = dt.date(1899, 12, 30)  # dia 0 das datas do Sheets


def _text(v) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return "" if v is None else str(v).strip()


def _date(v):
    """Data da planilha (número de série ou texto dd/mm/aaaa) em ISO; None se vazia; False se ilegível."""
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        try:
            return (EPOCH + dt.timedelta(days=int(v))).isoformat()
        except OverflowError:
            return False
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(v).strip())
    try:
        return dt.date(int(m[3]), int(m[2]), int(m[1])).isoformat() if m else False
    except ValueError:
        return False


def _revision(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def changes(model: layout.Model, records: dict[str, dict], queued: set[str]) -> tuple[list[dict], list[str]]:
    """(mudanças para Archive.from_sheet, IDs que a planilha perdeu e precisam ser regravados).

    records: cadastros do servidor no banco, por ID. queued: IDs com mudança na fila para a planilha."""
    out, seen = [], set()
    for b in model.blocks():
        for n in range(1, b.slots + 1):
            row = b.row(n)
            line = b.tab.grid[row - 1]
            values = {"appearance": _text(line[layout.APPEARANCE - 1]), "server_name": _text(line[layout.SERVER_NAME - 1]),
                      "work": _text(line[layout.WORK - 1]), "status": _text(line[layout.STATUS - 1]),
                      "justification": _text(b.tab.grid[row + 1][layout.APPEARANCE - 1]),
                      "image_url": _text(line[layout.URL - 1]), "date": _date(line[layout.DATE - 1])}
            rid = _text(line[layout.ID - 1])
            if rid:
                seen.add(rid)
                r = records.get(rid)
                # Fora do banco, na fila, em outra revisão ou movido para a guia de outra pessoa: não é edição.
                if not r or rid in queued or r["owner_id"] != b.owner or _revision(line[layout.MARK - 1]) != r["revision"]:
                    continue
                current = {k: r.get(k) or ("" if k != "date" else None) for k in FIELDS}
                if values == current:
                    continue
                if values["date"] is False:
                    values["date"] = "invalid"
                out.append({"id": rid, "revision": r["revision"], "tab": b.tab.name, **values})
            elif values["appearance"] or values["work"]:
                if values["date"] is False:
                    values["date"] = "invalid"
                out.append({"id": "", "owner_id": b.owner, "slot": n, "tab": b.tab.name, **values})
    lost = [rid for rid in records if rid not in seen and rid not in queued]
    return out, lost
