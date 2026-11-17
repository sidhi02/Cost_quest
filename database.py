import sqlite3
import time
from contextlib import closing
from pathlib import Path

from flask import current_app


def connect():
    path = Path(current_app.config["DATABASE_PATH"])
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=15000")
    return db


def _columns(db, table):
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}


def _create_watchlist_table(db, name="watchlist"):
    db.execute(f"""CREATE TABLE {name} (
        id INTEGER PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        product_key TEXT NOT NULL,
        product_name TEXT NOT NULL,
        retailer TEXT NOT NULL,
        product_url TEXT NOT NULL,
        target_price REAL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")


def init_db():
    with closing(connect()) as db, db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY, product_key TEXT NOT NULL, product_name TEXT NOT NULL,
            retailer TEXT NOT NULL, price REAL NOT NULL CHECK(price > 0),
            captured_at TEXT NOT NULL DEFAULT (datetime('now')), domain TEXT NOT NULL DEFAULT 'general',
            category TEXT NOT NULL DEFAULT 'general'
        );
        CREATE INDEX IF NOT EXISTS idx_history_key ON price_history(product_key, captured_at);
        CREATE TABLE IF NOT EXISTS search_rate_limits (
            client_key TEXT PRIMARY KEY, window_started INTEGER NOT NULL, hits INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rate_window ON search_rate_limits(window_started);
        """)
        table = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='watchlist'").fetchone()
        if not table:
            _create_watchlist_table(db)
        else:
            cols = _columns(db, "watchlist")
            schema = (table["sql"] or "").upper()
            if "USER_ID" not in cols or "PRODUCT_KEY TEXT NOT NULL UNIQUE" in schema:
                db.execute("ALTER TABLE watchlist RENAME TO watchlist_legacy")
                _create_watchlist_table(db)
                legacy = _columns(db, "watchlist_legacy")
                user_expr = "user_id" if "user_id" in legacy else "NULL"
                target_price_expr = "target_price" if "target_price" in legacy else "NULL"
                created_expr = "created_at" if "created_at" in legacy else "datetime('now')"
                required = {"id", "product_key", "product_name", "retailer", "product_url"}
                if required.issubset(legacy):
                    db.execute(f"""INSERT INTO watchlist(id,user_id,product_key,product_name,retailer,product_url,target_price,created_at)
                        SELECT id,{user_expr},product_key,product_name,retailer,product_url,{target_price_expr},{created_expr} FROM watchlist_legacy""")
                db.execute("DROP TABLE watchlist_legacy")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_watch_user_product ON watchlist(user_id,product_key) WHERE user_id IS NOT NULL")
        db.execute("CREATE INDEX IF NOT EXISTS idx_watch_user_created ON watchlist(user_id,created_at)")
        columns = _columns(db, "price_history")
        if "domain" not in columns:
            db.execute("ALTER TABLE price_history ADD COLUMN domain TEXT NOT NULL DEFAULT 'general'")
        if "category" not in columns:
            db.execute("ALTER TABLE price_history ADD COLUMN category TEXT NOT NULL DEFAULT 'general'")
        db.execute("CREATE INDEX IF NOT EXISTS idx_history_domain ON price_history(domain, category, captured_at)")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS tracking_runs (
            id INTEGER PRIMARY KEY, started_at TEXT NOT NULL DEFAULT (datetime('now')),
            finished_at TEXT, queries_checked INTEGER NOT NULL DEFAULT 0,
            offers_recorded INTEGER NOT NULL DEFAULT 0, errors INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_history_retailer_time ON price_history(product_key, retailer, captured_at);
        """)
        # Opt-in account recommendations: guest searches are never persisted.
        if "history_enabled" not in _columns(db, "users"):
            db.execute("ALTER TABLE users ADD COLUMN history_enabled INTEGER NOT NULL DEFAULT 0")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS user_search_history (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            query TEXT NOT NULL,
            domain TEXT NOT NULL,
            searched_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_user_search_history ON user_search_history(user_id, id DESC);
        """)
        db.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES(5)")


