import re


def extract(text):
    value = str(text or "").lower()
    attrs = {}
    match = re.search(r"\b(?:uk|us|india|indian)\s*(?:size\s*)?(\d+(?:\.\d+)?)\b", value)
    if match:
        attrs["size"] = float(match.group(1))
        attrs["size_scale"] = "uk" if "uk" in match.group(0) else "us" if "us" in match.group(0) else "india"
    else:
        match = re.search(r"\bsize\s*(xs|s|m|l|xl|xxl|xxxl|\d+)\b", value)
        if match: attrs["size"] = match.group(1).upper()
    for gender in ("men", "women", "boys", "girls", "unisex", "mens", "womens"):
        if re.search(rf"\b{gender}\b", value): attrs["gender"] = gender.rstrip("s"); break
    for material in ("cotton", "linen", "leather", "synthetic", "polyester", "wool", "silk", "denim", "canvas", "suede"):
        if re.search(rf"\b{material}\b", value): attrs["material"] = material; break
    for colour in ("black", "white", "blue", "navy", "red", "green", "pink", "brown", "beige", "grey", "gray", "yellow"):
        if re.search(rf"\b{colour}\b", value): attrs["colour"] = colour; break
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(ml|l|g|kg)\b", value)
    if match: attrs["quantity"] = f"{match.group(1)}{match.group(2)}"
    match = re.search(r"\b(\d{2,3})\s*(?:cm|centimetres?|centimeters?)\b", value)
    if match: attrs["size_cm"] = int(match.group(1))
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:litre|liter|litres|liters)\b", value)
    if match: attrs["capacity_l"] = float(match.group(1))
    for kind, terms in {
        "bag_type": ("suitcase", "trolley bag", "cabin bag", "backpack", "handbag", "duffel", "duffle", "wallet", "purse"),
        "watch_type": ("analog", "analogue", "digital", "smartwatch", "smart watch"),
        "eyewear_type": ("sunglasses", "eyeglasses", "spectacles", "optical frame"),
    }.items():
        for term in terms:
            if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", value):
                attrs[kind] = "analog" if term == "analogue" else "smart" if term in {"smartwatch", "smart watch"} else "eyeglasses" if term in {"eyeglasses", "spectacles", "optical frame"} else term
                break
    for lens in ("polarized", "photochromic", "blue light", "uv400"):
        if lens in value: attrs["lens_type"] = lens; break
    match = re.search(r"\b(?:ring\s*)?size\s*(\d+(?:\.\d+)?)\b", value)
    if match and re.search(r"\b(ring|jewellery|jewelry)\b", value): attrs["ring_size"] = float(match.group(1))
    return attrs
