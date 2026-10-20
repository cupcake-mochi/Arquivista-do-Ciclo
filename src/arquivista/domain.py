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
from collections import Counter
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit

STATUSES = ("Em preparação", "Em uso", "Arquivado", "Liberado")
PUBLIC_FIELDS = frozenset(("id", "appearance", "work", "owner_id", "occupied"))
# Nome completo e abreviações de cada comando de chat (AC:...). Sem letra solta, que dispara sem querer.
SHORT = {
    "aparencias": ("aparencias", "aparências", "lista", "ap"),
    "minhas": ("minhas", "min"),
    "galeria": ("galeria", "gal"),
    "consultar": ("consultar", "buscar", "busca", "con"),
    "registrar": ("registrar", "reg"),
    "editar": ("editar", "ed"),
    "situacao": ("situacao", "situação", "sit"),
    "transferir": ("transferir", "transf", "tr"),
    "obra": ("obra", "obras", "ob"),
    "apelido": ("apelido", "apelidos", "apl"),
    "remover": ("remover", "rem", "rm"),
    "limpar": ("limpar", "apagar"),
    "historico": ("historico", "histórico", "hist"),
    "ajuda": ("ajuda", "help", "aj"),
    "diagnostico": ("diagnostico", "diagnóstico", "diag", "status", "st"),
    "configurar": ("configurar", "config", "cfg", "registrarhistorico", "desativarhistorico", "registrarimagens", "desativarimagens"),
}
ALIASES = {name: action for action, names in SHORT.items() for name in names}
STAFF_ACTIONS = frozenset(("situacao", "transferir", "remover", "limpar", "apelido", "historico", "diagnostico"))

