import {$,node} from './api.js';
import {phoneAdvice} from './feedback.js';
const labels={matched:'没有标出明确差异',target_detected:'听到了目标音，还需复听',review:'机器有疑问，请复听',uncertain:'系统拿不准',unsupported:'暂时不支持这个词',content_mismatch:'先核对有没有读清这个词'};
export function pronunciation(result,play,duration){
 const p=result.pronunciation||{words:[]};
 $('pronunciationNotice').textContent='这一栏是补充信息，可以先不看。「系统拿不准」不代表你读错；「未检出」也不代表你漏读。';
 $('pronunciationWords').replaceChildren();$('phonemeDetail').replaceChildren();
 if(!p.words?.length){$('pronunciationNotice').textContent='本次没有可用的发音分析。'+(p.reason||'可以先听原录音，再重新录制。');return;}
 for(const w of p.words){
  const b=node('button',w.word,'word');b.onclick=()=>{
   $('phonemeDetail').replaceChildren();const advice=phoneAdvice({...w,diagnostic_ready:p.validation?.diagnostic_ready===true});
   $('phonemeDetail').append(node('h3',w.word),node('p',advice?advice.text+' 机器只是提出疑问，需要听录音确认。':labels[w.status]||'请结合录音判断。'));
   if(advice)$('phonemeDetail').append(node('p',advice.tip));
   else if(w.status==='review')$('phonemeDetail').append(node('p','模型标记了差异，但暂时无法给出可靠、具体的纠正建议。先不要照着它改读音。'));
   const start=w.start,end=w.end??(w.duration!=null?start+w.duration:null);const listen=node('button','▶ 听这个词及前后文','secondary');listen.disabled=start==null||end==null;listen.onclick=()=>play(Math.max(0,start-.3),Math.min(duration,end+.4));$('phonemeDetail').append(listen);
   const detail=node('details',undefined,'phoneEvidence');detail.append(node('summary','查看音标对照（可跳过）'));
   if(w.phonemes){const table=node('table',undefined,'phoneTable');const header=node('tr');for(const t of ['目标声音','机器识别','怎么理解'])header.append(node('th',t));table.append(header);for(const ph of w.phonemes){const row=node('tr');row.append(node('td',ph.expected||'无对应目标'),node('td',ph.heard||'机器没识别到'),node('td',labels[ph.status]||'请复听'));table.append(row);}detail.append(table);}
   else detail.append(node('pre',JSON.stringify(w,null,2)));
   detail.append(node('p','音标来自词典或你的输入。模型可能识别错，也未覆盖所有口音、弱读和连读。','hint'));$('phonemeDetail').append(detail);
  };$('pronunciationWords').append(b);
 }
}
