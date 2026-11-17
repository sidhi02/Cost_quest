from core.domain_registry import resolve_search_scope, DOMAIN_CATEGORIES
from core.query_expansion import query_variants
from core.matching_engine import process_offers, process_offers_detailed
from services.retailer_directory import retailer_breakdown


def test_all_22_screenshot_queries_route_to_expected_domains_and_categories():
    cases = [
        ("OnePlus 13R 256GB", "electronics", "phones"),
        ("Canon EOS R50 Mirrorless Camera with 18-45mm Lens", "electronics", "cameras"),
        ("Levi's Men's 511 Slim Fit Jeans Waist 32", "fashion", "fashion-clothing"),
        ("Bata Women's Comfit Sandals UK 6", "fashion", "fashion-footwear"),
        ("Havells Instanio 15L Storage Water Heater", "home_appliances", "appliances-water-heaters"),
        ("Prestige PIC 20.0 Induction Cooktop 1600W", "home_appliances", "appliances-kitchen"),
        ("Atomic Habits James Clear Paperback", "books_stationery", "books-fiction"),
        ("SG RSD Xtreme Cricket Bat Size SH", "sports_fitness", "sports-cricket"),
        ("IKEA LACK Coffee Table 90x55 cm", "furniture_home", "home-dining"),
        ("Sleepyhead Original Orthopedic Mattress Queen Size", "furniture_home", "home-mattresses"),
        ("Google Pixel 9a 256GB", "electronics", "phones"),
        ("Dell S2725DS 27-inch QHD Monitor", "electronics", "monitors"),
        ("Nike Revolution 7 Men's Running Shoes UK 9", "sports_fitness", "sports-footwear"),
        ("Allen Solly Men's Regular Fit Cotton Shirt Size 40", "fashion", "fashion-clothing"),
        ("Blue Star 1.5 Ton 3 Star Inverter Split AC", "home_appliances", "appliances-air-conditioners"),
        ("Kent Supreme RO Water Purifier 8L", "home_appliances", "appliances-water-purifiers"),
        ("The Psychology of Money Paperback Morgan Housel", "books_stationery", "books-fiction"),
        ("Arihant Objective General English SP Bakshi Paperback", "books_stationery", "books-exam-prep"),
        ("Nivia Storm Football Size 5", "sports_fitness", "sports-football"),
        ("Decathlon Domyos 500 Exercise Bike", "sports_fitness", "sports-gym-equipment"),
        ("Godrej Interio Slimline 2 Door Steel Wardrobe", "furniture_home", "home-storage"),
        ("Green Soul Jupiter Superb High Back Office Chair", "furniture_home", "home-office-furniture"),
    ]
    for query, domain, category in cases:
        found_domain, found_category = resolve_search_scope(query)
        assert found_domain == domain, query
        assert found_category and found_category["slug"] == category, query


def test_unknown_query_uses_general_shopping_instead_of_electronics_fallback():
    assert resolve_search_scope("specialized industrial component model qx-942") == ("general", None)


def test_domain_query_expansion_preserves_user_query_and_key_configuration():
    variants = query_variants("Blue Star 1.5 Ton 3 Star Inverter Split AC", "home_appliances", "appliances-air-conditioners")
    assert variants[0] == "Blue Star 1.5 Ton 3 Star Inverter Split AC"
    assert len(variants) <= 3
    assert any("1.5" in item for item in variants)
    books = query_variants("The Psychology of Money Paperback Morgan Housel", "books_stationery", "books-fiction")
    assert books[0] == "The Psychology of Money Paperback Morgan Housel"
    assert any("Morgan Housel" in item for item in books)


def test_rejection_diagnostics_report_reasons_per_aggregator():
    candidates = [
        {"name": "Samsung Galaxy S25 256GB", "brand": "Samsung", "price": 59999, "url": "https://shop.example/s25", "retailer": "Store A", "source": "PriceInIndia", "availability": "In stock"},
        {"name": "Samsung Galaxy S25 case", "brand": "Samsung", "price": 499, "url": "https://shop.example/case", "retailer": "Store B", "source": "PriceInIndia", "availability": "In stock"},
    ]
    products, diagnostics = process_offers_detailed("Samsung Galaxy S25 256GB", candidates, "electronics", "phones")
    assert len(products) == 1
    assert diagnostics["mapped"] == 2
    assert diagnostics["accepted"] == 1
    assert diagnostics["rejected"] == 1
    assert diagnostics["rejection_reasons"] == {"accessory_instead_of_product": 1}
    assert diagnostics["by_source"]["PriceInIndia"]["accepted"] == 1
    assert diagnostics["by_source"]["PriceInIndia"]["rejected_samples"][0]["title"] == "Samsung Galaxy S25 case"
    assert diagnostics["by_source"]["PriceInIndia"]["rejected_samples"][0]["reason"] == "accessory_instead_of_product"


