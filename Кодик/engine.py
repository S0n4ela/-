from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Optional

D = Decimal
CENT = D("0.01")
HUNDRED = D("100")

def money(x: Any) -> D:
    return D(str(x)).quantize(CENT, rounding=ROUND_HALF_EVEN)

@dataclass
class Product:
    id: str
    name: str
    basePrice: D
    category: str

    def __post_init__(self) -> None:
        self.basePrice = money(self.basePrice)
        if self.basePrice < 0:
            raise ValueError("basePrice не может быть отрицательным")

@dataclass
class CartItem:
    product: Product
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity должен быть > 0")

@dataclass
class Customer:
    id: str
    lastPurchaseDate: Optional[date]
    isFirstOrder: bool

@dataclass
class Order:
    id: str
    customer: Customer
    items: list
    promoCode: Optional[str] = None
    createdAt: date = field(default_factory=date.today)
    deliveryCost: D = field(default_factory=lambda: D("0"))

    def __post_init__(self) -> None:
        self.deliveryCost = money(self.deliveryCost)
        if self.deliveryCost < 0:
            raise ValueError("deliveryCost не может быть отрицательным")

@dataclass
class AppliedDiscount:
    name: str
    amount: D
    reason: str

@dataclass
class PricingResult:
    baseTotal: D
    appliedDiscounts: list
    finalTotal: D

@dataclass
class DiscountContext:
    order: Order
    items_total: D
    delivery: D
    applied: list = field(default_factory=list)
    entered_promo: Optional[str] = None
    applied_promo: Optional[str] = None

    def cut_items(self, name: str, amount: Any, reason: str) -> Optional[AppliedDiscount]:
        amount = min(money(amount), self.items_total)
        if amount <= 0:
            return None
        self.items_total = money(self.items_total - amount)
        rec = AppliedDiscount(name, amount, reason)
        self.applied.append(rec)
        return rec

    def cut_delivery(self, name: str, reason: str) -> Optional[AppliedDiscount]:
        if self.delivery <= 0:
            return None
        amount = self.delivery
        self.delivery = D("0")
        rec = AppliedDiscount(name, amount, reason)
        self.applied.append(rec)
        return rec

class Discount(ABC):

    stage: int = 99
    competes_in_percent_slot: bool = False

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def apply(self, ctx: DiscountContext) -> None:
        ...

    def preview_amount(self, ctx: DiscountContext) -> D:
        return D("0")

class ThreeForTwo(Discount):
    stage = 1

    def __init__(self, name: str, category: str) -> None:
        super().__init__(name)
        self.category = category

    def apply(self, ctx: DiscountContext) -> None:
        prices: list[D] = []
        for it in ctx.order.items:
            if it.product.category == self.category:
                for _ in range(it.quantity):
                    prices.append(it.product.basePrice)
        prices.sort()
        free_count = len(prices) // 3
        if free_count == 0:
            return
        amount = sum(prices[:free_count], D("0"))
        ctx.cut_items(
            self.name,
            amount,
            f"Категория {self.category}: {len(prices)} ед., {free_count} бесплатно",
        )

class Percent(Discount):

    stage = 2
    competes_in_percent_slot = True

    def __init__(self, name: str, value: Any) -> None:
        super().__init__(name)
        self.value = D(str(value))

    def preview_amount(self, ctx: DiscountContext) -> D:
        if self.value <= 0 or ctx.items_total <= 0:
            return D("0")
        return money(ctx.items_total * self.value / HUNDRED)

    def apply(self, ctx: DiscountContext) -> None:
        amount = self.preview_amount(ctx)
        if amount > 0:
            ctx.cut_items(self.name, amount, f"{self.value}% от суммы товаров")

class Loyalty(Discount):

    stage = 2
    competes_in_percent_slot = False

    def __init__(self, name: str, percent: Any = 5, days: int = 30) -> None:
        super().__init__(name)
        self.percent = D(str(percent))
        self.days = int(days)

    def apply(self, ctx: DiscountContext) -> None:
        last = ctx.order.customer.lastPurchaseDate
        if last is None:
            return
        delta = (ctx.order.createdAt - last).days
        if not (0 <= delta <= self.days):
            return
        amount = money(ctx.items_total * self.percent / HUNDRED)
        if amount > 0:
            ctx.cut_items(
                self.name,
                amount,
                f"Последняя покупка была {delta} дн. назад",
            )

