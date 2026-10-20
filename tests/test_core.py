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
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from arquivista.domain import (Actor, UserError, normalized, exact_key, parse_prefix,
    ranked, public_record, safe_image_url, signed_envelope, valid_attachment, can_manage, ALIASES)
from arquivista.store import Store
from arquivista.archive import Archive
from arquivista.importer import apply, check, summary
from arquivista.domain import BridgeError
import asyncio
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
        for short,action in (('reg','registrar'),('AP','aparencias'),('gal','galeria'),('busca','consultar'),('ed','editar'),
                             ('sit','situacao'),('tr','transferir'),('rm','remover'),('hist','historico'),('st','diagnostico'),('cfg','configurar')):
            self.assertEqual(parse_prefix(f'AC:{short} Takao')[0],action)
        from arquivista.domain import SHORT
        self.assertEqual(len(ALIASES),sum(len(v) for v in SHORT.values()))  # nenhuma abreviação usada por dois comandos
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
        for action in ('situacao','transferir','remover','diagnostico'):
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

G1='111111111111111111';G2='222222222222222222'
U1='333333333333333333';U2='444444444444444444';STAFF='555555555555555555'

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'data.sqlite';self.s=Store(self.path)
    def tearDown(self):
        self.s.close();self.tmp.cleanup()
    def test_settings_persist(self):
        self.s.set('avatar_hash','abc');self.s.close();self.s=Store(self.path)
        self.assertEqual(self.s.get('avatar_hash'),'abc')
    def test_guild_settings_are_separate(self):
        self.s.set_guild(G1,log_channel=10,staff_roles=[7,8]);self.s.set_guild(G2,image_channel=20)
        self.s.close();self.s=Store(self.path)
        self.assertEqual(self.s.guild(G1)['log_channel'],'10');self.assertEqual(self.s.guild(G1)['staff_roles'],['7','8'])
        self.assertIsNone(self.s.guild(G2)['log_channel']);self.assertEqual(self.s.guild(G2)['image_channel'],'20')
        self.s.set_guild(G1,log_channel=None);self.assertIsNone(self.s.guild(G1)['log_channel'])
        with self.assertRaises(ValueError):self.s.set_guild(G1,token='x')
    def test_legacy_settings_adopted_once(self):
        self.s.set('log_channel','99');self.s.set('image_channel','98')
        self.assertTrue(self.s.adopt_legacy(int(G1),[5]))
        self.assertEqual(self.s.guild(G1),{**self.s.guild(G1),'log_channel':'99','image_channel':'98','staff_roles':['5']})
        self.s.set_guild(G1,log_channel=None)
        self.assertFalse(self.s.adopt_legacy(int(G1),[5]));self.assertIsNone(self.s.guild(G1)['log_channel'])
    def test_messages(self):
        self.s.remember(123);self.assertTrue(self.s.is_ours(123));self.assertFalse(self.s.is_ours(456))

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'data.sqlite';self.s=Store(self.path)
        self.a=Archive(self.s,G1);self.b=Archive(self.s,G2)
        self.user=Actor(U1,'User');self.other=Actor(U2,'Other');self.staff=Actor(STAFF,'Staff',True)
    def tearDown(self):
        self.s.close();self.tmp.cleanup()
    def call(self,archive,action,actor,data=None,rid=None):
        return asyncio.run(archive.call(action,actor,data or {},rid))
    def code(self,archive,action,actor,data=None,rid=None):
        with self.assertRaises(BridgeError) as ctx:self.call(archive,action,actor,data,rid)
        return ctx.exception.code
    def create(self,archive=None,actor=None,appearance='Takao',work='Azur Lane',**extra):
        actor=actor or self.user
        return self.call(archive or self.a,'create',actor,{'fields':{'appearance':appearance,'work':work,**extra}})['record']
    def test_create_defaults(self):
        r=self.create(server_name='Kai')
        self.assertTrue(r['id'].startswith('AP-'));self.assertEqual(r['owner_id'],U1)
        self.assertEqual(r['status'],'Em preparação');self.assertEqual(r['revision'],1);self.assertRegex(r['date'],r'^\d{4}-\d\d-\d\d$')
    def test_duplicate_per_guild_only(self):
        self.create()
        self.assertEqual(self.code(self.a,'create',self.other,{'fields':{'appearance':' TAKAO ','work':'azur  lane'}}),'DUPLICATE')
        self.create(archive=self.b,actor=self.other)  # outro servidor, cadastro independente
        self.assertEqual(len(self.call(self.b,'list',self.other)['records']),1)
    def test_archived_still_occupies_released_frees(self):
        r=self.create()
        r=self.call(self.a,'change_status',self.staff,{'id':r['id'],'revision':r['revision'],'status':'Arquivado'})['record']
        self.assertEqual(self.code(self.a,'create',self.other,{'fields':{'appearance':'Takao','work':'Azur Lane'}}),'DUPLICATE')
        r=self.call(self.a,'change_status',self.staff,{'id':r['id'],'revision':r['revision'],'status':'Liberado'})['record']
        self.create(actor=self.other)
        # Voltar o liberado para ocupado com outra pessoa já no nome é duplicata.
        self.assertEqual(self.code(self.a,'change_status',self.staff,{'id':r['id'],'revision':r['revision'],'status':'Em uso'}),'DUPLICATE')
    def test_guilds_cannot_see_each_other(self):
        r=self.create()
        self.assertEqual(self.code(self.b,'get',self.staff,{'id':r['id']}),'NOT_FOUND')
        self.assertEqual(self.code(self.b,'remove',self.staff,{'id':r['id'],'revision':1}),'NOT_FOUND')
        self.assertEqual(self.call(self.b,'list',self.staff,{'include_released':True})['records'],[])
    def test_list_is_public_projection(self):
        self.create(server_name='SEGREDO')
        records=self.call(self.a,'list',self.other)['records']
        self.assertEqual(set(records[0]),{'id','appearance','work','owner_id','occupied'})
    def test_permissions(self):
        r=self.create()
        self.assertEqual(self.code(self.a,'get',self.other,{'id':r['id']}),'FORBIDDEN')
        self.assertEqual(self.code(self.a,'edit',self.other,{'id':r['id'],'revision':1,'fields':{'server_name':'x'}}),'FORBIDDEN')
        self.assertEqual(self.code(self.a,'edit',self.user,{'id':r['id'],'revision':1,'fields':{'work':'x'}}),'FORBIDDEN')
        for action in ('change_status','transfer','remove','history','status'):
            self.assertEqual(self.code(self.a,action,self.user,{'id':r['id'],'revision':1}),'FORBIDDEN')
        self.assertEqual(self.code(self.a,'create',self.user,{'fields':{'appearance':'A','work':'B'},'owner':{'id':U2,'name':'x'}}),'FORBIDDEN')
    def test_edit_revision_and_stale(self):
        r=self.create()
        out=self.call(self.a,'edit',self.user,{'id':r['id'],'revision':1,'fields':{'server_name':'Kai'}})
        self.assertTrue(out['changed']);self.assertEqual(out['record']['revision'],2)
        self.assertEqual(self.code(self.a,'edit',self.user,{'id':r['id'],'revision':1,'fields':{'server_name':'Outro'}}),'STALE')
        same=self.call(self.a,'edit',self.user,{'id':r['id'],'revision':2,'fields':{'server_name':'Kai'}})
        self.assertFalse(same['changed']);self.assertEqual(same['record']['revision'],2)
    def test_image_clear_and_media_reset(self):
        ref=f'discord://{G1}/{G1}/{G1}/{G1}'
        r=self.create(image_url='https://cdn.discordapp.com/a.png',media_ref=ref)
        r=self.call(self.a,'edit',self.user,{'id':r['id'],'revision':1,'fields':{'image_url':'https://i.pinimg.com/b.png'}})['record']
        self.assertEqual(r['media_ref'],'')
        r=self.call(self.a,'edit',self.user,{'id':r['id'],'revision':2,'fields':{'clear_image':True}})['record']
        self.assertEqual(r['image_url'],'')
    def test_media_ref_must_be_same_guild(self):
        ref=f'discord://{G2}/{G2}/{G2}/{G2}'
        self.assertEqual(self.code(self.a,'create',self.user,{'fields':{'appearance':'A','work':'B','media_ref':ref}}),'INVALID')
    def test_invalid_inputs(self):
        for fields in ({'appearance':'','work':'B'},{'appearance':'A'*101,'work':'B'},{'appearance':'A\x00','work':'B'},
                       {'appearance':'A','work':'B','image_url':'http://x.com/a'},{'appearance':'A','work':'B','status':'Em uso'}):
            with self.subTest(fields=fields):
                self.assertEqual(self.code(self.a,'create',self.user,{'fields':fields}),'INVALID')
    def test_member_picks_initial_status_but_cannot_change_it_later(self):
        r=self.call(self.a,'create',self.user,{'fields':{'appearance':'Exusiai','work':'Arknights'},'status':'Em uso'})['record']
        self.assertEqual(r['status'],'Em uso')
        self.assertEqual(self.create()['status'],'Em preparação')
        self.assertEqual(self.code(self.a,'create',self.user,{'fields':{'appearance':'X','work':'Y'},'status':'Banido'}),'INVALID')
        self.assertEqual(self.code(self.a,'change_status',self.user,{'id':r['id'],'revision':r['revision'],'status':'Arquivado'}),'FORBIDDEN')
    def test_idempotent_confirmation(self):
        data={'fields':{'appearance':'Amiya','work':'Arknights'}}
        first=self.call(self.a,'create',self.user,data,'req-1');again=self.call(self.a,'create',self.user,data,'req-1')
        self.assertEqual(first,again);self.assertEqual(len(self.call(self.a,'list',self.user)['records']),1)
        self.assertEqual(self.code(self.a,'create',self.user,{'fields':{'appearance':'Outra','work':'X'}},'req-1'),'REUSED_REQUEST')
        # O mesmo request_id em outro servidor é outro pedido.
        self.call(self.b,'create',self.user,data,'req-1')
    def test_transfer_and_remove_keep_history(self):
        r=self.create()
        r=self.call(self.a,'transfer',self.staff,{'id':r['id'],'revision':1,'owner':{'id':U2,'name':'Other'}})['record']
        self.assertEqual(r['owner_id'],U2);self.assertEqual(r['date'],self.create(appearance='X')['date'])
        self.assertEqual(self.code(self.a,'transfer',self.staff,{'id':r['id'],'revision':2,'owner':{'id':U2,'name':'Other'}}),'INVALID')
        out=self.call(self.a,'remove',self.staff,{'id':r['id'],'revision':2})
        self.assertEqual(out['removed_id'],r['id'])
        events=self.call(self.a,'history',self.staff,{'query':'takao azur'})['events']
        self.assertEqual([e['kind'] for e in events],['remove','transfer','create'])
        self.assertIsNone(events[0]['after']);self.assertEqual(events[2]['actor_id'],U1)
        self.assertEqual(self.call(self.b,'history',self.staff)['events'],[])
    def test_capacity_per_member(self):
        from arquivista import archive as module
        old=module.MAX_PER_MEMBER;module.MAX_PER_MEMBER=2
        try:
            self.create(appearance='A');self.create(appearance='B')
            self.assertEqual(self.code(self.a,'create',self.user,{'fields':{'appearance':'C','work':'W'}}),'CAPACITY')
            self.create(archive=self.b,appearance='C')
        finally:module.MAX_PER_MEMBER=old
    def test_notices_only_with_log_channel(self):
        self.create(appearance='Antes')
        self.assertEqual(self.s.pending(),[])
        self.s.set_guild(G1,log_channel=10)
        r=self.create(appearance='Depois',server_name='SEGREDO')
        self.call(self.a,'change_status',self.staff,{'id':r['id'],'revision':1,'status':'Em uso','justification':'INTERNO'})
        pending=self.s.pending()
        self.assertEqual([json.loads(p['data'])['kind'] for p in pending],['created','updated'])
        self.assertTrue(all(p['guild_id']==G1 for p in pending))
        self.assertNotIn('SEGREDO',json.dumps(pending));self.assertNotIn('INTERNO',json.dumps(pending))
    def test_notice_retry_and_delivery(self):
        self.s.set_guild(G1,log_channel=10);self.create()
        eid=self.s.pending()[0]['event_id']
        self.s.attempt(eid);self.s.failed(eid,0);self.assertEqual(self.s.pending(),[])
        self.s.close();self.s=Store(self.path)
        self.assertEqual(self.s.db.execute('SELECT tries FROM notices').fetchone()[0],1)
        self.s.delivered(eid,'2','3');self.assertEqual(self.s.db.execute('SELECT sent FROM notices').fetchone()[0],1)
    def test_status_counts(self):
        self.create();self.create(appearance='B',actor=self.other)
        s=self.call(self.a,'status',self.staff)
        self.assertEqual((s['records'],s['occupied'],s['members'],s['events']),(2,2,2,2))
    def test_refresh_image_needs_same_media(self):
        ref=f'discord://{G1}/{G1}/{G1}/{G1}'
        r=self.create(image_url='https://cdn.discordapp.com/a.png',media_ref=ref)
        self.call(self.a,'refresh_image',self.staff,{'id':r['id'],'media_ref':ref,'url':'https://cdn.discordapp.com/b.png'})
        self.assertEqual(self.call(self.a,'image',self.user,{'id':r['id']})['url'],'https://cdn.discordapp.com/b.png')
        self.assertEqual(self.code(self.a,'refresh_image',self.staff,{'id':r['id'],'media_ref':'x','url':'https://a.com/b'}),'STALE')

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'data.sqlite')
    def tearDown(self):
        self.s.close();self.tmp.cleanup()
    def export(self,*records):
        base={'id':'AP-0b0e4d0e-1111-4c2a-9a55-000000000001','owner_id':U1,'appearance':'Takao','work':'Azur Lane',
              'server_name':'Kai','status':'Em uso','justification':'INTERNO','image_url':'https://i.pinimg.com/a.png','date':45000}
        return {'format':'arquivista-export','version':1,'records':[{**base,**r} for r in records]}
    def test_check_and_apply_preserves_fields(self):
        data=self.export({},{'id':'AP-0b0e4d0e-1111-4c2a-9a55-000000000002','appearance':'Amiya','work':'Arknights','date':None,'status':'Arquivado'})
        records,errors,warnings=check(data)
        self.assertEqual(errors,[]);self.assertEqual(summary(records)['without_date'],1)
        self.assertEqual(apply(self.s,G1,records),2)
        a=Archive(self.s,G1);r=asyncio.run(a.call('get',Actor(STAFF,'S',True),{'id':data['records'][0]['id']}))['record']
        self.assertEqual((r['date'],r['justification'],r['status'],r['revision']),('2023-03-15','INTERNO','Em uso',1))
        self.assertIsNone(asyncio.run(a.call('get',Actor(STAFF,'S',True),{'id':data['records'][1]['id']}))['record']['date'])
        # Importado ocupa de verdade: duplicata recusada pelo fluxo normal.
        with self.assertRaises(BridgeError):asyncio.run(a.call('create',Actor(U2,'O'),{'fields':{'appearance':'takao','work':'AZUR LANE'}}))
        events=asyncio.run(a.call('history',Actor(STAFF,'S',True)))['events']
        self.assertEqual({e['kind'] for e in events},{'import'});self.assertEqual(self.s.pending(),[])
    def test_errors_block_everything(self):
        data=self.export({},{'id':'AP-0b0e4d0e-1111-4c2a-9a55-000000000002','owner_id':U2,'work':' azur  lane '},
                         {'id':'sem-id'},{'id':'AP-0b0e4d0e-1111-4c2a-9a55-000000000003','status':'Talvez','owner_id':'x'})
        records,errors,_=check(data)
        text=' '.join(errors)
        for part in ('ocupada também','formato AP-','desconhecida','Discord'):self.assertIn(part,text)
    def test_released_duplicates_are_fine(self):
        data=self.export({},{'id':'AP-0b0e4d0e-1111-4c2a-9a55-000000000002','status':'Liberado'})
        records,errors,_=check(data);self.assertEqual(errors,[]);apply(self.s,G1,records)
    def test_refuses_non_empty_guild_and_wrong_format(self):
        records,_,_=check(self.export({}));apply(self.s,G1,records)
        with self.assertRaises(ValueError):apply(self.s,G1,records)
        with self.assertRaises(ValueError):apply(self.s,G2,records)  # mesmo ID em outro servidor
        self.assertTrue(check({'format':'x'})[1])
    def test_long_text_and_bad_image_only_warn(self):
        records,errors,warnings=check(self.export({'justification':'x'*3000,'image_url':'http://a.com/b.png'}))
        self.assertEqual(errors,[]);self.assertEqual(len(warnings),2);self.assertEqual(records[0]['image_url'],'')

