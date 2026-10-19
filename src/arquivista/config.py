from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

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

@dataclass(frozen=True)
class Config:
    token: str
    guild_id: int
    bridge_url: str
    bridge_secret: str
    staff_roles: frozenset[int]
    db_path: Path
    persona_name: str = "Amiya"
    poll_seconds: int = 90
    configure_avatar: bool = True
    @classmethod
    def load(cls) -> "Config":
        load_env()
        missing = [k for k in ("DISCORD_TOKEN", "DISCORD_GUILD_ID", "AC_BRIDGE_URL", "AC_BRIDGE_SECRET") if not os.getenv(k)]
        if missing:
            raise ValueError("Preencha no .env: " + ", ".join(missing))
        url = os.environ["AC_BRIDGE_URL"].strip()
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "script.google.com" or not parsed.path.endswith("/exec") or parsed.query or parsed.fragment:
            raise ValueError("AC_BRIDGE_URL deve ser a URL /exec da implantação no Apps Script, sem parâmetros.")
        secret = os.environ["AC_BRIDGE_SECRET"]
        if len(secret) < 32:
            raise ValueError("AC_BRIDGE_SECRET deve ter pelo menos 32 caracteres aleatórios.")
        guild = os.environ["DISCORD_GUILD_ID"].strip()
        if not guild.isdigit() or not 17 <= len(guild) <= 20:
            raise ValueError("DISCORD_GUILD_ID inválido.")
        roles = frozenset(int(x.strip()) for x in os.getenv("STAFF_ROLE_IDS", "").split(",") if x.strip())
        return cls(os.environ["DISCORD_TOKEN"].strip(), int(guild), url, secret, roles,
                   Path(os.getenv("DATABASE_PATH", str(ROOT / "dados" / "arquivista.sqlite3"))),
                   os.getenv("PERSONA_NAME", "Amiya")[:64], max(60, int(os.getenv("POLL_SECONDS", "90"))),
                   os.getenv("CONFIGURAR_AVATAR", "true").lower() == "true")
