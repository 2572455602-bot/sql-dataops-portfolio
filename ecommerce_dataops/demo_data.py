"""Deterministic six-table e-commerce fixtures for tests and demos."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from ecommerce_dataops.input_contract import EXPECTED_SCHEMAS


DEMO_SEED = 20260712
MONEY = Decimal("0.01")


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY, rounding=ROUND_HALF_UP))


def _timestamp(value: datetime | None) -> str:
    return "" if value is None else value.strftime("%Y-%m-%d %H:%M:%S")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    header = EXPECTED_SCHEMAS[path.name]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def generate_demo_dataset(
    directory: Path,
    users: int = 40,
    seed: int = DEMO_SEED,
) -> dict[str, int]:
    """Create a compact, deterministic fixture matching all six source files."""

    if users < 4:
        raise ValueError("users must be at least 4")
    del seed  # The fixture is formula-driven; retaining the argument keeps runs explicit.
    directory.mkdir(parents=True, exist_ok=True)
    product_count = max(8, users // 2)
    base = datetime(2026, 1, 1, 9, 0, 0)
    categories = ("手机数码", "家用电器", "服装鞋包", "美妆护肤", "食品饮料", "运动户外")
    brands = ("品牌A", "品牌B", "品牌C", "品牌D")
    statuses = ("已完成", "已收货", "已发货", "已付款", "已取消", "待付款", "已退款")
    payment_methods = ("支付宝", "微信支付", "银行卡", "信用卡", "花呗")

    user_rows: list[dict[str, object]] = []
    for index in range(1, users + 1):
        user_rows.append(
            {
                "user_id": f"U{index:06d}",
                "age": 20 + index % 41,
                "gender": "男" if index % 2 else "女",
                "province": ("广东", "浙江", "江苏", "湖北")[index % 4],
                "city": ("深圳", "杭州", "南京", "武汉")[index % 4],
                "registration_date": _timestamp(base - timedelta(days=60 + index * 3)),
                "member_level": ("普通会员", "铜牌会员", "银牌会员", "金牌会员", "钻石会员")[index % 5],
                "account_balance": _money(Decimal(100 + index * 17)),
                "credit_score": 600 + index % 201,
            }
        )

    behavior_rows: list[dict[str, object]] = []
    behavior_counter = 0
    for index in range(1, users + 1):
        user_id = f"U{index:06d}"
        product_id = f"P{((index - 1) % product_count) + 1:06d}"
        behaviors = ["浏览", "点击"]
        if index % 2 == 0:
            behaviors.append("收藏")
        if index % 3 == 0:
            behaviors.append("加购")
        for offset, behavior_type in enumerate(behaviors):
            behavior_counter += 1
            behavior_rows.append(
                {
                    "behavior_id": f"B{behavior_counter:08d}",
                    "user_id": user_id,
                    "product_id": product_id,
                    "behavior_type": behavior_type,
                    "behavior_time": _timestamp(base + timedelta(days=index % 28, minutes=offset * 20)),
                    "duration_seconds": 30 + ((index + offset) * 17) % 480,
                }
            )

    order_specs: list[tuple[int, int]] = [(index, 0) for index in range(1, users + 1)]
    order_specs.extend((index, 1) for index in range(4, users + 1, 4))
    order_specs.extend((index, 2) for index in range(10, users + 1, 10))
    order_rows: list[dict[str, object]] = []
    for order_index, (user_index, repeat_index) in enumerate(order_specs, start=1):
        product_index = ((user_index + repeat_index * 3 - 1) % product_count) + 1
        unit_price = Decimal("50.00") + Decimal(product_index) * Decimal("23.75")
        quantity = 1 + (order_index % 3)
        total_amount = (unit_price * quantity * Decimal("0.98")).quantize(MONEY)
        discount_rate = Decimal(order_index % 3) * Decimal("0.05")
        discount = (total_amount * discount_rate).quantize(MONEY)
        actual_payment = total_amount - discount
        status = statuses[(order_index - 1) % len(statuses)]
        order_date = base + timedelta(days=30 + order_index % 35, hours=order_index % 10)
        delivery_date = (
            order_date + timedelta(days=2)
            if status in {"已发货", "已收货", "已完成"}
            else None
        )
        receive_date = (
            order_date + timedelta(days=4)
            if status in {"已收货", "已完成"}
            else None
        )
        reviewed = status == "已完成" and order_index % 2 == 0
        order_rows.append(
            {
                "order_id": f"O{order_index:08d}",
                "user_id": f"U{user_index:06d}",
                "product_id": f"P{product_index:06d}",
                "quantity": quantity,
                "order_date": _timestamp(order_date),
                "order_status": status,
                "payment_method": payment_methods[order_index % len(payment_methods)],
                "unit_price": _money(unit_price),
                "total_amount": _money(total_amount),
                "discount": _money(discount),
                "actual_payment": _money(actual_payment),
                "delivery_date": _timestamp(delivery_date),
                "receive_date": _timestamp(receive_date),
                "review_score": 4 + order_index % 2 if reviewed else "",
                "review_content": "体验良好" if reviewed else "",
            }
        )

    order_count_by_product: dict[str, int] = defaultdict(int)
    for row in order_rows:
        order_count_by_product[str(row["product_id"])] += 1
    product_rows: list[dict[str, object]] = []
    for index in range(1, product_count + 1):
        product_id = f"P{index:06d}"
        price = Decimal("50.00") + Decimal(index) * Decimal("23.75")
        product_rows.append(
            {
                "product_id": product_id,
                "product_name": f"示例商品{index:03d}",
                "category": categories[(index - 1) % len(categories)],
                "brand": brands[(index - 1) % len(brands)],
                "price": _money(price),
                "sales_count": order_count_by_product[product_id],
            }
        )

    user_orders: dict[str, list[dict[str, object]]] = defaultdict(list)
    product_orders: dict[str, list[dict[str, object]]] = defaultdict(list)
    user_behaviors: dict[str, list[dict[str, object]]] = defaultdict(list)
    product_behaviors: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in order_rows:
        user_orders[str(row["user_id"])].append(row)
        product_orders[str(row["product_id"])].append(row)
    for row in behavior_rows:
        user_behaviors[str(row["user_id"])].append(row)
        product_behaviors[str(row["product_id"])].append(row)
    max_order_date = max(datetime.fromisoformat(str(row["order_date"])) for row in order_rows)

    user_feature_rows: list[dict[str, object]] = []
    for index in range(1, users + 1):
        user_id = f"U{index:06d}"
        orders = user_orders[user_id]
        behaviors = user_behaviors[user_id]
        spent = sum(Decimal(str(row["actual_payment"])) for row in orders)
        completed = sum(row["order_status"] == "已完成" for row in orders)
        last_order = max(datetime.fromisoformat(str(row["order_date"])) for row in orders)
        counts = {name: sum(row["behavior_type"] == name for row in behaviors) for name in ("浏览", "点击", "收藏", "加购")}
        user_feature_rows.append(
            {
                "user_id": user_id,
                "total_spent": _money(spent),
                "order_count": len(orders),
                "completed_orders": completed,
                "avg_order_amount": _money(spent / len(orders)),
                "browse_count": counts["浏览"],
                "click_count": counts["点击"],
                "favorite_count": counts["收藏"],
                "cart_count": counts["加购"],
                "days_since_last_order": (max_order_date - last_order).days,
                "order_frequency": completed,
                "repurchase_indicator": int(len(orders) >= 2),
                "purchase_intent": round((counts["收藏"] + counts["加购"]) / max(len(behaviors), 1), 4),
                "consumption_level": "高" if spent >= Decimal("1000") else "中",
                "member_level_score": 1 + index % 5,
            }
        )

    product_feature_rows: list[dict[str, object]] = []
    for index in range(1, product_count + 1):
        product_id = f"P{index:06d}"
        orders = product_orders[product_id]
        behaviors = product_behaviors[product_id]
        revenue = sum(Decimal(str(row["actual_payment"])) for row in orders)
        completed = sum(row["order_status"] == "已完成" for row in orders)
        cancelled = sum(row["order_status"] in {"已取消", "已退款"} for row in orders)
        scores = [int(row["review_score"]) for row in orders if row["review_score"] != ""]
        counts = {name: sum(row["behavior_type"] == name for row in behaviors) for name in ("浏览", "点击", "收藏", "加购")}
        product_feature_rows.append(
            {
                "product_id": product_id,
                "total_revenue": _money(revenue),
                "total_sales": len(orders),
                "completed_count": completed,
                "cancel_count": cancelled,
                "加购_count": counts["加购"],
                "收藏_count": counts["收藏"],
                "浏览_count": counts["浏览"],
                "点击_count": counts["点击"],
                "conversion_rate": round(completed / len(orders), 4) if orders else 0,
                "avg_review_score": round(sum(scores) / len(scores), 2) if scores else "",
                "popularity_score": round((len(orders) + len(behaviors)) / 100, 4),
            }
        )

    tables = {
        "users.csv": user_rows,
        "products.csv": product_rows,
        "orders.csv": order_rows,
        "user_behaviors.csv": behavior_rows,
        "user_features.csv": user_feature_rows,
        "product_features.csv": product_feature_rows,
    }
    for filename, rows in tables.items():
        _write_csv(directory / filename, rows)
    return {filename: len(rows) for filename, rows in tables.items()}
