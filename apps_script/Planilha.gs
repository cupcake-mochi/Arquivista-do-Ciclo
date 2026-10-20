/**
 * Arquivista do Ciclo — planilha conectada v1.0.0 (etapa 3: o bot grava na planilha).
 *
 * Funciona em QUALQUER planilha: o script usa a planilha onde ele está, sem ID fixo.
 * Este arquivo é sozinho; não junte com Aparencias.gs/Arquivista.gs (são do modelo antigo).
 *
 * Instalação (staff):
 *  1. Crie uma planilha nova do Google. Extensões > Apps Script. Cole este arquivo.
 *  2. Em Serviços (+), adicione "Google Sheets API".
 *  3. Recarregue a planilha e use o menu Arquivista > Instalar. Informe o ID do servidor.
 *  4. Implantar > Nova implantação > App da Web: executar como você, acesso "Qualquer pessoa".
 *  5. No Discord, /configurar > Planilha: cole a URL /exec e a chave mostrada na instalação.
 *
 * O bot é a fonte dos dados. Ele manda cada mudança com a revisão do banco e a planilha
 * só aplica o que for mais novo do que já tem; repetir um pedido não duplica nada.
 * Nesta versão, editar a planilha à mão NÃO volta para o bot (isso é a etapa 4).
 */
const PL = Object.freeze({
  version: '1.1.0', step: 20, head: 13, width: 11,
  maxBody: 400000, maxOps: 100, firstBlock: 5,
  statuses: ['Em preparação', 'Em uso', 'Arquivado', 'Liberado'],
  headers: ['Nº', 'Aparência', 'Nome no servidor', 'Obra de origem', 'Situação', 'Cadastro', 'Imagem', 'Link da imagem', 'ID do registro', 'ID Discord', 'Revisão']
});
// Colunas (1 = A). K guarda marcadores e revisões e fica escondida.
const PC = Object.freeze({n: 1, appearance: 2, server_name: 3, work: 4, status: 5, date: 6, image: 7, url: 8, id: 9, owner: 10, mark: 11});

// ---------------- erros e utilitários ----------------
function plFail_(code) { const e = new Error(code); e.plCode = code; throw e; }
function plProps_() { return PropertiesService.getScriptProperties(); }
function plHex_(bytes) { return bytes.map(x => (x & 255).toString(16).padStart(2, '0')).join(''); }
function plHmac_(s, key) { return plHex_(Utilities.computeHmacSha256Signature(s, key, Utilities.Charset.UTF_8)); }
function plEqual_(a, b) { a = String(a); b = String(b); let d = a.length ^ b.length; for (let i = 0; i < Math.max(a.length, b.length); i++) d |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0); return d === 0; }
function plSnowflake_(s) { return typeof s === 'string' && /^[0-9]{17,20}$/.test(s); }
function plText_(v, max) { if (typeof v !== 'string' || v.length > max || /[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(v)) plFail_('INVALID'); return v.trim(); }
function plLetter_(c) { let s = ''; while (c > 0) { const m = (c - 1) % 26; s = String.fromCharCode(65 + m) + s; c = Math.floor((c - 1) / 26); } return s; }
function plSerial_(iso) {
  if (iso === null || iso === undefined || iso === '') return '';
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso)); if (!m) plFail_('INVALID');
  return Date.UTC(+m[1], +m[2] - 1, +m[3]) / 86400000 + 25569;
}
/** Fórmulas são escritas com vírgula e convertidas para o separador da planilha (pt-BR usa ;). */
function plF_(m, text) {
  if (m.sep === ',') return text;
  let out = '', quoted = false;
  for (const ch of text) { if (ch === '"') quoted = !quoted; out += (!quoted && ch === ',') ? m.sep : ch; }
  return out;
}

