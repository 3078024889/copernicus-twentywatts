import tempfile
import unittest
from pathlib import Path

from fixture_source import source_db
from tw10.offline_oracle import OfflineRuntime


class R203StopBeforeWriteTests(unittest.TestCase):
    def test_existing_stop_prevents_state_database_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state.sqlite"
            stop = root / "STOP"
            stop.touch()

            runtime = OfflineRuntime(
                source_db(),
                state,
                interval=1,
                participants=2,
                stop_file=stop,
                report=root / "report.json",
                training=True,
                all_configs=True,
            )

            runtime.start()

            self.assertEqual(runtime.worker["status"], "STOP_REQUESTED")
            self.assertIsNone(runtime.thread)
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
