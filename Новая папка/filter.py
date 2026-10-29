def apply_filters(record, from_dt, to_dt, level, source):
    if from_dt and record['timestamp'] < from_dt:
        return False
    if to_dt and record['timestamp'] >= to_dt:
        return False
    if level and record['level'] != level:
        return False
    if source and record['source'] != source:
        return False
    return True
