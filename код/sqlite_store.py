from __future__ import annotations

import sqlite3
import threading
from typing import Iterable

from models import ScalarValue, RecordKind


class SqliteStore:
    SCHEMA_VERSION = 2

    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._cn = sqlite3.connect(path, check_same_thread=False)
        cur = self._cn.cursor()
        cur.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=FULL;
        """)
        self._migrate()
        self._cn.commit()

    def _migrate(self) -> None:
        cur = self._cn.cursor()
        cur.execute("PRAGMA user_version;")
        version = cur.fetchone()[0]
        if version == self.SCHEMA_VERSION and \
           self._columns_ok("raw_values") and self._columns_ok("trends"):
            return
        cur.executescript("""
            DROP TABLE IF EXISTS raw_values;
            DROP TABLE IF EXISTS trends;
            CREATE TABLE raw_values(
                ts INTEGER NOT NULL,
                src_id INTEGER NOT NULL,
                obj_id INTEGER NOT NULL,
                vtype INTEGER NOT NULL,
                value TEXT NOT NULL
            );
            CREATE TABLE trends(
                ts INTEGER NOT NULL,
                src_id INTEGER NOT NULL,
                obj_id INTEGER NOT NULL,
                vtype INTEGER NOT NULL,
                value TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_raw ON raw_values(src_id, obj_id, ts);
            CREATE INDEX IF NOT EXISTS ix_tr  ON trends(src_id, obj_id, ts);
        """)
        cur.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION};")

    def _columns_ok(self, table: str) -> bool:
        cur = self._cn.cursor()
        cur.execute(f"PRAGMA table_info({table});")
        cols = {row[1] for row in cur.fetchall()}
        return {"ts", "src_id", "obj_id", "vtype", "value"}.issubset(cols)

    def _insert(self, table: str, rows: list[tuple]) -> None:
        if not rows:
            return
        with self._lock:
            cur = self._cn.cursor()
            cur.executemany(
                f"INSERT INTO {table}(ts,src_id,obj_id,vtype,value) VALUES(?,?,?,?,?)",
                rows,
            )
            self._cn.commit()

    def insert_mixed(self, batch: Iterable[ScalarValue]) -> None:
        raws, trends = [], []
        for v in batch:
            row = (v.ts, v.src_id, v.obj_id, v.vtype, v.value)
            if v.kind == int(RecordKind.RAW):
                raws.append(row)
            else:
                trends.append(row)
        self._insert("raw_values", raws)
        self._insert("trends", trends)

    def close(self) -> None:
        with self._lock:
            self._cn.close()