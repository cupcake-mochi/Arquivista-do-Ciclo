'use strict';
// Executa o planejador REAL de Planilha.gs e reaplica os pedidos gerados numa grade em
// memória, conferindo que o modelo do script e o resultado da batch batem. Formatação,
// mesclagens e grupos não são simulados aqui; isso é conferido numa planilha real (docs/TESTES.md).
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict'), path = require('path');
const root = path.resolve(__dirname, '..');
const ctx = vm.createContext({console, Date, Math, JSON, Number, String, Array, Object, Error, RegExp});
vm.runInContext(fs.readFileSync(root + '/apps_script/Planilha.gs', 'utf8'), ctx);
// Objetos criados dentro do vm têm outro protótipo; compara pelo conteúdo.
const plain = x => JSON.parse(JSON.stringify(x));
const eq = (a, b, msg) => assert.deepEqual(plain(a), plain(b), msg);
let passed = 0;
function test(name, fn) { try { fn(); passed++; console.log('OK ' + name); } catch (e) { console.error('FAIL ' + name); throw e; } }

// Grade de valores + nível de agrupamento de cada linha, imitando o Sheets real:
// linhas acrescentadas no fim herdam o nível da última linha (o grupo do último bloco
// se estende), e linhas inseridas herdam o da linha seguinte.
const depths = new Map();
function groupAt(d, sid, r) {
  // Grupo de nível r.depth = trecho máximo de linhas com nível >= depth.
  let a = r.startIndex, z = r.endIndex;
  if (a >= z || d.slice(a, z).some(x => x < r.depth)) return false;
  return (a === 0 || d[a - 1] < r.depth) && (z === d.length || d[z] < r.depth);
}
function apply(sheets, requests) {
  for (const q of requests) {
    if (q.addSheet) { const p = q.addSheet.properties; sheets.set(p.sheetId, Array.from({length: p.gridProperties.rowCount}, () => Array(11).fill(''))); depths.set(p.sheetId, Array(p.gridProperties.rowCount).fill(0)); }
    else if (q.appendDimension) {
      const sid = q.appendDimension.sheetId, g = sheets.get(sid), d = depths.get(sid), last = d.length ? d[d.length - 1] : 0;
      for (let i = 0; i < q.appendDimension.length; i++) { g.push(Array(11).fill('')); d.push(last); }
    }
    else if (q.insertDimension) {
      const r = q.insertDimension.range, g = sheets.get(r.sheetId), d = depths.get(r.sheetId), n = r.endIndex - r.startIndex;
      g.splice(r.startIndex, 0, ...Array.from({length: n}, () => Array(11).fill('')));
      d.splice(r.startIndex, 0, ...Array(n).fill(d[r.startIndex] || 0));
    }
    else if (q.addDimensionGroup) { const r = q.addDimensionGroup.range, d = depths.get(r.sheetId); for (let i = r.startIndex; i < r.endIndex; i++) d[i]++; }
    else if (q.deleteDimensionGroup) {
      const r = q.deleteDimensionGroup.range, d = depths.get(r.sheetId);
      assert.ok(d.slice(r.startIndex, r.endIndex).every(x => x > 0), 'deleteDimensionGroup sem grupo');
      for (let i = r.startIndex; i < r.endIndex; i++) d[i]--;
    }
    else if (q.updateDimensionGroup) {
      const g = q.updateDimensionGroup.dimensionGroup;
      assert.ok(groupAt(depths.get(g.range.sheetId), g.range.sheetId, {...g.range, depth: g.depth}), 'updateDimensionGroup sem grupo exato no nível ' + g.depth + ' em ' + g.range.startIndex + ':' + g.range.endIndex);
    }
    else if (q.updateCells) {
      const u = q.updateCells, g = sheets.get(u.start.sheetId);
      assert.ok(u.start.rowIndex < g.length, 'escrita fora da grade');
      u.rows.forEach((row, i) => row.values.forEach((c, j) => {
        assert.ok(u.start.columnIndex + j < 11, 'escrita fora das colunas A:K');
        const v = c.userEnteredValue || {};
        g[u.start.rowIndex + i][u.start.columnIndex + j] = 'formulaValue' in v ? v.formulaValue : 'numberValue' in v ? v.numberValue : 'stringValue' in v ? v.stringValue : '';
      }));
    }
  }
}
function fresh() { return {sep: ';', tabs: [], names: [], nextSheetId: 1000}; }
function run(m, sheets, ops) {
  const plan = ctx.plPlan_(m, ops);
  apply(sheets, plan.requests);
  m.tabs.forEach(t => eq(sheets.get(t.sheetId), t.grid, 'modelo diferente da planilha em ' + t.name));
  return plan;
}
const A = '111111111111111111', B = '222222222222222222';
let serial = 0;
function rec(owner, extra) {
  return Object.assign({id: 'AP-00000000-0000-0000-0000-' + String(++serial).padStart(12, '0'), owner_id: owner, owner_name: owner === A ? 'mizuki_sama' : owner === B ? 'takao' : 'membro_' + owner.slice(-2),
    appearance: 'Personagem ' + serial, work: 'Obra', server_name: '', status: 'Em uso', justification: '', image_url: '', date: '2026-10-20', revision: 1}, extra || {});
}
const up = r => ({op: 'upsert', record: r});

