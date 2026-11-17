import os
import subprocess
import sys
import unittest


class ProductionConfigSecurityTests(unittest.TestCase):
    def run_config(self, overrides, code="import config; print(config.Config.SECRET_KEY)"):
        env = os.environ.copy()
        env.update(overrides)
        return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)

    def test_production_requires_long_secret(self):
        result = self.run_config({"ENVIRONMENT": "production", "SECRET_KEY": "short"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)

    def test_production_cannot_disable_csrf_secure_cookie_or_debug_guard(self):
        code = "from config import Config; assert Config.CSRF_ENABLED; assert Config.SESSION_COOKIE_SECURE; assert not Config.DEBUG; assert Config.SESSION_COOKIE_NAME == '__Host-costquest-session'"
        result = self.run_config({"ENVIRONMENT": "production", "SECRET_KEY": "x" * 64, "CSRF_ENABLED": "0", "SESSION_COOKIE_SECURE": "0", "FLASK_DEBUG": "1"}, code)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_development_uses_non_secure_local_cookie_by_default(self):
        code = "from config import Config; assert not Config.SESSION_COOKIE_SECURE; assert Config.CSRF_ENABLED; assert not Config.DEBUG"
        result = self.run_config({"ENVIRONMENT": "development", "SECRET_KEY": "", "CSRF_ENABLED": "1", "SESSION_COOKIE_SECURE": "0", "FLASK_DEBUG": "0"}, code)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
