REQUIRED_OFFER_FIELDS = ("name", "price", "url", "retailer", "currency", "availability")
OPTIONAL_OFFER_FIELDS = ("brand", "sku", "image", "source", "source_updated_at", "mrp", "discount_percent", "attributes")


def normalize_offer(offer):
    """Return a safe, predictable copy of a provider offer."""
    if not isinstance(offer, dict):
        return None
    result = dict(offer)
    result["name"] = str(result.get("name") or "").strip()
    result["brand"] = str(result.get("brand") or "").strip()
    result["retailer"] = str(result.get("retailer") or "").strip()
    result["availability"] = str(result.get("availability") or "Unknown").strip()
    result["currency"] = str(result.get("currency") or "INR").upper()
    result["attributes"] = result.get("attributes") if isinstance(result.get("attributes"), dict) else {}
    if not result["name"] or not result["retailer"] or result["currency"] != "INR":
        return None
    return result
