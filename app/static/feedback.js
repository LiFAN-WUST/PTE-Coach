// Presentation only: preserve measurements and never turn a model flag into a verdict.
export function contentGroups(r){
 const groups=[];let group=null;
 for(const op of r.comparison?.operations||[]){
  if(op.kind==='match'){group=null;continue;}
  if(!group){group={expected:[],heard:[],start:null,end:null};groups.push(group);}
  if(op.reference)group.expected.push(op.reference);
  if(op.spoken)group.heard.push(op.spoken);
  const word=op.spoken_index!=null?r.features?.words?.[op.spoken_index]:null;
  if(word?.start!=null){group.start=group.start==null?word.start:Math.min(group.start,word.start);group.end=Math.max(group.end??0,word.end??word.start);}
 }
 return groups.map(g=>({...g,expected:g.expected.join(' '),heard:g.heard.join(' ')}));
}
const contrasts={
 'θ:s':{text:'检查 th 有没有读得像 s。',tip:'舌尖轻放上下齿之间，让气流通过；先练 think，再读这个词。'},
 'θ:t':{text:'检查 th 有没有读得像 t。',tip:'让气流持续通过舌齿之间，不要一下把气流堵住。'},
 'ð:d':{text:'检查 this 里的 th 有没有读得像 d。',tip:'舌尖轻触上下齿之间，保持气流和声带振动；先练 this。'},
 'ð:z':{text:'检查 this 里的 th 有没有读得像 z。',tip:'舌尖轻触上下齿之间，保持声带振动；先练 this，再读这个词。'},
 'w:v':{text:'检查 w 有没有读得像 v。',tip:'发 w 时先把嘴唇收圆，再打开；不要让上齿接触下唇。'},
 'v:w':{text:'检查 v 有没有读得像 w。',tip:'发 v 时让上齿轻触下唇，保持气流和声带振动。'},
 'ɹ:l':{text:'检查 r 有没有读得像 l。',tip:'发英语 r 时，舌尖不要顶住上齿后方；放进 red 里练习。'},
 'l:ɹ':{text:'检查 l 有没有读得像 r。',tip:'发 l 时舌尖轻触上齿后方；放进 light 里练习。'}
};
export function phoneAdvice(word){
 if(word.diagnostic_ready===false)return null;
 for(const p of word.phonemes||[]){if(p.status==='review'&&contrasts[p.expected+':'+p.heard])return contrasts[p.expected+':'+p.heard];}
 return null;
}
