import unittest
from unittest.mock import Mock, patch

import pytest
pytest.importorskip('flask')  # Run these integration tests whenever Flask is installed.
from app import app
from integrations.amazon import AmazonProvider
from integrations.flipkart import FlipkartProvider
from integrations.json_feed import JsonFeedProvider


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.original = app.config.copy()
        app.config.update(
            TESTING=True, REQUEST_TIMEOUT=3,
            AMAZON_CREATOR_CLIENT_ID="test-client", AMAZON_CREATOR_CLIENT_SECRET="test-secret",
            AMAZON_CREATOR_VERSION="3.2", AMAZON_PARTNER_TAG="test-20",
            FLIPKART_AFFILIATE_ID="test-affiliate", FLIPKART_AFFILIATE_TOKEN="test-token",
            CROMA_API_URL="https://feed.example/search", CROMA_API_TOKEN="feed-token",
        )

    def tearDown(self):
        app.config.clear()
        app.config.update(self.original)

    @staticmethod
    def response(payload, status=200):
        result = Mock()
        result.status_code = status
        result.json.return_value = payload
        result.raise_for_status.return_value = None
        return result

    @patch("integrations.json_feed.requests.get")
    def test_unconfigured_json_feed_is_skipped_without_provider_error(self, get):
        app.config["CROMA_API_URL"] = ""
        provider = JsonFeedProvider("Croma", "CROMA_API_URL", "CROMA_API_TOKEN")
        with app.app_context():
            self.assertFalse(provider.status()["configured"])
            self.assertEqual(provider.search("phone"), [])
        get.assert_not_called()

    @patch("integrations.amazon.requests.post")
    def test_amazon_oauth_and_search_mapping(self, post):
        AmazonProvider._token_cache.clear()
        post.side_effect = [
            self.response({"access_token": "token", "expires_in": 3600}),
            self.response({"searchResult": {"items": [{
                "asin": "B0001", "detailPageURL": "https://amazon.in/dp/B0001",
                "itemInfo": {"title": {"displayValue": "Phone 128GB"}},
                "offersV2": {"listings": [{"price": {"money": {"amount": 49999, "currency": "INR"}}}]},
            }]}}),
        ]
        with app.app_context():
            products = AmazonProvider().search("phone")
        self.assertEqual(products[0]["price"], 49999.0)
        self.assertEqual(post.call_args_list[0].args[0], "https://api.amazon.co.uk/auth/o2/token")
        self.assertEqual(post.call_args_list[1].args[0], "https://creatorsapi.amazon/catalog/v1/searchItems")

    @patch("integrations.flipkart.requests.get")
    def test_flipkart_search_mapping(self, get):
        get.return_value = self.response({"productInfoList": [{
            "productBaseInfo": {
                "productAttributes": {
                    "title": "Phone 128GB", "sellingPrice": {"amount": 45999},
                    "productUrl": "https://flipkart.com/item", "imageUrls": {"400x400": "https://img.example/p.jpg"},
                    "productBrand": "Brand", "inStock": True,
                },
                "productIdentifier": {"productId": "FK-1"},
            }
        }]})
        with app.app_context():
            products = FlipkartProvider().search("phone")
        self.assertEqual(products[0]["retailer"], "Flipkart")
        self.assertEqual(products[0]["price"], 45999.0)

    @patch("integrations.json_feed.requests.get")
    def test_authorized_json_feed_mapping(self, get):
        get.return_value = self.response({"products": [{
            "name": "Phone 128GB", "price": 44999, "url": "https://croma.example/p/1", "sku": "C-1",
        }]})
        with app.app_context():
            products = JsonFeedProvider("Croma", "CROMA_API_URL", "CROMA_API_TOKEN").search("phone")
        self.assertEqual(products[0]["price"], 44999.0)
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer feed-token")


if __name__ == "__main__":
    unittest.main(verbosity=2)
