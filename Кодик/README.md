# Движок скидок «Штучки-Дрючки»

Расширяемый механизм расчёта скидок на Python. Бизнес-правила отделены от ядра через паттерны **Strategy**, **Factory** и **Singleton**.

## Запуск

```bash
# Демо (один готовый заказ)
python engine.py

# Консольный пошаговый интерфейс
python main.py

# Unit-тесты
python -m unittest test_engine -v
# или из меню main.py → пункт 4
```

Требования: Python 3.10+ (стандартная библиотека, без внешних зависимостей).

## Схема классов

```
Discount (ABC)
├── ThreeForTwo          stage=1
├── Percent              stage=2, competes_in_percent_slot=True
├── Loyalty              stage=2
├── FirstOrder           stage=2
├── Promo (percent)      stage=2, competes_in_percent_slot=True, prefers_on_tie
├── Promo (fixed)        stage=3
├── Fixed                stage=3
└── FreeDelivery         stage=4

DiscountFactory.create(cfg)  →  Discount
DiscountRegistry (Singleton) → load(cfg) / build() → list[Discount]
PricingEngine.calculate(order, strategies) → PricingResult
```

Модели: `Product`, `CartItem`, `Customer`, `Order`, `DiscountContext`,
`AppliedDiscount`, `PricingResult`.

`PricingEngine` работает **только** с абстракцией `Discount` и полями
`stage` / `competes_in_percent_slot` / `prefers_on_tie` / `preview_amount`.
Проверок `isinstance` / `type is` конкретных стратегий внутри движка нет.

## Порядок применения скидок

1. **Stage 1** — «3 по цене 2» (количественная, до денежных).
2. **Percent-slot** — среди всех стратегий с `competes_in_percent_slot=True`
   (обычные `percent` + процентные промокоды) выбирается **одна** с
   максимальной денежной выгодой. При равенстве побеждает промокод
   (`prefers_on_tie`).
3. **Stage 2 (остальные)** — лояльность и скидка первого заказа
   (могут сочетаться с победителем percent-slot; считаются от уже
   уменьшенной суммы, в порядке конфигурации).
4. **Stage 3** — фиксированные скидки и **фиксированные** промокоды
   (не конфликтуют с обычной процентной).
5. **Stage 4** — бесплатная доставка (строго `items_total > threshold`).

Внутри одной стадии сохраняется порядок из конфигурации.

## Правила расчёта

| Правило | Детали |
|--------|--------|
| Процентные / фиксированные | Уменьшают только сумму товаров, не доставку |
| 3 по цене 2 | Товары одной категории вместе; бесплатны самые дешёвые; `floor(qty/3)` |
| Лояльность | `0 ≤ (createdAt − lastPurchaseDate).days ≤ days` (включительно). Будущая дата — скидки нет |
| Промокод | Срок включителен (`createdAt ≤ expires`). Сравнение кодов **case-insensitive** (через `.upper()`) |
| Нижняя граница | Скидка не больше текущей суммы соответствующей части; итог ≥ 0 |
| Округление | `Decimal.quantize(0.01, ROUND_HALF_EVEN)` после **каждого** денежного результата (`money()`) |

## Конфигурация

Движок не создаёт стратегии сам — получает готовый список из фабрики/реестра.

```python
[
  {"type": "percent", "value": 10, "name": "Осенняя распродажа"},
  {"type": "fixed", "value": 500, "threshold": 3000, "name": "500 ₽ от 3000"},
  {"type": "threeForTwo", "category": "Книги", "name": "3 по цене 2"},
  {"type": "loyalty", "percent": 5, "days": 30, "name": "Лояльность"},
  {"type": "firstOrder", "percent": 10, "name": "Первый заказ"},
  {"type": "freeDelivery", "threshold": 5000, "name": "Бесплатная доставка"},
  {"type": "promo", "code": "SALE", "value": 15, "kind": "percent", "name": "SALE"},
  {"type": "promo", "code": "FIX500", "value": 500, "kind": "fixed", "name": "FIX500",
   "expires": "2026-12-31", "active": true},
]
```

Расширение: новый класс-наследник `Discount` + `DiscountFactory.register("type", lambda cfg: ...)`.

## Некорректный ввод

| Ситуация | Реакция |
|----------|---------|
| `quantity ≤ 0` | `ValueError` |
| `basePrice < 0` / `deliveryCost < 0` | `ValueError` |
| Неизвестный `type` в конфиге | `ValueError` |
| Нет поля `type` | `ValueError` |
| Промокод неизвестен / просрочен / неактивен | Скидка не применяется (без исключения) |
| Пустая корзина | `finalTotal = 0`, пустой breakdown |

## Breakdown

В `appliedDiscounts` попадают только реально применённые скидки с
`amount > 0`, в порядке расчёта.

```json
{
  "baseTotal": 1800.00,
  "appliedDiscounts": [
    {"name": "3 по цене 2", "amount": 500.00, "reason": "Категория Книги: 3 ед., 1 бесплатно"},
    {"name": "Лояльность", "amount": 50.00, "reason": "Последняя покупка была 12 дн. назад"}
  ],
  "finalTotal": 1250.00
}
```

`baseTotal` = сумма `basePrice × quantity` + исходная `deliveryCost`.  
`finalTotal` = текущая сумма товаров + текущая доставка после всех правил.
