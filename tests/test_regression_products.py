import unittest
from services.electronics_catalog import detect_category, extract_specs, _model_signature
from services.product_intelligence import process_offers
from integrations.base import Provider


def offer(name, price=1000, retailer="Store", path=None, availability="Available", brand=""):
    return {"name": name, "price": price, "retailer": retailer, "url": f"https://{retailer.lower().replace(' ', '')}.example/{path or abs(hash(name))}", "availability": availability, "brand": brand, "sku": path or ""}


class TenSearchRegressionTests(unittest.TestCase):
    def test_samsung_galaxy_s26_exact_variant_and_fe_rejection(self):
        rows = [offer("Samsung Galaxy S26 256GB"), offer("Samsung Galaxy S26+ 256GB", retailer="B"), offer("Samsung Galaxy S26 Ultra 256GB", retailer="C"), offer("Samsung Galaxy S26 FE 256GB", retailer="D")]
        self.assertEqual([p["name"] for p in process_offers("Samsung Galaxy S26 256GB", rows)], ["Samsung Galaxy S26 256GB"])

    def test_apple_watch_family_search_keeps_series_distinct(self):
        rows = [offer("Apple Watch SE 3 by Apple - 40 mm GPS", retailer="A"), offer("Apple Watch Series 12 by Apple - 42 mm GPS", retailer="B"), offer("Samsung Galaxy Watch 7", retailer="C")]
        result = process_offers("Apple Watch", rows)
        self.assertEqual(len(result), 2)
        self.assertEqual(len({p["comparison_key"] for p in result}), 2)

    def test_apple_watch_strap_excludes_unrelated_products(self):
        self.assertEqual(detect_category("Apple Watch strap"), "wearable-accessories")
        rows = [offer("Apple Watch Strap by ACM - 120mm"), offer("Apple Watch Series 10 smartwatch", retailer="B"), offer("Samsung watch strap", retailer="C")]
        self.assertEqual([p["name"] for p in process_offers("Apple Watch strap", rows)], ["Apple Watch Strap by ACM - 120mm"])

    def test_sony_headphones_retain_exact_model(self):
        rows = [offer("WH-1000XM5 by Sony - Wireless Headphones"), offer("WH-1000XM4 by Sony - Wireless Headphones", retailer="B"), offer("Sony WF-1000XM5 earbuds", retailer="C")]
        self.assertEqual(len(process_offers("Sony WH-1000XM5", rows)), 1)

    def test_macbook_air_m4_ram_and_family(self):
        self.assertEqual(_model_signature("MacBook Air M4 16GB"), _model_signature("Apple MacBook Air M4 16GB"))
        rows = [offer("Apple MacBook Air M4 16GB", retailer="A"), offer("Apple MacBook Air M4 24GB", retailer="B"), offer("Apple MacBook Pro M4 16GB", retailer="C")]
        self.assertEqual(len(process_offers("MacBook Air M4 16GB", rows)), 1)

    def test_ipad_air_m3_connectivity_and_storage_are_separate(self):
        query = "iPad Air M3 11 inch"
        rows = [offer("iPad Air M3 by Apple - 11 inch Wi-Fi Tablet", retailer="A"), offer("iPad Air M3 11 inch Wi-Fi + Cellular 256GB", retailer="B"), offer("iPad Air M2 11 inch Wi-Fi", retailer="C")]
        result = process_offers(query, rows)
        self.assertEqual(len(result), 2)
        self.assertEqual(len({p["comparison_key"] for p in result}), 2)
        self.assertEqual(extract_specs("iPad Air M3 11 inch Wi-Fi + Cellular 256GB", "tablets")["connectivity"], "cellular")

    def test_rtx_5070_partner_cards_not_collapsed(self):
        rows = [offer("MSI GeForce RTX 5070 12G", retailer="A"), offer("Inno3D RTX 5070 Twin X2 12GB", retailer="B"), offer("MSI GeForce RTX 5070 12G", retailer="C", availability="Out of stock")]
        result = process_offers("NVIDIA RTX 5070", rows)
        self.assertEqual(len(result), 3)
        self.assertEqual(len({p["comparison_key"] for p in result}), 2)

    def test_ps5_slim_disc_excludes_digital_and_original(self):
        rows = [offer("Sony PlayStation 5 Slim Disc Edition Console", retailer="A"), offer("Sony PlayStation 5 Slim Digital Edition", retailer="B"), offer("Sony PlayStation 5 Disc Edition", retailer="C")]
        self.assertEqual(len(process_offers("PlayStation 5 Slim Disc Edition", rows)), 1)

    def test_samsung_45w_charger_excludes_cable_and_other_brands(self):
        rows = [offer("Fast Charger by Samsung - 45W USB-C", retailer="A"), offer("USB-C cable 45W", retailer="B"), offer("Anker 45W USB-C charger", retailer="C"), offer("Nothing 45W charger", retailer="D")]
        result = process_offers("Samsung 45W USB-C charger", rows)
        self.assertEqual([p["name"] for p in result], ["Fast Charger by Samsung - 45W USB-C"])

    def test_tp_link_archer_ax55_router_matching(self):
        rows = [offer("TP-Link Archer AX55 AX3000 Wi-Fi 6 Router", retailer="A"), offer("TP-Link Archer AX50 AX3000 Router", retailer="B"), offer("D-Link AX55 Router", retailer="C")]
        self.assertEqual(len(process_offers("TP-Link Archer AX55 router", rows)), 1)

    def test_device_search_excludes_accessories(self):
        rows = [offer("Apple iPhone 16 128GB", retailer="A"), offer("iPhone 16 protective case", retailer="B"), offer("iPhone 16 screen protector", retailer="C")]
        self.assertEqual(len(process_offers("iPhone 16 128GB", rows)), 1)

    def test_power_bank_search_is_not_treated_as_charger_or_cable(self):
        rows = [offer("Samsung 10000mAh Power Bank", retailer="A"), offer("Samsung 45W USB-C charger", retailer="B"), offer("Samsung USB-C cable", retailer="C")]
        self.assertEqual(len(process_offers("Samsung power bank", rows)), 1)


