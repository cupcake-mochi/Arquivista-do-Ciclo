"""Configuração local interativa. Nunca imprime o token Discord."""
from __future__ import annotations
import getpass
import os
from pathlib import Path
import re

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
    print('O valor digitado do token fica oculto e não será impresso.')
    token = getpass.getpass('Token Discord [Enter mantém o existente ou deixa pendente]: ').strip()
    if token:
        values['DISCORD_TOKEN'] = token
    else:
        values.setdefault('DISCORD_TOKEN', '')
    # Cargos e canais agora ficam por servidor, no /configurar. Aqui só o servidor de testes.
    old = values.pop('DISCORD_GUILD_ID', '')
    values.setdefault('DISCORD_DEV_GUILD_ID', old)
    while True:
        dev = input('ID do servidor de testes (comandos aparecem na hora só nele) [Enter mantém; - deixa público]: ').strip()
        dev = '' if dev == '-' else dev or values.get('DISCORD_DEV_GUILD_ID', '')
        if not dev or re.fullmatch(r'[0-9]{17,20}', dev):
            values['DISCORD_DEV_GUILD_ID'] = dev
            break
        print('Informe o ID do servidor, não o do bot ou do seu perfil.')
    values.setdefault('PERSONA_NAME', 'Amiya')
    values.setdefault('CONFIGURAR_AVATAR', 'true')
    values.setdefault('POLL_SECONDS', '90')
    values.setdefault('TIMEZONE', 'America/Sao_Paulo')
    write_private(ENV, values)
    print('\nConfiguração salva em .env. Não envie esse arquivo ao GitHub.')
    if not values['DISCORD_TOKEN']:
        print('Falta o token. Execute este assistente de novo quando tiver.')
    else:
        print('Próximo: python verificar.py — faz somente leituras, sem cadastrar ou enviar mensagens.')
        print('Depois, em cada servidor, a gerência usa /configurar para cargos de staff e canais.')

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyboardInterrupt, EOFError) as exc:
        raise SystemExit('Configuração não concluída: ' + (str(exc) or 'interrompida')) from None
