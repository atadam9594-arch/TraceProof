'use strict';
const $ = id => document.getElementById(id);
const maxFile = 250000000;
const translations = {
 en: {
   back: '← ProofGraph', heading: 'Compare video evidence', intro: 'Inspect potential visual overlaps between video files without sending them to an external service. A match is not proof of origin or authenticity.',
   choose: 'Select two videos', limit: 'Up to 250 MB per file; transferred to temporary storage on this computer in 1 MB chunks. FFmpeg and Pillow are required.',
   leftLabel: 'First video', rightLabel: 'Second video', samplesLabel: 'Frames sampled per video', run: 'Analyze videos', cancel: 'Cancel',
   progressTitle: 'Local transfer progress', ready: 'Ready to upload on your device', privacy: 'Source videos are discarded when processing finishes or the session is cancelled. Only the comparison report remains temporarily accessible.',
   resultTitle: 'Analysis results', idle: 'No analysis yet.', save: 'Export results (JSON)', limitsHeading: 'What this analysis can and cannot show',
   limitsText: 'Frame fingerprints are heuristic. Sparse sampling can miss edits or produce false matches. This tool cannot identify who created a video, determine editing direction or certify that content is AI-generated.',
   invalid: 'Select two MP4, MOV, MKV or WebM files (1–250 MB each).', uploading: 'Transferring to local temporary storage', analyzing: 'Video decoding and comparison in progress (no estimated percentage)',
   complete: 'Analysis complete — candidate matches are not provenance proof.', cancelled: 'Analysis cancelled and temporary data discarded.', failed: 'Analysis failed',
   setup: 'Video comparison requires FFmpeg/ffprobe and Pillow installed locally. Install the tools to enable analysis.', retry: 'Try again', status: 'Status', relation: 'Relationship', leftDuration: 'First video duration (s)', rightDuration: 'Second video duration (s)', matched: 'Sample matches', warning: 'Important limitation'
 },
 tr: {
   back: '← ProofGraph', heading: 'Video kanıtlarını karşılaştır', intro: 'Videolardaki olası görsel eşleşmeleri herhangi bir dış hizmete göndermeden inceleyin. Eşleşme, kaynak veya özgünlük kanıtı değildir.',
   choose: 'İki video seçin', limit: 'Dosya başına en fazla 250 MB; bu bilgisayardaki geçici alana 1 MB parçalar halinde aktarılır. FFmpeg ve Pillow gereklidir.',
   leftLabel: 'İlk video', rightLabel: 'İkinci video', samplesLabel: 'Video başına örnek kare', run: 'Videoları analiz et', cancel: 'İptal et',
   progressTitle: 'Yerel aktarım ilerlemesi', ready: 'Bu cihazda yüklemeye hazır', privacy: 'Video dosyaları işlem bittiğinde veya oturum iptal edildiğinde geçici alandan silinir. Yalnızca karşılaştırma sonucu kısa süre erişilebilir kalır.',
   resultTitle: 'Analiz sonuçları', idle: 'Henüz analiz yapılmadı.', save: 'Sonuçları dışa aktar (JSON)', limitsHeading: 'Bu analiz neleri gösterir?',
   limitsText: 'Kare parmak izleri sezgiseldir. Seyrek örnekleme değişiklikleri kaçırabilir veya yanlış eşleşmeler üretebilir. Bu araç videoyu kimin oluşturduğunu, düzenleme yönünü veya yapay zekâ ile üretilip üretilmediğini kanıtlayamaz.',
   invalid: '1–250 MB arasında iki MP4, MOV, MKV veya WebM dosyası seçin.', uploading: 'Yerel geçici alana aktarılıyor', analyzing: 'Video kareleri işlenip karşılaştırılıyor (tahmini yüzde yok)',
   complete: 'Analiz tamamlandı — olası eşleşmeler köken kanıtı değildir.', cancelled: 'İşlem iptal edildi; geçici veri silindi.', failed: 'Analiz başarısız',
   setup: 'Video karşılaştırması için FFmpeg/ffprobe ve Pillow bu bilgisayarda kurulu olmalı. Analizi etkinleştirmek için bunları kurun.', retry: 'Tekrar dene', status: 'Durum', relation: 'İlişki', leftDuration: 'İlk video süresi (sn)', rightDuration: 'İkinci video süresi (sn)', matched: 'Örnek eşleşmeleri', warning: 'Önemli sınırlama'
 },
 es: {
   back: '← ProofGraph', heading: 'Comparar evidencia de video', intro: 'Examine posibles coincidencias visuales sin enviar archivos a servicios externos. Una coincidencia no prueba el origen ni la autenticidad.',
   choose: 'Seleccione dos videos', limit: 'Hasta 250 MB por archivo; transferidos al almacenamiento temporal de este equipo en bloques de 1 MB. Requiere FFmpeg y Pillow.',
   leftLabel: 'Primer video', rightLabel: 'Segundo video', samplesLabel: 'Fotogramas muestreados por video', run: 'Analizar videos', cancel: 'Cancelar',
   progressTitle: 'Progreso de la transferencia local', ready: 'Preparado para transferir en este equipo', privacy: 'Los videos originales se eliminan del almacenamiento temporal al finalizar o cancelar. Solo el informe permanece accesible brevemente.',
   resultTitle: 'Resultados', idle: 'Sin análisis todavía.', save: 'Exportar resultados (JSON)', limitsHeading: 'Límites de este análisis',
   limitsText: 'Las huellas de fotogramas son heurísticas. El muestreo puede omitir cambios o producir coincidencias falsas. La herramienta no demuestra autoría, dirección de edición ni generación por IA.',
   invalid: 'Seleccione dos archivos MP4, MOV, MKV o WebM de 1–250 MB.', uploading: 'Transfiriendo al almacenamiento temporal local', analyzing: 'Procesando y comparando fotogramas (sin porcentaje estimado)',
   complete: 'Análisis terminado: las coincidencias no prueban procedencia.', cancelled: 'Análisis cancelado; datos temporales eliminados.', failed: 'Análisis fallido',
   setup: 'Se necesitan FFmpeg/ffprobe y Pillow instalados localmente. Instálelos para habilitar el análisis.', retry: 'Intentar de nuevo', status: 'Estado', relation: 'Relación', leftDuration: 'Duración del primero (s)', rightDuration: 'Duración del segundo (s)', matched: 'Coincidencias muestreadas', warning: 'Limitación importante'
 }
};
let activeSession = null;
let requestController = null;
let stopped = false;
let latest = null;
function t() { return translations[$('lang').value] || translations.en; }
function translate() {
 const local = t();
 document.documentElement.lang = $('lang').value;
 for (const id of ['back', 'heading', 'intro', 'choose', 'limit', 'leftLabel', 'rightLabel', 'samplesLabel', 'run', 'cancel', 'progressTitle', 'privacy', 'resultTitle', 'save', 'limitsHeading', 'limitsText']) $(id).textContent = local[id];
}
$('lang').addEventListener('change', translate);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function json(endpoint, data) {
 const response = await fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data), signal:requestController?.signal});
 const result = await response.json();
 if (!response.ok) throw Error(result.error || ('HTTP ' + response.status));
 return result;
}
function showResult(result) {
 const local = t();
 const overview = {
   [local.relation]: result.relation,
   [local.leftDuration]: result.left.duration_seconds,
   [local.rightDuration]: result.right.duration_seconds,
   [local.matched]: result.matched_samples,
   [local.warning]: result.warning
 };
 $('output').textContent = JSON.stringify(overview, null, 2);
 $('save').disabled = false;
}
async function cancelSession() {
 stopped = true;
 if (requestController) requestController.abort();
 if (activeSession) {
   // Do not reuse an aborted controller for cancellation.
   try { await fetch('/api/video/cancel', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session:activeSession})}); } catch (_) {}
 }
 activeSession = null;
 $('cancel').disabled = true;
 $('run').disabled = false;
 $('status').textContent = t().cancelled;
 $('progressText').textContent = t().cancelled;
}
$('cancel').addEventListener('click', cancelSession);
$('run').addEventListener('click', async () => {
 const a = $('left').files[0], b = $('right').files[0];
 const valid = f => f && f.size > 0 && f.size <= maxFile && /\.(mp4|mov|mkv|webm)$/i.test(f.name);
 if (!valid(a) || !valid(b)) { $('status').textContent = t().invalid; return; }
 $('run').disabled = true;
 $('cancel').disabled = false;
 $('save').disabled = true;
 $('progress').value = 0;
 $('output').textContent = '';
 stopped = false;
 latest = null;
 requestController = new AbortController();
 try {
   const session = await json('/api/video/session', {left:{name:a.name,size:a.size}, right:{name:b.name,size:b.size}, samples:Number($('samples').value)});
   activeSession = session.session;
   const total = a.size + b.size;
   let sent = 0;
   for (const [side, file] of [['left', a], ['right', b]]) {
     for (let offset = 0; offset < file.size; offset += session.chunk_bytes) {
       if (stopped) throw Error('cancelled');
       const size = Math.min(session.chunk_bytes, file.size - offset);
       const response = await fetch('/api/video/chunk', {
         method:'POST', headers:{'Content-Type':'application/octet-stream', 'X-TraceProof-Session':activeSession, 'X-TraceProof-Side':side, 'X-TraceProof-Offset':String(offset)},
         body:file.slice(offset, offset + size),signal:requestController.signal
       });
       const res = await response.json();
       if (!response.ok) throw Error(res.error || 'Transfer failed');
       sent += size;
       const percent = Math.floor(sent / total * 100);
       $('progress').value = percent;
       $('progressText').textContent = `${t().uploading}: ${percent}%`;
     }
   }
   if (stopped) throw Error('cancelled');
   await json('/api/video/start', {session:activeSession});
   $('status').textContent = t().analyzing;
   $('progressText').textContent = t().analyzing;
   for (;;) {
     if (stopped) throw Error('cancelled');
     await sleep(1100);
     const progress = await json('/api/video/status', {session:activeSession});
     if (progress.status === 'done') {
       latest = progress.result;
       showResult(latest);
       $('status').textContent = t().complete;
       break;
     }
     if (progress.status === 'failed' || progress.status === 'cancelled') throw Error(progress.error || progress.status);
   }
 } catch (error) {
   if (!stopped) {
     $('status').textContent = t().failed + ': ' + String(error.message || error);
     if (activeSession) {
       try { await fetch('/api/video/cancel', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session:activeSession})}); } catch (_) {}
     }
   }
 } finally {
   $('run').disabled = false;
   $('cancel').disabled = true;
   activeSession = null;
   requestController = null;
 }
});
$('save').addEventListener('click', () => {
 if (!latest) return;
 const url = URL.createObjectURL(new Blob([JSON.stringify(latest, null, 2)], {type:'application/json'}));
 const link = document.createElement('a'); link.href = url; link.download = 'traceproof-video-report.json'; link.click();
 setTimeout(() => URL.revokeObjectURL(url), 1000);
});
translate();
fetch('/api/video/capabilities').then(r => r.ok ? r.json() : Promise.reject(Error('capabilities'))).then(d => {
 if (!d.video_analysis_available) {
   $('run').disabled = true;
   $('status').textContent = t().setup;
 }
}).catch(() => { $('status').textContent = t().setup; });