import json, tempfile, threading, time, unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from fixture_source import source_db
from tw10.offline_oracle import OfflineRuntime, handler_for

class OfflineOracleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        source=source_db()
        self.runtime=OfflineRuntime(source,root/'v14.sqlite',interval=1,participants=2,stop_file=root/'STOP',report=root/'status.json')
    def test_page_status_read_only(self):
        self.runtime.start() if False else None
        s=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.runtime))
        t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
        try:
            url=f'http://127.0.0.1:{s.server_port}'
            with urlopen(url+'/') as r:self.assertIn('离线神谕之座',r.read().decode())
            with urlopen(url+'/api/live') as r:
                payload=json.load(r)
                self.assertEqual(payload['source']['configurations'],7777)
                self.assertEqual(payload['certified_independent_ais'],0)
            with self.assertRaises(HTTPError) as ex:urlopen(Request(url+'/api/live',method='POST'))
            self.assertEqual(ex.exception.code,405)
        finally:
            s.shutdown();s.server_close();t.join(timeout=3)
    def test_auto_training_and_recovery(self):
        self.runtime.start()
        for _ in range(120):
            if self.runtime.worker['batches_completed']>=1:break
            time.sleep(.05)
        self.assertGreaterEqual(self.runtime.worker['batches_completed'],1)
        self.runtime.stop()
        snapshot=self.runtime.snapshot()
        self.assertGreaterEqual(snapshot['longitudinal_cycles'],2)
        self.assertEqual(snapshot['promotion'],'LOCKED')
        other=OfflineRuntime(self.runtime.source,self.runtime.state,interval=1,participants=2,
                             stop_file=self.runtime.stop_file,report=self.runtime.report)
        self.assertGreaterEqual(other.snapshot()['longitudinal_cycles'],2)
    def test_stop_file_suppresses_worker(self):
        self.runtime.stop_file.touch()
        self.runtime.start()
        self.assertEqual(self.runtime.worker['status'],'STOP_REQUESTED')
        self.assertIsNone(self.runtime.thread)
    def test_invalid_params(self):
        with self.assertRaises(ValueError): OfflineRuntime(self.runtime.source,self.runtime.source)
        with self.assertRaises(ValueError): OfflineRuntime(self.runtime.source,self.runtime.state,interval=0)
