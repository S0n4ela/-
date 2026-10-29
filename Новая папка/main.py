import os
import sys
from cli import parse_cli_args
from parser import parse_line
from filter import apply_filters
from aggregator import Aggregator
from output import print_to_terminal, save_to_json, save_to_csv

def main():
    args = parse_cli_args()
    
    if not os.path.exists(args.input):
        print(f"Ошибка: Файл {args.input} не найден.")
        sys.exit(1)
    if os.path.getsize(args.input) == 0:
        print(f"Предупреждение: Файл {args.input} пуст.")
        sys.exit(0)

    agg = Aggregator()
    
    with open(args.input, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            record, error = parse_line(line, line_num)
            
            if error:
                agg.add_invalid(error)
                continue
                
            agg.add_record(record)
            
            if apply_filters(record, args.from_dt, args.to_dt, args.level, args.source):
                agg.add_filtered()

    print_to_terminal(agg, args.top)
    
    if args.format != "none":
        if not args.output:
            print("Ошибка: Укажите --output для сохранения файла.")
            sys.exit(1)
            
        if args.format == "json":
            save_to_json(agg, args.top, args.output)
        elif args.format == "csv":
            save_to_csv(agg, args.top, args.output)
        print(f"\nОтчет сохранен в {args.output}")

if __name__ == "__main__":
    main()
