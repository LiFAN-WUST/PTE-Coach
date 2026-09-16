"""Offline, experimental phone-sequence review. No calibrated pronunciation score."""
import json
import time
from pathlib import Path
import numpy as np
from app.analysis.phones import decode_phones,align_words,parse_ipa
from app.analysis.text import tokens

REVIEW_PAIRS={('θ','s'),('θ','t'),('θ','f'),('ð','d'),('ð','z'),('w','v'),('v','w'),
              ('ɹ','l'),('l','ɹ'),('s','ʃ'),('ʃ','s'),('tʃ','ʃ'),('dʒ','ʒ')}

def build_word_windows(reference,comparison,words,duration):
    windows=[None]*len(reference)
    if [token for w in words for token in tokens(w.get('text',''))]!=comparison.get('spoken_tokens',[]):return windows
    # Never manufacture separate time bounds for multi-token provider words.
    if any(len(tokens(w.get('text','')))!=1 for w in words):return windows
    previous=0
    for word in words:
        start,end=word.get('start'),word.get('end')
        if start is None or end is None or not 0<=start<end<=duration+.05 or start<previous-.05:return windows
        previous=end
    for op in comparison.get('operations',[]):
        ri,si=op.get('reference_index'),op.get('spoken_index')
        if op['kind']=='match' and ri is not None and si is not None and 0<=si<len(words):
            w=words[si];windows[ri]=(max(0,w['start']-.12),min(duration,w['end']+.12))
    return windows

def summarize(words,observed_count,blocked_indexes=None):
    blocked_indexes=blocked_indexes or set();reviews=0;eligible=0
    for word in words:
        blocked=word['index'] in blocked_indexes or not word['supported']
        word['status']='content_mismatch' if word['index'] in blocked_indexes else 'unsupported' if not word['supported'] else 'matched'
        expected_phones=[p for p in word['phonemes'] if p['expected']]
        match_fraction=sum(p['kind']=='match' for p in expected_phones)/max(1,len(expected_phones))
        word['alignment_match_fraction']=round(match_fraction,3)
        final=expected_phones[-1] if expected_phones else None
        for p in word['phonemes']:
            confidence=p['confidence'] or 0
            p['status']='uncertain'
            # Release/voicing and American flaps are not safely diagnosed by this recognizer.
            ambiguous=(p is final and p['expected'] in {'p','b','t','d','k','ɡ'} and p['kind']!='match') or (p['expected'] in {'t','d'} and p['heard']=='ɾ')
            if not blocked and not ambiguous and confidence>=.8 and p['kind'] in {'match','substitution'}:
                eligible+=1
                if p['kind']=='match':p['status']='matched'
                elif (p['expected'],p['heard']) in REVIEW_PAIRS and (match_fraction>=.5 or len(expected_phones)==1):
                    p['status']='review';reviews+=1;word['status']='review'
                elif word['status']=='matched':word['status']='uncertain'
            elif not blocked and word['status']=='matched':word['status']='uncertain'
        word['review_count']=sum(p['status']=='review' for p in word['phonemes'])
    return dict(status='experimental',provider='local-phoneme-onnx',accuracy_score=None,prosody_score=None,
        words=words,review_count=reviews,sequence_match_index=None,
        reliable_phone_count=eligible,observed_phone_count=observed_count,
        note='本地音素分析（实验）：参考音素与独立识别结果对照，仅提示复听候选；模型也会识别错。尚未校准发音分，不计入 Practice Score。弱读、口音差异、未释放词尾和音素边界需结合原录音判断。')

