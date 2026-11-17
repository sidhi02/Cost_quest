import re


def extract(text):
    value = str(text or "").lower().replace(",", "")
    attrs = {}
    patterns = {
        "capacity_l": r"\b(\d+(?:\.\d+)?)\s*(?:litre|liter|litres|liters|l)\b",
        "capacity_kg": r"\b(\d+(?:\.\d+)?)\s*kg\b",
        "tonnage": r"\b(0\.8|1|1\.2|1\.5|1\.8|2|2\.5)\s*ton(?:ne)?s?\b",
        "star_rating": r"\b(\d)\s*star\b",
        "power_w": r"\b(\d{2,5})\s*w(?:att)?\b",
        "place_settings": r"\b(\d{1,2})\s*place(?:\s+settings?)?\b",
        "dimension_cm": r"\b(\d{2,3})\s*cm\b",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, value)
        if match:
            attrs[key] = float(match.group(1)) if key in {"capacity_l", "capacity_kg", "tonnage"} else int(match.group(1))
    for load in ("front load", "top load", "semi automatic", "fully automatic"):
        if load in value: attrs["load_type"] = load; break
    if "non inverter" in value or "non-inverter" in value: attrs["inverter"] = False
    elif "inverter" in value: attrs["inverter"] = True
    for key, terms in {
        "appliance_type": ("side by side refrigerator", "double door refrigerator", "single door refrigerator", "convection microwave", "grill microwave", "solo microwave", "robot vacuum", "cordless vacuum", "upright vacuum", "canister vacuum", "air fryer", "mixer grinder", "induction cooktop", "electric kettle", "food processor", "coffee maker", "juicer", "reverse osmosis", "ro water purifier"),
    }.items():
        for term in terms:
            if term in value: attrs[key] = term; break
    for feature in ("frost free", "no frost", "convection", "inverter", "wifi", "wi-fi"):
        if feature in value:
            attrs["feature"] = "frost_free" if feature == "no frost" else feature.replace("-", "")
            if feature in {"inverter", "wifi", "wi-fi"}: attrs.pop("feature", None)
            else: break
    return attrs
