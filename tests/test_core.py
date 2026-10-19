from __future__ import annotations
import ast
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from arquivista.domain import (Actor, UserError, normalized, exact_key, parse_prefix,
    ranked, public_record, safe_image_url, signed_envelope, valid_attachment, can_manage, ALIASES)
from arquivista.store import Store
from arquivista.config import load_env

class DomainTests(unittest.TestCase):
    def test_prefix_variations(self):
        for text in ('AC:registrar','ac:registrar','  Ac: registrar  '):
            self.assertEqual(parse_prefix(text),('registrar','',None))
    def test_mentions_and_spaces(self):
        uid='459030926928904230'
        self.assertEqual(parse_prefix(f'AC:transferir Amiya de Arknights <@!{uid}>'),('transferir','Amiya de Arknights',uid))
    def test_non_commands_ignored(self):
        self.assertIsNone(parse_prefix('Eu escrevi AC:registrar.'))
        self.assertEqual(parse_prefix('AC:inexistente')[0],'unknown')
    def test_all_aliases(self):
        for alias,expected in ALIASES.items():
            self.assertEqual(parse_prefix('AC:'+alias)[0],expected)
    def test_normalization(self):
        self.assertEqual(normalized('  TAKA O\u00a0 '),'taka o')
        self.assertEqual(exact_key(' TAKAO ','Azur  Lane'),exact_key('Takao','AZUR LANE'))
        self.assertNotEqual(exact_key('Takao','Azur Lane'),exact_key('Takao','Outra Obra'))
        self.assertEqual(exact_key('🐰','AK'),'2:🐰:ak')
    def test_search_ambiguous_preserved(self):
        records=[{'id':'1','appearance':'Takao','work':'Azur Lane'},{'id':'2','appearance':'Takao','work':'Outra obra'}]
        self.assertEqual(len(ranked(records,'Takao')),2)
        self.assertEqual(ranked(records,'Takao Azur Lane')[0]['id'],'1')
    def test_search_small_typo(self):
        self.assertTrue(ranked([{'id':'1','appearance':'Amiya','work':'Arknights'}],'Amya'))
    def test_public_projection(self):
        full={'id':'abc','appearance':'Takao','work':'Azur Lane','owner_id':'9','occupied':True,
              'status':'Arquivado','justification':'SEGREDO','server_name':'NOMESECRETO',
              'revision':'hash','date':1,'image_url':'url','group':99}
        result=public_record(full)
        self.assertEqual(set(result),{'id','appearance','work','owner_id','occupied'})
        self.assertNotIn('SEGREDO',json.dumps(result))
    def test_permissions(self):
        user=Actor('1','User');staff=Actor('2','Staff',True)
        self.assertTrue(can_manage(user,'1','editar'))
        self.assertFalse(can_manage(user,'2','editar'))
        for action in ('situacao','transferir','remover','registrar_historico'):
            self.assertFalse(can_manage(user,'1',action))
            self.assertTrue(can_manage(staff,'1',action))
    def test_safe_urls(self):
        self.assertEqual(safe_image_url('https://i.pinimg.com/a.jpg'),'https://i.pinimg.com/a.jpg')
        self.assertEqual(safe_image_url(''),'')
    def test_unsafe_urls(self):
        for url in ('http://example.com/a','https://localhost/a','https://127.0.0.1/a','https://192.168.1.2/a',
                    'https://169.254.169.254/a','https://[::1]/a','https://user:pass@example.com/a',
                    'file:///etc/passwd','https://example.com:8080/a','https://x.local/a',
                    'https://discord.com/api/webhooks/1/secret','https://2130706433/a'):
            with self.subTest(url=url),self.assertRaises(UserError):safe_image_url(url)
    def test_signing(self):
        env=signed_envelope('x'*48,'create',{'a':'ç'},'123',Actor('456','Amiya'), 'request-abc', now=100)
        self.assertEqual(env['sig'],hmac.new(b'x'*48,env['body'].encode(),hashlib.sha256).hexdigest())
        self.assertNotIn('x'*48,env['body'])
        self.assertEqual(json.loads(env['body'])['ts'],100)
    def test_attachment_magic(self):
        self.assertEqual(valid_attachment(b'\x89PNG\r\n\x1a\n123'),'.png')
        self.assertEqual(valid_attachment(b'\xff\xd8\xff123'),'.jpg')
        for data in (b'not-image',b'<svg>malicious</svg>',b''):
            with self.assertRaises(UserError):valid_attachment(data)
    def test_attachment_max_size(self):
        with self.assertRaises(UserError):valid_attachment(b'\x89PNG\r\n\x1a\n'+b'x'*(8*1024*1024))

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'data.sqlite';self.s=Store(self.path)
    def tearDown(self):
        self.s.close();self.tmp.cleanup()
    def test_settings_persist(self):
        self.s.set('log_channel','123');self.s.close();self.s=Store(self.path)
        self.assertEqual(self.s.get('log_channel'),'123')
    def test_no_duplicate_event(self):
        event={'event_id':'EV1','seq':1}
        self.s.ingest([event],1);self.s.ingest([event],1)
        self.assertEqual(len(self.s.pending()),1)
        self.assertEqual(self.s.get('cursor'),1)
    def test_retry_and_delivery(self):
        self.s.ingest([{'event_id':'EV1','seq':1}],1)
        self.s.failed('EV1',0);self.assertEqual(self.s.pending(),[])
        self.s.delivered('EV1','2','3');self.assertEqual(self.s.pending(),[])
    def test_interrupted_attempt_survives_restart(self):
        self.s.ingest([{'event_id':'EV2','seq':2}],2)
        self.s.attempt('EV2');self.s.close();self.s=Store(self.path)
        self.assertEqual(self.s.pending()[0]['tries'],1)
    def test_messages(self):
        self.s.remember(123);self.assertTrue(self.s.is_ours(123));self.assertFalse(self.s.is_ours(456))

