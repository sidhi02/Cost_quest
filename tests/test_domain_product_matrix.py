import unittest

from core.domain_registry import DOMAIN_CATEGORIES, resolve_search_scope
from services.product_intelligence import process_offers


def make_offer(name, retailer, path, price=4999, availability="In stock"):
    return {
        "name": name, "brand": "", "price": price,
        "url": f"https://{retailer.lower().replace(' ', '')}.example/{path}",
        "retailer": retailer, "currency": "INR", "availability": availability,
    }


PRODUCT_CASES = [
    ("fashion", "fashion-clothing", "Zara women's cotton shirt size M", "Zara Women's Cotton Shirt Size M", "Zara Women's Cotton Shirt Size L"),
    ("fashion", "fashion-footwear", "Nike men's running shoes UK 8", "Nike Men's Revolution 6 Running Shoes UK 8", "Nike Men's Revolution 6 Running Shoes UK 9"),
    ("fashion", "fashion-bags", "American Tourister 55cm cabin suitcase", "American Tourister 55cm cabin suitcase", "American Tourister 75cm large suitcase"),
    ("fashion", "fashion-watches", "Casio analog wrist watch", "Casio analog wrist watch", "Casio digital wrist watch"),
    ("fashion", "fashion-eyewear", "Ray-Ban polarized sunglasses", "Ray-Ban polarized sunglasses", "Ray-Ban eyeglasses optical frame"),
    ("fashion", "fashion-jewellery", "silver ring size 7", "Silver ring size 7", "Silver ring size 8"),
    ("fashion", "fashion-beauty", "Nivea moisturizer 100ml", "Nivea moisturizer 100ml", "Nivea moisturizer 200ml"),
    ("home_appliances", "appliances-refrigerators", "LG 260 litre frost free refrigerator", "LG 260 litre frost free refrigerator", "LG 300 litre frost free refrigerator"),
    ("home_appliances", "appliances-washing-machines", "Samsung 8kg front load washing machine", "Samsung 8kg front load washing machine", "Samsung 9kg front load washing machine"),
    ("home_appliances", "appliances-air-conditioners", "Daikin 1.5 ton 5 star inverter split AC", "Daikin 1.5 ton 5 star inverter split AC", "Daikin 2 ton 5 star inverter split AC"),
    ("home_appliances", "appliances-microwaves-ovens", "IFB 30 litre convection microwave oven", "IFB 30 litre convection microwave oven", "IFB 23 litre convection microwave oven"),
    ("home_appliances", "appliances-dishwashers", "Bosch 13 place setting dishwasher", "Bosch 13 place setting dishwasher", "Bosch 14 place setting dishwasher"),
    ("home_appliances", "appliances-vacuum-cleaners", "Dyson V8 cordless vacuum cleaner", "Dyson V8 cordless vacuum cleaner", "Dyson V8 replacement filter"),
    ("home_appliances", "appliances-kitchen", "Prestige 5 litre air fryer", "Prestige 5 litre air fryer", "Prestige 3 litre air fryer"),
    ("home_appliances", "appliances-water-purifiers", "Kent RO 8 litre water purifier", "Kent RO 8 litre water purifier", "Kent RO replacement filter"),
    ("home_appliances", "appliances-water-heaters", "Havells 15 litre water heater geyser", "Havells 15 litre water heater geyser", "Havells 25 litre water heater geyser"),
    ("home_appliances", "appliances-air-purifiers", "Philips AC1711 air purifier", "Philips AC1711 air purifier", "Philips air purifier replacement filter"),
    ("books_stationery", "books-textbooks", "Engineering Mathematics textbook 5th edition paperback", "Engineering Mathematics textbook 5th edition paperback", "Engineering Mathematics textbook 4th edition paperback"),
    ("books_stationery", "books-exam-prep", "Arihant JEE Main previous year question bank", "Arihant JEE Main previous year question bank", "Arihant NEET previous year question bank"),
    ("books_stationery", "books-fiction", "Penguin The Alchemist paperback", "Penguin The Alchemist paperback", "Penguin The Alchemist audiobook"),
    ("books_stationery", "books-reference", "Oxford English dictionary hardcover", "Oxford English dictionary hardcover", "Oxford English dictionary paperback"),
    ("books_stationery", "stationery-notebooks", "Classmate 200 page ruled notebook pack of 5", "Classmate 200 page ruled notebook pack of 5", "Classmate 200 page ruled notebook pack of 10"),
    ("books_stationery", "stationery-writing", "Parker Vector blue ink ball pen pack of 2", "Parker Vector blue ink ball pen pack of 2", "Parker Vector blue ink fountain pen pack of 2"),
    ("books_stationery", "stationery-art", "Faber Castell colour pencil set 24 pieces", "Faber Castell colour pencil set 24 pieces", "Faber Castell colour pencil set 12 pieces"),
    ("books_stationery", "stationery-office", "Casio scientific calculator FX-991EX", "Casio scientific calculator FX-991EX", "Casio basic calculator MJ-12"),
    ("sports_fitness", "sports-gym-equipment", "5kg cast iron dumbbell", "5kg cast iron dumbbell", "10kg cast iron dumbbell"),
    ("sports_fitness", "sports-footwear", "Nike running shoes UK 8", "Nike running shoes UK 8", "Nike running shoes UK 9"),
    ("sports_fitness", "sports-cycling", "Hero mountain bicycle 21 speed", "Hero mountain bicycle 21 speed", "Hero road bicycle 18 speed"),
    ("sports_fitness", "sports-yoga", "Decathlon yoga mat 6mm", "Decathlon yoga mat 6mm", "Decathlon yoga mat 10mm"),
    ("sports_fitness", "sports-cricket", "SG cricket bat size SH English willow", "SG cricket bat size SH English willow", "SG cricket ball leather red"),
    ("sports_fitness", "sports-badminton", "Yonex badminton racket graphite", "Yonex badminton racket graphite", "Yonex nylon shuttlecock"),
    ("sports_fitness", "sports-football", "Nivia football size 5", "Nivia football size 5", "Nivia football size 4"),
    ("sports_fitness", "sports-protection", "Decathlon boxing gloves 12oz", "Decathlon boxing gloves 12oz", "Decathlon boxing gloves 16oz"),
    ("furniture_home", "home-sofas-seating", "Wakefit 3 seater fabric sofa", "Wakefit 3 seater fabric sofa", "Wakefit 2 seater fabric sofa"),
    ("furniture_home", "home-beds", "Godrej queen size bed frame solid wood", "Godrej queen size bed frame solid wood", "Godrej king size bed frame solid wood"),
    ("furniture_home", "home-mattresses", "Wakefit queen size memory foam mattress", "Wakefit queen size memory foam mattress", "Wakefit king size memory foam mattress"),
    ("furniture_home", "home-dining", "IKEA 6 seater solid wood dining table", "IKEA 6 seater solid wood dining table", "IKEA 4 seater solid wood dining table"),
    ("furniture_home", "home-office-furniture", "Green Soul ergonomic office chair", "Green Soul ergonomic office chair", "Green Soul study table"),
    ("furniture_home", "home-storage", "Godrej 3 door wardrobe engineered wood", "Godrej 3 door wardrobe engineered wood", "Godrej 2 door wardrobe engineered wood"),
    ("furniture_home", "home-lighting", "Philips LED ceiling light 24W", "Philips LED ceiling light 24W", "Philips LED table lamp 24W"),
    ("furniture_home", "home-decor", "D'Decor cotton bedsheet queen size", "D'Decor cotton bedsheet queen size", "D'Decor cotton bedsheet king size"),
]


