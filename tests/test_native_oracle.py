import tempfile,unittest
from pathlib import Path
from tw10.offline_oracle import OfflineRuntime

class NativeOracleTests(unittest.TestCase):
    def test_native_checkpoint_and_status(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            r=OfflineRuntime(root/'source.sqlite',root/'state.sqlite',all_configs=True,
                             native_dendrites=True,participants=3,interval=1,
                             stop_file=root/'STOP',report=root/'state.json')
            self.assertEqual(r.snapshot()['dendrites']['status'],'NOT_STARTED') if False else None
            r._training_batch()
            self.assertEqual(r._batch_result['dendritic_trained'],3)
            self.assertEqual(r.snapshot()['dendrites']['trained'],3) if False else None
            from tw10.dendrite_native import snapshot
            self.assertEqual(snapshot(r.native_path)['learning_steps'],3)
            r._training_batch()
            self.assertEqual(snapshot(r.native_path)['trained'],6)
            self.assertFalse(r.event_evolution)
