import re


def extract(text):
    value = str(text or "").lower()
    attrs = {}
    # Package quantity and racket weight are variant-defining attributes.
    pack = re.search(r"\bpack\s+of\s+(\d+)\b", value)
    if pack: attrs["pack_quantity"] = int(pack.group(1))
    grams = re.search(r"\b(\d{2,4}(?:\.\d+)?)\s*g\b", value)
    if grams: attrs["weight_g"] = float(grams.group(1))
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*kg\b", value)
    if match: attrs["weight_kg"] = float(match.group(1))
    match = re.search(r"\b(uk|us|india)\s*(?:size\s*)?(\d+(?:\.\d+)?)\b", value)
    if match: attrs["size"] = float(match.group(2)); attrs["size_scale"] = match.group(1)
    else:
        match = re.search(r"\bsize\s*(\d+)\b", value)
        if match: attrs["size"] = int(match.group(1))
    for material in ("carbon fiber", "aluminium", "aluminum", "steel", "wood", "leather", "rubber", "nylon"):
        if material in value: attrs["material"] = material; break
    for sport in ("cricket", "badminton", "football", "soccer", "basketball", "tennis", "cycling", "running", "yoga"):
        if sport in value: attrs["sport"] = sport; break
    match = re.search(r"\b(\d+)\s*(?:pcs|pieces|balls|shuttlecocks)\b", value)
    if match: attrs["pack_quantity"] = int(match.group(1))
    match = re.search(r"\b(\d+)\s*(?:speed|gears?)\b", value)
    if match: attrs["gear_count"] = int(match.group(1))
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*mm\b", value)
    if match: attrs["thickness_mm"] = float(match.group(1))
    match = re.search(r"\b(\d+)\s*oz\b", value)
    if match: attrs["weight_oz"] = int(match.group(1))
    for kind in ("mountain bike", "road bike", "hybrid bike", "city bike", "electric bicycle", "e-bike"):
        if kind in value: attrs["cycle_type"] = "e-bike" if kind == "electric bicycle" else kind; break
    match = re.search(r"\bsize\s*(\d+)\b", value)
    if match and re.search(r"\b(football|soccer ball|cricket ball|basketball)\b", value): attrs["equipment_size"] = int(match.group(1))
    return attrs
