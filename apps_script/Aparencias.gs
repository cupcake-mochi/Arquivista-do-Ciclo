/**
 * Ciclo Maldito — automação v1.2.0, compatibilidade com Arquivista.
 * APLICAR após terminar a ampliação e quando não houver execuções em andamento.
 * Preserva layout/estado v1.1; troca exclusão mútua por ScriptLock para uso no Web App.
 * instalarIntegracaoArquivista migra CM_* para ScriptProperties e ativa esta versão.
 * Base: automação v1.1.0, revisão do instalador.
 * SUBSTITUA somente o conteúdo do arquivo Aparencias.gs v1.0; não mantenha
 * duas definições de CM. Não apague outros módulos do projeto.
 * 1) Execute instalarCadastro. 2) Execute preparar100Membros.
 * A instalação NÃO repinta fichas nem cria centenas de proteções individualmente.
 * A ampliação é separada, retoma etapas salvas e usa gatilhos temporários.
 * Sem envio a serviços externos, sem implantação pública, sem mudança de compartilhamento.
 */
const CM = Object.freeze({
  id: '1SogJ4P5JjYrNL1KR1fIma5W6nWMRn2LZS28l6JMof4M',
  fichasId: 900120, membrosId: 900101, mapa: 'SISTEMA · MEMBROS',
  checagem: 'SISTEMA · CHECAGEM', estado: 'SISTEMA · REGISTROS',
  altura: 822, vagas: 200, membros: 100, ultimaLinhaMembros: 250,
  versao: '1.2.0', prefixo: 'CM · ', orcamentoMs: 110000, loteLegado: 20
});

// ---------------- instalação curta e retomável ----------------
function instalarCadastro() {
  const ss = cmPlanilha_(); cmExigirDono_(ss); cmExigirCompartilhamentoSeguro_();
  const props = cmProps_();
  if (!props.getProperty('CM_INSTALACAO_V11')) {
    props.setProperty('CM_INSTALACAO_V11', JSON.stringify({fase:'validar', iniciou:new Date().toISOString()}));
  }
  cmExecutarInstalacao_(ss);
}
function cmContinuarInstalacao() {
  cmApagarGatilhoTemporario_('cmContinuarInstalacao');
  cmExecutarInstalacao_(cmPlanilha_());
}
function cmExecutarInstalacao_(ss) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1500)) {
    console.log('Outra tarefa está usando a planilha; a instalação tentará novamente.');
    cmAgendar_('cmContinuarInstalacao'); return;
  }
  const props=cmProps_(), inicio=Date.now();
  let job=cmJson_(props.getProperty('CM_INSTALACAO_V11'));
  if (!job) { lock.releaseLock(); return; }
  try {
    while (Date.now()-inicio < CM.orcamentoMs) {
      console.log('INSTALAÇÃO · etapa: '+job.fase);
      props.setProperty('CM_INSTALACAO_V11',JSON.stringify(job));
      if (job.fase==='validar') {
        cmExigirDono_(ss); cmExigirCompartilhamentoSeguro_();
        const cap=cmDetectarCapacidade_(ss); cmValidarEstrutura_(ss,cap);
        props.setProperty('CM_MEMBROS_PRONTOS',String(cap));
        cmEstado_(ss); job.fase='membros';
      } else if (job.fase==='membros') {
        cmSincronizarMembros_(ss); job.fase='legado';
      } else if (job.fase==='legado') {
        const r=cmImportarLegado_(ss, inicio+CM.orcamentoMs);
        console.log('Legado regularizado neste lote: '+r.feitos+'; restante: '+r.restantes);
        if(r.restantes) { break; }
        job.fase='gatilhos';
      } else if (job.fase==='gatilhos') {
        cmInstalarGatilhos_(ss); job.fase='concluir';
      } else if (job.fase==='concluir') {
        props.setProperties({CM_VERSAO:CM.versao, CM_ATUALIZADO_EM:new Date().toISOString(),
          CM_ATIVADO_EM:props.getProperty('CM_ATIVADO_EM')||new Date().toISOString()});
        props.deleteProperty('CM_INSTALACAO_V11');
        cmApagarGatilhoTemporario_('cmContinuarInstalacao');
        props.deleteProperty('CM_ULTIMO_ERRO');
        ss.getSheetById(CM.fichasId).getRange('A2').setNote('AUTOMAÇÃO v1.2 ATIVA\nNovas fichas recebem ID e data. Datas de cadastros anteriores não são inventadas.\nVermelho: duplicidade de aparência + obra; amarelo: cadastro incompleto.\nO dono pode alterar áreas protegidas. Não mova células da estrutura.\nAmpliação para 100: tarefa separada; acompanhe no diagnóstico.');
        cmAoAbrir();
        console.log('INSTALAÇÃO CONCLUÍDA · v'+CM.versao);
        ss.toast('Automação v1.2 instalada. A ampliação para 100 é uma tarefa separada.', 'Cadastro de aparências',12);
        return;
      } else throw new Error('Etapa de instalação desconhecida. Consulte o diagnóstico.');
      props.setProperty('CM_INSTALACAO_V11',JSON.stringify(job));
    }
    props.setProperty('CM_INSTALACAO_V11',JSON.stringify(job));
    cmAgendar_('cmContinuarInstalacao');
    console.log('Progresso salvo. Continuação agendada; etapa pendente: '+job.fase);
  } catch(err) { cmErro_(ss,err); throw err; }
  finally { lock.releaseLock(); }
}
function cmInstalarGatilhos_(ss) {
  const todos=ScriptApp.getProjectTriggers();
  [['cmAoEditar','edit'],['cmAoAbrir','open'],['cmAoMudar','change']].forEach(([nome,tipo])=>{
    const ex=todos.filter(t=>t.getHandlerFunction()===nome && t.getTriggerSourceId()===ss.getId());
    if(!ex.length) {
      const b=ScriptApp.newTrigger(nome).forSpreadsheet(ss);
      if(tipo==='edit') b.onEdit().create(); else if(tipo==='open') b.onOpen().create(); else b.onChange().create();
    }
    ex.slice(1).forEach(t=>ScriptApp.deleteTrigger(t));
  });
}
function cmAoAbrir() {
  try { SpreadsheetApp.getUi().createMenu('Cadastro de aparências')
    .addItem('Ver diagnóstico / andamento','cmDiagnostico')
    .addItem('Diagnóstico do Arquivista','acDiagnostico')
    .addItem('Ordenar membros por nome','cmOrdenarMembros')
    .addItem('Revisar registros (dono)','cmRevisarCadastro')
    .addSeparator().addItem('Preparar 100 membros (dono)','preparar100Membros')
    .addItem('Continuar ampliação agora (dono)','continuarAmpliacao')
    .addItem('Pausar ampliação (dono)','pausarAmpliacao')
    .addSeparator().addItem('Proteção rígida opcional (dono)','ativarProtecaoRigida')
    .addItem('Remover apenas proteção rígida opcional','removerProtecaoRigida')
    .addItem('Testes de lógica','cmTestarLogica').addToUi();
  } catch(e) { console.log('Menu disponível após reabrir a planilha.'); }
}

