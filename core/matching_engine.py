import hashlib
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse

from core.domain_registry import DOMAIN_MODULES, resolve_search_scope
from core.product_schema import normalize_offer
from domains.electronics.attributes import extract as extract_electronics
from domains.fashion.attributes import extract as extract_fashion
from domains.home_appliances.attributes import extract as extract_appliances
from domains.books_stationery.attributes import extract as extract_books
from domains.sports_fitness.attributes import extract as extract_sports
from domains.furniture_home.attributes import extract as extract_furniture
from services.electronics_catalog import normalize_text, _model_signature
from services.product_ai import get_engine
from services.product_ai.normalization import extract_entities, normalize_product_text

ATTRIBUTE_EXTRACTORS = {
    "electronics": extract_electronics, "fashion": extract_fashion,
    "home_appliances": extract_appliances, "books_stationery": extract_books,
    "sports_fitness": extract_sports, "furniture_home": extract_furniture,
}
STOP_WORDS = {"the", "with", "and", "for", "in", "by", "new", "original", "official", "product", "available", "from", "india", "online", "buy", "price", "best", "latest", "size", "men", "mens", "women", "womens"}
ELECTRONICS_BRANDS = {
    "apple": ["apple"], "samsung": ["samsung"], "sony": ["sony"], "nvidia": ["nvidia", "geforce"],
    "tp link": ["tp link", "tplink"], "xiaomi": ["xiaomi", "mi"], "redmi": ["redmi"], "poco": ["poco"],
    "realme": ["realme"], "oppo": ["oppo"], "vivo": ["vivo"], "oneplus": ["oneplus", "one plus"],
    "google": ["google", "pixel"], "motorola": ["motorola", "moto"], "nothing": ["nothing"], "msi": ["msi"],
    "asus": ["asus"], "gigabyte": ["gigabyte"], "inno3d": ["inno3d"], "dell": ["dell"], "hp": ["hp", "hewlett packard"],
    "lenovo": ["lenovo"], "acer": ["acer"], "canon": ["canon"], "nikon": ["nikon"], "lg": ["lg"], "jbl": ["jbl"],
    "anker": ["anker"], "belkin": ["belkin"], "ugreen": ["ugreen"], "logitech": ["logitech"], "garmin": ["garmin"],
    "fitbit": ["fitbit"], "nintendo": ["nintendo"], "microsoft": ["microsoft"], "amd": ["amd"], "intel": ["intel"],
}


