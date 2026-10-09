from __future__ import annotations

import random
import time
from typing import Iterator

from models import ScalarValue, ValueType, RecordKind


class DataSource:

    OBJECTS_PER_SOURCE = 1000

    def __init__(self, src_id: int, seed: int):
        self.src_id = src_id
        rnd = random.Random(seed)
        self._objects: list[tuple[ValueType, callable]] = []
        for _ in range(self.OBJECTS_PER_SOURCE):
            t = ValueType(rnd.randint(0, 3))
            self._objects.append((t, self._make_gen(t, rnd)))

    @staticmethod
    def _make_gen(t: ValueType, rnd: random.Random):
        if t == ValueType.INT:
            return lambda: rnd.randint(-1_000_000, 1_000_000)
        if t == ValueType.DOUBLE:
            return lambda: rnd.random() * 1000.0
        if t == ValueType.BOOL:
            return lambda: rnd.randint(0, 1) == 1
        return lambda: "%08x" % rnd.getrandbits(32)

    def generate_second(self, rnd: random.Random) -> Iterator[ScalarValue]:
        n = rnd.randint(100, 600)
        ts = int(time.time() * 1000)
        for _ in range(n):
            obj = rnd.randrange(self.OBJECTS_PER_SOURCE)
            vtype, gen = self._objects[obj]
            yield ScalarValue.make(ts, self.src_id, obj, vtype, gen(), RecordKind.RAW)