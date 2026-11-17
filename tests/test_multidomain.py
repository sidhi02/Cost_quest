import unittest

from core.domain_registry import ALL_CATEGORIES, DOMAIN_INDEX, resolve_search_scope
from core.query_parser import parse_search
from services.product_intelligence import process_offers


def offer(name, price=1000, retailer="Store", path=None, brand="", attributes=None, availability="In stock"):
    slug = retailer.lower().replace(" ", "")
    return {"name": name, "brand": brand, "price": price, "retailer": retailer, "url": f"https://{slug}.example/{path or abs(hash(name))}", "availability": availability, "attributes": attributes or {}}


class DomainRegistryTests(unittest.TestCase):
    def test_six_domains_are_registered(self):
        self.assertEqual(set(DOMAIN_INDEX), {"electronics", "fashion", "home_appliances", "books_stationery", "sports_fitness", "furniture_home"})
        self.assertGreaterEqual(len(ALL_CATEGORIES), 55)

    def test_domain_detection(self):
        cases = [
            ("Samsung Galaxy S26", "electronics"),
            ("Nike running shoes UK 8", "sports_fitness"),
            ("LG 1.5 ton inverter AC", "home_appliances"),
            ("NCERT Class 10 Science textbook", "books_stationery"),
            ("Queen size mattress", "furniture_home"),
            ("Zara cotton shirt size M", "fashion"),
        ]
        for query, expected in cases:
            with self.subTest(query=query): self.assertEqual(resolve_search_scope(query)[0], expected)

    def test_explicit_domain_is_respected_for_ambiguous_queries(self):
        self.assertEqual(parse_search("watch", "fashion")["domain"], "fashion")
        self.assertEqual(parse_search("watch", "electronics")["domain"], "electronics")


class FashionMatchingTests(unittest.TestCase):
    def test_shoe_size_and_brand_are_hard_constraints(self):
        rows = [offer("Nike Men's Running Shoes UK 8", retailer="A"), offer("Nike Men's Running Shoes UK 9", retailer="B"), offer("Adidas Men's Running Shoes UK 8", retailer="C")]
        result = process_offers("Nike running shoes UK 8 men", rows, domain="fashion", category="fashion-footwear")
        self.assertEqual([row["name"] for row in result], ["Nike Men's Running Shoes UK 8"])

    def test_clothing_size_and_material_are_checked(self):
        rows = [offer("Zara Women's Cotton Shirt Size M", retailer="A"), offer("Zara Women's Cotton Shirt Size L", retailer="B"), offer("Zara Women's Linen Shirt Size M", retailer="C")]
        result = process_offers("Zara women's cotton shirt size M", rows, domain="fashion", category="fashion-clothing")
        self.assertEqual([row["name"] for row in result], ["Zara Women's Cotton Shirt Size M"])

    def test_title_word_order_does_not_prevent_equivalent_offer_grouping(self):
        rows = [
            offer("Nike Men's Revolution 6 Running Shoes UK 8", 4999, "Store A", "one"),
            offer("Nike Revolution 6 Men's Running Shoes UK Size 8", 4599, "Store B", "two"),
        ]
        result = process_offers("Nike Revolution 6 men's running shoes UK 8", rows, domain="fashion", category="fashion-footwear")
        self.assertEqual(len(result), 2)
        self.assertEqual({row["comparison_key"] for row in result}, {result[0]["comparison_key"]})
        self.assertEqual([row["name"] for row in result if row["is_best"]], ["Nike Revolution 6 Men's Running Shoes UK Size 8"])


