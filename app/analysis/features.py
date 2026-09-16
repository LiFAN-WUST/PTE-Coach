import re
from functools import lru_cache
import numpy as np
from app.analysis.text import tokens, PATTERN

@lru_cache(maxsize=1)
def lexicon():
    try:
        import cmudict
        return cmudict.dict()
    except ImportError:
        return {}

@lru_cache(maxsize=10000)
def syllables(word):
    # A count estimate, never an observed syllable boundary.
    phones=lexicon().get(word)
    if phones: return sum(p[-1:].isdigit() for p in phones[0]),'cmudict'
    groups=len(re.findall('[aeiouy]+',word))
    return max(1,groups-(word.endswith('e') and not word.endswith(('le','ye')))),'spelling-estimate'

def extract(duration,regions,words,comparison,reference,y,sr,pitch):
    speaking=sum(r['end']-r['start'] for r in regions)
    span=regions[-1]['end']-regions[0]['start'] if regions else 0
    pauses=[{'start':a['end'],'end':b['start'],'duration':round(b['start']-a['end'],3),'source':'Silero VAD'}
            for a,b in zip(regions,regions[1:]) if b['start']-a['end']>=.2-1e-6]
    # Map normalized recognized tokens to provider word intervals, without manufacturing split boundaries.
    mapped=[]
    for w in words:
        for token in tokens(w.text): mapped.append((token,w))
    ref_matches=list(PATTERN.finditer(reference.replace('’',"'")))
    boundaries=set()
    for i,match in enumerate(ref_matches):
        following=ref_matches[i+1].start() if i+1<len(ref_matches) else len(reference)
        if re.search('[,.;:!?—]',reference[match.end():following]): boundaries.add(i)
    ref_by_spoken={o['spoken_index']:o['reference_index'] for o in comparison['operations'] if o['spoken_index'] is not None}
    consistent=[t for t,_ in mapped]==comparison['spoken_tokens']
    abnormal=[]; details=[]
    for i,(token,w) in enumerate(mapped):
        valid=w.start is not None and w.end is not None and 0<=w.start<w.end<=duration+.1
        d=w.json();d.update(token=token,index=i,duration=round(w.end-w.start,3) if valid else None,pronunciation_confidence=None,
                            stress_accuracy=None,possible_pronunciation_issue=None)
        if valid:
            samples=y[int(w.start*sr):int(w.end*sr)]
            d['rms_dbfs']=round(float(20*np.log10(max(float(np.sqrt(np.mean(samples*samples))),1e-10))),1) if len(samples) else None
            ps=[p['hz'] for p in pitch['contour'] if p['hz'] is not None and w.start<=p['time']<=w.end]
            d['median_f0_hz']=round(float(np.median(ps)),1) if ps else None
        details.append(d)
        if i+1<len(mapped) and consistent and valid:
            nxt=mapped[i+1][1]
            ri=ref_by_spoken.get(i)
            if nxt.start is not None and nxt.start-w.end>=.5 and ri is not None and ri not in boundaries:
                abnormal.append({'after_word':token,'before_word':mapped[i+1][0],'start':w.end,'end':nxt.start,
                                 'duration':round(nxt.start-w.end,3),'word_index':i,'source':'word alignment gap',
                                 'status':'candidate','explanation':'此处无标点且词间隔 ≥500ms；请复听判断是否属于短语内部停顿。'})
    count=len(comparison['spoken_tokens']); syllable_results=[syllables(w) for w in comparison['spoken_tokens']]
    syllable_count=sum(x[0] for x in syllable_results)
    return {'total_duration':round(duration,3),'speaking_duration':round(speaking,3),'silence_duration':round(duration-speaking,3),
            'utterance_span':round(span,3),'leading_silence':round(regions[0]['start'],3) if regions else duration,
            'trailing_silence':round(duration-regions[-1]['end'],3) if regions else 0,
            'internal_silence_ratio':max(0,(span-speaking)/span) if span else 0,
            'speech_ratio':speaking/duration if duration else 0,'word_count':count,
            'wpm':round(count/span*60,1) if span else 0,'articulation_rate_wpm':round(count/speaking*60,1) if speaking else 0,
            'syllables_per_second_estimate':round(syllable_count/span,2) if span else 0,
            'articulation_syllables_per_second_estimate':round(syllable_count/speaking,2) if speaking else 0,
            'syllable_method':sorted(set(x[1] for x in syllable_results)),
            'pause_count':len(pauses),'mean_pause_duration':round(float(np.mean([p['duration'] for p in pauses])),3) if pauses else 0,
            'max_pause_duration':max([p['duration'] for p in pauses],default=0),
            'pause_counts':{str(ms):sum(p['duration']>=ms/1000 for p in pauses) for ms in [200,500,1000]},
            'pauses':pauses,'abnormal_pauses':abnormal,'abnormal_pause_count':len(abnormal),
            'repetition_count':sum(r['length'] for r in comparison['repetitions']),'fillers':comparison['fillers'],
            'restarts':None,'self_corrections':None,'words':details,'timestamp_coverage':sum(w['duration'] is not None for w in details)/max(1,len(details)),'word_mapping_valid':consistent,'speech_regions':regions}
