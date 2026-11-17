import os
import tempfile
import unittest
from unittest.mock import patch

import pytest
pytest.importorskip('flask')  # Run these integration tests whenever Flask is installed.
from app import app
from integrations.base import Provider


class FakeProvider(Provider):
    name = "Test Store"

    def status(self):
        from flask import current_app
        current_app.config.get("TESTING")
        return {"name": self.name, "configured": True, "message": "Ready"}

    def search(self, query):
        from flask import current_app
        current_app.config.get("TESTING")
        return [self.product("Apple iPhone 16 128GB", 69999, "https://store.example/iphone", retailer=self.name, sku="sku-1")]


class FailingProvider(FakeProvider):
    name = "Broken Store"

    def search(self, query):
        raise RuntimeError("internal details must not leak")


class AggregatorProvider(Provider):
    name = "PriceInIndia"

    def status(self):
        return {"name": self.name, "configured": True, "role": "Marketplace aggregator", "message": "Ready"}

    def search(self, query):
        product = self.product("Android Phone 128GB", 14999, "https://croma.example/phone", retailer="Croma", sku="croma-1")
        product["source"] = "PriceInIndia"
        return [product]


class UnconfiguredProvider(Provider):
    name = "Unconfigured Retailer"

    def status(self):
        return {"name": self.name, "configured": False, "message": "Credentials required"}

    def search(self, query):
        raise AssertionError("Unconfigured providers must not be searched")


