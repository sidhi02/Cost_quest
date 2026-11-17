import re
import unicodedata

ALIASES = {
    "one plus": "oneplus", "tp link": "tplink", "tp-link": "tplink", "wi fi": "wifi", "bluetooth": "bluetooth",
    "wh 1000 xm5": "wh1000xm5", "wh-1000xm5": "wh1000xm5", "wh 1000xm5": "wh1000xm5",
    "galaxy s 26": "galaxy s26", "galaxy s 25": "galaxy s25", "iphone 16 pro max": "iphone16promax",
    "iphone 16 pro": "iphone16pro", "iphone 16 plus": "iphone16plus", "iphone 16e": "iphone16e",
    "macbook air m 4": "macbook air m4", "macbook pro m 4": "macbook pro m4",
}


def normalize_product_text(value):
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = text.replace("×", "x").replace("–", "-").replace("—", "-").replace("’", "'")
    text = re.sub(r"\b(wh|gb|tb|mb|kg|g|cm|mm|inch|inches|hz|mah|w)\b", r"\1", text)
    text = re.sub(r"[^a-z0-9.%+/-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for source, target in ALIASES.items():
        text = re.sub(rf"(?<![a-z0-9]){re.escape(source)}(?![a-z0-9])", target, text)
    return re.sub(r"\s+", " ", text).strip()


def extract_entities(value):
    """Lightweight product NER. Domain catalog extractors remain authoritative for variant checks."""
    text = normalize_product_text(value)
    entities = {}
    patterns = {
        "isbn": r"\b(?:isbn\s*)?(97[89][0-9-]{10,16}|[0-9][0-9-]{8,12}[0-9x])\b",
        "storage": r"\b(\d{2,4})\s*(gb|tb)\s*(?:storage|rom|ufs|ssd)?\b",
        "ram": r"\b(\d{1,3})\s*gb\s*ram\b",
        "wattage": r"\b(\d{1,4})\s*w(?:att)?\b",
        "screen_inches": r"\b(\d{1,2}(?:\.\d)?)\s*(?:inch|in)\b",
        "capacity": r"\b(\d{1,4}(?:\.\d)?)\s*(litre|liter|l|kg)\b",
        "shoe_size": r"\b(?:uk|us|eu)\s*(\d{1,2}(?:\.\d)?)\b",
        "edition": r"\b(\d{1,2})(?:st|nd|rd|th)\s*edition\b",
        "quantity": r"\b(?:pack\s*of|set\s*of|pack)\s*(\d{1,3})\b",
    }
    for key, pattern in patterns.items():
        found = re.search(pattern, text)
        if found:
            entities[key] = f"{found.group(1)}{found.group(2)}" if key in {"storage", "capacity"} else found.group(0).strip()
    models = re.findall(r"\b[a-z]{1,8}[-/]?\d{2,}[a-z0-9-]*\b", text)
    if models:
        entities["model_tokens"] = sorted(set(models))
    if "5g" in text:
        entities["connectivity"] = "5g"
    elif "wifi" in text or "wi-fi" in text:
        entities["connectivity"] = "wifi"
    if "cellular" in text:
        entities["connectivity"] = "cellular"
    if "inverter" in text:
        entities["inverter"] = "yes"
    elif "non inverter" in text:
        entities["inverter"] = "no"
    return entities
