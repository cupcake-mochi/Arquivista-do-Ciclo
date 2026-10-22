"""Importação independente: Google/Discord simulados; nenhum arquivo real é alterado."""
import asyncio
import copy
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from arquivista import importer, layout
from arquivista.domain import UserError
from arquivista.existing_sheet import ExistingSheets, spreadsheet_id, AUTH_RANGE
from arquivista.google import GoogleError, SHEETS
from arquivista.sheet import read_sheet, unseal
from arquivista.existing_views import ExistingModal, ExistingPanel, preview
from arquivista.idiomas import usar, preparar_interface
import test_managed as managed_tests
from test_managed import MemoryGoogle, G, A, B
from sheet_sim import FakeSheet

FILE = 'existing_source_001'
SOURCE = '444444444444444444'
URL = 'https://docs.google.com/spreadsheets/d/' + FILE + '/edit'
EMAIL = 'copia@example.com'
RID = 'AP-00000000-0000-0000-0000-000000000001'


class ImportGoogle(MemoryGoogle):
    def __init__(self, bot):
        super().__init__(bot)
        self.source_meta = {'id': FILE, 'name': 'ARQUIVO_PRIVADO',
            'mimeType': 'application/vnd.google-apps.spreadsheet', 'trashed': False,
            'isAppAuthorized': True, 'capabilities': {'canCopy': True}, 'appProperties': {}}
        self.named_range = {'name': AUTH_RANGE, 'range': {'sheetId': 0,
            'startRowIndex': 0, 'endRowIndex': 1, 'startColumnIndex': 1, 'endColumnIndex': 2}}
        self.code = ''
        self.info_calls = 0

    async def file_info(self, file_id):
        assert file_id == FILE
        self.info_calls += 1
        return copy.deepcopy(self.source_meta)

    async def request(self, method, url, *, body=None, params=None):
        if url == SHEETS + '/' + FILE and params == {'fields': 'namedRanges(name,range)'}:
            self.calls.append((method, url, copy.deepcopy(body), copy.deepcopy(params)))
            return {'namedRanges': [self.named_range] if self.named_range else []}
        if url == SHEETS + '/' + FILE + '/values:batchGetByDataFilter' and body['dataFilters'] == [{'a1Range': AUTH_RANGE}]:
            self.calls.append((method, url, copy.deepcopy(body), copy.deepcopy(params)))
            return {'valueRanges': [{'dataFilters': body['dataFilters'], 'valueRange': {'values': [[self.code]]}}]}
        return await super().request(method, url, body=body, params=params)


class ExistingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await managed_tests.ManagedTests.asyncSetUp(self)
        self.managed.api = self.api = ImportGoogle(self.bot)
        self.service = ExistingSheets(self.bot)
        self.source = FakeSheet()
        self.api.sheets[FILE] = self.source
        model, expect = await read_sheet(self.source, None)
        req, _ = model.plan([{'op': 'upsert', 'record': self.record()}])
        await self.source.call('write', None, {'requests': req, 'expect': expect})
        model, _ = await read_sheet(self.source, None)
        self.block = model.block_of(A)
        self.baseline = copy.deepcopy(self.source.grids)

    async def asyncTearDown(self):
        await managed_tests.ManagedTests.asyncTearDown(self)

    def record(self):
        return dict(id=RID, owner_id=A, owner_name='Pessoa', appearance='Aparência', work='Obra',
            server_name='Nome interno', status='Em uso', justification='NOTA_PRIVADA',
            image_url='https://example.com/a.png', date='2026-01-02', revision=5)

    async def prepare(self):
        request, known = await self.service.begin(self.guild, self.owner, URL, EMAIL)
        self.api.code = request.token
        summary = await self.service.inspect(self.guild, self.owner, request)
        return request, summary

    def source_writes(self):
        return [c for c in self.api.calls if c[0] != 'GET' and c[1].startswith(SHEETS + '/' + FILE)
                and not c[1].endswith('/values:batchGetByDataFilter')]

    async def test_preview_is_read_only_and_does_not_reveal_data_before_authorization(self):
        request, known = await self.service.begin(self.guild, self.owner, URL, EMAIL)
        self.assertFalse(known)
        self.assertEqual(request.title, '')
        with self.assertRaisesRegex(UserError, 'código'):
            await self.service.inspect(self.guild, self.owner, request)
        self.assertIsNone(request.records)
        self.assertIsNone(self.bot.store.managed_sheet(G))
        self.assertFalse(self.bot.store.records(G))
        self.assertEqual(self.source.grids, self.baseline)
        self.assertFalse(self.source_writes())
        self.assertFalse(self.api.shares)

    async def test_import_creates_private_independent_file_with_editor_only_on_copy(self):
        request, summary = await self.prepare()
        self.assertEqual(summary['records'], 1)
        self.assertFalse(self.bot.store.records(G))
        url = await self.service.confirm(self.guild, self.owner, request)
        self.assertNotEqual(url, URL)
        row = self.bot.store.managed_sheet(G)
        self.assertEqual(row['state'], 'ready')
        self.assertEqual(self.api.shares[row['file_id']], {EMAIL})
        self.assertNotIn(FILE, self.api.shares)
        self.assertEqual(unseal(self.bot.config.master_key, row['editor']), EMAIL)
        records = self.bot.store.records(G)
        self.assertEqual(len(records), 1)
        self.assertNotEqual(records[0]['id'], RID)
        self.assertEqual(records[0]['revision'], 1)
        self.assertEqual(records[0]['owner_id'], A)
        self.assertEqual(records[0]['date'], '2026-01-02')
        self.assertEqual(records[0]['justification'], 'NOTA_PRIVADA')
        await self.bot.sheets.guild(G)
        await self.bot.sheets.pull(G)
        self.assertEqual(len(self.bot.store.records(G)), 1)
        self.assertEqual(self.source.grids, self.baseline)
        self.assertFalse(self.source_writes())
        self.assertTrue(request.used)

    async def test_records_without_ids_are_imported_once_and_original_remains_unidentified(self):
        line = self.source.grids[self.block.tab.sheet_id][self.block.row(1)-1]
        line[layout.ID-1], line[layout.MARK-1] = '', ''
        original = copy.deepcopy(self.source.grids)
        request, _ = await self.prepare()
        await self.service.confirm(self.guild, self.owner, request)
        await self.bot.sheets.guild(G)
        await self.bot.sheets.pull(G)
        self.assertEqual(len(self.bot.store.records(G)), 1)
        self.assertEqual(self.source.grids, original)

    async def test_foreign_record_ids_get_new_ids_without_touching_source_server(self):
        importer.apply(self.bot.store, SOURCE, [self.record()])
        original = self.bot.store.records(SOURCE)
        request, _ = await self.prepare()
        await self.service.confirm(self.guild, self.owner, request)
        self.assertEqual(self.bot.store.records(SOURCE), original)
        self.assertNotEqual(self.bot.store.records(G)[0]['id'], RID)

    async def test_expired_wrong_owner_and_wrong_guild_are_rejected_without_creating(self):
        request, _ = await self.prepare()
        request.author_id = B
        with self.assertRaises(UserError):
            await self.service.confirm(self.guild, self.owner, request)
        request.author_id, request.guild_id = A, SOURCE
        with self.assertRaises(UserError):
            await self.service.confirm(self.guild, self.owner, request)
        request.guild_id, request.expires = G, 0
        with self.assertRaises(UserError):
            await self.service.confirm(self.guild, self.owner, request)
        self.assertFalse(self.api.files)
        self.assertFalse(self.bot.store.records(G))

    async def test_non_manager_never_reads_google(self):
        with self.assertRaises(UserError):
            await self.service.begin(self.guild, self.other, URL, EMAIL)
        self.assertEqual(self.api.info_calls, 0)
        self.assertFalse(self.api.calls)

    async def test_manager_role_rechecked_after_preview(self):
        request, _ = await self.prepare()
        self.owner.manager = False
        with self.assertRaises(UserError):
            await self.service.confirm(self.guild, self.owner, request)
        self.assertFalse(self.api.files)

    async def test_source_change_cancels_confirmation(self):
        request, _ = await self.prepare()
        self.source.grids[self.block.tab.sheet_id][self.block.row(1)-1][layout.APPEARANCE-1] = 'Mudou'
        with self.assertRaisesRegex(UserError, 'mudou'):
            await self.service.confirm(self.guild, self.owner, request)
        self.assertFalse(self.api.files)
        self.assertFalse(self.bot.store.records(G))

    async def test_target_change_cancels_without_overwriting_existing_records(self):
        request, _ = await self.prepare()
        r = self.record(); r['id'] = 'AP-00000000-0000-0000-0000-000000000002'
        importer.apply(self.bot.store, G, [r])
        before = self.bot.store.records(G)
        with self.assertRaises(UserError):
            await self.service.confirm(self.guild, self.owner, request)
        self.assertEqual(self.bot.store.records(G), before)
        self.assertFalse(self.api.files)

    async def test_existing_managed_or_legacy_connection_is_not_replaced(self):
        self.bot.store.begin_managed_sheet(G, 'another-request', 'sealed')
        with self.assertRaisesRegex(UserError, 'já tem uma planilha'):
            await self.service.begin(self.guild, self.owner, URL, EMAIL)
        self.assertEqual(self.api.info_calls, 0)

    async def test_explicit_owner_code_and_single_cell_range_are_required(self):
        request, _ = await self.service.begin(self.guild, self.owner, URL, EMAIL)
        for bad in (None, {'name': AUTH_RANGE, 'range': {'startRowIndex':0,'endRowIndex':2,'startColumnIndex':0,'endColumnIndex':1}}):
            self.api.named_range = bad
            with self.assertRaises(UserError):
                await self.service.inspect(self.guild, self.owner, request)
        self.assertFalse(self.bot.store.records(G))

    async def test_one_server_cannot_bypass_origin_permission_using_drive_metadata(self):
        self.api.source_meta['appProperties'] = {'arquivista_guild': SOURCE}
        request, known = await self.service.begin(self.guild, self.owner, URL, EMAIL)
        self.assertFalse(known)  # The bot is not in this origin server.
        with self.assertRaises(UserError):
            await self.service.inspect(self.guild, self.owner, request)
        self.api.code = request.token
        summary = await self.service.inspect(self.guild, self.owner, request)
        self.assertEqual(summary['records'], 1)

    async def test_authorization_removed_after_preview_is_rechecked(self):
        request, _ = await self.prepare()
        self.api.code = 'outro'
        with self.assertRaises(UserError):
            await self.service.confirm(self.guild, self.owner, request)
        self.assertFalse(self.api.files)

    async def test_no_longer_copyable_or_trashed_or_not_native_is_rejected(self):
        for change in ({'trashed':True}, {'isAppAuthorized':False}, {'mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, {'capabilities':{'canCopy':False}}):
            original = copy.deepcopy(self.api.source_meta)
            self.api.source_meta.update(change)
            with self.assertRaises(UserError):
                await self.service.begin(self.guild, self.owner, URL, EMAIL)
            self.api.source_meta = original
        self.assertFalse(self.bot.store.records(G))

    async def test_invalid_source_data_is_not_silently_dropped(self):
        line = self.source.grids[self.block.tab.sheet_id][self.block.row(1)-1]
        line[layout.STATUS-1] = 'impossivel'
        request, _ = await self.service.begin(self.guild, self.owner, URL, EMAIL)
        self.api.code = request.token
        with self.assertRaisesRegex(UserError, 'inválidos'):
            await self.service.inspect(self.guild, self.owner, request)
        self.assertFalse(self.api.files)

    async def test_failure_creating_copy_is_resumable_without_importing_again(self):
        request, _ = await self.prepare()
        self.api.lost_create = True
        with self.assertRaises(GoogleError):
            await self.service.confirm(self.guild, self.owner, request)
        records = self.bot.store.records(G)
        self.assertTrue(request.used)
        self.assertEqual(len(records), 1)
        with self.assertRaises(UserError):
            await self.service.confirm(self.guild, self.owner, request)
        await self.managed.create(self.guild, self.owner)
        self.assertEqual(self.bot.store.records(G), records)
        self.assertEqual(len(self.api.files), 1)

    async def test_double_confirmation_imports_and_shares_only_once(self):
        request, _ = await self.prepare()
        results = await asyncio.gather(self.service.confirm(self.guild, self.owner, request),
            self.service.confirm(self.guild, self.owner, request), return_exceptions=True)
        self.assertEqual(sum(isinstance(r, str) for r in results), 1)
        self.assertEqual(len(self.bot.store.records(G)), 1)
        self.assertEqual(len(self.api.files), 1)
        self.assertEqual(self.source.grids, self.baseline)

    async def test_database_failure_rolls_back_import_and_reservation_together(self):
        request, _ = await self.prepare()
        self.bot.store.db.execute("CREATE TRIGGER fail_import BEFORE INSERT ON managed_sheets BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(Exception):
            await self.service.confirm(self.guild, self.owner, request)
        self.assertFalse(self.bot.store.records(G))
        self.assertIsNone(self.bot.store.managed_sheet(G))
        self.assertEqual(self.bot.store.db.execute('SELECT count(*) FROM events').fetchone()[0], 0)
        self.assertFalse(self.api.files)

    async def test_ui_preview_describes_copy_not_original_permission_grant(self):
        request, summary = await self.prepare()
        text = preview(self.bot, request, summary).description
        self.assertIn('nova planilha', text)
        self.assertIn('IDs novos', text)
        self.assertIn('Somente a cópia', text)
        self.assertLessEqual(len(text), 4096)
        modal = ExistingModal(self.bot)
        self.assertEqual(len(modal.children), 2)
        view = ExistingPanel(self.bot, request, confirmation=True)
        self.assertEqual([c.label for c in view.children], ['Importar e criar cópia', 'Cancelar'])

    async def test_code_cannot_be_reused_for_another_request(self):
        first, _ = await self.prepare()
        second, _ = await self.service.begin(self.guild, self.owner, URL, EMAIL)
        self.assertNotEqual(first.token, second.token)
        with self.assertRaises(UserError):
            await self.service.inspect(self.guild, self.owner, second)
        self.assertFalse(self.api.files)

    async def test_registered_source_manager_authorizes_without_source_edit(self):
        self.api.source_meta['appProperties'] = {'arquivista_guild': G}
        request, identified = await self.service.begin(self.guild, self.owner, URL, EMAIL)
        self.assertTrue(identified)
        await self.service.inspect(self.guild, self.owner, request)
        await self.service.confirm(self.guild, self.owner, request)
        self.assertEqual(self.source.grids, self.baseline)
        self.assertFalse(self.source_writes())

    async def test_large_source_fails_before_reading_values(self):
        request, _ = await self.service.begin(self.guild, self.owner, URL, EMAIL)
        self.api.code = request.token
        with patch('arquivista.existing_sheet.MAX_CELLS', 0), self.assertRaisesRegex(UserError, 'tamanho'):
            await self.service.inspect(self.guild, self.owner, request)
        self.assertFalse(self.api.files)

    async def test_import_limit_fails_instead_of_truncating_records(self):
        with patch('arquivista.existing_sheet.MAX_RECORDS', 0), self.assertRaisesRegex(UserError, '5.000'):
            await self.prepare()
        self.assertFalse(self.bot.store.records(G))

    async def test_english_form_preview_and_buttons_are_translated(self):
        request, summary = await self.prepare()
        with usar('en'):
            modal = ExistingModal(self.bot)
            view = ExistingPanel(self.bot, request, confirmation=True)
            preparar_interface(view)
            self.assertIn('Import', modal.title)
            self.assertEqual(modal.email.label, 'Google email to edit the copy')
            self.assertEqual(view.confirm.label, 'Import and create copy')
            text = preview(self.bot, request, summary).description
            self.assertIn('Only the new copy', text)
            self.assertNotIn('Somente', text)

    async def test_cancel_keeps_source_and_database_and_google_permissions(self):
        request, _ = await self.prepare()
        panel = ExistingPanel(self.bot, request)
        with patch('arquivista.existing_views.private_reply', new_callable=AsyncMock):
            await panel.cancel.callback(SimpleNamespace(response=SimpleNamespace(defer=AsyncMock())))
        self.assertTrue(request.used)
        self.assertFalse(request.started)
        self.assertFalse(self.bot.store.records(G))
        self.assertFalse(self.api.shares)
        self.assertEqual(self.source.grids, self.baseline)

    async def test_cancel_after_import_does_not_claim_to_undo_saved_records(self):
        request, _ = await self.prepare()
        await self.service.confirm(self.guild, self.owner, request)
        panel = ExistingPanel(self.bot, request)
        with patch('arquivista.existing_views.private_reply', new_callable=AsyncMock) as reply:
            await panel.cancel.callback(SimpleNamespace(response=SimpleNamespace(defer=AsyncMock())))
        self.assertNotIn('cancelada', reply.call_args.kwargs['content'])
        self.assertEqual(len(self.bot.store.records(G)), 1)
        self.assertEqual(len(self.api.files), 1)

    async def test_existing_panel_rechecks_requester_server_and_management(self):
        request, _ = await self.prepare()
        panel = ExistingPanel(self.bot, request)
        with patch('arquivista.existing_views.private_reply', new_callable=AsyncMock), patch('arquivista.views.private_reply', new_callable=AsyncMock):
            self.assertTrue(await panel.interaction_check(SimpleNamespace(user=self.owner,guild_id=int(G))))
            self.assertFalse(await panel.interaction_check(SimpleNamespace(user=self.other,guild_id=int(G))))
            self.assertFalse(await panel.interaction_check(SimpleNamespace(user=self.owner,guild_id=int(SOURCE))))
            self.owner.manager = False
            self.assertFalse(await panel.interaction_check(SimpleNamespace(user=self.owner,guild_id=int(G))))


class URLTests(unittest.TestCase):
    def test_canonical_sheet_links(self):
        for suffix in ('', '/', '/edit', '/edit?gid=1#gid=1', '/view', '/preview'):
            self.assertEqual(spreadsheet_id(URL[:-5]+suffix), FILE)

    def test_other_destinations_are_rejected(self):
        for value in ('http://docs.google.com/spreadsheets/d/'+FILE,
            'https://docs.google.com.evil.test/spreadsheets/d/'+FILE,
            'https://docs.google.com@evil.test/spreadsheets/d/'+FILE,
            'https://docs.google.com:443/spreadsheets/d/'+FILE,
            'https://drive.google.com/file/d/'+FILE+'/view',
            'https://script.google.com/macros/s/a/exec', 'file:///tmp/test', 'abc'):
            with self.subTest(value=value), self.assertRaises(UserError):
                spreadsheet_id(value)
