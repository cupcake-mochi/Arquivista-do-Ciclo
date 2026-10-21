"""English presentation, canonical data and per-server permissions; entirely offline."""
import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from unittest.mock import AsyncMock

from arquivista import layout, pull
from arquivista.domain import STATUSES
from arquivista.idiomas import usar, tr, preparar_interface
from arquivista.store import Store
from arquivista.views import Confirm, RecordModal
from arquivista.sheet import read_sheet
from arquivista.google import DirectSheet, SHEETS, GoogleError
import test_managed as managed_tests
from test_managed import MemoryGoogle, G, A, B
from sheet_sim import FakeSheet


def record(i=1,owner=A):
    return dict(id=f'AP-00000000-0000-0000-0000-{i:012d}',owner_id=owner,owner_name='Aparência',
        appearance='Situação',work='Nome no servidor',server_name='Justificativa',status='Em uso',
        justification='CANARIO_USUARIO',image_url='',date='2026-10-21',revision=1)

class LayoutLanguage(unittest.IsolatedAsyncioTestCase):
    async def test_roundtrip_english_labels_and_canonical_status(self):
        sheet=FakeSheet(',');sheet.language='en'
        m,expect=await read_sheet(sheet,None)
        req,res=m.plan([{'op':'upsert','record':record()}])
        self.assertEqual(res[0]['status'],'ok')
        await sheet.call('write',None,{'requests':req,'expect':expect})
        m,_=await read_sheet(sheet,None);b=m.blocks()[0]
        self.assertEqual(b.tab.grid[0][0],'APPEARANCE CATALOG')
        self.assertEqual(b.tab.name,'Aparência')  # username is not translated
        self.assertEqual(b.cell(1,layout.APPEARANCE),'Situação')
        self.assertEqual(b.cell(1,layout.WORK),'Nome no servidor')
        self.assertEqual(b.cell(1,layout.STATUS),'In use')
        values=pull.row_values(b,1)
        self.assertEqual(values['status'],'Em uso')
        self.assertEqual(values['server_name'],'Justificativa')
        self.assertEqual(values['date'],'2026-10-21')
        self.assertIn('No appearance in this slot',b.tab.grid[b.start+1][2])
        self.assertIn('Appearance:',b.tab.grid[b.start+3][2])
        self.assertIn('yyyy-mm-dd',json.dumps(req))
        for st in STATUSES:
            original=record();original['status']=st;original['revision']=2
            m=layout.Model(',',language='en');m.plan([{'op':'upsert','record':original}]);b=m.blocks()[0]
            self.assertEqual(pull.row_values(b,1)['status'],st)

    async def test_expansion_transfer_and_no_changes_to_other_tabs(self):
        s=FakeSheet(',');s.language='en';control=[['KEEP_THIS','VALUE']+['']*9 for _ in range(12)]
        s.add_plain('Control',1,copy.deepcopy(control))
        m,expect=await read_sheet(s,None)
        req,res=m.plan([{'op':'upsert','record':record(i)} for i in range(1,39)])
        await s.call('write',None,{'requests':req,'expect':expect})
        m,_=await read_sheet(s,None);self.assertEqual(m.blocks()[0].slots,60)
        self.assertEqual(s.grids[1],control)
        moved=record(1,owner=B);moved['revision']=2
        req,res=m.plan([{'op':'upsert','record':moved}]);self.assertEqual(res[0]['status'],'ok')
        self.assertEqual(m.find(moved['id'])[0].owner,B)

    async def test_english_confirmation_keeps_status_code_and_user_content(self):
        with usar('en'):
            payload=dict(record());v=Confirm(NS(),99,'create',payload)
            preparar_interface(v)
            self.assertEqual(payload['status'],'Em uso')
            p={};fresh=Confirm(NS(),99,'create',p);preparar_interface(fresh)
            self.assertEqual(p['status'],'Em preparação')
            self.assertEqual(fresh.status.options[0].label,'In preparation')
            self.assertEqual(fresh.status.options[0].value,'Em preparação')
            self.assertEqual(fresh.confirm.label,'Confirm and save')
            modal=RecordModal(NS(),99,'create',record=record())
            preparar_interface(modal)
            self.assertEqual(modal.fields['appearance'].default,'Situação')
            self.assertEqual(modal.fields['work'].default,'Nome no servidor')
            self.assertEqual(modal.fields['work'].label,'Source work')

    async def test_backup_controls_and_setup_link_use_current_language(self):
        from arquivista.views import BackupPanel
        from arquivista.docs import setup_link
        cfg={'backup_hours':12,'backup_channel':None}
        bot=NS(store=NS(guild=lambda _:cfg),carteiro=NS(decorate=lambda e:e))
        with usar('en'):
            view=BackupPanel(bot,99,NS(id=123))
            self.assertEqual([o.label for o in view.every.options],
                ['Every 6 hours','Every 12 hours','Daily','Every 3 days','Weekly'])
            self.assertEqual([o.value for o in view.every.options],['6','12','24','72','168'])
            self.assertIn('every 12 hours',view.embed().description)
            self.assertIn('[Server owner guide]',setup_link())
        with usar('pt-BR'):
            self.assertIn('[Guia do dono do servidor]',setup_link())

    async def test_languages_are_concurrent_task_local(self):
        async def f(lang):
            with usar(lang):
                await asyncio.sleep(0)
                return tr('Cancelar')
        self.assertEqual(await asyncio.gather(f('en'),f('pt-BR')),['Cancel','Cancelar'])

