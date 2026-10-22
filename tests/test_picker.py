"""Liberação drive.file do arquivo de origem: PKCE e conta dedicada, sem Google real."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, call
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from configurar_google import authorization_url
import autorizar_arquivo_google as picker

FILE='existing_source_001'
URL='https://docs.google.com/spreadsheets/d/'+FILE+'/edit'
VALUES={'GOOGLE_CLIENT_ID':'client','GOOGLE_CLIENT_SECRET':'secret','GOOGLE_REFRESH_TOKEN':'refresh'}

class PickerTests(unittest.TestCase):
    def test_native_picker_requests_only_the_selected_file_and_scope(self):
        result=authorization_url('client','http://127.0.0.1:123/callback','state','SECRET_VERIFIER',FILE)
        query=parse_qs(urlsplit(result).query)
        self.assertEqual(query['scope'],['https://www.googleapis.com/auth/drive.file'])
        self.assertEqual(query['file_ids'],[FILE])
        self.assertEqual(query['allow_multiple'],['false'])
        self.assertEqual(query['trigger_onepick'],['true'])
        self.assertEqual(query['code_challenge_method'],['S256'])
        self.assertNotIn('SECRET_VERIFIER',result)
        self.assertNotIn('refresh',result)

    def test_same_account_verifies_access_using_the_existing_refresh_token(self):
        with patch.object(picker,'refresh',return_value='old_account_token') as refresh, patch.object(picker,'account',return_value='same_account') as account, patch.object(picker,'authorize',return_value='temporary_token') as authorize, patch.object(picker,'request_json',return_value={'id':FILE,'isAppAuthorized':True,'mimeType':'application/vnd.google-apps.spreadsheet'}) as request:
            picker.authorize_existing(VALUES,URL)
            self.assertEqual(account.call_args_list,[call('old_account_token'),call('temporary_token')])
            self.assertEqual(refresh.call_count,2)
            self.assertEqual(authorize.call_args.kwargs,{'file_id':FILE})
            self.assertEqual(request.call_args.args[1],'old_account_token')

    def test_wrong_account_is_rejected_before_using_it_to_read_source(self):
        with patch.object(picker,'refresh',return_value='old'),patch.object(picker,'account',side_effect=['expected','wrong']),patch.object(picker,'authorize',return_value='new'),patch.object(picker,'request_json') as request:
            with self.assertRaisesRegex(ValueError,'outra conta'):
                picker.authorize_existing(VALUES,URL)
            request.assert_not_called()

    def test_file_mismatch_and_missing_app_authorization_are_rejected(self):
        for meta in ({'id':'other','isAppAuthorized':True},{'id':FILE,'isAppAuthorized':False}):
            with patch.object(picker,'refresh',return_value='old'),patch.object(picker,'account',return_value='same'),patch.object(picker,'authorize',return_value='new'),patch.object(picker,'request_json',return_value=meta):
                with self.assertRaises(ValueError):picker.authorize_existing(VALUES,URL)