class FilesTests(unittest.TestCase):
    def test_python_syntax(self):
        for p in ROOT.rglob('*.py'):
            ast.parse(p.read_text(),filename=str(p))
    def test_secret_not_hardcoded(self):
        import re
        for p in ROOT.rglob('*'):
            if p.suffix not in ('.py','.gs','.md','.txt','.json','.yml'):continue
            text=p.read_text()
            self.assertIsNone(re.search(r'[MN][A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{20,}',text),p)
    def test_shared_lock_migration(self):
        cm=(ROOT/'apps_script/Aparencias.gs').read_text()
        self.assertNotIn('LockService.getDocumentLock()',cm)
        self.assertIn('if(typeof acCapturarEdicao_',cm)
        self.assertIn("CM_USAR_SCRIPT_PROPERTIES",cm)
    def test_env_not_overwrite_and_no_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'.env';p.write_text('AC_TEST_ONLY="a b"\n#skip\nBAD-LINE\n')
            try:load_env(p);self.assertEqual(os.environ['AC_TEST_ONLY'],'a b')
            finally:os.environ.pop('AC_TEST_ONLY',None)
    def test_slash_prefix_parity_ast(self):
        text=(ROOT/'src/arquivista/bot.py').read_text();tree=ast.parse(text)
        names=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='command':
                for kw in node.keywords:
                    if kw.arg=='name':names.append(ast.literal_eval(kw.value))
        self.assertEqual(set(names),set(ALIASES.values()))
        self.assertEqual(len(names),16)


class SetupTests(unittest.TestCase):
    def test_setup_preserves_secret_and_private_file(self):
        spec=importlib.util.spec_from_file_location('ac_setup',ROOT/'configurar.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'.env'
            values={'DISCORD_TOKEN':'TEST_ONLY','AC_BRIDGE_SECRET':'x'*48,'DISCORD_GUILD_ID':'123456789012345678'}
            module.write_private(path,values)
            self.assertEqual(module.read_existing(path),values)
            self.assertFalse(path.with_name('.env.tmp').exists())
            if os.name!='nt':self.assertEqual(path.stat().st_mode&0o777,0o600)
    def test_setup_rejects_newline_injection(self):
        spec=importlib.util.spec_from_file_location('ac_setup',ROOT/'configurar.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'.env'
            with self.assertRaises(ValueError):module.write_private(path,{'TOKEN':'a\nOTHER=bad'})
            self.assertFalse(path.exists())

@unittest.skipUnless(importlib.util.find_spec('discord'),'discord.py não disponível neste ambiente; executar também na CI/hospedagem')
class DiscordImportTests(unittest.IsolatedAsyncioTestCase):
    async def test_commands_and_views_construct(self):
        from arquivista.bot import Arquivista
        from arquivista.config import Config
        from arquivista.views import RecordModal,Confirm,Gate,StatusPicker,Picker,Paginator
        with tempfile.TemporaryDirectory() as d:
            cfg=Config('FAKE',123456789012345678,'https://script.google.com/macros/s/test/exec','x'*48,frozenset(),Path(d)/'t.sqlite')
            bot=Arquivista(cfg)
            self.assertEqual(len(bot.tree.get_commands()),16)
            for c in bot.tree.get_commands():c.to_dict(bot.tree)
            r={'id':'AP-test','appearance':'Takao','work':'Azur Lane','owner_id':'123456789012345678',
               'status':'Em uso','revision':'r','justification':''}
            for obj in (Gate(bot,1,'editar'),RecordModal(bot,1,'create'),RecordModal(bot,1,'edit',record=r),
                        Confirm(bot,1,'remove',{}),StatusPicker(bot,1,r),Picker(bot,1,[r],'editar'),Paginator(bot,1,[r])):
                self.assertTrue(obj.to_components())
            await bot.close()

if __name__=='__main__':unittest.main(verbosity=2)
