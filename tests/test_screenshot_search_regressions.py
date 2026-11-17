from pathlib import Path

from core.query_parser import parse_search
from services.electronics_catalog import _model_signature
from core.matching_engine import process_offers


def test_ten_screenshot_queries_resolve_to_the_intended_domain_and_category():
    expected = [
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
    ]
    for query, domain, category in expected:
        scope = parse_search(query)
        assert (scope["domain"], scope["category"]) == (domain, category), query


def test_oneplus_and_canon_model_signatures_are_specific():
    assert _model_signature("OnePlus 13R 256GB") == "oneplus13r"
    assert _model_signature("OnePlus 13 256GB") == "oneplus13"
    assert _model_signature("Canon EOS R50 Mirrorless Camera") == "canoneosr50"
    assert _model_signature("Canon EOS R10 Mirrorless Camera") == "canoneosr10"


def test_models_from_screenshot_queries_do_not_cross_match():
    oneplus = [
        {"name": "OnePlus 13R 256GB 5G", "price": 39999, "url": "https://shop.example/13r", "brand": "OnePlus", "sku": "13R", "retailer": "Shop"},
        {"name": "OnePlus 13 256GB 5G", "price": 59999, "url": "https://shop.example/13", "brand": "OnePlus", "sku": "13", "retailer": "Shop"},
    ]
    camera = [
        {"name": "Canon EOS R50 Mirrorless Camera 18-45mm", "price": 69999, "url": "https://shop.example/r50", "brand": "Canon", "sku": "R50", "retailer": "Shop"},
        {"name": "Canon EOS R10 Mirrorless Camera 18-45mm", "price": 89999, "url": "https://shop.example/r10", "brand": "Canon", "sku": "R10", "retailer": "Shop"},
    ]
    assert [p["name"] for p in process_offers("OnePlus 13R 256GB", oneplus, "electronics", "phones")] == ["OnePlus 13R 256GB 5G"]
    assert [p["name"] for p in process_offers("Canon EOS R50 Mirrorless Camera with 18-45mm Lens", camera, "electronics", "cameras")] == ["Canon EOS R50 Mirrorless Camera 18-45mm"]


def test_comparison_search_form_auto_detects_and_has_clear_control():
    template = (Path(__file__).parents[1] / "templates" / "compare.html").read_text()
    assert 'name="domain"' not in template
    assert 'name="category"' not in template
    assert 'class="search-clear"' in template


def test_homepage_shows_all_six_domains_without_technical_pipeline():
    template = (Path(__file__).parents[1] / "templates" / "index.html").read_text()
    assert "One comparison platform. Six domains." not in template
    assert "Six product domains" not in template
    assert "EXPLORE EVERY CATEGORY" in template
    assert "shop-domains" in template
    assert "AI matching pipeline" not in template
    assert 'name="domain"' not in template
    assert 'class="search-clear"' in template


def test_no_results_template_uses_clear_explanation_and_review_section():
    template = (Path(__file__).parents[1] / "templates" / "compare.html").read_text()
    assert 'class="cq-empty"' in template
    assert "No verified offers found" in template
    assert "need specification verification" in template


def test_single_offer_is_not_misrepresented_as_a_price_comparison():
    offers = [{"name": "Sleepyhead Original Orthopedic Mattress Queen Size", "price": 12219, "url": "https://shop.example/mattress", "brand": "Sleepyhead", "sku": "MATTRESS-Q", "retailer": "Amazon", "availability": "Available"}]
    result = process_offers("Sleepyhead Original Orthopedic Mattress Queen Size", offers, "furniture_home", "home-mattresses")
    assert len(result) == 1
    assert result[0]["comparison_count"] == 1
    assert result[0]["is_best"] is False


def test_model_specific_home_appliance_query_rejects_generic_listing():
    offers = [{"name": "Induction Cooktop by Prestige - 1600W", "price": 2998, "url": "https://shop.example/pic", "brand": "Prestige", "sku": "PIC-GENERIC", "retailer": "Flipkart", "availability": "Available", "attributes": {"power_w": 1600, "appliance_type": "induction cooktop"}}]
    result = process_offers("Prestige PIC 20.0 Induction Cooktop 1600W", offers, "home_appliances", "appliances-kitchen")
    assert result == []


def test_queen_mattress_query_rejects_listing_without_confirmed_size():
    offers = [{"name": "Orthopedic Memory Foam Mattress by Sleepyhead - Original", "price": 12219, "url": "https://shop.example/mattress", "brand": "Sleepyhead", "sku": "MATTRESS", "retailer": "Amazon", "availability": "Available"}]
    result = process_offers("Sleepyhead Original Orthopedic Mattress Queen Size", offers, "furniture_home", "home-mattresses")
    assert result == []
