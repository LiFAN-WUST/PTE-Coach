import numpy as np
from app.analysis.features import extract
from app.analysis.text import compare
from app.models import Word
from app.repository import Repository

def measured(reference='one two three',gap=.7):
    words=[Word('one',.5,1),Word('two',1+gap,2+gap),Word('three',2.1+gap,2.5+gap)]
    regions=[{'start':.5,'end':1},{'start':1+gap,'end':2.5+gap}]
    return extract(4,regions,words,compare(reference,'one two three'),reference,np.ones(64000)*.1,16000,{'contour':[]})

def test_edge_silence_not_counted_as_pause():
    f=measured()
    assert f['pause_count']==1
    assert f['speaking_duration']+f['silence_duration']==4
    assert f['leading_silence']==.5
    assert f['pause_counts']=={'200':1,'500':1,'1000':0}

def test_punctuation_not_abnormal_chunk():
    assert measured('one, two three')['abnormal_pause_count']==0
    assert measured()['abnormal_pause_count']==1

def test_legitimate_repeated_reference_not_penalized():
    assert compare('he had had lunch','he had had lunch')['repetitions']==[]

def test_unknown_boundaries_are_explicit():
    f=extract(2,[{'start':0,'end':2}],[Word('one',None,None)],compare('one','one'),'one',np.ones(32000)*.1,16000,{'contour':[]})
    assert f['words'][0]['duration'] is None

def test_restart_recovers_interrupted_attempt(tmp_path):
    r=Repository(tmp_path/'db.sqlite');r.create('abc','one two three');r.set('abc','processing')
    restarted=Repository(tmp_path/'db.sqlite')
    assert restarted.get('abc')['status']=='failed'