test('primeiro cadastro cria a guia com o nome de usuário e o bloco do membro', () => {
  const m = fresh(), sheets = new Map(), r = rec(A, {justification: 'teste', image_url: 'https://exemplo.com/a.png'});
  const plan = run(m, sheets, [up(r)]);
  eq(plan.results, [{id: r.id, status: 'ok'}]);
  assert.equal(m.tabs[0].name, 'mizuki_sama');
  const b = ctx.plBlocks_(m)[0], loc = ctx.plFind_(m, r.id);
  assert.equal(b.owner, A); assert.equal(b.slots, 20); assert.equal(b.start, 5); assert.equal(loc.n, 1);
  const line = m.tabs[0].grid[loc.row - 1];
  eq(line.slice(1, 6), ['Personagem ' + (serial), '', 'Obra', 'Em uso', 46315]);
  eq(line.slice(7, 11), ['https://exemplo.com/a.png', r.id, A, 1]);
  assert.equal(m.tabs[0].grid[loc.row + 1][1], 'teste');
  assert.equal(m.tabs[0].grid[b.start - 1][0], 'mizuki_sama');
  assert.match(m.tabs[0].grid[loc.row - 1][6], /^=IF\(H\d+="";"";IFERROR\(IMAGE\(H\d+\);""\)\)$/);
});

test('fórmulas usam o separador da planilha', () => {
  assert.equal(ctx.plF_({sep: ';'}, '=IF(A1="a,b",1,2)'), '=IF(A1="a,b";1;2)');
  assert.equal(ctx.plF_({sep: ','}, '=IF(A1,1,2)'), '=IF(A1,1,2)');
});

test('revisão: repetir não regrava, antiga é ignorada, nova atualiza no mesmo lugar', () => {
  const m = fresh(), sheets = new Map(), r = rec(A);
  run(m, sheets, [up(r)]);
  const row = ctx.plFind_(m, r.id).row;
  let plan = run(m, sheets, [up(r)]);
  assert.equal(plan.results[0].status, 'ok'); assert.equal(plan.requests.length, 0);
  plan = run(m, sheets, [up(Object.assign({}, r, {revision: 3, status: 'Arquivado'}))]);
  assert.equal(ctx.plFind_(m, r.id).row, row); assert.equal(m.tabs[0].grid[row - 1][4], 'Arquivado');
  plan = run(m, sheets, [up(Object.assign({}, r, {revision: 2, status: 'Em uso'}))]);
  assert.equal(plan.results[0].status, 'stale'); assert.equal(m.tabs[0].grid[row - 1][4], 'Arquivado');
});

