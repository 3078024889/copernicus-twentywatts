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
from .resource_meter import measure
from .research_journal import record as journal_record, inspect as journal_inspect, verify_all as journal_verify
from .event_evolution import enqueue as evolution_enqueue, process_pending as evolution_process, status as evolution_status
from .full_pool import init as pool_init, bootstrap as pool_bootstrap, batch as pool_batch, status as pool_status
from .dendrite_native import advance as dendrite_advance, snapshot as dendrite_snapshot, database as dendrite_db, bootstrap as dendrite_bootstrap, advance_descendants, verify_all as dendrite_verify_all

PROTOCOL = 'TW14_OFFLINE_ORACLE_V1'
_HTML = r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>二十瓦特 · 离线神谕之座</title><style>
:root{color-scheme:dark;font-family:system-ui,'Microsoft YaHei',sans-serif;background:#080e1b;color:#eaf0fc}*{box-sizing:border-box}body{max-width:1150px;margin:auto;padding:24px}h1{font-size:29px;font-weight:600;margin-bottom:4px}p,.sub{color:#abb9d5}header{display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap}.pill{border:1px solid #4b6384;border-radius:20px;padding:6px 12px;color:#adc6ef}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:24px 0}.card{background:#111c31;border:1px solid #253956;border-radius:14px;padding:16px}.n{font-size:30px;font-weight:650;margin-top:8px}.muted{font-size:13px;color:#9fb3d5}.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.good{color:#81e4c2}.warn{color:#ffd18a}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;max-height:280px;overflow:auto}a{color:#a1c1ff}footer{margin-top:26px;color:#8396b8;font-size:12px}</style></head><body>
<header><div><h1>二十瓦特 · 神谕之座</h1><div class="sub">Copernicus / 7777 → 12 · 本地离线实验控制台</div></div><span id="badge" class="pill">读取中</span></header>
<div class="grid"><div class="card"><div class="muted">初始配置（非认证算法）</div><div id="candidates" class="n">—</div></div><div class="card"><div class="muted">历史实验证据</div><div id="records" class="n">—</div></div><div class="card"><div class="muted">长期训练轮次</div><div id="cycles" class="n">—</div></div><div class="card"><div class="muted">认证 AI</div><div id="certified" class="n">—</div></div></div>
<div class="grid"><section class="card"><h3>离线训练</h3><div id="training" class="good">—</div><p class="muted">无外部 API，按设定时间间隔自动续跑。关闭服务即停止；重启后按 SQLite 检查点继续。</p><p class="muted">网页不提供远程启动或删除控制。</p></section><section class="card"><h3>证据与认证</h3><div id="integrity">—</div><p class="warn">研究参与者不等于认证赢家；合成实验不构成现实自主学习证明。Mother 晋升锁定。</p></section></div>
<section class="card"><h3>D 系列原生树突训练与后代</h3><div id="dendrites">—</div><p class="muted">独立训练检查点、父代状态继承、试验性后代；不等于独立 AI 认证。</p></section><section class="card"><h3>事件驱动 · 树突后代实验</h3><div id="evolution">—</div><p class="muted">由训练负迁移或经验重置触发独立树突后代试验；不等于已迁移旧配置权重，也不自动认证。</p></section><section class="card"><h3>持久研究流水账</h3><div id="journal">—</div><p class="muted">追加记录，不覆盖历史；重启恢复已完成批次计数。证据哈希与深度校验分离。</p></section><section class="card"><h3>科研实验 · 资源与迁移验证</h3><div id="research">尚未运行独立研究任务</div><p class="muted">旧版周期性研究数据保留供对照；启用事件驱动进化后不再按固定批次运行旧科研任务。研究结果不自动认证。</p></section>
<section class="card"><div class="row"><h3>最新运行记录</h3><span class="muted" id="updated"></span></div><pre id="latest">—</pre></section><footer>127.0.0.1 本地服务 · 研究闭环 · V3 历史数据只读归档、未经迁移不混入新协议</footer>
<script>async function refresh(){try{let r=await fetch('/api/live',{cache:'no-store'});if(!r.ok)throw Error(r.status);let d=await r.json();let x=d.source||{};document.getElementById('candidates').textContent=(x.configurations??0).toLocaleString();document.getElementById('records').textContent=((x.screen||0)+(x.holdout||0)).toLocaleString();document.getElementById('cycles').textContent=(d.longitudinal_cycles??0).toLocaleString()+' / 已训练 '+(d.trained_distinct??'—')+' 个';document.getElementById('certified').textContent=(d.certified_independent_ais??0)+'/12';document.getElementById('badge').textContent=d.worker?.status||'UNKNOWN';document.getElementById('training').textContent='状态：'+(d.worker?.status||'—')+' · 完成批次 '+(d.worker?.batches_completed||0);document.getElementById('integrity').textContent='源数据库：'+(x.integrity||'—')+' · Mother：'+d.promotion;document.getElementById('latest').textContent=JSON.stringify(d.worker?.latest||{},null,2);let nv=d.dendrites||{};if(nv.registered){document.getElementById('candidates').textContent=nv.registered.toLocaleString();document.getElementById('cycles').textContent=nv.learning_steps.toLocaleString()+' / 已训练 '+nv.trained+' 个';document.querySelector('#candidates').previousElementSibling.textContent='D 系列可执行树突变异体';}document.getElementById('dendrites').textContent=nv.status==='DISABLED'?'未启用 D 系列训练':('已训练 '+(nv.trained||0)+' / '+(nv.registered||0)+' · 学习轮次 '+(nv.learning_steps||0)+' · 后代实验 '+(nv.offspring_trials||0)+' · 延续后代 '+(nv.descendant_states||0)+' · 后代续训轮次 '+(nv.descendant_learning_steps||0)+' · 启动全库验收 '+(nv.startup_full_audit||'—')+' · 正式认证 0/12');let ev=d.evolution||{};document.getElementById('evolution').textContent='已执行后代试验 '+(ev.completed||0)+' · 待执行 '+(ev.pending||0)+' · 预算不合格 '+(ev.resource_ineligible||0)+' · 认证 0/12'+(ev.latest?' · 最新变异 '+ev.latest.mutation+' · 未知任务 '+ev.latest.transfer_pp+'pp · 旧知识 '+ev.latest.retention_pp+'pp':'');document.getElementById('research').textContent=nv.registered?'旧版科研调度已由 D 系列父子实验替代':('研究状态：'+(d.research?.status||'WAITING'));document.getElementById('journal').textContent='已记录服务批次：'+(d.journal?.training_batches||0)+' · 证据条目：'+(d.journal?.entries||0)+' · 最近记录校验：'+(d.journal?.integrity||'—')+' · D 系列学习轮次：'+(nv.learning_steps||0)+'（独立检查点）';document.getElementById('updated').textContent=new Date().toLocaleTimeString();}catch(e){document.getElementById('badge').textContent='服务读取失败';document.getElementById('latest').textContent=String(e)}}refresh();setInterval(refresh,5000)</script></body></html>'''

class OfflineRuntime:
    def __init__(self, source, state, *, interval=20, cycles=1, participants=12, stop_file=None, report=None, training=True, all_configs=False, research_every=20, research_seeds=4, event_evolution=False, native_dendrites=False):
        if not (1 <= interval <= 86400 and 1 <= cycles <= 25 and 1 <= participants <= (7777 if all_configs else 12)):
            raise ValueError('Invalid bounded offline parameters')
        self.source=Path(source).resolve(); self.state=Path(state).resolve()
        if self.source == self.state: raise ValueError('Source/state collision')
        self.stop_file=Path(stop_file or str(self.state)+'.stop').resolve()
        self.report=Path(report or str(self.state)+'.status.json').resolve()
        self.interval=interval;self.cycles=cycles;self.participants=participants;self.training=training
        self.all_configs=all_configs
        if not (1 <= research_every <= 100000 and 2 <= research_seeds <= 32): raise ValueError("Invalid bounded research parameters")
        self.research_every=research_every; self.research_seeds=research_seeds
        self.event_evolution=event_evolution and all_configs and not native_dendrites
        self.native_dendrites=bool(native_dendrites)
        self.native_path=self.state.with_name(self.state.name+'.dendrite_native.sqlite')
        self.evolution_path=self.state.with_name(self.state.name+'.event_evolution.sqlite')
        self.journal_path=self.state.with_name(self.state.name+'.research_journal.sqlite')
        journal_state=journal_inspect(self.journal_path)
        last_research=journal_state.get('latest_research')
        self.research={'status':'REPLACED_BY_EVENT_DRIVEN' if self.event_evolution else 'WAITING','latest':None,'last_error':None}
        if last_research:
            event=last_research['payload']
            if last_research['kind']=='research':
                self.research={'status':'COMPLETED','latest':event.get('results'),
                               'at_batch':event.get('batch'),'last_error':None,
                               'restored_from_journal':True}
            else:
                self.research={'status':'ERROR','latest':None,
                               'at_batch':event.get('batch'),'last_error':event.get('error'),
                               'restored_from_journal':True}
        self.shutdown=threading.Event();self.guard=threading.RLock();self.thread=None
        self.worker={'status':'STARTING','batches_completed':journal_inspect(self.journal_path)['training_batches'],'latest':{},'last_error':None,'updated_at':None}
        self._last_snapshot=None
        self.native_verified_at_start=False
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
            with self.guard:base['research']=dict(self.research)
            base['journal']=journal_inspect(self.journal_path)
            base['evolution']=evolution_status(self.evolution_path) if self.event_evolution else {'status':'DISABLED'}
            base['dendrites']=dendrite_snapshot(self.native_path) if self.native_dendrites else {'status':'DISABLED'}
            if self.native_dendrites:base['dendrites']['startup_full_audit']=('PASS' if self.native_verified_at_start else 'PENDING')
            self._last_snapshot=base
            return base
        except (OSError,sqlite3.Error,RuntimeError) as e:
            return {'protocol':PROTOCOL,'source':{},'worker':w,'health':'ERROR','detail':str(e),
                    'certified_independent_ais':0,'promotion':'LOCKED'}
    def full_snapshot(self):
        # Dashboard polling must never initialize schemas, change journal mode,
        # or acquire a writer lock. In particular, a read-only HTTP GET must
        # not mutate/repair the candidate checkpoint.
        with closing(sqlite3.connect(
            f'file:{self.state.as_posix()}?mode=ro', uri=True, timeout=2
        )) as db:
            db.execute('PRAGMA query_only=ON')
            result=pool_status(db, deep_check=False)
        # Report actual source trial coverage, not fabricated zero values when
        # all-configs longitudinal training uses a separate state database.
        from tw8.arena import PROTOCOL as source_protocol
        with closing(sqlite3.connect(f'file:{self.source.as_posix()}?mode=ro', uri=True)) as source_db:
            coverage = dict(source_db.execute(
                'SELECT phase,COUNT(*) FROM trials WHERE protocol=? GROUP BY phase',
                (source_protocol,)).fetchall())
            source_integrity = 'NOT_CHECKED_IN_POLL' # Verified by full bootstrap before server binds
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
                resources={}
                with measure(resources):
                    self._training_batch()
                latest=dict(self._batch_result)
                latest["resources"]=resources
                with self.guard: n=self.worker["batches_completed"]+1
                # Durable training commit must precede research.  A crash during
                # a heavy research run must not make batch n repeat on restart.
                latest['time']=datetime.now(timezone.utc).isoformat()
                journal_record(self.journal_path,'training',{'batch':n,'latest':latest})
                self.update(status='RUNNING',batches_completed=n,latest=latest,last_error=None)
                if self.event_evolution:
                    try:
                        evolution_enqueue(self.evolution_path,batch=n,gain=latest['mean_gain_vs_cold'],resets=latest['reset_count'],accuracy=latest['mean_holdout_accuracy'])
                        evolution_process(self.evolution_path,limit=1)
                    except Exception as evolution_error:
                        # Evolution trial failure must not interrupt durable base training.
                        journal_record(self.journal_path,'research_error',{'batch':n,'component':'event_evolution','error':f'{type(evolution_error).__name__}: {evolution_error}'})
                if self.all_configs and not self.event_evolution and not self.native_dendrites and n % self.research_every == 0:
                    self._research_cycle(n)
            except Exception as e:
                self.update(status="ERROR",last_error=f"{type(e).__name__}: {e}")
                break
            self.shutdown.wait(self.interval)
        if self.worker["status"] not in ("ERROR","STOP_REQUESTED"):
            self.update(status="STOPPED")

    def _training_batch(self):
        if self.native_dendrites:
            result=dendrite_advance(self.native_path,limit=self.participants)
            descendants=advance_descendants(self.native_path,limit=2)
            self._batch_result={'advanced_this_run':result['advanced'],
                'dendritic_registered':result['registered'],
                'dendritic_trained':result['trained'],
                'dendritic_learning_steps':result['learning_steps'],
                'descendant_trials':result['offspring_trials'],
                'descendant_states':result['descendant_states'],
                'descendant_updated_this_run':descendants['advanced_descendants'],
                'selection_adoptions':result['selection_adoptions'],
                'offspring_evidence_total':result['offspring_trials'],
                'integrity':'HASHED_CHECKPOINTS',
                'scope':'D_SERIES_SYNTHETIC_NOT_CERTIFIED'}
            return
        if self.all_configs:
            with closing(pool_init(self.state)) as db:
                result=pool_batch(db,limit=self.participants)
            self._batch_result={'advanced_this_run':result['advanced'],
                'evidence_records':result['status']['audit_records'],
                'trained_distinct':result['status']['trained_distinct'],
                'mean_gain_vs_cold':result['mean_gain_vs_cold'],
                'reset_count':result['reset_count'],
                'mean_holdout_accuracy':result['mean_holdout_accuracy'],
                'integrity':result['status']['integrity']}
        else:
            result=execute(self.source,self.state,self.cycles,self.participants)
            self._batch_result={'advanced_this_run':result['advanced_this_run'],
                'evidence_records':result['evidence_records'],
                'mean_longitudinal_minus_cold':result.get('mean_longitudinal_minus_cold'),
                'transfer_guard':result.get('transfer_guard'),
                'integrity':result['integrity']}

    def _research_cycle(self, batch_number):
        # Research errors remain isolated from the live training checkpoint.
        try:
            from .compute_backtest import evaluate
            with self.guard:self.research['status']='RUNNING'
            payload=evaluate(count=self.research_seeds,
                seed=190000+batch_number*self.research_seeds, generations=3)
            path=self.report.with_name(self.report.stem+f'.research.batch{batch_number}.json')
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_name(path.name+'.tmp')
            if path.exists():
                raise RuntimeError(f'Research evidence already exists; refusing overwrite: {path}')
            temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
            os.replace(temp,path)
            journal_record(self.journal_path,'research',{'batch':batch_number,'results':{k:v for k,v in payload.items() if k!='records'}})
            with self.guard:
                self.research={'status':'COMPLETED','last_error':None,
                    'latest':{k:v for k,v in payload.items() if k!='records'},
                    'evidence_file':str(path),'at_batch':batch_number}
        except Exception as e:
            journal_record(self.journal_path,'research_error',{'batch':batch_number,'error':f'{type(e).__name__}: {e}'})
            with self.guard:self.research={'status':'ERROR',
                'last_error':f'{type(e).__name__}: {e}', 'latest':None}

    def start(self):
        if self.journal_path.exists():journal_verify(self.journal_path)
        if self.event_evolution:evolution_status(self.evolution_path) # reject tampering before service starts
        if self.native_dendrites:
            with closing(dendrite_db(self.native_path)) as db:dendrite_bootstrap(db)
            dendrite_verify_all(self.native_path)
            self.native_verified_at_start=True
        if self.all_configs:
            with closing(pool_init(self.state)) as db: pool_bootstrap(db,self.source)
        snapshot=self.snapshot() # Validate before network binds
        if snapshot.get('health') == 'ERROR':
            raise RuntimeError(f"Offline source/state validation failed: {snapshot.get('detail')}")
        if not self.all_configs and snapshot.get('source', {}).get('integrity') != 'ok':
            raise RuntimeError('Source integrity not verified')
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
    ap.add_argument('--research-every',type=int,default=20)
    ap.add_argument('--research-seeds',type=int,default=4)
    ap.add_argument('--native-dendrites',action='store_true',help='Train 7777 executable D-genotypes with persistent independent checkpoints')
    ap.add_argument('--event-evolution',action='store_true',help='Trigger bounded descendant trials from real training setbacks')
    ap.add_argument('--all-configs',action='store_true',help='Train entire 7777 pool fairly, not fixed 12')
    a=ap.parse_args(argv)
    if a.state_db.resolve() in {a.source_db.resolve(),(a.source_db.resolve().parent/'v9.sqlite').resolve()}:
        ap.error('Refusing legacy/source state database')
    # Refuse silent startup without the correct original evidence pool.
    if a.all_configs:
        with closing(pool_init(a.state_db)) as db:pool_bootstrap(db,a.source_db)
    else:inspect(a.source_db,a.state_db)
    runtime=OfflineRuntime(a.source_db,a.state_db,interval=a.interval,cycles=a.cycles,
                           participants=a.participants,stop_file=a.stop_file,report=a.report,training=not a.read_only,all_configs=a.all_configs,
                           research_every=a.research_every,research_seeds=a.research_seeds,event_evolution=a.event_evolution,native_dendrites=a.native_dendrites)
    print(f'OFFLINE_ORACLE http://127.0.0.1:{a.port}/',flush=True)
    serve(runtime,port=a.port)
if __name__=='__main__':main()
