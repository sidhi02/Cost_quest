import hashlib
import math
import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse


class Provider(ABC):
    name = "Provider"

    @abstractmethod
    def search(self, query):
        raise NotImplementedError

    @abstractmethod
    def status(self):
        raise NotImplementedError

    @staticmethod
    def product(name, price, url, image="", brand="", sku="", retailer="", currency="INR", availability="Unknown", attributes=None):
        clean = re.sub(r"\s+", " ", str(name or "")).strip()
        try: amount = float(price)
        except (TypeError, ValueError): return None
        product_url = str(url or "").strip()
        parsed = urlparse(product_url)
        if not clean or len(clean) > 500 or not math.isfinite(amount) or not 0 < amount <= 100_000_000 or parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        image_url = str(image or "").strip()
        image_parsed = urlparse(image_url)
        if image_parsed.scheme not in {"http", "https"} or not image_parsed.hostname or image_parsed.username or image_parsed.password:
            image_url = ""
        currency = str(currency or "INR").upper()
        if currency != "INR": return None
        retailer = re.sub(r"\s+", " ", str(retailer or "")).strip()
        if not retailer: return None
        identity = str(sku or clean).strip().lower()
        key = hashlib.sha256(f"{retailer.lower()}|{identity}".encode()).hexdigest()[:24]
        return {
            "product_key": key, "name": clean, "price": round(amount, 2), "url": product_url,
            "image": image_url, "brand": str(brand or "").strip(), "sku": str(sku or "").strip(),
            "retailer": retailer, "currency": currency, "availability": str(availability or "Unknown").strip(),
            "source": retailer, "source_updated_at": None, "mrp": None, "discount_percent": None,
            "attributes": attributes if isinstance(attributes, dict) else {},
        }