test('perto do fim o bloco ganha mais 20 posições sem mexer na guia dos outros', () => {
  const m = fresh(), sheets = new Map(), first = rec(B);
  run(m, sheets, [up(rec(A)), up(first)]);
  const before = ctx.plBlocks_(m).find(b => b.owner === B).start;
  const ops = []; for (let i = 0; i < 17; i++) ops.push(up(rec(A)));
  run(m, sheets, ops);
  const a = ctx.plBlocks_(m).find(b => b.owner === A), b = ctx.plBlocks_(m).find(x => x.owner === B);
  assert.equal(a.slots, 40); assert.equal(ctx.plUsed_(a), 18);
  assert.equal(b.start, before); assert.equal(ctx.plFind_(m, first.id).block.owner, B);
  assert.equal(m.tabs[1].grid.length, sheets.get(m.tabs[1].sheetId).length);
  for (let n = 1; n <= 40; n++) assert.equal(m.tabs[0].grid[ctx.plSlotRow_(a, n) - 1][0], n);
  // As fórmulas do visor apontam até o rodapé, que desce junto com a inserção.
  assert.match(m.tabs[0].grid[a.start - 1][5], new RegExp('A' + (a.start + 13) + ':A' + (a.start + 13 + 80)));
});

test('transferir move para o bloco do novo dono; limpar esvazia a posição', () => {
  const m = fresh(), sheets = new Map(), r = rec(A);
  run(m, sheets, [up(r), up(rec(B))]);
  const old = ctx.plFind_(m, r.id).row;
  run(m, sheets, [up(Object.assign({}, r, {owner_id: B, owner_name: 'takao', revision: 2}))]);
  const loc = ctx.plFind_(m, r.id);
  assert.equal(loc.block.owner, B); assert.equal(loc.n, 2); assert.equal(loc.block.tab.name, 'takao');
  eq(m.tabs[0].grid[old - 1].slice(1, 6), ['', '', '', '', '']);
  let plan = run(m, sheets, [{op: 'clear', id: r.id, revision: 3}]);
  assert.equal(plan.results[0].status, 'ok'); assert.equal(ctx.plFind_(m, r.id), null);
  plan = run(m, sheets, [{op: 'clear', id: r.id, revision: 3}]);
  assert.equal(plan.results[0].status, 'ok'); assert.equal(plan.requests.length, 0);
});

test('renovar o link da imagem troca só a coluna H, na mesma revisão', () => {
  const m = fresh(), sheets = new Map(), r = rec(A, {image_url: 'https://cdn.discordapp.com/a.png?ex=1'});
  run(m, sheets, [up(r)]);
  let plan = run(m, sheets, [{op: 'image', id: r.id, revision: 1, image_url: 'https://cdn.discordapp.com/a.png?ex=2'}]);
  const row = ctx.plFind_(m, r.id).row;
  assert.equal(plan.results[0].status, 'ok'); assert.equal(plan.requests.length, 1);
  assert.equal(m.tabs[0].grid[row - 1][7], 'https://cdn.discordapp.com/a.png?ex=2');
  plan = run(m, sheets, [{op: 'image', id: r.id, revision: 2, image_url: 'https://cdn.discordapp.com/a.png?ex=3'}]);
  assert.equal(plan.results[0].status, 'stale'); assert.equal(m.tabs[0].grid[row - 1][7], 'https://cdn.discordapp.com/a.png?ex=2');
});

test('cada pessoa ganha a própria guia, cada uma com um bloco', () => {
  const m = fresh(), sheets = new Map(), ops = [];
  for (let i = 0; i < 21; i++) ops.push(up(rec('1000000000000000' + String(i).padStart(2, '0'))));
  run(m, sheets, ops);
  assert.equal(m.tabs.length, 21); assert.equal(m.tabs[20].name, 'membro_20');
  m.tabs.forEach(t => { const own = ctx.plBlocks_(m).filter(b => b.tab === t); assert.equal(own.length, 1); assert.equal(own[0].start, 5); });
});

