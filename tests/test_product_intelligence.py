import unittest
from services.product_intelligence import process_offers


def offer(name, price=50000, retailer="Store", url=None, availability="Available"):
    return {"name": name, "price": price, "retailer": retailer, "url": url or f"https://{retailer.lower()}.example/{price}", "availability": availability}


class ProductIntelligenceTests(unittest.TestCase):
    def test_iphone_base_excludes_sibling_models(self):
        rows = [offer("iPhone 16 by Apple - 128GB", 69900), offer("iPhone 16e by Apple - 128GB", 59900), offer("iPhone 16 Plus - 128GB", 79900), offer("iPhone 16 Pro - 128GB", 89900)]
        result = process_offers("iPhone 16 128GB", rows)
        self.assertEqual([p["name"] for p in result], ["iPhone 16 by Apple - 128GB"])

    def test_storage_variants_do_not_mix(self):
        rows = [offer("iPhone 16 - 128GB", 69900), offer("iPhone 16 - 256GB", 79900)]
        result = process_offers("iPhone 16 256GB", rows)
        self.assertEqual(len(result), 1)
        self.assertIn("256GB", result[0]["name"])

    def test_galaxy_fe_is_not_base_s25(self):
        rows = [offer("Samsung Galaxy S25 256GB", 60000), offer("Samsung Galaxy S25 FE 256GB", 52000)]
        result = process_offers("Samsung Galaxy S25 256GB", rows)
        self.assertEqual(len(result), 1)
        self.assertNotIn("FE", result[0]["name"])

    def test_macbook_ram_matching(self):
        rows = [offer("Apple MacBook Air M4 16GB", 99900), offer("Apple MacBook Air M4 24GB", 119900), offer("Apple MacBook Pro M4 16GB", 149900)]
        result = process_offers("MacBook Air M4 16GB", rows)
        self.assertEqual(len(result), 1)
        self.assertIn("Air M4 16GB", result[0]["name"])

    def test_duplicate_url_removed_and_lowest_price_selected(self):
        rows = [offer("iPhone 16 128GB", 70000, "Store", "https://store.example/p"), offer("iPhone 16 128GB", 70000, "Store", "https://store.example/p/"), offer("iPhone 16 128GB", 68000, "Other", "https://other.example/p")]
        result = process_offers("iPhone 16 128GB", rows)
        self.assertEqual(len(result), 2)
        self.assertEqual(sum(bool(p["is_best"]) for p in result), 1)
        self.assertEqual(next(p for p in result if p["is_best"])["price"], 68000)

    def test_out_of_stock_does_not_win_over_available_offer(self):
        rows = [offer("iPhone 16 128GB", 50000, "A", availability="Out of stock"), offer("iPhone 16 128GB", 60000, "B", availability="Available")]
        result = process_offers("iPhone 16 128GB", rows)
        self.assertFalse(next(p for p in result if p["retailer"] == "A")["is_best"])
        self.assertTrue(next(p for p in result if p["retailer"] == "B")["is_best"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
