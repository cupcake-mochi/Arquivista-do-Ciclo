"""Regras de apresentação e validação. A autorização final também ocorre na ponte."""
from __future__ import annotations
import hashlib
import hmac
import ipaddress
import json
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlsplit

STATUSES = ("Em preparação", "Em uso", "Arquivado", "Liberado")
PUBLIC_FIELDS = frozenset(("id", "appearance", "work", "owner_id", "occupied"))
ALIASES = {
    "aparencias": "aparencias", "aparências": "aparencias", "lista": "aparencias",
    "galeria": "galeria", "consultar": "consultar", "buscar": "consultar",
    "minhas": "minhas", "registrar": "registrar", "editar": "editar",
    "situacao": "situacao", "situação": "situacao", "transferir": "transferir",
    "remover": "remover", "historico": "historico", "histórico": "historico",
    "registrarhistorico": "registrar_historico", "registrar_historico": "registrar_historico",
    "desativarhistorico": "desativar_historico", "desativar_historico": "desativar_historico",
    "registrarimagens": "registrar_imagens", "registrar_imagens": "registrar_imagens",
    "desativarimagens": "desativar_imagens", "desativar_imagens": "desativar_imagens",
    "ajuda": "ajuda", "help": "ajuda", "status": "status",
    "configurar": "configurar", "config": "configurar",
}
STAFF_ACTIONS = frozenset(("situacao", "transferir", "remover", "historico", "status",
    "registrar_historico", "desativar_historico", "registrar_imagens", "desativar_imagens"))

ERRORS = {
    "AUTH": "A conexão com o arquivo não foi autorizada. A staff precisa conferir a configuração.",
    "BUSY": "O arquivo está ocupado com outra operação. Aguarde um pouco e tente novamente.",
    "MAINTENANCE": "A planilha está em preparação ou revisão. Vou aguardar antes de alterar cadastros.",
    "DUPLICATE": "Essa aparência e obra já estão ocupadas. Consulte o arquivo antes de registrar.",
    "FORBIDDEN": "Você não tem autorização para essa alteração.",
    "NOT_FOUND": "Não encontrei mais esse cadastro. Faça uma nova consulta.",
    "STALE": "O cadastro mudou enquanto você preenchia. Abra a edição novamente para não sobrescrever outra alteração.",
    "CAPACITY": "Os espaços preparados para esse membro ou servidor estão ocupados. A staff precisa ampliar a estrutura.",
    "REUSED_REQUEST": "Essa confirmação já foi utilizada para outra operação. Abra o comando novamente.",
    "INVALID": "Um dos dados não passou na validação. Confira os campos e tente novamente.",
    "NOT_READY": "A integração do Arquivista ainda não foi ativada na planilha.",
    "INTERNAL": "Não consegui confirmar a operação. A staff pode verificar o diagnóstico sem repetir o cadastro às cegas.",
}

class UserError(Exception):
    """Mensagem deliberadamente segura para o usuário; não contém segredos ou tracebacks."""

class BridgeError(UserError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

@dataclass(frozen=True)
class Actor:
    id: str
    name: str
    staff: bool = False
    def wire(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name[:100], "staff": self.staff}

def normalized(text: Any) -> str:
    return " ".join(str(text or "").replace("\u00a0", " ").strip().lower().split())

def search_text(text: Any) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", normalized(text))
                   if not unicodedata.combining(c))

def exact_key(appearance: str, work: str) -> str:
    a, w = normalized(appearance), normalized(work)
    # Match Google Sheets LEN / JavaScript UTF-16 length, including emoji.
    length = len(a.encode("utf-16-le")) // 2
    return f"{length}:{a}:{w}" if a and w else ""

def parse_prefix(content: str) -> tuple[str, str, str | None] | None:
    m = re.match(r"^\s*ac:\s*([^\s]+)(?:\s+(.*))?$", content, re.I | re.S)
    if not m:
        return None
    command = ALIASES.get(m[1].lower(), "unknown")
    args = (m[2] or "").strip()
    mention = re.search(r"<@!?(\d{17,20})>", args)
    member = mention[1] if mention else None
    if mention:
        args = (args[:mention.start()] + args[mention.end():]).strip()
    return command, args.strip('"'), member

def public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {k: record[k] for k in PUBLIC_FIELDS if k in record}

def ranked(records: list[dict], query: str, limit: int | None = None) -> list[dict]:
    q = search_text(query)
    if not q:
        result = sorted(records, key=lambda r: (search_text(r.get("appearance")), search_text(r.get("work"))))
    else:
        scores = []
        for r in records:
            names = [search_text(r.get("appearance")), search_text(r.get("id"))]
            full = search_text(f"{r.get('appearance','')} {r.get('work','')}")
            if q in names:
                score = 3.0
            elif any(q in n for n in names + [full]):
                score = 2.0
            else:
                score = max(SequenceMatcher(None, q, n).ratio() for n in names + [full])
            if score >= .54:
                scores.append((score, search_text(r.get("appearance")), r))
        result = [r for _, _, r in sorted(scores, key=lambda t: (-t[0], t[1]))]
    return result if limit is None else result[:limit]

def safe_image_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if len(value) > 1500 or any(ord(c) < 33 for c in value):
        raise UserError("O endereço da imagem contém caracteres inválidos ou é muito longo.")
    try:
        url = urlsplit(value)
        host = (url.hostname or "").lower().rstrip(".")
        if url.scheme != "https" or not host or url.username or url.password or url.port not in (None, 443):
            raise ValueError
        if host == "localhost" or host.endswith((".local", ".internal", ".localhost")) or "." not in host:
            raise ValueError
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            if ":" in host or re.fullmatch(r"[\d.]+", host):
                raise UserError("Use um endereço HTTPS público da imagem.")
        else:
            if not ip.is_global:
                raise ValueError
        if host in ("discord.com", "discordapp.com") and "/api/webhooks/" in url.path:
            raise ValueError
    except (ValueError, TypeError):
        raise UserError("Use um endereço HTTPS público e direto da imagem.") from None
    return value

def signed_envelope(secret: str, action: str, payload: dict, guild: str,
                    actor: Actor, request_id: str | None = None, now: int | None = None) -> dict:
    body = {"v": 1, "ts": int(time.time()) if now is None else now, "nonce": uuid.uuid4().hex,
            "request_id": request_id or str(uuid.uuid4()), "action": action,
            "guild_id": guild, "actor": actor.wire(), "data": payload}
    text = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    return {"body": text, "sig": hmac.new(secret.encode(), text.encode(), hashlib.sha256).hexdigest()}

def valid_attachment(data: bytes) -> str:
    if not data or len(data) > 8 * 1024 * 1024:
        raise UserError("Envie uma imagem de até 8 MB.")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    raise UserError("Formato não aceito. Use PNG, JPEG, GIF ou WebP.")

def can_manage(actor: Actor, owner_id: str, action: str) -> bool:
    if action in STAFF_ACTIONS:
        return actor.staff
    return actor.staff or actor.id == owner_id
