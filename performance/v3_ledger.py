"""Opt-in, legacy-compatible accelerated V3 JSONL evidence ledger.

No writes to the legacy V3 workspace are made by this module unless caller passes
that path explicitly. Single-process append-only writer; do not share across writers.
"""
from __future__ import annotations
import json
import os
import threading
from pathlib import Path
from typing import Callable


class FastLedger:
    def __init__(self, path: Path, canonical: Callable, digest: Callable):
        self.path = Path(path)
        self.canonical = canonical
        self.digest = digest
        self._lock = threading.RLock()
        self._last_hash = 'GENESIS'
        self._size = 0
        self._mtime_ns = None
        self._loaded = False

    def _reload(self):
        """Stream-verify complete legacy chain once at open or on external change.

        Refuses malformed, truncated, or modified evidence rather than truncating it.
        """
        last = 'GENESIS'
        if self.path.exists():
            with self.path.open('rb') as f:
                for number, raw in enumerate(f, 1):
                    if not raw.strip():
                        continue
                    if not raw.endswith(b'\n'):
                        raise ValueError(f'incomplete ledger line {number}')
                    obj = json.loads(raw.decode('utf-8'))
                    event_hash = obj.pop('event_hash')
                    if obj.get('prev_hash') != last or self.digest(obj) != event_hash:
                        raise ValueError(f'evidence chain mismatch at line {number}')
                    last = event_hash
        self._last_hash = last
        self._sync_stat()
        self._loaded = True

    def _sync_stat(self):
        if self.path.exists():
            st = self.path.stat()
            self._size, self._mtime_ns = st.st_size, st.st_mtime_ns
        else:
            self._size, self._mtime_ns = 0, None

    def _changed(self):
        if not self.path.exists():
            return self._size != 0
        st = self.path.stat()
        return st.st_size != self._size or st.st_mtime_ns != self._mtime_ns

    def append(self, event):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self._loaded or self._changed():
                self._reload()
            import time
            obj = dict(event)
            obj['schema'] = 'twentywatts-evolution-lab-v3-learning-algorithm'
            obj['ts_ns'] = time.time_ns()
            obj['prev_hash'] = self._last_hash
            obj['event_hash'] = self.digest(obj)
            raw = (self.canonical(obj) + '\n').encode('utf-8')
            with self.path.open('ab') as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            self._last_hash = obj['event_hash']
            self._sync_stat()
            return obj

    def verify(self):
        with self._lock:
            try:
                self._reload()
                return True
            except (ValueError, KeyError, UnicodeError, json.JSONDecodeError):
                return False
