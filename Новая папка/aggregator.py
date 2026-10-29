class Aggregator:
    def __init__(self):
        self.valid_count = 0
        self.invalid_count = 0
        self.filtered_count = 0
        self.errors = []
        self.levels = {}
        self.sources = {}
        self.error_codes = {}

    def add_invalid(self, error_msg):
        self.invalid_count += 1
        self.errors.append(error_msg)

    def add_record(self, record):
        self.valid_count += 1
        self.levels[record['level']] = self.levels.get(record['level'], 0) + 1
        self.sources[record['source']] = self.sources.get(record['source'], 0) + 1
        
        if record['level'] == 'ERROR':
            code = record['event_code']
            self.error_codes[code] = self.error_codes.get(code, 0) + 1

    def add_filtered(self):
        self.filtered_count += 1

    def get_top_n_errors(self, n):
        sorted_codes = sorted(self.error_codes.items(), key=lambda x: (-x[1], x[0]))
        return sorted_codes[:n]

    def get_summary(self):
        return {
            "valid_lines": self.valid_count,
            "invalid_lines": self.invalid_count,
            "filtered_events": self.filtered_count,
            "levels_summary": dict(sorted(self.levels.items())),
            "sources_summary": dict(sorted(self.sources.items())),
            "invalid_lines_details": self.errors
        }