// ---------------- aparência (cores do modelo de hoje) ----------------
function plRgb_(r, g, b) { return {red: r, green: g, blue: b}; }
const PS = Object.freeze({
  ink: plRgb_(0.2, 0.255, 0.326), purple: plRgb_(0.322, 0.231, 0.384), white: plRgb_(1, 1, 1),
  title: plRgb_(0.122, 0.165, 0.267), help: plRgb_(0.922, 0.933, 0.969), header: plRgb_(0.322, 0.227, 0.384),
  visor: plRgb_(0.925, 0.906, 0.949), pick: plRgb_(1, 0.945, 0.827), pickInk: plRgb_(0.184, 0.345, 0.557),
  photo: plRgb_(0.937, 0.945, 0.961), name: plRgb_(0.969, 0.969, 0.98), note: plRgb_(0.976, 0.973, 1),
  columns: plRgb_(0.204, 0.267, 0.365), section: plRgb_(0.922, 0.91, 0.953), slot: plRgb_(0.878, 0.859, 0.929),
  slotInk: plRgb_(0.31, 0.227, 0.4), media: plRgb_(0.961, 0.965, 0.976), label: plRgb_(0.898, 0.859, 0.949),
  justify: plRgb_(0.984, 0.976, 1)
});
function plRange_(sid, r1, r2, c1, c2) { return {sheetId: sid, startRowIndex: r1 - 1, endRowIndex: r2, startColumnIndex: c1 - 1, endColumnIndex: c2}; }
function plFormat_(req, sid, r1, r2, c1, c2, f) {
  const fmt = {textFormat: {fontFamily: 'Arial', fontSize: f.size || 10, bold: !!f.bold, foregroundColor: f.ink || PS.ink},
    backgroundColor: f.bg || PS.white, verticalAlignment: f.v || 'MIDDLE', horizontalAlignment: f.h || 'LEFT', wrapStrategy: f.wrap || 'WRAP'};
  if (f.date) fmt.numberFormat = {type: 'DATE', pattern: 'dd/mm/yyyy'};
  req.push({repeatCell: {range: plRange_(sid, r1, r2, c1, c2), cell: {userEnteredFormat: fmt}, fields: 'userEnteredFormat'}});
}
function plMerge_(req, sid, r1, r2, c1, c2) { req.push({mergeCells: {range: plRange_(sid, r1, r2, c1, c2), mergeType: 'MERGE_ALL'}}); }
function plHeight_(req, sid, r1, r2, px) { req.push({updateDimensionProperties: {range: {sheetId: sid, dimension: 'ROWS', startIndex: r1 - 1, endIndex: r2}, properties: {pixelSize: px}, fields: 'pixelSize'}}); }
function plGroup_(req, sid, r1, r2, depth, collapsed) {
  const range = {sheetId: sid, dimension: 'ROWS', startIndex: r1 - 1, endIndex: r2};
  req.push({addDimensionGroup: {range: range}});
  if (collapsed) req.push({updateDimensionGroup: {dimensionGroup: {range: range, depth: depth, collapsed: true}, fields: 'collapsed'}});
}

// ---------------- modelo em memória (valores A:K de cada guia de membro) ----------------
function plCell_(v) {
  if (v === null || v === undefined || v === '') return {};
  if (typeof v === 'object' && v.f) return {userEnteredValue: {formulaValue: v.f}};
  return {userEnteredValue: typeof v === 'number' ? {numberValue: v} : {stringValue: String(v)}};
}
/** Grava valores numa linha e mantém o modelo igual ao que a planilha vai ficar. */
function plSet_(m, tab, row, col, values) {
  m.req.push({updateCells: {start: {sheetId: tab.sheetId, rowIndex: row - 1, columnIndex: col - 1},
    rows: [{values: values.map(plCell_)}], fields: 'userEnteredValue'}});
  const line = tab.grid[row - 1];
  values.forEach((v, j) => { line[col - 1 + j] = (typeof v === 'object' && v && v.f) ? v.f : (v === null || v === undefined ? '' : v); });
}
function plEmptyRows_(n) { return Array.from({length: n}, () => Array(PL.width).fill('')); }
function plGrow_(m, tab, rows) {
  if (tab.grid.length >= rows) return;
  const n = rows - tab.grid.length, start = tab.grid.length;
  const last = tab.grid.length ? String(tab.grid[start - 1][PC.mark - 1] || '') : '';
  m.req.push({appendDimension: {sheetId: tab.sheetId, dimension: 'ROWS', length: n}});
  // No Sheets, linhas acrescentadas entram no grupo da última linha. Quando ela é o rodapé
  // de um bloco, o grupo dele engoliria o bloco novo: tira as linhas novas desse grupo.
  if (last.startsWith('FIM:')) m.req.push({deleteDimensionGroup: {range: {sheetId: tab.sheetId, dimension: 'ROWS', startIndex: start, endIndex: start + n}}});
  tab.grid.push(...plEmptyRows_(n));
}
function plInsert_(m, tab, before, n) {
  m.req.push({insertDimension: {range: {sheetId: tab.sheetId, dimension: 'ROWS', startIndex: before - 1, endIndex: before - 1 + n}, inheritFromBefore: false}});
  tab.grid.splice(before - 1, 0, ...plEmptyRows_(n));
}
/** Blocos lidos dos marcadores da coluna K: BLOCO:<id> no cabeçalho e FIM:<id> no rodapé. */
function plBlocks_(m) {
  const out = [];
  m.tabs.forEach(tab => {
    let open = null;
    tab.grid.forEach((line, i) => {
      const k = String(line[PC.mark - 1] || '');
      if (k.startsWith('BLOCO:')) open = {tab: tab, owner: k.slice(6), start: i + 1};
      else if (k.startsWith('FIM:') && open && k.slice(4) === open.owner) {
        open.end = i + 1; open.slots = (open.end - open.start - PL.head) / 4;
        if (Number.isInteger(open.slots) && open.slots > 0) out.push(open);
        open = null;
      }
    });
  });
  return out;
}
function plSlotRow_(b, n) { return b.start + PL.head + 4 * (n - 1); }
function plFind_(m, id) {
  for (const b of plBlocks_(m)) for (let n = 1; n <= b.slots; n++) {
    const row = plSlotRow_(b, n);
    if (b.tab.grid[row - 1][PC.id - 1] === id) return {block: b, row: row, n: n};
  }
  return null;
}
function plUsed_(b) { let used = 0; for (let n = 1; n <= b.slots; n++) if (b.tab.grid[plSlotRow_(b, n) - 1][PC.id - 1]) used++; return used; }

