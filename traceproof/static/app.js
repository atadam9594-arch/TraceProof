'use strict';
const $ = id => document.getElementById(id);
const CMP = {
 en:{compareTitle:'Compare two files',compareInfo:'Optional local analysis. Small files are processed by the localhost service and never sent to a cloud provider. Results are similarity hints, not proof of origin.',leftFile:'First file',rightFile:'Second file',compareBtn:'Compare files'},
 tr:{compareTitle:'İki dosyayı karşılaştır',compareInfo:'İsteğe bağlı yerel analiz. Küçük dosyalar yalnızca yerel sunucuda işlenir; buluta gönderilmez. Benzerlik, köken kanıtı değildir.',leftFile:'Birinci dosya',rightFile:'İkinci dosya',compareBtn:'Dosyaları karşılaştır'},
 es:{compareTitle:'Comparar dos archivos',compareInfo:'Análisis local opcional. Los archivos pequeños se procesan en el servidor local, sin nube. La similitud no demuestra procedencia.',leftFile:'Primer archivo',rightFile:'Segundo archivo',compareBtn:'Comparar archivos'}
};
const I = {
 en:{offline:'LOCAL-FIRST · NO CLOUD',eyebrow:'A NEW STANDARD FOR UNCERTAINTY',hero:'',sub:'A portable, independently verifiable chain of evidence. Your files stay on your device. Missing proof never becomes a fake percentage.',newCase:'Start an investigation',subjectLabel:'What are you trying to establish?',create:'Create case',noCase:'No active case',addArtifact:'Register evidence',drop:'Drop files or choose from this device',dropHint:'SHA-256 calculated in your browser. Files are never uploaded.',noneYet:'No artifacts yet.',legacy:'Optional: register a previous v0.2 report',claims:'Claims & counter-evidence',claimLabel:'A testable claim',register:'Add claim',observation:'Add an observation (not a verdict)',registerObservation:'Add observation',finding:'Evidence map',status:'CONCLUSION',unresolved:'UNRESOLVED',policy:'Integrity of a case ≠ truth of the claim. Contradictions remain visible, never averaged away.',startHint:'Create a case and add evidence to see its testable claims, opposing observations and missing proof.',json:'Save case JSON',bundle:'Export ProofBundle',noOriginal:'Exports omit original media by default.',verifyHead:'Independent verification',verifyInfo:'Import any ProofBundle to check event-chain and file integrity. No login, no proprietary service.',verifyBtn:'Choose ProofBundle (.zip)',caseImport:'Resume a saved case',loadHint:'Import your previously exported TraceProof v0.3 case JSON. Previous v0.2 reports can be attached above.',footer:'Evidence is not a verdict. No cloud. No invented certainty.',contested:'CONTESTED',review_required:'REVIEW REQUIRED',unresolvedStatus:'UNRESOLVED',support:'Support',oppose:'Counter-evidence',missing:'Missing evidence',none:'None',success:'Saved',noActive:'Create a case first',processing:'Processing locally…',integrity:'Integrity',provenance:'Provenance',authorship:'Authorship',context:'Context',other:'Other',noFile:'No linked file',selectClaim:'Choose claim',download:'Downloaded',verifyDone:'Verification completed',oversized:'File is too large to hash in browser (max 150 MB)',errors:'Error'},
 tr:{offline:'YEREL ÖNCELİKLİ · BULUT YOK',eyebrow:'BELİRSİZLİĞE YENİ YAKLAŞIM',sub:'Taşınabilir, bağımsız doğrulanabilir kanıt zinciri. Dosyalar cihazınızda kalır. Eksik kanıt sahte bir yüzdeye dönüşmez.',newCase:'İnceleme başlat',subjectLabel:'Neyi doğrulamak istiyorsunuz?',create:'Dosya oluştur',noCase:'Aktif inceleme yok',addArtifact:'Kanıt kaydet',drop:'Dosyaları sürükleyin veya cihazdan seçin',dropHint:'SHA-256 tarayıcınızda hesaplanır. Dosyalar yüklenmez.',noneYet:'Henüz dosya yok.',legacy:'İsteğe bağlı: önceki v0.2 raporunu kaydet',claims:'İddialar ve karşı kanıtlar',claimLabel:'Sınanabilir iddia',register:'İddia ekle',observation:'Gözlem ekle (hüküm değil)',registerObservation:'Gözlem ekle',finding:'Kanıt haritası',status:'SONUÇ',unresolved:'BELİRSİZ',policy:'Kayıt bütünlüğü ≠ iddianın doğruluğu. Çelişkiler gizlenmez, ortalamaya dönüştürülmez.',startHint:'Bir inceleme oluşturun. İddiaları, karşı kanıtları ve eksik bilgileri burada göreceksiniz.',json:'JSON dosyasını kaydet',bundle:'ProofBundle dışa aktar',noOriginal:'Orijinal medya varsayılan olarak dışa aktarılmaz.',verifyHead:'Bağımsız doğrulama',verifyInfo:'Bir ProofBundle yükleyip kanıt zincirini ve dosya bütünlüğünü denetleyin. Giriş gerekmez.',verifyBtn:'ProofBundle (.zip) seç',caseImport:'Kaydedilmiş incelemeye devam et',loadHint:'TraceProof v0.3 inceleme JSON dosyasını içeri alın. Önceki v0.2 raporları yukarıdan eklenebilir.',footer:'Kanıt, hüküm değildir. Bulut yok. Uydurma kesinlik yok.',contested:'ÇELİŞKİLİ',review_required:'İNCELEME GEREKİYOR',unresolvedStatus:'BELİRSİZ',support:'Destekleyen',oppose:'Karşı kanıt',missing:'Eksik kanıt',none:'Yok',success:'Kaydedildi',noActive:'Önce bir inceleme başlatın',processing:'Cihazınızda işleniyor…',integrity:'Bütünlük',provenance:'Köken',authorship:'Üreten',context:'Bağlam',other:'Diğer',noFile:'Dosya seçilmedi',selectClaim:'İddia seç',download:'İndirildi',verifyDone:'Doğrulama tamamlandı',oversized:'Tarayıcıda işlemek için dosya çok büyük (en fazla 150 MB)',errors:'Hata'},
 es:{offline:'PRIMERO LOCAL · SIN NUBE',eyebrow:'UN NUEVO ESTÁNDAR DE INCERTIDUMBRE',sub:'Una cadena portátil de evidencias verificable de forma independiente. Los archivos quedan en tu dispositivo. La ausencia de prueba no se convierte en un porcentaje ficticio.',newCase:'Iniciar investigación',subjectLabel:'¿Qué intentas establecer?',create:'Crear caso',noCase:'Sin caso activo',addArtifact:'Registrar evidencia',drop:'Arrastra archivos o selecciónalos aquí',dropHint:'SHA-256 se calcula en el navegador. Los archivos nunca se suben.',noneYet:'Todavía sin archivos.',legacy:'Opcional: registrar informe v0.2 anterior',claims:'Afirmaciones y contraevidencia',claimLabel:'Afirmación comprobable',register:'Añadir afirmación',observation:'Añadir observación (no veredicto)',registerObservation:'Añadir observación',finding:'Mapa de evidencias',status:'CONCLUSIÓN',unresolved:'NO RESUELTO',policy:'La integridad del expediente ≠ verdad de la afirmación. Las contradicciones permanecen visibles.',startHint:'Crea un caso y añade evidencias para ver las afirmaciones y las pruebas faltantes.',json:'Guardar caso JSON',bundle:'Exportar ProofBundle',noOriginal:'No se incluyen archivos originales por defecto.',verifyHead:'Verificación independiente',verifyInfo:'Importa un ProofBundle y verifica su cadena e integridad sin cuentas ni servicios propietarios.',verifyBtn:'Elegir ProofBundle (.zip)',caseImport:'Continuar un caso guardado',loadHint:'Importa un archivo JSON de TraceProof v0.3. Adjunta informes anteriores v0.2 arriba.',footer:'La evidencia no es un veredicto. Sin nube. Sin certeza inventada.',contested:'CONTRADICTORIO',review_required:'REQUIERE REVISIÓN',unresolvedStatus:'NO RESUELTO',support:'A favor',oppose:'En contra',missing:'Pruebas faltantes',none:'Ninguno',success:'Guardado',noActive:'Primero crea un caso',processing:'Procesando localmente…',integrity:'Integridad',provenance:'Procedencia',authorship:'Autoría',context:'Contexto',other:'Otro',noFile:'Sin archivo',selectClaim:'Elegir afirmación',download:'Descargado',verifyDone:'Verificación completa',oversized:'Archivo demasiado grande (máx. 150 MB)',errors:'Error'}
};
let caseFile = null, activeLang = 'en', nextId = 0, busy = false;
const STATUS = {
 en:{contested:'CONTESTED',unresolved:'UNRESOLVED',challenged:'CHALLENGED',supported_contextually:'CONTEXTUALLY SUPPORTED'},
 tr:{contested:'ÇELİŞKİLİ',unresolved:'BELİRSİZ',challenged:'İTİRAZ VAR',supported_contextually:'BAĞLAMSAL DESTEK'},
 es:{contested:'CONTRADICTORIO',unresolved:'NO RESUELTO',challenged:'CUESTIONADO',supported_contextually:'APOYO CONTEXTUAL'}
};
const MISSING = {
 'Collect an independent corroborating source or original file':{tr:'Bağımsız destekleyici kaynak veya orijinal dosya edinin',es:'Obtén una fuente independiente o el archivo original'},
 'Obtain origin records or a verifiable signed content credential':{tr:'Kaynak kayıtları veya doğrulanabilir imzalı içerik kimliği edinin',es:'Obtén registros de origen o credenciales de contenido verificables'},
 'Compare against a separately trusted baseline hash or signed original':{tr:'Bağımsız güvenilen özet değeri veya imzalı orijinal ile karşılaştırın',es:'Compara contra un hash de referencia fiable o el original firmado'},
 'Resolve conflicting observations; do not average them into a score':{tr:'Çelişkili gözlemleri çözümlendirin; puan ortalamasına dönüştürmeyin',es:'Resuelve las contradicciones; no las conviertas en un promedio'},
 'Attach a locally hashed artifact':{tr:'Yerel özeti hesaplanmış bir dosya ekleyin',es:'Adjunta un archivo con hash calculado localmente'}
};
function t(id){ return (I[activeLang] || I.en)[id] || I.en[id] || id; }
function missingText(value){return MISSING[value]?.[activeLang] || value;}
function translations(){document.documentElement.lang = activeLang; document.querySelectorAll('[data-t]').forEach(el=>{if(el.dataset.t !== 'hero')el.textContent=(CMP[activeLang]?.[el.dataset.t]||t(el.dataset.t));});
 document.querySelector('h1').innerHTML = activeLang==='tr'?'Gerçeği tahmin etme.<br><em>Kanıtlanabileni göster.</em>':activeLang==='es'?'No adivines qué es real.<br><em>Muestra lo que puede probarse.</em>':"Don't guess what is real.<br><em>Show what is provable.</em>";
 for(const sel of [$('kind')]) [...sel.options].forEach(opt=>opt.textContent=t(opt.value));
 $('subject').placeholder=activeLang==='tr'?'Örn. Görsel, teslim alındıktan sonra değişti mi?':activeLang==='es'?'Ej. ¿Cambió el archivo tras recibirlo?':'e.g. Was this file modified after receipt?';
 $('claimText').placeholder=activeLang==='tr'?'Bu dosya teslim alınan sürümle birebir aynı.':activeLang==='es'?'El archivo coincide con la versión recibida.':'The file matches the originally received version.';
 $('obsSource').placeholder=activeLang==='tr'?'Gözlemin kaynağı':activeLang==='es'?'Fuente de la observación':'Source of observation';
 $('obsDetails').placeholder=activeLang==='tr'?'Ne gözlemlediniz? Neler belirsiz?':activeLang==='es'?'¿Qué observaste? ¿Qué falta?':'What did you observe? What remains uncertain?';
 $('reportDesc').placeholder=activeLang==='tr'?'Raporun kaynağı ve sınırları':activeLang==='es'?'Fuente y límites del informe':'Report source and limitations';
 render();}