class SheetTests(unittest.TestCase):
    """Etapa 3: fila bot→planilha, chave cifrada e envio com uma ponte falsa."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'data.sqlite')
        self.a=Archive(self.s,G1);self.user=Actor(U1,'User');self.staff=Actor(STAFF,'Staff',True)
    def tearDown(self):
        self.s.close();self.tmp.cleanup()
    def call(self,action,actor,data=None):
        return asyncio.run(self.a.call(action,actor,data or {}))
    def queue(self):
        return {r['record_id']:(r['revision'],json.loads(r['payload'])) for r in self.s.sheet_batch(G1,100)}
    def connect(self):
        self.s.set_guild(G1,sheet_url='https://script.google.com/macros/s/'+'a'*30+'/exec',sheet_key='x')
    def test_seal_roundtrip_and_tamper(self):
        from arquivista.sheet import seal,unseal
        k=hashlib.sha256(b'k').digest();box=seal(k,'f'*64)
        self.assertEqual(unseal(k,box),'f'*64);self.assertNotIn('f'*16,box)
        with self.assertRaises(ValueError):unseal(hashlib.sha256(b'outra').digest(),box)
        v,n,b,t=box.split('.');bad='.'.join((v,n,b[:-2]+('A' if b[-2]!='A' else 'B')+b[-1],t))
        with self.assertRaises(ValueError):unseal(k,bad)
    def test_master_key_from_env_or_token(self):
        from arquivista.config import master_key
        old=os.environ.pop('AC_MASTER_KEY',None)
        try:
            self.assertEqual(master_key('tok'),master_key('tok'));self.assertNotEqual(master_key('tok'),master_key('outro'))
            os.environ['AC_MASTER_KEY']='m'*40;self.assertEqual(master_key('a'),master_key('b'))  # com a chave explícita, trocar o token não muda nada
            os.environ['AC_MASTER_KEY']='curta'
            with self.assertRaises(ValueError):master_key('tok')
        finally:
            os.environ.pop('AC_MASTER_KEY',None)
            if old is not None:os.environ['AC_MASTER_KEY']=old
    def test_nothing_queued_without_sheet(self):
        self.call('create',self.user,{'fields':{'appearance':'Takao','work':'Azur Lane'}})
        self.assertEqual(self.queue(),{})
    def test_changes_queue_latest_version_only(self):
        self.connect()
        r=self.call('create',self.user,{'fields':{'appearance':'Takao','work':'Azur Lane'}})['record']
        self.assertEqual(self.queue()[r['id']][0],1)
        r=self.call('change_status',self.staff,{'id':r['id'],'revision':1,'status':'Em uso','justification':'ok'})['record']
        q=self.queue();self.assertEqual(len(q),1);rev,op=q[r['id']]
        self.assertEqual(rev,2);self.assertEqual(op['op'],'upsert');self.assertEqual(op['record']['status'],'Em uso')
        self.assertNotIn('media_ref',op['record'])
        self.call('remove',self.staff,{'id':r['id'],'revision':2})
        self.assertEqual(self.queue()[r['id']],(3,{'op':'clear','id':r['id'],'revision':3}))
    def test_done_keeps_newer_version(self):
        self.connect()
        r=self.call('create',self.user,{'fields':{'appearance':'Takao','work':'Azur Lane'}})['record']
        self.call('change_status',self.staff,{'id':r['id'],'revision':1,'status':'Em uso'})
        self.s.sheet_done(G1,r['id'],1)  # resposta atrasada da versão 1 não apaga a 2
        self.assertEqual(self.queue()[r['id']][0],2)
        self.s.sheet_done(G1,r['id'],2);self.assertEqual(self.queue(),{})
    def test_full_sync_and_disconnect(self):
        for name in ('Takao','Atago'):self.call('create',self.user,{'fields':{'appearance':name,'work':'Azur Lane'}})
        self.connect();self.assertEqual(self.s.queue_full_sync(G1),2);self.assertEqual(len(self.queue()),2)
        self.s.drop_sheet(G1);self.assertEqual(self.queue(),{});self.assertIsNone(self.s.guild(G1)['sheet_url'])
    def test_old_database_gets_new_columns(self):
        path=Path(self.tmp.name)/'velho.sqlite';import sqlite3
        db=sqlite3.connect(path);db.execute("CREATE TABLE guilds(guild_id TEXT PRIMARY KEY,staff_roles TEXT NOT NULL DEFAULT '[]',log_channel TEXT,image_channel TEXT,created REAL NOT NULL,updated REAL NOT NULL)")
        db.execute("INSERT INTO guilds VALUES(?,?,?,?,1,1)",(G1,'[]','123',None));db.commit();db.close()
        s=Store(path);g=s.guild(G1);s.close()
        self.assertEqual(g['log_channel'],'123');self.assertIsNone(g['sheet_url'])
    def test_sync_sends_and_handles_results(self):
        from arquivista.sheet import SheetSync,seal
        from arquivista.config import Config
        self.s.set_guild(G1,sheet_url='https://script.google.com/macros/s/'+'a'*30+'/exec',sheet_key=seal(b'k'*32,'f'*64))
        ids=[self.call('create',self.user,{'fields':{'appearance':n,'work':'Azur Lane'}})['record']['id'] for n in ('Takao','Atago','Kaga')]
        sent=[]
        class Member:display_name='Kal\'tsits';name='mizuki_sama'
        class Guild:
            def get_member(self,_):return Member()
        class Bot:
            store=self.s;config=Config('T',Path('x'),master_key=b'k'*32);session=None
            class user:id=999999999999999999
            def get_guild(self,_):return Guild()
            def now_text(self):return 'agora'
        sync=SheetSync(Bot())
        sys.path.insert(0,str(ROOT/'tests'));from sheet_sim import FakeSheet
        sheet=FakeSheet();sheet.fail=BridgeError('BUSY','ocupado')
        sync.bridge=lambda gid,cfg=None:sheet
        asyncio.run(sync.run())
        self.assertEqual(self.s.sheet_pending(G1),(3,0));self.assertEqual(self.s.guild(G1)['sheet_error'],'BUSY')
        self.assertEqual(self.s.sheet_due(),[])  # em espera depois da falha
        self.s.db.execute("UPDATE sheet_outbox SET next_try=0");self.s.db.commit()
        # Um dos três chega com dado que a planilha recusa; os outros dois vão.
        self.s.db.execute("UPDATE sheet_outbox SET payload=replace(payload,'Em prepara','Qualquer') WHERE record_id=?",(ids[2],));self.s.db.commit()
        sheet.fail=None
        asyncio.run(sync.run())
        self.assertEqual([a for a,_ in sheet.calls[-2:]],['status','write'])
        _,data=sheet.calls[-1]
        names=[q['updateSheetProperties'] for q in data['requests'] if 'updateSheetProperties' in q]
        added=[q['addSheet']['properties']['title'] for q in data['requests'] if 'addSheet' in q]
        self.assertEqual(added,['mizuki_sama'])
        self.assertEqual(list(self.queue()),[]);self.assertEqual(self.s.sheet_pending(G1),(1,1))  # o recusado espera bem mais
        g=self.s.guild(G1);self.assertIsNone(g['sheet_error']);self.assertEqual(g['sheet_ok'],'agora')
        # Sincronização completa: só o que faltava (o recusado, agora válido) gera gravação.
        self.s.db.execute("DELETE FROM sheet_outbox");self.s.db.commit()
        self.s.queue_full_sync(G1);asyncio.run(sync.run())
        self.assertEqual(sheet.writes,2);self.assertEqual(list(self.queue()),[]);self.assertEqual(len(sheet.calls[-1][1]['requests']),3)
    def test_refresh_image_keeps_revision(self):
        self.connect()
        r=self.call('create',self.user,{'fields':{'appearance':'Takao','work':'Azur Lane','media_ref':f'discord://{G1}/1{"0"*17}/1{"0"*17}/1{"0"*17}','image_url':'https://cdn.discordapp.com/a.png'}})['record']
        self.s.sheet_done(G1,r['id'],1)
        self.call('refresh_image',self.staff,{'id':r['id'],'media_ref':r['media_ref'],'url':'https://cdn.discordapp.com/b.png'})
        self.assertEqual(self.queue()[r['id']],(1,{'op':'image','id':r['id'],'revision':1,'image_url':'https://cdn.discordapp.com/b.png'}))

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
        from arquivista.bot import SLASH,PUBLIC
        self.assertEqual(names,list(SLASH))
        # Todo comando de chat cai num comando de barra ou numa consulta pública.
        self.assertTrue(set(ALIASES.values())<=set(SLASH)|PUBLIC)
        self.assertEqual(len(names),10)


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
        from arquivista.views import RecordModal,Confirm,Gate,StatusPicker,Picker,Paginator,Settings
        with tempfile.TemporaryDirectory() as d:
            cfg=Config('FAKE',Path(d)/'t.sqlite')
            bot=Arquivista(cfg)
            self.assertEqual(len(bot.tree.get_commands()),10)
            # Um método do bot com nome de método do discord.py derrubava o login (dispatch).
            from discord.ext import commands
            mine={n for n in vars(Arquivista) if not n.startswith('__')}
            self.assertEqual(mine & set(dir(commands.Bot)),{'setup_hook','on_message','close'})
            bot.dispatch('connect')
            for c in bot.tree.get_commands():c.to_dict(bot.tree)
            r={'id':'AP-test','appearance':'Takao','work':'Azur Lane','owner_id':'123456789012345678',
               'status':'Em uso','revision':'r','justification':''}
            for obj in (Gate(bot,1,'editar'),RecordModal(bot,1,'create'),RecordModal(bot,1,'edit',record=r),
                        Confirm(bot,1,'remove',{}),StatusPicker(bot,1,r),Picker(bot,1,[r],'editar'),Paginator(bot,1,[r])):
                self.assertTrue(obj.to_components())
            labels=lambda v:[c.get('label') for row in v.to_components() for c in row['components']]
            self.assertEqual(labels(Paginator(bot,1,[r])),['Anterior','Próxima','Ver em galeria'])
            self.assertEqual(labels(Paginator(bot,1,[r],'gallery'))[-1],'Ver em lista')
            self.assertEqual(labels(Paginator(bot,1,[],'history')),['Anterior','Próxima'])
            self.assertEqual(labels(Gate(bot,1,'registrar')),['Preencher ficha'])
            class Avatar:url='https://cdn.discordapp.com/avatars/1/a.png'
            class Owner:id=123456789012345678;display_name='[M] - Kal\'sits';display_avatar=Avatar()
            e=(await Paginator(bot,1,[r],owner=Owner()).embed()).to_dict()
            self.assertEqual(e['thumbnail']['url'],Avatar.url);self.assertTrue(e['title'].startswith('Aparências de'))
            self.assertIn('Takao** · Azur Lane',e['description']);self.assertEqual(e['description'].count('<@'),1)
            self.assertNotIn('thumbnail',(await Paginator(bot,1,[r]).embed()).to_dict())
            m=RecordModal(bot,1,'create').to_components()
            self.assertNotIn('remover',json.dumps(m,ensure_ascii=False))
            self.assertIn('remover',json.dumps(RecordModal(bot,1,'edit',record=r).to_components(),ensure_ascii=False))
            modal=RecordModal(bot,1,'create',uploads=True).to_components()
            self.assertEqual(len(modal),5);self.assertEqual(modal[-1]['type'],18);self.assertEqual(modal[-1]['component']['type'],19)
            self.assertEqual(len(RecordModal(bot,1,'create').to_components()),4)
            rows=Confirm(bot,1,'create',{'fields':{}}).to_components()
            self.assertEqual([[c['type'] for c in row['components']] for row in rows],[[3],[2,2]])
            class Guild:
                id=int(G1)
                def get_role(self,_):return None
            self.assertTrue(Settings(bot,1,Guild()).to_components())
            self.assertIn('Backup',labels(Settings(bot,1,Guild())))
            from arquivista.views import BackupPanel
            self.assertEqual(labels(BackupPanel(bot,1,Guild()))[-2:],['Fazer backup agora','Desligar backup'])
            # Envio do backup: .json sempre, .xlsx só com planilha; agenda o próximo.
            import arquivista.bot as botmod
            sent=[]
            class Channel:
                async def send(self,**kw):sent.append(kw)
            old=botmod.backup_problem;botmod.backup_problem=lambda c:None
            try:
                Archive(bot.store,G1)
                await Archive(bot.store,G1).call('create',Actor(U1,'x'),{'fields':{'appearance':'Takao','work':'Azur Lane'}})
                bot.store.set_guild(G1,backup_channel='5'*18,backup_hours=12)
                await bot.send_backup(G1,Channel())
                self.assertEqual([f.filename.rsplit('.',1)[1] for f in sent[-1]['files']],['json'])
                nxt=bot.store.guild(G1)['backup_next'];self.assertAlmostEqual(nxt,time.time()+12*3600,delta=60)
                bot.store.set_guild(G1,sheet_url='https://script.google.com/macros/s/'+'a'*30+'/exec')
                async def name(g,o):return 'mizuki_sama'
                bot.sheets.owner_name=name
                await bot.send_backup(G1,Channel())
                self.assertEqual([f.filename.rsplit('.',1)[1] for f in sent[-1]['files']],['json','xlsx'])
            finally:
                botmod.backup_problem=old
            await bot.close()

if __name__=='__main__':unittest.main(verbosity=2)

class BridgeLoginTests(unittest.TestCase):
    def test_login_page_names_the_access_setting(self):
        from arquivista.bridge import Bridge
        class Response:
            def __init__(self, status, location=''):
                self.status, self.headers = status, {'Location': location}
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
        for reply in (Response(302, 'https://accounts.google.com/ServiceLogin?x=1'), Response(403)):
            class Session:
                def request(self, *a, **k): return reply
            bridge = Bridge(Session(), 'https://script.google.com/macros/s/' + 'a' * 40 + '/exec', 'k' * 48, 123456789012345678)
            with self.assertRaises(BridgeError) as ctx:
                asyncio.run(bridge.call('status', Actor('1', 'A', True), {}))
            self.assertEqual(ctx.exception.code, 'LOGIN')
