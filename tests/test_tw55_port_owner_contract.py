from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class FixedPortOwnershipTests(unittest.TestCase):
 def test_owner_inspection_never_kills_processes(self):
  s=(ROOT/'scripts/INSPECT_PORT_OWNERS_WINDOWS.ps1').read_text()
  self.assertIn('Get-CimInstance Win32_Process',s)
  self.assertIn('Get-NetTCPConnection',s)
  for forbidden in ('Stop-Process','taskkill','Remove-Item','Terminate('):
   self.assertNotIn(forbidden,s)
 def test_switch_inspects_occupied_ports_before_migration(self):
  s=(ROOT/'scripts/SWITCH_TO_FIXED_28720_WINDOWS.ps1').read_text()
  self.assertLess(s.index('FIXED_PORT_BUSY'),s.index('migrate_native_state.py'))
  self.assertIn('INSPECT_PORT_OWNERS_WINDOWS.ps1',s)

class MigrationRollbackTests(unittest.TestCase):
 def test_failed_post_commit_validation_restores_target_and_removes_new_sidecar(self):
  import tempfile, sqlite3
  from contextlib import closing
  from unittest.mock import patch
  from scripts.migrate_native_state import migrate, verify_all as native_verify
  from tw10.dendrite_native import advance
  with tempfile.TemporaryDirectory() as tmp:
   old=Path(tmp)/'old'; new=Path(tmp)/'new'
   for r in (old,new):
    (r/'data').mkdir(parents=True)
    (r/'data'/'v8.sqlite').write_bytes(b'same-source')
   source=old/'data'/'full_pool_fair_v2.sqlite'
   target=new/'data'/'full_pool_fair_v2.sqlite'
   with closing(sqlite3.connect(source)) as db:
    db.execute('CREATE TABLE marker(n INTEGER)');db.execute('INSERT INTO marker VALUES(99)');db.commit()
   with closing(sqlite3.connect(target)) as db:
    db.execute('CREATE TABLE marker(n INTEGER)');db.execute('INSERT INTO marker VALUES(12)');db.commit()
   native=Path(str(source)+'.dendrite_native.sqlite')
   advance(native,limit=1)
   count=[0]
   def fail_after_install(path):
    count[0]+=1
    if count[0]>=3:raise RuntimeError('intentional verification failure')
    return native_verify(path)
   with patch('scripts.migrate_native_state.verify_all',side_effect=fail_after_install):
    with self.assertRaisesRegex(RuntimeError,'intentional verification failure'):
     migrate(old,new)
   with closing(sqlite3.connect(target)) as db:
    self.assertEqual(db.execute('SELECT n FROM marker').fetchone()[0],12)
   self.assertFalse((new/'data'/native.name).exists())
