/**
 * Arquivista do Ciclo — planilha conectada v2.0.0 (o bot grava na planilha).
 *
 * Este script é fixo: ele só confere a assinatura do bot, lê a planilha e aplica os pedidos
 * que o bot mandar. Quem decide onde fica cada ficha e como ela aparece é o bot; melhorias
 * na planilha chegam atualizando o bot, sem colar este arquivo de novo.
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
 * Nesta versão, editar a planilha à mão NÃO volta para o bot.
 */
const PL = Object.freeze({
  version: '2.0.0', maxBody: 4000000, maxRanges: 500, maxRequests: 20000, system: 'SISTEMA · ARQUIVISTA',
  // Só o que o bot precisa para montar as guias. Nada que apague guias ou mexa em permissões.
  allowed: ['addSheet', 'updateSheetProperties', 'updateDimensionProperties', 'appendDimension', 'insertDimension',
    'addDimensionGroup', 'deleteDimensionGroup', 'updateDimensionGroup', 'updateCells', 'repeatCell', 'mergeCells',
    'updateBorders', 'addConditionalFormatRule', 'setDataValidation']
});

// ---------------- erros e utilitários ----------------
function plFail_(code) { const e = new Error(code); e.plCode = code; throw e; }
function plProps_() { return PropertiesService.getScriptProperties(); }
function plHex_(bytes) { return bytes.map(x => (x & 255).toString(16).padStart(2, '0')).join(''); }
function plHmac_(s, key) { return plHex_(Utilities.computeHmacSha256Signature(s, key, Utilities.Charset.UTF_8)); }
function plEqual_(a, b) { a = String(a); b = String(b); let d = a.length ^ b.length; for (let i = 0; i < Math.max(a.length, b.length); i++) d |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0); return d === 0; }
function plSnowflake_(s) { return typeof s === 'string' && /^[0-9]{17,20}$/.test(s); }
function plSpreadsheet_() {
  const id = plProps_().getProperty('PL_SS_ID');
  if (!id) plFail_('NOT_READY');
  return SpreadsheetApp.openById(id);
}
function plSheets_(ss) { return ss.getSheets().map(s => ({title: s.getName(), sheetId: s.getSheetId(), rows: s.getMaxRows()})); }

// ---------------- ações ----------------
function plRead_(ss, ranges) {
  if (!Array.isArray(ranges) || ranges.length > PL.maxRanges || ranges.some(r => typeof r !== 'string' || r.length > 300)) plFail_('INVALID');
  const out = [];
  for (let i = 0; i < ranges.length; i += 100) {
    const res = Sheets.Spreadsheets.Values.batchGet(ss.getId(), {ranges: ranges.slice(i, i + 100), valueRenderOption: 'FORMULA'}).valueRanges;
    res.forEach(r => out.push(r.values || []));
  }
  return out;
}
/** Todo sheetId citado num pedido, em qualquer profundidade. */
function plIds_(x, out) {
  if (Array.isArray(x)) x.forEach(y => plIds_(y, out));
  else if (x && typeof x === 'object') Object.keys(x).forEach(k => { if (k === 'sheetId') out.push(x[k]); else plIds_(x[k], out); });
  return out;
}
function plWrite_(ss, data) {
  const requests = data.requests, expect = data.expect;
  if (!Array.isArray(requests) || requests.length > PL.maxRequests || !Array.isArray(expect)) plFail_('INVALID');
  const sheets = plSheets_(ss), sys = sheets.find(s => s.title === PL.system);
  requests.forEach(q => {
    const keys = q && typeof q === 'object' ? Object.keys(q) : [];
    if (keys.length !== 1 || PL.allowed.indexOf(keys[0]) < 0) plFail_('INVALID');
  });
  if (sys && plIds_(requests, []).indexOf(sys.sheetId) >= 0) plFail_('INVALID');
  // O bot planejou em cima do que leu. Se alguém mexeu no tamanho ou no nome das guias nesse meio-tempo, ele lê de novo.
  expect.forEach(e => {
    const s = e && sheets.find(x => x.sheetId === e.sheetId);
    if (!s || s.rows !== e.rows || s.title !== e.title) plFail_('CHANGED');
  });
  if (requests.length) Sheets.Spreadsheets.batchUpdate({requests: requests}, ss.getId());
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
    if (q.action === 'status') return plOutput_({ok: true, data: {version: PL.version, sep: p.getProperty('PL_SEP') || ';', sheets: plSheets_(ss)}});
    if (q.action === 'read') return plOutput_({ok: true, data: {values: plRead_(ss, q.data.ranges)}});
    if (q.action === 'write') { plWrite_(ss, q.data); return plOutput_({ok: true, data: {}}); }
    // Bot antigo (planilha montada pelo script) pede "apply": avisa que o bot precisa ser atualizado.
    plFail_(q.action === 'apply' ? 'OLD_BOT' : 'INVALID');
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
  let sh = ss.getSheetByName(PL.system);
  if (!sh) { sh = ss.insertSheet(PL.system); sh.hideSheet(); }
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
  const p = plProps_(), ss = SpreadsheetApp.getActiveSpreadsheet();
  const data = {versao: PL.version, servidor: p.getProperty('PL_GUILD_ID') || 'não instalado', guias: ss.getSheets().length,
    separador: p.getProperty('PL_SEP') || ';', chave: p.getProperty('PL_SECRET') ? 'criada' : 'não criada'};
  SpreadsheetApp.getUi().alert('Arquivista do Ciclo', JSON.stringify(data, null, 2), SpreadsheetApp.getUi().ButtonSet.OK);
}