class BroaderCategoryRegressionTests(unittest.TestCase):
    def test_additional_electronics_categories_reject_cross_category_noise(self):
        cases = {
            "27 inch 144Hz monitor": ("Samsung 27 inch 144Hz Gaming Monitor", "Sony WH-1000XM5 headphones"),
            "Canon mirrorless camera": ("Canon EOS R50 Mirrorless Camera", "Canon printer"),
            "Samsung 55 inch OLED TV": ("Samsung 55 inch OLED Smart TV", "Samsung Galaxy S25 phone"),
            "Logitech wireless mouse": ("Logitech Wireless Mouse", "Logitech Keyboard"),
            "JBL Bluetooth speaker": ("JBL Bluetooth Speaker", "Sony headphones"),
            "WD 1TB external hard drive": ("WD 1TB External Hard Drive", "WD 1TB internal SSD"),
        }
        for query, (good, bad) in cases.items():
            with self.subTest(query=query):
                self.assertEqual([p["name"] for p in process_offers(query, [offer(good), offer(bad, retailer="Bad")])], [good])


    def test_relevance_across_all_twenty_electronics_categories(self):
        cases = [
            ("iPhone 16 128GB", "Apple iPhone 16 128GB", "Samsung Galaxy S25 128GB"),
            ("Dell XPS 13 laptop", "Dell XPS 13 laptop", "Dell 27 inch monitor"),
            ("iPad Air M3 tablet", "Apple iPad Air M3 tablet", "Apple MacBook Air M3"),
            ("Samsung 27 inch monitor", "Samsung 27 inch monitor", "Samsung 55 inch TV"),
            ("Sony WH-1000XM5 headphones", "Sony WH-1000XM5 headphones", "Sony mirrorless camera"),
            ("Samsung 45W USB-C charger", "Samsung 45W USB-C charger", "Samsung USB-C cable"),
            ("NVIDIA RTX 5070 GPU", "MSI RTX 5070 graphics card", "MSI RTX 5060 graphics card"),
            ("Samsung 55 inch OLED TV", "Samsung 55 inch OLED TV", "Samsung Galaxy S25 phone"),
            ("Canon mirrorless camera", "Canon EOS R50 mirrorless camera", "Canon printer"),
            ("Apple Watch Series 10 smartwatch", "Apple Watch Series 10 smartwatch", "Apple Watch strap"),
            ("PlayStation 5 Slim Disc Edition", "Sony PlayStation 5 Slim Disc Edition", "Sony PlayStation 5 Digital Edition"),
            ("TP-Link Archer AX55 router", "TP-Link Archer AX55 Wi-Fi 6 router", "TP-Link Archer AX50 router"),
        ]
        for query, matching, unrelated in cases:
            with self.subTest(query=query):
                result = process_offers(query, [offer(matching), offer(unrelated, retailer="Other")])
                self.assertEqual([item["name"] for item in result], [matching])

class ProviderDataIntegrityTests(unittest.TestCase):
    def test_provider_rejects_invalid_prices_and_product_urls(self):
        self.assertIsNone(Provider.product("Phone", 0, "https://store.example/p"))
        self.assertIsNone(Provider.product("Phone", float("nan"), "https://store.example/p"))
        self.assertIsNone(Provider.product("Phone", 100, "javascript:alert(1)"))
        self.assertIsNone(Provider.product("Phone", 100, "https://user:pass@store.example/p"))

    def test_provider_discards_invalid_image_url_without_losing_offer(self):
        item = Provider.product("Phone", 100, "https://store.example/p", image="javascript:alert(1)", retailer="Store")
        self.assertIsNotNone(item)
        self.assertEqual(item["image"], "")
        self.assertEqual(item["url"], "https://store.example/p")

    def test_provider_rejects_non_inr_prices(self):
        self.assertIsNone(Provider.product("Phone", 100, "https://store.example/p", currency="USD"))

    def test_out_of_stock_only_group_has_no_buyable_lowest_badge(self):
        rows = [offer("Apple iPhone 16 128GB", 50000, "A", availability="Out of stock"), offer("Apple iPhone 16 128GB", 52000, "B", availability="Sold out")]
        result = process_offers("iPhone 16 128GB", rows)
        self.assertTrue(result)
        self.assertFalse(any(item["is_best"] for item in result))

    def test_unknown_stock_does_not_beat_known_in_stock_offer(self):
        rows = [offer("Apple iPhone 16 128GB", 50000, "A", availability="Check retailer"), offer("Apple iPhone 16 128GB", 52000, "B", availability="In stock")]
        result = process_offers("iPhone 16 128GB", rows)
        self.assertFalse(next(item for item in result if item["retailer"] == "A")["is_best"])
        self.assertTrue(next(item for item in result if item["retailer"] == "B")["is_best"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