// ---------------- estrutura: guia, bloco de membro e posições ----------------
/** Nome de guia livre: o nome de usuário do dono, com (2), (3)... se já existir outra guia com ele. */
function plTabName_(m, name, owner, self) {
  const base = String(name || ('Membro ' + owner)).replace(/[\x00-\x1f]/g, '').trim().slice(0, 90) || ('Membro ' + owner);
  // O Sheets não aceita duas guias com o mesmo nome, nem só mudando maiúsculas.
  const key = n => n.toLowerCase(), taken = n => m.names.some(x => key(x) === key(n) && x !== self);
  let out = base;
  for (let i = 2; taken(out); i++) out = base + ' (' + i + ')';
  return out;
}
function plNewTab_(m, name, owner) {
  const sid = m.nextSheetId++;
  const tab = {name: plTabName_(m, name, owner), sheetId: sid, grid: plEmptyRows_(PL.firstBlock)};
  m.names.push(tab.name);
  const req = m.req;
  req.push({addSheet: {properties: {sheetId: sid, title: tab.name,
    gridProperties: {rowCount: PL.firstBlock, columnCount: PL.width, frozenRowCount: 3, hideGridlines: true}}}});
  [48, 160, 160, 140, 135, 100, 155, 225, 290, 180, 70].forEach((px, i) => req.push({updateDimensionProperties: {
    range: {sheetId: sid, dimension: 'COLUMNS', startIndex: i, endIndex: i + 1}, properties: {pixelSize: px}, fields: 'pixelSize'}}));
  req.push({updateDimensionProperties: {range: {sheetId: sid, dimension: 'COLUMNS', startIndex: PC.mark - 1, endIndex: PC.mark},
    properties: {hiddenByUser: true}, fields: 'hiddenByUser'}});
  m.tabs.push(tab);
  plSet_(m, tab, 1, 1, ['CATÁLOGO DE APARÊNCIAS']);
  plSet_(m, tab, 2, 1, ['Esta planilha é atualizada pelo Arquivista. Use + / − para abrir as justificativas. Vermelho: aparência + obra repetida nas fichas desta pessoa.']);
  plSet_(m, tab, 3, 1, ['Cada membro começa com 20 posições e ganha mais 20 quando está perto de encher. O visor mostra a posição escolhida.']);
  plMerge_(req, sid, 1, 1, 1, 10); plMerge_(req, sid, 2, 2, 1, 10); plMerge_(req, sid, 3, 3, 1, 10);
  plFormat_(req, sid, 1, 1, 1, 10, {bg: PS.title, ink: PS.white, bold: true, size: 16});
  plFormat_(req, sid, 2, 3, 1, 10, {bg: PS.help});
  plHeight_(req, sid, 1, 1, 44); plHeight_(req, sid, 2, 3, 32); plHeight_(req, sid, 4, 4, 12);
  // Uma regra por coluna para a guia inteira, no lugar de milhares de pedaços.
  const colors = {'Em preparação': [plRgb_(1, 0.953, 0.867), plRgb_(0.557, 0.357, 0.075)], 'Em uso': [plRgb_(0.91, 0.957, 0.925), plRgb_(0.137, 0.416, 0.282)],
    'Arquivado': [plRgb_(0.922, 0.914, 0.961), plRgb_(0.337, 0.271, 0.475)], 'Liberado': [plRgb_(0.918, 0.937, 0.973), plRgb_(0.212, 0.337, 0.471)]};
  const status = {sheetId: sid, startRowIndex: PL.firstBlock - 1, startColumnIndex: PC.status - 1, endColumnIndex: PC.status};
  PL.statuses.forEach(s => req.push({addConditionalFormatRule: {index: 0, rule: {ranges: [status], booleanRule: {
    condition: {type: 'TEXT_EQ', values: [{userEnteredValue: s}]}, format: {backgroundColor: colors[s][0], textFormat: {bold: true, foregroundColor: colors[s][1]}}}}}}));
  const r = PL.firstBlock;
  req.push({addConditionalFormatRule: {index: 0, rule: {ranges: [{sheetId: sid, startRowIndex: r - 1, startColumnIndex: PC.appearance - 1, endColumnIndex: PC.appearance}],
    booleanRule: {condition: {type: 'CUSTOM_FORMULA', values: [{userEnteredValue: plF_(m, '=AND($I' + r + '<>"",$E' + r + '<>"Liberado",COUNTIFS($B:$B,$B' + r + ',$D:$D,$D' + r + ',$E:$E,"<>Liberado",$I:$I,"<>")>1)')}]},
      format: {backgroundColor: plRgb_(0.992, 0.882, 0.882), textFormat: {bold: true, foregroundColor: plRgb_(0.6, 0.098, 0.129)}}}}}});
  return tab;
}
function plSlots_(m, tab, first, from, count) {
  const req = m.req, sid = tab.sheetId;
  for (let i = 0; i < count; i++) {
    const n = from + i, r = first + 4 * i;
    plSet_(m, tab, r, PC.n, [n]);
    plSet_(m, tab, r, PC.image, [{f: plF_(m, '=IF(H' + r + '="","",IFERROR(IMAGE(H' + r + '),""))')}]);
    plSet_(m, tab, r + 1, PC.appearance, ['JUSTIFICATIVA / OBSERVAÇÃO   ·   campo interno da equipe']);
    plMerge_(req, sid, r, r + 3, 1, 1); plMerge_(req, sid, r, r + 3, 7, 7); plMerge_(req, sid, r, r + 3, 8, 8);
    plMerge_(req, sid, r + 1, r + 1, 2, 6); plMerge_(req, sid, r + 2, r + 3, 2, 6);
    plGroup_(req, sid, r + 2, r + 3, 2, true);
  }
  const last = first + 4 * count - 1;
  plFormat_(req, sid, first, last, 1, 1, {bg: PS.slot, ink: PS.slotInk, bold: true, size: 11, h: 'CENTER', v: 'TOP'});
  plFormat_(req, sid, first, last, 7, 8, {bg: PS.media, size: 9, h: 'CENTER'});
  plFormat_(req, sid, first, last, 9, 11, {wrap: 'CLIP'});
  plHeight_(req, sid, first, last, 32);
  for (let i = 0; i < count; i++) {
    const r = first + 4 * i;
    plFormat_(req, sid, r, r, 2, 2, {bold: true, ink: PS.purple});
    plFormat_(req, sid, r, r, 3, 5, {});
    plFormat_(req, sid, r, r, 6, 6, {h: 'CENTER', date: true});
    plFormat_(req, sid, r + 1, r + 1, 2, 6, {bg: PS.label, ink: PS.slotInk, bold: true, size: 9});
    plFormat_(req, sid, r + 2, r + 3, 2, 6, {bg: PS.justify, v: 'TOP'});
  }
  req.push({setDataValidation: {range: plRange_(sid, first, last, PC.status, PC.status), rule: {condition: {type: 'ONE_OF_LIST',
    values: PL.statuses.map(s => ({userEnteredValue: s}))}, strict: true, showCustomUi: true}}});
  // A validação vale para a coluna toda do trecho; as linhas de justificativa não usam E/F.
  req.push({setDataValidation: {range: plRange_(sid, first, last, PC.date, PC.date), rule: {condition: {type: 'DATE_IS_VALID'}, strict: true}}});
}
function plBlock_(m, owner, name) {
  // Uma guia por membro, com o nome de usuário dele.
  const tab = plNewTab_(m, name, owner), s = PL.firstBlock;
  const slots = PL.step, a = s + PL.head, z = a + 4 * slots, req = m.req, sid = tab.sheetId;
  plGrow_(m, tab, z);
  const A = 'A' + a + ':A' + z, at = col => col + a + ':' + col + z, M = 'MATCH(F' + (s + 1) + ',' + A + ',0)';
  const pick = col => 'INDEX(' + at(col) + ',' + M + ')';
  plSet_(m, tab, s, 1, [name || ('Membro ' + owner)]);
  plSet_(m, tab, s, 6, [{f: plF_(m, '=COUNTIFS(' + A + ',">=1",' + at('I') + ',"<>")&" / "&MAX(' + A + ')')}]);
  plSet_(m, tab, s, PC.mark, ['BLOCO:' + owner]);
  plSet_(m, tab, s + 1, 1, ['VISOR DO PERSONAGEM · consulta']);
  plSet_(m, tab, s + 1, 5, ['Escolher nº', 1]);
  plSet_(m, tab, s + 2, 1, [{f: plF_(m, '=IFERROR(' + pick('G') + ',"")')}]);
  plSet_(m, tab, s + 2, 3, [{f: plF_(m, '=IFERROR(IF(' + pick('B') + '="","Nenhuma aparência nesta posição",IF(' + pick('C') + '="",' + pick('B') + ',' + pick('C') + ')),"Escolha uma posição válida")')}]);
  plSet_(m, tab, s + 4, 3, [{f: plF_(m, '=IFERROR("Aparência: "&' + pick('B') + ',"")')}]);
  plSet_(m, tab, s + 5, 3, [{f: plF_(m, '=IFERROR("Obra: "&' + pick('D') + ',"")')}]);
  plSet_(m, tab, s + 6, 3, [{f: plF_(m, '=IFERROR("Situação: "&' + pick('E') + ',"")')}]);
  plSet_(m, tab, s + 7, 3, [{f: plF_(m, '=IFERROR("Cadastro: "&IF(' + pick('F') + '="","não informado",TEXT(' + pick('F') + ',"dd/mm/yyyy")),"")')}]);
  plSet_(m, tab, s + 8, 3, ['OBSERVAÇÃO / JUSTIFICATIVA · leitura']);
  plSet_(m, tab, s + 9, 3, [{f: plF_(m, '=IFERROR(IF(INDEX(' + at('B') + ',' + M + '+2)="","Sem observação / justificativa.",INDEX(' + at('B') + ',' + M + '+2)),"")')}]);
  plSet_(m, tab, s + 11, 1, PL.headers);
  plSet_(m, tab, s + 12, 1, ['POSIÇÕES   ·   abra o + ao lado de cada ficha para ver a justificativa']);
  plSet_(m, tab, z, PC.mark, ['FIM:' + owner]);
  plMerge_(req, sid, s, s, 1, 5); plMerge_(req, sid, s, s, 6, 7); plMerge_(req, sid, s + 1, s + 1, 1, 4); plMerge_(req, sid, s + 1, s + 1, 6, 7);
  plMerge_(req, sid, s + 2, s + 9, 1, 2); plMerge_(req, sid, s + 2, s + 3, 3, 7);
  for (let r = s + 4; r <= s + 9; r++) plMerge_(req, sid, r, r, 3, 7);
  plMerge_(req, sid, s + 12, s + 12, 1, 7);
  plFormat_(req, sid, s, s, 1, 7, {bg: PS.header, ink: PS.white, bold: true, size: 12});
  plFormat_(req, sid, s + 1, s + 1, 1, 5, {bg: PS.visor, ink: PS.purple, bold: true});
  plFormat_(req, sid, s + 1, s + 1, 6, 7, {bg: PS.pick, ink: PS.pickInk, bold: true, size: 12, h: 'CENTER'});
  plFormat_(req, sid, s + 2, s + 9, 1, 2, {bg: PS.photo, size: 11, h: 'CENTER'});
  plFormat_(req, sid, s + 2, s + 3, 3, 7, {bg: PS.name, ink: PS.purple, bold: true, size: 13});
  plFormat_(req, sid, s + 4, s + 7, 3, 7, {size: 11});
  plFormat_(req, sid, s + 8, s + 8, 3, 7, {bg: PS.visor, ink: PS.purple, bold: true});
  plFormat_(req, sid, s + 9, s + 9, 3, 7, {bg: PS.note, size: 11, v: 'TOP'});
  plFormat_(req, sid, s + 11, s + 11, 1, 10, {bg: PS.columns, ink: PS.white, bold: true});
  plFormat_(req, sid, s + 12, s + 12, 1, 7, {bg: PS.section, ink: PS.purple, bold: true, size: 9});
  plHeight_(req, sid, s, s, 44); plHeight_(req, sid, s + 1, s + 8, 32); plHeight_(req, sid, s + 9, s + 9, 96);
  plHeight_(req, sid, s + 10, s + 10, 12); plHeight_(req, sid, s + 11, s + 11, 44); plHeight_(req, sid, s + 12, s + 12, 32); plHeight_(req, sid, z, z, 24);
  req.push({setDataValidation: {range: plRange_(sid, s + 1, s + 1, 6, 6), rule: {condition: {type: 'NUMBER_BETWEEN',
    values: [{userEnteredValue: '1'}, {userEnteredValue: '10000'}]}, strict: true, inputMessage: 'Número da posição que o visor mostra.'}}});
  // O grupo do bloco vem antes dos grupos das posições (que ficam no nível 2) e inclui o
  // rodapé, então as linhas inseridas antes dele na expansão entram no grupo.
  plGroup_(req, sid, s + 1, z, 1, false);
  plSlots_(m, tab, a, 1, slots);
  return plBlocks_(m).find(b => b.owner === owner);
}
function plExpand_(m, b) {
  const footer = b.end, from = b.slots + 1;
  plInsert_(m, b.tab, footer, 4 * PL.step);
  plSlots_(m, b.tab, footer, from, PL.step);
  return plBlocks_(m).find(x => x.owner === b.owner);
}

