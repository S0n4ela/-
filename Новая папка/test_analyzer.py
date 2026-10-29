import pytest
import os
import json
import csv
from parser import parse_line, parse_timestamp
from filter import apply_filters
from aggregator import Aggregator
from output import save_to_json, save_to_csv

# --- Тесты парсера ---

def test_parse_valid():
    line = "2026-09-01T00:08:59Z | WARN | auth-api | AUTH_LOGIN_OK | User session created"
    rec, err = parse_line(line, 1)
    assert err is None
    assert rec['level'] == 'WARN'
    assert rec['source'] == 'auth-api'
    assert rec['event_code'] == 'AUTH_LOGIN_OK'

def test_parse_invalid_timestamp():
    rec, err = parse_line("not-a-timestamp | ERROR | api | E1 | msg", 1)
    assert err is not None
    assert "неверный формат timestamp" in err

def test_parse_invalid_level():
    rec, err = parse_line("2026-09-01T00:08:59Z | NOTICE | api | E1 | msg", 1)
    assert err is not None
    assert "неверный уровень" in err

def test_parse_empty_level():
    rec, err = parse_line("2026-09-01T00:08:59Z |  | api | E1 | msg", 1)
    assert err is not None
    assert "пустые поля" in err

def test_parse_empty_message():
    rec, err = parse_line("2026-09-01T00:08:59Z | ERROR | api | E1 | ", 1)
    assert err is not None
    assert "пустые поля" in err

def test_parse_wrong_columns_too_few():
    rec, err = parse_line("2026-09-01T00:08:59Z | ERROR | api", 1)
    assert err is not None
    assert "неверное количество полей" in err

def test_parse_wrong_columns_too_many():
    rec, err = parse_line("2026-09-01T00:08:59Z | ERROR | api | E1 | msg | extra", 1)
    assert err is not None
    assert "неверное количество полей" in err

def test_parse_empty_line():
    rec, err = parse_line("", 1)
    assert err is not None
    assert "пустая строка" in err

def test_parse_all_levels():
    for level in ['TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR']:
        line = f"2026-09-01T00:08:59Z | {level} | api | E1 | msg"
        rec, err = parse_line(line, 1)
        assert err is None
        assert rec['level'] == level

# --- Тесты фильтра ---

def test_filter_no_filters():
    rec = {'timestamp': parse_timestamp("2026-09-01T12:00:00Z"), 'level': 'ERROR', 'source': 'api', 'event_code': 'E1', 'message': 'm'}
    assert apply_filters(rec, None, None, None, None) == True

def test_filter_time_from_inclusive():
    rec = {'timestamp': parse_timestamp("2026-09-01T12:00:00Z"), 'level': 'ERROR', 'source': 'api', 'event_code': 'E1', 'message': 'm'}
    from_dt = parse_timestamp("2026-09-01T12:00:00Z")
    assert apply_filters(rec, from_dt, None, None, None) == True

def test_filter_time_to_exclusive():
    rec = {'timestamp': parse_timestamp("2026-09-01T13:00:00Z"), 'level': 'ERROR', 'source': 'api', 'event_code': 'E1', 'message': 'm'}
    to_dt = parse_timestamp("2026-09-01T13:00:00Z")
    assert apply_filters(rec, None, to_dt, None, None) == False

def test_filter_time_range():
    rec = {'timestamp': parse_timestamp("2026-09-01T12:30:00Z"), 'level': 'ERROR', 'source': 'api', 'event_code': 'E1', 'message': 'm'}
    from_dt = parse_timestamp("2026-09-01T12:00:00Z")
    to_dt = parse_timestamp("2026-09-01T13:00:00Z")
    assert apply_filters(rec, from_dt, to_dt, None, None) == True

def test_filter_level():
    rec = {'timestamp': parse_timestamp("2026-09-01T12:00:00Z"), 'level': 'ERROR', 'source': 'api', 'event_code': 'E1', 'message': 'm'}
    assert apply_filters(rec, None, None, 'ERROR', None) == True
    assert apply_filters(rec, None, None, 'INFO', None) == False

def test_filter_source():
    rec = {'timestamp': parse_timestamp("2026-09-01T12:00:00Z"), 'level': 'ERROR', 'source': 'api', 'event_code': 'E1', 'message': 'm'}
    assert apply_filters(rec, None, None, None, 'api') == True
    assert apply_filters(rec, None, None, None, 'other') == False

def test_filter_combined():
    rec = {'timestamp': parse_timestamp("2026-09-01T12:00:00Z"), 'level': 'ERROR', 'source': 'api', 'event_code': 'E1', 'message': 'm'}
    from_dt = parse_timestamp("2026-09-01T12:00:00Z")
    to_dt = parse_timestamp("2026-09-01T13:00:00Z")
    assert apply_filters(rec, from_dt, to_dt, 'ERROR', 'api') == True
    assert apply_filters(rec, from_dt, to_dt, 'INFO', 'api') == False

