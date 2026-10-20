"""Monta dados/arquivista.zip só com o que o bot precisa na Discloud. Sem .env e sem banco:
as variáveis vão pelo painel e o banco que já está na hospedagem não é sobrescrito."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
SAIDA = ROOT / "dados" / "arquivista.zip"

def arquivos():
    lista = [ROOT / n for n in ("discloud.config", "iniciar.py", "requirements.txt", "assets/amiya.png")]
    lista += sorted(p for p in (ROOT / "src" / "arquivista").glob("*.py"))
    return lista

if __name__ == "__main__":
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SAIDA, "w", zipfile.ZIP_DEFLATED) as z:
        for p in arquivos():
            z.write(p, p.relative_to(ROOT).as_posix())
    print(f"{SAIDA} ({SAIDA.stat().st_size // 1024} KB, {len(arquivos())} arquivos, sem .env e sem banco)")