class FirstOrder(Discount):
    stage = 2
    competes_in_percent_slot = False

    def __init__(self, name: str, percent: Any = 10) -> None:
        super().__init__(name)
        self.percent = D(str(percent))

    def apply(self, ctx: DiscountContext) -> None:
        if not ctx.order.customer.isFirstOrder:
            return
        amount = money(ctx.items_total * self.percent / HUNDRED)
        if amount > 0:
            ctx.cut_items(self.name, amount, "Первый заказ")

class Fixed(Discount):
    stage = 3

    def __init__(self, name: str, value: Any, threshold: Any = 0) -> None:
        super().__init__(name)
        self.value = money(value)
        self.threshold = money(threshold)

    def apply(self, ctx: DiscountContext) -> None:
        if ctx.items_total < self.threshold:
            return
        ctx.cut_items(
            self.name,
            self.value,
            f"Фикс. {self.value} при сумме ≥ {self.threshold}",
        )

class Promo(Discount):
    prefers_on_tie = True

    def __init__(
        self,
        name: str,
        value: Any,
        code: str,
        kind: str = "percent",
        expires: Optional[date] = None,
        active: bool = True,
    ) -> None:
        super().__init__(name)
        kind = (kind or "percent").lower()
        if kind not in ("percent", "fixed"):
            raise ValueError(f"promo kind должен быть 'percent' или 'fixed', получено: {kind!r}")
        self.kind = kind
        self.value = D(str(value)) if kind == "percent" else money(value)
        self.code = code.upper()
        self.expires = expires
        self.active = bool(active)
        if kind == "percent":
            self.stage = 2
            self.competes_in_percent_slot = True
        else:
            self.stage = 3
            self.competes_in_percent_slot = False

    def _valid(self, ctx: DiscountContext) -> bool:
        if not self.active:
            return False
        entered = ctx.entered_promo
        if entered is None:
            return False
        if entered.upper() != self.code:
            return False
        if self.expires is not None and ctx.order.createdAt > self.expires:
            return False
        return True

    def preview_amount(self, ctx: DiscountContext) -> D:
        if not self._valid(ctx) or self.kind != "percent":
            return D("0")
        if self.value <= 0 or ctx.items_total <= 0:
            return D("0")
        return money(ctx.items_total * self.value / HUNDRED)

    def apply(self, ctx: DiscountContext) -> None:
        if not self._valid(ctx):
            return
        if self.kind == "percent":
            amount = money(ctx.items_total * self.value / HUNDRED)
            rec = ctx.cut_items(self.name, amount, f"Промокод {self.code} (−{self.value}%)")
        else:
            rec = ctx.cut_items(
                self.name,
                self.value,
                f"Промокод {self.code} (−{self.value} ₽)",
            )
        if rec is not None:
            ctx.applied_promo = self.code

class FreeDelivery(Discount):
    stage = 4

    def __init__(self, name: str, threshold: Any) -> None:
        super().__init__(name)
        self.threshold = money(threshold)

    def apply(self, ctx: DiscountContext) -> None:
        if ctx.items_total > self.threshold:
            ctx.cut_delivery(
                self.name,
                f"Сумма товаров {ctx.items_total} > {self.threshold}: доставка 0",
            )

class DiscountFactory:
    _creators: dict = {}

    @classmethod
    def register(cls, type_name: str, creator) -> None:
        cls._creators[type_name] = creator

    @classmethod
    def create(cls, cfg: dict) -> Discount:
        if "type" not in cfg:
            raise ValueError("в конфиге отсутствует поле 'type'")
        t = cfg["type"]
        if t not in cls._creators:
            raise ValueError(f"неизвестный тип скидки: {t!r}")
        return cls._creators[t](cfg)

def _parse_expires(raw) -> Optional[date]:
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw))