test('nome repetido (até só nas maiúsculas) ganha (2); sem nome usa o ID', () => {
  const m = fresh(), sheets = new Map();
  m.names.push('Takao');  // guia qualquer que o dono da planilha criou
  run(m, sheets, [up(rec(B)), up(rec('333333333333333333', {owner_name: 'takao'})), up(rec('444444444444444444', {owner_name: ''}))]);
  eq(m.tabs.map(t => t.name), ['takao (2)', 'takao (3)', 'Membro 444444444444444444']);
});

test('trocar o nome de usuário renomeia a guia e o cabeçalho', () => {
  const m = fresh(), sheets = new Map(), r = rec(A);
  run(m, sheets, [up(r), up(rec(B))]);
  const plan = run(m, sheets, [up(rec(A, {owner_name: 'kaltsits'}))]);
  const rename = plan.requests.filter(q => q.updateSheetProperties);
  eq(rename.map(q => q.updateSheetProperties.properties), [{sheetId: m.tabs[0].sheetId, title: 'kaltsits'}]);
  assert.equal(m.tabs[0].name, 'kaltsits'); assert.equal(m.tabs[0].grid[4][0], 'kaltsits');
  // Mesmo registro reenviado igual (sincronização completa) ainda conserta o nome, sem regravar a linha.
  const again = run(m, sheets, [up(Object.assign({}, r, {owner_name: 'kaltsits2'}))]);
  eq(again.requests.filter(q => q.updateSheetProperties).length, 1);
  assert.equal(again.requests.filter(q => q.updateCells).length, 1);
  // Sem nome (membro saiu do servidor): mantém o que tinha.
  assert.equal(run(m, sheets, [up(rec(A, {owner_name: ''}))]).requests.filter(q => q.updateSheetProperties).length, 0);
  assert.equal(m.tabs[0].name, 'kaltsits2');
});

test('operação inválida não leva as outras e não deixa resto', () => {
  const m = fresh(), sheets = new Map(), good = rec(A);
  const plan = run(m, sheets, [up(rec(A, {status: 'Qualquer'})), up(rec(A, {image_url: 'http://x.com'})), up(good), {op: 'outra'}]);
  eq(plan.results.map(x => x.status), ['invalid', 'invalid', 'ok', 'invalid']);
  assert.equal(ctx.plUsed_(ctx.plBlocks_(m)[0]), 1);
});

test('cenário da planilha de teste real', () => {
  // Gera o arquivo usado para conferir formatação e fórmulas numa planilha do Google.
  const m = fresh(), sheets = new Map(), ops = [up(rec(A, {appearance: 'Takao', work: 'Azur Lane', server_name: 'Takao', justification: 'Aprovada pela staff.',
    image_url: 'https://i.pinimg.com/736x/86/b4/a4/86b4a43271945151a9f2e2dc904c6daf.jpg'})), up(rec(B, {status: 'Em preparação', date: null}))];
  for (let i = 0; i < 17; i++) ops.push(up(rec(B)));
  ops.push(up(rec(A, {appearance: 'Takao', work: 'Azur Lane'})));
  const plan = run(m, sheets, ops);
  if (process.env.PLANILHA_CENARIO) fs.writeFileSync(process.env.PLANILHA_CENARIO, JSON.stringify(plan.requests));
});

