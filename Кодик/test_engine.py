import unittest
from datetime import date, timedelta
from decimal import Decimal

from engine import (
    Product,
    CartItem,
    Customer,
    Order,
    DiscountRegistry,
    PricingEngine,
    DiscountFactory,
)

D = Decimal

def P(price, cat="Книги"):
    return Product("x", "n", D(str(price)), cat)

def make_order(items, delivery="0", promo=None, first=False, last=None):
    d = None if last is None else date.today() - timedelta(days=last)
    return Order(
        "o",
        Customer("c", d, first),
        items,
        promo,
        date.today(),
        D(delivery),
    )

def run(order, cfg):
    DiscountRegistry().load(cfg)
    return PricingEngine().calculate(order, DiscountRegistry().build())

class TestThreeForTwo(unittest.TestCase):
    def test_applies(self):
        r = run(
            make_order([CartItem(P(500), 3)]),
            [{"type": "threeForTwo", "name": "3x2", "category": "Книги"}],
        )
        self.assertEqual(r.finalTotal, D("1000.00"))
        self.assertEqual(r.appliedDiscounts[0].amount, D("500.00"))
        self.assertEqual(r.appliedDiscounts[0].name, "3x2")

    def test_not_applied(self):
        r = run(
            make_order([CartItem(P(500), 2)]),
            [{"type": "threeForTwo", "name": "3x2", "category": "Книги"}],
        )
        self.assertEqual(r.appliedDiscounts, [])
        self.assertEqual(r.finalTotal, D("1000.00"))

    def test_cheapest_are_free(self):
        items = [CartItem(P(100), 1), CartItem(P(200), 1), CartItem(P(300), 1)]
        r = run(
            make_order(items),
            [{"type": "threeForTwo", "name": "3x2", "category": "Книги"}],
        )
        self.assertEqual(r.appliedDiscounts[0].amount, D("100.00"))

    def test_other_category_not_touched(self):
        r = run(
            make_order(
                [
                    CartItem(P(500, "Книги"), 3),
                    CartItem(P(999, "Игрушки"), 3),
                ]
            ),
            [{"type": "threeForTwo", "name": "3x2", "category": "Книги"}],
        )
        self.assertEqual(r.appliedDiscounts[0].amount, D("500.00"))
        self.assertEqual(r.finalTotal, D("1000.00") + D("2997.00"))

class TestPercent(unittest.TestCase):
    def test_applies(self):
        r = run(
            make_order([CartItem(P(1000), 1)]),
            [{"type": "percent", "name": "p", "value": 10}],
        )
        self.assertEqual(r.finalTotal, D("900.00"))

    def test_zero_items(self):
        r = run(
            make_order([]),
            [{"type": "percent", "name": "p", "value": 10}],
        )
        self.assertEqual(r.appliedDiscounts, [])

class TestFixed(unittest.TestCase):
    def test_threshold(self):
        r = run(
            make_order([CartItem(P(3000), 1)]),
            [{"type": "fixed", "name": "f", "value": 500, "threshold": 3000}],
        )
        self.assertEqual(r.finalTotal, D("2500.00"))

    def test_below_threshold(self):
        r = run(
            make_order([CartItem(P(2999), 1)]),
            [{"type": "fixed", "name": "f", "value": 500, "threshold": 3000}],
        )
        self.assertEqual(r.appliedDiscounts, [])

    def test_cannot_go_below_zero(self):
        r = run(
            make_order([CartItem(P(100), 1)]),
            [{"type": "fixed", "name": "f", "value": 500}],
        )
        self.assertEqual(r.finalTotal, D("0.00"))
        self.assertEqual(r.appliedDiscounts[0].amount, D("100.00"))

class TestLoyalty(unittest.TestCase):
    def test_border_30_inclusive(self):
        r = run(
            make_order([CartItem(P(1000), 1)], last=30),
            [{"type": "loyalty", "name": "l", "percent": 5, "days": 30}],
        )
        self.assertEqual(r.finalTotal, D("950.00"))

    def test_31_days_no_discount(self):
        r = run(
            make_order([CartItem(P(1000), 1)], last=31),
            [{"type": "loyalty", "name": "l", "percent": 5, "days": 30}],
        )
        self.assertEqual(r.appliedDiscounts, [])

    def test_future_date_no_discount(self):
        r = run(
            make_order([CartItem(P(1000), 1)], last=-5),
            [{"type": "loyalty", "name": "l"}],
        )
        self.assertEqual(r.appliedDiscounts, [])

    def test_no_date_no_discount(self):
        r = run(
            make_order([CartItem(P(1000), 1)], last=None),
            [{"type": "loyalty", "name": "l"}],
        )
        self.assertEqual(r.appliedDiscounts, [])

