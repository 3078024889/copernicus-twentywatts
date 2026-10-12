"""Offline-only local Oracle Seat: status/dashboard + bounded continual-learning worker.

No model API, no web fetch, no automatic certification, no V3 mutation.
"""
from __future__ import annotations
import argparse, json, os, signal, socket, sqlite3, threading, time
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .operations import inspect, execute, single_writer
from .full_pool import init as pool_init, bootstrap as pool_bootstrap, batch as pool_batch, status as pool_status

PROTOCOL = 'TW14_OFFLINE_ORACLE_V1'
_HTML = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>二十瓦特 · 离线神谕之座</title><style>
:root{color-scheme:dark;font-family:system-ui,'Microsoft YaHei',sans-serif;background:#080e1b;color:#eaf0fc}*{box-sizing:border-box}body{max-width:1150px;margin:auto;padding:24px}h1{font-size:29px;font-weight:600;margin-bottom:4px}p,.sub{color:#abb9d5}header{display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap}.pill{border:1px solid #4b6384;border-radius:20px;padding:6px 12px;color:#adc6ef}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:24px 0}.card{background:#111c31;border:1px solid #253956;border-radius:14px;padding:16px}.n{font-size:30px;font-weight:650;margin-top:8px}.muted{font-size:13px;color:#9fb3d5}.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.good{color:#81e4c2}.warn{color:#ffd18a}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;max-height:280px;overflow:auto}a{color:#a1c1ff}footer{margin-top:26px;color:#8396b8;font-size:12px}</style></head><body>
<header><div><h1>二十瓦特 · 神谕之座</h1><div class="sub">Copernicus / 7777 → 12 · 本地离线实验控制台</div></div><span id="badge" class="pill">读取中</span></header>
<div class="grid"><div class="card"><div class="muted">候选配置</div><div id="candidates" class="n">—</div></div><div class="card"><div class="muted">历史实验证据</div><div id="records" class="n">—</div></div><div class="card"><div class="muted">长期训练轮次</div><div id="cycles" class="n">—</div></div><div class="card"><div class="muted">认证 AI</div><div id="certified" class="n">—</div></div></div>
<div class="grid"><section class="card"><h3>离线训练</h3><div id="training" class="good">—</div><p class="muted">无外部 API，按设定时间间隔自动续跑。关闭服务即停止；重启后按 SQLite 检查点继续。</p><p class="muted">网页不提供远程启动或删除控制。</p></section><section class="card"><h3>证据与认证</h3><div id="integrity">—</div><p class="warn">研究参与者不等于认证赢家；合成实验不构成现实自主学习证明。Mother 晋升锁定。</p></section></div>
<section class="card"><div class="row"><h3>最新运行记录</h3><span class="muted" id="updated"></span></div><pre id="latest">—</pre></section><footer>127.0.0.1 本地服务 · 研究闭环 · V3 历史数据只读归档、未经迁移不混入新协议</footer>
<script>async function refresh(){try{let r=await fetch('/api/live',{cache:'no-store'});if(!r.ok)throw Error(r.status);let d=await r.json();let x=d.source||{};document.getElementById('candidates').textContent=(x.configurations??0).toLocaleString();document.getElementById('records').textContent=((x.screen||0)+(x.holdout||0)).toLocaleString();document.getElementById('cycles').textContent=(d.longitudinal_cycles??0).toLocaleString()+' / 已训练 '+(d.trained_distinct??'—')+' 个';document.getElementById('certified').textContent=(d.certified_independent_ais??0)+'/12';document.getElementById('badge').textContent=d.worker?.status||'UNKNOWN';document.getElementById('training').textContent='状态：'+(d.worker?.status||'—')+' · 完成批次 '+(d.worker?.batches_completed||0);document.getElementById('integrity').textContent='源数据库：'+(x.integrity||'—')+' · Mother：'+d.promotion;document.getElementById('latest').textContent=JSON.stringify(d.worker?.latest||{},null,2);document.getElementById('updated').textContent=new Date().toLocaleTimeString();}catch(e){document.getElementById('badge').textContent='服务读取失败';document.getElementById('latest').textContent=String(e)}}refresh();setInterval(refresh,5000)</script></body></html>'''

class OfflineRuntime:
    def __init__(self, source, state, *, interval=20, cycles=1, participants=12, stop_file=None, report=None, training=True, all_configs=False):
        if not (1 <= interval <= 86400 and 1 <= cycles <= 25 and 1 <= participants <= (7777 if all_configs else 12)):
            raise ValueError('Invalid bounded offline parameters')
        self.source=Path(source).resolve(); self.state=Path(state).resolve()
        if self.source == self.state: raise ValueError('Source/state collision')
        self.stop_file=Path(stop_file or str(self.state)+'.stop').resolve()
        self.report=Path(report or str(self.state)+'.status.json').resolve()
        self.interval=interval;self.cycles=cycles;self.participants=participants;self.training=training
        self.all_configs=all_configs
        self.shutdown=threading.Event();self.guard=threading.RLock();self.thread=None
        self.worker={'status':'STARTING','batches_completed':0,'latest':{},'last_error':None,'updated_at':None}
        self._last_snapshot=None
    def update(self, **fields):
        with self.guard:
            self.worker.update(fields);self.worker['updated_at']=datetime.now(timezone.utc).isoformat()
            payload={'protocol':PROTOCOL,'worker':dict(self.worker),'certified_independent_ais':0,'promotion':'LOCKED'}
            self.report.parent.mkdir(parents=True,exist_ok=True)
            temp=self.report.with_name(self.report.name+'.tmp')
            temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
            os.replace(temp,self.report)
    def snapshot(self):
        with self.guard: w=dict(self.worker)
        try:
            # SQLite queries are read-only. Never accept paths from HTTP clients.
            base=(inspect(self.source,self.state) if not self.all_configs else self.full_snapshot())
            base['worker']=w;base['protocol']=PROTOCOL
            self._last_snapshot=base
            return base
        except (OSError,sqlite3.Error,RuntimeError) as e:
            return {'protocol':PROTOCOL,'source':{},'worker':w,'health':'ERROR','detail':str(e),
                    'certified_independent_ais':0,'promotion':'LOCKED'}
    def full_snapshot(self):
        with closing(pool_init(self.state)) as db:
            result=pool_status(db)
        # Report actual source trial coverage, not fabricated zero values when
        # all-configs longitudinal training uses a separate state database.
        from tw8.arena import PROTOCOL as source_protocol
        with closing(sqlite3.connect(f'file:{self.source.as_posix()}?mode=ro', uri=True)) as source_db:
            coverage = dict(source_db.execute(
                'SELECT phase,COUNT(*) FROM trials WHERE protocol=? GROUP BY phase',
                (source_protocol,)).fetchall())
            source_integrity = source_db.execute('PRAGMA quick_check').fetchone()[0]
        return {'source': {'configurations': result['registered'], 'integrity':source_integrity,
                           'screen':coverage.get('screen',0),'holdout':coverage.get('holdout',0)},
                'longitudinal_cycles':result['total_cycles'],
                'trained_distinct':result['trained_distinct'],
                'all_candidates':result,
                'certified_independent_ais':0,'promotion':'LOCKED'}

    def work_loop(self):
        self.update(status='RUNNING')
        while not self.shutdown.is_set():
            if self.stop_file.exists():
                self.update(status='STOP_REQUESTED');break
            try:
                if self.all_configs:
                    with closing(pool_init(self.state)) as db:
                        result=pool_batch(db,limit=self.participants)
                    latest={'advanced_this_run':result['advanced'],
                            'evidence_records':result['status']['audit_records'],
                            'trained_distinct':result['status']['trained_distinct'],
                            'mean_gain_vs_cold':result['mean_gain_vs_cold'],
                            'reset_count':result['reset_count'],
                            'integrity':result['status']['integrity']}
                else:
                    result=execute(self.source,self.state,self.cycles,self.participants)
                    latest={'advanced_this_run':result['advanced_this_run'],
                            'evidence_records':result['evidence_records'],
                            'mean_longitudinal_minus_cold':result.get('mean_longitudinal_minus_cold'),
                            'transfer_guard':result.get('transfer_guard'),
                            'integrity':result['integrity']}
                with self.guard: n=self.worker['batches_completed']+1
                latest['time']=datetime.now(timezone.utc).isoformat()
                self.update(status='RUNNING',batches_completed=n,latest=latest,last_error=None)
            except Exception as e:
                self.update(status='ERROR',last_error=f'{type(e).__name__}: {e}')
                break # fail closed, never silently retry corruption
            self.shutdown.wait(self.interval)
        if self.worker['status'] not in ('ERROR','STOP_REQUESTED'):
            self.update(status='STOPPED')
    def start(self):
        if self.all_configs:
            with closing(pool_init(self.state)) as db: pool_bootstrap(db,self.source)
        self.snapshot() # Validate before network binds
        if not self.source.is_file():raise FileNotFoundError(self.source)
        if self.stop_file.exists():
            self.update(status='STOP_REQUESTED')
            return
        if self.training:
            self.thread=threading.Thread(target=self.work_loop,name='TWOfflineLearner',daemon=True)
            self.thread.start()
        else:self.update(status='READ_ONLY')
    def stop(self):
        self.shutdown.set()
        if self.thread:self.thread.join(timeout=15)


def handler_for(runtime):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path=urlsplit(self.path).path
            if path in ('/','/index.html'):
                body=_HTML.encode('utf-8');kind='text/html; charset=utf-8';code=200
            elif path in ('/api/live','/api/health'):
                body=json.dumps(runtime.snapshot(),ensure_ascii=False).encode('utf-8');kind='application/json; charset=utf-8';code=200
            else:
                body=b'{"error":"not_found"}';kind='application/json';code=404
            self.send_response(code)
            self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(body)
        def do_POST(self):
            self.send_error(405,'Read-only HTTP interface')
        def log_message(self,fmt,*args): pass
    return Handler


def serve(runtime,host='127.0.0.1',port=28722):
    if host!='127.0.0.1':raise ValueError('Offline server must bind to loopback')
    if not (1024 <= port <= 65535):raise ValueError('Bad port')
    # Exit if another offline oracle is running, or if the service is supervised twice.
    with single_writer(Path(str(runtime.state)+'.servicelock')):
        with ThreadingHTTPServer((host,port),handler_for(runtime)) as server:
            server.daemon_threads=True
            server.timeout=1
            runtime.start()
            try:
                while not runtime.shutdown.is_set():
                    server.handle_request()
            except KeyboardInterrupt:pass
            finally: runtime.stop()

def main(argv=None):
    ap=argparse.ArgumentParser(description='Offline-only TwentyWatts local Oracle Seat')
    ap.add_argument('--source-db',type=Path,required=True);ap.add_argument('--state-db',type=Path,required=True)
    ap.add_argument('--port',type=int,default=28722);ap.add_argument('--interval',type=int,default=20)
    ap.add_argument('--cycles',type=int,default=1);ap.add_argument('--participants',type=int,default=12)
    ap.add_argument('--stop-file',type=Path);ap.add_argument('--report',type=Path)
    ap.add_argument('--read-only',action='store_true')
    ap.add_argument('--all-configs',action='store_true',help='Train entire 7777 pool fairly, not fixed 12')
    a=ap.parse_args(argv)
    if a.state_db.resolve() in {a.source_db.resolve(),(a.source_db.resolve().parent/'v9.sqlite').resolve()}:
        ap.error('Refusing legacy/source state database')
    # Refuse silent startup without the correct original evidence pool.
    if a.all_configs:
        with closing(pool_init(a.state_db)) as db:pool_bootstrap(db,a.source_db)
    else:inspect(a.source_db,a.state_db)
    runtime=OfflineRuntime(a.source_db,a.state_db,interval=a.interval,cycles=a.cycles,
                           participants=a.participants,stop_file=a.stop_file,report=a.report,training=not a.read_only,all_configs=a.all_configs)
    print(f'OFFLINE_ORACLE http://127.0.0.1:{a.port}/',flush=True)
    serve(runtime,port=a.port)
if __name__=='__main__':main()
