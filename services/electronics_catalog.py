import re
import unicodedata

ELECTRONICS_CATEGORIES = [
    {"slug": "phones", "name": "Mobiles & Phones", "icon": "📱", "terms": ["phone", "mobile", "smartphone", "iphone", "galaxy s", "galaxy a", "galaxy z", "redmi", "poco", "pixel", "oneplus", "realme", "oppo", "vivo", "iqoo", "motorola", "nothing phone"]},
    {"slug": "laptops", "name": "Laptops & Computers", "icon": "💻", "terms": ["laptop", "notebook computer", "notebook pc", "macbook", "thinkpad", "inspiron", "pavilion", "vivobook", "ideapad", "aspire", "zenbook", "desktop", "mini pc", "all in one pc"]},
    {"slug": "tablets", "name": "Tablets & E-readers", "icon": "▣", "terms": ["tablet", "ipad", "galaxy tab", "kindle", "e reader", "oneplus pad", "xiaomi pad"]},
    {"slug": "monitors", "name": "Monitors & Displays", "icon": "🖥️", "terms": ["monitor", "display", "ultrawide", "portable monitor"]},
    {"slug": "audio", "name": "Headphones & Audio", "icon": "🎧", "terms": ["headphone", "headphones", "earbud", "earbuds", "earphone", "earphones", "neckband", "speaker", "speakers", "soundbar", "airpods", "galaxy buds", "microphone", "mic"]},
    {"slug": "chargers-cables", "name": "Chargers, Cables & Power Banks", "icon": "🔌", "terms": ["charger", "charging adapter", "power adapter", "usb cable", "type c cable", "lightning cable", "power bank", "wall adapter"]},
    {"slug": "components", "name": "PC Components", "icon": "🧩", "terms": ["graphics card", "gpu", "processor", "cpu", "ram", "ddr4", "ddr5", "ssd", "nvme", "motherboard", "power supply", "psu", "pc case", "pc cabinet", "cpu cooler", "computer case"]},
    {"slug": "storage", "name": "Storage & Memory", "icon": "💾", "terms": ["external hard drive", "external ssd", "pen drive", "usb drive", "memory card", "micro sd", "sd card", "hard disk", "hard drive", "portable ssd"]},
    {"slug": "tv", "name": "TVs & Home Entertainment", "icon": "📺", "terms": ["television", "smart tv", "oled tv", "qled", "led tv", "google tv", "android tv", "projector"]},
    {"slug": "cameras", "name": "Cameras & Photography", "icon": "📷", "terms": ["camera", "mirrorless", "dslr", "action camera", "camcorder", "camera lens", "lens"]},
    {"slug": "wearables", "name": "Smartwatches & Wearables", "icon": "⌚", "terms": ["smartwatch", "smart watch", "apple watch", "galaxy watch", "fitness band", "fitness tracker", "smart ring"]},
    {"slug": "gaming", "name": "Gaming & Consoles", "icon": "🎮", "terms": ["playstation", "ps5", "ps4", "xbox", "nintendo", "gaming console", "steam deck", "rog ally", "controller", "gaming handheld"]},
    {"slug": "printers", "name": "Printers & Scanners", "icon": "🖨️", "terms": ["printer", "scanner", "laserjet", "ink tank", "all in one printer"]},
    {"slug": "networking", "name": "Networking", "icon": "📡", "terms": ["router", "mesh wifi", "mesh system", "network switch", "wifi adapter", "access point", "modem"]},
    {"slug": "peripherals", "name": "Computer Peripherals", "icon": "⌨️", "terms": ["keyboard", "mouse", "webcam", "trackpad", "drawing tablet", "graphics tablet", "docking station", "usb hub", "kvm switch"]},
    {"slug": "ups-power", "name": "UPS & Power Backup", "icon": "🔋", "terms": ["ups", "inverter", "power backup", "surge protector", "voltage stabilizer"]},
    {"slug": "smart-home", "name": "Smart Home & Security", "icon": "🏠", "terms": ["smart speaker", "smart display", "smart bulb", "smart plug", "security camera", "cctv", "video doorbell", "smart lock", "home automation"]},
    {"slug": "appliances", "name": "Small Electronics & Appliances", "icon": "⚙️", "terms": ["electric shaver", "trimmer", "hair dryer", "electric toothbrush"]},
    {"slug": "wearable-accessories", "name": "Wearable Accessories", "icon": "🧷", "terms": ["watch strap", "watch band", "watch belt", "watch charger", "watch screen protector", "sport band", "strap", "watch band"]},
    {"slug": "phone-accessories", "name": "Phone Accessories", "icon": "📱", "terms": ["phone case", "mobile cover", "screen protector", "tempered glass", "camera lens protector", "phone battery", "replacement display"]},
]