class TestFirstOrder(unittest.TestCase):
    def test_applies(self):
        r = run(
            make_order([CartItem(P(1000), 1)], first=True),
            [{"type": "firstOrder", "name": "fo"}],
        )
        self.assertEqual(r.finalTotal, D("900.00"))

    def test_not_first(self):
        r = run(
            make_order([CartItem(P(1000), 1)], first=False),
            [{"type": "firstOrder", "name": "fo"}],
        )
        self.assertEqual(r.appliedDiscounts, [])

class TestFreeDelivery(unittest.TestCase):
    def test_strict_boundary(self):
        r = run(
            make_order([CartItem(P(5000), 1)], delivery="300"),
            [{"type": "freeDelivery", "name": "fd", "threshold": 5000}],
        )
        self.assertEqual(r.appliedDiscounts, [])

    def test_applies(self):
        r = run(
            make_order([CartItem(P(5001), 1)], delivery="300"),
            [{"type": "freeDelivery", "name": "fd", "threshold": 5000}],
        )
        self.assertEqual(r.appliedDiscounts[0].amount, D("300.00"))
        self.assertEqual(r.finalTotal, D("5001.00"))

class TestPromoPercent(unittest.TestCase):
    def test_unknown(self):
        r = run(
            make_order([CartItem(P(1000), 1)], promo="X"),
            [{"type": "promo", "name": "s", "value": 10, "code": "SALE"}],
        )
        self.assertEqual(r.appliedDiscounts, [])

    def test_expired(self):
        r = run(
            make_order([CartItem(P(1000), 1)], promo="SALE"),
            [
                {
                    "type": "promo",
                    "name": "s",
                    "value": 10,
                    "code": "SALE",
                    "expires": date.today() - timedelta(days=1),
                }
            ],
        )
        self.assertEqual(r.appliedDiscounts, [])

    def test_last_day_inclusive(self):
        r = run(
            make_order([CartItem(P(1000), 1)], promo="SALE"),
            [
                {
                    "type": "promo",
                    "name": "s",
                    "value": 10,
                    "code": "SALE",
                    "expires": date.today(),
                }
            ],
        )
        self.assertEqual(r.finalTotal, D("900.00"))

    def test_inactive(self):
        r = run(
            make_order([CartItem(P(1000), 1)], promo="SALE"),
            [
                {
                    "type": "promo",
                    "name": "s",
                    "value": 10,
                    "code": "SALE",
                    "active": False,
                }
            ],
        )
        self.assertEqual(r.appliedDiscounts, [])

    def test_case_insensitive(self):
        r = run(
            make_order([CartItem(P(1000), 1)], promo="sale"),
            [{"type": "promo", "name": "s", "value": 10, "code": "SALE"}],
        )
        self.assertEqual(r.finalTotal, D("900.00"))

    def test_no_code_in_order(self):
        r = run(
            make_order([CartItem(P(1000), 1)], promo=None),
            [{"type": "promo", "name": "s", "value": 10, "code": "SALE"}],
        )
        self.assertEqual(r.appliedDiscounts, [])

class TestPromoFixed(unittest.TestCase):
    def test_fixed_promo_applies(self):
        r = run(
            make_order([CartItem(P(2000), 1)], promo="FIX"),
            [
                {
                    "type": "promo",
                    "name": "fix",
                    "value": 300,
                    "code": "FIX",
                    "kind": "fixed",
                }
            ],
        )
        self.assertEqual(r.finalTotal, D("1700.00"))
        self.assertEqual(r.appliedDiscounts[0].name, "fix")

    def test_fixed_promo_no_conflict_with_percent(self):
        r = run(
            make_order([CartItem(P(2000), 1)], promo="FIX"),
            [
                {"type": "percent", "name": "p10", "value": 10},
                {
                    "type": "promo",
                    "name": "fix",
                    "value": 100,
                    "code": "FIX",
                    "kind": "fixed",
                },
            ],
        )
        names = [d.name for d in r.appliedDiscounts]
        self.assertIn("p10", names)
        self.assertIn("fix", names)
        self.assertEqual(r.finalTotal, D("1700.00"))

