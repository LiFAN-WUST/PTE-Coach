"""Independent CTC phone evidence and dictionary alignment, never an exam score."""
from functools import lru_cache
import re
import numpy as np
import cmudict

ARPABET = dict(zip('AA AE AH AO AW AY B CH D DH EH ER EY F G HH IH IY JH K L M N NG OW OY P R S SH T TH UH UW V W Y Z ZH'.split(),
                  'ɑ æ ʌ ɔ aʊ aɪ b tʃ d ð ɛ ɚ eɪ f ɡ h ɪ i dʒ k l m n ŋ oʊ ɔɪ p ɹ s ʃ t θ ʊ u v w j z ʒ'.split()))

def normalize(phone):
    return phone.replace('ː','').replace('ɫ','l').replace('g','ɡ')

@lru_cache(maxsize=1)
def dictionary():
    return cmudict.dict()

@lru_cache(maxsize=4096)
def word_variants(word):
    result=[]
    for variant in dictionary().get(word.lower(),[]):
        phones=['ə' if p=='AH0' else ARPABET[re.sub(r'\d','',p)] for p in variant]
        if phones not in result: result.append(phones)
    return result

def decode_phones(logits,id2phone,seconds_per_frame,offset=0):
    if not len(logits):return []
    shifted=logits-logits.max(axis=-1,keepdims=True)
    probabilities=np.exp(shifted);probabilities/=probabilities.sum(axis=-1,keepdims=True)
    ids=logits.argmax(axis=-1);result=[];i=0
    while i<len(ids):
        j=i+1
        while j<len(ids) and ids[j]==ids[i]:j+=1
        label=id2phone[int(ids[i])]
        if not label.startswith('<'):
            phone=normalize(label)
            parts={'əl':['ə','l'],'n̩':['ə','n'],'l̩':['ə','l'],'ɑɹ':['ɑ','ɹ'],
                   'ɔɹ':['ɔ','ɹ'],'ɛɹ':['ɛ','ɹ'],'ɪɹ':['ɪ','ɹ'],'ʊɹ':['ʊ','ɹ'],'ju':['j','u']}.get(phone,[phone])
            for part in parts:
                result.append(dict(phone=part,start=round(offset+i*seconds_per_frame,3),
                    end=round(offset+j*seconds_per_frame,3),confidence=float(probabilities[i:j,ids[i]].mean()),
                    model_token=label,shared_boundary=len(parts)>1))
        i=j
    return result

def compatible(expected,heard):
    return expected==heard or (expected=='ə' and heard=='ᵻ')

def substitution_cost(expected,heard):
    if compatible(expected,heard):return 0
    vowels=set('aeiouɑɐɒæəɚɛɜɪɔʊʌɨɯʉøyœᵻ')
    # Prefer an unaligned pair over a fabricated vowel/consonant substitution.
    if bool(expected and expected[0] in vowels)!=bool(heard and heard[0] in vowels):return 2.1
    return 1

IPA=set(ARPABET.values())|{'ɒ','ɜ','ə','əʊ','ɪə','eə','ʊə','ɐ','ɾ'}
def parse_ipa(text):
    if text.strip().lower()=='th':raise ValueError('th 有两种常见发音，请输入 /θ/（think）或 /ð/（this）。')
    text=normalize(re.sub(r'[\s/\[\]ˈˌˑ]','',text)).replace('r','ɹ')
    result=[];symbols=sorted(IPA,key=len,reverse=True)
    while text:
        phone=next((s for s in symbols if text.startswith(s)),None)
        if phone is None:raise ValueError('暂不支持这个音标字符。请使用英语 IPA，例如 /θ/、/ð/、/ʃ/、/tʃ/ 或 /iː/。')
        result.append(phone);text=text[len(phone):]
    if not 1<=len(result)<=24:raise ValueError('音标模式请输入 1–24 个英语音素。')
    return result

def align_words(words,observed,variants=None,windows=None):
    # A DAG preserves every dictionary variant without greedily fixing heteronyms.
    nodes=[dict(phone=None,preds=[],owner=0)];previous=0
    for wi,word in enumerate(words):
        ends=[]
        for variant in (variants[wi] if variants is not None else word_variants(word)) or [['?']]:
            parent=previous
            for phone in variant:
                nodes.append(dict(phone=phone,preds=[parent],owner=wi));parent=len(nodes)-1
            ends.append(parent)
        nodes.append(dict(phone=None,preds=ends,owner=wi));previous=len(nodes)-1
    n=len(observed);cost=np.full((len(nodes),n+1),1e8);back={}
    cost[0]=np.arange(n+1)
    for j in range(1,n+1):back[0,j]=(0,j-1,'insertion')
    for i,node in enumerate(nodes[1:],1):
        for j in range(n+1):
            candidates=[]
            for p in node['preds']:
                if node['phone'] is None:candidates.append((cost[p,j],p,j,'epsilon'))
                else:
                    if j:
                        match=compatible(node['phone'],observed[j-1]['phone'])
                        window=windows[node['owner']] if windows is not None else None
                        midpoint=(observed[j-1]['start']+observed[j-1]['end'])/2
                        # The unconstrained sequence path can slide phones into another word.
                        if window is None or window[0]<=midpoint<=window[1]:
                            candidates.append((cost[p,j-1]+substitution_cost(node['phone'],observed[j-1]['phone']),p,j-1,'match' if match else 'substitution'))
                    candidates.append((cost[p,j]+1,p,j,'deletion'))
            if j:candidates.append((cost[i,j-1]+1,i,j-1,'insertion'))
            value,p,k,kind=min(candidates,key=lambda c:c[0]);cost[i,j]=value;back[i,j]=(p,k,kind)
    output=[dict(word=w,index=i,phonemes=[],supported=bool(variants[i] if variants is not None else word_variants(w))) for i,w in enumerate(words)]
    i=len(nodes)-1;j=n;trace=[]
    while i or j:
        p,k,kind=back[i,j]
        if kind!='epsilon':
            obs=observed[j-1] if kind in {'match','substitution','insertion'} else {}
            trace.append((nodes[i]['owner'],dict(kind=kind,expected=nodes[i]['phone'] if kind!='insertion' else None,
                heard=obs.get('phone'),start=obs.get('start'),end=obs.get('end'),confidence=obs.get('confidence'),
                shared_boundary=obs.get('shared_boundary',False))))
        i,j=p,k
    for owner,phone in reversed(trace):
        if output:output[owner]['phonemes'].append(phone)
    for word in output:
        timed=[p for p in word['phonemes'] if p['start'] is not None]
        word['start']=min((p['start'] for p in timed),default=None)
        word['end']=max((p['end'] for p in timed),default=None)
        word['expected']=' '.join(p['expected'] for p in word['phonemes'] if p['expected'])
        word['heard']=' '.join(p['heard'] for p in word['phonemes'] if p['heard'])
        word['alignment_window']=list(windows[word['index']]) if windows is not None and windows[word['index']] is not None else None
    return output