function notify(str){const el=$('toast');el.textContent=str;el.classList.add('show');clearTimeout(notify.timer);notify.timer=setTimeout(()=>el.classList.remove('show'),3600);}
function fail(e){notify(`${t('errors')}: ${e.message||e}`); console.error(e);}
async function api(url,obj,asBlob=false){const res=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)}); if(!res.ok){const err=await res.json().catch(()=>({error:res.statusText}));throw Error(err.error||res.statusText);}return asBlob?res.blob():res.json();}
function uid(prefix){nextId++; return prefix+String(Date.now())+'_'+nextId;}
function active(){if(!caseFile){notify(t('noActive'));return false;}return true;}
async function event(action,payload){if(!active())return;const out=await api('/api/event',{case:caseFile,action,payload});caseFile=out;await render();}
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function node(tag,text,cls){const e=document.createElement(tag);if(text!=null)e.textContent=text;if(cls)e.className=cls;return e;}
function render(){const root=$('artifacts'),state=caseFile?.state;root.replaceChildren();if(!state){root.textContent=t('noneYet');}
 else { $('caseTitle').textContent=state.subject;for(const a of state.artifacts){const r=node('div',null,'fileRow');r.append(node('span','▧','fileicon'));const meta=node('div');meta.append(node('strong',a.name));meta.append(node('small',a.media_type+' · '+(a.size/1024).toFixed(1)+' KB · '+a.sha256.slice(0,24)+'…'));r.append(meta);root.append(r);}if(!state.artifacts.length)root.textContent=t('noneYet');}
 const claimSelect=$('claimSelect'), artSelect=$('artifactSelect');claimSelect.replaceChildren(new Option(t('selectClaim'),''));artSelect.replaceChildren(new Option(t('noFile'),''));if(state){state.claims.forEach(c=>claimSelect.add(new Option(c.statement.slice(0,65),c.id)));state.artifacts.forEach(a=>artSelect.add(new Option(a.name,a.id)));}
 for (const id of ['addClaim','addObservation','downloadCase','bundle']) $(id).disabled=!caseFile;
 if(!caseFile){$('results').replaceChildren(node('div',t('startHint'),'emptyblock'));$('verdict').textContent=t('unresolved');return;}
 return api('/api/evaluate',{case:caseFile}).then(e=>{const results=$('results');results.replaceChildren();$('verdict').textContent=t(e.overall==='unresolved'?'unresolvedStatus':'review_required');if(!e.claim_results.length){results.append(node('div',t('startHint'),'emptyblock'));return;}for(const c of e.claim_results){const el=node('section',null,'claimResult');el.append(node('strong',c.statement));el.append(node('div',(STATUS[activeLang]||STATUS.en)[c.status]||c.status,'claimMeta'));el.append(node('p',t('support')+': '+(c.supporting.join(', ')||t('none')),'yes'));el.append(node('p',t('oppose')+': '+(c.opposing.join(', ')||t('none')),'no'));c.missing.forEach(v=>el.append(node('p','• '+missingText(v),'needed')));results.append(el);}}).catch(fail);
}
$('lang').addEventListener('change',e=>{activeLang=e.target.value;translations();});
$('create').addEventListener('click',async()=>{try{if(!$('subject').value.trim()){notify(t('subjectLabel'));return;}caseFile=await api('/api/new',{subject:$('subject').value.trim()});await render();notify(t('success'));}catch(e){fail(e);}});
async function fileHash(file){if(file.size>150*1024*1024)throw Error(t('oversized'));const bytes=await file.arrayBuffer(),sha=await crypto.subtle.digest('SHA-256',bytes),view=new Uint8Array(sha);return [...view].map(b=>b.toString(16).padStart(2,'0')).join('');}
function sniffFirst(file){return file.slice(0,16).arrayBuffer().then(buf=>{let b=new Uint8Array(buf);if(b[0]===137&&b[1]===80&&b[2]===78&&b[3]===71)return'image/png';if(b[0]===255&&b[1]===216&&b[2]===255)return'image/jpeg';if(String.fromCharCode(...b.slice(0,4))==='%PDF')return'application/pdf';if(String.fromCharCode(...b.slice(0,4))==='RIFF'&&String.fromCharCode(...b.slice(8,12))==='WAVE')return'audio/wav';if(String.fromCharCode(...b.slice(0,4))==='RIFF'&&String.fromCharCode(...b.slice(8,12))==='WEBP')return'image/webp';if(String.fromCharCode(...b.slice(0,4))==='OggS')return'audio/ogg';if(String.fromCharCode(...b.slice(4,8))==='ftyp')return'video/mp4-or-quicktime';if(String.fromCharCode(...b.slice(0,2))==='PK')return'application/zip';return'application/octet-stream';});}
async function addFiles(files){if(!active()||busy)return;busy=true;try{for(const file of files){notify(t('processing'));const hash=await fileHash(file),type=await sniffFirst(file);await event('artifact_added',{id:uid('artifact_'),name:file.name.slice(0,500),size:file.size,sha256:hash,media_type:type});}notify(t('success'));}catch(e){fail(e);}finally{busy=false;$('files').value='';}}
$('drop').addEventListener('click',()=>$('files').click());$('drop').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('files').click();}});$('files').addEventListener('change',e=>addFiles(e.target.files));$('drop').addEventListener('dragover',e=>{e.preventDefault();$('drop').classList.add('hover');});$('drop').addEventListener('dragleave',()=>$('drop').classList.remove('hover'));$('drop').addEventListener('drop',e=>{e.preventDefault();$('drop').classList.remove('hover');addFiles(e.dataTransfer.files);});
$('addClaim').addEventListener('click',async()=>{if(!active())return;try{const value=$('claimText').value.trim();if(!value)return;await event('claim_added',{id:uid('claim_'),statement:value,kind:$('kind').value});$('claimText').value='';}catch(e){fail(e);}});
$('addObservation').addEventListener('click',async()=>{if(!active())return;try{const details=$('obsDetails').value.trim();if(!$('claimSelect').value||!$('obsSource').value.trim())return notify(t('observation'));await event('observation_added',{id:uid('obs_'),claim_id:$('claimSelect').value,artifact_id:$('artifactSelect').value||null,source:$('obsSource').value.trim(),state:$('obsState').value,trust:'contextual',details:{note:details}});$('obsDetails').value='';$('obsSource').value='';}catch(e){fail(e);}});
$('report').addEventListener('change',async e=>{if(!active()||!e.target.files.length)return;try{const f=e.target.files[0],hash=await fileHash(f);await event('report_attached',{id:uid('report_'),sha256:hash,name:f.name,summary:$('reportDesc').value.trim()||'External report, not independently validated by ProofGraph'});notify(t('success'));e.target.value='';}catch(err){fail(err);}});
$('downloadCase').addEventListener('click',()=>{if(!active())return;download(new Blob([JSON.stringify(caseFile,null,2)],{type:'application/json'}),'traceproof-case-v0.3.json');});
$('bundle').addEventListener('click',async()=>{if(!active())return;try{const zip=await api('/api/pack',{case:caseFile},true);download(zip,'traceproof-proofbundle-v0.3.zip');}catch(e){fail(e);}});
$('verifyFile').addEventListener('change',async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>5_000_000)throw Error('Verification upload exceeds UI limit (5 MB); use CLI for larger bundles');const url=await new Promise((res,rej)=>{const reader=new FileReader();reader.onload=()=>res(reader.result);reader.onerror=rej;reader.readAsDataURL(f);});const out=await api('/api/verify',{bundle_base64:url.split(',',2)[1]});$('verifyOutput').textContent=JSON.stringify(out,null,2);notify(t('verifyDone'));}catch(err){$('verifyOutput').textContent=String(err.message||err);fail(err);}});
$('loadCase').addEventListener('change',async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>5_000_000)throw Error('Case JSON exceeds 5 MB');const candidate=JSON.parse(await f.text());await api('/api/evaluate',{case:candidate});caseFile=candidate;await render();notify(t('success'));}catch(err){fail(err);}});
translations();