// ---------------- aplicar mudanças vindas do bot ----------------
function plRecord_(r) {
  if (!r || typeof r !== 'object') plFail_('INVALID');
  if (typeof r.id !== 'string' || !/^AP-[0-9A-Za-z-]{8,64}$/.test(r.id) || !plSnowflake_(r.owner_id)) plFail_('INVALID');
  if (!PL.statuses.includes(r.status) || !Number.isInteger(r.revision) || r.revision < 1) plFail_('INVALID');
  const url = plText_(r.image_url || '', 1500);
  if (url && !/^https:\/\//i.test(url)) plFail_('INVALID');
  return {id: r.id, owner_id: r.owner_id, owner_name: plText_(r.owner_name || '', 100), appearance: plText_(r.appearance, 100),
    work: plText_(r.work, 100), server_name: plText_(r.server_name || '', 100), status: r.status,
    justification: plText_(r.justification || '', 2000), image_url: url, date: plSerial_(r.date), revision: r.revision};
}
function plClearSlot_(m, loc) {
  plSet_(m, loc.block.tab, loc.row, PC.appearance, ['', '', '', '', '']);
  plSet_(m, loc.block.tab, loc.row, PC.url, ['', '', '', '']);
  plSet_(m, loc.block.tab, loc.row + 2, PC.appearance, ['']);
}
function plUpsert_(m, op) {
  const r = plRecord_(op.record);
  const mine = plBlocks_(m).find(x => x.owner === r.owner_id);
  if (mine) plOwnerName_(m, mine, r.owner_name);
  let loc = plFind_(m, r.id);
  if (loc) {
    const stored = Number(loc.block.tab.grid[loc.row - 1][PC.mark - 1]) || 0;
    if (stored > r.revision) return 'stale';
    if (stored === r.revision) return 'ok';
    if (loc.block.owner !== r.owner_id) { plClearSlot_(m, loc); loc = null; }
  }
  let b = plBlocks_(m).find(x => x.owner === r.owner_id) || plBlock_(m, r.owner_id, r.owner_name);
  if (!loc) {
    let n = 0;
    for (let i = 1; i <= b.slots && !n; i++) if (!b.tab.grid[plSlotRow_(b, i) - 1][PC.id - 1]) n = i;
    if (!n) { b = plExpand_(m, b); n = b.slots - PL.step + 1; }
    loc = {block: b, row: plSlotRow_(b, n), n: n};
  }
  const tab = loc.block.tab;
  plSet_(m, tab, loc.row, PC.appearance, [r.appearance, r.server_name, r.work, r.status, r.date]);
  plSet_(m, tab, loc.row, PC.url, [r.image_url, r.id, r.owner_id, r.revision]);
  plSet_(m, tab, loc.row + 2, PC.appearance, [r.justification]);
  // Como a expansão por edição: perto do fim (2 posições livres), o bloco ganha mais 20.
  b = plBlocks_(m).find(x => x.owner === r.owner_id);
  if (b.slots - plUsed_(b) <= 2) plExpand_(m, b);
  return 'ok';
}
/** Nome do dono no cabeçalho e no título da guia (só quando a guia é dele sozinho). Vazio = o bot não achou o membro. */
function plOwnerName_(m, b, name) {
  if (!name) return;
  if (b.tab.grid[b.start - 1][0] !== name) plSet_(m, b.tab, b.start, 1, [name]);
  if (plBlocks_(m).filter(x => x.tab === b.tab).length !== 1) return;  // guia antiga com vários membros fica como está
  const title = plTabName_(m, name, b.owner, b.tab.name);
  if (title === b.tab.name) return;
  m.req.push({updateSheetProperties: {properties: {sheetId: b.tab.sheetId, title: title}, fields: 'title'}});
  m.names = m.names.map(x => x === b.tab.name ? title : x);
  b.tab.name = title;
}
function plClear_(m, op) {
  if (typeof op.id !== 'string' || !/^AP-[0-9A-Za-z-]{8,64}$/.test(op.id) || !Number.isInteger(op.revision)) plFail_('INVALID');
  const loc = plFind_(m, op.id);
  if (!loc) return 'ok';
  if ((Number(loc.block.tab.grid[loc.row - 1][PC.mark - 1]) || 0) > op.revision) return 'stale';
  plClearSlot_(m, loc);
  return 'ok';
}
function plImage_(m, op) {
  // Link de anexo do Discord expira e o bot renova: troca só o link, na mesma revisão.
  if (typeof op.id !== 'string' || !/^AP-[0-9A-Za-z-]{8,64}$/.test(op.id) || !Number.isInteger(op.revision)) plFail_('INVALID');
  const url = plText_(op.image_url || '', 1500);
  if (url && !/^https:\/\//i.test(url)) plFail_('INVALID');
  const loc = plFind_(m, op.id);
  if (!loc) return 'ok';
  if ((Number(loc.block.tab.grid[loc.row - 1][PC.mark - 1]) || 0) !== op.revision) return 'stale';
  if (loc.block.tab.grid[loc.row - 1][PC.url - 1] !== url) plSet_(m, loc.block.tab, loc.row, PC.url, [url]);
  return 'ok';
}
/** Planeja todas as operações sobre o modelo; devolve os pedidos da batch e o resultado de cada uma. */
function plPlan_(m, ops) {
  m.req = [];
  const results = ops.map(op => {
    const id = op && (op.id || (op.record && op.record.id)) || '';
    try {
      // A validação acontece antes de qualquer mudança, então uma operação inválida não deixa resto.
      if (op && op.op === 'upsert') return {id: id, status: plUpsert_(m, op)};
      if (op && op.op === 'clear') return {id: id, status: plClear_(m, op)};
      if (op && op.op === 'image') return {id: id, status: plImage_(m, op)};
      plFail_('INVALID');
    } catch (e) {
      if (e.plCode !== 'INVALID') throw e;
      return {id: id, status: 'invalid'};
    }
  });
  return {requests: m.req, results: results};
}

// ---------------- leitura e gravação reais ----------------
function plSpreadsheet_() {
  const id = plProps_().getProperty('PL_SS_ID');
  if (!id) plFail_('NOT_READY');
  return SpreadsheetApp.openById(id);
}
function plLoad_(ss) {
  const sheets = ss.getSheets(), all = sheets.map(s => ({name: s.getName(), sheetId: s.getSheetId(), rows: s.getMaxRows()}));
  const m = {sep: plProps_().getProperty('PL_SEP') || ';', tabs: [], names: all.map(t => t.name), nextSheetId: Math.max(1000, ...sheets.map(s => s.getSheetId() + 1))};
  const get = ranges => Sheets.Spreadsheets.Values.batchGet(ss.getId(), {ranges: ranges, valueRenderOption: 'FORMULA'}).valueRanges;
  // Guia de membro = tem o marcador BLOCO: na coluna K. Lê só K de todas e depois A:K das que são.
  const marks = all.length ? get(all.map(t => "'" + t.name.replace(/'/g, "''") + "'!K1:K" + t.rows)) : [];
  const tabs = all.filter((t, i) => (marks[i].values || []).some(l => String(l[0] || '').startsWith('BLOCO:')));
  if (tabs.length) {
    const res = get(tabs.map(t => "'" + t.name.replace(/'/g, "''") + "'!A1:K" + t.rows));
    tabs.forEach((t, i) => {
      const values = res[i].values || [];
      t.grid = Array.from({length: t.rows}, (_, r) => { const line = (values[r] || []).slice(0, PL.width); while (line.length < PL.width) line.push(''); return line; });
      m.tabs.push(t);
    });
  }
  return m;
}
function plCommit_(ss, requests) {
  for (let i = 0; i < requests.length; i += 4000) Sheets.Spreadsheets.batchUpdate({requests: requests.slice(i, i + 4000)}, ss.getId());
  SpreadsheetApp.flush();
}

// ---------------- Web App (assinado pelo bot) ----------------
function plOutput_(x) { return ContentService.createTextOutput(JSON.stringify(x)).setMimeType(ContentService.MimeType.JSON); }
function doGet() { return plOutput_({ok: false, code: 'AUTH'}); }
function doPost(e) {
  let lock;
  try {
    const raw = e && e.postData && e.postData.contents, p = plProps_();
    if (typeof raw !== 'string' || raw.length > PL.maxBody) plFail_('AUTH');
    let env, q;
    try { env = JSON.parse(raw); } catch (x) { plFail_('AUTH'); }
    const secret = p.getProperty('PL_SECRET');
    if (!secret || secret.length < 32 || typeof env.body !== 'string' || !/^[0-9a-f]{64}$/.test(String(env.sig))) plFail_('AUTH');
    if (!plEqual_(plHmac_(env.body, secret), env.sig)) plFail_('AUTH');
    try { q = JSON.parse(env.body); } catch (x) { plFail_('AUTH'); }
    // Assinatura já conferida: daqui pra frente o erro pode dizer o que está errado.
    if (q.v !== 1 || !Number.isInteger(q.ts)) plFail_('AUTH');
    if (Math.abs(Date.now() / 1000 - q.ts) > 300) plFail_('CLOCK');
    if (q.guild_id !== p.getProperty('PL_GUILD_ID')) plFail_('GUILD');
    if (!q.data || typeof q.data !== 'object' || Array.isArray(q.data)) plFail_('INVALID');
    lock = LockService.getScriptLock();
    if (!lock.tryLock(20000)) plFail_('BUSY');
    const ss = plSpreadsheet_();
    if (q.action === 'status') {
      const m = plLoad_(ss), blocks = plBlocks_(m);
      return plOutput_({ok: true, data: {version: PL.version, tabs: m.tabs.length, members: blocks.length,
        records: blocks.reduce((s, b) => s + plUsed_(b), 0)}});
    }
    if (q.action === 'apply') {
      const ops = q.data.ops;
      if (!Array.isArray(ops) || ops.length > PL.maxOps) plFail_('INVALID');
      const m = plLoad_(ss), plan = plPlan_(m, ops);
      plCommit_(ss, plan.requests);
      return plOutput_({ok: true, data: {results: plan.results}});
    }
    plFail_('INVALID');
  } catch (err) {
    const code = err.plCode || 'INTERNAL';
    console.error('ARQUIVISTA: ' + code + (code === 'INTERNAL' ? ' ' + err : ''));
    return plOutput_({ok: false, code: code});
  } finally { if (lock && lock.hasLock()) lock.releaseLock(); }
}

// ---------------- instalação e menu ----------------
function onOpen() {
  SpreadsheetApp.getUi().createMenu('Arquivista')
    .addItem('Instalar ou reinstalar', 'instalarArquivista')
    .addItem('Mostrar a chave da conexão', 'mostrarChaveArquivista')
    .addItem('Trocar a chave da conexão', 'trocarChaveArquivista')
    .addItem('Diagnóstico', 'diagnosticoArquivista').addToUi();
}
function plSeparator_(ss) {
  // Planilha com vírgula decimal (pt-BR) usa ; nas fórmulas. Descobre escrevendo 1,5 numa guia escondida.
  let sh = ss.getSheetByName('SISTEMA · ARQUIVISTA');
  if (!sh) { sh = ss.insertSheet('SISTEMA · ARQUIVISTA'); sh.hideSheet(); }
  const cell = sh.getRange('A1'); cell.setNumberFormat('0.0').setValue(1.5); SpreadsheetApp.flush();
  const sep = cell.getDisplayValue().indexOf(',') >= 0 ? ';' : ',';
  sh.getRange('A1:B2').setValues([['Separador de fórmulas', sep], ['Versão do script', PL.version]]);
  return sep;
}
function instalarArquivista() {
  const ss = SpreadsheetApp.getActiveSpreadsheet(), ui = SpreadsheetApp.getUi(), p = plProps_();
  if (!ss) throw new Error('Abra pela própria planilha: Extensões > Apps Script, com o script ligado a ela.');
  if (typeof Sheets === 'undefined') throw new Error('Adicione o serviço "Google Sheets API" em Serviços (+) no editor do Apps Script.');
  const current = p.getProperty('PL_GUILD_ID') || '';
  const answer = ui.prompt('Arquivista do Ciclo', 'ID do servidor Discord (clique com o botão direito no servidor > Copiar ID do servidor).' + (current ? '\nAtual: ' + current : ''), ui.ButtonSet.OK_CANCEL);
  if (answer.getSelectedButton() !== ui.Button.OK) return;
  const guild = answer.getResponseText().trim() || current;
  if (!plSnowflake_(guild)) { ui.alert('Esse ID não parece um ID de servidor do Discord.'); return; }
  p.setProperties({PL_SS_ID: ss.getId(), PL_GUILD_ID: guild, PL_SEP: plSeparator_(ss), PL_VERSION: PL.version});
  if (!p.getProperty('PL_SECRET')) p.setProperty('PL_SECRET', plNewSecret_());
  ui.alert('Arquivista instalado', 'Agora: Implantar > Nova implantação > App da Web (executar como você, acesso "Qualquer pessoa"). ' +
    'Copie a URL que termina em /exec.\n\nNo Discord, use /configurar > Planilha e cole a URL e esta chave:\n\n' + p.getProperty('PL_SECRET') +
    '\n\nNão mostre a chave para ninguém fora da staff.', ui.ButtonSet.OK);
}
function plNewSecret_() { return (Utilities.getUuid() + Utilities.getUuid()).replace(/-/g, ''); }
function mostrarChaveArquivista() {
  const s = plProps_().getProperty('PL_SECRET');
  SpreadsheetApp.getUi().alert('Chave da conexão', s ? s : 'Instale primeiro pelo menu Arquivista > Instalar.', SpreadsheetApp.getUi().ButtonSet.OK);
}
function trocarChaveArquivista() {
  const ui = SpreadsheetApp.getUi();
  if (ui.alert('Trocar a chave?', 'O bot para de gravar aqui até você colar a chave nova no /configurar.', ui.ButtonSet.YES_NO) !== ui.Button.YES) return;
  plProps_().setProperty('PL_SECRET', plNewSecret_());
  mostrarChaveArquivista();
}
function diagnosticoArquivista() {
  const p = plProps_(), ss = SpreadsheetApp.getActiveSpreadsheet(), m = plLoad_(ss), blocks = plBlocks_(m);
  const data = {versao: PL.version, servidor: p.getProperty('PL_GUILD_ID') || 'não instalado', guias: m.tabs.length,
    membros: blocks.length, cadastros: blocks.reduce((s, b) => s + plUsed_(b), 0), separador: m.sep};
  SpreadsheetApp.getUi().alert('Arquivista do Ciclo', JSON.stringify(data, null, 2), SpreadsheetApp.getUi().ButtonSet.OK);
}
