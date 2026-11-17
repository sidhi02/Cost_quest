from importlib import import_module
import re

DOMAIN_MODULES = {
    "electronics": "domains.electronics.catalog",
    "fashion": "domains.fashion.catalog",
    "home_appliances": "domains.home_appliances.catalog",
    "books_stationery": "domains.books_stationery.catalog",
    "sports_fitness": "domains.sports_fitness.catalog",
    "furniture_home": "domains.furniture_home.catalog",
}
DOMAIN_LABELS = {
    "electronics": "Electronics", "fashion": "Fashion & Lifestyle",
    "home_appliances": "Home Appliances", "books_stationery": "Books & Stationery",
    "sports_fitness": "Sports & Fitness", "furniture_home": "Furniture & Home",
    "general": "General Shopping",
}
DOMAIN_ICONS = {"electronics": "⚡", "fashion": "👗", "home_appliances": "🏠", "books_stationery": "📚", "sports_fitness": "🏃", "furniture_home": "🛋️", "general": "🛍️"}
DOMAIN_DETECTION_PRIORITY = {"home_appliances": 7, "electronics": 6, "books_stationery": 5, "sports_fitness": 4, "furniture_home": 3, "fashion": 2}


def _load_catalogs():
    return {domain: import_module(path).CATEGORIES for domain, path in DOMAIN_MODULES.items()}


DOMAIN_CATEGORIES = _load_catalogs()
ALL_CATEGORIES = [dict(item, domain=domain, domain_name=DOMAIN_LABELS[domain]) for domain, categories in DOMAIN_CATEGORIES.items() for item in categories]
CATEGORY_INDEX = {item["slug"]: item for item in ALL_CATEGORIES}
DOMAIN_INDEX = {slug: {"slug": slug, "name": DOMAIN_LABELS[slug], "icon": DOMAIN_ICONS[slug], "categories": DOMAIN_CATEGORIES[slug]} for slug in DOMAIN_MODULES}
GENERAL_DOMAIN = {"slug": "general", "name": DOMAIN_LABELS["general"], "icon": DOMAIN_ICONS["general"], "categories": []}


def get_domain(domain):
    return GENERAL_DOMAIN if str(domain or "").strip().lower() == "general" else DOMAIN_INDEX.get(str(domain or "").strip().lower())


def get_category(slug):
    return CATEGORY_INDEX.get(str(slug or "").strip().lower())


def categories_for_domain(domain):
    return DOMAIN_CATEGORIES.get(domain, [])


def detect_category(query, domain=None):
    text = str(query or "").lower()
    # Gaming laptop families often include an RTX GPU number; a GPU chip
    # mention must not override the actual laptop product category.
    if domain in (None, "electronics") and re.search(
        r"\b(?:acer\s+)?nitro\s+(?:v\s*\d+|5\b)|\b(?:hp\s+)?victus\b|\b(?:asus\s+)?tuf\s+gaming\b|\brog\s+(?:strix|zephyrus)\b",
        text,
    ):
        return "electronics", CATEGORY_INDEX["laptops"]
    if domain in (None, "electronics"):
        from services.electronics_catalog import detect_category as detect_electronics, category_by_slug
        accessory_slug = detect_electronics(query)
        if accessory_slug in {"wearable-accessories", "phone-accessories"}:
            accessory_category = category_by_slug(accessory_slug)
            if accessory_category:
                return "electronics", accessory_category
    catalogs = [(domain, DOMAIN_CATEGORIES[domain])] if domain in DOMAIN_CATEGORIES else list(DOMAIN_CATEGORIES.items())
    matches = []
    for domain_slug, categories in catalogs:
        for category in categories:
            for term in category.get("terms", []):
                term = term.lower().strip()
                if term and re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text):
                    matches.append((len(term), DOMAIN_DETECTION_PRIORITY[domain_slug], domain_slug, category))
    if matches:
        _, _, found_domain, category = max(matches, key=lambda row: (row[0], row[1]))
        return found_domain, category

    # Preserve the mature electronics classifier, but never accept its generic fallback.
    if domain in (None, "electronics"):
        from services.electronics_catalog import detect_category as detect_electronics, category_by_slug
        slug = detect_electronics(query)
        category = category_by_slug(slug) if slug and slug != "electronics" else None
        if category:
            return "electronics", category
    return (domain if domain in DOMAIN_MODULES else "general"), None


def resolve_search_scope(query, domain=None, category=None):
    selected_category = get_category(category)
    if selected_category:
        return selected_category["domain"], selected_category
    selected_domain = domain if domain in DOMAIN_MODULES else None
    if selected_domain:
        found_domain, found_category = detect_category(query, selected_domain)
        return selected_domain, found_category
    found_domain, found_category = detect_category(query)
    return found_domain, found_category
