"""Conservative payable-price calculation; unknown charges are never assumed to be zero."""
from decimal import Decimal, InvalidOperation


def _amount(value):
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() and result >= 0 else None


def calculate_final_price(listed_price, shipping=None, coupon=None, bank_discount=None, *, eligibility_verified=False):
    price = _amount(listed_price)
    delivery = _amount(shipping)
    if price is None or price == 0:
        raise ValueError("A positive listed price is required")
    if shipping is not None and delivery is None:
        raise ValueError("Invalid shipping charge")
    discount = _amount(coupon) if eligibility_verified else None
    bank = _amount(bank_discount) if eligibility_verified else None
    if eligibility_verified and ((coupon is not None and discount is None) or (bank_discount is not None and bank is None)):
        raise ValueError("Invalid discount")
    known_total = price + (delivery or 0) - (discount or 0) - (bank or 0)
    known_total = max(Decimal('0'), known_total)
    return {
        "listed_price": float(price),
        "shipping": float(delivery) if delivery is not None else None,
        "coupon_applied": float(discount or 0),
        "bank_discount_applied": float(bank or 0),
        "estimated_total": float(known_total) if delivery is not None else None,
        "known_subtotal": float(known_total),
        "complete": delivery is not None,
        "disclaimer": "Estimate only; retailer checkout determines the final payable amount.",
    }
