import requests
from flask import current_app
from integrations.base import Provider

class FlipkartProvider(Provider):
    name = "Flipkart"
    endpoint = "https://affiliate-api.flipkart.net/affiliate/1.0/search.json"

    def status(self):
        ready = bool(current_app.config["FLIPKART_AFFILIATE_ID"] and current_app.config["FLIPKART_AFFILIATE_TOKEN"])
        return {"name": self.name, "configured": ready, "message": "Affiliate API credentials configured" if ready else "Affiliate ID and API token required"}

    def search(self, query):
        if not self.status()["configured"]:
            return []
        response = requests.get(self.endpoint, params={"query": query, "resultCount": 10}, headers={
            "Fk-Affiliate-Id": current_app.config["FLIPKART_AFFILIATE_ID"],
            "Fk-Affiliate-Token": current_app.config["FLIPKART_AFFILIATE_TOKEN"]
        }, timeout=current_app.config["REQUEST_TIMEOUT"])
        response.raise_for_status()
        output = []
        for entry in response.json().get("productInfoList", []):
            base = entry.get("productBaseInfo", {})
            attrs, ident = base.get("productAttributes", {}), base.get("productIdentifier", {})
            raw = attrs.get("sellingPrice") or attrs.get("flipkartSpecialPrice") or {}
            price = raw.get("amount") if isinstance(raw, dict) else raw
            image = attrs.get("imageUrls") or {}
            item = self.product(attrs.get("title"), price, attrs.get("productUrl"), image.get("400x400") or image.get("200x200"), attrs.get("productBrand"), ident.get("productId"), self.name, availability="In stock" if attrs.get("inStock") else "Check retailer")
            if item:
                output.append(item)
        return output