BRAND_ALIASES = {"mi": "xiaomi", "red mi": "redmi", "one plus": "oneplus", "iq oo": "iqoo", "hewlett packard": "hp", "hewlett-packard": "hp", "apple inc": "apple"}
MODEL_ALIASES = {
    "mac book air": "macbook air", "mac book pro": "macbook pro", "air pods": "airpods", "galaxy s 26": "galaxy s26", "galaxy s 25": "galaxy s25", "galaxy s 24": "galaxy s24", "galaxy s 23": "galaxy s23", "galaxy z fold 7": "galaxy z fold7", "galaxy z flip 7": "galaxy z flip7", "redmi note 14 pro plus": "redmi note 14 pro+", "wh 1000 xm5": "wh1000xm5", "wh 1000 xm 5": "wh1000xm5", "rtx 4070 ti super": "rtx4070tisuper", "type c": "usb c", "usb type c": "usb c", "type-c": "usb c",
}

ACCESSORY_TERMS = {
    "case", "cover", "back cover", "screen protector", "tempered glass", "protector", "strap", "band", "belt", "watch band", "watch strap", "replacement strap", "battery", "replacement battery", "replacement display", "screen replacement", "charging dock", "charger", "charging cable", "cable", "adapter", "mount", "hanger bracket", "bracket", "holder", "stand", "skin", "sleeve", "pouch", "stylus tip", "spare part", "spare parts", "replacement part", "replacement parts", "repair", "hinge repair", "ear tips", "ear tip", "ear cushions", "ear cushion", "ear pads", "ear pad", "earpad", "earpads", "earpad cushion", "earpad cushions", "remote cover", "controller grip", "controller case", "headband cushion", "headphone cushion", "headphone parts", "headphone accessories", "earcup", "ear cup", "replacement hinge", "hinge assembly", "repair kit", "charging case", "toner cartridge", "ink cartridge", "printer cartridge", "replacement blade", "replacement blades", "shaver blade", "shaver blades", "trimmer blade", "trimmer blades", "printer head", "print head", "ink bottle"
}


def normalize_text(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9.+]+", " ", text).strip()
    text = re.sub(r"\s+", " ", text)
    for alias, canonical in sorted({**BRAND_ALIASES, **MODEL_ALIASES}.items(), key=lambda item: -len(item[0])):
        text = re.sub(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", canonical, text)
    return re.sub(r"\s+", " ", text).strip()


def is_accessory(text):
    normalized = normalize_text(text)
    padded = f" {normalized} "
    return any(f" {term} " in padded for term in ACCESSORY_TERMS)


def detect_category(query):
    text = normalize_text(query)
    # Explicit accessory intents take precedence over the device name they reference.
    if any(f" {term} " in f" {text} " for term in ("watch strap", "watch band", "watch belt", "watch charger", "watch screen protector", "sport band", "strap", "watch band")):
        return "wearable-accessories"
    if any(f" {term} " in f" {text} " for term in ("phone case", "mobile cover", "screen protector", "tempered glass", "phone battery", "replacement display")):
        return "phone-accessories"
    for category in ELECTRONICS_CATEGORIES:
        if category["slug"] in {"wearable-accessories", "phone-accessories"}:
            continue
        if any(re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text) for term in category["terms"]):
            return category["slug"]
    if re.search(r"\b(iphone\s*\d+|samsung\s+s\s*\d+|galaxy\s*[samz]\s*\d+|redmi|poco|pixel|oneplus|realme|oppo|vivo|iqoo|motorola|nothing phone)\b", text):
        return "phones"
    if re.search(r"\b(macbook|thinkpad|inspiron|pavilion|vivobook|ideapad|aspire)\b", text):
        return "laptops"
    if re.search(r"rtx\s*\d{4}|gtx\s*\d{3,4}|\b(radeon|geforce|core i[3579]|ryzen)\b", text):
        return "components"
    if re.search(r"\b(wh\s*\d{3,4}\s*xm\s*\d|airpods|galaxy buds|wf\s*\d{4})\b", text):
        return "audio"
    return "electronics"


def category_by_slug(slug):
    return next((item for item in ELECTRONICS_CATEGORIES if item["slug"] == slug), None)