def _contains(text, phrase):
    phrase = normalize_text(phrase)
    return bool(phrase and re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", normalize_text(text)))


def _brand_map(domain):
    if domain == "electronics":
        return ELECTRONICS_BRANDS
    if domain not in DOMAIN_MODULES:
        return {}
    from importlib import import_module
    module = import_module(DOMAIN_MODULES[domain])
    aliases = getattr(module, "BRAND_ALIASES", {})
    return {key.lower().strip(): [str(alias).lower().strip() for alias in values] for key, values in aliases.items()}


def _requested_brand(query, domain):
    matches = [(len(alias), brand) for brand, aliases in _brand_map(domain).items() for alias in aliases if _contains(query, alias)]
    return max(matches)[1] if matches else None


def _is_accessory(text, domain):
    if domain not in DOMAIN_MODULES:
        return False
    from importlib import import_module
    module = import_module(DOMAIN_MODULES[domain])
    terms = list(getattr(module, "ACCESSORY_TERMS", []))
    if domain == "electronics":
        from services.electronics_catalog import ACCESSORY_TERMS
        terms.extend(ACCESSORY_TERMS)
    return any(_contains(text, term) for term in terms)


def _extract_attributes(product, domain, category_slug=None):
    extractor = ATTRIBUTE_EXTRACTORS.get(domain)
    if not extractor:
        return {}
    text = " ".join(str(product.get(key) or "") for key in ("name", "brand", "model"))
    result = extractor(text, category_slug) if domain == "electronics" else extractor(text)
    supplied = product.get("attributes") if isinstance(product.get("attributes"), dict) else {}
    result.update({key: value for key, value in supplied.items() if value not in (None, "")})
    return result


def _model_identity(query, domain):
    if domain == "electronics":
        return _model_signature(query)
    if domain == "sports_fitness":
        # Recognize common numbered racket families, not just the sport name.
        normalized = normalize_text(query)
        match = re.search(r"\b(?:yonex\s+)?astrox\s*\d{2,3}\s*(?:pro|play|game|tour)?\b", normalized)
        if match:
            return re.sub(r"\s+", "", match.group(0))
    if domain == "books_stationery":
        attrs = extract_books(query)
        if attrs.get("isbn"):
            return "isbn:" + attrs["isbn"]
    normalized = normalize_text(query)
    if domain == "home_appliances":
        match = re.search(r"\b([a-z]{3,8})\s*(\d{2,4}(?:\.\d+)?[a-z0-9]*)\b", normalized)
        if match:
            return "".join(match.groups())
    if domain in {"home_appliances", "sports_fitness", "furniture_home", "fashion"}:
        match = re.search(r"\b([a-z]{1,8}[-/]?\d{2,}[a-z0-9-]*)\b", normalized)
        return match.group(1) if match else None
    return None


def _stock_state(value):
    text = normalize_text(value)
    if any(term in text for term in ("out of stock", "outofstock", "sold out", "unavailable", "not available", "not in stock")):
        return "out"
    if any(term in text for term in ("in stock", "available", "ready to ship")):
        return "in"
    return "unknown"


def _comparison_key(product, domain, category_slug, unverified=()):
    attrs = _extract_attributes(product, domain, category_slug)
    identity = None
    if domain == "books_stationery" and attrs.get("isbn"):
        identity = "isbn:" + attrs["isbn"]
    elif domain == "electronics":
        identity = _model_identity(product.get("name"), domain)
    if not identity:
        title = normalize_text(" ".join(str(product.get(k) or "") for k in ("name", "brand", "model")))
        tokens = sorted({token for token in title.split() if token not in STOP_WORDS and token not in {"uk", "us", "india", "indian"}})
        identity = "tokens:" + " ".join(tokens)
    parts = [domain, category_slug or "general", identity]
    for key in sorted(attrs):
        parts.append(f"{key}={attrs[key]}")
    for key in sorted(unverified):
        parts.append(f"unverified:{key}")
    if domain == "electronics" and str(identity).startswith("rtx"):
        partner = normalize_text(product.get("brand")) or next((item for item in ("msi", "asus", "gigabyte", "inno3d", "zotac", "pny", "gainward") if _contains(product.get("name"), item)), "reference")
        parts.append("board=" + partner)
    return "|".join(parts)


def _assess_offer(query, product, domain, category_slug, ai_features=None, ai_config=None):
    title = normalize_text(" ".join(str(product.get(key) or "") for key in ("name", "brand", "model")))
    if not title:
        return "invalid_title", None, []
    query_accessory = _is_accessory(query, domain)
    product_accessory = _is_accessory(title, domain)
    if product_accessory and not query_accessory:
        return "accessory_instead_of_product", None, []
    if query_accessory and not product_accessory:
        return "wrong_product_type", None, []

    requested_brand = _requested_brand(query, domain)
    if requested_brand:
        aliases = _brand_map(domain)[requested_brand]
        if not any(_contains(title, alias) for alias in aliases):
            if not (domain == "electronics" and requested_brand == "nvidia" and _model_identity(query, domain) == _model_identity(title, domain)):
                return "wrong_brand", None, []

    query_identity, product_identity = _model_identity(query, domain), _model_identity(title, domain)
    if query_identity and product_identity and query_identity != product_identity:
        return "model_mismatch", None, []
    if query_identity and not product_identity:
        return "model_not_verified", None, []

    if category_slug:
        _, product_category = resolve_search_scope(title, domain)
        if product_category and product_category["slug"] != category_slug:
            return "wrong_category", None, []

    query_attributes = _extract_attributes({"name": query}, domain, category_slug)
    product_attributes = _extract_attributes(product, domain, category_slug)
    unverified = []
    for key, expected in query_attributes.items():
        actual = product_attributes.get(key)
        if actual in (None, ""):
            if key == "size":
                return "variant_not_verified:size", None, []
            unverified.append(key)
        elif str(actual).casefold() != str(expected).casefold():
            return f"attribute_mismatch:{key}", None, []

    if domain == "electronics":
        q_norm = normalize_text(query)
        p_norm = title
        for term in ("slim", "disc", "digital", "cellular", "wifi", "wi fi", "gps", "ultra", "pro", "plus", "fe"):
            if _contains(q_norm, term) and not _contains(p_norm, term):
                if term in {"ultra", "pro", "plus", "fe", "slim", "disc", "digital", "cellular"}:
                    return f"variant_mismatch:{term}", None, []
                unverified.append(term)
        q_cable, p_cable = _contains(q_norm, "cable"), _contains(p_norm, "cable")
        q_bank, p_bank = _contains(q_norm, "power bank"), _contains(p_norm, "power bank")
        if q_cable != p_cable or q_bank != p_bank:
            return "wrong_product_type", None, []
        if _contains(q_norm, "charger") and not any(_contains(p_norm, term) for term in ("charger", "adapter")):
            return "wrong_product_type", None, []
        q_strap = _contains(q_norm, "strap") or _contains(q_norm, "band")
        p_strap = _contains(p_norm, "strap") or _contains(p_norm, "band")
        if q_strap != p_strap:
            return "wrong_product_type", None, []

    q_tokens = {token for token in normalize_text(query).split() if token not in STOP_WORDS and not token.isdigit() and len(token) > 1}
    p_tokens = set(title.split())
    overlap = len(q_tokens & p_tokens) / max(1, len(q_tokens))
    threshold = 0.25 if domain == "general" else 0.34
    semantic_score = (ai_features or {}).get("semantic")
    siamese_score = (ai_features or {}).get("siamese")
    semantic_threshold = float((ai_config or {}).get("AI_SEMANTIC_RESCUE_THRESHOLD", 0.84))
    siamese_threshold = max(float((ai_config or {}).get("AI_SIAMESE_RESCUE_THRESHOLD", 0.90)), float((ai_features or {}).get("siamese_threshold") or 0.0))
    semantic_rescue = domain != "general" and bool(category_slug or requested_brand or query_identity) and semantic_score is not None and semantic_score >= semantic_threshold
    siamese_rescue = domain != "general" and bool(category_slug or requested_brand or query_identity) and siamese_score is not None and siamese_score >= siamese_threshold
    if overlap < threshold and not query_identity and not semantic_rescue and not siamese_rescue:
        return "low_title_relevance", None, []

    confidence = "review" if unverified else "high" if query_identity or product_attributes.get("isbn") else "medium"
    return None, confidence, unverified


def _semantic_pair_allowed(left, right, domain):
    if left.get("comparison_key") == right.get("comparison_key"):
        return False
    if left.get("unverified_attributes") or right.get("unverified_attributes"):
        return False
    left_title = " ".join(str(left.get(key) or "") for key in ("name", "brand", "model"))
    right_title = " ".join(str(right.get(key) or "") for key in ("name", "brand", "model"))
    left_brand = _requested_brand(left_title, domain)
    right_brand = _requested_brand(right_title, domain)
    if not left_brand or left_brand != right_brand:
        return False
    left_identity, right_identity = _model_identity(left_title, domain), _model_identity(right_title, domain)
    if left_identity != right_identity and (left_identity or right_identity):
        return False
    left_attrs, right_attrs = left.get("attributes", {}), right.get("attributes", {})
    for key in set(left_attrs) & set(right_attrs):
        if str(left_attrs[key]).casefold() != str(right_attrs[key]).casefold():
            return False
    for key in ("domain", "category"):
        if left.get(key) != right.get(key):
            return False
    return True


def _apply_semantic_grouping(valid, domain, engine):
    candidates = sorted(valid, key=lambda item: item.get("relevance_score", 0), reverse=True)[:30]
    pairs, indices = [], []
    for i, left in enumerate(candidates):
        for j in range(i + 1, len(candidates)):
            right = candidates[j]
            if _semantic_pair_allowed(left, right, domain):
                pairs.append((normalize_product_text(" ".join(str(left.get(key) or "") for key in ("name", "brand", "model"))), normalize_product_text(" ".join(str(right.get(key) or "") for key in ("name", "brand", "model")))))
                indices.append((left, right))
    if not pairs:
        return 0
    scores = engine.compare_title_pairs(pairs)
    score_by_pair = {frozenset((id(left), id(right))): score for (left, right), score in zip(indices, scores)}
    parent = list(range(len(candidates)))
    position = {id(item): index for index, item in enumerate(candidates)}
    initial_keys = {}
    for index, item in enumerate(candidates):
        key = item.get("comparison_key")
        if key in initial_keys:
            parent[index] = initial_keys[key]
        else:
            initial_keys[key] = index

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def pair_matches(left, right):
        if left.get("comparison_key") == right.get("comparison_key"):
            return True
        score = score_by_pair.get(frozenset((id(left), id(right))))
        if score is None:
            return False
        siamese_match = score.get("siamese") is not None and score["siamese"] >= max(0.75, learned_threshold)
        transformer_match = score.get("semantic") is not None and score["semantic"] >= 0.86 and score.get("cross_encoder") is not None and score["cross_encoder"] >= 0.88
        return siamese_match or transformer_match

    learned_threshold = engine.siamese_threshold()
    grouped = 0
    ai_merged = set()
    for (left, right), score in zip(indices, scores):
        left_root, right_root = find(position[id(left)]), find(position[id(right)])
        if left_root == right_root:
            continue
        left_members = [item for index, item in enumerate(candidates) if find(index) == left_root]
        right_members = [item for index, item in enumerate(candidates) if find(index) == right_root]
        if not all(pair_matches(a, b) for a in left_members for b in right_members):
            continue
        parent[right_root] = left_root
        ai_merged.update(id(item) for item in left_members + right_members)
        left["semantic_grouped"] = right["semantic_grouped"] = True
        left["pair_match_evidence"] = right["pair_match_evidence"] = {key: round(value, 4) if value is not None else None for key, value in score.items()}
        grouped += 1

    clusters = defaultdict(list)
    for index, item in enumerate(candidates):
        clusters[find(index)].append(item)
    for members in clusters.values():
        if len(members) < 2 or not any(id(item) in ai_merged for item in members):
            continue
        original_keys = {item.get("comparison_key") for item in members}
        all_members = [item for item in valid if item.get("comparison_key") in original_keys]
        signature = "|".join(sorted(normalize_product_text(item["name"]) for item in all_members))
        key = "ai:" + hashlib.sha256(f"{domain}|{members[0].get('category')}|{signature}".encode()).hexdigest()[:20]
        for item in all_members:
            item["comparison_key"] = key
            item["semantic_grouped"] = True
    return grouped


def process_offers_detailed(query, products, domain=None, category=None, ai_config=None):
    domain, detected_category = resolve_search_scope(query, domain, category)
    category_slug = category or (detected_category["slug"] if detected_category else None)
    valid, seen = [], set()
    diagnostics = {"mapped": 0, "accepted": 0, "rejected": 0, "duplicates": 0, "rejection_reasons": {}, "rejected_samples": [], "by_source": {}}
    engine = get_engine(ai_config)
    try:
        ai_features = engine.score_candidates(query, products, domain)
    except Exception:
        ai_features = [{} for _ in products]
    reasons = Counter()
    by_source = defaultdict(lambda: {"mapped": 0, "accepted": 0, "rejected": 0, "duplicates": 0, "rejection_reasons": {}, "rejected_samples": []})

    def record_rejection(source, original, reason):
        diagnostics["rejected"] += 1
        by_source[source]["rejected"] += 1
        reasons[reason] += 1
        local = by_source[source]["rejection_reasons"]
        local[reason] = local.get(reason, 0) + 1
        sample = {"title": str((original or {}).get("name") or (original or {}).get("title") or "Unknown listing")[:180], "retailer": str((original or {}).get("retailer") or "Unknown retailer")[:80], "reason": reason}
        if len(diagnostics["rejected_samples"]) < 30:
            diagnostics["rejected_samples"].append(sample)
        if len(by_source[source]["rejected_samples"]) < 10:
            by_source[source]["rejected_samples"].append(sample)

    for index, original in enumerate(products):
        feature = ai_features[index] if index < len(ai_features) else {}
        source = str((original or {}).get("source") or (original or {}).get("retailer") or "Unknown") if isinstance(original, dict) else "Unknown"
        diagnostics["mapped"] += 1
        by_source[source]["mapped"] += 1
        normalized = normalize_offer(original)
        reason = None
        confidence, unverified = None, []
        if not normalized:
            reason = "invalid_offer_data"
        else:
            reason, confidence, unverified = _assess_offer(query, normalized, domain, category_slug, feature, ai_config)
        if reason:
            record_rejection(source, original, reason)
            continue

        parsed = urlparse(str(normalized.get("url") or ""))
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            reason = "invalid_product_url"
        else:
            try:
                price = float(normalized.get("price"))
            except (TypeError, ValueError):
                reason = "invalid_price"
            else:
                if not (0 < price <= 100_000_000):
                    reason = "invalid_price"
        if reason:
            record_rejection(source, original, reason)
            continue

        normalized["price"] = round(price, 2)
        host, path = (parsed.hostname or "").lower(), parsed.path.rstrip("/")
        sku = normalize_text(normalized.get("sku"))
        dedupe_key = (host, path, sku) if path and sku else (host, path) if path else (host, sku or normalize_text(normalized["name"]), price)
        if dedupe_key in seen:
            diagnostics["duplicates"] += 1
            by_source[source]["duplicates"] += 1
            continue
        seen.add(dedupe_key)
        normalized["domain"] = domain
        normalized["category"] = category_slug or "general"
        normalized["attributes"] = _extract_attributes(normalized, domain, category_slug)
        normalized["unverified_attributes"] = unverified
        normalized["comparison_key"] = _comparison_key(normalized, domain, category_slug, unverified)
        normalized["match_confidence"] = confidence
        normalized["nlp_entities"] = feature.get("entities") or extract_entities(normalized["name"])
        normalized["ai_evidence"] = {key: feature.get(key) for key in ("bm25", "char_tfidf", "semantic", "cross_encoder", "siamese", "clip") if feature.get(key) is not None}
        normalized["relevance_score"] = float(feature.get("rank_score") or 0.0)
        requested_tokens = {token for token in normalize_text(query).split() if token not in STOP_WORDS and not token.isdigit() and len(token) > 1}
        candidate_tokens = set(normalize_text(normalized["name"]).split())
        title_overlap = len(requested_tokens & candidate_tokens) / max(1, len(requested_tokens))
        minimum_overlap = 0.25 if domain == "general" else 0.34
        normalized["semantic_rescued"] = title_overlap < minimum_overlap and bool(feature.get("semantic") is not None and feature["semantic"] >= float((ai_config or {}).get("AI_SEMANTIC_RESCUE_THRESHOLD", 0.84)))
        normalized["siamese_rescued"] = title_overlap < minimum_overlap and bool(feature.get("siamese") is not None and feature["siamese"] >= float((ai_config or {}).get("AI_SIAMESE_RESCUE_THRESHOLD", 0.90)))
        normalized["is_best"] = False
        normalized["saving"] = 0.0
        valid.append(normalized)
        diagnostics["accepted"] += 1
        by_source[source]["accepted"] += 1

    diagnostics["semantic_pair_merges"] = _apply_semantic_grouping(valid, domain, engine) if domain != "general" else 0
    diagnostics["intelligence"] = engine.status()
    groups = defaultdict(list)
    for product in valid:
        groups[product["comparison_key"]].append(product)
    for offers in groups.values():
        in_stock = [item for item in offers if _stock_state(item.get("availability")) == "in"]
        unknown_stock = [item for item in offers if _stock_state(item.get("availability")) == "unknown"]
        pool = [item for item in (in_stock or unknown_stock) if item["match_confidence"] != "review"]
        lowest = min((item["price"] for item in pool), default=None)
        for item in offers:
            item["comparison_count"] = len(offers)
            item["is_best"] = len(offers) > 1 and lowest is not None and item in pool and item["price"] == lowest
            item["saving"] = round(item["price"] - lowest, 2) if lowest is not None and _stock_state(item.get("availability")) != "out" else 0.0
    diagnostics["rejection_reasons"] = dict(reasons)
    diagnostics["by_source"] = dict(by_source)
    return sorted(valid, key=lambda item: (_stock_state(item.get("availability")) == "out", item["price"], normalize_text(item.get("retailer")))), diagnostics


def process_offers(query, products, domain=None, category=None):
    return process_offers_detailed(query, products, domain, category)[0]
