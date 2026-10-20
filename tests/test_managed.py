"""Criação retomável e sincronização direta com Google simulado; nenhuma chamada externa."""
import asyncio
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
import discord

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from arquivista.archive import Archive
from arquivista.config import Config
from arquivista.domain import Actor, UserError, BridgeError
from arquivista.google import GoogleAPI, GoogleConfig, GoogleError, DirectSheet, DRIVE, SHEETS
from arquivista.managed import ManagedSheets, valid_email
from arquivista.sheet import SheetSync, read_sheet, unseal
from arquivista.store import Store
from arquivista import layout
from sheet_sim import FakeSheet

G, A, B = "111111111111111111", "222222222222222222", "333333333333333333"

class MemoryGoogle(GoogleAPI):
    def __init__(self, bot):
        super().__init__(bot)
        self.files, self.sheets, self.shares, self.calls = {}, {}, {}, []
        self.lost_create = self.fail_share = False
        self.before_write = None
        self.locale = "pt_BR"

    async def request(self, method, url, *, body=None, params=None):
        self.calls.append((method, url, copy.deepcopy(body), copy.deepcopy(params)))
        if url == DRIVE:
            if method == "GET":
                return {"files": [{"id": k, "webViewLink": v["url"]} for k, v in self.files.items()
                                  if v["request"] in params["q"]]}
            key = "file_" + str(len(self.files) + 1)
            link = "https://docs.google.com/spreadsheets/d/" + key + "/edit"
            self.files[key] = {"request": body["appProperties"]["arquivista_request"], "url": link}
            self.sheets[key] = FakeSheet()
            self.sheets[key].add_plain("Sheet1", 0, [[""] * 11 for _ in range(30)])
            self.shares[key] = set()
            if self.lost_create:
                self.lost_create = False
                raise GoogleError("BUSY", uncertain=True)
            return {"id": key, "webViewLink": link}
        if url.startswith(DRIVE + "/"):
            key = url.split("/")[-2]
            if method == "GET":
                return {"permissions": [{"type": "user", "role": "writer", "emailAddress": e} for e in self.shares[key]]}
            if self.fail_share:
                raise GoogleError("GOOGLE_INVALID")
            self.shares[key].add(body["emailAddress"])
            assert body["role"] == "writer" and params["sendNotificationEmail"] == "false"
            return {"id": "permission"}
        key = url[len(SHEETS) + 1:].split("/")[0].split(":")[0]
        sheet = self.sheets[key]
        if method == "GET":
            return {"properties": {"locale": self.locale}, "sheets": [{"properties": {
                **m, "gridProperties": {"rowCount": len(sheet.grids[m["sheetId"]]), "columnCount": 11}}} for m in sheet.meta]}
        if url.endswith("values:batchGetByDataFilter"):
            # A resposta pode vir em outra ordem: o adaptador precisa usar os filtros.
            return {"valueRanges": [{"valueRange": {"values": sheet.read(f["a1Range"])}, "dataFilters": [f]}
                                    for f in reversed(body["dataFilters"])]}
        requests = body["requests"]
        if requests and "updateSpreadsheetProperties" in requests[0]:
            self.locale = requests[0]["updateSpreadsheetProperties"]["properties"]["locale"]
            requests = requests[1:]
        if self.before_write:
            fn, self.before_write = self.before_write, None
            fn()
        sheet.apply(requests)
        return {}

class ManagedTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        store = Store(Path(self.tmp.name) / "test.sqlite")
        guild = SimpleNamespace(id=int(G), name="Servidor", owner_id=int(A))
        def member(uid, manager=False):
            m = Mock(spec=discord.Member)
            m.id, m.name, m.guild, m.manager = int(uid), "membro_" + uid[-3:], guild, manager
            return m
        self.owner, self.other = member(A, True), member(B)
        async def fetch(uid):
            return {int(A): self.owner, int(B): self.other}[uid]
        guild.fetch_member = AsyncMock(side_effect=fetch)
        guild.get_member = lambda uid: {int(A): self.owner, int(B): self.other}.get(uid)
        self.guild = guild
        self.bot = SimpleNamespace(store=store, sheet_lock=asyncio.Lock(), session=None,
            config=Config("FAKE", Path(self.tmp.name) / "test.sqlite", master_key=b"k"*32,
                          google=GoogleConfig("client", "secret", "refresh")),
            can_configure=lambda m: bool(m.manager), notify_soon=lambda: None, now_text=lambda: "agora",
            get_guild=lambda _: guild, user=SimpleNamespace(id=999999999999999999),
            archive=lambda gid: Archive(store, gid))
        self.bot.sheets = SheetSync(self.bot)
        self.bot.managed = self.managed = ManagedSheets(self.bot)
        self.managed.api = self.api = MemoryGoogle(self.bot)

    async def asyncTearDown(self):
        self.bot.store.close()
        self.tmp.cleanup()

    async def create(self):
        return await self.managed.create(self.guild, self.owner, "dono@example.com")

    async def test_creates_private_file_prepares_owner_and_reuses_after_restart(self):
        url = await self.create()
        row = self.bot.store.managed_sheet(G)
        self.assertEqual(row["state"], "ready")
        self.assertEqual(unseal(b"k"*32, row["editor"]), "dono@example.com")
        self.assertNotIn("dono@example.com", row["editor"])
        self.assertEqual(self.api.shares[row["file_id"]], {"dono@example.com"})
        model, _ = await read_sheet(self.bot.sheets.bridge(G), None)
        self.assertEqual(model.block_of(A).slots, 20)
        # Reinicia o serviço mantendo apenas o banco e o Google.
        managed = ManagedSheets(self.bot); managed.api = self.api
        self.assertEqual(await managed.create(self.guild, self.owner, "outro@example.com"), url)
        self.assertEqual(len(self.api.files), 1)
        self.assertEqual(self.api.shares[row["file_id"]], {"dono@example.com"})
        self.bot.store.drop_sheet(G)
        self.assertEqual(await managed.create(self.guild, self.owner), url)
        self.assertEqual(self.bot.store.guild(G)["sheet_url"], url)

    async def test_lost_create_response_recovers_same_file(self):
        self.api.lost_create = True
        with self.assertRaises(GoogleError):
            await self.create()
        self.assertEqual(self.bot.store.managed_sheet(G)["state"], "creating")
        await self.create()
        self.assertEqual(len(self.api.files), 1)

    async def test_uncertain_creation_does_not_create_again_when_search_is_empty(self):
        self.bot.store.begin_managed_sheet(G, "request", "sealed")
        self.bot.store.update_managed_sheet(G, state="creating")
        with self.assertRaisesRegex(UserError, "não confirmou"):
            await self.create()
        self.assertFalse(self.api.files)

    async def test_share_failure_resumes_without_another_file_or_tab(self):
        self.api.fail_share = True
        with self.assertRaises(UserError):
            await self.create()
        self.assertIsNone(self.bot.store.guild(G)["sheet_url"])
        self.assertEqual(self.bot.store.managed_sheet(G)["state"], "awaiting_email")
        self.api.fail_share = False
        await self.managed.create(self.guild, self.owner, "corrigido@example.com")
        self.assertEqual(len(self.api.files), 1)
        self.assertEqual(len(self.api.sheets["file_1"].meta), 2)
        self.assertEqual(self.api.shares["file_1"], {"corrigido@example.com"})

    async def test_concurrent_creates_reuse_one_file(self):
        links = await asyncio.gather(self.create(), self.create())
        self.assertEqual(links[0], links[1])
        self.assertEqual(len(self.api.files), 1)

    async def test_denies_non_manager_without_google_access(self):
        with self.assertRaises(UserError):
            await self.managed.create(self.guild, self.other, "dono@example.com")
        self.assertFalse(self.api.calls)

    async def test_does_not_replace_legacy_sheet(self):
        self.bot.store.set_guild(G, sheet_url="https://script.google.com/macros/s/" + "a"*30 + "/exec", sheet_key="secret")
        with self.assertRaisesRegex(UserError, "anterior"):
            await self.create()
        self.assertFalse(self.api.calls)

    async def test_no_credentials_keeps_bot_usable(self):
        self.api.config = GoogleConfig()
        with self.assertRaises(GoogleError) as cm:
            await self.create()
        self.assertEqual(cm.exception.code, "GOOGLE_SETUP")
        self.assertIsNone(self.bot.store.managed_sheet(G))

    async def test_member_rejects_text_other_guild_and_member_who_left(self):
        for invalid in ("@nome", "apelido", B, SimpleNamespace(id=int(B), guild=self.guild)):
            with self.assertRaisesRegex(UserError, "membro válido"):
                await self.managed.prepare_member(self.guild, self.owner, invalid)
        self.other.guild = SimpleNamespace(id=42)
        with self.assertRaises(UserError):
            await self.managed.prepare_member(self.guild, self.owner, self.other)
        self.other.guild = self.guild
        response = SimpleNamespace(status=404, reason="not found")
        original_fetch = self.guild.fetch_member.side_effect
        async def left(uid):
            if uid == int(B): raise discord.NotFound(response, {"message": "Unknown Member", "code": 10007})
            return await original_fetch(uid)
        self.guild.fetch_member.side_effect = left
        with self.assertRaisesRegex(UserError, "não está mais"):
            await self.managed.prepare_member(self.guild, self.owner, self.other)
        self.assertFalse(self.api.calls)

    async def test_manual_registration_expands_20_40_60_and_syncs_back(self):
        await self.create()
        await self.managed.prepare_member(self.guild, self.owner, self.other)
        sheet = self.api.sheets["file_1"]
        model, _ = await read_sheet(self.bot.sheets.bridge(G), None)
        other_sid = model.block_of(B).tab.sheet_id
        untouched = copy.deepcopy(sheet.grids[other_sid])
        # Preenche manualmente todas as 20 posições, inclusive além do gatilho de 18.
        owner = model.block_of(A)
        for n in range(1, 21):
            line = sheet.grids[owner.tab.sheet_id][owner.row(n)-1]
            line[1:5] = ["Manual " + str(n), "Nome", "Obra", "Em uso"]
        self.assertEqual(await self.bot.sheets.pull(G), 20)
        await self.bot.sheets.run()
        model, _ = await read_sheet(self.bot.sheets.bridge(G), None)
        self.assertEqual((model.block_of(A).slots, model.block_of(A).used()), (40, 20))
        self.assertEqual(sheet.grids[other_sid], untouched)
        # Pelo bot, avança até o próximo limiar: 38 ocupadas -> 60 posições.
        archive = self.bot.archive(G)
        for n in range(21, 39):
            await archive.call("create", Actor(A, "membro"), {"fields": {"appearance": "Bot " + str(n), "work": "Obra"}})
        await self.bot.sheets.run()
        model, _ = await read_sheet(self.bot.sheets.bridge(G), None)
        self.assertEqual((model.block_of(A).slots, model.block_of(A).used()), (60, 38))
        loc = model.find(self.bot.store.records(G)[0]["id"])
        sheet.grids[loc[0].tab.sheet_id][loc[1]-1][layout.SERVER_NAME-1] = "Editado no Sheets"
        self.assertEqual(await self.bot.sheets.pull(G), 1)
        self.assertTrue(any(r["server_name"] == "Editado no Sheets" for r in self.bot.store.records(G)))
        await self.bot.sheets.run()
        self.assertEqual(sheet.grids[other_sid], untouched)
        self.assertEqual(self.bot.store.sheet_pending(G), (0, 0))

    async def test_direct_write_refuses_concurrent_manual_change(self):
        await self.create()
        direct = self.bot.sheets.bridge(G)
        model, expect = await read_sheet(direct, None)
        b = model.block_of(A)
        self.api.sheets["file_1"].grids[b.tab.sheet_id][b.row(1)-1][1] = "nova edição"
        with self.assertRaises(BridgeError) as cm:
            await direct.call("write", None, {"requests": [], "expect": expect})
        self.assertEqual(cm.exception.code, "CHANGED")

