import ipaddress
from urllib.parse import urlparse

import requests
from flask import current_app

from integrations.base import Provider


def validate_feed_url(url):
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Feed URL must be a valid HTTPS endpoint")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Private feed hosts are not allowed")
    try:
        address = ipaddress.ip_address(host)
        if not address.is_global:
            raise ValueError("Private feed addresses are not allowed")
    except ValueError as exc:
        if "not allowed" in str(exc): raise
    return url


class JsonFeedProvider(Provider):
    def __init__(self, name, url_key, token_key):
        self.name, self.url_key, self.token_key = name, url_key, token_key

    def status(self):
        ready = bool(current_app.config.get(self.url_key))
        return {"name": self.name, "configured": ready, "message": "Authorized JSON feed configured" if ready else "No authorized product feed configured", "domain_coverage": "unverified"}

    def _search_url(self, url, token, query):
        validate_feed_url(url)
        response = requests.get(url, params={"q": query, "query": query}, headers={"Authorization": f"Bearer {token}"} if token else {}, timeout=current_app.config["REQUEST_TIMEOUT"], allow_redirects=False)
        if 300 <= response.status_code < 400:
            raise ValueError("Feed redirects are not allowed")
        response.raise_for_status()
        payload = response.json()
        entries = payload if isinstance(payload, list) else payload.get("products", payload.get("items", [])) if isinstance(payload, dict) else None
        if not isinstance(entries, list): raise ValueError("Feed response must contain a product list")
        output = []
        for row in entries[:100]:
            if not isinstance(row, dict): continue
            price = row.get("price") or row.get("sellingPrice")
            if isinstance(price, dict): price = price.get("amount")
            item = self.product(row.get("name") or row.get("title"), price, row.get("url") or row.get("productUrl"), row.get("image") or row.get("imageUrl"), row.get("brand", ""), row.get("sku") or row.get("productId", ""), self.name, row.get("currency", "INR"), row.get("availability", "Unknown"), row.get("attributes") if isinstance(row.get("attributes"), dict) else {})
            if item: output.append(item)
        return output

    def search(self, query):
        url = current_app.config.get(self.url_key)
        if not url:
            return []
        return self._search_url(url, current_app.config.get(self.token_key), query)
