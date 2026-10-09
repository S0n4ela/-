from __future__ import annotations

from typing import Iterator

from models import ScalarValue, ValueType, RecordKind


class TrendEngine:


    WINDOW = 10

    def __init__(self):
        self._sum: dict[tuple[int, int], float] = {}
        self._cnt: dict[tuple[int, int], int] = {}

    def on_raw(self, v: ScalarValue) -> Iterator[ScalarValue]:
        if v.vtype != int(ValueType.DOUBLE):
            return
        key = (v.src_id, v.obj_id)
        self._sum[key] = self._sum.get(key, 0.0) + float(v.value)
        self._cnt[key] = self._cnt.get(key, 0) + 1
        if self._cnt[key] >= self.WINDOW:
            avg = self._sum[key] / self._cnt[key]
            self._sum[key] = 0.0
            self._cnt[key] = 0
            yield ScalarValue.make(v.ts, v.src_id, v.obj_id,
                                   ValueType.DOUBLE, avg, RecordKind.TREND)