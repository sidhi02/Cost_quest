import unittest
from services.electronics_catalog import ELECTRONICS_CATEGORIES, detect_category, extract_specs, normalize_text
from services.product_intelligence import process_offers


def offer(name, price=1000, retailer="store", url=None, availability="Available"):
    return {"name": name, "price": price, "retailer": retailer, "url": url or f"https://{retailer}.example/{price}", "availability": availability}


class ElectronicsCatalogTests(unittest.TestCase):
    def test_catalog_has_twenty_families(self):
        self.assertEqual(len(ELECTRONICS_CATEGORIES), 20)

    def test_category_detection(self):
        cases = {"Redmi Note 14 Pro": "phones", "MacBook Air M4": "laptops", "27 inch 144Hz monitor": "monitors", "Sony WH-1000XM5 headphones": "audio", "65W USB C charger": "chargers-cables", "iPad Air": "tablets", "RTX 4070 Ti Super": "components", "Samsung OLED TV": "tv", "Canon mirrorless camera": "cameras", "Apple Watch Series 10": "wearables", "PlayStation 5 Slim": "gaming", "HP LaserJet printer": "printers"}
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(detect_category(query), expected)

    def test_alias_normalization(self):
        self.assertEqual(normalize_text("Mac Book Air"), "macbook air")
        self.assertEqual(normalize_text("One Plus"), "oneplus")
        self.assertEqual(normalize_text("WH 1000 XM5"), "wh1000xm5")

    def test_laptop_ram_is_not_mistaken_for_ssd(self):
        specs = extract_specs("MacBook Air M4 16GB", "laptops")
        self.assertEqual(specs["ram"], 16)
        self.assertNotIn("storage", specs)

    def test_sibling_phone_models_are_rejected(self):
        results = process_offers("iPhone 16 128GB", [offer("Apple iPhone 16 128GB"), offer("Apple iPhone 16e 128GB", retailer="other"), offer("Apple iPhone 16 Plus 128GB", retailer="third")])
        self.assertEqual([item["name"] for item in results], ["Apple iPhone 16 128GB"])

    def test_storage_variants_are_not_merged(self):
        results = process_offers("iPhone 16 128GB", [offer("iPhone 16 128GB"), offer("iPhone 16 256GB", retailer="other")])
        self.assertEqual(len(results), 1)

    def test_samsung_fe_is_rejected_for_base_s25(self):
        results = process_offers("Samsung Galaxy S25 256GB", [offer("Samsung Galaxy S25 256GB"), offer("Samsung Galaxy S25 FE 256GB", retailer="other")])
        self.assertEqual(len(results), 1)

    def test_lowest_price_is_per_exact_configuration(self):
        results = process_offers("iPhone 16 128GB", [offer("iPhone 16 128GB", 69900), offer("iPhone 16 128GB", 67900, "other"), offer("iPhone 16 256GB", 79900, "third")])
        self.assertEqual(len(results), 2)
        self.assertTrue(any(item["is_best"] and item["price"] == 67900 for item in results))

    def test_out_of_stock_not_ranked_as_best_when_in_stock_exists(self):
        results = process_offers("iPhone 16 128GB", [offer("iPhone 16 128GB", 60000, "a", availability="Out of stock"), offer("iPhone 16 128GB", 70000, "b")])
        self.assertFalse(next(item for item in results if item["retailer"] == "a")["is_best"])
        self.assertTrue(next(item for item in results if item["retailer"] == "b")["is_best"])


if __name__ == "__main__":
    unittest.main()
