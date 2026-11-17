from services.electronics_catalog import extract_specs, normalize_text
import re


def extract(text, category=None):
    value = normalize_text(text)
    resolved = "laptops" if category == "laptops" or "macbook" in value or "laptop" in value else category
    attrs = extract_specs(value, resolved)
    if re.search(r"\b(cellular|5g cellular|wi fi \+ cellular)\b", value): attrs["connectivity"] = "cellular"
    elif re.search(r"\b(wi fi|wifi)\b", value): attrs["connectivity"] = "wifi"
    if re.search(r"\b(disc edition|disc)\b", value): attrs["edition"] = "disc"
    elif re.search(r"\b(digital edition|digital)\b", value): attrs["edition"] = "digital"
    if re.search(r"\b(front load|top load)\b", value): attrs["load_type"] = "front load" if "front load" in value else "top load"
    match = re.search(r"\b(\d{3,5})\s*va\b", value)
    if match: attrs["capacity_va"] = int(match.group(1))
    for kind in ("wireless mouse", "mouse", "keyboard", "webcam", "trackball", "docking station", "usb hub", "kvm switch", "graphics tablet", "drawing tablet"):
        if re.search(rf"(?<![a-z0-9]){re.escape(kind)}(?![a-z0-9])", value): attrs["peripheral_type"] = kind; break
    for kind in ("electric shaver", "shaver", "trimmer", "hair dryer", "electric toothbrush"):
        if re.search(rf"(?<![a-z0-9]){re.escape(kind)}(?![a-z0-9])", value): attrs["personal_appliance_type"] = kind; break
    return attrs
