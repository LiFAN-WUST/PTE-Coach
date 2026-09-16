import {$,node} from './api.js';
import {wave} from './charts.js';
import {contentGroups,phoneAdvice} from './feedback.js';
import {pronunciation} from './pronunciation.js';
let stopAt=null;
$('playback').addEventListener('timeupdate',()=>{if(stopAt!==null&&$('playback').currentTime>=stopAt){$('playback').pause();stopAt=null;}});
export function play(start=0,end=null){const a=$('playback');a.currentTime=Math.max(0,start);stopAt=end;a.play().catch(()=>{});}
function listen(start,end,duration){const b=node('button','▶ 听这一段','secondary');b.disabled=start==null||end==null;b.onclick=()=>play(Math.max(0,start-.3),Math.min(duration,end+.4));if(b.disabled)b.textContent='请用下方播放器复听全文';return b;}
function practice(text,mode='word'){const b=node('button','单独练「'+text+'」','primary');b.onclick=()=>{const select=$('taskType');select.value=mode==='word'&&text.trim().split(/\s+/).length>5?'read_aloud':mode;select.dispatchEvent(new Event('change'));$('reference').value=text;$('reference').oninput();$('reference').focus();$('reference').scrollIntoView({block:'center',behavior:'smooth'});};return b;}
function card(label,title,detail){const c=node('div',undefined,'summaryCard');c.append(node('small',label),node('h3',title),node('p',detail));$('scoreCards').append(c);}
function action(title,detail,tip,start,end,r,target,mode){const c=node('article',undefined,'practiceAction');c.append(node('h3',title),node('p',detail),node('p',tip,'nextStep'));const buttons=node('div',undefined,'actionButtons');buttons.append(listen(start,end,r.duration));if(target)buttons.append(practice(target,mode));c.append(buttons);$('coaching').append(c);}
export function render(row){
 const r=row.result;if(!r)return;
 window.history.replaceState({},'','?attempt='+encodeURIComponent(row.id));
 $('result').hidden=false;$('reanalyze').dataset.id=row.id;$('export').href='/api/attempts/'+row.id+'/export';
 $('playback').pause();stopAt=null;$('playback').src='/api/attempts/'+row.id+'/audio';
 for(const id of ['scoreCards','coaching','contentReview','metrics','scoreEvidence'])$(id).replaceChildren();
 const targeted=['word','phoneme'].includes(r.task_type),groups=contentGroups(r),f=r.features;
 const candidates=(r.pronunciation?.validation?.diagnostic_ready===true?r.pronunciation.words:[]).map(w=>({w,advice:phoneAdvice(w)})).filter(x=>x.advice);
 $('scoreNotice').textContent='先看下面的练习重点。机器也会听错，点击录音确认后再练；这里不提供 PTE 考试分数。'+(r.pronunciation?.validation?.note||'这份发音分析尚未经过人工评分对照验证，只供复听参考。');
 $('contentSection').hidden=targeted;$('measurementSection').hidden=targeted;
 if(targeted){
  const detected=r.pronunciation?.words?.some(w=>['matched','target_detected'].includes(w.status));
  card('这次练习',row.reference,'录音 '+r.duration.toFixed(1)+' 秒');
  card('机器的判断',detected?'听到了目标读音':candidates.length?'有一处值得复听':'这次还拿不准',detected?'识别到了相应声音，还需要听录音确认是否自然清楚。':'拿不准不代表你读错。孤立的音比完整单词更容易识别失败。');
 }else{
  card('朗读内容',groups.length?groups.length+' 处文字需要核对':'转写与原文一致',groups.length?'机器听到的文字与原文不同；可能是朗读差异，也可能是识别错误。':'机器识别的文字与原文相符，仍不能据此判断发音都正确。');
  card('朗读节奏',f.abnormal_pause_count?'有 '+f.abnormal_pause_count+' 处停顿值得听听':'未标出明显的句内长停顿','约每分钟 '+f.wpm+' 个词。这只是速度和停顿的观察，不是流利度分数。');
 }
 const first=groups[0];
 if(first)action('先核对这句：'+(first.expected||'可能多读的内容'),'原文：'+(first.expected||'这里没有这些词')+'。机器听成：'+(first.heard||'没有识别到对应文字')+'。','先听录音。如果确实读得不清楚，慢读这段两遍，再放回整句。',first.start,first.end,r,first.expected||null);
 if(candidates.length){const {w,advice}=candidates[0];action('再听「'+w.word+'」的发音',advice.text+' 这是机器的疑似提示，还没有确认你读错。',advice.tip,w.start,w.end,r,w.word,r.task_type==='phoneme'?'phoneme':'word');}
 if(!targeted&&f.abnormal_pauses?.length){const p=f.abnormal_pauses[0];action('听听这里是否停得太久',p.after_word+' → '+p.before_word+'，间隔约 '+p.duration.toFixed(1)+' 秒。','如果这里应该连着读，先把前后两个词放进短语练习。',p.start-.3,p.end+.3,r,null);}
 else if(groups.length>1){const g=groups[1];action('接着核对：'+(g.expected||'可能多读的内容'),'原文：'+(g.expected||'无')+'。机器听成：'+(g.heard||'未识别到')+'。','只改复听后确认的问题，不需要追着机器的每条标记改。',g.start,g.end,r,g.expected||null);}
 if(!$('coaching').children.length){const w=r.pronunciation?.words?.[0];action(targeted?'先听一遍自己的录音':'先复听，再换一段材料',targeted?'目前没有足够把握指出具体发音错误。':'这次没有筛出足够可靠的优先练习项，这不等于所有发音都正确。',targeted?(r.coach?.actions?.[0]?.detail||'把目标放进常用例词里，再录一次。'):'听听是否清楚连贯，再用一段新材料检验。',0,r.duration,r,targeted?row.reference:null,r.task_type);}
 $('moreReview').textContent=groups.length>1?'全部文字差异可在下方展开查看。':'每次先练上面的重点就够了，不必处理所有机器标记。';
 $('contentReview').append(node('p','下面是机器转写与原文的差异，尚未经人工确认。','hint'));
 for(const g of groups){const c=node('article',undefined,'phraseReview');c.append(node('p','你要读：'+(g.expected||'这里没有额外的词')),node('p','机器听成：'+(g.heard||'未识别到对应文字')),listen(g.start,g.end,r.duration));$('contentReview').append(c);}
 if(!groups.length)$('contentReview').append(node('p','机器转写与原文一致。'));
 wave($('waveform'),r.waveform,r.duration,f?.abnormal_pauses||[]);$('duration').textContent=r.duration.toFixed(1)+' 秒';
 $('waveform').onclick=e=>{const box=e.currentTarget.getBoundingClientRect();play((e.clientX-box.left)/box.width*r.duration);};
 pronunciation(r,play,r.duration);
 if(f)for(const [label,value] of [['录音时长',r.duration.toFixed(1)+' 秒'],['语速',f.wpm+' 词/分钟'],['检测到的停顿',f.pause_count+' 次'],['最长停顿',f.max_pause_duration+' 秒']]){const d=node('div',undefined,'metric');d.append(node('span',label),node('strong',value));$('metrics').append(d);}
 $('scoreEvidence').append(node('p','旧版显示的训练指数只计算内容与节奏，不包含本地发音分析，容易误解，所以不再放在主结果页。以下保留原始记录，方便核查。'),node('pre',JSON.stringify(r.scores,null,2)));
 $('provenance').textContent=JSON.stringify({provenance:r.provenance,warnings:r.warnings,quality:r.quality},null,2);
}
