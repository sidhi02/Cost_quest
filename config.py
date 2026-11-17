import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
_SECRET = os.getenv("SECRET_KEY", "")
_IS_PRODUCTION = ENVIRONMENT == "production"
if _IS_PRODUCTION and len(_SECRET) < 32:
    raise RuntimeError("Production SECRET_KEY must contain at least 32 characters; use a cryptographically random value")


class Config:
    ENVIRONMENT = ENVIRONMENT
    SECRET_KEY = _SECRET or "cost-quest-local-development-key-change-before-deploy"
    CSRF_ENABLED = True if _IS_PRODUCTION else os.getenv("CSRF_ENABLED", "1").lower() not in {"0", "false", "no"}
    DEBUG = False if _IS_PRODUCTION else os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    SESSION_COOKIE_NAME = "__Host-costquest-session" if _IS_PRODUCTION else "costquest-session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True if _IS_PRODUCTION else os.getenv("SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_PATH = "/"
    SESSION_COOKIE_DOMAIN = None
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    PREFERRED_URL_SCHEME = "https" if _IS_PRODUCTION else "http"
    MAX_CONTENT_LENGTH = 1024 * 1024
    MAX_PROVIDER_WORKERS = max(1, min(8, int(os.getenv("MAX_PROVIDER_WORKERS", "5"))))
    SEARCH_RATE_LIMIT = max(1, int(os.getenv("SEARCH_RATE_LIMIT", "60")))
    SEARCH_RATE_WINDOW = max(1, int(os.getenv("SEARCH_RATE_WINDOW", "60")))
    AUTH_RATE_LIMIT = max(1, int(os.getenv("AUTH_RATE_LIMIT", "10")))
    AUTH_IP_RATE_LIMIT = max(1, int(os.getenv("AUTH_IP_RATE_LIMIT", "50")))
    AUTH_RATE_WINDOW = max(60, int(os.getenv("AUTH_RATE_WINDOW", "900")))
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "instance" / "costquest.sqlite3"))
    REQUEST_TIMEOUT = max(2.0, min(60.0, float(os.getenv("REQUEST_TIMEOUT", "15"))))
    FLIPKART_AFFILIATE_ID = os.getenv("FLIPKART_AFFILIATE_ID", "")
    FLIPKART_AFFILIATE_TOKEN = os.getenv("FLIPKART_AFFILIATE_TOKEN", "")
    AMAZON_CREATOR_CLIENT_ID = os.getenv("AMAZON_CREATOR_CLIENT_ID", "")
    AMAZON_CREATOR_CLIENT_SECRET = os.getenv("AMAZON_CREATOR_CLIENT_SECRET", "")
    AMAZON_CREATOR_VERSION = os.getenv("AMAZON_CREATOR_VERSION", "3.2")
    AMAZON_PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG", "")
    CROMA_API_URL = os.getenv("CROMA_API_URL", "")
    CROMA_API_TOKEN = os.getenv("CROMA_API_TOKEN", "")
    RELIANCE_API_URL = os.getenv("RELIANCE_API_URL", "")
    RELIANCE_API_TOKEN = os.getenv("RELIANCE_API_TOKEN", "")
    EXTRA_JSON_FEEDS = os.getenv("EXTRA_JSON_FEEDS", "")
    ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "")  # Comma-separated exact account emails, none by default.
    AI_SEMANTIC_ENABLED = os.getenv("AI_SEMANTIC_ENABLED", "1")
    AI_CROSS_ENCODER_ENABLED = os.getenv("AI_CROSS_ENCODER_ENABLED", "1")
    AI_SIAMESE_ENABLED = os.getenv("AI_SIAMESE_ENABLED", "1")
    AI_CLIP_ENABLED = os.getenv("AI_CLIP_ENABLED", "0")
    AI_EMBEDDING_MODEL = os.getenv("AI_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    AI_CROSS_ENCODER_MODEL = os.getenv("AI_CROSS_ENCODER_MODEL", "cross-encoder/stsb-distilroberta-base")
    AI_CLIP_MODEL = os.getenv("AI_CLIP_MODEL", "openai/clip-vit-base-patch32")
    AI_SIAMESE_CHECKPOINT = os.getenv("AI_SIAMESE_CHECKPOINT", str(BASE_DIR / "artifacts" / "siamese" / "siamese_head.pt"))
    AI_CLIP_CACHE_DIR = os.getenv("AI_CLIP_CACHE_DIR", str(BASE_DIR / "instance" / "product_images"))
    AI_SEMANTIC_RESCUE_THRESHOLD = float(os.getenv("AI_SEMANTIC_RESCUE_THRESHOLD", "0.84"))
    AI_SIAMESE_RESCUE_THRESHOLD = float(os.getenv("AI_SIAMESE_RESCUE_THRESHOLD", "0.90"))
