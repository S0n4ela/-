from __future__ import annotations

import glob
import os
import queue
import random
import signal
import threading
import time

from models import ScalarValue, RecordKind
from wal import Wal, merge_wals
from sqlite_store import SqliteStore
from data_source import DataSource
from trend_engine import TrendEngine
from json_exporter import JsonTrendExporter

SOURCES_COUNT = 4
WAL_MAX_SIZE = 100 * 1024 * 1024
SQLITE_BATCH = 5000
SQLITE_FLUSH_SEC = 1.0
JSON_DUMP_SEC = 10

class App:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")
        self.json_dir = os.path.join(self.data_dir, "json_dumps")
        self.db_path = os.path.join(self.data_dir, "data.db")

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)

        self.stop = threading.Event()

        self.wal_q: queue.Queue = queue.Queue(maxsize=500_000)
        self.sql_q: queue.Queue = queue.Queue(maxsize=500_000)

        self.wals: dict[int, Wal] = {}
        for i in range(SOURCES_COUNT):
            p = os.path.join(self.data_dir, f"wal_{i}.jsonl")
            self.wals[i] = Wal(p, max_size=WAL_MAX_SIZE)

        self.store: SqliteStore | None = None
        self.trend_engine = TrendEngine()
        self.json_exporter = JsonTrendExporter(self.json_dir)
        self.threads: list[threading.Thread] = []

    def recover_from_wals(self) -> int:

        paths: list[str] = []
        for i in range(SOURCES_COUNT):
            paths += glob.glob(os.path.join(self.data_dir, f"wal_{i}.jsonl*"))

        if not paths:
            return 0

        n = 0
        buf: list[ScalarValue] = []
        for v in merge_wals(paths):
            buf.append(v)
            n += 1
            if len(buf) >= SQLITE_BATCH:
                self.store.insert_mixed(buf)
                buf.clear()
        if buf:
            self.store.insert_mixed(buf)

        for p in paths:
            try:
                os.remove(p)
            except OSError:
                pass
        return n

    def wal_worker(self):
        while not self.stop.is_set() or not self.wal_q.empty():
            try:
                v = self.wal_q.get(timeout=0.2)
            except queue.Empty:
                continue
            self.wals[v.src_id].append(v)
            self.sql_q.put(v)
            if v.kind == int(RecordKind.TREND):
                self.json_exporter.add(v)
            self.wal_q.task_done()

    def sql_worker(self):
        buf: list[ScalarValue] = []
        last = time.time()
        while not self.stop.is_set() or not self.sql_q.empty():
            try:
                buf.append(self.sql_q.get(timeout=0.2))
            except queue.Empty:
                pass
            if len(buf) >= SQLITE_BATCH or (buf and time.time() - last > SQLITE_FLUSH_SEC):
                self.store.insert_mixed(buf)
                buf.clear()
                last = time.time()
        if buf:
            self.store.insert_mixed(buf)

    def json_worker(self):
        while not self.stop.is_set():
            if self.stop.wait(JSON_DUMP_SEC):
                break
            self.json_exporter.dump_and_clear()
        self.json_exporter.dump_and_clear()

    def source_worker(self, src: DataSource):
        rnd = random.Random(int(time.time() * 1000) ^ src.src_id)
        while not self.stop.is_set():
            t0 = time.time()
            for raw in src.generate_second(rnd):
                if self.stop.is_set():
                    break
                self.wal_q.put(raw)
                for tr in self.trend_engine.on_raw(raw):
                    self.wal_q.put(tr)
            dt = time.time() - t0
            if dt < 1.0:
                time.sleep(1.0 - dt)

    def run(self):
        self.store = SqliteStore(self.db_path)

        recovered = self.recover_from_wals()
        print(f"[startup] восстановлено из журналов: {recovered}")

        for i in range(SOURCES_COUNT):
            p = os.path.join(self.data_dir, f"wal_{i}.jsonl")
            self.wals[i] = Wal(p, max_size=WAL_MAX_SIZE)

        t_wal = threading.Thread(target=self.wal_worker, daemon=True, name="wal")
        t_sql = threading.Thread(target=self.sql_worker, daemon=True, name="sqlite")
        t_json = threading.Thread(target=self.json_worker, daemon=True, name="json")
        for t in (t_wal, t_sql, t_json):
            t.start()
            self.threads.append(t)

        for i in range(SOURCES_COUNT):
            src = DataSource(i, seed=42 + i)
            t = threading.Thread(target=self.source_worker, args=(src,),
                                 daemon=True, name=f"src-{i}")
            t.start()
            self.threads.append(t)

        print("Работаем. Ctrl+C для выхода.")

        def on_sigint(signum, frame):
            print("[shutdown] остановка...")
            self.stop.set()

        signal.signal(signal.SIGINT, on_sigint)

        while not self.stop.is_set():
            time.sleep(0.5)

        for t in self.threads:
            t.join(timeout=30)

        for w in self.wals.values():
            w.close()
        self.store.close()
        print("[shutdown] готово")

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    App(base).run()