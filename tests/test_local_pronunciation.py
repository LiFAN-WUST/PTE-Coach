import numpy as np
from app.analysis.phones import decode_phones, align_words, word_variants
from app.providers.local_pronunciation import summarize
from app.analysis.phones import parse_ipa
import pytest


def heard(phones, confidence=.98):
    return [dict(phone=p,start=i*.1,end=(i+1)*.1,confidence=confidence) for i,p in enumerate(phones)]


def test_ctc_collapses_repeats_but_blank_separates():
    logits=np.full((5,3),-8.)
    logits[np.arange(5),[1,1,0,1,2]]=8
    result=decode_phones(logits,{0:'<pad>',1:'s',2:'iː'},.1)
    assert [p['phone'] for p in result]==['s','s','i']
    assert result[0]['start']==0 and result[0]['end']==.2


def test_pronunciation_variants_do_not_penalize_read_past_tense():
    result=align_words(['read'],heard(['ɹ','ɛ','d']))
    assert all(p['kind']=='match' for p in result[0]['phonemes'])


def test_theta_s_is_candidate_not_certain_diagnosis():
    words=align_words(['three'],heard(['s','ɹ','i']))
    result=summarize(words,3)
    assert result['status']=='experimental'
    assert result['accuracy_score'] is None
    assert result['words'][0]['phonemes'][0]['status']=='review'
    assert result['words'][0]['phonemes'][0]['expected']=='θ'
    assert result['words'][0]['phonemes'][0]['heard']=='s'


def test_low_confidence_is_not_flagged():
    words=align_words(['three'],heard(['s','ɹ','i'],.3))
    result=summarize(words,3)
    assert result['review_count']==0
    assert result['sequence_match_index'] is None


def test_missing_final_stop_is_uncertain():
    result=summarize(align_words(['cat'],heard(['k','æ'])),2)
    assert result['review_count']==0
    assert result['words'][0]['phonemes'][-1]['status']=='uncertain'


def test_unknown_and_content_error_words_are_not_scored():
    assert word_variants('zzxxq')==[]
    result=summarize(align_words(['three'],heard(['s','ɹ','i'])),3,blocked_indexes={0})
    assert result['words'][0]['status']=='content_mismatch'
    assert result['sequence_match_index'] is None


def test_silence_never_gets_a_pronunciation_index():
    result=summarize(align_words(['three'],[]),0)
    assert result['sequence_match_index'] is None
    assert result['review_count']==0


def test_insertion_is_kept_in_evidence():
    result=align_words(['cat'],heard(['k','s','æ','t']))
    assert any(p['kind']=='insertion' for p in result[0]['phonemes'])

def test_final_stop_voicing_does_not_become_definite_review():
    result=summarize(align_words(['cat'],heard(['k','æ','d'])),3)
    assert result['review_count']==0
    assert result['words'][0]['phonemes'][-1]['status']=='uncertain'

def test_long_recording_processes_last_window():
    from app.providers.local_pronunciation import LocalPronunciation
    class Session:
        def get_inputs(self):return []
        def run(self,outputs,inputs):
            n=(inputs['input_values'].shape[1]-400)//320+1
            logits=np.full((1,n,2),-8.)
            logits[:,:,0]=8
            logits[:,::10,0]=-8;logits[:,::10,1]=8
            return [logits]
    p=LocalPronunciation('unused');p.session=Session();p.id2phone={0:'<pad>',1:'s'}
    phones=p.recognize(np.zeros(31*16000),16000)
    assert max(x['end'] for x in phones)>30
    assert all(0<=x['start']<=x['end']<=31 for x in phones)

def test_ipa_targets_accept_both_th_sounds_and_affricates():
    assert parse_ipa('/θ/')==['θ']
    assert parse_ipa('[ð]')==['ð']
    assert parse_ipa('/ˈtiːtʃə/')==['t','i','tʃ','ə']
    with pytest.raises(ValueError,match='θ.*ð'):parse_ipa('th')
    with pytest.raises(ValueError):parse_ipa('hello🌍')
    with pytest.raises(ValueError):parse_ipa('///')

def test_ipa_direct_recognition_is_not_conditioned_on_target(monkeypatch):
    from app.providers.local_pronunciation import LocalPronunciation
    p=LocalPronunciation('unused')
    monkeypatch.setattr(p,'recognize',lambda y,sr:heard(['s']))
    r=p.assess_ipa(np.zeros(16000),16000,'/θ/')
    assert r['words'][0]['phonemes'][0]['heard']=='s'
    assert r['words'][0]['phonemes'][0]['expected']=='θ'
    assert r['accuracy_score'] is None

def test_single_phone_detected_with_context_and_ambiguous_substitution_abstains(monkeypatch):
    from app.providers.local_pronunciation import LocalPronunciation
    p=LocalPronunciation('unused')
    monkeypatch.setattr(p,'recognize',lambda y,sr:heard(['θ','ɪ','ŋ','k']))
    assert p.assess_ipa(np.zeros(16000),16000,'/θ/')['words'][0]['status']=='target_detected'
    monkeypatch.setattr(p,'recognize',lambda y,sr:heard(['s','ɪ','ŋ','k']))
    assert p.assess_ipa(np.zeros(16000),16000,'/θ/')['review_count']==0