# --- Тесты агрегатора ---

def test_aggregator_counts():
    agg = Aggregator()
    agg.add_record({'level': 'ERROR', 'source': 'api', 'event_code': 'E1'})
    agg.add_record({'level': 'ERROR', 'source': 'api', 'event_code': 'E1'})
    agg.add_record({'level': 'INFO', 'source': 'web', 'event_code': 'I1'})
    assert agg.valid_count == 3
    assert agg.levels == {'ERROR': 2, 'INFO': 1}
    assert agg.sources == {'api': 2, 'web': 1}

def test_aggregator_error_codes():
    agg = Aggregator()
    for _ in range(5): agg.add_record({'level': 'ERROR', 'source': 'api', 'event_code': 'E1'})
    for _ in range(3): agg.add_record({'level': 'ERROR', 'source': 'api', 'event_code': 'E2'})
    for _ in range(1): agg.add_record({'level': 'INFO', 'source': 'api', 'event_code': 'I1'})
    top = agg.get_top_n_errors(2)
    assert top == [('E1', 5), ('E2', 3)]

def test_aggregator_top_n_deterministic():
    agg = Aggregator()
    for _ in range(3): agg.add_record({'level': 'ERROR', 'source': 'api', 'event_code': 'B'})
    for _ in range(3): agg.add_record({'level': 'ERROR', 'source': 'api', 'event_code': 'A'})
    top = agg.get_top_n_errors(2)
    assert top == [('A', 3), ('B', 3)]

def test_aggregator_invalid():
    agg = Aggregator()
    agg.add_invalid("Ошибка 1")
    agg.add_invalid("Ошибка 2")
    assert agg.invalid_count == 2
    assert len(agg.errors) == 2

def test_aggregator_filtered():
    agg = Aggregator()
    agg.add_record({'level': 'ERROR', 'source': 'api', 'event_code': 'E1'})
    agg.add_filtered()
    assert agg.filtered_count == 1

def test_aggregator_summary():
    agg = Aggregator()
    agg.add_record({'level': 'ERROR', 'source': 'api', 'event_code': 'E1'})
    agg.add_invalid("err")
    agg.add_filtered()
    s = agg.get_summary()
    assert s['valid_lines'] == 1
    assert s['invalid_lines'] == 1
    assert s['filtered_events'] == 1

# --- Тесты вывода JSON/CSV ---

def test_save_json(tmp_path):
    agg = Aggregator()
    agg.add_record({'level': 'ERROR', 'source': 'api', 'event_code': 'E1'})
    agg.add_invalid("err")
    j_path = str(tmp_path / "out.json")
    save_to_json(agg, 5, j_path)
    assert os.path.exists(j_path)
    with open(j_path) as f:
        data = json.load(f)
    assert data['valid_lines'] == 1
    assert data['invalid_lines'] == 1

def test_save_csv(tmp_path):
    agg = Aggregator()
    agg.add_record({'level': 'ERROR', 'source': 'api', 'event_code': 'E1'})
    c_path = str(tmp_path / "out.csv")
    save_to_csv(agg, 5, c_path)
    assert os.path.exists(c_path)
    with open(c_path) as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert len(rows) > 1

# --- Тесты пустого файла ---

def test_empty_file(tmp_path):
    f_path = str(tmp_path / "empty.log")
    with open(f_path, 'w') as f:
        pass
    agg = Aggregator()
    with open(f_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            record, error = parse_line(line, line_num)
            if error:
                agg.add_invalid(error)
            else:
                agg.add_record(record)
    assert agg.valid_count == 0
    assert agg.invalid_count == 0

# --- Тесты только повреждённых данных ---

def test_only_invalid_lines():
    agg = Aggregator()
    lines = [
        "bad line",
        "2026-09-01T00:08:59Z | BADLEVEL | api | E1 | msg",
        "",
    ]
    for i, line in enumerate(lines, 1):
        rec, err = parse_line(line, i)
        if err:
            agg.add_invalid(err)
        else:
            agg.add_record(rec)
    assert agg.valid_count == 0
    assert agg.invalid_count == 3

# --- Тесты парсера timestamp ---

def test_parse_timestamp_valid():
    ts = parse_timestamp("2026-09-01T12:00:00Z")
    assert ts is not None

def test_parse_timestamp_invalid():
    ts = parse_timestamp("not-a-date")
    assert ts is None

def test_parse_timestamp_without_z():
    ts = parse_timestamp("2026-09-01T12:00:00")
    assert ts is not None
