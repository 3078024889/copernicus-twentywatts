import unittest
from pathlib import Path
from unittest.mock import patch

from fixture_source import source_db
from tw10.offline_oracle import OfflineRuntime


class R208StopRaceTests(unittest.TestCase):
    def test_stop_created_during_source_validation_prevents_initialization(self):
        with __import__("tempfile").TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state.sqlite"
            stop = root / "STOP"
            source = source_db()

            runtime = OfflineRuntime(
                source,
                state,
                interval=1,
                participants=2,
                stop_file=stop,
                report=root / "report.json",
                training=True,
                all_configs=True,
            )

            path_type = type(runtime.source)
            original_is_file = path_type.is_file

            def inject_stop(path):
                if path == runtime.source:
                    stop.touch(exist_ok=True)
                    return True
                return original_is_file(path)

            with patch.object(
                path_type,
                "is_file",
                autospec=True,
                side_effect=inject_stop,
            ):
                runtime.start()

            self.assertEqual(runtime.worker["status"], "STOP_REQUESTED")
            self.assertIsNone(runtime.thread)
            self.assertFalse(
                state.exists(),
                "STOP appeared before initialization, but state DB was created",
            )


if __name__ == "__main__":
    unittest.main()
