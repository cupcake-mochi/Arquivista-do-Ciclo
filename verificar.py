"""Diagnóstico de configuração: só leituras no Discord e no banco local."""
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
        from arquivista.store import Store
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
    try:
        store = Store(config.db_path)
        count = store.db.execute('SELECT COUNT(*) FROM appearances').fetchone()[0]
        servers = store.db.execute('SELECT COUNT(DISTINCT guild_id) FROM appearances').fetchone()[0]
        store.close()
        print(f'Banco aberto: {count} cadastro(s) em {servers} servidor(es).')
    except Exception as exc:
        print('Não consegui abrir o banco em', config.db_path, '· tipo do problema:', type(exc).__name__)
        return 1
    headers = {'Authorization': 'Bot ' + config.token}
    async with aiohttp.ClientSession(headers={'User-Agent':'ArquivistaDoCiclo/0.3 preflight'}) as session:
        try:
            async with session.get('https://discord.com/api/v10/users/@me', headers=headers,
                    timeout=aiohttp.ClientTimeout(total=25)) as response:
                if response.status != 200:
                    print('Discord não autorizou a leitura da conta. Confira o token e tente novamente.')
                    return 1
                me = await response.json()
            if not me.get('bot'):
                print('A credencial não pertence a um bot. Use somente o token do aplicativo Arquivista.')
                return 1
            print('Conta do bot:', me.get('username', 'não informado'), '· ID', me['id'])
            async with session.get('https://discord.com/api/v10/users/@me/guilds', headers=headers,
                    timeout=aiohttp.ClientTimeout(total=25)) as response:
                guilds = await response.json() if response.status == 200 else []
            print('Servidores com o bot:', len(guilds))
            for g in guilds[:10]:
                print(' ·', g.get('name', 'sem nome'), g.get('id'))
            if config.dev_guild_id:
                if not any(str(g.get('id')) == str(config.dev_guild_id) for g in guilds):
                    print('O bot não está no servidor de testes configurado. Confira o convite e DISCORD_DEV_GUILD_ID.')
                    return 1
                print('Modo de testes: os comandos / aparecem só no servidor', config.dev_guild_id)
            else:
                print('Modo público: comandos / em todos os servidores (o Discord pode levar até 1 h na primeira vez).')
            print('Leituras autorizadas. Nenhuma mensagem foi enviada; nada foi cadastrado.')
            print('Próximo: python iniciar.py. Em cada servidor, a gerência usa /configurar.')
            return 0
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, KeyError) as exc:
            print('A verificação não terminou. Tipo do problema:', type(exc).__name__)
            print('Confira a rede e o token. Nenhuma credencial foi impressa.')
            return 1

if __name__ == '__main__':
    try:
        raise SystemExit(asyncio.run(check()))
    except KeyboardInterrupt:
        raise SystemExit('Verificação interrompida.') from None