// ---------------- identificação e registros ----------------
function cmPlanilha_() {
  const atual=SpreadsheetApp.getActiveSpreadsheet();
  if(atual && atual.getId()!==CM.id) throw new Error('Este módulo pertence à Planilha Aparências original.');
  return atual||SpreadsheetApp.openById(CM.id);
}
function cmExigirDono_(ss) {
  const owner=ss.getOwner();
  if(!owner || owner.getEmail()!==Session.getEffectiveUser().getEmail())
    throw new Error('Execute esta operação com a conta dona da planilha.');
}
function cmExigirCompartilhamentoSeguro_() {
  const f=DriveApp.getFileById(CM.id), a=f.getSharingAccess();
  if(a===DriveApp.Access.ANYONE || a===DriveApp.Access.ANYONE_WITH_LINK ||
     a===DriveApp.Access.DOMAIN || a===DriveApp.Access.DOMAIN_WITH_LINK)
    throw new Error('Use Compartilhar > Acesso geral > Restrito e convide apenas a equipe confiável.');
}
function cmJson_(s) { if(!s) return null; try{return JSON.parse(s);}catch(e){throw new Error('Progresso interno inválido; não apague os registros.');} }
function cmCapacidade_() {
  const n=Number(cmProps_().getProperty('CM_MEMBROS_PRONTOS'));
  return n===100?100:50;
}
function cmDetectarCapacidade_(ss) {
  if(cmProps_().getProperty('CM_AMPLIACAO_V11'))return cmCapacidade_();
  const f=ss.getSheetById(CM.fichasId);
  if(!f) throw new Error('FICHAS não encontrada.');
  if(f.getMaxRows()>=41104 && f.getRange('A40283').getDisplayValue() &&
     f.getRange('L40283').getDisplayValue() && Number(f.getRange('L41099').getValue())===200) return 100;
  return 50;
}
function cmValidarEstrutura_(ss,cap) {
  cap=cap||cmCapacidade_();
  const f=ss.getSheetById(CM.fichasId), mapa=ss.getSheetByName(CM.mapa);
  if(!f||!mapa||!ss.getSheetById(CM.membrosId)||!ss.getSheetByName(CM.checagem))
    throw new Error('Uma das abas esperadas não foi encontrada.');
  const expandindo=!!cmProps_().getProperty('CM_AMPLIACAO_V11');
  const rows=f.getMaxRows(), esperado=4+(cap/2)*CM.altura;
  if(f.getMaxColumns()!==23 || (rows!==esperado && !((expandindo||cap===50) && rows===41104)))
    throw new Error('A estrutura de linhas/colunas mudou. Desfaça a alteração estrutural antes de cadastrar.');
  // Poucas leituras sentinelas, não uma leitura por posição vazia.
  [[1,1],[1,51],[cap,200]].forEach(([m,n])=>{
    const a=cmEndereco_(m,n);
    if(Number(f.getRange(a.row,a.col).getValue())!==n) throw new Error('Numeração deslocada em '+cmLetra_(a.col)+a.row+'.');
  });
}
function cmSincronizarMembros_(ss) {
  const cap=cmCapacidade_(), sh=ss.getSheetById(CM.membrosId), mapa=ss.getSheetByName(CM.mapa);
  const rows=sh.getRange(4,1,Math.min(CM.ultimaLinhaMembros,sh.getMaxRows())-3,2).getDisplayValues();
  const atuais=mapa.getRange(2,1,cap,5).getDisplayValues();
  const vistos=new Set(), lista=[], index=new Map(), livres=[];
  rows.forEach((r,i)=>{
    const id=String(r[0]).trim(), nome=String(r[1]).trim();
    if(!id)return;
    if(!/^[0-9]{17,20}$/.test(id))throw new Error('ID Discord inválido em MEMBROS!A'+(i+4));
    if(vistos.has(id))throw new Error('ID Discord repetido em MEMBROS.'); vistos.add(id);
    if(nome)lista.push({id,nome});
  });
  atuais.forEach((r,i)=>{if(r[1]){if(index.has(r[1]))throw new Error('Vínculo técnico duplicado.');index.set(r[1],i);}else livres.push(i);});
  if(lista.filter(m=>!index.has(m.id)).length>livres.length)
    throw new Error('Os '+cap+' grupos preparados estão ocupados. Conclua a ampliação antes de novos vínculos.');
  let mudouId=false,mudouNome=false;
  lista.forEach(m=>{
    let i=index.get(m.id);
    if(i===undefined){i=livres.shift();atuais[i][1]=m.id;index.set(m.id,i);mudouId=true;}
    if(atuais[i][4]!==m.nome){atuais[i][4]=m.nome;mudouNome=true;}
  });
  if(mudouId)mapa.getRange(2,2,cap,1).setNumberFormat('@').setValues(atuais.map(r=>[r[1]]));
  if(mudouNome)mapa.getRange(2,5,cap,1).setValues(atuais.map(r=>[r[4]]));
}
function cmEstado_(ss) {
  let sh=ss.getSheetByName(CM.estado);
  if(!sh){sh=ss.insertSheet(CM.estado);sh.getRange(1,1,1,4).setValues([['ID registro','Data original','Legado sem data','Endereço']]);sh.hideSheet();cmProteger_(sh.protect(),CM.prefixo+'estado de registros');}
  const last=sh.getLastRow(), data=last>1?sh.getRange(2,1,last-1,4).getValues():[], map=new Map();
  data.forEach((r,i)=>{const id=String(r[0]||'');if(!id)return;if(map.has(id))throw new Error('ID repetido no histórico técnico.');map.set(id,{row:i+2,date:cmDataValida_(r[1])?r[1]:null,legado:r[2]===true,address:String(r[3]||'')});});
  return {sheet:sh,map,nextRow:Math.max(2,last+1),maxRows:sh.getMaxRows()};
}
function cmDataValida_(v){return v instanceof Date&&!Number.isNaN(v.getTime());}
function cmEscolherData_(anterior,atual,legado,agora){
  if(cmDataValida_(anterior))return {date:new Date(anterior.getTime()),legado:false};
  if(cmDataValida_(atual))return {date:new Date(atual.getTime()),legado:false};
  return legado?{date:null,legado:true}:{date:new Date(agora.getTime()),legado:false};
}
function cmProcessarRegistro_(f,a,state,legado) {
  const v=f.getRange(a.row,a.col,1,9).getValues(); const r=v[0];
  if(!String(r[1]||'').trim())return false;
  if(Number(r[0])!==a.n)throw new Error('A ficha '+a.n+' foi deslocada. Não mova linhas/células da estrutura.');
  const address=cmLetra_(a.col+1)+a.row, oldId=String(r[8]||'').trim();
  const anterior=oldId?state.map.get(oldId):null;
  if(anterior&&anterior.address&&anterior.address!==address)throw new Error('ID já vinculado a '+anterior.address+'. Use transferência controlada, não copie IDs.');
  if(r[5]!==''&&r[5]!==null&&!cmDataValida_(r[5]))throw new Error('Data inválida em '+cmLetra_(a.col+5)+a.row);
  const x=cmEscolherData_(anterior&&anterior.date,r[5],!!legado||(anterior?anterior.legado:!!oldId),new Date());
  const id=oldId||'AP-'+Utilities.getUuid();
  if(!oldId)f.getRange(a.row,a.col+8).setNumberFormat('@').setValue(id);
  if(x.date&&(!cmDataValida_(r[5])||r[5].getTime()!==x.date.getTime()))f.getRange(a.row,a.col+5).setValue(x.date).setNumberFormat('dd/MM/yyyy');
  const mudou=!anterior||anterior.address!==address||anterior.legado!==x.legado||
    (anterior.date?anterior.date.getTime():null)!==(x.date?x.date.getTime():null);
  if(mudou){
    const line=anterior?anterior.row:state.nextRow++;
    if(line>state.maxRows){state.sheet.insertRowsAfter(state.maxRows,500);state.maxRows+=500;}
    state.sheet.getRange(line,1,1,4).setValues([[id,x.date||'',x.legado,address]]);
    state.map.set(id,{row:line,date:x.date,legado:x.legado,address});
  }
  return mudou;
}
function cmLerIndice_(ss) {
  const sh=ss.getSheetByName(CM.checagem), out=[];
  // Páginas crescentes: um catálogo pequeno exige só uma leitura; um catálogo
  // cheio não gera 80 chamadas pequenas. No máximo seis leituras para 20 mil.
  let row=2,size=128;
  while(row<=sh.getMaxRows()){
    const count=Math.min(size,sh.getMaxRows()-row+1);
    const vals=sh.getRange(row,1,count,9).getValues();
    for(const r of vals){
      if(r[0]===''||r[0]===null)return out;
      if(typeof r[0]!=='number')throw new Error('O índice de checagem está com erro. Corrija as fórmulas antes de importar.');
      out.push(r);
    }
    row+=count;size=Math.min(8192,size*4);
  }
  return out;
}
function cmImportarLegado_(ss,deadline) {
  const state=cmEstado_(ss), idx=cmLerIndice_(ss), f=ss.getSheetById(CM.fichasId), seen=new Set();
  idx.forEach(r=>{const id=String(r[7]||'');if(id&&seen.has(id))throw new Error('Há IDs técnicos duplicados nas fichas.');if(id)seen.add(id);});
  const jobs=idx.filter(r=>{
    const st=state.map.get(String(r[7]||''));
    if(st&&st.address!==((Number(r[1])===1?'B':'M')+r[0]))throw new Error('Um ID técnico foi movido de sua ficha.');
    return !r[7]||!st;
  });
  let feitos=0;
  for(const r of jobs){
    if(feitos>=CM.loteLegado||Date.now()>deadline-10000)break;
    const m=2*Math.floor((Number(r[0])-5)/CM.altura)+Number(r[1]);
    cmProcessarRegistro_(f,cmEndereco_(m,Number(r[2])),state,true);feitos++;
  }
  return {feitos,restantes:jobs.length-feitos};
}
function cmAoEditar(e) {
  if(!e||!e.range||!e.source||e.source.getId()!==CM.id)return;
  const props=cmProps_();
  if(props.getProperty('CM_VERSAO')!==CM.versao)return;
  if(props.getProperty('CM_ESTRUTURA_ALERTA')){e.source.toast('Estrutura alterada: confira o diagnóstico antes de continuar.');return;}
  const sh=e.range.getSheet(), sid=sh.getSheetId();if(sid!==CM.fichasId&&sid!==CM.membrosId)return;
  const lock=LockService.getScriptLock();
  if(!lock.tryLock(10000)){props.setProperty('CM_REVISAO_NECESSARIA','Uma edição coincidiu com outra tarefa; revise seus dados e a data real.');e.source.toast('Outra tarefa em andamento. Confira o diagnóstico e revise este cadastro.');return;}
  try {
    if(sid===CM.membrosId){if(e.range.getColumn()<=2&&e.range.getLastRow()>=4)cmSincronizarMembros_(e.source);return;}
    const alvos=cmAlvosDaEdicao_(e.range.getRow(),e.range.getLastRow(),e.range.getColumn(),e.range.getLastColumn()).filter(a=>a.m<=cmCapacidade_());
    if(alvos.length>20){props.setProperty('CM_REVISAO_NECESSARIA','Colagem em mais de 20 fichas. Revise e informe datas reais.');throw new Error('Cole até 20 fichas por operação ou use a revisão de legado.');}
    if(!alvos.length)return;
    const state=cmEstado_(e.source);
    alvos.forEach(a=>cmProcessarRegistro_(sh,a,state,false));
    if(typeof acCapturarEdicao_==='function') acCapturarEdicao_(e.source,alvos,e);
  }catch(err){cmErro_(e.source,err);throw err;}finally{lock.releaseLock();}
}
function cmAoMudar(e) {
  if(!e||!e.source||e.source.getId()!==CM.id)return;
  if(!['INSERT_ROW','REMOVE_ROW','INSERT_COLUMN','REMOVE_COLUMN','REMOVE_GRID'].includes(e.changeType))return;
  try{cmValidarEstrutura_(e.source);}catch(err){
    cmProps_().setProperty('CM_ESTRUTURA_ALERTA',String(err.message));
    cmErro_(e.source,new Error('Alteração estrutural detectada. A automação foi pausada; desfaça a alteração e execute cmLiberarAposVerificacao.'));
  }
}
function cmLiberarAposVerificacao(){const ss=cmPlanilha_();cmExigirDono_(ss);cmValidarEstrutura_(ss);cmProps_().deleteProperty('CM_ESTRUTURA_ALERTA');ss.toast('Verificação básica aprovada; confira também os campos deslocados.');}
function cmRevisarCadastro(){
  const ss=cmPlanilha_();cmExigirDono_(ss);const l=LockService.getScriptLock();if(!l.tryLock(1500))throw new Error('Outra tarefa está ativa. Aguarde.');
  try{cmValidarEstrutura_(ss);cmSincronizarMembros_(ss);const r=cmImportarLegado_(ss,Date.now()+CM.orcamentoMs);console.log(JSON.stringify(r));ss.toast(r.restantes?'Progresso salvo. Execute a revisão novamente para continuar.':'Revisão de IDs concluída. Datas antigas desconhecidas continuam vazias.');}finally{l.releaseLock();}
}
function cmOrdenarMembros(){const ss=cmPlanilha_();ss.getSheetById(CM.membrosId).getRange(4,1,CM.ultimaLinhaMembros-3,2).sort({column:2,ascending:true});ss.toast('ID e nome ordenados juntos; grupos preservados.');}
function cmEndereco_(m,n){
  if(!Number.isInteger(m)||!Number.isInteger(n)||m<1||m>CM.membros||n<1||n>200)throw new Error('Posição fora dos limites.');
  const base=n<=5?18+4*(n-1):n<=50?39+4*(n-6):n<=100?221+4*(n-51):n<=150?423+4*(n-101):625+4*(n-151);
  return {m,n,row:base+822*Math.floor((m-1)/2),col:1+11*((m-1)%2)};
}
function cmAlvosDaEdicao_(r1,r2,c1,c2){
  const out=[];for(let p=Math.max(0,Math.floor((r1-5)/822));p<=Math.min(49,Math.floor((r2-5)/822));p++)for(let s=0;s<2;s++){
    if(c2<2+11*s||c1>8+11*s)continue;
    for(let n=1;n<=200;n++){const a=cmEndereco_(2*p+s+1,n);if(a.row<=r2&&a.row+3>=r1)out.push(a);}
  }return out;
}
function cmLetra_(n){let s='';for(;n>0;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
function cmNormalizar_(s){return String(s||'').replace(/\u00a0/g,' ').trim().replace(/ +/g,' ').toLowerCase();}
function cmChave_(a,o){a=cmNormalizar_(a);o=cmNormalizar_(o);return a&&o?a.length+':'+a+':'+o:'';}
function cmErro_(ss,e){console.error(e&&e.stack||String(e));cmProps_().setProperty('CM_ULTIMO_ERRO',new Date().toISOString()+' | '+String(e.message||e));ss.toast(String(e.message||e),'Cadastro: atenção',15);}
function cmAgendar_(nome){const ex=ScriptApp.getProjectTriggers().some(t=>t.getHandlerFunction()===nome);if(!ex)ScriptApp.newTrigger(nome).timeBased().after(60000).create();}
function cmApagarGatilhoTemporario_(nome){ScriptApp.getProjectTriggers().filter(t=>t.getHandlerFunction()===nome).forEach(t=>ScriptApp.deleteTrigger(t));}

// ---------------- ampliação separada para 100 membros ----------------
// Requer o serviço avançado "Google Sheets API" (identificador Sheets).
// Não depende do conector usado no chat. Opera na MESMA planilha original.
function cmExigirSheets_(){
  if(typeof Sheets==='undefined')throw new Error('No editor, em Serviços > +, adicione Google Sheets API (identificador Sheets). Depois execute novamente.');
}
function preparar100Membros(){
  const ss=cmPlanilha_();cmExigirDono_(ss);cmExigirCompartilhamentoSeguro_();cmExigirSheets_();
  const props=cmProps_();
  if(props.getProperty('CM_VERSAO')!==CM.versao)throw new Error('Conclua instalarCadastro v1.1 antes de ampliar.');
  if(cmCapacidade_()===100&&!props.getProperty('CM_AMPLIACAO_V11')){ss.toast('Os 100 membros já estão preparados.');return;}
  if(!props.getProperty('CM_AMPLIACAO_V11'))props.setProperty('CM_AMPLIACAO_V11',JSON.stringify({fase:'verificar',par:25,iniciou:new Date().toISOString()}));
  props.deleteProperty('CM_AMPLIACAO_PAUSADA');cmExecutarAmpliacao_(ss);
}
function continuarAmpliacao(){
  const ss=cmPlanilha_();cmExigirDono_(ss);cmExigirSheets_();
  cmProps_().deleteProperty('CM_AMPLIACAO_PAUSADA');
  cmExecutarAmpliacao_(ss);
}
function cmContinuarAmpliacao(){
  cmApagarGatilhoTemporario_('cmContinuarAmpliacao');
  if(cmProps_().getProperty('CM_AMPLIACAO_PAUSADA'))return;
  cmExecutarAmpliacao_(cmPlanilha_());
}
function pausarAmpliacao(){
  const ss=cmPlanilha_();cmExigirDono_(ss);
  cmProps_().setProperty('CM_AMPLIACAO_PAUSADA','1');
  cmApagarGatilhoTemporario_('cmContinuarAmpliacao');
  ss.toast('Próximas etapas pausadas. Uma etapa já em execução pode terminar. Use Continuar ampliação para retomar.');
}
function cmExecutarAmpliacao_(ss){
  cmExigirSheets_();const props=cmProps_();
  let job=cmJson_(props.getProperty('CM_AMPLIACAO_V11'));
  if(!job){ss.toast('Não há ampliação pendente.');return;}
  const l=LockService.getScriptLock();
  if(!l.tryLock(1500)){cmAgendar_('cmContinuarAmpliacao');return;}
  const inicio=Date.now();let unidades=0;
  try{
    cmExigirDono_(ss);
    // No máximo duas unidades grandes por execução, além do orçamento de tempo.
    while(Date.now()-inicio<CM.orcamentoMs && unidades<2){
      if(props.getProperty('CM_AMPLIACAO_PAUSADA'))return;
      console.log('AMPLIAÇÃO · '+job.fase+' · dupla '+(job.par+1)+' / 50');
      props.setProperty('CM_AMPLIACAO_V11',JSON.stringify(job));
      if(job.fase==='verificar'){
        cmValidarEstrutura_(ss,50);
        const f=ss.getSheetById(CM.fichasId),mapa=ss.getSheetByName(CM.mapa).getRange(2,2,50,1).getDisplayValues();
        // Escolhe uma dupla realmente vazia; não copia personagens reais.
        let source=-1;
        for(let p=24;p>=0;p--)if(!mapa[2*p][0]&&!mapa[2*p+1][0]&&cmBlocoSemDados_(f,p)){source=p;break;}
        if(source<0)throw new Error('Não há dupla-modelo completamente vazia entre os 50 grupos. A ampliação foi interrompida sem apagar dados.');
        job.source=source;job.fase='grade';
      }else if(job.fase==='grade'){
        const f=ss.getSheetById(CM.fichasId),mapa=ss.getSheetByName(CM.mapa),check=ss.getSheetByName(CM.checagem);
        if(f.getMaxRows()>41104)throw new Error('FICHAS tem linhas além do layout esperado. Não vou reduzir nem apagar linhas.');
        cmBatch_([{updateSheetProperties:{properties:{sheetId:CM.fichasId,gridProperties:{rowCount:41104}},fields:'gridProperties.rowCount'}},
          {updateSheetProperties:{properties:{sheetId:mapa.getSheetId(),gridProperties:{rowCount:Math.max(101,mapa.getMaxRows())}},fields:'gridProperties.rowCount'}},
          {updateSheetProperties:{properties:{sheetId:check.getSheetId(),gridProperties:{rowCount:Math.max(20002,check.getMaxRows())}},fields:'gridProperties.rowCount'}}]);
        job.fase='mapa';
      }else if(job.fase==='mapa'){
        const id=ss.getSheetByName(CM.mapa).getSheetId();let req=[];
        // B (Discord) e E (nome preservado) NÃO são sobrescritos em uma retomada.
        [0,2,3].forEach(col=>{
          const rows=[];for(let g=51;g<=100;g++){
            const formula=col===0?'=ROW()-1':col===2?'=5+822*QUOTIENT(A'+(g+1)+'-1;2)':'=IF(MOD(A'+(g+1)+';2)=1;"A";"L")';
            rows.push({values:[{userEnteredValue:{formulaValue:formula}}]});
          }
          req.push({updateCells:{start:{sheetId:id,rowIndex:51,columnIndex:col},rows,fields:'userEnteredValue'}});
        });cmBatch_(req);job.fase='modelos';
      }else if(job.fase==='modelos'){
        if(job.par>=50){job.fase='formulas';continue;}
        cmPrepararDupla_(ss,job.source,job.par);
        job.par++;if(job.par>=50)job.fase='formulas';
      }else if(job.fase==='formulas'){
        cmAmpliarFormulas_(ss);job.fase='protecao';job.protecaoPar=0;
      }else if(job.fase==='protecao'){
        // Completa proteções de TODOS os cabeçalhos com um batch por cinco duplas.
        cmCompletarProtecoesBatch_(ss,job.protecaoPar,Math.min(50,job.protecaoPar+5));
        job.protecaoPar+=5;if(job.protecaoPar>=50)job.fase='concluir';
      }else if(job.fase==='concluir'){
        cmValidarEstrutura_(ss,100);
        const f=ss.getSheetById(CM.fichasId);
        if(!f.getRange('A40283').getDisplayValue()||!f.getRange('L40283').getDisplayValue())throw new Error('Cabeçalhos finais ausentes.');
        props.setProperty('CM_MEMBROS_PRONTOS','100');
        cmSincronizarMembros_(ss);
        cmBatch_([cmCelula_(CM.fichasId,2,0,{stringValue:'Navegação: use MEMBROS. Capacidade: 100 membros · 200 posições por pessoa. Utilize os controles + / −.'})]);
        props.setProperty('CM_AMPLIADO_EM',new Date().toISOString());
        props.deleteProperty('CM_ULTIMO_ERRO');
        props.deleteProperty('CM_AMPLIACAO_V11');props.deleteProperty('CM_AMPLIACAO_PAUSADA');
        cmApagarGatilhoTemporario_('cmContinuarAmpliacao');
        console.log('AMPLIAÇÃO CONCLUÍDA · 100 membros / 20.000 posições');
        ss.toast('100 membros preparados. Cadastros anteriores preservados.', 'Cadastro de aparências',15);return;
      }else throw new Error('Etapa de ampliação desconhecida.');
      unidades++;props.setProperty('CM_AMPLIACAO_V11',JSON.stringify(job));
    }
    cmAgendar_('cmContinuarAmpliacao');
    console.log('Etapa salva. A próxima execução continuará de '+job.fase+'.');
  }catch(e){props.setProperty('CM_AMPLIACAO_PAUSADA','1');cmErro_(ss,e);throw e;}
  finally{l.releaseLock();}
}
function cmBlocoSemDados_(f,p){
  const h=5+822*p, vals=f.getRange(h,1,822,21).getValues();
  for(let s=0;s<2;s++)for(let n=1;n<=200;n++){
    const a=cmEndereco_(2*p+s+1,n),r=vals[a.row-h],c=a.col-1;
    // Dados, arquivo de imagem, link, ID e justificativa: qualquer conteúdo impede cópia.
    for(let k=1;k<=8;k++)if(r[c+k]!==''&&r[c+k]!==null)return false;
    if(vals[a.row-h+2][c+1]!==''&&vals[a.row-h+2][c+1]!==null)return false;
  }return true;
}
function cmPrepararDupla_(ss,source,p){
  const marker='CM11_PAR_'+String(p+1).padStart(3,'0')+'_PRONTO';
  const meta=Sheets.Spreadsheets.get(CM.id,{fields:'namedRanges(name),sheets(properties(sheetId),rowGroups)'});
  if((meta.namedRanges||[]).some(n=>n.name===marker)){
    console.log('Dupla '+(p+1)+' já gravada; não será copiada novamente.');return;
  }
  const f=ss.getSheetById(CM.fichasId);
  if(!cmBlocoSemDados_(f,source))throw new Error('A dupla-modelo foi preenchida durante a ampliação. Dados preservados; escolha um novo modelo antes de retomar.');
  if(!cmBlocoSemDados_(f,p))throw new Error('Há conteúdo na nova dupla '+(p+1)+'. Não vou sobrescrevê-lo.');
  const start=4+822*p,src=4+822*source, sid=CM.fichasId;
  const tentar=(req,rotulo)=>{
    for(let t=1;;t++){
      try{return cmBatch_(req);}
      catch(e){
        if(t>=3||!/unavailable|indispon|internal|backend|timed? ?out/i.test(String(e&&e.message||e)))throw e;
        console.log('Google ocupado em '+rotulo+'; nova tentativa '+(t+1)+'/3.');Utilities.sleep(4000*t);
      }
    }
  };
  // Os arrays dos IDs de responsáveis J e U continuam fora da cópia.
  const trechos=[[0,34],[34,215],[215,417],[417,619],[619,822]];
  [[0,9],[11,20]].forEach(([c1,c2])=>trechos.forEach(([a,b])=>{
    tentar([{copyPaste:{source:cmRange_(sid,src+a,src+b,c1,c2),destination:cmRange_(sid,start+a,start+b,c1,c2),pasteType:'PASTE_NORMAL'}}],
      'dupla '+(p+1)+' · linhas '+a+'-'+b+' · colunas '+c1+'-'+c2);
  }));
  const req=[];
  const h=(a,b,size)=>req.push({updateDimensionProperties:{range:{sheetId:sid,dimension:'ROWS',startIndex:start+a,endIndex:start+b},properties:{pixelSize:size},fields:'pixelSize'}});
  h(0,822,29);h(0,1,38);h(1,10,32);h(9,10,96);h(10,11,12);
  [11,33,215,417,619].forEach((x,i)=>h(x,x+1,i===1?48:44));
  const existentes=(meta.sheets||[]).find(x=>x.properties.sheetId===sid);
  const groups=existentes&&existentes.rowGroups||[];
  const add=(a,b,depth)=>{
    const range={sheetId:sid,dimension:'ROWS',startIndex:start+a,endIndex:start+b};
    const ex=groups.some(g=>g.depth===depth&&g.range.startIndex===range.startIndex&&g.range.endIndex===range.endIndex);
    if(!ex)req.push({addDimensionGroup:{range}});
    req.push({updateDimensionGroup:{dimensionGroup:{range,depth,collapsed:true},fields:'collapsed'}});
  };
  // Agrupamento do membro + expansões de 50 e justificativas das cinco fichas iniciais.
  add(1,820,1);
  [[34,214],[215,416],[417,618],[619,820]].forEach(([a,b])=>add(a,b,2));
  for(let n=1;n<=5;n++){const r=cmEndereco_(2*p+1,n).row-1;add(r-start+2,r-start+4,2);}
  req.push({updateSheetProperties:{properties:{sheetId:sid,gridProperties:{rowGroupControlAfter:false}},fields:'gridProperties.rowGroupControlAfter'}});
  // O marcador vai no MESMO batch final: sem ele, a retomada refaz a cópia (que é segura).
  req.push({addNamedRange:{namedRange:{name:marker,range:cmRange_(sid,start,start+1,0,1)}}});
  tentar(req,'dupla '+(p+1)+' · alturas, grupos e marcador');
}
function cmAmpliarFormulas_(ss){
  const sid=CM.fichasId,check=ss.getSheetByName(CM.checagem).getSheetId(),req=[];
  const head='=LET(g;1+2*QUOTIENT(ROW()-5;822)+QUOTIENT(COLUMN()-1;11);id;INDEX(\'SISTEMA · MEMBROS\'!$B$2:$B$101;g);IF(id="";"MEMBRO "&TEXT(g;"00");IFERROR(INDEX(MEMBROS!$B$4:$B$250;MATCH(id;MEMBROS!$A$4:$A$250;0));INDEX(\'SISTEMA · MEMBROS\'!$E$2:$E$101;g)&" · perfil não localizado")))';
  for(let p=0;p<50;p++)[0,11].forEach(c=>req.push(cmCelula_(sid,4+822*p,c,{formulaValue:head})));
  const own=(a,b,g)=>'=ARRAYFORMULA(IF(ISNUMBER('+a+'18:'+a+'41104)*('+b+'18:'+b+'41104<>"");IFNA(VLOOKUP('+g+'+2*QUOTIENT(ROW('+a+'18:'+a+'41104)-5;822);\'SISTEMA · MEMBROS\'!A2:B101;2;FALSE);"");""))';
  req.push(cmCelula_(sid,17,9,{formulaValue:own('A','B',1)}),cmCelula_(sid,17,20,{formulaValue:own('L','M',2)}));
  const block=(s)=>{
    const c=s===1?['A','B','D','E','J','I','C']:['L','M','O','P','U','T','N'];
    return 'HSTACK(SEQUENCE(41085;1;18;1);ARRAYFORMULA(IF(ROW(FICHAS!'+c[0]+'18:'+c[0]+'41102)>0;'+s+';'+s+'));'+c.map(x=>'FICHAS!'+x+'18:'+x+'41102').join(';')+')';
  };
  req.push(cmCelula_(check,1,0,{formulaValue:'=IFERROR(LET(d;VSTACK('+block(1)+';'+block(2)+');FILTER(d;ISNUMBER(CHOOSECOLS(d;3));CHOOSECOLS(d;4)<>""));"")'}));
  const extras={
    9:'=ARRAYFORMULA(LET(a;LOWER(TRIM(SUBSTITUTE(D2:D20001;CHAR(160);" ")));o;LOWER(TRIM(SUBSTITUTE(E2:E20001;CHAR(160);" ")));IF((a="")+(o="");"";LEN(a)&":"&a&":"&o)))',
    10:'=ARRAYFORMULA(IF(D2:D20001="";"";LOWER(TRIM(F2:F20001))<>"liberado"))',
    11:'=ARRAYFORMULA(IF(D2:D20001="";"";IF(J2:J20001="";FALSE;K2:K20001*(IFNA(VLOOKUP(J2:J20001;$P$2:$Q$20002;2;FALSE);0)>1)>0)))',
    12:'=ARRAYFORMULA(IF(D2:D20001="";"";((TRIM(E2:E20001)="")+(TRIM(F2:F20001)="")+(REGEXMATCH(TO_TEXT(G2:G20001);"^[0-9]{17,20}$")=FALSE))>0))',
    13:'=ARRAYFORMULA(IF(D2:D20001="";"";2*N(L2:L20001)+N(M2:M20001)))',
    15:'=IFERROR(QUERY(FILTER(J2:J20001;J2:J20001<>"";K2:K20001=TRUE);"select Col1,count(Col1) group by Col1 label Col1 \'\',count(Col1) \'\'";0);"")'
  };
  Object.keys(extras).forEach(c=>req.push(cmCelula_(check,1,Number(c),{formulaValue:extras[c]})));
  ['A','L'].forEach((c,i)=>req.push(cmCelula_(sid,1,21+i,{formulaValue:'=ARRAYFORMULA(IFNA(VLOOKUP(ROW('+c+'2:'+c+'41104);FILTER(HSTACK(\'SISTEMA · CHECAGEM\'!A2:A20001;\'SISTEMA · CHECAGEM\'!N2:N20001);\'SISTEMA · CHECAGEM\'!B2:B20001='+(i+1)+');2;FALSE);0))'})));
  const rows=[];
  for(let r=4;r<=250;r++){
    const count='=IF($A'+r+'="";"";IFERROR(LET(g;MATCH($A'+r+';\'SISTEMA · MEMBROS\'!$B$2:$B$101;0);VALUE(REGEXEXTRACT(INDEX(FICHAS!$F$5:$Q$40283;1+822*QUOTIENT(g-1;2);IF(MOD(g;2)=1;1;12));"^[0-9]+")));"Aguardando vínculo"))';
    const link='=IF($A'+r+'="";IF(ROW()<=103;HYPERLINK("#gid=900120&range="&IF(MOD(ROW()-4;2)=0;"A";"L")&(5+822*QUOTIENT(ROW()-4;2));"Abrir · grupo "&TEXT(ROW()-3;"00"));"");IFERROR(LET(g;MATCH($A'+r+';\'SISTEMA · MEMBROS\'!$B$2:$B$101;0);HYPERLINK("#gid=900120&range="&IF(MOD(g;2)=1;"A";"L")&(5+822*QUOTIENT(g-1;2));"Abrir · "&$B'+r+'));"Aguardando vínculo"))';
    rows.push({values:[{userEnteredValue:{formulaValue:count}},{userEnteredValue:{formulaValue:link}}]});
  }
  req.push({updateCells:{start:{sheetId:CM.membrosId,rowIndex:3,columnIndex:2},rows,fields:'userEnteredValue'}});
  const meta=Sheets.Spreadsheets.get(CM.id,{fields:'sheets(properties(sheetId),conditionalFormats)'});
  const rules=(meta.sheets.find(s=>s.properties.sheetId===sid)||{}).conditionalFormats||[];
  // Mantém as regras existentes e expande seus limites, sem apagar alterações da staff.
  rules.forEach((rule,index)=>{
    let changed=false;rule.ranges.forEach(r=>{if(r.endRowIndex===20554||r.endRowIndex===20552){r.endRowIndex=r.endRowIndex===20554?41104:41102;changed=true;}});
    if(changed)req.push({updateConditionalFormatRule:{sheetId:sid,index,rule}});
  });
  rules.map((r,i)=>({r,i})).filter(x=>String(x.r.booleanRule&&x.r.booleanRule.condition&&x.r.booleanRule.condition.values&&x.r.booleanRule.condition.values[0]&&x.r.booleanRule.condition.values[0].userEnteredValue||'').includes('MOD(ROW()-8;4)=0')).reverse().forEach(x=>req.push({deleteConditionalFormatRule:{sheetId:sid,index:x.i}}));
  cmBatch_(req);
}
function cmCompletarProtecoesBatch_(ss,inicio,fim){
  const meta=Sheets.Spreadsheets.get(CM.id,{fields:'sheets(properties(sheetId),protectedRanges(description))'});
  const existentes=new Set((meta.sheets.find(s=>s.properties.sheetId===CM.fichasId).protectedRanges||[]).map(p=>p.description));
  const owner=ss.getOwner().getEmail(),req=[];
  const add=(range,description)=>{if(!existentes.has(description))req.push({addProtectedRange:{protectedRange:{range,description,warningOnly:false,editors:{users:[owner]}}}});};
  for(let p=inicio;p<fim;p++){
    const h=4+822*p;
    [[5,'DATA DO CADASTRO — v1.1\nNovas fichas recebem a data automaticamente após a instalação. A data original é preservada. Cadastros antigos sem data não recebem uma data inventada. Não use HOJE() ou AGORA().'],[8,'ID PERMANENTE — v1.1\nGerado pela automação. Não copiar, reutilizar ou editar.'],[3,'OBRA DE ORIGEM\nInforme a obra da aparência. A combinação aparência + obra é verificada automaticamente; Arquivado continua ocupado, Liberado não.']].forEach(([c,note])=>[0,11].forEach(offset=>req.push({repeatCell:{range:cmRange_(CM.fichasId,h+13,h+820,c+offset,c+offset+1),cell:{note},fields:'note'}})));
    add(cmRange_(CM.fichasId,h,h+1,0,18),CM.prefixo+'cabeçalho '+String(p+1).padStart(2,'0'));
    add(cmRange_(CM.fichasId,h+2,h+10,0,18),CM.prefixo+'visor '+String(p+1).padStart(2,'0'));
    [16,38,220,422,624].forEach(r=>add(cmRange_(CM.fichasId,r-1+822*p,r+822*p,0,21),CM.prefixo+'índice '+(r+822*p)));
  }
  if(inicio===0){
    add({sheetId:CM.fichasId,startColumnIndex:0,endColumnIndex:1},CM.prefixo+'numeração e âncoras esquerdas');
    add({sheetId:CM.fichasId,startColumnIndex:11,endColumnIndex:12},CM.prefixo+'numeração e âncoras direitas');
    add({sheetId:CM.fichasId,startColumnIndex:8,endColumnIndex:10},CM.prefixo+'IDs de registros e responsáveis esquerdos');
    add({sheetId:CM.fichasId,startColumnIndex:19,endColumnIndex:23},CM.prefixo+'IDs direitos e alertas automáticos');
  }
  if(req.length)cmBatch_(req);
}
function cmRange_(sheetId,startRowIndex,endRowIndex,startColumnIndex,endColumnIndex){return {sheetId,startRowIndex,endRowIndex,startColumnIndex,endColumnIndex};}
function cmCelula_(sheetId,rowIndex,columnIndex,value){return {updateCells:{start:{sheetId,rowIndex,columnIndex},rows:[{values:[{userEnteredValue:value}]}],fields:'userEnteredValue'}};}
function cmBatch_(requests){cmExigirSheets_();return Sheets.Spreadsheets.batchUpdate({requests,includeSpreadsheetInResponse:false},CM.id);}

// ---------------- proteção: limites explícitos ----------------
function cmProteger_(p,desc){
  p.setDescription(desc).setWarningOnly(false);const me=Session.getEffectiveUser();p.addEditor(me);
  const others=p.getEditors().filter(u=>u.getEmail()!==me.getEmail());if(others.length)p.removeEditors(others);
  if(p.canDomainEdit())p.setDomainEdit(false);return p;
}
function ativarProtecaoRigida(){
  const ss=cmPlanilha_();cmExigirDono_(ss);cmExigirSheets_();
  const ui=SpreadsheetApp.getUi();
  const resposta=ui.alert('Proteção rígida opcional',
    'Bloqueia a folha e libera somente áreas de preenchimento e seletores. Pode impedir que outras contas operem os agrupamentos +/−. Teste com uma conta da staff; para voltar, use Remover apenas proteção rígida opcional. O dono sempre pode editar e células liberadas ainda podem ser recortadas entre si. Ativar?',ui.ButtonSet.YES_NO);
  if(resposta!==ui.Button.YES)return;
  const cap=cmCapacidade_(),sheetId=CM.fichasId,unprotectedRanges=[];
  for(let m=1;m<=cap;m++){
    const p=Math.floor((m-1)/2),c=11*((m-1)%2),h=4+822*p;
    unprotectedRanges.push(cmRange_(sheetId,h+1,h+2,c+5,c+7));
    [[18,37],[39,218],[221,420],[423,622],[625,824]].forEach(([a,b])=>unprotectedRanges.push(cmRange_(sheetId,a-1+822*p,b+822*p,c+1,c+8)));
  }
  const desc=CM.prefixo+'folha rígida opcional v1.1',meta=Sheets.Spreadsheets.get(CM.id,{fields:'sheets(properties(sheetId),protectedRanges(protectedRangeId,description))'});
  const old=(meta.sheets.find(s=>s.properties.sheetId===sheetId).protectedRanges||[]).find(p=>p.description===desc);
  const protectedRange={range:{sheetId},description:desc,warningOnly:false,unprotectedRanges,editors:{users:[ss.getOwner().getEmail()]}};
  cmBatch_([old?{updateProtectedRange:{protectedRange:Object.assign({protectedRangeId:old.protectedRangeId},protectedRange),fields:'range,description,warningOnly,unprotectedRanges,editors'}}:{addProtectedRange:{protectedRange}}]);
  ss.toast('Proteção rígida ativada. Confira os +/− com outra conta antes de adotar esse modo.');
}
function removerProtecaoRigida(){
  const ss=cmPlanilha_();cmExigirDono_(ss);cmExigirSheets_();
  const meta=Sheets.Spreadsheets.get(CM.id,{fields:'sheets(properties(sheetId),protectedRanges(protectedRangeId,description))'});
  const p=(meta.sheets.find(s=>s.properties.sheetId===CM.fichasId).protectedRanges||[]).find(x=>x.description===CM.prefixo+'folha rígida opcional v1.1');
  if(p)cmBatch_([{deleteProtectedRange:{protectedRangeId:p.protectedRangeId}}]);
  ss.toast('Apenas o modo rígido opcional foi removido. Proteções das partes automáticas preservadas.');
}

// ---------------- diagnóstico e testes ----------------
function cmDiagnostico(){
  const ss=cmPlanilha_(),p=cmProps_(),job=cmJson_(p.getProperty('CM_AMPLIACAO_V11')),
    install=cmJson_(p.getProperty('CM_INSTALACAO_V11'));
  const texto=[
    'Código: v'+CM.versao,
    'Versão ativada: '+(p.getProperty('CM_VERSAO')||'não instalada'),
    'Instalação: '+(install?'pendente — '+install.fase:'sem etapa pendente'),
    'Grupos prontos: '+cmCapacidade_()+' de 100',
    'Ampliação: '+(job?job.fase+' · duplas preparadas até '+job.par+'/50':'sem etapa pendente'),
    'Ampliação pausada: '+(p.getProperty('CM_AMPLIACAO_PAUSADA')?'sim':'não'),
    'Estrutura: '+(p.getProperty('CM_ESTRUTURA_ALERTA')||'sem alerta registrado'),
    'Revisão: '+(p.getProperty('CM_REVISAO_NECESSARIA')||'sem pendência registrada'),
    'Último erro registrado: '+(p.getProperty('CM_ULTIMO_ERRO')||'nenhum'),
    'Não há garantia de bloqueio de arrastar dentro de células editáveis. O dono não é bloqueado.'
  ].join('\n');
  console.log(texto);SpreadsheetApp.getUi().alert('Cadastro de aparências',texto,SpreadsheetApp.getUi().ButtonSet.OK);
}
function cmTestarLogica(){
  let ok=0;const check=(x,msg)=>{if(!x)throw new Error('Teste falhou: '+msg);ok++;};const seen=new Set();
  for(let m=1;m<=100;m++)for(let n=1;n<=200;n++){
    const a=cmEndereco_(m,n),k=a.row+':'+a.col;check(!seen.has(k),'endereço único');seen.add(k);check(a.row+3<=41104,'limite');
  }
  [[1,1],[1,5],[1,6],[1,50],[1,51],[1,100],[1,101],[1,150],[1,151],[100,200]].forEach(([m,n])=>{
    const a=cmEndereco_(m,n),xs=cmAlvosDaEdicao_(a.row+2,a.row+2,a.col+1,a.col+1);check(xs.length===1&&xs[0].m===m&&xs[0].n===n,'justificativa');
  });
  check(cmEndereco_(100,200).row===41099,'última ficha');check(cmAlvosDaEdicao_(6,6,6,6).length===0,'seletor');
  check(cmChave_('  TAKAO  ',' AZUR   LANE ')===cmChave_('Takao','Azur Lane'),'normalização');
  check(cmChave_('ab','c')!==cmChave_('a','bc'),'colisão');
  const old=new Date('2025-01-01T15:00:00Z'),now=new Date('2026-10-19T15:00:00Z');
  check(cmEscolherData_(old,now,false,now).date.getTime()===old.getTime(),'preserva data');
  check(cmEscolherData_(null,null,true,now).date===null,'legado');check(cmEscolherData_(null,null,false,now).date.getTime()===now.getTime(),'nova data');
  const result={aprovados:ok,posicoes:seen.size,escopo:'lógica; não substitui execução no Google ou teste por outra conta'};
  console.log(JSON.stringify(result));return result;
}

// Compatibilidade antes/depois da migração. Nunca depende de DocumentLock no Web App.
function cmProps_(){
  const p=PropertiesService.getScriptProperties();
  if(p.getProperty('CM_USAR_SCRIPT_PROPERTIES')==='1')return p;
  const old=PropertiesService.getDocumentProperties();
  if(!old)throw new Error('Execute instalarIntegracaoArquivista no editor antes de usar a ponte.');
  return old;
}
