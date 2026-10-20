"""Importa a exportação da Planilha Aparências para o banco de um servidor.

    python importar.py exportacao.json --servidor ID            # só confere, não grava
    python importar.py exportacao.json --servidor ID --aplicar  # grava

Rode com o bot desligado. O arquivo tem dados internos (situação, justificativa):
não publique nem envie para o GitHub.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def main() -> int:
    from arquivista.config import ROOT, load_env
    from arquivista.importer import apply, check, summary
    from arquivista.store import Store
    import os
    parser = argparse.ArgumentParser(description="Importar a Planilha Aparências para o banco do Arquivista.")
    parser.add_argument("arquivo", type=Path)
    parser.add_argument("--servidor", required=True, help="ID do servidor Discord dono desses cadastros")
    parser.add_argument("--aplicar", action="store_true", help="grava no banco (sem isso, só confere)")
    parser.add_argument("--banco", type=Path, help="caminho do banco (padrão: DATABASE_PATH ou dados/arquivista.sqlite3)")
    args = parser.parse_args()
    if not args.servidor.isdigit() or not 17 <= len(args.servidor) <= 20:
        print("ID do servidor inválido."); return 1
    try:
        data = json.loads(args.arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print("Não consegui ler o arquivo:", type(exc).__name__); return 1
    records, errors, warnings = check(data)
    s = summary(records)
    print(f"Cadastros no arquivo: {s['records']} · membros: {s['members']} · sem data: {s['without_date']} · com imagem: {s['with_image']}")
    print("Por situação: " + ", ".join(f"{k} {v}" for k, v in s["status"].items()))
    for w in warnings[:30]:
        print("Aviso:", w)
    if len(warnings) > 30:
        print(f"... outros avisos: {len(warnings)-30}.")
    if errors:
        for e in errors[:50]:
            print("Erro:", e)
        if len(errors) > 50:
            print(f"... outros erros: {len(errors)-50}.")
        print("Nada foi gravado. Corrija na planilha, exporte de novo e rode outra vez.")
        return 2
    if not args.aplicar:
        print("Conferência sem erros. Nada foi gravado; use --aplicar para importar.")
        return 0
    load_env()
    path = args.banco or Path(os.getenv("DATABASE_PATH", str(ROOT / "dados" / "arquivista.sqlite3")))
    store = Store(path)
    try:
        n = apply(store, args.servidor, records)
        # Conferência depois de gravar: contagem e uma amostra campo a campo.
        count = store.db.execute("SELECT COUNT(*) FROM appearances WHERE guild_id=?", (args.servidor,)).fetchone()[0]
        sample = records[:: max(1, len(records) // 20)]
        bad = [r["id"] for r in sample if dict(store.db.execute(
            "SELECT owner_id,appearance,work,status,date FROM appearances WHERE id=?", (r["id"],)).fetchone() or {})
            != {k: r[k] for k in ("owner_id", "appearance", "work", "status", "date")}]
    except ValueError as exc:
        print(str(exc)); return 1
    finally:
        store.close()
    print(f"Cadastros importados: {n}. Total neste servidor: {count}. Amostra conferida: {len(sample) - len(bad)}/{len(sample)}.")
    if bad or count != n:
        print("A importação terminou com diferenças. Confira o arquivo e o banco antes de iniciar o bot."); return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
