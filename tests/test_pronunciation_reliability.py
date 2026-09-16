import numpy as np
from app.analysis.phones import align_words
from app.providers.local_pronunciation import summarize,build_word_windows,LocalPronunciation

def obs(sounds,start=0):
    return [dict(phone=p,start=start+i*.1,end=start+i*.1+.02,confidence=.99) for i,p in enumerate(sounds)]

def test_time_windows_prevent_matching_a_later_word_to_an_earlier_phone():
    words=align_words(['cat','cat'],obs(['k','æ','t'],2),windows=[(0,.5),(2,2.5)])
    assert not any(p['kind']=='match' for p in words[0]['phonemes'])
    assert all(p['kind']=='match' for p in words[1]['phonemes'])

def test_high_confidence_vowel_to_stop_is_not_a_pronunciation_diagnosis():
    result=summarize(align_words(['last'],obs(['l','t','s','t'])),4)
    assert result['review_count']==0

def test_alignment_does_not_claim_a_vowel_was_a_consonant():
    words=align_words(['cat'],obs(['k','s','t']))
    assert not any(p['expected']=='æ' and p['heard']=='s' and p['kind']=='substitution' for p in words[0]['phonemes'])

def test_unreliable_whole_word_abstains_even_if_a_single_phone_is_confident():
    result=summarize(align_words(['empire'],obs(['i','a','m','h','æ'])),5)
    assert result['review_count']==0

def test_valid_th_s_contrast_retained_when_neighbors_match():
    result=summarize(align_words(['three'],obs(['s','ɹ','i'])),3)
    assert result['review_count']==1

def test_word_timing_requires_consistent_token_mapping():
    comparison={'spoken_tokens':['cat'],'operations':[dict(kind='match',reference_index=0,spoken_index=0)]}
    assert build_word_windows(['cat'],comparison,[dict(text='dog',start=0,end=1)],2)==[None]
    assert build_word_windows(['cat'],comparison,[dict(text='cat',start=0,end=1)],2)==[(0,1.12)]

def test_second_context_disagreement_suppresses_candidate(monkeypatch):
    p=LocalPronunciation('unused');calls=[]
    def recognize(y,sr):
        calls.append(len(y));return obs(['s','ɹ','i'],.2) if len(calls)==1 else obs(['θ','ɹ','i'],.2)
    monkeypatch.setattr(p,'recognize',recognize)
    r=p.assess(np.zeros(32000),16000,'three')
    assert r['review_count']==0
    assert r['words'][0]['phonemes'][0]['verification']=='context_disagreement'

def test_release_gate_does_not_turn_stable_model_output_into_validated_diagnosis(monkeypatch):
    p=LocalPronunciation('unused')
    monkeypatch.setattr(p,'recognize',lambda y,sr:obs(['θ','ɹ','i'],.2))
    r=p.assess(np.zeros(32000),16000,'three')
    assert r['accuracy_score'] is None
    assert r['validation']['diagnostic_ready'] is False
    assert all(w['diagnostic_ready'] is False for w in r['words'])
