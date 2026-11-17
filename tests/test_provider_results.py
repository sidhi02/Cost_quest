from core.provider_results import deduplicate_provider_offers


def test_provider_results_deduplicate_same_product_url_across_query_variants():
    offers = [
        {"name": "Product", "url": "https://store.example/p/1?utm_source=a", "retailer": "Store"},
        {"name": "Product", "url": "https://store.example/p/1/", "retailer": "Store"},
        {"name": "Different", "url": "https://store.example/p/2", "retailer": "Store"},
    ]
    unique, duplicates = deduplicate_provider_offers(offers)
    assert len(unique) == 2
    assert duplicates == 1


def test_provider_results_keep_same_path_on_different_retailer_hosts():
    offers = [
        {"name": "Product", "url": "https://store-a.example/product/1", "retailer": "A"},
        {"name": "Product", "url": "https://store-b.example/product/1", "retailer": "B"},
    ]
    unique, duplicates = deduplicate_provider_offers(offers)
    assert len(unique) == 2
    assert duplicates == 0


def test_provider_results_without_urls_fall_back_to_retailer_and_sku():
    offers = [
        {"name": "Product", "retailer": "Store", "sku": "A"},
        {"name": "Product", "retailer": "Store", "sku": "A"},
        {"name": "Product", "retailer": "Store", "sku": "B"},
    ]
    unique, duplicates = deduplicate_provider_offers(offers)
    assert len(unique) == 2
    assert duplicates == 1


def test_provider_results_preserve_variant_skus_on_the_same_product_page():
    offers = [
        {"name": "Product Blue", "url": "https://store.example/product/1", "retailer": "Store", "sku": "BLUE"},
        {"name": "Product Red", "url": "https://store.example/product/1", "retailer": "Store", "sku": "RED"},
        {"name": "Product Blue", "url": "https://store.example/product/1?tracking=1", "retailer": "Store", "sku": "BLUE"},
    ]
    unique, duplicates = deduplicate_provider_offers(offers)
    assert len(unique) == 2
    assert duplicates == 1