ERRORS = {
    "AUTH": "A conexão com o arquivo não foi autorizada. A staff precisa conferir a configuração.",
    "GUILD": "A planilha foi instalada para outro servidor. No menu Arquivista > Instalar ou reinstalar, informe o ID deste servidor.",
    "CLOCK": "O relógio do bot e o do Google não batem. Confira a hora da hospedagem.",
    "LOGIN": "O Google pediu login antes de chegar no script. Na implantação do App da Web, deixe \"Quem pode acessar\" em \"Qualquer pessoa\".",
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
    "OLD_SCRIPT": "O script da planilha é de uma versão antiga. Cole o Planilha.gs novo e faça Implantar > Gerenciar implantações > Nova versão.",
    "OLD_BOT": "O script da planilha é mais novo que o bot. Atualize o bot.",
    "CHANGED": "A planilha mudou enquanto eu gravava. Vou ler de novo e tentar outra vez.",
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

# ---------------- obras com grafias diferentes
# Cada pessoa escreve a obra de um jeito ("Arknights", "Arknights Endfield", "Endfield", "arknighs").
# Duas grafias ficam juntas quando as palavras de uma estão todas na outra (com erro de digitação
# tolerado) ou quando o nome inteiro é quase igual. O agrupamento é transitivo, como uma franquia.
WORD_STOP = frozenset(("the", "of", "a", "an", "and", "to", "in", "no", "wo", "ga", "de", "do", "da", "dos", "das", "e", "o", "os", "as"))

# Palavra comum em título não junta obras sozinha ("Love Live" e "Live A Live" ficam separadas).
WORD_COMMON = frozenset(("live", "love", "online", "story", "stories", "world", "fantasy", "saga", "legend", "legends",
    "chronicle", "chronicles", "tale", "tales", "project", "game", "games", "academy", "school", "war", "wars", "hero",
    "heroes", "quest", "impact", "collection", "new", "last", "final", "dark", "black", "blue", "red", "white", "girl",
    "girls", "boy", "boys", "life", "star", "stars", "sword", "princess", "king", "queen", "lord", "art", "night",
    "day", "days", "high", "super", "big", "little", "my", "your", "one", "two", "zero", "world", "z", "x", "ii", "iii",
    "vida", "amor", "mundo", "guerra", "jogo", "escola", "anime", "manga", "novel", "movie", "filme", "serie", "series"))

def work_words(name: Any) -> tuple[str, ...]:
    words = list(dict.fromkeys(re.findall(r"[a-z0-9]+", search_text(name))))
    return tuple(w for w in words if w not in WORD_STOP) or tuple(words)

@lru_cache(maxsize=4096)
def _letters(a: str) -> Counter:
    return Counter(a)

def _close(a: str, b: str, limit: float) -> bool:
    # Corta antes da conta cara: a semelhança nunca passa de 2*(letras em comum)/(soma dos tamanhos).
    total = len(a) + len(b)
    if 2 * min(len(a), len(b)) < limit * total or 2 * sum((_letters(a) & _letters(b)).values()) < limit * total:
        return False
    return SequenceMatcher(None, a, b, autojunk=False).ratio() >= limit

def _same_word(a: str, b: str) -> bool:
    if a == b:
        return True
    # Erro de digitação só em palavra comprida; número e palavra curta precisam bater.
    return min(len(a), len(b)) >= 5 and not (a.isdigit() or b.isdigit()) and _close(a, b, .85)

def _related(wa: tuple[str, ...], wb: tuple[str, ...]) -> bool:
    if not wa or not wb:
        return False
    ja, jb = "".join(wa), "".join(wb)
    if ja == jb or (min(len(ja), len(jb)) >= 6 and (ja in jb or jb in ja or _close(ja, jb, .9))):
        return True  # mesmo nome com espaço ou pontuação diferente; "Umamusume" e "Uma Musume Pretty Derby"
    small, big = sorted((wa, wb), key=len)
    if len(small) == 1 and len(big) >= 3 and small[0].isalpha() and small[0] == "".join(w[0] for w in big):
        return True  # sigla: "HSR" e "Honkai Star Rail"
    return (sum(map(len, small)) >= 4 and any(x not in WORD_COMMON and not x.isdigit() for x in small)
            and all(any(_same_word(x, y) for y in big) for x in small))

def related_works(a: Any, b: Any) -> bool:
    return _related(work_words(a), work_words(b))

def work_key(name: Any) -> str:
    return " ".join(work_words(name)) or normalized(name)

def work_groups(works: list[str], aliases: dict[str, str] | None = None) -> list[dict]:
    """Junta as grafias parecidas. Devolve [{label, names, count, keys}] do grupo com mais cadastros para o menor;
    label é a grafia mais usada do grupo. aliases: apelido -> nome da obra, cadastrados pela staff do servidor;
    juntam o que a semelhança sozinha não junta ("JJK" e "Jujutsu Kaisen") e dão o nome do grupo.
    Não altere o resultado: ele fica em cache."""
    return _work_groups(tuple(sorted(works)), tuple(sorted((aliases or {}).items())))

@lru_cache(maxsize=64)
def _work_groups(works: tuple[str, ...], aliases: tuple[tuple[str, str], ...] = ()) -> list[dict]:
    count: dict[str, int] = {}
    spelling: dict[str, dict[str, int]] = {}
    for w in works:
        key = work_key(w)
        if not key:
            continue
        count[key] = count.get(key, 0) + 1
        spelling.setdefault(key, {})
        spelling[key][w.strip()] = spelling[key].get(w.strip(), 0) + 1
    links, targets = [], {}
    for alias, target in aliases:
        ak, tk = work_key(alias), work_key(target)
        if not ak or not tk:
            continue
        for k, name in ((ak, alias), (tk, target)):
            count.setdefault(k, 0)
            spelling.setdefault(k, {}).setdefault(name.strip(), 0)
        links.append((ak, tk))
        targets[tk] = target.strip()
    keys = sorted(count)
    parent = {k: k for k in keys}
    def root(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k
    words = {k: tuple(k.split()) for k in keys}
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if root(a) != root(b) and _related(words[a], words[b]):
                parent[root(b)] = root(a)
    for ak, tk in links:
        if root(ak) != root(tk):
            parent[root(ak)] = root(tk)
    groups: dict[str, list[str]] = {}
    for k in keys:
        groups.setdefault(root(k), []).append(k)
    out = []
    for members in groups.values():
        total = sum(count[k] for k in members)
        if not total:
            continue  # apelido de obra que ninguém usa ainda
        # Nome do grupo: o nome que a staff deu num apelido; sem isso, a grafia mais usada; no empate,
        # a que mais aparece dentro das outras ("Arknights" está em "Arknights Endfield"), depois a que
        # começa como as outras (franquia antes do subtítulo), depois a de palavras mais repetidas
        # ("Arknights" ganha de "arknighs"), sem preferir sigla. Dentro da grafia, a forma com maiúscula mais comum.
        words: dict[str, int] = {}
        for k in members:
            for w in k.split():
                words[w] = words.get(w, 0) + count[k]
        base = lambda k: sum(count[o] for o in members if all(any(_same_word(x, y) for y in o.split()) for x in k.split()))
        lead = lambda k: sum(count[o] for o in members if _same_word(k.split()[0], o.split()[0]))
        best = lambda k: (k not in targets, -count[k], -base(k), -lead(k),
                          -sum(words[w] for w in k.split()) / len(k.split()), len(k) <= 4, len(k), k)
        ordered = sorted(members, key=best)
        shown = lambda k: targets.get(k) or sorted(spelling[k], key=lambda n: (-spelling[k][n], n == n.lower(), n))[0]
        names = [shown(ordered[0])] + [shown(k) for k in ordered[1:] if count[k]]
        out.append({"label": names[0], "names": names, "count": total, "keys": members})
    return sorted(out, key=lambda g: (-g["count"], search_text(g["label"])))

def find_work(groups: list[dict], query: str) -> list[dict]:
    """Grupos que a busca alcança: a busca parecida com alguma grafia, ou contida nela."""
    q = " ".join(work_words(query))
    if not q:
        return []
    return [g for g in groups if any(related_works(q, k) or (len(q) >= 3 and q in k) for k in g["keys"])]

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
