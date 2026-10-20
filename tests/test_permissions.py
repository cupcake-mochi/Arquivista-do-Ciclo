"""Permissões de canal e de painéis com os objetos reais do discord.py, sem login."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import discord
from arquivista.bot import Arquivista
from arquivista.config import Config
from arquivista.views import GuardedView, backup_problem


class BackupAccessTests(unittest.TestCase):
    def setUp(self):
        self.everyone = MagicMock(spec=discord.Role)
        self.everyone.id = 1
        self.everyone.managed = False
        self.guild = SimpleNamespace(default_role=self.everyone, roles=[self.everyone],
                                     owner_id=10, me=SimpleNamespace(id=20))
        self.channel = MagicMock(spec=discord.TextChannel)
        self.channel.guild = self.guild
        self.channel.mention = '#backup'
        self.channel.overwrites = {}
        self.channel.permissions_for.side_effect = lambda target: discord.Permissions.all() if target is self.guild.me else discord.Permissions.none()

    def member(self, uid=30, **permissions):
        member = MagicMock(spec=discord.Member)
        member.id, member.roles = uid, []
        member.guild_permissions = discord.Permissions(**permissions)
        self.channel.overwrites[member] = discord.PermissionOverwrite(view_channel=True)
        return member

    def test_private_channel_allows_bot_and_owner(self):
        self.member(10)
        self.member(20)
        self.assertIsNone(backup_problem(self.channel))

    def test_public_channel_refused(self):
        self.channel.permissions_for.return_value = discord.Permissions.all()
        self.channel.permissions_for.side_effect = None
        self.assertIn('todo mundo', backup_problem(self.channel))

    def test_nonstaff_role_refused(self):
        role = MagicMock(spec=discord.Role)
        role.id, role.managed, role.mention = 40, False, '@Membro'
        role.permissions = discord.Permissions.none()
        self.guild.roles.append(role)
        self.channel.permissions_for.side_effect = lambda target: discord.Permissions.all() if target is self.guild.me or target is role else discord.Permissions.none()
        self.assertIn('@Membro', backup_problem(self.channel))
        self.assertIsNone(backup_problem(self.channel, [40]))

    def test_individual_member_allow_refused(self):
        self.member()
        self.assertIn('acesso individual', backup_problem(self.channel))

    def test_uncached_individual_allow_refused(self):
        self.channel.overwrites[discord.Object(id=30, type=discord.User)] = discord.PermissionOverwrite(view_channel=True)
        self.assertIn('acesso individual', backup_problem(self.channel))

    def test_individual_deny_does_not_grant_access(self):
        member = self.member()
        self.channel.overwrites[member] = discord.PermissionOverwrite(view_channel=False)
        self.assertIsNone(backup_problem(self.channel))

    def test_managers_and_configured_staff_allowed(self):
        for permission in ('administrator', 'manage_guild'):
            with self.subTest(permission=permission):
                self.channel.overwrites = {}
                self.member(**{permission: True})
                self.assertIsNone(backup_problem(self.channel))
        member = self.member(31)
        member.roles = [SimpleNamespace(id=40)]
        self.assertIsNone(backup_problem(self.channel, ['40']))
        self.assertIsNotNone(backup_problem(self.channel, []))


class PanelAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_mentions_require_direct_account_or_exclusive_bot_role(self):
        bot_id=123456789012345678
        own_role=SimpleNamespace(id=123456789012345679,tags=SimpleNamespace(bot_id=bot_id))
        common_role=SimpleNamespace(id=123456789012345680,tags=None)
        other_role=SimpleNamespace(id=123456789012345681,tags=SimpleNamespace(bot_id=999))
        cases=[
            ('@everyone',True,[SimpleNamespace(id=bot_id)],[],None,False),
            ('@here',True,[SimpleNamespace(id=bot_id)],[],123,False),
            (f'<@&{common_role.id}>',False,[],[common_role],None,False),
            (f'<@&{other_role.id}>',False,[],[other_role],None,False),
            ('<@999>',False,[SimpleNamespace(id=999)],[],None,False),
            (f'<@{bot_id}>',False,[SimpleNamespace(id=bot_id)],[],None,True),
            (f'<@!{bot_id}>',False,[SimpleNamespace(id=bot_id)],[],None,True),
            (f'<@&{own_role.id}>',False,[],[own_role],None,True),
            (f'@everyone <@{bot_id}>',True,[SimpleNamespace(id=bot_id)],[],None,True),
            ('uma dúvida',False,[],[],123,True),
            ('uma dúvida',False,[],[],456,False),
        ]
        for content,everyone,mentions,roles,reply,expected in cases:
            with self.subTest(content=content,reply=reply):
                bot=SimpleNamespace(user=SimpleNamespace(id=bot_id),last_mention={},
                    store=SimpleNamespace(is_ours=lambda mid:mid==123),carteiro=SimpleNamespace(send=AsyncMock()),run_action=AsyncMock())
                message=SimpleNamespace(content=content,mention_everyone=everyone,mentions=mentions,role_mentions=roles,
                    reference=SimpleNamespace(message_id=reply) if reply else None,author=SimpleNamespace(id=30,bot=False),
                    webhook_id=None,guild=SimpleNamespace(id=1),channel=SimpleNamespace(id=2),attachments=[])
                await Arquivista.on_message(bot,message)
                self.assertEqual(bot.carteiro.send.await_count,int(expected))
        message.content='AC:ajuda @everyone'
        message.mention_everyone=True
        await Arquivista.on_message(bot,message)
        self.assertEqual(bot.run_action.await_count,1)

    async def test_owner_can_confirm_removal_and_cancel_without_writing(self):
        from arquivista.archive import Archive
        from arquivista.domain import Actor
        from arquivista.views import Confirm, Gate, Picker
        with tempfile.TemporaryDirectory() as directory:
            bot = Arquivista(Config('FAKE', Path(directory) / 'test.sqlite'))
            try:
                actor=Actor('30','Dono')
                archive=Archive(bot.store,'123')
                r=(await archive.call('create',actor,{'fields':{'appearance':'Teste próprio','work':'Teste'}}))['record']
                payload={'id':r['id'],'revision':r['revision']}
                bot.actor=AsyncMock(return_value=actor)
                bot.notify_soon=MagicMock()
                i=SimpleNamespace(user=SimpleNamespace(id=30),guild_id=123,response=SimpleNamespace(
                    is_done=lambda:False,send_message=AsyncMock(),defer=AsyncMock(),edit_message=AsyncMock()),edit_original_response=AsyncMock())
                canceled=Confirm(bot,30,'remove',dict(payload))
                await canceled.cancel.callback(i)
                self.assertEqual(len((await archive.call('list',actor))['records']),1)
                for view in (Gate(bot,30,'remover'),Picker(bot,30,[r],'remover'),Confirm(bot,30,'remove',dict(payload))):
                    self.assertFalse(view.requires_staff)
                    self.assertTrue(await view.interaction_check(i))
                own=Confirm(bot,30,'remove',dict(payload))
                self.assertEqual(own.confirm.label,'Confirmar remoção')
                await own.confirm.callback(i)
                self.assertTrue(own.completed)
                self.assertEqual((await archive.call('list',actor))['records'],[])
                self.assertEqual(bot.actor.await_count,1)
                self.assertTrue(Confirm(bot,30,'purge',{}).requires_staff)
            finally:
                await bot.close()

    async def test_other_user_and_lost_staff_cannot_use_panel(self):
        with tempfile.TemporaryDirectory() as directory:
            bot = Arquivista(Config('FAKE', Path(directory) / 'test.sqlite'))
            try:
                guild = SimpleNamespace(id=123, owner_id=10)
                member = SimpleNamespace(id=30, guild=guild, guild_permissions=discord.Permissions.none(), roles=[])
                i = SimpleNamespace(user=member, guild_id=123, response=SimpleNamespace(
                    is_done=lambda: False, send_message=AsyncMock()), original_response=AsyncMock())
                view = GuardedView(bot, 99)
                self.assertFalse(await view.interaction_check(i))
                self.assertTrue(i.response.send_message.call_args.kwargs['ephemeral'])
                view.author_id, view.requires_staff = 30, True
                bot.store.set_guild(123, staff_roles=['40'])
                member.roles = [SimpleNamespace(id=40)]
                self.assertTrue(await view.interaction_check(i))
                member.roles = []
                self.assertFalse(await view.interaction_check(i))
                self.assertFalse(bot.can_configure(member))
                member.roles = [SimpleNamespace(id=40)]
                self.assertTrue(bot.is_staff_member(member))
                self.assertFalse(bot.can_configure(member))
            finally:
                await bot.close()

    async def test_actor_refetches_permission_before_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            bot = Arquivista(Config('FAKE', Path(directory) / 'test.sqlite'))
            try:
                guild = SimpleNamespace(id=123, owner_id=10)
                member = SimpleNamespace(id=30, display_name='Teste', guild=guild,
                    guild_permissions=discord.Permissions.none(), roles=[])
                guild.fetch_member = AsyncMock(return_value=member)
                bot.get_guild = lambda _: guild
                bot.store.set_guild(123, staff_roles=['40'])
                self.assertFalse((await bot.actor(30, 123)).staff)
                member.roles = [SimpleNamespace(id=40)]
                self.assertTrue((await bot.actor(30, 123)).staff)
                member.roles = []
                self.assertFalse((await bot.actor(30, 123)).staff)
                self.assertEqual(guild.fetch_member.await_count, 3)
            finally:
                await bot.close()
