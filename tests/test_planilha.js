'use strict';
// Testa o Web App fixo de Planilha.gs: assinatura, servidor, horário, leitura, gravação, lista de
// pedidos permitidos, guia de sistema protegida e recusa quando a planilha mudou desde a leitura.
// A montagem das guias é do bot e é testada em tests/test_layout.py.
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict'), path = require('path'), crypto = require('crypto');
const root = path.resolve(__dirname, '..');
const plain = x => JSON.parse(JSON.stringify(x));
const eq = (a, b, msg) => assert.deepEqual(plain(a), plain(b), msg);
let passed = 0;
function test(name, fn) { try { fn(); passed++; console.log('OK ' + name); } catch (e) { console.error('FAIL ' + name); throw e; } }

const SECRET = 'k'.repeat(48), GUILD = '333333333333333333';
function webApp() {
  const props = new Map([['PL_SECRET', SECRET], ['PL_GUILD_ID', GUILD], ['PL_SS_ID', 'ss'], ['PL_SEP', ';']]);
  const meta = [{title: 'SISTEMA · ARQUIVISTA', sheetId: 5, rows: 2}, {title: "Notas d'staff", sheetId: 7, rows: 3}];
  const cells = new Map([[7, [['a', 'b'], [], ['c']]]]);
  const state = {meta, cells, batches: [], gets: []};
  const ss = {getId: () => 'ss', getSheets: () => meta.map(x => ({getName: () => x.title, getSheetId: () => x.sheetId, getMaxRows: () => x.rows}))};
  state.ctx = vm.createContext({console: {log() {}, error() {}}, Date, Math, JSON, Number, String, Array, Object, Error, RegExp,
    PropertiesService: {getScriptProperties: () => ({getProperty: k => props.get(k) || null})},
    LockService: {getScriptLock: () => { let held = false; return {tryLock() { held = true; return true; }, hasLock: () => held, releaseLock() { held = false; }}; }},
    ContentService: {MimeType: {JSON: 'json'}, createTextOutput: x => ({setMimeType: () => JSON.parse(x)})},
    Utilities: {Charset: {UTF_8: 'utf8'}, computeHmacSha256Signature: (t, k) => [...crypto.createHmac('sha256', k).update(t).digest()]},
    SpreadsheetApp: {openById: () => ss, flush() {}},
    Sheets: {Spreadsheets: {Values: {batchGet: (id, o) => { state.gets.push(o); return {valueRanges: o.ranges.map(r => ({values: cells.get(meta.find(t => r.startsWith("'" + t.title.replace(/'/g, "''") + "'!")).sheetId)}))}; }},
      batchUpdate(body) { state.batches.push(body.requests); }}}});
  vm.runInContext(fs.readFileSync(root + '/apps_script/Planilha.gs', 'utf8'), state.ctx);
  state.post = (action, data, extra, secret) => {
    const body = JSON.stringify(Object.assign({v: 1, ts: Math.floor(Date.now() / 1000), nonce: 'n', request_id: 'req-00000001', action: action,
      guild_id: GUILD, actor: {id: '999999999999999999', name: 'Arquivista', staff: true}, data: data}, extra || {}));
    return state.ctx.doPost({postData: {contents: JSON.stringify({body: body, sig: crypto.createHmac('sha256', secret || SECRET).update(body).digest('hex')})}});
  };
  return state;
}

test('só aceita pedido assinado, recente e do servidor certo', () => {
  const w = webApp();
  eq(w.post('status', {}, {}, 'x'.repeat(48)), {ok: false, code: 'AUTH'});
  eq(w.post('status', {}, {guild_id: '444444444444444444'}), {ok: false, code: 'GUILD'});
  eq(w.post('status', {}, {ts: Math.floor(Date.now() / 1000) - 600}), {ok: false, code: 'CLOCK'});
  eq(w.ctx.doPost({postData: {contents: 'x'.repeat(4000001)}}), {ok: false, code: 'AUTH'});
  eq(w.ctx.doGet(), {ok: false, code: 'AUTH'});
});

test('status lista as guias e o separador', () => {
  const w = webApp();
  eq(w.post('status', {}), {ok: true, data: {version: '2.0.0', sep: ';', sheets: [
    {title: 'SISTEMA · ARQUIVISTA', sheetId: 5, rows: 2}, {title: "Notas d'staff", sheetId: 7, rows: 3}]}});
});

test('read devolve os valores na ordem pedida, em lotes de 100', () => {
  const w = webApp(), ranges = Array.from({length: 150}, () => "'Notas d''staff'!A1:K3");
  const res = w.post('read', {ranges: ranges});
  assert.equal(res.data.values.length, 150); eq(res.data.values[0], [['a', 'b'], [], ['c']]);
  eq(w.gets.map(g => [g.ranges.length, g.valueRenderOption]), [[100, 'FORMULA'], [50, 'FORMULA']]);
  eq(w.post('read', {ranges: 'x'}), {ok: false, code: 'INVALID'});
  eq(w.post('read', {ranges: Array(501).fill('A1')}), {ok: false, code: 'INVALID'});
});

test('write aplica numa batch só; recusa pedido fora da lista e a guia de sistema', () => {
  const w = webApp(), cell = {updateCells: {start: {sheetId: 7, rowIndex: 0, columnIndex: 0}, rows: [{values: [{}]}], fields: 'userEnteredValue'}};
  eq(w.post('write', {requests: [cell, {addSheet: {properties: {sheetId: 1000, title: 'x'}}}], expect: [{sheetId: 7, rows: 3, title: "Notas d'staff"}]}), {ok: true, data: {}});
  assert.equal(w.batches.length, 1); assert.equal(w.batches[0].length, 2);
  eq(w.post('write', {requests: [{deleteSheet: {sheetId: 7}}], expect: []}), {ok: false, code: 'INVALID'});
  eq(w.post('write', {requests: [{updateCells: {}, repeatCell: {}}], expect: []}), {ok: false, code: 'INVALID'});
  eq(w.post('write', {requests: [{repeatCell: {range: {sheetId: 5}}}], expect: []}), {ok: false, code: 'INVALID'});
  eq(w.post('write', {requests: 'x', expect: []}), {ok: false, code: 'INVALID'});
  eq(w.post('write', {requests: [], expect: []}), {ok: true, data: {}});
  assert.equal(w.batches.length, 1);  // nada foi gravado pelos pedidos recusados nem pelo vazio
});

test('write recusa (CHANGED) se a guia mudou de tamanho ou de nome desde a leitura', () => {
  const w = webApp(), cell = {updateCells: {start: {sheetId: 7, rowIndex: 0, columnIndex: 0}, rows: [{values: [{}]}], fields: 'userEnteredValue'}};
  eq(w.post('write', {requests: [cell], expect: [{sheetId: 7, rows: 4, title: "Notas d'staff"}]}), {ok: false, code: 'CHANGED'});
  eq(w.post('write', {requests: [cell], expect: [{sheetId: 7, rows: 3, title: 'outro'}]}), {ok: false, code: 'CHANGED'});
  eq(w.post('write', {requests: [cell], expect: [{sheetId: 99, rows: 3, title: 'x'}]}), {ok: false, code: 'CHANGED'});
  assert.equal(w.batches.length, 0);
});

test('bot antigo recebe OLD_BOT; ação desconhecida é INVALID', () => {
  const w = webApp();
  eq(w.post('apply', {ops: []}), {ok: false, code: 'OLD_BOT'});
  eq(w.post('outra', {}), {ok: false, code: 'INVALID'});
});

test('os pedidos que o bot gera passam na lista do script', () => {
  // Gerado por tests/test_layout.py (PLANILHA_CENARIO); confere que o bot não usa nada que o script recusa.
  const file = process.env.PLANILHA_CENARIO;
  if (!file || !fs.existsSync(file)) { console.log('   (sem cenário do bot; rode com PLANILHA_CENARIO)'); return; }
  const w = webApp(), requests = JSON.parse(fs.readFileSync(file, 'utf8'));
  eq(w.post('write', {requests: requests, expect: []}), {ok: true, data: {}});
  assert.equal(w.batches[0].length, requests.length);
});

console.log(passed + ' testes do script da planilha aprovados.');
