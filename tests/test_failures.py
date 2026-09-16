from pathlib import Path
import tempfile
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
from test_api import audio_bytes,poll

class BrokenASR:
    def transcribe(self,path):raise RuntimeError('SECRET-SHOULD-NOT-LEAK')

def test_provider_failure_preserves_record_and_redacts_error():
    with tempfile.TemporaryDirectory() as d:
        with TestClient(create_app(Settings(data_dir=Path(d)),asr=BrokenASR(),vad=lambda y,sr:[{'start':0,'end':3}])) as c:
            r=c.post('/api/attempts',data={'reference':'one two three'},files={'audio':('x.wav',audio_bytes())})
            done=poll(c,r.json()['id'])
            assert done['status']=='failed'
            assert 'SECRET' not in done['error']
            assert c.get('/api/attempts/'+done['id']+'/audio').status_code==200

def test_corrupt_file_and_size_limit():
    with tempfile.TemporaryDirectory() as d:
        with TestClient(create_app(Settings(data_dir=Path(d)))) as c:
            r=c.post('/api/attempts',data={'reference':'one two three'},files={'audio':('bad.wav',b'not audio')})
            assert poll(c,r.json()['id'])['status']=='failed'
            assert c.post('/api/attempts',headers={'Content-Length':str(30*1024*1024)}).status_code==413

def test_serves_modules_and_local_configuration():
    with tempfile.TemporaryDirectory() as d:
        with TestClient(create_app(Settings(data_dir=Path(d)))) as c:
            r=c.get('/');assert r.status_code==200
            assert 'PTE Coach' in r.text
            assert 'frame-ancestors' in r.headers['content-security-policy']
            for name in ['app','api','charts','recorder','results']:
                assert c.get('/static/'+name+'.js').status_code==200
            assert c.get('/api/config').json()['cloud_enabled'] is False