class PerFileGoogle(MemoryGoogle):
    def __init__(self,bot):super().__init__(bot);self.locales={}
    async def request(self,method,url,*,body=None,params=None):
        key=url[len(SHEETS)+1:].split('/')[0].split(':')[0] if url.startswith(SHEETS+'/') else None
        if key and body:
            for req in body.get('requests',[]):
                props=req.get('updateSpreadsheetProperties',{}).get('properties',{})
                if 'locale' in props:self.locales[key]=props['locale']
        result=await super().request(method,url,body=body,params=params)
        if key and method=='GET' and key in self.locales:
            result['properties']['locale']=self.locales[key]
        return result

class CreationLanguage(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await managed_tests.ManagedTests.asyncSetUp(self)
        self.managed.api=self.api=PerFileGoogle(self.bot)
    async def asyncTearDown(self):await managed_tests.ManagedTests.asyncTearDown(self)
    async def test_new_file_in_english_retry_and_server_switch_preserve_file_language(self):
        self.bot.store.set_guild(G,language='en')
        url=await self.managed.create(self.guild,self.owner,'editor@example.com')
        row=self.bot.store.managed_sheet(G)
        self.assertEqual(row['language'],'en')
        self.assertEqual(self.api.locales[row['file_id']],'en_US')
        sheet=self.api.sheets[row['file_id']]
        self.assertTrue(any(x['title']=='START HERE' for x in sheet.meta))
        self.assertTrue(any(grid[0][0]=='APPEARANCE CATALOG' for grid in sheet.grids.values()))
        self.bot.store.set_guild(G,language='pt-BR')
        self.assertEqual(await self.managed.create(self.guild,self.owner),url)
        self.assertEqual(len(self.api.files),1)
        self.assertEqual(self.bot.store.managed_sheet(G)['language'],'en')
        bridge=self.bot.sheets.bridge(G);self.assertEqual(bridge.language,'en')
        await self.managed.prepare_member(self.guild,self.owner,self.other)
        self.assertTrue(all(grid[0][0]=='APPEARANCE CATALOG' for sid,grid in sheet.grids.items() if layout.is_member_tab([[x[10]] for x in grid])))
    async def test_english_sheet_manual_edits_sync_canonical_data_without_duplicate_records(self):
        from arquivista.domain import Actor
        self.bot.store.set_guild(G,language='en')
        await self.managed.create(self.guild,self.owner,'editor@example.com')
        row=self.bot.store.managed_sheet(G);sheet=self.api.sheets[row['file_id']]
        model,_=await read_sheet(self.bot.sheets.bridge(G),None)
        block=model.block_of(A)
        cells=sheet.grids[block.tab.sheet_id][block.row(1)-1]
        cells[1:5]=['CANARIO_MANUAL','Nome do usuário','Obra','In use']
        self.assertEqual(await self.bot.sheets.pull(G),1)
        await self.bot.sheets.run()
        records=self.bot.store.records(G);self.assertEqual(len(records),1)
        self.assertEqual(records[0]['status'],'Em uso')
        identity=records[0]['id']
        self.bot.store.set_guild(G,language='pt-BR')
        r=(await self.bot.archive(G).call('change_status',Actor(A,'membro',True),{'id':identity,'revision':records[0]['revision'],'status':'Arquivado','justification':'CANARIO'}))['record']
        await self.bot.sheets.run()
        model,_=await read_sheet(self.bot.sheets.bridge(G),None);b,n,_=model.find(identity)
        self.assertEqual(b.tab.grid[n-1][layout.STATUS-1],'Archived')
        self.assertEqual(len(self.bot.store.records(G)),1)
        self.assertEqual(self.bot.store.sheet_pending(G),(0,0))
    async def test_old_file_remains_portuguese_after_server_switch(self):
        await self.managed.create(self.guild,self.owner,'editor@example.com')
        row=self.bot.store.managed_sheet(G);self.assertEqual(row['language'],'pt-BR')
        self.bot.store.set_guild(G,language='en')
        bridge=self.bot.sheets.bridge(G);self.assertEqual(bridge.language,'pt-BR')
        self.assertEqual((await bridge.call('status'))['sep'],';')
    async def test_manual_locale_change_is_still_rejected(self):
        self.bot.store.set_guild(G,language='en')
        await self.managed.create(self.guild,self.owner,'editor@example.com')
        row=self.bot.store.managed_sheet(G)
        self.api.locales[row['file_id']]='pt_BR'
        with self.assertRaises(GoogleError):await self.bot.sheets.bridge(G).call('status')

class StoredLanguage(unittest.TestCase):
    def test_persists_without_touching_roles_or_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'db';s=Store(p);s.set_guild(77,staff_roles=[88],language='en');s.close()
            s=Store(p);self.assertEqual(s.guild(77)['staff_roles'],['88']);self.assertEqual(s.guild(77)['language'],'en')
            self.assertEqual(s.guild(78)['language'],'pt-BR')
            for bad in ('fr','en_US','',None):
                with self.assertRaises(ValueError):s.set_guild(77,language=bad)
            s.close()

class ServerLanguagePermissions(unittest.IsolatedAsyncioTestCase):
    async def test_language_member_denied_staff_allowed_and_foreign_member_denied(self):
        from arquivista.bot import Arquivista
        from arquivista.config import Config
        from unittest.mock import patch
        import discord
        with tempfile.TemporaryDirectory() as d:
            bot=Arquivista(Config('FAKE',Path(d)/'db'))
            guild=NS(id=77,owner_id=1)
            def interaction(uid=9,roles=(),**perms):
                return NS(guild_id=77,user=NS(id=uid,guild=guild,roles=[NS(id=r) for r in roles],guild_permissions=discord.Permissions(**perms)))
            try:
                with patch('arquivista.bot.private_reply',new_callable=AsyncMock) as reply:
                    await bot.change_language(interaction(),'en')
                    self.assertEqual(bot.store.guild(77)['language'],'pt-BR')
                    self.assertIn('Gerenciar servidor',reply.call_args.kwargs['content'])
                    bot.store.set_guild(77,staff_roles=[88])
                    await bot.change_language(interaction(roles=(88,)),'en')
                    self.assertEqual(bot.store.guild(77)['language'],'en')
                    self.assertIn('Existing files keep',reply.call_args.kwargs['content'])
                    self.assertEqual(bot.store.guild(78)['language'],'pt-BR')
                    wrong=interaction(roles=(88,));wrong.user.guild=NS(id=78,owner_id=1)
                    await bot.change_language(wrong,'pt-BR')
                    self.assertEqual(bot.store.guild(77)['language'],'en')
                    await bot.change_language(interaction(administrator=True),'pt-BR')
                    self.assertEqual(bot.store.guild(77)['language'],'pt-BR')
            finally:await bot.close()
    async def test_native_menu_names_are_unique_and_english_options_keep_wire_values(self):
        from arquivista.bot import Arquivista,install_slash_commands
        from arquivista.config import Config
        from arquivista.idiomas import arvore_e_tradutor
        with tempfile.TemporaryDirectory() as d:
            bot=Arquivista(Config('FAKE',Path(d)/'db'))
            try:
                _,T=arvore_e_tradutor();translator=T()
                payload=[await c.get_translated_payload(bot.tree,translator) for c in bot.tree.get_commands()]
                Path('/tmp/arquivista-slash-publico.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
                def walk(items):
                    names=[c.get('name_localizations',{}).get('en-US',c['name']) for c in items]
                    self.assertEqual(len(names),len(set(names)),names)
                    for c in items:
                        if 'options' in c:walk(c['options'])
                        for choice in c.get('choices',[]):
                            self.assertLessEqual(len(choice.get('name_localizations',{}).get('en-US',choice['name'])),100)
                walk(payload)
                appear=next(p for p in payload if p['name']=='aparencias')
                self.assertEqual(appear['name_localizations']['en-US'],'appearances')
                mode=next(p for p in appear['options'] if p['name']=='modo')
                self.assertEqual(mode['choices'][1]['name_localizations']['en-US'],'gallery')
                self.assertEqual(mode['choices'][1]['value'],'galeria')
            finally:await bot.close()

class EnglishErrorsAndBackup(unittest.TestCase):
    def test_validation_and_google_errors_without_changing_codes(self):
        from arquivista.domain import UserError,BridgeError
        from arquivista.managed import valid_email
        with usar('en'):
            with self.assertRaisesRegex(UserError,'valid Google account email'):valid_email('not an email')
            error=GoogleError('GOOGLE_LOCALE');self.assertEqual(error.code,'GOOGLE_LOCALE')
            self.assertIn('original locale',str(error))
            self.assertEqual(str(BridgeError('FORBIDDEN','Você não tem autorização para essa alteração.')),'You do not have permission to make this change.')
        self.assertIn('localidade',str(GoogleError('GOOGLE_LOCALE')))
    def test_backup_english_headers_status_dates_and_json_remain_canonical(self):
        import io,zipfile
        from arquivista import backup
        r=record()
        with zipfile.ZipFile(io.BytesIO(backup.workbook([r],{r['owner_id']:'Nome do usuário'},'en'))) as z:
            xml=z.read('xl/worksheets/sheet1.xml').decode()
            self.assertIn('Appearance',xml);self.assertIn('In use',xml);self.assertIn('2026-10-21',xml)
            self.assertIn('Situação',xml)  # actual appearance name, not a UI label
            self.assertIn('Nome do usuário',z.read('xl/workbook.xml').decode())
        self.assertEqual(json.loads(backup.export_json('77',[r]))['records'][0]['status'],'Em uso')
        with zipfile.ZipFile(io.BytesIO(backup.workbook([],{},'en'))) as z:
            self.assertIn('No records',z.read('xl/workbook.xml').decode());self.assertIn('Appearance',z.read('xl/worksheets/sheet1.xml').decode())
