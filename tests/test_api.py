import io
import time
import tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient
from app.config import Settings
from app.models import Word, Transcript
from app.main import create_app

class TestASR:
    def transcribe(self,path):
        return Transcript('the modern technology works',[Word('the',.2,.45,.9),Word('modern',.5,1,.9),Word('technology',1.6,2.3,.9),Word('works',2.4,2.8,.9)],'test-fixture')

def audio_bytes():
    y=.15*np.sin(2*np.pi*180*np.arange(48000)/16000)
    stream=io.BytesIO();sf.write(stream,y,16000,format='WAV');return stream.getvalue()

def poll(client,id):
    for _ in range(200):
        r=client.get('/api/attempts/'+id).json()
        if r['status'] in {'done','failed','rejected'}: return r
        time.sleep(.05)
    raise AssertionError('job did not finish')

def test_complete_lifecycle():
    with tempfile.TemporaryDirectory() as d:
        app=create_app(Settings(data_dir=Path(d)),asr=TestASR(),vad=lambda y,sr:[{'start':.2,'end':1.0},{'start':1.6,'end':2.8}])
        with TestClient(app) as c:
            r=c.post('/api/attempts',data={'reference':'The modern technology works.'},files={'audio':('x.wav',audio_bytes(),'audio/wav')})
            assert r.status_code==202
            id=r.json()['id']; done=poll(c,id)
            assert done['status']=='done',done
            assert done['result']['scores']['content']['value']==100
            assert done['result']['features']['abnormal_pause_count']==1
            assert c.get('/api/attempts/'+id+'/audio').status_code==200
            assert len(c.get('/api/attempts').json())==1
            assert len(c.get('/api/profile').json()['series'])==1
            assert c.get('/api/attempts/'+id+'/export').status_code==200
            assert c.delete('/api/attempts/'+id).status_code==200
            assert c.get('/api/attempts/'+id).status_code==404

def test_reject_silence_and_bad_reference():
    with tempfile.TemporaryDirectory() as d:
        with TestClient(create_app(Settings(data_dir=Path(d)),asr=TestASR())) as c:
            assert c.post('/api/attempts',data={'reference':'!!!'},files={'audio':('x.wav',audio_bytes())}).status_code==422
            stream=io.BytesIO();sf.write(stream,np.zeros(16000),16000,format='WAV')
            r=c.post('/api/attempts',data={'reference':'one two three'},files={'audio':('x.wav',stream.getvalue())})
            done=poll(c,r.json()['id'])
            assert done['status']=='rejected'
            assert done['result']['scores'] is None

def test_cross_origin_blocked():
    with tempfile.TemporaryDirectory() as d:
        with TestClient(create_app(Settings(data_dir=Path(d)),asr=TestASR())) as c:
            assert c.post('/api/attempts',headers={'Origin':'https://evil.example'}).status_code==403
            assert c.get('/api/config',headers={'Host':'evil.example'}).status_code==400

def test_reanalysis_preserves_original():
    with tempfile.TemporaryDirectory() as d:
        with TestClient(create_app(Settings(data_dir=Path(d)),asr=TestASR(),vad=lambda y,sr:[{'start':.2,'end':2.8}])) as c:
            job=c.post('/api/attempts',data={'reference':'The modern technology works.'},files={'audio':('x.wav',audio_bytes())}).json()
            original=poll(c,job['id'])
            r=c.post('/api/attempts/'+job['id']+'/reanalyze')
            assert r.status_code==202
            assert r.json()['id']!=job['id']
            new=poll(c,r.json()['id'])
            assert new['status']=='done'
            assert new['result']['source_attempt_id']==job['id']
            assert c.get('/api/attempts/'+job['id']).json()==original
            assert len(c.get('/api/attempts').json())==2
            assert c.post('/api/attempts/missing/reanalyze').status_code==404
            assert c.post('/api/attempts/'+job['id']+'/reanalyze',headers={'Origin':'https://evil.example'}).status_code==403

def test_local_model_failure_keeps_content_and_reports_unavailable(monkeypatch):
    from app.providers.local_pronunciation import LocalPronunciation
    def fail(*args,**kwargs):raise RuntimeError('private internal path')
    monkeypatch.setattr(LocalPronunciation,'assess',fail)
    with tempfile.TemporaryDirectory() as d:
        with TestClient(create_app(Settings(data_dir=Path(d),pronunciation='local'),asr=TestASR(),vad=lambda y,sr:[{'start':.2,'end':2.8}])) as c:
            job=c.post('/api/attempts',data={'reference':'The modern technology works.'},files={'audio':('x.wav',audio_bytes())}).json()
            row=poll(c,job['id'])
            assert row['status']=='done'
            assert row['result']['pronunciation']['status']=='unavailable'
            assert row['result']['scores']['pronunciation']['value'] is None
            assert 'private internal path' not in str(row)

def test_ipa_and_single_word_modes_skip_asr_and_keep_mode_on_reanalysis(monkeypatch):
    from app.providers.local_pronunciation import LocalPronunciation,summarize
    from app.analysis.phones import align_words
    monkeypatch.setattr(LocalPronunciation,'recognize',lambda self,y,sr:[dict(phone='θ',start=.2,end=.5,confidence=.99)])
    class ForbiddenASR:
        def transcribe(self,path):raise AssertionError('Isolated phones must not go through ASR')
    with tempfile.TemporaryDirectory() as d:
        with TestClient(create_app(Settings(data_dir=Path(d),pronunciation='local'),asr=ForbiddenASR(),vad=lambda y,sr:[])) as c:
            for mode,reference in [('phoneme','/θ/'),('word','think')]:
                response=c.post('/api/attempts',data={'reference':reference,'task_type':mode},files={'audio':('x.wav',audio_bytes())})
                assert response.status_code==202,response.text
                row=poll(c,response.json()['id'])
                assert row['status']=='done',row
                assert row['task_type']==mode
                assert row['result']['scores'] is None
                assert row['result']['pronunciation']['status']=='experimental'
                rerun=c.post('/api/attempts/'+row['id']+'/reanalyze')
                assert poll(c,rerun.json()['id'])['task_type']==mode
            assert c.get('/api/profile').json()['series']==[]
            bad=c.post('/api/attempts',data={'reference':'th','task_type':'phoneme'},files={'audio':('x.wav',audio_bytes())})
            assert bad.status_code==422 and 'θ' in bad.text