ELECTRONICS_CASES = [
    ("phones", "Samsung Galaxy S26 256GB", "Samsung Galaxy S26 256GB", "Samsung Galaxy S26 phone case"),
    ("laptops", "Dell XPS 13 laptop", "Dell XPS 13 laptop 16GB", "Dell 27 inch monitor"),
    ("tablets", "iPad Air M3 11 inch tablet", "Apple iPad Air M3 11 inch Wi-Fi tablet", "Apple MacBook Air M3"),
    ("monitors", "Samsung 27 inch 144Hz monitor", "Samsung 27 inch 144Hz gaming monitor", "Samsung 55 inch OLED TV"),
    ("audio", "Sony WH-1000XM5 headphones", "Sony WH-1000XM5 wireless headphones", "Sony WH-1000XM5 ear pads"),
    ("chargers-cables", "Samsung 45W USB-C charger", "Samsung 45W USB-C wall charger", "Samsung USB-C cable"),
    ("components", "NVIDIA RTX 5070 graphics card", "MSI NVIDIA RTX 5070 12GB graphics card", "MSI NVIDIA RTX 5060 12GB graphics card"),
    ("storage", "WD 1TB external hard drive", "WD 1TB external hard drive portable", "WD 1TB internal SSD"),
    ("tv", "Samsung 55 inch OLED TV", "Samsung 55 inch OLED Smart TV", "Samsung Galaxy S25 phone"),
    ("cameras", "Canon mirrorless camera", "Canon EOS R50 mirrorless camera", "Canon LaserJet printer"),
    ("wearables", "Apple Watch Series 10 smartwatch", "Apple Watch Series 10 GPS smartwatch", "Apple Watch Series 10 strap"),
    ("gaming", "PlayStation 5 Slim Disc Edition", "Sony PlayStation 5 Slim Disc Edition Console", "Sony PlayStation 5 Slim Digital Edition"),
    ("printers", "HP LaserJet printer", "HP LaserJet Pro printer", "HP LaserJet toner cartridge"),
    ("networking", "TP-Link Archer AX55 router", "TP-Link Archer AX55 AX3000 Wi-Fi 6 router", "TP-Link Archer AX50 router"),
    ("peripherals", "Logitech wireless mouse", "Logitech MX Master 3S wireless mouse", "Logitech wireless keyboard"),
    ("ups-power", "APC 1100VA UPS", "APC 1100VA UPS power backup", "APC 1500VA UPS power backup"),
    ("smart-home", "Philips Hue smart bulb", "Philips Hue smart bulb E27", "Philips CCTV security camera"),
    ("appliances", "Philips electric shaver", "Philips electric shaver trimmer", "Philips replacement shaver blades"),
    ("wearable-accessories", "Apple Watch sport band", "Apple Watch sport band 42mm", "Apple Watch Series 10 smartwatch"),
    ("phone-accessories", "Samsung Galaxy S26 phone case", "Samsung Galaxy S26 protective phone case", "Samsung Galaxy S26 256GB smartphone"),
]


