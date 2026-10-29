import argparse
from parser import parse_timestamp

def parse_cli_args():
    parser = argparse.ArgumentParser(description="Анализатор журналов событий")
    parser.add_argument("--input", required=True, help="Путь к файлу лога")
    parser.add_argument("--from", dest="from_dt", help="Начало интервала (ISO 8601)")
    parser.add_argument("--to", dest="to_dt", help="Конец интервала (ISO 8601)")
    parser.add_argument("--level", help="Фильтр по уровню")
    parser.add_argument("--source", help="Фильтр по источнику")
    parser.add_argument("--top", type=int, default=5, help="Количество топ-ошибок")
    parser.add_argument("--format", choices=["json", "csv", "none"], default="none")
    parser.add_argument("--output", help="Путь для сохранения отчета")
    
    args = parser.parse_args()
    
    if args.from_dt:
        args.from_dt = parse_timestamp(args.from_dt)
        if not args.from_dt:
            raise ValueError("Неверный формат даты --from")
    if args.to_dt:
        args.to_dt = parse_timestamp(args.to_dt)
        if not args.to_dt:
            raise ValueError("Неверный формат даты --to")
        
    return args
