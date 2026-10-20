from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def load_env(path: Path = ROOT / ".env") -> None:
    """Lê somente KEY=VALUE. Sem expansão de comandos, sem imprimir credenciais."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        text = raw.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        if key.strip().replace("_", "").isalnum():
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))

def snowflake(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    if not value.isdigit() or not 17 <= len(value) <= 20:
        raise ValueError(f"{name} inválido.")
    return int(value)

@dataclass(frozen=True)
class Config:
    token: str
    db_path: Path
    # Opcional: servidor de testes, onde os comandos aparecem na hora (o global leva até 1 h).
    dev_guild_id: int | None = None
    # Opcional: cargos de staff da v0.2, levados uma vez para a configuração desse servidor.
    legacy_staff_roles: frozenset[int] = frozenset()
    persona_name: str = "Amiya"
    poll_seconds: int = 90
    configure_avatar: bool = True
    timezone: str = "America/Sao_Paulo"
    @classmethod
    def load(cls) -> "Config":
        load_env()
        if not os.getenv("DISCORD_TOKEN", "").strip():
            raise ValueError("Preencha no .env: DISCORD_TOKEN")
        dev = snowflake("DISCORD_DEV_GUILD_ID") or snowflake("DISCORD_GUILD_ID")
        roles = frozenset(int(x.strip()) for x in os.getenv("STAFF_ROLE_IDS", "").split(",") if x.strip())
        return cls(os.environ["DISCORD_TOKEN"].strip(),
                   Path(os.getenv("DATABASE_PATH", str(ROOT / "dados" / "arquivista.sqlite3"))),
                   dev, roles, os.getenv("PERSONA_NAME", "Amiya")[:64],
                   max(60, int(os.getenv("POLL_SECONDS", "90"))),
                   os.getenv("CONFIGURAR_AVATAR", "true").lower() == "true",
                   os.getenv("TIMEZONE", "America/Sao_Paulo"))