class ProductMatrixTests(unittest.TestCase):
    def test_all_category_terms_are_accepted_in_explicit_scope(self):
        tested = 0
        for domain, categories in DOMAIN_CATEGORIES.items():
            for category in categories:
                for term in category.get("terms", []):
                    tested += 1
                    product = make_offer(f"Generic {term} product", "Store", f"term/{tested}")
                    with self.subTest(domain=domain, category=category["slug"], term=term):
                        result = process_offers(term, [product], domain=domain, category=category["slug"])
                        self.assertEqual(len(result), 1)
        self.assertEqual(tested, 451)

    def test_each_non_electronics_category_rejects_a_materially_different_variant(self):
        self.assertEqual(len(PRODUCT_CASES), 41)
        for index, (domain, category, query, expected, rejected) in enumerate(PRODUCT_CASES, 1):
            offers = [make_offer(expected, "Store A", f"matrix/{index}/good"), make_offer(rejected, "Store B", f"matrix/{index}/bad", 3999)]
            with self.subTest(domain=domain, category=category, query=query):
                names = [item["name"] for item in process_offers(query, offers, domain=domain, category=category)]
                self.assertIn(expected, names)
                self.assertNotIn(rejected, names)

    def test_all_electronics_categories_reject_wrong_product_types_and_variants(self):
        self.assertEqual(len(ELECTRONICS_CASES), 20)
        for index, (category, query, expected, rejected) in enumerate(ELECTRONICS_CASES, 1):
            offers = [make_offer(expected, "Store A", f"electronics/{index}/good"), make_offer(rejected, "Store B", f"electronics/{index}/bad", 3999)]
            with self.subTest(category=category, query=query):
                names = [item["name"] for item in process_offers(query, offers, domain="electronics", category=category)]
                self.assertIn(expected, names)
                self.assertNotIn(rejected, names)

    def test_shared_term_auto_detection_prefers_home_appliances_for_clear_appliance_searches(self):
        for query in ("vacuum cleaner", "robot vacuum", "air purifier", "induction cooktop"):
            with self.subTest(query=query):
                self.assertEqual(resolve_search_scope(query)[0], "home_appliances")

    def test_accessories_are_rejected_from_device_searches(self):
        cases = [
            ("electronics", "phones", "Samsung Galaxy S26 256GB", "Samsung Galaxy S26 phone case"),
            ("fashion", "fashion-footwear", "Nike running shoes UK 8", "Nike replacement shoelaces"),
            ("home_appliances", "appliances-vacuum-cleaners", "Dyson V8 vacuum cleaner", "Dyson V8 replacement filter"),
            ("books_stationery", "books-textbooks", "Engineering Mathematics textbook", "Engineering Mathematics book cover"),
            ("sports_fitness", "sports-badminton", "Yonex badminton racket", "Yonex racket cover"),
            ("furniture_home", "home-sofas-seating", "Wakefit fabric sofa", "Wakefit sofa cover"),
        ]
        for index, (domain, category, query, rejected) in enumerate(cases, 1):
            product = make_offer(rejected, "Store", f"accessory/{index}")
            with self.subTest(domain=domain, query=query):
                self.assertEqual(process_offers(query, [product], domain=domain, category=category), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
