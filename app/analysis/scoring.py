import hashlib
import json
from pathlib import Path
RUBRIC=json.loads(Path(__file__).with_name('rubric.json').read_text(encoding='utf-8'))

def score(comparison,features,pronunciation,rubric=None):
    r=rubric or RUBRIC
    content=max(0.,100*(1-comparison['wer']))
    wpm=features['wpm']; low,high=r['wpm_comfort_band']
    speed_distance=max(low-wpm,0,wpm-high)
    per_min=features['abnormal_pause_count']/max(features['utterance_span']/60,1/60)
    defs=[('wpm',wpm,min(r['speed_max_penalty'],speed_distance*r['speed_penalty_per_wpm']),f"舒适区间 {low}–{high}，非考试标准"),
          ('internal_silence_ratio',features['internal_silence_ratio'],min(r['silence_max_penalty'],max(0,features['internal_silence_ratio']-r['internal_silence_free_ratio'])*r['silence_penalty_per_ratio']),'仅计算首尾语音之间的静音'),
          ('abnormal_pauses_per_min',per_min,min(r['chunk_pause_max_penalty'],per_min*r['chunk_pause_penalty_per_min']),'无标点处 ≥500ms 词间隔，仅为候选异常'),
          ('repetition_count',features['repetition_count'],min(r['repetition_max_penalty'],features['repetition_count']/max(1,features['word_count'])*r['repetition_penalty_per_token_ratio']),'ASR 可观察到的重复下界')]
    evidence=[{'feature':k,'raw':round(v,3),'penalty':round(p,3),'explanation':note} for k,v,p,note in defs]
    absent={'value':None,'status':'unavailable','evidence':[]}
    result={'content':{'value':round(content,1),'status':'ASR-derived','evidence':[{'feature':'word_error_rate','raw':comparison['wer'],'formula':'max(0, 100 × (1 − WER))','counts':comparison['counts']}]},
            'fluency':{'value':round(max(0,100-sum(x['penalty'] for x in evidence)),1),'status':'heuristic, uncalibrated','evidence':evidence},
            'pronunciation':dict(absent),'prosody':dict(absent)}
    if not features.get('word_mapping_valid',True) or features.get('timestamp_coverage',1)<.8:
        result['fluency']={**absent,'status':'insufficient word alignment; cannot assess pause penalties'}
    if pronunciation and pronunciation.get('status')=='available':
        for k,field in [('pronunciation','accuracy_score'),('prosody','prosody_score')]:
            val=pronunciation.get(field)
            if val is not None:
                result[k]={'value':round(float(val),1),'status':'Azure vendor assessment; not Pearson',
                           'evidence':[{'feature':field,'raw':val,'provider':'azure','path':'pronunciation.words'}]}
    available=[k for k in r['weights'] if result[k]['value'] is not None]
    coverage=sum(r['weights'][k] for k in available)
    result.update(overall=round(sum(result[k]['value']*r['weights'][k] for k in available)/coverage,1),
                  coverage=round(coverage,2),components=available,rubric_version=r['version'],
                  rubric_hash=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()[:12],rubric=r,
                  label='Practice Score',note='未校准训练指数；只聚合可用维度，不可换算 PTE 官方分数。')
    return result
