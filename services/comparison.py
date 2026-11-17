from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from flask import current_app

from core.query_expansion import query_variants
from core.provider_results import deduplicate_provider_offers
from integrations.amazon import AmazonProvider
from integrations.flipkart import FlipkartProvider
from integrations.json_feed import JsonFeedProvider
from integrations.priceinindia import PriceInIndiaProvider
from core.matching_engine import process_offers_detailed
from services.retailer_directory import retailer_breakdown


class InlineJsonFeedProvider(JsonFeedProvider):
    def __init__(self, name, url, token):
        self.name, self.url, self.token = name, url, token

    def status(self):
        return {"name": self.name, "configured": True, "message": "Authorized JSON feed configured", "domain_coverage": "unverified", "role": "Direct retailer feed"}

    def search(self, query):
        return self._search_url(self.url, self.token, query)


def configured_providers():
    providers = [PriceInIndiaProvider(), AmazonProvider(), FlipkartProvider(),
        JsonFeedProvider("Croma", "CROMA_API_URL", "CROMA_API_TOKEN"),
        JsonFeedProvider("Reliance Digital", "RELIANCE_API_URL", "RELIANCE_API_TOKEN")]
    for entry in filter(None, current_app.config.get("EXTRA_JSON_FEEDS", "").split(";")):
        parts = entry.split("|", 2)
        if len(parts) == 3 and parts[0].strip() and parts[1].strip():
            providers.append(InlineJsonFeedProvider(parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return providers


def _search_provider(app, provider, variants, category):
    results, errors = [], []
    for query in variants:
        try:
            with app.app_context():
                found = provider.search(query)
            if not isinstance(found, list):
                raise ValueError("Provider adapter must return a list")
            results.extend(found)
        except Exception as exc:
            errors.append(exc)
    unique, duplicate_count = deduplicate_provider_offers(results)
    return unique, errors, duplicate_count


def _error_message(exc):
    if isinstance(exc, requests.Timeout): return "Provider timed out"
    if isinstance(exc, requests.HTTPError):
        code = exc.response.status_code if exc.response is not None else "unknown"
        return f"Provider returned HTTP {code}"
    if isinstance(exc, requests.ConnectionError): return "Could not connect to provider"
    if isinstance(exc, requests.RequestException): return "Provider request failed"
    if isinstance(exc, (ValueError, KeyError, TypeError)): return "Provider returned an invalid response"
    if "mcp" in str(exc).lower() and "no module" in str(exc).lower(): return "MCP dependency is not installed"
    return "Provider integration error"


def search_products(query, category=None, domain=None):
    query = " ".join(str(query or "").split())[:160]
    if not query:
        return [], []
    app = current_app._get_current_object()
    providers = configured_providers()
    variants = query_variants(query, domain, category)
    candidates, statuses = [], []
    runnable = []
    for provider in providers:
        with app.app_context():
            status = provider.status()
        status.update(role=status.get("role") or ("Marketplace aggregator" if isinstance(provider, PriceInIndiaProvider) else "Direct retailer API/feed"), domain_coverage="unverified")
        if not status.get("configured"):
            status.update(state="not_configured", mapped_count=0, accepted_count=0, rejected_count=0, duplicate_count=0, message="Not connected · search skipped")
            statuses.append(status)
        else:
            runnable.append((provider, status))

    workers = min(current_app.config.get("MAX_PROVIDER_WORKERS", 5), max(1, len(runnable)))
    variant_duplicates = {}
    if runnable:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            jobs = {pool.submit(_search_provider, app, provider, variants, category): (provider, status) for provider, status in runnable}
            for future in as_completed(jobs):
                provider, status = jobs[future]
                try:
                    found, errors, duplicates = future.result()
                    if errors and not found:
                        raise errors[0]
                    candidates.extend(found)
                    variant_duplicates[provider.name] = duplicates
                    status.update(state="completed" if found else "empty", mapped_count=len(found), message=f"{len(found)} offers returned" if found else "Search completed · 0 offers returned", error=False)
                    if errors:
                        status["warning"] = f"{len(errors)} query variant(s) failed; other searches completed"
                except Exception as exc:
                    status.update(state="error", error=True, mapped_count=0, message=_error_message(exc))
                statuses.append(status)

    products, diagnostics = process_offers_detailed(query, candidates, domain=domain, category=category, ai_config=current_app.config)
    by_source = diagnostics.get("by_source", {})
    order = {provider.name: index for index, provider in enumerate(providers)}
    for status in statuses:
        source_stats = by_source.get(status["name"], {})
        status.update(
            accepted_count=source_stats.get("accepted", 0),
            rejected_count=source_stats.get("rejected", 0),
            duplicate_count=source_stats.get("duplicates", 0) + variant_duplicates.get(status["name"], 0),
            rejection_reasons=source_stats.get("rejection_reasons", {}),
            rejected_samples=source_stats.get("rejected_samples", []),
        )
        if status.get("state") in {"completed", "empty"}:
            status["message"] = f"{status['mapped_count']} offers · {status['accepted_count']} relevant · {status['rejected_count']} rejected"
        elif status.get("state") == "not_configured":
            status["message"] = "Not connected · search skipped"
    statuses.sort(key=lambda item: order.get(item["name"], len(order)))
    return products, statuses
