import json
import re
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "frontend/js/mocks/data"
SUCCESS_TOLERANCE = 0.10
DAY_FILES = ("day-summary", "day-summary-empty", "day-summary-over-target")
NUTRIENTS = ("kcal", "protein", "fat", "carbs")
MEALS = {"breakfast", "lunch", "dinner", "snack"}


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def rounded(value, places="1"):
    return float(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


@pytest.mark.parametrize("name", DAY_FILES)
def test_day_totals_remaining_and_success_match_entries(name):
    summary = load(name)
    assert set(summary) == {
        "date", "entries", "totals", "norm", "remaining", "is_success"
    }
    assert summary["norm"] == load("profile")["norm"]
    for key in NUTRIENTS:
        total = sum(item[key] for item in summary["entries"])
        assert summary["totals"][key] == pytest.approx(total)
        assert summary["remaining"][key] == pytest.approx(
            summary["norm"][key] - total
        )
    expected = bool(summary["entries"]) and abs(
        summary["totals"]["kcal"] - summary["norm"]["kcal"]
    ) <= summary["norm"]["kcal"] * SUCCESS_TOLERANCE
    assert summary["is_success"] is expected


@pytest.mark.parametrize("name", DAY_FILES)
def test_portions_match_product_snapshots_and_rounding(name):
    products = {item["id"]: item for item in load("products")}
    summary = load(name)
    entries = summary["entries"]
    assert len({item["id"] for item in entries}) == len(entries)
    for item in entries:
        assert re.fullmatch(r"[a-f0-9]{24}", item["id"])
        assert item["date"] == summary["date"]
        assert item["meal"] in MEALS
        assert 1 <= item["grams"] <= 5000
        product = products[item["product_id"]]
        assert product["name"] == item["product_name"]
        for key in NUTRIENTS:
            portion = Decimal(str(product[key])) * Decimal(str(item["grams"]))
            assert item[key] == rounded(portion / 100, "0.1")


def test_profile_uses_architecture_fields_and_calculated_integer_norm():
    profile = load("profile")
    today = date.fromisoformat(load("day-summary")["date"])
    birth = date.fromisoformat(profile["birth_date"])
    age = today.year - birth.year - (
        (today.month, today.day) < (birth.month, birth.day)
    )
    assert age == 25
    assert profile["sex"] == "male"
    assert profile["activity"] == 1.55
    assert profile["goal"] == "lose"
    bmr = (
        Decimal("10") * Decimal(str(profile["weight_kg"]))
        + Decimal("6.25") * Decimal(str(profile["height_cm"]))
        - Decimal("5") * age + 5
    )
    target = bmr * Decimal(str(profile["activity"])) * Decimal("0.85")
    norm = profile["norm"]
    assert norm == {"kcal": 2437, "protein": 183, "fat": 81, "carbs": 244}
    assert norm["kcal"] == rounded(target)
    for key, ratio, divisor in (
        ("protein", "0.30", 4), ("fat", "0.30", 9), ("carbs", "0.40", 4)
    ):
        assert norm[key] == rounded(target * Decimal(ratio) / divisor)
    assert all(type(value) is int for value in norm.values())
    assert not {"gender", "age", "daily_calories", "macros"} & profile.keys()


@pytest.mark.parametrize("name", ("stats-calories", "stats-calories-empty"))
def test_graph_has_seven_ordered_days_and_ten_percent_tolerance(name):
    stats = load(name)
    assert set(stats) == {"norm_kcal", "days"}
    assert stats["norm_kcal"] == load("profile")["norm"]["kcal"]
    dates = [date.fromisoformat(item["date"]) for item in stats["days"]]
    assert len(dates) == 7
    assert dates == [dates[0] + timedelta(days=i) for i in range(7)]
    for day in stats["days"]:
        expected = day["kcal"] > 0 and abs(
            day["kcal"] - stats["norm_kcal"]
        ) <= stats["norm_kcal"] * SUCCESS_TOLERANCE
        assert day["is_success"] is expected


def test_token_profile_weight_streak_and_stats_are_consistent():
    login = load("auth-login")
    register = load("auth-register")
    profile = load("profile")
    summary = load("day-summary")
    stats = load("stats-calories")
    assert set(login) == {"token"} and login["token"]
    assert register == {"token": login["token"], "profile": profile}
    assert stats["days"][-1] == {
        "date": summary["date"], "kcal": summary["totals"]["kcal"],
        "is_success": summary["is_success"],
    }
    current = 0
    for day in reversed(stats["days"]):
        if not day["is_success"]:
            break
        current += 1
    streak = load("streak")
    assert streak["current"] == current == 4
    assert streak["record"] >= current
    history = load("weight-history")
    assert history[-1] == load("weight-log-saved")
    assert history[-1]["weight_kg"] == profile["weight_kg"]
    dates = [date.fromisoformat(item["date"]) for item in history]
    assert dates == sorted(set(dates))
    for item in history:
        assert 30 <= item["weight_kg"] <= 300
        assert re.fullmatch(r"[a-f0-9]{24}", item["id"])


def test_created_and_updated_entries_and_custom_product_use_public_models():
    created = load("food-entry-created")
    assert created in load("day-summary")["entries"]
    updated = load("food-entry-updated")
    assert created["id"] == updated["id"]
    assert updated["grams"] == 300
    product = next(
        item for item in load("products")
        if item["id"] == updated["product_id"]
    )
    for key in NUTRIENTS:
        value = Decimal(str(product[key])) * Decimal(str(updated["grams"]))
        assert updated[key] == rounded(value / 100, "0.1")
    custom = load("product-created")
    assert custom in load("products")
    assert custom["owner_id"] == load("profile")["id"]
    assert any(item["owner_id"] is None for item in load("products"))


def test_empty_and_over_target_examples_cover_ui_edge_cases():
    empty = load("day-summary-empty")
    assert empty["entries"] == []
    assert empty["totals"] == dict.fromkeys(NUTRIENTS, 0)
    assert empty["remaining"] == empty["norm"]
    assert not empty["is_success"]
    over = load("day-summary-over-target")
    assert over["remaining"]["kcal"] < 0
    assert not over["is_success"]
    assert load("products-empty") == load("weight-history-empty") == []
    assert load("streak-empty") == {"current": 0, "record": 0}


@pytest.mark.parametrize("path", sorted(DATA.glob("*.json")))
def test_responses_do_not_expose_passwords_or_obsolete_field_names(path):
    obsolete = {
        "calories", "total_calories", "target_calories", "eaten_calories",
        "remaining_calories", "is_custom", "password", "password_hash"
    }

    def check(value):
        if isinstance(value, dict):
            assert not obsolete & value.keys()
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", sorted(DATA.glob("error-*.json")))
def test_error_examples_follow_the_shared_error_envelope(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"error"}
    error = data["error"]
    assert isinstance(error["code"], str) and error["code"]
    assert isinstance(error["message"], str) and error["message"]
    if "field" in error:
        assert isinstance(error["field"], str) and error["field"]
