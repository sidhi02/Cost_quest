from urllib.parse import urlparse


def deduplicate_provider_offers(products):
    unique, seen, duplicates = [], set(), 0
    for product in products:
        if not isinstance(product, dict):
            unique.append(product)
            continue
        parsed = urlparse(str(product.get("url") or ""))
        sku = str(product.get("sku") or "").strip().casefold()
        key = (parsed.hostname or "", parsed.path.rstrip("/"), sku) if parsed.path and sku else (parsed.hostname or "", parsed.path.rstrip("/")) if parsed.path else (product.get("retailer"), sku or product.get("name"))
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
            unique.append(product)
    return unique, duplicates
