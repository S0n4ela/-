from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional

from engine import (
    Product,
    CartItem,
    Customer,
    Order,
    DiscountRegistry,
    PricingEngine,
    D,
)

DEFAULT_CONFIG = [
    {"type": "threeForTwo", "name": "3 по цене 2", "category": "Книги"},
    {"type": "percent", "name": "Осенняя распродажа", "value": 10},
    {"type": "fixed", "name": "500 ₽ от 3000", "value": 500, "threshold": 3000},
    {"type": "loyalty", "name": "Лояльность", "percent": 5, "days": 30},
    {"type": "firstOrder", "name": "Первый заказ", "percent": 10},
    {"type": "freeDelivery", "name": "Бесплатная доставка", "threshold": 5000},
    {
        "type": "promo",
        "name": "Промо SALE",
        "value": 15,
        "code": "SALE",
        "kind": "percent",
        "active": True,
    },
    {
        "type": "promo",
        "name": "Промо FIX500",
        "value": 500,
        "code": "FIX500",
        "kind": "fixed",
        "active": True,
    },
]
def _input(prompt: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    if not raw and default is not None:
        return default
    return raw

def _money(prompt: str, default: str = "0") -> D:
    while True:
        raw = _input(prompt, default)
        try:
            v = D(raw)
            if v < 0:
                print("  Значение не может быть отрицательным.")
                continue
            return v
        except (InvalidOperation, ValueError):
            print("  Введите число, например 1000.50")

def _int(prompt: str, default: str = "1", min_val: int = 1) -> int:
    while True:
        raw = _input(prompt, default)
        try:
            v = int(raw)
            if v < min_val:
                print(f"  Нужно число ≥ {min_val}")
                continue
            return v
        except ValueError:
            print("  Введите целое число")

def build_sample_order() -> Order:
    print(" Сборка заказа ")
    items = []
    n = _int("Сколько позиций в корзине", "2")
    for i in range(n):
        print(f"Позиция {i + 1}:")
        name = _input("  Название", f"Товар{i + 1}")
        price = _money("  Цена", "500")
        cat = _input("  Категория", "Книги")
        qty = _int("  Количество", "1")
        items.append(
            CartItem(Product(f"p{i + 1}", name, price, cat), qty)
        )

    delivery = _money("Стоимость доставки", "300")
    promo = _input("Промокод (пусто — без)", "")
    promo = promo or None

    first = _input("Первый заказ? (y/n)", "n").lower().startswith("y")
    last_raw = _input("Дней с последней покупки (пусто — нет даты)", "")
    last_date = None
    if last_raw:
        try:
            last_date = date.today() - timedelta(days=int(last_raw))
        except ValueError:
            print("  Некорректное число дней, дата не задана.")

    return Order(
        id="console-order",
        customer=Customer("console-user", last_date, first),
        items=items,
        promoCode=promo,
        createdAt=date.today(),
        deliveryCost=delivery,
    )

def print_result(result) -> None:
    print("PricingResult")
    print(f"baseTotal : {result.baseTotal}")
    if not result.appliedDiscounts:
        print("applied   : (нет применённых скидок)")
    else:
        print("applied   :")
        for d in result.appliedDiscounts:
            print(f"  • {d.name}: −{d.amount}  — {d.reason}")
    print(f"finalTotal: {result.finalTotal}")

def show_config(cfg: list) -> None:
    print("Текущая конфигурация скидок:")
    for i, c in enumerate(cfg, 1):
        print(f"  {i}. {c}")

def main() -> None:
    registry = DiscountRegistry()
    registry.load(DEFAULT_CONFIG)
    engine = PricingEngine()

    menu = """
  Движок скидок «Штучки-Дрючки»          
       1. Показать конфигурацию скидок         
       2. Рассчитать заказ (пошаговый ввод)    
       3. Демо-заказ (готовые данные)          
       4. Запустить unit-тесты                 
       0. Выход                                
"""
    while True:
        print(menu)
        choice = _input("Выбор", "0")
        if choice == "0":
            print("До свидания.")
            break
        if choice == "1":
            show_config(registry._config)
        elif choice == "2":
            order = build_sample_order()
            result = engine.calculate(order, registry.build())
            print_result(result)
        elif choice == "3":
            books = Product("p1", "Книга", D("500"), "Книги")
            pens = Product("p2", "Ручка", D("100"), "Канцелярия")
            order = Order(
                id="demo",
                customer=Customer(
                    "c1", date.today() - timedelta(days=12), False
                ),
                items=[CartItem(books, 3), CartItem(pens, 2)],
                promoCode="SALE",
                createdAt=date.today(),
                deliveryCost=D("300"),
            )
            print("Демо: 3 книги × 500, 2 ручки × 100, доставка 300,")
            print("      промокод SALE (15%), лояльность, 3-по-2, …")
            result = engine.calculate(order, registry.build())
            print_result(result)
        elif choice == "4":
            import unittest
            import test_engine

            suite = unittest.defaultTestLoader.loadTestsFromModule(test_engine)
            unittest.TextTestRunner(verbosity=2).run(suite)
        else:
            print("Неизвестный пункт меню.")

if __name__ == "__main__":
    main()