async function base64File(file){
 if(!file||file.size>3_000_000)throw Error('Select files up to 3 MB each');
 const bytes=new Uint8Array(await file.arrayBuffer());let binary='';
 for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
 return {name:file.name.slice(0,200),base64:btoa(binary)};
}
$('compareBtn').addEventListener('click',async()=>{
 const output=$('compareOutput');output.textContent=t('processing');
 try{
  const left=await base64File($('compareLeft').files[0]);
  const right=await base64File($('compareRight').files[0]);
  const result=await api('/api/compare',{left,right});
  output.textContent=JSON.stringify({relation:result.relation,sha256_left:result.left.sha256,sha256_right:result.right.sha256,text_similarity:result.text_similarity,image_hamming_distance:result.image_hamming_distance,crop_hamming_distance:result.crop_hamming_distance,direction:result.direction,warning:result.warning},null,2);
 }catch(e){output.textContent=String(e.message||e);fail(e);}
});

// Batch relationship graph: fixed positions, no remote graph dependencies, textContent-only labels.
let latestGraph=null;
const GRAPH_I={
 en:{scanTitle:'Relationship graph · batch scan',scanInfo:'Select up to 40 files (1 MB each). An edge is a candidate relationship, not provenance proof.',scanBtn:'Build graph',graphExport:'Export graph JSON'},
 tr:{scanTitle:'İlişki grafiği · toplu tarama',scanInfo:'En fazla 40 dosya (her biri 1 MB). Bağlantılar kesin köken kanıtı değildir.',scanBtn:'Grafik oluştur',graphExport:'Grafiği JSON olarak indir'},
 es:{scanTitle:'Grafo de relaciones · análisis por lotes',scanInfo:'Hasta 40 archivos (1 MB cada uno). Las conexiones no prueban procedencia.',scanBtn:'Crear grafo',graphExport:'Exportar grafo JSON'}
};
for(const [lang,keys] of Object.entries(GRAPH_I))Object.assign(I[lang],keys);
function drawGraph(result){
 latestGraph=result;$('graphExport').disabled=false;
 const host=$('graph');host.replaceChildren();
 const n=result.files.length,edges=result.edges;
 $('graphSummary').textContent=`${n} files · ${edges.length} relationships · direction unknown`;
 const ns='http://www.w3.org/2000/svg';
 const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 720 420');svg.setAttribute('role','img');svg.setAttribute('aria-label','File relationships');
 const pos=result.files.map((_,i)=>({x:360+285*Math.cos(2*Math.PI*i/Math.max(n,1)-Math.PI/2),y:210+165*Math.sin(2*Math.PI*i/Math.max(n,1)-Math.PI/2)}));
 for(const edge of edges){const a=pos[edge.left],b=pos[edge.right];if(!a||!b)continue;const line=document.createElementNS(ns,'line');for(const [k,v] of Object.entries({x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:'#56c3c7','stroke-width':2}))line.setAttribute(k,v);svg.append(line);}
 for(let i=0;i<n;i++){const p=pos[i],g=document.createElementNS(ns,'g');const circle=document.createElementNS(ns,'circle');for(const [k,v] of Object.entries({cx:p.x,cy:p.y,r:Math.max(6,Math.min(15,220/Math.max(n,1))),fill:'#70a7ff'}))circle.setAttribute(k,v);const title=document.createElementNS(ns,'title');title.textContent=result.files[i].name;g.append(circle,title);svg.append(g);}
 host.append(svg);
 const list=$('graphEdges');list.replaceChildren();for(const edge of edges){const row=document.createElement('div');row.className='fileRow';row.textContent=`${result.files[edge.left].name} ↔ ${result.files[edge.right].name} · ${edge.relation}`;list.append(row);}
 if(!edges.length)list.textContent='No matching relationships detected.';
}
$('scanBtn').addEventListener('click',async()=>{
 const files=[...$('scanFiles').files];try{
  if(!files.length||files.length>40)throw Error('Select 1–40 files');
  if(files.some(f=>f.size>1_000_000))throw Error('Each file must be 1 MB or smaller');
  $('graphSummary').textContent=t('processing');
  const items=[];for(const f of files)items.push(await base64File(f));
  drawGraph(await api('/api/scan',{files:items}));
 }catch(e){$('graphSummary').textContent=String(e.message||e);fail(e);}
});
$('graphExport').addEventListener('click',()=>{if(latestGraph)download(new Blob([JSON.stringify(latestGraph,null,2)],{type:'application/json'}),'traceproof-relationship-graph.json');});
translations();