/**
 * Arquivista do Ciclo — ponte autenticada v0.2.0.
 * ADICIONE como arquivo separado no MESMO projeto de Aparencias.gs.
 * Requer a versão de Aparencias.gs deste pacote (lock e propriedades compartilhados).
 * A planilha continua RESTRITA. A URL Web App rejeita pedidos sem HMAC válido.
 * Nunca coloque o token Discord aqui. AC_SECRET pertence às Propriedades do script.
 */
const AC = Object.freeze({version:'0.2.0', events:'SISTEMA · AC EVENTOS',
  requests:'SISTEMA · AC PEDIDOS', snapshots:'SISTEMA · AC SNAPSHOTS', maxBody:24000,
  statuses:['Em preparação','Em uso','Arquivado','Liberado']});

function acFail_(code){const e=new Error(code);e.acCode=code;throw e;}
function acJson_(x){try{return JSON.parse(x);}catch(e){acFail_('INVALID');}}
function acProps_(){return PropertiesService.getScriptProperties();}
function acHash_(s){return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,String(s),Utilities.Charset.UTF_8).map(x=>(x&255).toString(16).padStart(2,'0')).join('');}
function acHmac_(s,key){return Utilities.computeHmacSha256Signature(s,key,Utilities.Charset.UTF_8).map(x=>(x&255).toString(16).padStart(2,'0')).join('');}
function acEqual_(a,b){a=String(a);b=String(b);let diff=a.length^b.length;for(let i=0;i<Math.max(a.length,b.length);i++)diff|=(a.charCodeAt(i)||0)^(b.charCodeAt(i)||0);return diff===0;}
function acId_(s){return typeof s==='string'&&/^[0-9]{17,20}$/.test(s);}
function acText_(v,max,required){if(typeof v!=='string'||v.length>max||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(v))acFail_('INVALID');v=v.trim();if(required&&!v)acFail_('INVALID');return v;}
function acUrl_(v){v=acText_(v,1500,false);if(!v)return '';const m=/^https:\/\/([^\/?#]+)([^\s]*)$/i.exec(v);if(!m||m[1].includes('@')||m[1].includes(':')||!m[1].includes('.'))acFail_('INVALID');const h=m[1].toLowerCase().replace(/\.$/,'');if(/(^|\.)(localhost|local|internal)$/.test(h)||/^[0-9.]+$/.test(h)||(h==='discord.com'&&v.includes('/api/webhooks/')))acFail_('INVALID');return v;}
function acMedia_(v){if(!v)return '';if(typeof v!=='string'||!/^discord:\/\/[0-9]{17,20}\/[0-9]{17,20}\/[0-9]{17,20}\/[0-9]{17,20}$/.test(v))acFail_('INVALID');if(v.split('/')[2]!==acProps_().getProperty('AC_GUILD_ID'))acFail_('INVALID');return v;}
function acOutput_(x){return ContentService.createTextOutput(JSON.stringify(x)).setMimeType(ContentService.MimeType.JSON);}
function doGet(){return acOutput_({ok:false,code:'AUTH'});}
function doPost(e){
  let l;
  try{
    const raw=e&&e.postData&&e.postData.contents;
    if(typeof raw!=='string'||raw.length>AC.maxBody)acFail_('AUTH');
    const env=acJson_(raw),secret=acProps_().getProperty('AC_SECRET');
    if(!secret||secret.length<32||typeof env.body!=='string'||!/^[0-9a-f]{64}$/.test(String(env.sig)))acFail_('AUTH');
    if(!acEqual_(acHmac_(env.body,secret),env.sig))acFail_('AUTH');
    const q=acJson_(env.body);
    if(q.v!==1||!Number.isInteger(q.ts)||Math.abs(Date.now()/1000-q.ts)>300||q.guild_id!==acProps_().getProperty('AC_GUILD_ID'))acFail_('AUTH');
    if(!q.actor||!acId_(q.actor.id)||typeof q.actor.staff!=='boolean'||typeof q.request_id!=='string'||!/^[A-Za-z0-9_.:-]{8,100}$/.test(q.request_id))acFail_('AUTH');
    if(!q.data||typeof q.data!=='object'||Array.isArray(q.data))acFail_('INVALID');
    if(acProps_().getProperty('AC_ATIVO')!=='1')acFail_('NOT_READY');
    l=LockService.getScriptLock();if(!l.tryLock(4000))acFail_('BUSY');
    const ss=SpreadsheetApp.openById(CM.id);
    const result=acDispatch_(ss,q);
    return acOutput_({ok:true,data:result});
  }catch(err){
    const code=err.acCode||'INTERNAL';
    // Sem corpo, assinaturas, URLs privadas ou dados de personagens nos logs.
    console.error('ARQUIVISTA: '+code);
    if(code==='INTERNAL')acProps_().setProperty('AC_ULTIMO_ERRO',new Date().toISOString()+' | falha interna; confira a estrutura e permissões');
    return acOutput_({ok:false,code:code});
  }finally{if(l&&l.hasLock())l.releaseLock();}
}

/** Execute como dono, apenas DEPOIS que a ampliação terminar. Repetível. */
function instalarIntegracaoArquivista(){
  const ss=cmPlanilha_();cmExigirDono_(ss);cmExigirCompartilhamentoSeguro_();cmExigirSheets_();
  const l=LockService.getScriptLock();if(!l.tryLock(1500))throw new Error('Há outra tarefa rodando. Aguarde.');
  try{
    const sp=acProps_(),dp=PropertiesService.getDocumentProperties();
    const original=sp.getProperty('CM_USAR_SCRIPT_PROPERTIES')==='1'?sp:dp;
    if(!original||!original.getProperty('CM_VERSAO'))throw new Error('Conclua a instalação original primeiro.');
    ['CM_AMPLIACAO_V11','CM_INSTALACAO_V11','CM_ESTRUTURA_ALERTA'].forEach(k=>{if(original.getProperty(k))throw new Error('Há preparação/revisão pendente: '+k+'. Não instale a ponte ainda.');});
    if((sp.getProperty('AC_SECRET')||'').length<32||!acId_(sp.getProperty('AC_GUILD_ID')))throw new Error('Configure AC_SECRET e AC_GUILD_ID nas Propriedades do script.');
    if(sp.getProperty('CM_USAR_SCRIPT_PROPERTIES')!=='1'){
      const values=original.getProperties(),copy={};Object.keys(values).filter(k=>k.startsWith('CM_')).forEach(k=>copy[k]=values[k]);
      copy.CM_USAR_SCRIPT_PROPERTIES='1';sp.setProperties(copy);
    }
    sp.setProperty('CM_VERSAO',CM.versao);cmValidarEstrutura_(ss);
    const tables=[
      [AC.events,['Evento','Pedido','Quando','Tipo','Autor Discord','Origem','Antes JSON','Depois JSON']],
      [AC.requests,['Pedido','Assinatura lógica','Resultado JSON','Quando']],
      [AC.snapshots,['ID registro','Snapshot JSON']]
    ];
    tables.forEach(([name,heads])=>{
      let sh=ss.getSheetByName(name);
      if(!sh){sh=ss.insertSheet(name);sh.getRange(1,1,1,heads.length).setValues([heads]);sh.hideSheet();cmProteger_(sh.protect(),CM.prefixo+'Arquivista '+name);}
    });
    if(sp.getProperty('AC_BASE_COMPLETA')!=='1')sp.setProperty('AC_BASE_PENDENTE','1');
    sp.setProperty('AC_ATIVO','1');cmInstalarGatilhos_(ss);
    acBasePasso_(ss);
    console.log('PONTE PREPARADA · v'+AC.version+'. Confira acDiagnostico; depois implante o Web App.');
    ss.toast('Ponte do Arquivista preparada. O acesso ao arquivo continua restrito.','Arquivista',12);
  }finally{l.releaseLock();}
}
function acContinuarBase(){
  cmApagarGatilhoTemporario_('acContinuarBase');const l=LockService.getScriptLock();
  if(!l.tryLock(1500)){cmAgendar_('acContinuarBase');return;}
  try{acBasePasso_(SpreadsheetApp.openById(CM.id));}finally{l.releaseLock();}
}
function acBasePasso_(ss){
  const p=acProps_();if(p.getProperty('AC_BASE_COMPLETA')==='1')return;
  const snapshots=acSnapshots_(ss),idx=acIndex_(ss),pending=idx.filter(x=>x.id&&!snapshots.has(x.id));
  const batch=pending.slice(0,50),records=acReadMany_(ss,batch,snapshots),req=[];
  records.forEach(r=>acSnapshotPlan_(ss,snapshots,r.id,r,req));if(req.length)acBatch_(req);
  if(pending.length>batch.length){cmAgendar_('acContinuarBase');console.log('Base histórica: continuação agendada.');}
  else{p.setProperty('AC_BASE_COMPLETA','1');p.deleteProperty('AC_BASE_PENDENTE');console.log('BASE HISTÓRICA PRONTA. Não foram emitidos avisos retroativos.');}
}
function acDiagnostico(){
  const p=acProps_();const data={ponte:AC.version,ativa:p.getProperty('AC_ATIVO')==='1',base:p.getProperty('AC_BASE_COMPLETA')==='1',membros:cmCapacidade_(),erro:p.getProperty('AC_ULTIMO_ERRO')||'nenhum'};
  console.log(JSON.stringify(data));SpreadsheetApp.getUi().alert('Arquivista do Ciclo',JSON.stringify(data,null,2),SpreadsheetApp.getUi().ButtonSet.OK);
}
function acReady_(ss){
  const p=acProps_();if(p.getProperty('AC_BASE_COMPLETA')!=='1')acFail_('NOT_READY');
  if(['CM_AMPLIACAO_V11','CM_INSTALACAO_V11','CM_ESTRUTURA_ALERTA','CM_REVISAO_NECESSARIA'].some(k=>p.getProperty(k)))acFail_('MAINTENANCE');
  try{cmValidarEstrutura_(ss);}catch(e){acFail_('MAINTENANCE');}
}
function acDispatch_(ss,q){
  const d=q.data,a=q.actor;
  if(q.action==='status'){
    if(!a.staff)acFail_('FORBIDDEN');const p=acProps_();
    return {version:AC.version,capacity:cmCapacidade_(),ready:p.getProperty('AC_BASE_COMPLETA')==='1',
      maintenance:['CM_AMPLIACAO_V11','CM_INSTALACAO_V11','CM_ESTRUTURA_ALERTA','CM_REVISAO_NECESSARIA'].some(k=>!!p.getProperty(k)),
      events_last_seq:Math.max(0,ss.getSheetByName(AC.events).getLastRow()-1)};
  }
  acReady_(ss);
  if(q.action==='list'){
    const owner=d.owner_id?String(d.owner_id):'';if(owner&&!acId_(owner))acFail_('INVALID');
    const records=acIndex_(ss).filter(r=>(!owner||r.owner_id===owner)&&((d.include_released===true)||r.status!=='Liberado'));
    return {records:acReadMany_(ss,records,acSnapshots_(ss)).map(acPublic_)};
  }
  if(q.action==='get'){
    const r=acGet_(ss,String(d.id));if(!a.staff&&r.owner_id!==a.id)acFail_('FORBIDDEN');return {record:r};
  }
  if(q.action==='image'){
    const r=acGet_(ss,String(d.id));if(r.status==='Liberado'&&!a.staff&&a.id!==r.owner_id)acFail_('NOT_FOUND');
    let url=r.image_url;const cell=ss.getSheetById(CM.fichasId).getRange(r.row,r.col+6),value=cell.getValue();
    if(!cell.getFormula()&&value&&typeof value.getContentUrl==='function')url=value.getContentUrl();
    return {url:url||'',media_ref:r.media_ref||''};
  }
  if(q.action==='events'){
    if(!a.staff)acFail_('FORBIDDEN');const after=Math.max(0,Math.floor(Number(d.after)||0));
    const last=ss.getSheetByName(AC.events).getLastRow()-1;
    const events=acEvents_(ss,after,100).map(acPublicEvent_);
    return {events:events,cursor:events.length?events[events.length-1].seq:Math.min(after,last)};
  }
  if(q.action==='history'){
    if(!a.staff)acFail_('FORBIDDEN');const query=cmNormalizar_(String(d.query||''));
    if(query.length>200)acFail_('INVALID');
    const total=ss.getSheetByName(AC.events).getLastRow()-1,base=Math.max(0,total-5000);
    const all=acEvents_(ss,base,5000),found=all.filter(e=>!query||[e.before,e.after].some(r=>r&&(cmNormalizar_(r.id)===query||cmNormalizar_(r.appearance+' '+r.work).includes(query))));
    return {events:found.slice(-200).reverse(),truncated:found.length>200||base>0};
  }
  if(q.action==='reconcile'){
    if(!a.staff)acFail_('FORBIDDEN');return acReconcile_(ss);
  }
  if(q.action==='refresh_image'){
    if(!a.staff)acFail_('FORBIDDEN');const r=acGet_(ss,String(d.id));
    if(!r.media_ref||r.media_ref!==d.media_ref)acFail_('STALE');
    r.image_url=acUrl_(d.url);const req=[];
    acPut_(req,CM.fichasId,r.row,r.col+7,[r.image_url]);
    const snaps=acSnapshots_(ss);acSnapshotPlan_(ss,snaps,r.id,r,req);acBatch_(req);return {};
  }
  if(q.action==='export'){
    // Leitura completa para importar no banco do bot (só staff; contém campos internos).
    if(!a.staff)acFail_('FORBIDDEN');return acExport_(ss);
  }
  if(!['create','edit','change_status','transfer','remove'].includes(q.action))acFail_('INVALID');
  if(['change_status','transfer','remove'].includes(q.action)&&!a.staff)acFail_('FORBIDDEN');
  return acMutate_(ss,q);
}

function acExport_(ss){
  // Funciona antes de instalar a ponte: sem a aba de snapshots, só não há media_ref.
  const idx=acIndex_(ss),snaps=ss.getSheetByName(AC.snapshots)?acSnapshots_(ss):new Map(),out=[];
  for(let i=0;i<idx.length;i+=400)acReadMany_(ss,idx.slice(i,i+400),snaps).forEach(r=>out.push({id:r.id,owner_id:r.owner_id,
    appearance:r.appearance,work:r.work,server_name:r.server_name,status:r.status,justification:r.justification,
    image_url:r.image_url,date:r.date}));
  return {format:'arquivista-export',version:1,exported_at:new Date().toISOString(),records:out};
}
/** Execute como dono: grava no seu Drive um .json para o importar.py do bot. Só leitura na planilha. */
function exportarParaArquivista(){
  const ss=SpreadsheetApp.openById(CM.id);cmExigirDono_(ss);
  const l=LockService.getScriptLock();if(!l.tryLock(5000))throw new Error('Outra tarefa está usando a planilha. Tente de novo em instantes.');
  try{
    const data=acExport_(ss),name='arquivista-export-'+data.exported_at.slice(0,10)+'.json';
    const file=DriveApp.createFile(name,JSON.stringify(data),'application/json');
    console.log(data.records.length+' cadastros exportados para '+name+' no seu Drive (privado). '+file.getUrl());
    ss.toast(data.records.length+' cadastros exportados para '+name+' no seu Drive.');
  }finally{l.releaseLock();}
}

// ---------------- leituras pequenas / estruturas auxiliares ----------------
function acIndex_(ss){
  SpreadsheetApp.flush();const index=cmLerIndice_(ss),seen=new Set();
  return index.map(v=>{
    const row=Number(v[0]),side=Number(v[1]),slot=Number(v[2]),group=2*Math.floor((row-5)/822)+side;
    const pos=cmEndereco_(group,slot);if(pos.row!==row||![1,2].includes(side)||group>cmCapacidade_())acFail_('MAINTENANCE');
    const id=String(v[7]||'');if(!id||seen.has(id))acFail_('MAINTENANCE');seen.add(id);
    return {id,row,col:pos.col,group,slot,appearance:String(v[3]||''),work:String(v[4]||''),status:String(v[5]||''),owner_id:String(v[6]||'')};
  });
}
function acPublic_(r){return {id:r.id,appearance:r.appearance,work:r.work,server_name:r.server_name,owner_id:r.owner_id,occupied:r.status!=='Liberado'};}
function acSnapshots_(ss){
  const sh=ss.getSheetByName(AC.snapshots),last=sh.getLastRow(),map=new Map();
  if(last>1)sh.getRange(2,1,last-1,2).getValues().forEach((r,i)=>{if(r[0])map.set(String(r[0]),{row:i+2,record:r[1]?acJson_(String(r[1])):null});});
  return map;
}
function acReadMany_(ss,idx,snapshots){
  if(!idx.length)return [];const ranges=[];
  idx.forEach(r=>{ranges.push('FICHAS!'+cmLetra_(r.col)+r.row+':'+cmLetra_(r.col+9)+r.row);ranges.push('FICHAS!'+cmLetra_(r.col+1)+(r.row+2));});
  const res=Sheets.Spreadsheets.Values.batchGet(CM.id,{ranges:ranges,valueRenderOption:'UNFORMATTED_VALUE',dateTimeRenderOption:'SERIAL_NUMBER'}).valueRanges;
  return idx.map((r,i)=>{
    const v=(res[2*i].values||[[]])[0],j=(res[2*i+1].values||[[]])[0];
    if(Number(v[0])!==r.slot||String(v[8]||'')!==r.id)acFail_('MAINTENANCE');
    const old=snapshots&&snapshots.get(r.id),prev=old&&old.record;
    const rec={id:r.id,group:r.group,slot:r.slot,row:r.row,col:r.col,owner_id:r.owner_id,
      appearance:String(v[1]||''),server_name:String(v[2]||''),work:String(v[3]||''),status:String(v[4]||''),
      date:typeof v[5]==='number'?v[5]:null,justification:String(j[0]||''),image_url:String(v[7]||''),
      media_ref:prev&&prev.image_url===String(v[7]||'')?prev.media_ref||'':'',native_rev:prev?prev.native_rev||'':''};
    rec.revision=acRevision_(rec);return rec;
  });
}
function acGet_(ss,id){const idx=acIndex_(ss),found=idx.find(r=>r.id===id);if(!found)acFail_('NOT_FOUND');return acReadMany_(ss,[found],acSnapshots_(ss))[0];}
function acRevision_(r){
  return acHash_(JSON.stringify(['id','owner_id','appearance','server_name','work','status','date','justification','image_url','media_ref','native_rev'].map(k=>r[k]===undefined?'':r[k])));
}
function acCell_(v){return v===null||v===undefined||v===''?{}:{userEnteredValue:typeof v==='number'?{numberValue:v}:typeof v==='boolean'?{boolValue:v}:{stringValue:String(v)}};}
function acPut_(req,sid,row,col,values){req.push({updateCells:{start:{sheetId:sid,rowIndex:row-1,columnIndex:col-1},rows:[{values:values.map(acCell_)}],fields:'userEnteredValue'}});}
function acFormula_(req,sid,row,col,text){req.push({updateCells:{start:{sheetId:sid,rowIndex:row-1,columnIndex:col-1},rows:[{values:[{userEnteredValue:{formulaValue:text}}]}],fields:'userEnteredValue'}});}
function acAppend_(req,sid,values){req.push({appendCells:{sheetId:sid,rows:[{values:values.map(acCell_)}],fields:'userEnteredValue'}});}
function acBatch_(req){if(req.length)Sheets.Spreadsheets.batchUpdate({requests:req,includeSpreadsheetInResponse:false},CM.id);SpreadsheetApp.flush();}
function acSnapshotPlan_(ss,snaps,id,record,req){
  const sh=ss.getSheetByName(AC.snapshots),old=snaps.get(id);
  if(old)acPut_(req,sh.getSheetId(),old.row,1,[id,JSON.stringify(record)]);
  else acAppend_(req,sh.getSheetId(),[id,JSON.stringify(record)]);
}
function acEvents_(ss,after,limit){
  const sh=ss.getSheetByName(AC.events),last=sh.getLastRow()-1,count=Math.max(0,Math.min(last-after,limit===null?last:limit));
  if(!count)return [];
  return sh.getRange(after+2,1,count,8).getValues().map((r,i)=>({seq:after+i+1,event_id:String(r[0]),request_id:String(r[1]),at:String(r[2]),kind:String(r[3]),actor_id:String(r[4]||''),source:String(r[5]),before:r[6]?acJson_(String(r[6])):null,after:r[7]?acJson_(String(r[7])):null}));
}
function acPublicEvent_(e){
  const r=e.after||e.before||{};
  return {seq:e.seq,event_id:e.event_id,at:e.at,kind:e.kind==='create'?'created':e.kind==='remove'?'removed':e.kind==='transfer'?'transferred':'updated',
    appearance:r.appearance||'',work:r.work||'',owner_id:r.owner_id||'',actor_id:e.actor_id,source:e.source};
}
function acEventPlan_(ss,req,q,before,after,kind,source){
  acAppend_(req,ss.getSheetByName(AC.events).getSheetId(),['EV-'+Utilities.getUuid(),q?q.request_id:'',new Date().toISOString(),kind,q?q.actor.id:'',source||'discord',JSON.stringify(before),JSON.stringify(after)]);
}
function acRemembered_(ss,rid,digest){
  const sh=ss.getSheetByName(AC.requests);if(sh.getLastRow()<2)return null;
  const match=sh.getRange(2,1,sh.getLastRow()-1,1).createTextFinder(rid).matchEntireCell(true).matchCase(true).findNext();
  if(!match)return null;const r=sh.getRange(match.getRow(),1,1,3).getValues()[0];
  if(r[1]!==digest)acFail_('REUSED_REQUEST');return acJson_(r[2]);
}
function acStatePlan_(ss,r,req){
  const state=cmEstado_(ss),old=state.map.get(r.id),row=old?old.row:state.nextRow;
  if(row>state.maxRows)req.push({appendDimension:{sheetId:state.sheet.getSheetId(),dimension:'ROWS',length:500}});
  acPut_(req,state.sheet.getSheetId(),row,1,[r.id,r.date,r.date===null,cmLetra_(r.col+1)+r.row]);
  req.push({repeatCell:{range:{sheetId:state.sheet.getSheetId(),startRowIndex:row-1,endRowIndex:row,startColumnIndex:1,endColumnIndex:2},cell:{userEnteredFormat:{numberFormat:{type:'DATE',pattern:'dd/mm/yyyy'}}},fields:'userEnteredFormat.numberFormat'}});
}
function acMemberPlan_(ss,owner,idx,req){
  if(!owner||!acId_(owner.id))acFail_('INVALID');const name=acText_(owner.name,100,true),cap=cmCapacidade_();
  const members=ss.getSheetById(CM.membrosId),map=ss.getSheetByName(CM.mapa),rows=members.getRange(4,1,CM.ultimaLinhaMembros-3,2).getDisplayValues(),maps=map.getRange(2,1,cap,5).getDisplayValues();
  const duplicates=rows.filter(r=>r[0]===owner.id);if(duplicates.length>1||maps.filter(r=>r[1]===owner.id).length>1)acFail_('MAINTENANCE');
  let mi=rows.findIndex(r=>r[0]===owner.id);if(mi<0){mi=rows.findIndex(r=>!r[0]&&!r[1]);if(mi<0)acFail_('CAPACITY');acPut_(req,members.getSheetId(),mi+4,1,[owner.id,name]);}
  let group=maps.findIndex(r=>r[1]===owner.id)+1;
  if(!group){group=maps.findIndex((r,i)=>!r[1]&&!idx.some(x=>x.group===i+1))+1;if(!group)acFail_('CAPACITY');acPut_(req,map.getSheetId(),group+1,2,[owner.id]);acPut_(req,map.getSheetId(),group+1,5,[rows[mi][1]||name]);}
  return group;
}
function acFree_(ss,group){
  const f=ss.getSheetById(CM.fichasId),first=cmEndereco_(group,1),last=cmEndereco_(group,200);
  const values=f.getRange(first.row,first.col,last.row-first.row+4,9).getValues();
  for(let n=1;n<=200;n++){
    const a=cmEndereco_(group,n),v=values[a.row-first.row];
    if(Number(v[0])!==n)acFail_('MAINTENANCE');
    if(v.slice(1).some(x=>x!==''&&x!==null))continue;
    if(values[a.row-first.row+2][1])continue;
    return {group,slot:n,row:a.row,col:a.col};
  }acFail_('CAPACITY');
}
function acDuplicate_(idx,r){if(r.status==='Liberado')return false;const k=cmChave_(r.appearance,r.work);return idx.some(x=>x.id!==r.id&&x.status!=='Liberado'&&cmChave_(x.appearance,x.work)===k);}
function acInput_(input){
  if(!input||typeof input!=='object')acFail_('INVALID');
  const allowed=['appearance','server_name','work','image_url','media_ref'];Object.keys(input).forEach(k=>{if(!allowed.includes(k))acFail_('INVALID');});
  return {appearance:acText_(input.appearance,100,true),work:acText_(input.work,100,true),server_name:acText_(input.server_name||'',100,false),image_url:acUrl_(input.image_url||''),media_ref:acMedia_(input.media_ref||'')};
}
function acCleanSlot_(req,r){
  acPut_(req,CM.fichasId,r.row,r.col+1,['','','','','']);acPut_(req,CM.fichasId,r.row,r.col+7,['','']);
  acPut_(req,CM.fichasId,r.row+2,r.col+1,['']);
  const link=cmLetra_(r.col+7)+r.row;
  acFormula_(req,CM.fichasId,r.row,r.col+6,'=IF('+link+'="";"";IFERROR(IMAGE('+link+');""))');
}
function acWriteRecord_(req,before,after,action,forceImage){
  if(action==='remove'){acCleanSlot_(req,before);return;}
  if(action==='transfer'){
    req.push({copyPaste:{source:{sheetId:CM.fichasId,startRowIndex:before.row-1,endRowIndex:before.row+3,startColumnIndex:before.col+5,endColumnIndex:before.col+6},destination:{sheetId:CM.fichasId,startRowIndex:after.row-1,endRowIndex:after.row+3,startColumnIndex:after.col+5,endColumnIndex:after.col+6},pasteType:'PASTE_NORMAL'}});
    acCleanSlot_(req,before);
  }
  acPut_(req,CM.fichasId,after.row,after.col+1,[after.appearance,after.server_name,after.work,after.status,after.date]);
  acPut_(req,CM.fichasId,after.row,after.col+7,[after.image_url,after.id]);
  acPut_(req,CM.fichasId,after.row+2,after.col+1,[after.justification]);
  if(forceImage||!before||after.image_url!==before.image_url){const h=cmLetra_(after.col+7)+after.row;acFormula_(req,CM.fichasId,after.row,after.col+6,'=IF('+h+'="";"";IFERROR(IMAGE('+h+');""))');}
}
function acMutate_(ss,q){
  const d=q.data,actor=q.actor,action=q.action;
  const digest=acHash_(JSON.stringify([q.action,q.guild_id,q.actor.id,q.actor.staff,q.data]));
  const saved=acRemembered_(ss,q.request_id,digest);if(saved)return saved;
  const idx=acIndex_(ss),snaps=acSnapshots_(ss),req=[];
  let before=null,after=null,forceImage=false;
  if(action==='create'){
    const input=acInput_(d.fields),owner=d.owner||actor;
    if(!actor.staff&&owner.id!==actor.id)acFail_('FORBIDDEN');
    const group=acMemberPlan_(ss,owner,idx,req),slot=acFree_(ss,group);
    const day=Utilities.formatDate(new Date(),ss.getSpreadsheetTimeZone(),'yyyy-MM-dd');
    after=Object.assign({},slot,input,{id:'AP-'+Utilities.getUuid(),owner_id:owner.id,status:'Em preparação',justification:'',date:Date.parse(day+'T00:00:00Z')/86400000+25569,native_rev:''});
  }else{
    const meta=idx.find(r=>r.id===d.id);if(!meta)acFail_('NOT_FOUND');before=acReadMany_(ss,[meta],snaps)[0];
    if(!actor.staff&&before.owner_id!==actor.id)acFail_('FORBIDDEN');
    if(!d.revision||before.revision!==d.revision)acFail_('STALE');
    after=Object.assign({},before);
    if(action==='edit'){
      const patch=d.fields||{},keys=Object.keys(patch);
      if(keys.some(k=>!['appearance','server_name','work','image_url','media_ref','clear_image'].includes(k)))acFail_('INVALID');
      if(!actor.staff&&keys.some(k=>['appearance','work'].includes(k)))acFail_('FORBIDDEN');
      if('clear_image' in patch&&typeof patch.clear_image!=='boolean')acFail_('INVALID');
      forceImage=patch.clear_image===true;
      const validPatch=Object.assign({},patch);delete validPatch.clear_image;
      const merged=acInput_(Object.assign({},Object.fromEntries(['appearance','work','server_name','image_url','media_ref'].map(k=>[k,before[k]||''])),validPatch));
      if(Object.prototype.hasOwnProperty.call(patch,'image_url')&&!Object.prototype.hasOwnProperty.call(patch,'media_ref'))merged.media_ref='';
      Object.assign(after,merged);
      if(forceImage){after.image_url='';after.media_ref='';after.native_rev='clear@'+new Date().toISOString();}
    }else if(action==='change_status'){
      if(!AC.statuses.includes(d.status))acFail_('INVALID');after.status=d.status;after.justification=acText_(d.justification||'',2000,false);
    }else if(action==='transfer'){
      const owner=d.owner;if(!owner||owner.id===before.owner_id)acFail_('INVALID');
      const group=acMemberPlan_(ss,owner,idx,req);Object.assign(after,acFree_(ss,group),{owner_id:owner.id});
    }else if(action==='remove'){after=null;}
  }
  if(after&&acDuplicate_(idx,after))acFail_('DUPLICATE');
  if(after)after.revision=acRevision_(after);
  const unchanged=before&&after&&before.revision===after.revision&&!forceImage;
  const result={changed:!unchanged,record:after,removed_id:after?'':before.id};
  if(!unchanged){
    acWriteRecord_(req,before,after,action,forceImage);if(after)acStatePlan_(ss,after,req);
    acSnapshotPlan_(ss,snaps,(after||before).id,after,req);acEventPlan_(ss,req,q,before,after,action,'discord');
  }
  acAppend_(req,ss.getSheetByName(AC.requests).getSheetId(),[q.request_id,digest,JSON.stringify(result),new Date().toISOString()]);
  // Uma batch atômica: ficha + mapa de membro + ID/data + auditoria + chave de retentativa.
  acBatch_(req);return result;
}

// ---------------- histórico de alterações manuais ----------------
// Chamada DENTRO do mesmo ScriptLock do cmAoEditar, sem abrir outra trava.
function acCapturarEdicao_(ss,alvos,e){
  if(acProps_().getProperty('AC_BASE_COMPLETA')!=='1')return;
  const snaps=acSnapshots_(ss),idx=acIndex_(ss),targets=idx.filter(r=>alvos.some(a=>a.row===r.row&&a.col===r.col)),req=[];
  const records=acReadMany_(ss,targets,snaps);
  records.forEach(r=>{
    if(e&&e.range&&e.range.getColumn()<=r.col+6&&e.range.getLastColumn()>=r.col+6)r.native_rev=new Date().toISOString();
    r.revision=acRevision_(r);const previous=snaps.get(r.id),before=previous?previous.record:null;
    if(!before||before.revision!==r.revision){acEventPlan_(ss,req,null,before,r,before?'manual_edit':'create','planilha');acSnapshotPlan_(ss,snaps,r.id,r,req);}
  });
  snaps.forEach((s,id)=>{if(s.record&&alvos.some(a=>a.row===s.record.row&&a.col===s.record.col)&&!idx.some(r=>r.id===id)){acEventPlan_(ss,req,null,s.record,null,'remove','planilha');acSnapshotPlan_(ss,snaps,id,null,req);}});
  acBatch_(req);
}
function acReconcile_(ss){
  const idx=acIndex_(ss),snaps=acSnapshots_(ss),p=acProps_(),start=Number(p.getProperty('AC_RECONCILE_CURSOR')||0),batch=idx.slice(start,start+50),req=[];
  const records=acReadMany_(ss,batch,snaps);let changed=0;
  records.forEach(r=>{const old=snaps.get(r.id),before=old?old.record:null;if(!before||before.revision!==r.revision){acSnapshotPlan_(ss,snaps,r.id,r,req);acEventPlan_(ss,req,null,before,r,before?'manual_edit':'create','planilha');changed++;}});
  const active=new Set(idx.map(r=>r.id));snaps.forEach((s,id)=>{if(s.record&&!active.has(id)){acSnapshotPlan_(ss,snaps,id,null,req);acEventPlan_(ss,req,null,s.record,null,'remove','planilha');changed++;}});
  acBatch_(req);p.setProperty('AC_RECONCILE_CURSOR',String(start+50>=idx.length?0:start+50));
  return {changed,scanned:batch.length,total:idx.length};
}
