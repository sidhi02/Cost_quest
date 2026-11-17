import re


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip(" -")


def query_variants(query, domain, category=None):
    original = _clean(query)
    if not original:
        return []
    variants = [original]
    lower = original.lower()

    if domain == "electronics":
        if "pixel" in lower:
            variants.append(re.sub(r"\bgoogle\s+", "", original, flags=re.I))
            variants.append(re.sub(r"\b(256gb|128gb|512gb)\b", r"\1 smartphone", original, flags=re.I))
        if "monitor" in lower and re.search(r"\b[a-z]{1,4}\d{3,}[a-z0-9]*\b", lower):
            variants.append(re.sub(r"\b\d{2,3}[- ]inch\b", "", original, flags=re.I))
        if "oneplus" in lower:
            variants.append(re.sub(r"\s+5g\b", "", original, flags=re.I))
    elif domain == "fashion":
        variants.append(re.sub(r"\b(men'?s|women'?s|regular fit|slim fit)\b", "", original, flags=re.I))
    elif domain == "home_appliances":
        if re.search(r"\b(ac|air conditioner)\b", lower):
            variants.append(re.sub(r"\bsplit ac\b", "split air conditioner", original, flags=re.I))
            variants.append(re.sub(r"\b3 star\b", "", re.sub(r"\binverter\b", "", original, flags=re.I), flags=re.I))
        if "water purifier" in lower:
            variants.append(re.sub(r"\bwater purifier\b", "RO purifier", original, flags=re.I))
    elif domain == "books_stationery":
        variants.append(re.sub(r"\b(paperback|hardcover|spiral bound)\b", "", original, flags=re.I))
        if "morgan housel" in lower:
            variants.append("The Psychology of Money Morgan Housel")
        if "sp bakshi" in lower:
            variants.append("Arihant Objective General English SP Bakshi")
    elif domain == "sports_fitness":
        if "football" in lower:
            variants.append(re.sub(r"\b(size\s*)?5\b", "size 5", original, flags=re.I))
        if "exercise bike" in lower:
            variants.append(re.sub(r"\b500\b", "", original, flags=re.I))
    elif domain == "furniture_home":
        if "wardrobe" in lower:
            variants.append(re.sub(r"\bsteel\b", "", original, flags=re.I))
        if "office chair" in lower:
            variants.append(re.sub(r"\bhigh back\b", "", original, flags=re.I))

    result, seen = [], set()
    for variant in variants:
        variant = _clean(variant)
        key = variant.casefold()
        if variant and key not in seen:
            seen.add(key)
            result.append(variant)
    return result[:3]
