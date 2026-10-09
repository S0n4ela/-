from __future__ import annotations

import json
import os
import threading
import time

from models import ScalarValue


class JsonTrendExporter:

    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self._lock = threading.Lock()
        self._pending: list[ScalarValue] = []

    def add(self, v: ScalarValue) -> None:
        with self._lock:
            self._pending.append(v)

    def dump_and_clear(self) -> None:
        with self._lock:
            snapshot, self._pending = self._pending, []
        if not snapshot:
            return
        fname = f"trends_dump_{int(time.time() * 1000)}.json"
        path = os.path.join(self.out_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([v.__dict__ for v in snapshot], f,
                      ensure_ascii=False, separators=(",", ":"))