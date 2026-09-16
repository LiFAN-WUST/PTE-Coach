import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime,timezone

class Repository:
    def __init__(self,path):
        self.path=path
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
            db.execute("INSERT OR IGNORE INTO metadata VALUES('schema_version','1')")
            db.execute('''CREATE TABLE IF NOT EXISTS attempts(
                id TEXT PRIMARY KEY,created_at TEXT NOT NULL,task_type TEXT NOT NULL,
                reference TEXT NOT NULL,status TEXT NOT NULL,result TEXT,error TEXT)''')
            db.execute("UPDATE attempts SET status='failed',error='进程中断，请重新提交录音。' WHERE status IN ('queued','processing')")
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.row_factory=sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()
    def create(self,id,reference,task_type='read_aloud'):
        with self.connect() as db:
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?)',(id,datetime.now(timezone.utc).isoformat(),task_type,reference,'queued',None,None))
    def set(self,id,status,result=None,error=None):
        with self.connect() as db:
            db.execute('UPDATE attempts SET status=?,result=?,error=? WHERE id=?',(status,json.dumps(result,ensure_ascii=False,allow_nan=False) if result else None,error,id))
    def get(self,id):
        with self.connect() as db: row=db.execute('SELECT * FROM attempts WHERE id=?',(id,)).fetchone()
        if row is None:return None
        r=dict(row);r['result']=json.loads(r['result']) if r['result'] else None;return r
    def list(self,limit=200):
        with self.connect() as db: rows=db.execute('SELECT id,created_at,task_type,reference,status FROM attempts ORDER BY created_at DESC LIMIT ?',(limit,)).fetchall()
        return [dict(r) for r in rows]
    def pending(self):
        with self.connect() as db: return db.execute("SELECT count(*) FROM attempts WHERE status IN ('queued','processing')").fetchone()[0]
    def delete(self,id):
        with self.connect() as db:db.execute('DELETE FROM attempts WHERE id=?',(id,))
    def profile(self):
        with self.connect() as db:
            rows=db.execute("SELECT id,created_at,result FROM attempts WHERE status='done' AND task_type='read_aloud' ORDER BY created_at DESC LIMIT 1000").fetchall()
        series=[]
        for row in reversed(rows):
            r=json.loads(row['result']);f=r['features'];s=r['scores']
            series.append({'id':row['id'],'date':row['created_at'],'wpm':f['wpm'],
                'abnormal_pauses_per_min':round(f['abnormal_pause_count']/max(f['utterance_span']/60,1/60),2),
                'score':s['overall'] if s else None,'signature':r['comparison_signature']})
        return {'series':series,'note':'仅在相同模型／评分版本／可用维度下比较分数；不同题目难度也会影响趋势。'}
