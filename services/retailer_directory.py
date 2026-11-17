import re
from collections import Counter
from urllib.parse import urlparse


RETAILER_LABELS = {
    "croma": "Croma", "cromacom": "Croma", "reliancedigital": "Reliance Digital",
    "reliancedigitalin": "Reliance Digital", "amazon": "Amazon", "amazonin": "Amazon",
    "flipkart": "Flipkart", "flipkartcom": "Flipkart", "tatacliq": "Tata CLiQ",
    "tatacliqcom": "Tata CLiQ", "vijaysales": "Vijay Sales", "vijaysalescom": "Vijay Sales",
    "jiomart": "JioMart", "jiomartcom": "JioMart", "nykaa": "Nykaa", "nykaacom": "Nykaa",
}


def canonical_retailer_name(value):
    raw = str(value or "Unknown retailer").strip()
    host = urlparse(raw if "://" in raw else f"https://{raw}").hostname or raw
    compact = re.sub(r"[^a-z0-9]", "", host.lower().removeprefix("www."))
    return RETAILER_LABELS.get(compact, host.replace("www.", "").split(".")[0].replace("-", " ").title() if "." in host else raw)


def retailer_breakdown(products):
    counts = Counter(canonical_retailer_name(product.get("retailer")) for product in products)
    return [{"name": name, "count": count} for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))]