test('Web App: só aceita pedido assinado, recente e do servidor certo; apply grava pela API', () => {
  const crypto = require('crypto'), props = new Map([['PL_SECRET', 'k'.repeat(48)], ['PL_GUILD_ID', '333333333333333333'], ['PL_SS_ID', 'ss'], ['PL_SEP', ';']]);
  const sheets = new Map(), meta = [];
  const ss = {getId: () => 'ss', getSheets: () => meta.map(x => ({getName: () => x.title, getSheetId: () => x.sheetId, getMaxRows: () => sheets.get(x.sheetId).length}))};
  let batches = 0;
  const web = vm.createContext({console: {log() {}, error() {}}, Date, Math, JSON, Number, String, Array, Object, Error, RegExp,
    PropertiesService: {getScriptProperties: () => ({getProperty: k => props.get(k) || null})},
    LockService: {getScriptLock: () => { let held = false; return {tryLock() { held = true; return true; }, hasLock: () => held, releaseLock() { held = false; }}; }},
    ContentService: {MimeType: {JSON: 'json'}, createTextOutput: x => ({setMimeType: () => JSON.parse(x)})},
    Utilities: {Charset: {UTF_8: 'utf8'}, computeHmacSha256Signature: (t, k) => [...crypto.createHmac('sha256', k).update(t).digest()]},
    SpreadsheetApp: {openById: () => ss, flush() {}},
    Sheets: {Spreadsheets: {Values: {batchGet: (id, o) => ({valueRanges: o.ranges.map(r => {
      const cut = r.lastIndexOf("'!"), title = r.slice(1, cut).replace(/''/g, "'"), x = meta.find(t => t.title === title), cells = r.slice(cut + 2);
      assert.ok(x, 'guia inexistente ' + r);
      const g = sheets.get(x.sheetId);
      return {values: cells.startsWith('K1:K') ? g.map(l => [l[10] === undefined ? '' : l[10]]) : g.map(l => l.slice())};
    })})}, batchUpdate(body) {
      batches++;
      body.requests.forEach(q => {
        if (q.addSheet) meta.push({title: q.addSheet.properties.title, sheetId: q.addSheet.properties.sheetId});
        if (q.updateSheetProperties) meta.find(t => t.sheetId === q.updateSheetProperties.properties.sheetId).title = q.updateSheetProperties.properties.title;
      });
      apply(sheets, body.requests);
    }}}});
  vm.runInContext(fs.readFileSync(root + '/apps_script/Planilha.gs', 'utf8'), web);
  const post = (body, secret) => web.doPost({postData: {contents: JSON.stringify({body: body, sig: crypto.createHmac('sha256', secret || 'k'.repeat(48)).update(body).digest('hex')})}});
  const env = (action, data, extra) => JSON.stringify(Object.assign({v: 1, ts: Math.floor(Date.now() / 1000), nonce: 'n', request_id: 'req-00000001', action: action,
    guild_id: '333333333333333333', actor: {id: '999999999999999999', name: 'Arquivista', staff: true}, data: data}, extra || {}));
  eq(post(env('status', {}), 'x'.repeat(48)), {ok: false, code: 'AUTH'});
  eq(post(env('status', {}, {guild_id: '444444444444444444'})), {ok: false, code: 'GUILD'});
  eq(post(env('status', {}, {ts: Math.floor(Date.now() / 1000) - 600})), {ok: false, code: 'CLOCK'});
  eq(web.doPost({postData: {contents: 'x'.repeat(500000)}}), {ok: false, code: 'AUTH'});
  eq(post(env('status', {})), {ok: true, data: {version: '1.1.0', tabs: 0, members: 0, records: 0}});
  const r = rec(A);
  eq(post(env('apply', {ops: [up(r)]})), {ok: true, data: {results: [{id: r.id, status: 'ok'}]}});
  eq(post(env('apply', {ops: [up(r)]})), {ok: true, data: {results: [{id: r.id, status: 'ok'}]}});
  eq(post(env('status', {})).data, {version: '1.1.0', tabs: 1, members: 1, records: 1});
  // Guia antiga do 1.0 com um membro só é renomeada; guia sem marcador é ignorada.
  assert.equal(meta[0].title, 'mizuki_sama');
  meta[0].title = "FICHAS 1–20"; meta.push({title: "Notas d'staff", sheetId: 7}); sheets.set(7, [['x']]);
  eq(post(env('apply', {ops: [up(Object.assign({}, r, {owner_name: "kal'tsits"}))]})), {ok: true, data: {results: [{id: r.id, status: 'ok'}]}});
  eq(meta.map(t => t.title), ["kal'tsits", "Notas d'staff"]);
  eq(post(env('status', {})).data, {version: '1.1.0', tabs: 1, members: 1, records: 1});
  eq(post(env('apply', {ops: 'x'})), {ok: false, code: 'INVALID'});
  assert.equal(batches, 2);  // o pedido repetido não gerou outra gravação; o renomear gerou uma
});

console.log(passed + ' testes da planilha conectada aprovados (planejador real, grade simulada).');