class InputTests(unittest.TestCase):
    def test_google_file_is_not_hidden_by_empty_template_variables(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".env").write_text("DISCORD_TOKEN=FAKE\nGOOGLE_CLIENT_ID=\nGOOGLE_CLIENT_SECRET=\nGOOGLE_REFRESH_TOKEN=\n", encoding="utf-8")
            (root / ".env.google").write_text("GOOGLE_CLIENT_ID=client\nGOOGLE_CLIENT_SECRET=secret\nGOOGLE_REFRESH_TOKEN=refresh\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch("arquivista.config.ROOT", root):
                self.assertTrue(Config.load().google.ready)

    def test_operator_oauth_uses_loopback_state_and_pkce_without_secret_in_url(self):
        sys.path.insert(0, str(ROOT))
        from configurar_google import authorization_url
        from urllib.parse import parse_qs, urlsplit
        url = authorization_url("public_client", "http://127.0.0.1:12345/callback", "random_state", "PRIVATE_VERIFIER")
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(urlsplit(url).hostname, "accounts.google.com")
        self.assertEqual(query["redirect_uri"], ["http://127.0.0.1:12345/callback"])
        self.assertEqual(query["state"], ["random_state"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["scope"], ["https://www.googleapis.com/auth/drive.file"])
        self.assertEqual(query["access_type"], ["offline"])
        self.assertNotIn("PRIVATE_VERIFIER", url)

    def test_email_and_credentials_are_not_echoed(self):
        for invalid in ("email", "a@b", "a@b.com\nBcc:alguem@exemplo.com", "@gmail.com", "a..b@example.com"):
            with self.assertRaises(UserError): valid_email(invalid)
        self.assertEqual(valid_email(" dono+bot@EXAMPLE.COM "), "dono+bot@example.com")
        self.assertNotIn("private", repr(GoogleConfig("private", "private", "private")))

    def test_slash_member_is_discord_user_option_not_free_text(self):
        from arquivista.bot import Arquivista
        with tempfile.TemporaryDirectory() as d:
            bot = Arquivista(Config("FAKE", Path(d)/"t.sqlite"))
            group = bot.tree.get_command("planilha")
            self.assertEqual([c.name for c in group.commands], ["criar", "abrir", "membro"])
            option = group.get_command("membro").to_dict(bot.tree)["options"][0]
            self.assertEqual((option["name"], option["type"], option["required"]), ("membro", 6, True))
            bot.store.close()

class Response:
    def __init__(self, status, data=None):
        self.status, self.data = status, data or {}
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    async def json(self): return self.data

class HTTPSession:
    def __init__(self, responses=()):
        self.responses, self.calls, self.refreshes = list(responses), [], 0
    def post(self, url, **kwargs):
        self.refreshes += 1
        assert url == "https://oauth2.googleapis.com/token"
        return Response(200, {"access_token": "TOKEN_PRIVATE", "expires_in": 3600})
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception): raise response
        return response

class TransportTests(unittest.IsolatedAsyncioTestCase):
    def api(self, responses=()):
        session = HTTPSession(responses)
        bot = SimpleNamespace(config=SimpleNamespace(google=GoogleConfig("client", "secret", "refresh")), session=session)
        return GoogleAPI(bot), session

    async def test_one_refresh_for_concurrent_reads_and_one_retry_for_unauthorized(self):
        api, session = self.api([Response(401), Response(200, {"files": []})])
        await asyncio.gather(api.access_token(), api.access_token())
        self.assertEqual(session.refreshes, 1)
        await api.request("GET", DRIVE)
        self.assertEqual(session.refreshes, 2)
        self.assertEqual(len(session.calls), 2)
        self.assertFalse(session.calls[0][2]["allow_redirects"])

    async def test_create_timeout_is_uncertain_and_is_not_retried(self):
        api, session = self.api([asyncio.TimeoutError()])
        with self.assertRaises(GoogleError) as cm:
            await api.create_file("Servidor", "request", G)
        self.assertTrue(cm.exception.uncertain)
        self.assertEqual(len(session.calls), 1)

    async def test_google_errors_do_not_echo_private_response_and_classify_quota(self):
        for status, reason, code in ((400, "badRequest", "GOOGLE_INVALID"),
                (403, "storageQuotaExceeded", "GOOGLE_STORAGE"), (403, "userRateLimitExceeded", "BUSY"),
                (403, "forbidden", "GOOGLE_ACCESS"), (404, "notFound", "GOOGLE_MISSING"), (503, "backendError", "BUSY")):
            api, session = self.api([Response(status, {"error": {"message": "PRIVATE_EMAIL", "errors": [{"reason": reason}]}})])
            with self.assertRaises(GoogleError) as cm:
                await api.create_file("Servidor", "request", G)
            self.assertEqual(cm.exception.code, code)
            self.assertNotIn("PRIVATE", str(cm.exception))
            self.assertEqual(cm.exception.uncertain, status == 503)

    async def test_disallows_untrusted_destinations_before_authorizing(self):
        api, session = self.api()
        with self.assertRaises(ValueError):
            await api.request("GET", "https://exemplo.com/")
        self.assertEqual(session.refreshes, 0)

    async def test_revoked_refresh_token_has_safe_actionable_message(self):
        api, session = self.api()
        session.post = lambda *args, **kwargs: Response(400, {"error": "invalid_grant", "secret": "PRIVATE"})
        with self.assertRaises(GoogleError) as cm:
            await api.access_token()
        self.assertEqual(cm.exception.code, "GOOGLE_AUTH")
        self.assertNotIn("PRIVATE", str(cm.exception))
