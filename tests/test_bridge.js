'use strict';
// Executa o código REAL da ponte em uma simulação em memória dos serviços Google.
// Não equivale a um teste remoto de autorização, quotas, imagens ou gatilhos.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),crypto=require('crypto');
const path=require('path');const root=path.resolve(__dirname,'..');
let passed=0;function test(name,fn){try{fn();passed++;console.log('OK '+name);}catch(e){console.error('FAIL '+name);throw e;}}
const uid='459030926928904230',other='111111111111111111',staffid='222222222222222222',gid='333333333333333333';
const propsMap=new Map([['AC_SECRET','z'.repeat(48)],['AC_GUILD_ID',gid],['AC_ATIVO','1'],['AC_BASE_COMPLETA','1'],['CM_MEMBROS_PRONTOS','50'],['CM_USAR_SCRIPT_PROPERTIES','1']]);
const props={getProperty:k=>propsMap.get(k)||null,setProperty:(k,v)=>propsMap.set(k,String(v)),deleteProperty:k=>propsMap.delete(k),getProperties:()=>Object.fromEntries(propsMap),setProperties:o=>Object.entries(o).forEach(([k,v])=>propsMap.set(k,String(v)))};
let serial=0,locks=0,batches=0;
class Range{
 constructor(sh,row,col,nr=1,nc=1){Object.assign(this,{sh,row,col,nr,nc});}
 getValues(){return Array.from({length:this.nr},(_,i)=>Array.from({length:this.nc},(_,j)=>this.sh.read(this.row+i,this.col+j)));}
 getDisplayValues(){return this.getValues().map(r=>r.map(v=>String(v??'')));}
 getValue(){return this.sh.read(this.row,this.col);}
 getFormula(){return (this.sh.cells.get(`${this.row},${this.col}`)||{}).formulaValue||'';}
 getRow(){return this.row;}getColumn(){return this.col;}getLastColumn(){return this.col+this.nc-1;}getLastRow(){return this.row+this.nr-1;}
 createTextFinder(text){const self=this;return {matchEntireCell(){return this;},matchCase(){return this;},findNext(){for(let i=0;i<self.nr;i++)if(self.sh.read(self.row+i,self.col)===text)return new Range(self.sh,self.row+i,self.col);return null;}};}
}
class Sheet{
 constructor(id,name,rows=1000,cols=26){Object.assign(this,{id,name,rows,cols});this.cells=new Map();}
 getSheetId(){return this.id;}getName(){return this.name;}getMaxRows(){return this.rows;}getMaxColumns(){return this.cols;}
 getLastRow(){let last=0;for(const key of this.cells.keys())last=Math.max(last,Number(key.split(',')[0]));return last;}
 getRange(r,c,nr,nc){return new Range(this,r,c,nr,nc);}
 read(r,c){const v=this.cells.get(`${r},${c}`);if(v){if('stringValue'in v)return v.stringValue;if('numberValue'in v)return v.numberValue;if('boolValue'in v)return v.boolValue;return '';}
  if(this.id===900120&&(c===1||c===12)){for(let g=(c===1?1:2);g<=50;g+=2)for(let n=1;n<=200;n++){let a=ctx.cmEndereco_(g,n);if(a.row===r)return n;}}
  return '';
 }
 put(r,c,v){this.cells.set(`${r},${c}`,typeof v==='number'?{numberValue:v}:typeof v==='boolean'?{boolValue:v}:{stringValue:String(v??'')});}
}
const sheets=[new Sheet(900120,'FICHAS',20554,23),new Sheet(900101,'MEMBROS',250,4),new Sheet(900140,'SISTEMA · MEMBROS',51,5),new Sheet(10,'SISTEMA · REGISTROS'),new Sheet(11,'SISTEMA · AC EVENTOS'),new Sheet(12,'SISTEMA · AC PEDIDOS'),new Sheet(13,'SISTEMA · AC SNAPSHOTS')];
const ss={getSheetById:id=>sheets.find(s=>s.id===id),getSheetByName:name=>sheets.find(s=>s.name===name),getSpreadsheetTimeZone:()=> 'America/Sao_Paulo'};
for(let s of sheets.slice(3))s.put(1,1,'Cabeçalho');
function readA1(a1){const [name,r]=a1.split('!');const m=/^([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$/.exec(r);const col=s=>[...s].reduce((v,c)=>26*v+c.charCodeAt(0)-64,0);let a=+m[2],b=col(m[1]),end=+(m[4]||m[2]),endCol=col(m[3]||m[1]);return ss.getSheetByName(name).getRange(a,b,end-a+1,endCol-b+1).getValues();}
const ctx=vm.createContext({console,Date,Map,Set,Number,String,JSON,Object,Array,Error,Math,RegExp,
 PropertiesService:{getScriptProperties:()=>props,getDocumentProperties:()=>props},
 SpreadsheetApp:{flush(){},openById:()=>ss,getActiveSpreadsheet:()=>ss},
 LockService:{getScriptLock(){let held=false;return {tryLock(){if(locks)return false;locks++;held=true;return true;},hasLock:()=>held,releaseLock(){if(held){locks--;held=false;}}};}},
 ContentService:{MimeType:{JSON:'json'},createTextOutput(x){return {setMimeType(){return x;}};}},
 Utilities:{Charset:{UTF_8:'utf8'},DigestAlgorithm:{SHA_256:'sha256'},getUuid:()=>`00000000-0000-0000-0000-${String(++serial).padStart(12,'0')}`,
 computeDigest:(alg,s)=>[...crypto.createHash('sha256').update(s).digest()],computeHmacSha256Signature:(s,k)=>[...crypto.createHmac('sha256',k).update(s).digest()],formatDate:()=> '2026-10-19'},
 Sheets:{Spreadsheets:{Values:{batchGet:(id,opts)=>({valueRanges:opts.ranges.map(r=>({values:readA1(r)}))})},batchUpdate(body){
  batches++;
  for(const req of body.requests){
   if(req.updateCells){const u=req.updateCells,sh=ss.getSheetById(u.start.sheetId);(u.rows||[]).forEach((row,i)=>(row.values||[]).forEach((cell,j)=>sh.cells.set(`${u.start.rowIndex+i+1},${u.start.columnIndex+j+1}`,cell.userEnteredValue||{})));}
   else if(req.appendCells){const u=req.appendCells,sh=ss.getSheetById(u.sheetId),start=sh.getLastRow()+1;u.rows.forEach((r,i)=>r.values.forEach((v,j)=>sh.cells.set(`${start+i},${j+1}`,v.userEnteredValue||{})));}
   else if(req.appendDimension){ss.getSheetById(req.appendDimension.sheetId).rows+=req.appendDimension.length;}
   else if(req.copyPaste){const cp=req.copyPaste;const sh=ss.getSheetById(cp.source.sheetId);for(let r=0;r<cp.source.endRowIndex-cp.source.startRowIndex;r++)for(let c=0;c<cp.source.endColumnIndex-cp.source.startColumnIndex;c++){const v=sh.cells.get(`${cp.source.startRowIndex+r+1},${cp.source.startColumnIndex+c+1}`)||{};sh.cells.set(`${cp.destination.startRowIndex+r+1},${cp.destination.startColumnIndex+c+1}`,{...v});}}
   else if(!req.repeatCell)throw Error('Requisição não simulada: '+Object.keys(req)[0]);
  }return {};
 }}}
});
vm.runInContext(fs.readFileSync(root+'/apps_script/Aparencias.gs','utf8'),ctx);
vm.runInContext(fs.readFileSync(root+'/apps_script/Arquivista.gs','utf8'),ctx);
ctx.cmValidarEstrutura_=()=>{}; // Sentinelas testadas separadamente; não é motor de fórmulas Google.
ctx.cmCapacidade_=()=>50;
ctx.cmEstado_=()=>{const sh=ss.getSheetByName('SISTEMA · REGISTROS'),map=new Map();for(let r=2;r<=sh.getLastRow();r++){const v=sh.getRange(r,1,1,4).getValues()[0];if(v[0])map.set(v[0],{row:r,date:typeof v[1]==='number'?new Date((v[1]-25569)*86400000):null,address:v[3],legado:v[2]});}return {sheet:sh,map,nextRow:sh.getLastRow()+1,maxRows:sh.rows};};
ctx.cmLerIndice_=()=>{const f=ss.getSheetById(900120),map=ss.getSheetById(900140),out=[];for(let g=1;g<=50;g++)for(let n=1;n<=200;n++){let a=ctx.cmEndereco_(g,n),name=f.cells.get(`${a.row},${a.col+1}`)?.stringValue||'';if(name)out.push([a.row,g%2?1:2,n,name,f.read(a.row,a.col+3),f.read(a.row,a.col+4),map.read(g+1,2),f.read(a.row,a.col+8),f.read(a.row,a.col+2)]);}return out;};
const map=ss.getSheetById(900140);for(let g=1;g<=50;g++){map.put(g+1,1,g);map.put(g+1,3,5+822*Math.floor((g-1)/2));map.put(g+1,4,g%2?'A':'L');}
const actor={id:uid,name:'Mizuki',staff:false},staff={id:staffid,name:'Staff',staff:true};
function request(action,data,who=actor,rid=`request-${++serial}`){return {v:1,action,guild_id:gid,actor:who,data,request_id:rid};}
function call(action,data,who=actor,rid){return ctx.acDispatch_(ss,request(action,data,who,rid));}
function get(id){return ctx.acGet_(ss,id);}
function assertCode(code,fn){assert.throws(fn,e=>e.acCode===code);}
let takao,newid;
test('20.000 coordenadas únicas, 200 por membro',()=>{const unique=new Set();for(let m=1;m<=100;m++)for(let n=1;n<=200;n++){const a=ctx.cmEndereco_(m,n);unique.add(`${a.row}:${a.col}`);}assert.equal(unique.size,20000);assert.equal(ctx.cmEndereco_(100,200).row,41099);});
test('registro cria membro, mapa, ID, data, snapshot e evento juntos',()=>{const result=call('create',{fields:{appearance:'Takao',work:'Azur Lane',server_name:'Nome interno'}});takao=result.record;assert.equal(takao.owner_id,uid);assert.equal(map.read(2,2),uid);assert.equal(ss.getSheetById(900101).read(4,1),uid);assert.equal(ss.getSheetByName('SISTEMA · AC EVENTOS').getLastRow(),2);assert.equal(typeof takao.date,'number');});
test('duplicata não cria membro nem deixa escrita parcial',()=>{const count=batches;assertCode('DUPLICATE',()=>call('create',{fields:{appearance:' TAKAO ',work:'Azur  Lane'}},{id:other,name:'Outro',staff:false}));assert.equal(batches,count);assert.equal(map.read(3,2),'');});
test('membro não cadastra em nome de outra pessoa',()=>assertCode('FORBIDDEN',()=>call('create',{owner:{id:other,name:'Outro'},fields:{appearance:'X',work:'Y'}})));
test('membro não altera identidade original',()=>assertCode('FORBIDDEN',()=>call('edit',{id:takao.id,revision:get(takao.id).revision,fields:{appearance:'Nova'}})));
test('membro não altera o cadastro de outro',()=>assertCode('FORBIDDEN',()=>call('edit',{id:takao.id,revision:get(takao.id).revision,fields:{server_name:'x'}},{id:other,name:'Outro',staff:false})));
test('edição permitida preserva ID/data e exige revisão atual',()=>{const before=get(takao.id);const result=call('edit',{id:takao.id,revision:before.revision,fields:{server_name:'Akira'}});assert.equal(result.record.id,before.id);assert.equal(result.record.date,before.date);assert.equal(get(takao.id).server_name,'Akira');assertCode('STALE',()=>call('edit',{id:takao.id,revision:before.revision,fields:{server_name:'Velho'}}));});
test('mesmo pedido repetido não duplica cadastro/evento',()=>{const before=get(takao.id),q=request('edit',{id:takao.id,revision:before.revision,fields:{server_name:'Repetível'}},actor,'request-idempotente');const a=ctx.acDispatch_(ss,q),count=batches,events=ss.getSheetByName('SISTEMA · AC EVENTOS').getLastRow();const b=ctx.acDispatch_(ss,q);assert.equal(JSON.stringify(a),JSON.stringify(b));assert.equal(batches,count);assert.equal(ss.getSheetByName('SISTEMA · AC EVENTOS').getLastRow(),events);});
test('reuso do pedido com outro conteúdo é negado',()=>assertCode('REUSED_REQUEST',()=>call('edit',{id:takao.id,revision:'x',fields:{server_name:'outro'}},actor,'request-idempotente')));
test('Arquivado continua ocupando',()=>{call('change_status',{id:takao.id,revision:get(takao.id).revision,status:'Arquivado',justification:'SEGREDO'},staff);assertCode('DUPLICATE',()=>call('create',{fields:{appearance:'Takao',work:'Azur Lane'}},{id:other,name:'Outro',staff:false}));});
test('Liberado permite novo uso; não é uma morte automática',()=>{call('change_status',{id:takao.id,revision:get(takao.id).revision,status:'Liberado'},staff);const r=call('create',{fields:{appearance:'Takao',work:'Azur Lane'}},{id:other,name:'Outro',staff:false});newid=r.record.id;assert.notEqual(newid,takao.id);});
test('membro não libera/remova/transfere por payload',()=>{for(const action of ['change_status','remove','transfer'])assertCode('FORBIDDEN',()=>call(action,{id:takao.id,revision:get(takao.id).revision,status:'Liberado'}));});
test('projeções públicas não vazam situação, justificativa ou nome interno',()=>{const r=call('list',{});const text=JSON.stringify(r);assert(!text.includes('justification'));assert(!text.includes('server_name'));assert(!text.includes('status'));assert(!text.includes('SEGREDO'));const ev=call('events',{after:0},staff);assert(!JSON.stringify(ev).includes('SEGREDO'));assert(!JSON.stringify(ev).includes('Arquivado'));});
test('transferência preserva ID/data e limpa apenas a ficha antiga',()=>{const before=get(newid);const after=call('transfer',{id:newid,revision:before.revision,owner:{id:staffid,name:'Staff'}},staff).record;assert.equal(after.id,before.id);assert.equal(after.date,before.date);assert.equal(after.owner_id,staffid);assert.equal(ss.getSheetById(900120).read(before.row,before.col+1),'');assert.equal(get(newid).owner_id,staffid);});
test('remoção guarda auditoria e não reutiliza ID',()=>{const before=get(newid);call('remove',{id:newid,revision:before.revision},staff);assertCode('NOT_FOUND',()=>get(newid));assert(call('history',{query:newid},staff).events.length>=2);const r=call('create',{fields:{appearance:'Takao',work:'Azur Lane'}},{id:other,name:'Outro',staff:false});assert.notEqual(r.record.id,newid);});
test('entrada de fórmula é gravada como texto, não executada',()=>{const r=call('create',{fields:{appearance:'=IMPORTDATA("x")',work:'Teste'}}).record;assert.equal(ss.getSheetById(900120).cells.get(`${r.row},${r.col+1}`).stringValue,'=IMPORTDATA("x")');});
test('gatilho manual registra mudança significativa, não recálculo/visor',()=>{let r=get(takao.id),f=ss.getSheetById(900120),events=ss.getSheetByName('SISTEMA · AC EVENTOS').getLastRow();ctx.acCapturarEdicao_(ss,[{row:r.row,col:r.col}],null);assert.equal(ss.getSheetByName('SISTEMA · AC EVENTOS').getLastRow(),events);f.put(r.row+2,r.col+1,'Justificativa nova');ctx.acCapturarEdicao_(ss,[{row:r.row,col:r.col}],null);assert.equal(ss.getSheetByName('SISTEMA · AC EVENTOS').getLastRow(),events+1);const last=call('history',{query:takao.id},staff).events[0];assert.equal(last.actor_id,'');assert.equal(last.source,'planilha');});
test('reconciliação detecta alteração manual não capturada',()=>{const r=get(takao.id);ss.getSheetById(900120).put(r.row,r.col+2,'Manual');const x=call('reconcile',{},staff);assert(x.changed>=1);assert.equal(call('reconcile',{},staff).changed,0);});
test('estado de ampliação impede gravações',()=>{props.setProperty('CM_AMPLIACAO_V11','{}');assertCode('MAINTENANCE',()=>call('create',{fields:{appearance:'X',work:'Y'}}));props.deleteProperty('CM_AMPLIACAO_V11');});
test('HMAC inválido não acessa registros nem adquire lock',()=>{let before=batches;const out=JSON.parse(ctx.doPost({postData:{contents:JSON.stringify({body:'{}',sig:'0'.repeat(64)})}}));assert.equal(out.code,'AUTH');assert.equal(batches,before);assert.equal(locks,0);});
test('HMAC válido processa pedido e libera lock',()=>{const q=request('status',{},staff);q.ts=Math.floor(Date.now()/1000);const body=JSON.stringify(q),sig=crypto.createHmac('sha256','z'.repeat(48)).update(body).digest('hex');const out=JSON.parse(ctx.doPost({postData:{contents:JSON.stringify({body,sig})}}));assert.equal(out.ok,true);assert.equal(out.data.capacity,50);assert.equal(locks,0);});
test('assinatura vencida e servidor diferente são rejeitados',()=>{for(const change of [{ts:1},{guild_id:uid}]){const q={...request('status',{},staff),ts:Math.floor(Date.now()/1000),...change};let body=JSON.stringify(q),sig=crypto.createHmac('sha256','z'.repeat(48)).update(body).digest('hex');assert.equal(JSON.parse(ctx.doPost({postData:{contents:JSON.stringify({body,sig})}})).code,'AUTH');}});
test('URLs perigosas e campos extras são rejeitados',()=>{for(const url of ['http://example.com/a','https://127.0.0.1/a','https://localhost/a','https://user@host.com/a'])assertCode('INVALID',()=>ctx.acUrl_(url));assertCode('INVALID',()=>call('create',{fields:{appearance:'x',work:'y',status:'Liberado'}}));});
test('chaves Unicode compatíveis com o Sheets',()=>{assert.equal(ctx.cmChave_('🐰','AK'),'2:🐰:ak');assert.equal(ctx.cmChave_('  Takao\u00a0','Azur   Lane'),'5:takao:azur lane');});
test('limpar imagem nativa restaura a fórmula mesmo sem link',()=>{const before=get(takao.id);ss.getSheetById(900120).put(before.row,before.col+6,'imagem nativa simulada');const result=call('edit',{id:before.id,revision:before.revision,fields:{clear_image:true}},staff);assert.equal(result.changed,true);assert(ss.getSheetById(900120).cells.get(`${before.row},${before.col+6}`).formulaValue.includes('IMAGE'));});
test('histórico e detalhes de terceiros exigem staff',()=>{assertCode('FORBIDDEN',()=>call('history',{}));assertCode('FORBIDDEN',()=>call('get',{id:takao.id},{id:other,name:'Outro',staff:false}));});
test('outro escritor recebe BUSY antes de qualquer alteração',()=>{locks=1;const q={...request('status',{},staff),ts:Math.floor(Date.now()/1000)};const body=JSON.stringify(q),sig=crypto.createHmac('sha256','z'.repeat(48)).update(body).digest('hex');const result=JSON.parse(ctx.doPost({postData:{contents:JSON.stringify({body,sig})}}));assert.equal(result.code,'BUSY');locks=0;});
console.log(`\n${passed} testes JavaScript aprovados. Serviços Google simulados, não executados remotamente.`);
