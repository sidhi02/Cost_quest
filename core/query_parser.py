from core.domain_registry import resolve_search_scope


def parse_search(query, domain=None, category=None):
    clean_query = " ".join(str(query or "").split())[:160]
    resolved_domain, resolved_category = resolve_search_scope(clean_query, domain, category)
    return {"query": clean_query, "domain": resolved_domain, "category": resolved_category["slug"] if resolved_category else None, "category_name": resolved_category["name"] if resolved_category else None}
