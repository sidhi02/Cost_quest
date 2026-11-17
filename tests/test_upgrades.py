from services.pricing import calculate_final_price
import pytest


def test_estimated_checkout_price():
    result = calculate_final_price(50000, 100, 1500, eligibility_verified=True)
    assert result["estimated_total"] == 48600
    assert result["complete"]


def test_unknown_shipping_not_falsely_exact():
    result = calculate_final_price(50000)
    assert result["estimated_total"] is None
    assert not result["complete"]


def test_unverified_discounts_not_applied():
    assert calculate_final_price(1000, 0, 300)["estimated_total"] == 1000


def test_invalid_price_rejected():
    with pytest.raises(ValueError):
        calculate_final_price(-1, 0)
