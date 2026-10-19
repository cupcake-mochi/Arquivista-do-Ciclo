"""Configuração local interativa. Nunca imprime o token Discord."""
from __future__ import annotations
import getpass
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
ENV = ROOT / '.env'


def read_existing(path: Path) -> dict[str, str]:
    values = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            if re.fullmatch(r'[A-Z_][A-Z0-9_]*', k.strip()):
                values[k.strip()] = v.strip().strip('"\'')
    return values


def write_private(path: Path, values: dict[str, str]) -> None:
    for k, v in values.items():
        if '\n' in v or '\r' in v:
            raise ValueError('Valores de configuração devem ocupar uma única linha.')
    text = '# SEGREDOS LOCAIS — não publicar no GitHub nem compartilhar.\n'
    text += '\n'.join(f'{k}={v}' for k, v in values.items()) + '\n'
    tmp = path.with_name(path.name + '.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, path)
        if os.name != 'nt':
            path.chmod(0o600)
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> None:
    values = read_existing(ENV)
    print('Arquivista do Ciclo — configuração local')
    print('Use um token novo. O valor digitado fica oculto e não será impresso.')
    token = getpass.getpass('Token Discord [Enter mantém o existente ou deixa pendente]: ').strip()
    if token:
        values['DISCORD_TOKEN'] = token
    else:
        values.setdefault('DISCORD_TOKEN', '')
    while True:
        guild = input('ID do servidor Discord [Enter mantém o existente]: ').strip() or values.get('DISCORD_GUILD_ID', '')
        if re.fullmatch(r'[0-9]{17,20}', guild):
            values['DISCORD_GUILD_ID'] = guild
            break
        print('Informe o ID do servidor, não o do bot ou do seu perfil.')
    raw = input('IDs dos cargos de staff separados por vírgula [Enter mantém; - limpa]: ').strip()
    roles = '' if raw == '-' else raw or values.get('STAFF_ROLE_IDS', '')
    if any(not re.fullmatch(r'[0-9]{17,20}', x.strip()) for x in roles.split(',') if x.strip()):
        raise ValueError('Cargo inválido. Copie o ID numérico; não use o nome do cargo.')
    values['STAFF_ROLE_IDS'] = ','.join(x.strip() for x in roles.split(',') if x.strip())
    if len(values.get('AC_BRIDGE_SECRET', '')) < 32:
        values['AC_BRIDGE_SECRET'] = secrets.token_urlsafe(48)
    url = input('URL /exec do Web App [Enter mantém ou configura depois]: ').strip() or values.get('AC_BRIDGE_URL', '')
    if url:
        p = urlsplit(url)
        if p.scheme != 'https' or p.hostname != 'script.google.com' or not p.path.endswith('/exec') or p.query or p.fragment:
            raise ValueError('A URL precisa ser https://script.google.com/.../exec, sem parâmetros.')
    values['AC_BRIDGE_URL'] = url
    values.setdefault('PERSONA_NAME', 'Amiya')
    values.setdefault('CONFIGURAR_AVATAR', 'true')
    values.setdefault('POLL_SECONDS', '90')
    write_private(ENV, values)
    print('\nConfiguração salva em .env. Não envie esse arquivo ao GitHub.')
    print('No Apps Script, Propriedades do script, configure estas duas propriedades:')
    print('AC_GUILD_ID =', values['DISCORD_GUILD_ID'])
    print('AC_SECRET =', values['AC_BRIDGE_SECRET'])
    print('AC_SECRET também é segredo. Copie para sua própria conta e não publique prints dele.')
    if not values['DISCORD_TOKEN'] or not url:
        print('Há dados pendentes. Depois de implantar o Web App, execute este assistente novamente; a chave da ponte será preservada.')
    else:
        print('Próximo: python verificar.py — faz somente leituras, sem cadastrar ou enviar mensagens.')

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyboardInterrupt, EOFError) as exc:
        raise SystemExit('Configuração não concluída: ' + (str(exc) or 'interrompida')) from None
