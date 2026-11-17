import asyncio
import json
from importlib.util import find_spec
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import current_app

from integrations.base import Provider
from services.retailer_directory import canonical_retailer_name


class PriceInIndiaProvider(Provider):
    name = "PriceInIndia"
    endpoint = "https://mcp.priceinindia.website/mcp"

    def status(self):
        available = find_spec("mcp") is not None
        return {"name": self.name, "configured": available, "role": "Marketplace aggregator", "message": "Free public read-only MCP provider" if available else "MCP package missing · install project requirements"}

    async def _request(self, query):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(self.endpoint, timeout=current_app.config["REQUEST_TIMEOUT"]) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                # Cost Quest category slugs are not PriceInIndia category IDs/names.
                # Keep upstream discovery broad and enforce exact domain rules locally.
                arguments = {"query": query, "sort": "price_asc", "page": 1, "per_page": 20}
                result = await session.call_tool("search_products", arguments)
                if getattr(result, "isError", False):
                    raise RuntimeError("PriceInIndia search tool returned an error")
                structured = getattr(result, "structuredContent", None)
                if structured is not None:
                    return structured
                texts = [item.text for item in (getattr(result, "content", []) or []) if getattr(item, "type", None) == "text"]
                if not texts:
                    return {}
                try:
                    return json.loads(texts[0])
                except json.JSONDecodeError as exc:
                    raise ValueError("Provider returned non-JSON content") from exc

    @staticmethod
    def _rows(payload):
        rows = payload if isinstance(payload, list) else payload.get("products", payload.get("items", [])) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            raise ValueError("PriceInIndia returned an invalid product list")
        return rows

    def search(self, query):
        timeout = current_app.config["REQUEST_TIMEOUT"]
        payload = asyncio.run(asyncio.wait_for(self._request(query), timeout=timeout + 5))
        rows = self._rows(payload)

        unique_rows, seen_rows = [], set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            identity = str(row.get("productUrl") or row.get("productPageUrl") or row.get("id") or row.get("title") or "").strip().lower()
            if identity and identity not in seen_rows:
                seen_rows.add(identity)
                unique_rows.append(row)
        rows = unique_rows
        output = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            store = str(row.get("store") or "Unknown retailer")
            host = urlparse(store if "://" in store else f"https://{store}").hostname or store
            updated = row.get("lastUpdated")
            try:
                updated_at = datetime.fromtimestamp(float(updated), timezone.utc).isoformat() if updated else None
            except (TypeError, ValueError, OSError):
                updated_at = None
            retailer_name = canonical_retailer_name(host)
            product = self.product(
                row.get("title"), row.get("price"), row.get("productUrl") or row.get("productPageUrl"),
                row.get("imageUrl"), row.get("brand", ""), row.get("id", ""), retailer_name,
                row.get("currency", "INR"), "Out of stock" if row.get("outOfStock") else "Available",
                row.get("attributes") if isinstance(row.get("attributes"), dict) else {},
            )
            if product:
                product["source"] = self.name
                product["source_updated_at"] = updated_at
                product["mrp"] = row.get("mrp")
                product["discount_percent"] = row.get("discountPercent")
                product["retailer"] = retailer_name
                product["retailer_host"] = host
                output.append(product)
        return output
