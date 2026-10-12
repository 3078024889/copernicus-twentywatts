import importlib.util
import tempfile
import unittest
from pathlib import Path
def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
import hashlib, json
from performance.v3_ledger import FastLedger

def digest(x):
    return hashlib.sha256(canonical(x).encode('utf-8')).hexdigest()

class LedgerPerformanceTests(unittest.TestCase):
    def test_legacy_chain_compatible(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'evidence_ledger.jsonl'
            ledger=FastLedger(path,canonical,digest)
            records=[ledger.append({'type':'OBSERVATION','n':i}) for i in range(100)]
            self.assertTrue(ledger.verify())
            self.assertEqual(records[-1]['prev_hash'],records[-2]['event_hash'])
            self.assertEqual(len(path.read_text(encoding='utf-8').splitlines()),100)
            other=FastLedger(path,canonical,digest)
            new=other.append({'type':'RESUME'})
            self.assertEqual(new['prev_hash'],records[-1]['event_hash'])

    def test_reject_tampered_history(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'evidence_ledger.jsonl'
            ledger=FastLedger(path,canonical,digest)
            ledger.append({'type':'SAFE'})
            data=path.read_text(encoding='utf-8').replace('SAFE','TAMPERED')
            path.write_text(data,encoding='utf-8')
            before=path.stat().st_size
            with self.assertRaises(ValueError): ledger.append({'type':'LATER'})
            self.assertEqual(path.stat().st_size,before)

    def test_reject_torn_tail(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'evidence_ledger.jsonl'
            ledger=FastLedger(path,canonical,digest)
            ledger.append({'type':'SAFE'})
            with path.open('ab') as f:f.write(b'{"broken":')
            with self.assertRaises(ValueError): ledger.append({'type':'LATER'})

    def test_external_append_detected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'evidence_ledger.jsonl'
            a=FastLedger(path,canonical,digest)
            a.append({'type':'A'})
            b=FastLedger(path,canonical,digest)
            b.append({'type':'B'})
            x=a.append({'type':'C'})
            self.assertEqual(x['prev_hash'],json.loads(path.read_text(encoding='utf-8').splitlines()[1])['event_hash'])
            self.assertTrue(a.verify())

if __name__=='__main__':unittest.main()
