from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from enum import IntEnum


class ValueType(IntEnum):
    INT = 0
    DOUBLE = 1
    BOOL = 2
    STRING = 3


class RecordKind(IntEnum):
    RAW = 0
    TREND = 1


@dataclass
class ScalarValue:
    ts: int
    src_id: int
    obj_id: int
    vtype: int
    kind: int
    value: str

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def from_dict(d: dict) -> "ScalarValue":
        return ScalarValue(
            ts=int(d["ts"]),
            src_id=int(d["src_id"]),
            obj_id=int(d["obj_id"]),
            vtype=int(d["vtype"]),
            kind=int(d["kind"]),
            value=str(d["value"]),
        )

    @staticmethod
    def make(ts: int, src: int, obj: int, vtype: ValueType,
             raw, kind: RecordKind) -> "ScalarValue":
        if vtype == ValueType.INT:
            s = str(int(raw))
        elif vtype == ValueType.DOUBLE:
            s = repr(float(raw))
        elif vtype == ValueType.BOOL:
            s = "1" if bool(raw) else "0"
        else:
            s = str(raw)
        return ScalarValue(ts, src, obj, int(vtype), int(kind), s)