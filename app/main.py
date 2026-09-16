import asyncio
import json
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI,UploadFile,File,Form,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse,Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.config import Settings
from app.repository import Repository
from app.pipeline import Pipeline
from app.analysis.text import tokens
from app.analysis.phones import parse_ipa

STATIC=Path(__file__).parent/'static'

def create_app(settings=None,asr=None,vad=None):
    cfg=settings or Settings();repo=Repository(cfg.data_dir/'history.sqlite3')
    pipeline=Pipeline(cfg,asr,vad);executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='speech')
    @asynccontextmanager
    async def lifespan(app):
        yield
        executor.shutdown(wait=True,cancel_futures=True)
    app=FastAPI(title='PTE Coach',lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver','[::1]'])
    @app.middleware('http')
    async def security(request:Request,call_next):
        if request.method in {'POST','DELETE','PUT','PATCH'}:
            origin=request.headers.get('origin')
            if origin and urlparse(origin).netloc!=request.headers.get('host'):
                return JSONResponse({'detail':'Cross-origin mutation blocked'},status_code=403)
            try:length=int(request.headers.get('content-length','0'))
            except ValueError:return JSONResponse({'detail':'Invalid Content-Length'},status_code=400)
            if length>cfg.max_bytes+65536:return JSONResponse({'detail':'音频最大 20 MiB'},status_code=413)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        return response
    def get(id):
        row=repo.get(id)
        if not row:raise HTTPException(404,'训练记录不存在。')
        return row
    def execute(id,source,reference,source_attempt_id=None,task_type='read_aloud'):
        repo.set(id,'processing')
        try:
            status,result=pipeline.run(source,reference,task_type)
            if source_attempt_id:result['source_attempt_id']=source_attempt_id
            repo.set(id,status,result)
        except ValueError as exc:repo.set(id,'failed',error=str(exc))
        except Exception as exc:
            # Never serialize provider exception strings: they may contain credentials or URLs.
            repo.set(id,'failed',error=f'分析失败（{type(exc).__name__}）。检查模型是否下载、FFmpeg、设备配置和依赖；音频已保留。')
    @app.get('/api/config')
    def config():
        return {'task_types':['read_aloud','word','phoneme'],'asr_model':cfg.asr_model,'device':cfg.device,
                'pronunciation':cfg.pronunciation,'cloud_enabled':cfg.cloud_enabled,'max_seconds':cfg.max_seconds,
                'notice':'Practice Score 为 0–100 未校准训练指数，不是 Pearson 官方分数。'}
    @app.post('/api/attempts',status_code=202)
    async def submit(audio:UploadFile=File(...),reference:str=Form(...),task_type:str=Form('read_aloud')):
        if task_type not in {'read_aloud','word','phoneme'}:raise HTTPException(422,'请选择短文、单词或音标模式。')
        if len(reference)>5000:raise HTTPException(422,'输入内容过长。')
        if task_type=='phoneme':
            try:parse_ipa(reference)
            except ValueError as exc:raise HTTPException(422,str(exc))
        elif not (3<=len(tokens(reference))<=200 if task_type=='read_aloud' else 1<=len(tokens(reference))<=5):
            raise HTTPException(422,'短文模式请输入 3–200 个英文词；单词模式请输入 1–5 个英文词。')
        if task_type!='read_aloud' and cfg.pronunciation!='local':raise HTTPException(422,'单词和音标专项需要启用本地音素模型。')
        if repo.pending()>=cfg.max_pending:raise HTTPException(429,'队列已满，请等待当前分析完成。')
        id=uuid.uuid4().hex;directory=cfg.data_dir/id;directory.mkdir();source=directory/'original.audio'
        size=0
        try:
            with source.open('wb') as output:
                while chunk:=await audio.read(1024*1024):
                    size+=len(chunk)
                    if size>cfg.max_bytes:raise HTTPException(413,'音频最大 20 MiB。')
                    output.write(chunk)
            if not size:raise HTTPException(422,'录音为空。')
            # Recheck after streaming upload to avoid oversubscribing the bounded queue.
            if repo.pending()>=cfg.max_pending:raise HTTPException(429,'队列已满。')
            repo.create(id,reference,task_type)
            executor.submit(execute,id,source,reference,None,task_type)
        except Exception:
            shutil.rmtree(directory,ignore_errors=True);raise
        finally:await audio.close()
        return {'id':id,'status':'queued'}
    @app.get('/api/attempts')
    def history():return repo.list()
    @app.post('/api/attempts/{id}/reanalyze',status_code=202)
    async def reanalyze(id:str):
        row=get(id)
        if row['status'] in {'queued','processing'}:raise HTTPException(409,'这条录音仍在分析中。')
        if repo.pending()>=cfg.max_pending:raise HTTPException(429,'队列已满，请稍后重试。')
        source=cfg.data_dir/id/'original.audio'
        if not source.exists():source=cfg.data_dir/id/'audio.wav'
        if not source.exists():raise HTTPException(404,'原录音文件不存在，无法重新分析。')
        new_id=uuid.uuid4().hex;directory=cfg.data_dir/new_id;directory.mkdir()
        try:
            target=directory/'original.audio';shutil.copyfile(source,target)
            repo.create(new_id,row['reference'],row['task_type']);executor.submit(execute,new_id,target,row['reference'],id,row['task_type'])
        except Exception:
            shutil.rmtree(directory,ignore_errors=True);repo.delete(new_id);raise
        return {'id':new_id,'status':'queued','source_attempt_id':id}
    @app.get('/api/attempts/{id}')
    def attempt(id:str):return get(id)
    @app.get('/api/attempts/{id}/audio')
    def audio(id:str):
        get(id);path=cfg.data_dir/id/'audio.wav'
        if not path.exists():raise HTTPException(404,'音频尚未完成解码。')
        return FileResponse(path,media_type='audio/wav')
    @app.get('/api/attempts/{id}/export')
    def export(id:str):
        row=get(id)
        return Response(json.dumps(row,ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="attempt-{id}.json"'})
    @app.delete('/api/attempts/{id}')
    def delete(id:str):
        row=get(id)
        if row['status'] in {'queued','processing'}:raise HTTPException(409,'请等待分析结束后删除。')
        shutil.rmtree(cfg.data_dir/id,ignore_errors=True);repo.delete(id);return {'deleted':id}
    @app.get('/api/profile')
    def profile():return repo.profile()
    @app.get('/')
    def home():return FileResponse(STATIC/'index.html')
    app.mount('/static',StaticFiles(directory=STATIC),name='static')
    return app

# Use uvicorn app.main:create_app --factory, one worker.
