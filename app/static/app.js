import {$,api,node} from './api.js';
import {Recorder} from './recorder.js';
import {render} from './results.js';
import {trend} from './charts.js';
const recorder=new Recorder();let blob=null,previewURL=null,recording=false,starting=false,busy=false,pollTimer=null;
function status(message,error=false){$('status').textContent=message;$('status').className=error?'error':'';}
function setTake(value){blob=value;if(previewURL)URL.revokeObjectURL(previewURL);previewURL=URL.createObjectURL(blob);$('preview').src=previewURL;$('take').hidden=false;}
function buttons(){ $('taskType').disabled=recording||busy;for(const b of document.querySelectorAll('[data-ipa]'))b.disabled=recording||busy; $('reanalyze').disabled=recording||busy; $('record').disabled=recording||busy;$('stop').disabled=!recording||starting;$('analyze').disabled=recording||busy;$('upload').disabled=recording||busy;$('reference').disabled=recording||busy; }
const drafts={read_aloud:$('reference').value,word:'think',phoneme:'/θ/'};let currentMode='read_aloud';
function updateMode(reset=false){
  if(reset){drafts[currentMode]=$('reference').value;currentMode=$('taskType').value;$('reference').value=drafts[currentMode];blob=null;$('take').hidden=true;if(previewURL){URL.revokeObjectURL(previewURL);previewURL=null;}$('preview').removeAttribute('src');$('result').hidden=true;}
  $('recordHint').textContent=$('taskType').value==='read_aloud'?'自然出声，保持平常音量。支持录音或上传，最长 120 秒。':'自然发声，建议录 1–3 秒。单词与音标专项最长 20 秒。';
  $('ipaPicker').hidden=$('taskType').value!=='phoneme';
  $('modeHint').textContent={read_aloud:'原文可以自由修改或粘贴，3–200 个英文词。',word:'输入 1–5 个英文词；专项录音最长 20 秒，提供发音提示。',phoneme:'直接输入英语音标，例如 /θ/、/ð/。每次录 1–3 秒，最长 20 秒；不评元音长短或重音。'}[$('taskType').value];
  $('reference').placeholder=$('taskType').value==='phoneme'?'/θ/ 或 /ð/':'输入你想读的英文';$('reference').oninput();
}
$('reference').oninput=()=>{$('wordCount').textContent=$('taskType').value==='phoneme'?'英语音标':($('reference').value.match(/[a-z]+(?:'[a-z]+)?|\d+/gi)||[]).length+' 个词';};
$('taskType').onchange=()=>{updateMode(true);status('练习内容已切换，录一段新的声音吧。');};
for(const b of document.querySelectorAll('[data-ipa]'))b.onclick=()=>{$('reference').value=b.dataset.ipa;$('reference').oninput();};
function loadReference(row){currentMode=row.task_type||'read_aloud';$('taskType').value=currentMode;$('reference').value=row.reference;updateMode();}
updateMode();
$('record').onclick=async()=>{try{recording=true;starting=true;buttons();await recorder.start(seconds=>{$('timer').textContent=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;if(seconds>=($('taskType').value==='read_aloud'?119:19)&&recording)$('stop').click();});starting=false;buttons();status('正在录音。按自己的节奏读完即可。');}catch(e){recording=false;starting=false;buttons();status(e.message,true);}};
$('stop').onclick=async()=>{recording=false;buttons();try{const result=await recorder.stop();if(result?.size){setTake(result);status('录音已就绪，可以先试听。');}}catch(e){status(e.message,true);}};
$('upload').onchange=e=>{const file=e.target.files[0];if(file){if(file.size>20*1024*1024){status('音频最大 20 MiB。',true);return;}setTake(file);status('音频已就绪。');}};
async function poll(id){try{const row=await api('/attempts/'+id);if(['queued','processing'].includes(row.status)){status(row.status==='queued'?'排队中…':'正在本机分析：转写、声学特征、音素对照与训练反馈。');pollTimer=setTimeout(()=>poll(id),1200);return;}busy=false;buttons();if(row.status==='done'){render(row);status('分析完成。先看最优先的练习建议。');}else{$('result').hidden=true;status(row.error||row.result?.quality?.reasons?.join(' ')||'本次无法评分。',true);}}catch(e){busy=false;buttons();status(e.message+' 可在训练记录中查看任务状态。',true);}}
$('analyze').onclick=async()=>{if(!blob)return;busy=true;buttons();$('result').hidden=true;status('正在保存录音…');try{const form=new FormData();form.append('reference',$('reference').value);form.append('task_type',$('taskType').value);form.append('audio',blob,'recording');const job=await api('/attempts',{method:'POST',body:form});await poll(job.id);}catch(e){busy=false;buttons();status(e.message,true);}};
function view(history){$('practiceView').hidden=history;$('historyView').hidden=!history;$('practiceNav').classList.toggle('active',!history);$('historyNav').classList.toggle('active',history);}
async function loadHistory(){try{const [rows,profile]=await Promise.all([api('/attempts'),api('/profile')]);trend($('trend'),profile.series);$('history').replaceChildren();if(!rows.length)$('history').append(node('p','还没有练习记录，先完成一段朗读吧。','muted'));for(const row of rows){const el=node('div',undefined,'historyRow');const desc=node('div');desc.append(node('small',new Date(row.created_at).toLocaleString()+' · '+({done:'已完成',failed:'分析失败',rejected:'需要重录',queued:'排队中',processing:'分析中'}[row.status]||row.status)),node('p',row.reference));const actions=node('div',undefined,'historyActions');const open=node('button','查看','secondary');open.onclick=async()=>{try{const full=await api('/attempts/'+row.id);view(false);loadReference(full);if(full.status==='done'){render(full);status('历史练习 · '+new Date(full.created_at).toLocaleString());}else{status(full.error||full.result?.quality?.reasons?.join(' ')||'任务仍在处理中。',true);$('result').hidden=true;}}catch(e){status(e.message,true);}};const del=node('button','删除','secondary');del.disabled=['queued','processing'].includes(row.status);del.onclick=async()=>{if(!confirm('删除这条记录及对应音频？'))return;try{await api('/attempts/'+row.id,{method:'DELETE'});await loadHistory();}catch(e){status(e.message,true);}};actions.append(open,del);el.append(desc,actions);$('history').append(el);}}catch(e){$('history').textContent=e.message;}}
$('historyNav').onclick=()=>{view(true);loadHistory();};$('practiceNav').onclick=()=>view(false);$('refresh').onclick=loadHistory;
api('/config').then(c=>{$('privacy').textContent=c.cloud_enabled?'已启用云端：配置的评测／教练可发送数据':'本地分析 · 不向云端发送录音';}).catch(e=>status(e.message,true));
window.addEventListener('beforeunload',()=>{recorder.cleanup();clearTimeout(pollTimer);if(previewURL)URL.revokeObjectURL(previewURL);});
const initialAttempt=new URLSearchParams(window.location.search).get('attempt');
if(initialAttempt&&/^[a-f0-9]{32}$/.test(initialAttempt)){api('/attempts/'+initialAttempt).then(row=>{if(row.status==='done'){render(row);loadReference(row);status('已打开这次录音的分析结果。');}else{status('这条记录暂时没有完成的结果。');}}).catch(e=>status(e.message,true));}

$('reanalyze').onclick=async()=>{const id=$('reanalyze').dataset.id;if(!id||busy||recording)return;busy=true;buttons();status('正在用当前模型重新分析，原记录会保留。');try{const job=await api('/attempts/'+id+'/reanalyze',{method:'POST'});await poll(job.id);}catch(e){busy=false;buttons();status(e.message,true);}};