class CostQuestTests(unittest.TestCase):
    def setUp(self):
        handle, self.db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        app.config.update(TESTING=True, CSRF_ENABLED=True, DATABASE_PATH=self.db_path, SECRET_KEY="test-secret")
        with app.app_context():
            from database import init_db
            init_db()
        self.client = app.test_client()

    def csrf_token(self):
        with self.client.session_transaction() as session:
            token = session.get("_csrf_token")
            if not token:
                token = "test-csrf-token"
                session["_csrf_token"] = token
        return token

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.unlink(self.db_path + suffix)
            except FileNotFoundError:
                pass

    def test_home_renders_generic_store_focused_experience(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Cost Quest", response.data)
        self.assertIn(b"EXPLORE EVERY CATEGORY", response.data)
        self.assertIn(b'class="search-clear"', response.data)
        self.assertNotIn(b"One comparison platform. Six domains.", response.data)
        self.assertNotIn(b'name="domain"', response.data)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["application"], "Cost Quest")

    def test_post_rejects_missing_csrf(self):
        self.assertEqual(self.client.post("/watchlist/add", data={}).status_code, 400)

    @patch("services.comparison.search_products", return_value=([], []))
    def test_compare_form_uses_auto_detection_and_has_clear_control(self, _):
        response = self.client.get("/compare?q=OnePlus+13R+256GB")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="search-clear"', response.data)
        self.assertNotIn(b'name="domain"', response.data)
        self.assertNotIn(b'name="category"', response.data)

    @patch("services.comparison.search_products", return_value=([], []))
    def test_no_results_state_is_visually_marked_as_an_error_like_status(self, _):
        response = self.client.get("/compare?q=unmatched+product")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="cq-empty"', response.data)
        self.assertIn(b'No verified offers found', response.data)

    def test_search_requires_query(self):
        self.assertEqual(self.client.get("/api/search").status_code, 400)

    def test_empty_compare_redirects(self):
        self.assertEqual(self.client.get("/compare?q=").status_code, 302)

    @patch("services.comparison.configured_providers", return_value=[FakeProvider()])
    def test_api_search_and_history_snapshot(self, _):
        response = self.client.get("/api/search?q=iphone+16")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["products"]), 1)
        product = response.json["products"][0]
        self.assertEqual(product["price"], 69999.0)
        history = self.client.get(f"/history/{product['product_key']}")
        self.assertEqual(history.status_code, 200)
        self.assertIn(b"69,999.00", history.data)

    @patch("services.comparison.configured_providers", return_value=[AggregatorProvider(), UnconfiguredProvider()])
    def test_provider_cards_separate_aggregator_offers_from_retailer_storefronts(self, _):
        response = self.client.get("/api/search?q=phone")
        self.assertEqual(response.status_code, 200)
        statuses = {item["name"]: item for item in response.json["providers"]}
        self.assertEqual(statuses["PriceInIndia"]["role"], "Marketplace aggregator")
        self.assertEqual(statuses["PriceInIndia"]["mapped_count"], 1)
        self.assertEqual(statuses["PriceInIndia"]["accepted_count"], 1)
        self.assertEqual(statuses["Unconfigured Retailer"]["state"], "not_configured")
        self.assertEqual(statuses["Unconfigured Retailer"]["message"], "Not connected · search skipped")
        self.assertEqual(response.json["retailer_sources"], [{"name": "Croma", "count": 1}])

    @patch("services.comparison.configured_providers", return_value=[FakeProvider(), FailingProvider()])
    def test_provider_failure_is_isolated_and_sanitized(self, _):
        response = self.client.get("/api/search?q=iphone")
        self.assertEqual(response.status_code, 200)
        statuses = {item["name"]: item for item in response.json["providers"]}
        self.assertEqual(statuses["Test Store"]["error"], False)
        self.assertEqual(statuses["Broken Store"]["message"], "Provider integration error")
        self.assertNotIn("internal details", str(response.json))

    def register_user(self, email="student@example.com"):
        self.client.get("/register")
        response = self.client.post("/register", data={"email": email, "password": "Correct-Horse-42!", "confirm_password": "Correct-Horse-42!", "csrf_token": self.csrf_token()})
        self.assertEqual(response.status_code, 302)

    def test_registration_login_logout_and_watchlist_gate(self):
        self.assertEqual(self.client.get("/watchlist").status_code, 302)
        self.client.get("/register")
        response = self.client.post("/register", data={"email": "user@example.com", "password": "Correct-Horse-42!", "confirm_password": "Correct-Horse-42!", "csrf_token": self.csrf_token()})
        self.assertEqual(response.status_code, 302)
        self.assertIn(b"My account", self.client.get("/").data)
        self.assertEqual(self.client.post("/logout", data={"csrf_token": self.csrf_token()}).status_code, 302)
        self.client.get("/login")
        response = self.client.post("/login", data={"email": "user@example.com", "password": "Correct-Horse-42!", "csrf_token": self.csrf_token()})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/watchlist").status_code, 200)

    @patch("services.comparison.configured_providers", return_value=[FakeProvider()])
    def test_watchlist_add_and_remove(self, _):
        self.register_user()
        response = self.client.get("/api/search?q=iphone")
        product = response.json["products"][0]
        added = self.client.post("/watchlist/add", data={
            "product_key": product["product_key"], "name": product["name"],
            "retailer": product["retailer"], "url": product["url"], "csrf_token": self.csrf_token(),
        })
        self.assertEqual(added.status_code, 302)
        page = self.client.get("/watchlist")
        self.assertIn(b"Apple iPhone 16 128GB", page.data)
        from database import get_watchlist
        with self.client.session_transaction() as session:
            user_id = session["user_id"]
        with app.app_context():
            item_id = get_watchlist(user_id)[0]["id"]
        removed = self.client.post(f"/watchlist/{item_id}/remove", data={"csrf_token": self.csrf_token()})
        self.assertEqual(removed.status_code, 302)
        self.assertEqual(self.client.get("/watchlist").status_code, 200)
        self.assertNotIn(b"Apple iPhone 16 128GB", self.client.get("/watchlist").data)

    @patch("services.comparison.configured_providers", return_value=[FakeProvider()])
    def test_guest_watch_action_is_saved_after_login(self, _):
        product = self.client.get("/api/search?q=iphone").json["products"][0]
        response = self.client.post("/watchlist/add", data={
            "product_key": product["product_key"], "name": product["name"], "retailer": product["retailer"], "url": product["url"], "csrf_token": self.csrf_token(),
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)
        self.client.get(response.location)
        self.client.post("/register", data={"email": "watch@example.com", "password": "Correct-Horse-42!", "confirm_password": "Correct-Horse-42!", "csrf_token": self.csrf_token()})
        self.assertIn(b"Apple iPhone 16 128GB", self.client.get("/watchlist").data)


    def test_auth_pages_send_no_store_and_security_headers(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("default-src 'self'", response.headers.get("Content-Security-Policy", ""))

    def test_registration_persists_only_password_hash(self):
        self.register_user("hash-check@example.com")
        with app.app_context():
            from database import connect
            with connect() as db:
                stored = db.execute("SELECT password_hash FROM users WHERE email=?", ("hash-check@example.com",)).fetchone()[0]
        self.assertNotEqual(stored, "Correct-Horse-42!")
        self.assertTrue(stored.startswith("scrypt:32768:8:1$"))

    def test_production_configuration_rejects_disabled_security_controls(self):
        from app import create_app
        class UnsafeProductionConfig:
            ENVIRONMENT = "production"
            SECRET_KEY = "x" * 64
            CSRF_ENABLED = False
            SESSION_COOKIE_SECURE = False
            DEBUG = True
            DATABASE_PATH = self.db_path
        with self.assertRaises(RuntimeError):
            create_app(UnsafeProductionConfig)


    def test_production_session_cookie_uses_host_prefix_and_secure_flags(self):
        from app import create_app
        class ProductionConfig:
            ENVIRONMENT = "production"
            SECRET_KEY = "s" * 64
            CSRF_ENABLED = True
            SESSION_COOKIE_SECURE = True
            DEBUG = False
            DATABASE_PATH = self.db_path
        production_app = create_app(ProductionConfig)
        response = production_app.test_client().get("/login")
        cookie = " ".join(response.headers.getlist("Set-Cookie"))
        self.assertIn("__Host-costquest-session=", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("Strict-Transport-Security", response.headers)

    def test_next_parameter_rejects_external_redirect(self):
        response = self.client.get("/login?next=https://attacker.example")
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            session["_csrf_token"] = "safe-next-test"
        response = self.client.post("/login?next=https://attacker.example", data={
            "email": "missing@example.com", "password": "not-the-password", "csrf_token": "safe-next-test"
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("attacker.example", response.get_data(as_text=True))

    def test_product_validation_rejects_invalid_values(self):
        self.assertIsNone(Provider.product("", 100, "https://store.example/p"))
        self.assertIsNone(Provider.product("Phone", float("nan"), "https://store.example/p"))
        self.assertIsNone(Provider.product("Phone", 100, "javascript:alert(1)"))
        self.assertIsNone(Provider.product("Phone", 100, "https://store.example/p", currency="USD"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
