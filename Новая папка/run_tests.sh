#!/bin/bash
echo "=== Запуск тестов и генерация отчёта ==="
python3 -m pytest test_analyzer.py -v --cov=. --cov-report=html:htmlcov --html=report.html --self-contained-html
echo ""
echo "=== Готово! ==="
echo "HTML-отчёт по тестам: ./report.html"
echo "HTML-отчёт по покрытию: ./htmlcov/index.html"
