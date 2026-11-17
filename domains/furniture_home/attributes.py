import re


def extract(text):
    value = str(text or "").lower()
    attrs = {}
    match = re.search(r"\b(single|twin|double|full|queen|king|super king)\s*(?:size)?\b", value)
    if match: attrs["size"] = match.group(1)
    dimensions = re.search(r"(\d{2,3})\s*[x×*]\s*(\d{2,3})(?:\s*[x×*]\s*(\d{2,3}))?\s*(cm|mm|inch|inches)?", value)
    if dimensions:
        unit = dimensions.group(4) or "cm"
        factor = 2.54 if unit.startswith("inch") else 0.1 if unit == "mm" else 1
        attrs["dimensions_cm"] = [round(float(dimensions.group(i)) * factor, 1) for i in (1, 2, 3) if dimensions.group(i)]
    for material in ("solid wood", "engineered wood", "plywood", "sheesham", "teak", "metal", "fabric", "leather", "mango wood", "mdf"):
        if material in value: attrs["material"] = material; break
    match = re.search(r"\b(\d+)\s*seater\b", value)
    if match: attrs["seats"] = int(match.group(1))
    match = re.search(r"\b(\d+)\s*door\b", value)
    if match: attrs["door_count"] = int(match.group(1))
    for kind, terms in {
        "furniture_type": ("office chair", "study chair", "study table", "computer desk", "standing desk", "sofa", "couch", "recliner", "dining table", "dining chair", "wardrobe", "cabinet", "bookshelf", "ceiling light", "table lamp", "floor lamp", "pendant light", "chandelier", "wall light", "bedsheet", "bed sheet", "curtain", "rug", "carpet"),
    }.items():
        for term in terms:
            if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", value): attrs[kind] = term; break
    for subtype in ("ergonomic", "reclining", "orthopedic", "memory foam", "latex", "coir", "led", "solar"):
        if subtype in value: attrs["subtype"] = subtype; break
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*w\b", value)
    if match: attrs["power_w"] = float(match.group(1))
    return attrs