def _model_signature(text):
    text = normalize_text(text)
    patterns = [
        r"\b(oneplus\s+\d+[a-z]?(?:\s*(?:pro|plus|ultra))?)\b",
        r"\b(canon\s+eos\s+r\d+[a-z]?)\b",
        r"\b(logitech\s+mx\s+master\s*\d+[a-z]?)\b",
        r"\b(jbl\s+tune\s*\d{3,4}[a-z]{0,3})\b",
        r"\b(iphone\s*\d+\s*(?:pro\s*max|pro|plus|mini|e)?)\b",
        r"\b((?:samsung\s*)?galaxy\s*(?:s|a|m)\s*\d+\s*(?:ultra|\+|plus|fe|edge)?)(?![a-z0-9])",
        r"\b(samsung\s+s\s*\d+\s*(?:ultra|plus|fe)?)\b",
        r"\b(samsung\s+s\s*\d+\s*(?:ultra|plus|fe)?)\b",
        r"\b(galaxy\s*z\s*(?:fold|flip)\s*\d+\s*(?:ultra|fe)?)\b",
        r"\b(redmi\s*(?:note\s*)?\d+(?:\s*pro\+?)?)\b",
        r"\b(poco\s*[a-z]?\s*\d+\s*(?:pro|plus|ultra|x)?)\b",
        r"\b(realme\s*(?:gt|narzo|number)?\s*\d+[a-z]?(?:\s*pro\+?)?)\b",
        r"\b(oppo\s*(?:reno|find|a)\s*[a-z0-9]+(?:\s*pro|plus|ultra)?)\b",
        r"\b(vivo\s*(?:x|v|y|t)\s*\d+\w*)\b",
        r"\b(pixel\s*\d+\s*(?:pro\s*xl|pro|a)?)\b",
        r"\b(ipad\s*(?:air|pro|mini)\s*m?\d+)\b",
        r"\b(archer\s*ax\s*\d+)\b",
        r"\b(macbook\s*(?:air|pro)\s*(?:m\d+(?:\s*pro|\s*max)?)?)\b",
        r"\b(apple\s*watch\s*(?:series\s*)?\d+\s*(?:ultra\s*\d*)?)\b",
        r"\b((?:gps|gps cellular|cellular)\s+watch\s+by\s+apple\s*[- ]\s*series\s*\d+)\b",
        r"\b(galaxy\s*watch\s*(?:ultra\s*)?\d*)\b",
        r"\b(galaxy\s*tab\s*s\s*\d+\s*(?:ultra|\+|fe)?)\b",
        r"\b(playstation\s*5\s*(?:slim|pro)?|ps5\s*(?:slim|pro)?)\b",
        r"\b(xbox\s*series\s*[xs])\b",
        r"\b(rtx\s*\d{4}\s*(?:ti\s*super|ti|super)?)\b",
        r"\b(rx\s*\d{4}\s*(?:xt|xtx)?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            raw = match.group(1)
            if "watch by apple" in raw:
                series = re.search(r"series\s*(\d+)", raw)
                if series:
                    return f"applewatchseries{series.group(1)}"
            signature = re.sub(r"\s+", "", raw)
            return signature.replace("samsung", "").replace("galaxy", "")
    for pattern in (r"\b(wh\s*\d{3,4}\s*xm\s*\d+)\b", r"\b(wh\d{3,4}xm\d+)\b", r"\b(sm-[a-z0-9]+)\b", r"\b(ep-[a-z0-9]+)\b"):
        match = re.search(pattern, text)
        if match:
            return re.sub(r"\s+", "", match.group(1))
    return None


def extract_specs(text, category=None):
    text = normalize_text(text)
    specs = {}
    patterns = {
        "storage": r"\b(\d+(?:\.\d+)?)\s*(tb|gb)\b", "ram": r"\b(\d+)\s*gb\s*(?:ram|memory|unified memory)\b",
        "wattage": r"\b(\d+(?:\.\d+)?)\s*w(?:att)?\b", "screen_inches": r"\b(\d{1,2}(?:\.\d)?)\s*(?:inch|inches|\")\b",
        "refresh_hz": r"\b(\d{2,3})\s*hz\b", "resolution": r"\b(4k|8k|2k|1080p|1440p|2160p|uhd|fhd|qhd)\b",
        "capacity_mah": r"\b(\d{3,5})\s*mah\b", "colour": r"\b(black|white|blue|green|pink|silver|grey|gray|gold|purple|titanium)\b",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            value = match.group(1)
            if key == "storage":
                amount, unit = match.groups(); specs[key] = int(float(amount) * (1024 if unit == "tb" else 1))
            elif key in {"wattage", "screen_inches"}: specs[key] = float(value)
            elif key in {"refresh_hz", "capacity_mah"}: specs[key] = int(value)
            else: specs[key] = value
    if category == "wearables":
        case_match = re.search(r"\b(38|40|41|42|44|45|46|49)\s*mm\b", text)
        if case_match:
            specs["case_mm"] = int(case_match.group(1))
    if category == "laptops":
        if "ram" not in specs:
            match = re.search(r"\b(8|16|18|24|32|36|48|64|96|128)\s*gb\b", text)
            if match: specs["ram"] = int(match.group(1))
        if specs.get("storage") == specs.get("ram"):
            specs.pop("storage", None)
    if re.search(r"\b(cellular|5g cellular|wi fi \+ cellular)\b", text): specs["connectivity"] = "cellular"
    elif re.search(r"\b(wi fi|wifi)\b", text): specs["connectivity"] = "wifi"
    if re.search(r"\b(disc edition|disc)\b", text): specs["edition"] = "disc"
    elif re.search(r"\b(digital edition|digital)\b", text): specs["edition"] = "digital"
    return specs
