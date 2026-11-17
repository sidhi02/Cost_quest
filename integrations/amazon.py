import hashlib
import threading
import time

import requests
from flask import current_app

from integrations.base import Provider


class AmazonProvider(Provider):
    name = "Amazon"
    _token_cache = {}
    _token_lock = threading.Lock()

    def status(self):
        config = current_app.config
        ready = all(config[key] for key in ("AMAZON_CREATOR_CLIENT_ID", "AMAZON_CREATOR_CLIENT_SECRET", "AMAZON_PARTNER_TAG"))
        return {
            "name": self.name,
            "configured": ready,
            "message": "Creators API credentials configured" if ready else "Amazon Associates Creators API access and credentials required",
        }

    def _access_token(self):
        config = current_app.config
        client_id, client_secret = config["AMAZON_CREATOR_CLIENT_ID"], config["AMAZON_CREATOR_CLIENT_SECRET"]
        cache_key = hashlib.sha256(f"{client_id}:{client_secret}".encode()).hexdigest()
        with self._token_lock:
            cached = self._token_cache.get(cache_key)
            if cached and time.time() < cached[1] - 60:
                return cached[0]
            version = config["AMAZON_CREATOR_VERSION"]
            token_hosts = {
                "3.1": "https://api.amazon.com/auth/o2/token",
                "3.2": "https://api.amazon.co.uk/auth/o2/token",
                "3.3": "https://api.amazon.co.jp/auth/o2/token",
            }
            token_host = token_hosts.get(version)
            if not token_host:
                raise ValueError(f"Unsupported Amazon Creators API credential version: {version}")
            response = requests.post(token_host, json={
                "grant_type": "client_credentials", "client_id": client_id,
                "client_secret": client_secret, "scope": "creatorsapi::default",
            }, timeout=config["REQUEST_TIMEOUT"])
            response.raise_for_status()
            payload = response.json()
            token, expires = payload["access_token"], time.time() + int(payload.get("expires_in", 3600))
            self._token_cache[cache_key] = (token, expires)
            return token

    def search(self, query):
        if not self.status()["configured"]:
            return []
        config = current_app.config
        response = requests.post(
            "https://creatorsapi.amazon/catalog/v1/searchItems",
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Content-Type": "application/json",
                "x-marketplace": "www.amazon.in",
            },
            json={
                "keywords": query, "partnerTag": config["AMAZON_PARTNER_TAG"],
                "marketplace": "www.amazon.in", "currencyOfPreference": "INR", "itemCount": 10,
                "resources": ["images.primary.medium", "itemInfo.title", "offersV2.listings.price", "offersV2.listings.availability"],
            },
            timeout=config["REQUEST_TIMEOUT"],
        )
        response.raise_for_status()
        items = response.json().get("searchResult", {}).get("items", [])
        output = []
        for item in items:
            title = item.get("itemInfo", {}).get("title", {}).get("displayValue", "")
            listing = (item.get("offersV2", {}).get("listings") or [{}])[0]
            money = listing.get("price", {}).get("money", {})
            image = item.get("images", {}).get("primary", {}).get("medium", {}).get("url", "")
            product = self.product(
                title, money.get("amount"), item.get("detailPageURL", ""), image, "",
                item.get("asin", ""), self.name, money.get("currency", "INR"),
                listing.get("availability", {}).get("type", "Unknown"),
            )
            if product:
                output.append(product)
        return output
