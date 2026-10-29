from datetime import datetime

VALID_LEVELS = {'TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR'}

def parse_timestamp(ts_str):
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    except Exception:
        return None

def parse_line(line, line_num):
    line = line.strip()
    if not line:
        return None, f"Строка {line_num}: пустая строка"
    
    parts = line.split('|')
    if len(parts) != 5:
        return None, f"Строка {line_num}: неверное количество полей ({len(parts)})"
    
    ts_str, level, source, event_code, message = [p.strip() for p in parts]
    
    if not all([ts_str, level, source, event_code, message]):
        return None, f"Строка {line_num}: есть пустые поля"
        
    ts = parse_timestamp(ts_str)
    if not ts:
        return None, f"Строка {line_num}: неверный формат timestamp ({ts_str})"
        
    if level not in VALID_LEVELS:
        return None, f"Строка {line_num}: неверный уровень ({level})"
        
    return {
        'timestamp': ts,
        'level': level,
        'source': source,
        'event_code': event_code,
        'message': message
    }, None