class HomeApplianceMatchingTests(unittest.TestCase):
    def test_ac_tonnage_and_inverter_type_are_checked(self):
        rows = [offer("LG 1.5 Ton Inverter Split AC", retailer="A"), offer("LG 2 Ton Inverter Split AC", retailer="B"), offer("LG 1.5 Ton Non Inverter Split AC", retailer="C")]
        result = process_offers("LG 1.5 ton inverter AC", rows, domain="home_appliances", category="appliances-air-conditioners")
        self.assertEqual([row["name"] for row in result], ["LG 1.5 Ton Inverter Split AC"])

    def test_washing_machine_capacity_and_load_type_are_checked(self):
        rows = [offer("Samsung 8kg Front Load Washing Machine", retailer="A"), offer("Samsung 9kg Front Load Washing Machine", retailer="B"), offer("Samsung 8kg Top Load Washing Machine", retailer="C")]
        result = process_offers("Samsung 8kg front load washing machine", rows, domain="home_appliances", category="appliances-washing-machines")
        self.assertEqual([row["name"] for row in result], ["Samsung 8kg Front Load Washing Machine"])


class BooksMatchingTests(unittest.TestCase):
    def test_isbn_is_exact_identity(self):
        rows = [offer("Engineering Mathematics Textbook ISBN 9789355731234", retailer="A"), offer("Engineering Mathematics Textbook ISBN 9789355731235", retailer="B")]
        result = process_offers("Engineering Mathematics textbook ISBN 9789355731234", rows, domain="books_stationery", category="books-textbooks")
        self.assertEqual([row["name"] for row in result], ["Engineering Mathematics Textbook ISBN 9789355731234"])

    def test_edition_and_format_are_preserved(self):
        rows = [offer("Operating Systems 4th Edition Paperback", retailer="A"), offer("Operating Systems 3rd Edition Paperback", retailer="B"), offer("Operating Systems 4th Edition Hardcover", retailer="C")]
        result = process_offers("Operating Systems 4th edition paperback", rows, domain="books_stationery", category="books-textbooks")
        self.assertEqual([row["name"] for row in result], ["Operating Systems 4th Edition Paperback"])


class SportsMatchingTests(unittest.TestCase):
    def test_equipment_weight_is_hard_constraint(self):
        rows = [offer("5kg Cast Iron Dumbbell", retailer="A"), offer("10kg Cast Iron Dumbbell", retailer="B")]
        result = process_offers("5kg dumbbell", rows, domain="sports_fitness", category="sports-gym-equipment")
        self.assertEqual([row["name"] for row in result], ["5kg Cast Iron Dumbbell"])

    def test_badminton_racket_does_not_match_shuttlecock(self):
        rows = [offer("Yonex Badminton Racket", retailer="A"), offer("Yonex Nylon Shuttlecock", retailer="B")]
        result = process_offers("Yonex badminton racket", rows, domain="sports_fitness", category="sports-badminton")
        self.assertEqual([row["name"] for row in result], ["Yonex Badminton Racket"])

    def test_exercise_bike_search_rejects_replacement_pedals(self):
        rows = [offer("Decathlon Domyos 500 Exercise Bike", retailer="A"), offer("Decathlon Domyos 500 Exercise Bike Replacement Pedal", retailer="B")]
        result = process_offers("Decathlon Domyos 500 Exercise Bike", rows, domain="sports_fitness", category="sports-gym-equipment")
        self.assertEqual([row["name"] for row in result], ["Decathlon Domyos 500 Exercise Bike"])


class FurnitureMatchingTests(unittest.TestCase):
    def test_mattress_sizes_are_separate(self):
        rows = [offer("Wakefit Queen Size Memory Foam Mattress", retailer="A"), offer("Wakefit King Size Memory Foam Mattress", retailer="B")]
        result = process_offers("Wakefit queen size mattress", rows, domain="furniture_home", category="home-mattresses")
        self.assertEqual([row["name"] for row in result], ["Wakefit Queen Size Memory Foam Mattress"])

    def test_material_is_checked_when_requested(self):
        rows = [offer("Sheesham Solid Wood Dining Table", retailer="A"), offer("Engineered Wood Dining Table", retailer="B")]
        result = process_offers("Sheesham solid wood dining table", rows, domain="furniture_home", category="home-dining")
        self.assertEqual([row["name"] for row in result], ["Sheesham Solid Wood Dining Table"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