DiscountFactory.register(
    "percent",
    lambda c: Percent(c["name"], c["value"]),
)
DiscountFactory.register(
    "fixed",
    lambda c: Fixed(c["name"], c["value"], c.get("threshold", 0)),
)
DiscountFactory.register(
    "threeForTwo",
    lambda c: ThreeForTwo(c["name"], c["category"]),
)
DiscountFactory.register(
    "loyalty",
    lambda c: Loyalty(c["name"], c.get("percent", 5), c.get("days", 30)),
)
DiscountFactory.register(
    "firstOrder",
    lambda c: FirstOrder(c["name"], c.get("percent", 10)),
)
DiscountFactory.register(
    "freeDelivery",
    lambda c: FreeDelivery(c["name"], c["threshold"]),
)
DiscountFactory.register(
    "promo",
    lambda c: Promo(
        c["name"],
        c["value"],
        c["code"],
        kind=c.get("kind", "percent"),
        expires=_parse_expires(c.get("expires")),
        active=c.get("active", True),
    ),
)

class DiscountRegistry:

    _instance: Optional["DiscountRegistry"] = None

    def __new__(cls) -> "DiscountRegistry":
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._config: list = []
            cls._instance = inst
        return cls._instance

    def load(self, config: list) -> None:
        self._config = list(config)

    def build(self) -> list:
        return [DiscountFactory.create(c) for c in self._config]

    def clear(self) -> None:
        self._config = []

class PricingEngine:
    def calculate(self, order: Order, strategies: list) -> PricingResult:
        items_sum = money(
            sum((it.product.basePrice * it.quantity for it in order.items), D("0"))
        )
        base_total = money(items_sum + order.deliveryCost)

        ctx = DiscountContext(
            order=order,
            items_total=items_sum,
            delivery=money(order.deliveryCost),
            entered_promo=order.promoCode,
        )

        slot_competitors = [s for s in strategies if s.competes_in_percent_slot]
        others = [s for s in strategies if not s.competes_in_percent_slot]

        for s in sorted(
            [s for s in others if s.stage == 1],
            key=lambda s: strategies.index(s),
        ):
            s.apply(ctx)

        winner = self._pick_percent_slot_winner(slot_competitors, ctx)
        if winner is not None:
            winner.apply(ctx)

        for s in sorted(
            [s for s in others if s.stage == 2],
            key=lambda s: strategies.index(s),
        ):
            s.apply(ctx)

        for s in sorted(
            [s for s in others if s.stage == 3],
            key=lambda s: strategies.index(s),
        ):
            s.apply(ctx)

        for s in sorted(
            [s for s in others if s.stage == 4],
            key=lambda s: strategies.index(s),
        ):
            s.apply(ctx)

        final_total = money(ctx.items_total + ctx.delivery)
        if final_total < 0:
            final_total = D("0")

        return PricingResult(base_total, list(ctx.applied), final_total)

    @staticmethod
    def _pick_percent_slot_winner(
        competitors: list, ctx: DiscountContext
    ) -> Optional[Discount]:
        best_amount = D("0")
        winner: Optional[Discount] = None
        for s in competitors:
            amount = s.preview_amount(ctx)
            if amount <= 0:
                continue
            prefers = bool(getattr(s, "prefers_on_tie", False))
            if winner is None or amount > best_amount or (
                amount == best_amount and prefers
            ):
                best_amount = amount
                winner = s
        return winner

def demo() -> None:
    from datetime import timedelta

    books = Product("p1", "Книга", D("500"), "Книги")
    pens = Product("p2", "Ручка", D("100"), "Канцелярия")

    order = Order(
        id="o1",
        customer=Customer("c1", date.today() - timedelta(days=12), False),
        items=[CartItem(books, 3), CartItem(pens, 2)],
        promoCode=None,
        createdAt=date.today(),
        deliveryCost=D("300"),
    )
    DiscountRegistry().load(
        [
            {"type": "threeForTwo", "name": "3 по цене 2", "category": "Книги"},
            {"type": "loyalty", "name": "Лояльность", "percent": 5, "days": 30},
            {"type": "freeDelivery", "name": "Доставка 0", "threshold": 1000},
        ]
    )

    result = PricingEngine().calculate(order, DiscountRegistry().build())

    print("baseTotal =", result.baseTotal)
    for d in result.appliedDiscounts:
        print(f"  - {d.name}: {d.amount}  ({d.reason})")
    print("finalTotal =", result.finalTotal)

if __name__ == "__main__":
    demo()