"""Diagnóstico de configuração: só leituras em Discord e Apps Script."""
from __future__ import annotations
import asyncio
import importlib.metadata
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

async def check() -> int:
    try:
        import aiohttp
        from arquivista.config import Config
        from arquivista.bridge import Bridge
        from arquivista.domain import Actor, UserError
        config = Config.load()
    except (ImportError, ValueError, OSError) as exc:
        print('Configuração incompleta:', str(exc))
        print('Execute python -m pip install -r requirements.txt e python configurar.py.')
        return 1
    try:
        version = importlib.metadata.version('discord.py')
        print('Biblioteca discord.py instalada:', version)
    except importlib.metadata.PackageNotFoundError:
        print('Instale discord.py com python -m pip install -r requirements.txt.')
        return 1
    async with aiohttp.ClientSession(headers={'User-Agent':'ArquivistaDoCiclo/0.2 preflight'}) as session:
        try:
            async with session.get('https://discord.com/api/v10/users/@me',
                    headers={'Authorization':'Bot '+config.token}, timeout=aiohttp.ClientTimeout(total=25)) as response:
                if response.status != 200:
                    print('Discord não autorizou a leitura da conta. Confira o token e tente novamente.')
                    return 1
                me = await response.json()
            if not me.get('bot'):
                print('A credencial não pertence a um bot. Use somente o token do aplicativo Arquivista.')
                return 1
            print('Conta do bot:', me.get('username', 'não informado'), '· ID', me['id'])
            async with session.get(f'https://discord.com/api/v10/guilds/{config.guild_id}',
                    headers={'Authorization':'Bot '+config.token}, timeout=aiohttp.ClientTimeout(total=25)) as response:
                if response.status != 200:
                    print('O bot não conseguiu ler o servidor configurado. Confira o convite e DISCORD_GUILD_ID.')
                    return 1
                guild = await response.json()
            print('Servidor autorizado:', guild.get('name', 'não informado'))
            bridge = Bridge(session, config.bridge_url, config.bridge_secret, config.guild_id)
            status = await bridge.call('status', Actor(me['id'], 'Arquivista · diagnóstico', True))
            print('Ponte:', status['version'])
            print('Grupos preparados:', status['capacity'])
            print('Base histórica pronta:', 'sim' if status['ready'] else 'não')
            print('Manutenção pendente:', 'sim' if status['maintenance'] else 'não')
            if not status['ready'] or status['maintenance']:
                print('Aguarde a preparação/revisão da planilha antes de abrir os cadastros.')
                return 2
            print('Leituras autorizadas. Nenhuma mensagem foi enviada; nada foi cadastrado.')
            print('Próximo: python iniciar.py. Teste comandos, formulários e permissões com a staff.')
            return 0
        except UserError as exc:
            print('Ponte:', str(exc))
            return 1
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError) as exc:
            print('A verificação não terminou. Tipo do problema:', type(exc).__name__)
            print('Confira a rede, a implantação /exec e o diagnóstico do Apps Script. Nenhuma credencial foi impressa.')
            return 1

if __name__ == '__main__':
    try:
        raise SystemExit(asyncio.run(check()))
    except KeyboardInterrupt:
        raise SystemExit('Verificação interrompida.') from None
