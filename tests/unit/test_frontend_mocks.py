import json
import re
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "frontend/js/mocks/data"
DAY_FILES = (
    "day-summary",
    "day-summary-empty",
    "day-summary-over-target",
)
MEALS = {"breakfast", "lunch", "dinner", "snack"}
NUTRIENTS = ("calories", "protein", "fat", "carbs")


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def entries(summary):
    return [entry for meal in summary["meals"].values() for entry in meal]


@pytest.mark.parametrize("name", DAY_FILES)
def test_day_summary_matches_entries_and_success_rule(name):
    summary = load(name)
    profile = load("profile")
    assert set(summary["meals"]) == MEALS
    total = sum(entry["calories"] for entry in entries(summary))
    assert summary["eaten_calories"] == pytest.approx(total)
    assert summary["target_calories"] == profile["daily_calories"]
    assert summary["remaining_calories"] == pytest.approx(
        profile["daily_calories"] - total
    )
    expected_success = abs(total - profile["daily_calories"]) <= (
        profile["daily_calories"] * 0.05
    )
    assert summary["is_success"] is expected_success
    assert summary["streak"]["record"] >= summary["streak"]["current"]
    if not expected_success:
        assert summary["streak"]["current"] == 0


@pytest.mark.parametrize("name", DAY_FILES)
def test_portions_use_product_nutrients_per_100_grams(name):
    products = {item["name"]: item for item in load("products")}
    ids = []
    for entry in entries(load(name)):
        ids.append(entry["entry_id"])
        assert re.fullmatch(r"[a-f0-9]{24}", entry["entry_id"])
        product = products[entry["product_name"]]
        for key in NUTRIENTS:
            value = Decimal(str(product[key])) * Decimal(str(entry["grams"]))
            expected = (value / 100).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
            assert entry[key] == float(expected)
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("name", ("analytics-weekly", "analytics-empty"))
def test_weekly_graph_has_seven_ordered_days_and_correct_flags(name):
    data = load(name)
    target = load("profile")["daily_calories"]
    days = data["calories_weekly"]
    dates = [date.fromisoformat(item["date"]) for item in days]
    assert len(days) == 7
    assert dates == [dates[0] + timedelta(days=i) for i in range(7)]
    for item in days:
        assert item["is_success"] is (
            abs(item["total_calories"] - target) <= target * 0.05
        )
    weights = data["weight_dynamics"]
    weight_dates = [date.fromisoformat(item["date"]) for item in weights]
    assert weight_dates == sorted(set(weight_dates))
    assert set(weight_dates) <= set(dates)
    assert all(item["weight_kg"] > 0 for item in weights)


def test_auth_profile_summary_and_charts_share_one_demo_user():
    login = load("auth-login")
    register = load("auth-register")
    profile = load("profile")
    summary = load("day-summary")
    weekly = load("analytics-weekly")
    assert login["user_id"] == register["user_id"]
    assert re.fullmatch(r"[a-f0-9]{24}", login["user_id"])
    assert login["name"] == profile["name"]
    assert register["daily_calories"] == summary["target_calories"]
    assert weekly["calories_weekly"][-1] == {
        "date": summary["date"],
        "total_calories": summary["eaten_calories"],
        "is_success": summary["is_success"],
    }
    assert weekly["weight_dynamics"][-1]["weight_kg"] == profile["weight_kg"]
    current_streak = 0
    for day in reversed(weekly["calories_weekly"]):
        if not day["is_success"]:
            break
        current_streak += 1
    assert current_streak == summary["streak"]["current"]


def test_created_entry_and_custom_product_exist_in_sample_data():
    created_entry = load("food-entry-created")
    matching = [
        entry for entry in entries(load("day-summary"))
        if entry["entry_id"] == created_entry["entry_id"]
    ]
    assert len(matching) == 1
    assert matching[0]["calories"] == created_entry["calculated_calories"]
    custom_id = load("product-created")["product_id"]
    assert any(
        product["product_id"] == custom_id and product["is_custom"]
        for product in load("products")
    )


def test_empty_and_over_target_examples_cover_ui_edge_cases():
    empty = load("day-summary-empty")
    over_target = load("day-summary-over-target")
    assert entries(empty) == []
    assert empty["eaten_calories"] == 0
    assert over_target["remaining_calories"] < 0
    assert load("products-empty") == []
    assert load("analytics-empty")["weight_dynamics"] == []
    assert all(
        item["total_calories"] == 0
        for item in load("analytics-empty")["calories_weekly"]
    )


@pytest.mark.parametrize("path", sorted(DATA.glob("error-*.json")))
def test_error_examples_follow_openapi_error_envelope(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"error"}
    error = data["error"]
    assert isinstance(error["code"], str) and error["code"]
    assert isinstance(error["message"], str) and error["message"]
    if "field" in error:
        assert isinstance(error["field"], str) and error["field"]