class LocalPronunciation:
    def __init__(self,model_dir):
        self.model_dir=Path(model_dir);self.session=None

    def _load(self):
        if self.session is not None:return
        import onnxruntime as ort
        options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
        session=ort.InferenceSession(str(self.model_dir/'onnx/model.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        self.id2phone={v:k for k,v in json.loads((self.model_dir/'vocab.json').read_text(encoding='utf-8')).items()}
        self.session=session

    def recognize(self,y,sr):
        if sr!=16000:raise ValueError('本地音素模型需要 16 kHz 音频。')
        self._load();output=[]
        # Non-overlapping ownership windows with context. Process every sample, including long recordings.
        for body in range(0,len(y),12*sr):
            left=max(0,body-sr//2);right=min(len(y),body+12*sr+sr//2)
            audio=np.asarray(y[left:right],dtype=np.float32)
            if len(audio)<400:continue
            audio=(audio-audio.mean())/np.sqrt(audio.var()+1e-7)
            inputs={'input_values':audio[None,:]}
            for item in self.session.get_inputs():
                if item.name=='attention_mask':inputs[item.name]=np.ones((1,len(audio)),dtype=np.int64)
            logits=self.session.run(None,inputs)[0][0]
            phones=decode_phones(logits,self.id2phone,.02,left/sr)
            for p in phones:
                midpoint=(p['start']+p['end'])/2
                if body/sr<=midpoint<min(len(y),body+12*sr)/sr:
                    output.append(p)
        return output

    def assess(self,y,sr,reference,comparison=None,word_timings=None):
        started=time.perf_counter();observed=self.recognize(y,sr)
        blocked={o['reference_index'] for o in (comparison or {}).get('operations',[]) if o['kind']!='match' and o.get('reference_index') is not None}
        reference_words=tokens(reference)
        windows=build_word_windows(reference_words,comparison,word_timings or [],len(y)/sr) if comparison is not None else None
        result=summarize(align_words(reference_words,observed,windows=windows),len(observed),blocked)
        for word in result['words']:
            for phone in word['phonemes']:
                if phone['status']=='review' and windows is not None and windows[word['index']] is None:
                    phone['status']='uncertain';phone['verification']='missing_word_anchor'
        self.verify_context(result,y,sr)
        result['elapsed_seconds']=round(time.perf_counter()-started,2)
        result['model']=self.provenance()
        self.validation_gate(result)
        return result

    def verify_context(self,result,y,sr):
        for word in result['words']:
            candidates=[p for p in word['phonemes'] if p['status']=='review']
            if candidates:
                left=max(0,(word['alignment_window'] or [word['start'],word['end']])[0]-.4)
                right=min(len(y)/sr,(word['alignment_window'] or [word['start'],word['end']])[1]+.4)
                start=int(left*sr);end=int(right*sr)
                # A second identical input is not a stability check.
                if start==0 and end==len(y):
                    context=[];reason='insufficient_context_change'
                else:
                    context=self.recognize(y[start:end],sr);reason='context_disagreement'
                for phone in candidates:
                    center=(phone['start']+phone['end'])/2
                    same=[p for p in context if p['phone']==phone['heard'] and p['confidence']>=.8
                          and abs((p['start']+p['end'])/2+start/sr-center)<=.12]
                    phone['verification']='stable_across_contexts' if same else reason
                    if same:phone['context_confidence']=max(p['confidence'] for p in same)
                    else:phone['status']='uncertain'
            word['review_count']=sum(p['status']=='review' for p in word['phonemes'])
            if word['status']=='review' and not word['review_count']:word['status']='uncertain'
        result['review_count']=sum(w['review_count'] for w in result['words'])

    def assess_ipa(self,y,sr,target):
        expected=parse_ipa(target);started=time.perf_counter();observed=self.recognize(y,sr)
        result=summarize(align_words([target],observed,variants=[[expected]]),len(observed))
        self.verify_context(result,y,sr)
        if len(expected)==1:
            found=any(p['phone']==expected[0] and p['confidence']>=.8 for p in observed)
            if found:result['words'][0]['status']='target_detected'
            elif len(observed)>1:
                # Multiple unrelated sounds do not identify which one was an attempted target.
                result['review_count']=0;result['words'][0]['review_count']=0;result['words'][0]['status']='uncertain'
                for phone in result['words'][0]['phonemes']:
                    if phone['status']=='review':phone['status']='uncertain'
                result['ambiguous_target_alignment']=True
        result['elapsed_seconds']=round(time.perf_counter()-started,2)
        result['model']=self.provenance()
        result['note']='音标专项（实验）：直接识别录音音素，不经过单词转写。孤立音素、气流声和噪声可能难以区分；未检出不等于发错，序列一致不等于达标。可再放入例词交叉验证。本模式不评分，也不评重音和元音长短。'
        if not observed:result['note']='本次未识别出可靠音素。请靠近麦克风，自然发声后再试；也可以把目标放入例词交叉验证。'+result['note']
        self.validation_gate(result)
        return result

    def validation_gate(self,result):
        # Honest release gate: reducing flags did not establish useful error detection.
        result['validation']={'diagnostic_ready':False,'status':'not_validated',
            'note':'发音纠错尚未通过人工评分录音的对照验证。音素结果只用于复听，不据此认定你发错。',
            'benchmark':'SpeechOcean762 exploratory 50-utterance comparison; see docs/algorithm-v2-benchmark.json'}
        result['candidate_count']=result['review_count']
        for word in result['words']:word['diagnostic_ready']=False

    def provenance(self):
        return {'repository':'onnx-community/wav2vec2-lv-60-espeak-cv-ft-ONNX',
            'algorithm_version':'phone-evidence-v2','word_window_padding_seconds':.12,
            'review_policy':'restricted contrasts, matched neighbors, changed-context agreement; uncalibrated',
            'revision':'c69750f5043e5e1f8a71ab95dd3b98338c280c92','precision':'float32','device':'cpu',
            'alignment':'time-constrained dictionary-variant alignment when ASR anchors available; CTC emission peaks are not phone duration','dictionary':'CMUdict'}