def create_user(email, password_hash):
    with closing(connect()) as db, db:
        cursor = db.execute("INSERT INTO users(email,password_hash) VALUES(?,?)", (email.strip().lower(), password_hash))
        row = db.execute("SELECT id,email,created_at,history_enabled FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def get_user_by_email(email):
    with closing(connect()) as db:
        row = db.execute("SELECT id,email,password_hash,created_at,history_enabled FROM users WHERE email=? COLLATE NOCASE", (str(email or "").strip().lower(),)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id):
    if not user_id:
        return None
    with closing(connect()) as db:
        row = db.execute("SELECT id,email,created_at,history_enabled FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def save_price_snapshots(products):
    rows = [(p["product_key"], p["name"], p["retailer"], p["price"], p.get("domain", "general"), p.get("category", "general")) for p in products if p.get("price") and p.get("product_key")]
    if rows:
        with closing(connect()) as db, db:
            db.executemany("INSERT INTO price_history(product_key,product_name,retailer,price,domain,category) VALUES(?,?,?,?,?,?)", rows)


def get_price_history(product_key):
    with closing(connect()) as db:
        rows = db.execute("SELECT retailer, price, captured_at, domain, category FROM price_history WHERE product_key=? ORDER BY captured_at DESC LIMIT 100", (product_key,)).fetchall()
    return [dict(row) for row in reversed(rows)]


def add_watch(product, user_id):
    if not user_id:
        raise ValueError("A user account is required to save a watchlist item")
    with closing(connect()) as db, db:
        db.execute("""INSERT INTO watchlist(user_id,product_key,product_name,retailer,product_url,target_price)
            SELECT ?,?,?,?,?,? WHERE NOT EXISTS (SELECT 1 FROM watchlist WHERE user_id=? AND product_key=?)""",
            (user_id, product["product_key"], product["name"], product["retailer"], product["url"], product.get("target_price"), user_id, product["product_key"]))


def get_watchlist(user_id):
    if not user_id:
        return []
    with closing(connect()) as db:
        rows = db.execute("SELECT * FROM watchlist WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [dict(row) for row in rows]


def remove_watch(item_id, user_id):
    with closing(connect()) as db, db:
        db.execute("DELETE FROM watchlist WHERE id=? AND user_id=?", (item_id, user_id))


def check_search_rate_limit(client_key, limit=60, window=60):
    now = int(time.time())
    with closing(connect()) as db, db:
        db.execute("INSERT OR IGNORE INTO search_rate_limits(client_key,window_started,hits) VALUES(?,?,0)", (client_key, now))
        row = db.execute("SELECT window_started,hits FROM search_rate_limits WHERE client_key=?", (client_key,)).fetchone()
        if now - row["window_started"] >= window:
            db.execute("UPDATE search_rate_limits SET window_started=?,hits=1 WHERE client_key=?", (now, client_key))
            allowed = True
        elif row["hits"] >= limit:
            allowed = False
        else:
            db.execute("UPDATE search_rate_limits SET hits=hits+1 WHERE client_key=?", (client_key,))
            allowed = True
        if now % 100 == 0:
            db.execute("DELETE FROM search_rate_limits WHERE window_started<?", (now - window * 3,))
    return allowed


def set_history_preference(user_id, enabled):
    """User-controlled personalization, disabled by default.

    Turning it off also deletes stored searches.
    """
    with closing(connect()) as db, db:
        db.execute("UPDATE users SET history_enabled=? WHERE id=?", (int(bool(enabled)), user_id))
        if not enabled:
            db.execute("DELETE FROM user_search_history WHERE user_id=?", (user_id,))


def save_user_search(user_id, query, domain):
    if not user_id or not str(query or '').strip():
        return
    with closing(connect()) as db, db:
        enabled = db.execute("SELECT history_enabled FROM users WHERE id=?", (user_id,)).fetchone()
        if not enabled or not enabled['history_enabled']:
            return
        db.execute("INSERT INTO user_search_history(user_id,query,domain) VALUES(?,?,?)",
                   (user_id, str(query).strip()[:160], str(domain or 'general')[:40]))
        db.execute("DELETE FROM user_search_history WHERE user_id=? AND id NOT IN (SELECT id FROM user_search_history WHERE user_id=? ORDER BY id DESC LIMIT 100)", (user_id, user_id))


def get_user_searches(user_id, limit=30):
    if not user_id:
        return []
    with closing(connect()) as db:
        rows = db.execute("SELECT query,domain,searched_at FROM user_search_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
                          (user_id, max(1, min(int(limit), 100)))).fetchall()
    return [dict(row) for row in rows]


def clear_user_searches(user_id):
    with closing(connect()) as db, db:
        db.execute("DELETE FROM user_search_history WHERE user_id=?", (user_id,))


def delete_user_account(user_id):
    """Delete account plus watches and opt-in search history via cascades."""
    with closing(connect()) as db, db:
        db.execute("DELETE FROM users WHERE id=?", (user_id,))


def export_user_data(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return None
    return {"user": user, "watchlist": get_watchlist(user_id), "search_history": get_user_searches(user_id, 100)}


def list_tracking_queries(limit=100):
    """Watchlist entries supply the products that a scheduled worker refreshes."""
    with closing(connect()) as db:
        rows = db.execute("SELECT DISTINCT product_name FROM watchlist WHERE user_id IS NOT NULL ORDER BY product_name LIMIT ?", (limit,)).fetchall()
    return [row["product_name"] for row in rows]


def record_tracking_run(queries_checked, offers_recorded, errors):
    with closing(connect()) as db, db:
        db.execute("INSERT INTO tracking_runs(finished_at,queries_checked,offers_recorded,errors) VALUES(datetime('now'),?,?,?)", (queries_checked, offers_recorded, errors))
