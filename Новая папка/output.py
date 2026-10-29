import json
import csv

def print_to_terminal(agg, top_n):
    summary = agg.get_summary()
    print("\n=== СВОДКА ===")
    print(f"Корректных строк: {summary['valid_lines']}")
    print(f"Ошибочных строк: {summary['invalid_lines']}")
    print(f"Событий после фильтрации: {summary['filtered_events']}")
    
    print("\nСобытий по уровням:")
    for k, v in summary['levels_summary'].items():
        print(f"  {k}: {v}")
        
    print("\nСобытий по источникам:")
    for k, v in summary['sources_summary'].items():
        print(f"  {k}: {v}")
        
    print(f"\nTop-{top_n} кодов ошибок:")
    for code, count in agg.get_top_n_errors(top_n):
        print(f"  {code}: {count}")
        
    if summary['invalid_lines_details']:
        print("\nОшибки парсинга (первые 5):")
        for err in summary['invalid_lines_details'][:5]:
            print(f"  {err}")

def save_to_json(agg, top_n, filepath):
    data = agg.get_summary()
    data["top_error_codes"] = [{"code": c, "count": n} for c, n in agg.get_top_n_errors(top_n)]
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

def save_to_csv(agg, top_n, filepath):
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Категория", "Ключ", "Значение"])
        writer.writerow(["Общее", "Корректных строк", agg.valid_count])
        writer.writerow(["Общее", "Ошибочных строк", agg.invalid_count])
        writer.writerow(["Общее", "Отфильтровано событий", agg.filtered_count])
        
        for k, v in sorted(agg.levels.items()):
            writer.writerow(["Уровни", k, v])
        for k, v in sorted(agg.sources.items()):
            writer.writerow(["Источники", k, v])
        for code, count in agg.get_top_n_errors(top_n):
            writer.writerow(["Top Ошибки", code, count])