def test_retailer_breakdown_does_not_conflate_aggregator_with_storefront():
    result = retailer_breakdown([
        {"retailer": "Croma", "retailer_host": "www.croma.com"},
        {"retailer": "Reliance Digital", "retailer_host": "www.reliancedigital.in"},
        {"retailer": "Croma", "retailer_host": "www.croma.com"},
    ])
    assert result == [{"name": "Croma", "count": 2}, {"name": "Reliance Digital", "count": 1}]


def test_all_22_searches_accept_their_own_query_title_and_reject_unrelated_titles():
    cases = [
        ("OnePlus 13R 256GB", "electronics", "phones"),
        ("Canon EOS R50 Mirrorless Camera with 18-45mm Lens", "electronics", "cameras"),
        ("Levi's Men's 511 Slim Fit Jeans Waist 32", "fashion", "fashion-clothing"),
        ("Bata Women's Comfit Sandals UK 6", "fashion", "fashion-footwear"),
        ("Havells Instanio 15L Storage Water Heater", "home_appliances", "appliances-water-heaters"),
        ("Prestige PIC 20.0 Induction Cooktop 1600W", "home_appliances", "appliances-kitchen"),
        ("Atomic Habits James Clear Paperback", "books_stationery", "books-fiction"),
        ("SG RSD Xtreme Cricket Bat Size SH", "sports_fitness", "sports-cricket"),
        ("IKEA LACK Coffee Table 90x55 cm", "furniture_home", "home-dining"),
        ("Sleepyhead Original Orthopedic Mattress Queen Size", "furniture_home", "home-mattresses"),
        ("Google Pixel 9a 256GB", "electronics", "phones"),
        ("Dell S2725DS 27-inch QHD Monitor", "electronics", "monitors"),
        ("Nike Revolution 7 Men's Running Shoes UK 9", "sports_fitness", "sports-footwear"),
        ("Allen Solly Men's Regular Fit Cotton Shirt Size 40", "fashion", "fashion-clothing"),
        ("Blue Star 1.5 Ton 3 Star Inverter Split AC", "home_appliances", "appliances-air-conditioners"),
        ("Kent Supreme RO Water Purifier 8L", "home_appliances", "appliances-water-purifiers"),
        ("The Psychology of Money Paperback Morgan Housel", "books_stationery", "books-fiction"),
        ("Arihant Objective General English SP Bakshi Paperback", "books_stationery", "books-exam-prep"),
        ("Nivia Storm Football Size 5", "sports_fitness", "sports-football"),
        ("Decathlon Domyos 500 Exercise Bike", "sports_fitness", "sports-gym-equipment"),
        ("Godrej Interio Slimline 2 Door Steel Wardrobe", "furniture_home", "home-storage"),
        ("Green Soul Jupiter Superb High Back Office Chair", "furniture_home", "home-office-furniture"),
    ]
    for index, (query, domain, category) in enumerate(cases):
        offers = [
            {"name": query, "price": 1000 + index, "url": f"https://match.example/{index}", "retailer": "Match Store", "availability": "In stock"},
            {"name": "Unrelated replacement part for an unrelated item", "price": 10, "url": f"https://noise.example/{index}", "retailer": "Noise Store", "availability": "In stock"},
        ]
        matches = process_offers(query, offers, domain, category)
        assert [item["name"] for item in matches] == [query], query


def test_retailer_names_are_normalized_for_store_name_and_host_inputs():
    from services.retailer_directory import canonical_retailer_name
    assert canonical_retailer_name("Croma") == "Croma"
    assert canonical_retailer_name("www.croma.com") == "Croma"
    assert canonical_retailer_name("Reliance Digital") == "Reliance Digital"
    assert canonical_retailer_name("www.reliancedigital.in") == "Reliance Digital"
