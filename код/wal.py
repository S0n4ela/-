from __future__ import annotations

import json
import os
import threading
import time
from typing import Iterator

from models import ScalarValue


class Wal:


    def __init__(self, path: str, max_size: int = 100 * 1024 * 1024):
        self.path = path
        self.max_size = max_size
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._f = open(path, "a", encoding="utf-8")

    def append(self, v: ScalarValue) -> None:
        line = v.to_json_line()
        with self._lock:
            self._f.write(line + "")
            self._f.flush()
            os.fsync(self._f.fileno())
            if self._f.tell() > self.max_size:
                self._rotate_locked()

    def _rotate_locked(self) -> None:
        self._f.flush()
        os.fsync(self._f.fileno())
        self._f.close()
        ts = time.strftime("%Y%m%dT%H%M%S")
        os.rename(self.path, f"{self.path}.{ts}")
        self._f = open(self.path, "a", encoding="utf-8")

    def close(self) -> None:
        with self._lock:
            if not self._f.closed:
                self._f.flush()
                os.fsync(self._f.fileno())
                self._f.close()

    @staticmethod
    def read_all(path: str) -> Iterator[ScalarValue]:
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield ScalarValue.from_dict(json.loads(line))
                except Exception:
                    continue


def merge_wals(wal_paths: list[str]) -> Iterator[ScalarValue]:

    records: list[ScalarValue] = []
    for p in wal_paths:
        records.extend(Wal.read_all(p))
    records.sort(key=lambda v: v.ts)
    for r in records:
        yield r