class TestPercentVsPromo(unittest.TestCase):
    def test_promo_bigger_wins(self):
        r = run(
            make_order([CartItem(P(1000), 1)], promo="BIG"),
            [
                {"type": "percent", "name": "p5", "value": 5},
                {
                    "type": "promo",
                    "name": "big",
                    "value": 20,
                    "code": "BIG",
                    "kind": "percent",
                },
            ],
        )
        self.assertEqual(r.appliedDiscounts[0].name, "big")
        self.assertEqual(r.finalTotal, D("800.00"))

    def test_percent_wins(self):
        r = run(
            make_order([CartItem(P(1000), 1)], promo="SMALL"),
            [
                {"type": "percent", "name": "p20", "value": 20},
                {
                    "type": "promo",
                    "name": "small",
                    "value": 5,
                    "code": "SMALL",
                    "kind": "percent",
                },
            ],
        )
        self.assertEqual(r.appliedDiscounts[0].name, "p20")
        self.assertEqual(r.finalTotal, D("800.00"))

    def test_equal_promo_wins(self):
        r = run(
            make_order([CartItem(P(1000), 1)], promo="EQ"),
            [
                {"type": "percent", "name": "p10", "value": 10},
                {
                    "type": "promo",
                    "name": "eq",
                    "value": 10,
                    "code": "EQ",
                    "kind": "percent",
                },
            ],
        )
        self.assertEqual(r.appliedDiscounts[0].name, "eq")
        self.assertEqual(r.finalTotal, D("900.00"))

class TestCombinations(unittest.TestCase):
    def test_three_then_percent(self):
        r = run(
            make_order([CartItem(P(500), 3)]),
            [
                {"type": "threeForTwo", "name": "3x2", "category": "Книги"},
                {"type": "percent", "name": "p10", "value": 10},
            ],
        )
        self.assertEqual([d.name for d in r.appliedDiscounts], ["3x2", "p10"])
        self.assertEqual(r.finalTotal, D("900.00"))

    def test_breakdown_full_chain(self):
        r = run(
            make_order([CartItem(P(500), 3)], delivery="300", last=10),
            [
                {"type": "threeForTwo", "name": "3x2", "category": "Книги"},
                {"type": "loyalty", "name": "l"},
                {"type": "freeDelivery", "name": "fd", "threshold": 900},
            ],
        )
        self.assertEqual([d.name for d in r.appliedDiscounts], ["3x2", "l", "fd"])
        self.assertEqual(r.baseTotal, D("1800.00"))
        self.assertEqual(r.finalTotal, D("950.00"))

    def test_loyalty_and_first_order_stack(self):
        r = run(
            make_order([CartItem(P(1000), 1)], last=10, first=True),
            [
                {"type": "loyalty", "name": "l"},
                {"type": "firstOrder", "name": "fo"},
            ],
        )
        self.assertEqual(r.finalTotal, D("855.00"))

    def test_loyalty_stacks_with_percent_winner(self):
        r = run(
            make_order([CartItem(P(1000), 1)], last=10, promo="P15"),
            [
                {"type": "percent", "name": "p5", "value": 5},
                {
                    "type": "promo",
                    "name": "p15",
                    "value": 15,
                    "code": "P15",
                    "kind": "percent",
                },
                {"type": "loyalty", "name": "l"},
            ],
        )
        self.assertEqual(r.appliedDiscounts[0].name, "p15")
        self.assertEqual(r.appliedDiscounts[1].name, "l")
        self.assertEqual(r.finalTotal, D("807.50"))


class TestRounding(unittest.TestCase):
    def test_half_even(self):
        r = run(
            make_order([CartItem(P("10.25"), 1)]),
            [{"type": "percent", "name": "p", "value": D("1.2195121951")}],
        )
        self.assertEqual(r.appliedDiscounts[0].amount, D("0.12"))

class TestEdgeCases(unittest.TestCase):
    def test_empty_cart(self):
        r = run(
            make_order([]),
            [
                {"type": "percent", "name": "p", "value": 10},
                {"type": "fixed", "name": "f", "value": 500},
            ],
        )
        self.assertEqual(r.finalTotal, D("0.00"))
        self.assertEqual(r.appliedDiscounts, [])

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            run(
                make_order([CartItem(P(100), 1)]),
                [{"type": "nonsense", "name": "x"}],
            )

    def test_quantity_must_be_positive(self):
        with self.assertRaises(ValueError):
            CartItem(P(100), 0)
        with self.assertRaises(ValueError):
            CartItem(P(100), -1)

    def test_negative_price_raises(self):
        with self.assertRaises(ValueError):
            Product("1", "x", D("-1"), "c")

    def test_delivery_in_base_total(self):
        r = run(
            make_order([CartItem(P(1000), 1)], delivery="300"),
            [{"type": "percent", "name": "p", "value": 10}],
        )
        self.assertEqual(r.baseTotal, D("1300.00"))
        self.assertEqual(r.finalTotal, D("1200.00"))

    def test_factory_missing_type(self):
        with self.assertRaises(ValueError):
            DiscountFactory.create({"name": "x"})

if __name__ == "__main__":
    unittest.main(verbosity=2)
