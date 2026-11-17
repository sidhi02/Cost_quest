import json
from pathlib import Path
import hashlib
import hmac
import re
import secrets
import sqlite3
from contextlib import closing
from urllib.parse import urlsplit

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from core.domain_registry import ALL_CATEGORIES, DOMAIN_INDEX
from core.query_parser import parse_search
from database import delete_user_account, export_user_data, add_watch, check_search_rate_limit, connect, create_user, get_price_history, get_user_by_email, get_user_by_id, get_watchlist, init_db, remove_watch, save_price_snapshots
from services.comparison import configured_providers, retailer_breakdown, search_products
from services.presentation import prepare_comparison
from services.recommendations import autocomplete, recommend, personalized, domain_samples
from database import set_history_preference, save_user_search, get_user_searches, clear_user_searches
from services.product_ai import get_product_intelligence_status


def create_app(config_object=Config):
    application = Flask(__name__)
    application.config.from_object(config_object)
    production = application.config.get("ENVIRONMENT") == "production"
    if production:
        if len(str(application.config.get("SECRET_KEY", ""))) < 32:
            raise RuntimeError("Production SECRET_KEY must contain at least 32 characters")
        if not application.config.get("CSRF_ENABLED", True):
            raise RuntimeError("CSRF protection cannot be disabled in production")
        if not application.config.get("SESSION_COOKIE_SECURE", False):
            raise RuntimeError("Secure session cookies are mandatory in production")
        if application.config.get("DEBUG", False):
            raise RuntimeError("Debug mode must be disabled in production")
        application.config.update(SESSION_COOKIE_NAME="__Host-costquest-session", SESSION_COOKIE_SECURE=True, CSRF_ENABLED=True, DEBUG=False, PREFERRED_URL_SCHEME="https")
    application.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_PATH="/", SESSION_COOKIE_DOMAIN=None, MAX_CONTENT_LENGTH=1024 * 1024)
    application.secret_key = application.config["SECRET_KEY"]
    dummy_password_hash = generate_password_hash(secrets.token_urlsafe(32), method="scrypt:32768:8:1")
    with application.app_context():
        init_db()

    def current_user_id():
        return session.get("user_id")

    def safe_next(value):
        value = str(value or "")
        parsed = urlsplit(value)
        return value if value.startswith("/") and not value.startswith("//") and not parsed.scheme and not parsed.netloc and "\\" not in value else url_for("index")

    def auth_rate_allowed(email, action):
        remote = request.remote_addr or "unknown"
        window = application.config["AUTH_RATE_WINDOW"]
        secret = str(application.secret_key).encode()
        ip_identity = hmac.new(secret, f"{remote}|{action}".encode(), hashlib.sha256).hexdigest()
        pair_identity = hmac.new(secret, f"{remote}|{str(email or '').strip().lower()}|{action}".encode(), hashlib.sha256).hexdigest()
        ip_allowed = check_search_rate_limit("auth-ip:" + ip_identity, application.config["AUTH_IP_RATE_LIMIT"], window)
        pair_allowed = check_search_rate_limit("auth-pair:" + pair_identity, application.config["AUTH_RATE_LIMIT"], window)
        return ip_allowed and pair_allowed

    def valid_watch_product(product):
        parsed = urlsplit(product.get("url", ""))
        return (len(product.get("product_key", "")) == 24 and all(char in "0123456789abcdef" for char in product["product_key"])
                and all(product.values()) and len(product.get("name", "")) <= 300
                and parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password)

    def finish_login(user):
        pending = session.pop("pending_watch", None)
        session.clear()
        session["user_id"] = user["id"]
        session["_csrf_token"] = secrets.token_urlsafe(32)
        session.permanent = True
        if pending and valid_watch_product(pending):
            add_watch(pending, user["id"])
            flash("The product you selected has been added to your watchlist.", "success")

    @application.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-DNS-Prefetch-Control", "off")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; img-src 'self' https: data:; style-src 'self'; font-src 'self'; script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'")
        if application.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.endpoint in {"login", "register", "account", "admin", "account_export"} or request.path.startswith("/watchlist") or current_user_id():
            response.headers["Cache-Control"] = "no-store, private, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.vary.add("Cookie")
        return response

    def search_allowed():
        identity = request.remote_addr or "unknown"
        key = hmac.new(str(application.secret_key).encode(), identity.encode(), hashlib.sha256).hexdigest()
        return check_search_rate_limit("search:" + key, application.config["SEARCH_RATE_LIMIT"], application.config["SEARCH_RATE_WINDOW"])

    @application.before_request
    def protect_post_requests():
        if request.method == "POST" and application.config.get("CSRF_ENABLED", True):
            expected = session.get("_csrf_token", "")
            supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
            if not expected or not supplied or not hmac.compare_digest(expected, supplied):
                abort(400)

    def is_admin(user):
        # No default administrator or public registration-based escalation.
        allowed = {email.strip().casefold() for email in str(application.config.get("ADMIN_EMAILS") or "").split(",") if email.strip()}
        return bool(user and user.get("email", "").casefold() in allowed)

    @application.context_processor
    def inject_template_context():
        token = session.setdefault("_csrf_token", secrets.token_urlsafe(32))
        user = get_user_by_id(current_user_id())
        return {"csrf_token": token, "domains": list(DOMAIN_INDEX.values()), "all_categories": ALL_CATEGORIES,
                "current_user": user, "is_admin": is_admin(user)}

    @application.get("/")
    def index():
        statuses = []
        for provider in configured_providers():
            status = provider.status()
            status["role"] = status.get("role") or ("Marketplace aggregator" if status["name"] == "PriceInIndia" else "Direct retailer API/feed")
            statuses.append(status)
        user_id = current_user_id()
        user = get_user_by_id(user_id)
        suggestions = personalized(get_user_searches(user_id, 6)) if user and user.get('history_enabled') else []
        return render_template("index.html", providers=statuses, domains=list(DOMAIN_INDEX.values()),
                               domain_samples=domain_samples(), personal_suggestions=suggestions)

    @application.get("/admin")
    def admin():
        user = get_user_by_id(current_user_id())
        if not is_admin(user):
            abort(403)
        provider_status = []
        for provider in configured_providers():
            status = provider.status()
            provider_status.append({"name": status.get("name", "Unknown"),
                                    "role": status.get("role") or ("Aggregator" if status.get("name") == "PriceInIndia" else "Direct retailer adapter"),
                                    "configured": bool(status.get("configured")),
                                    "message": status.get("message", "Not configured")})
        reports = []
        for filename, label in (("offline_qa_report.json", "61-category fixture evaluation"),
                                ("novel_product_qa.json", "New six-domain matching tests"),
                                ("evaluation.json", "Experimental classifier evaluation")):
            filepath = Path(application.root_path) / "artifacts" / "search_models" / filename
            try:
                with filepath.open(encoding="utf8") as handle:
                    info = json.load(handle)
                reports.append({"label": label, "data": info, "available": True})
            except (OSError, ValueError):
                reports.append({"label": label, "data": {}, "available": False})
        return render_template("admin.html", provider_status=provider_status, qa_reports=reports)

    @application.route("/register", methods=["GET", "POST"])
    def register():
        if current_user_id():
            return redirect(url_for("index"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if not auth_rate_allowed(email, "register"):
                flash("Too many account attempts. Please try again later.", "error")
            elif not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
                flash("Enter a valid email address.", "error")
            elif len(password) < 12 or len(password) > 128:
                flash("Use a password containing 12 to 128 characters.", "error")
            elif password != confirm:
                flash("The passwords do not match.", "error")
            else:
                try:
                    user = create_user(email, generate_password_hash(password, method="scrypt:32768:8:1"))
                    finish_login(user)
                    if request.form.get('personalize') == 'yes':
                        set_history_preference(user['id'], True)
                    flash("Your account has been created.", "success")
                    return redirect(safe_next(request.args.get("next") or request.form.get("next")))
                except sqlite3.IntegrityError:
                    flash("An account with this email already exists. Please log in.", "error")
        return render_template("register.html", next_url=safe_next(request.args.get("next")))

    @application.route("/login", methods=["GET", "POST"])
    def login():
        if current_user_id():
            return redirect(url_for("index"))
        next_url = safe_next(request.args.get("next") or request.form.get("next"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not auth_rate_allowed(email, "login"):
                flash("Too many login attempts. Please wait 15 minutes before trying again.", "error")
            else:
                user = get_user_by_email(email)
                password_hash = user["password_hash"] if user else dummy_password_hash
                password_valid = check_password_hash(password_hash, password)
                if user and password_valid:
                    finish_login(user)
                    flash("You are now logged in.", "success")
                    return redirect(next_url)
                flash("Email or password is incorrect.", "error")
        return render_template("login.html", next_url=next_url)

    @application.post("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("index"))

    @application.get("/compare")
    def compare():
        query = request.args.get("q", "").strip()[:160]
        if not query:
            return redirect(url_for("index"))
        if not search_allowed():
            abort(429)
        scope = parse_search(query, request.args.get("domain"), request.args.get("category"))
        products, providers = search_products(query, scope["category"], scope["domain"])
        save_price_snapshots(products)
        display_offers, review_offers, best_price = prepare_comparison(products)
        save_user_search(current_user_id(), query, scope['domain'])
        suggestions = recommend(query, limit=6, domain=scope['domain'] if scope['domain'] in DOMAIN_INDEX else None,
                                category=scope['category'])
        return render_template("compare.html", similar_suggestions=suggestions, query=query, products=display_offers, review_offers=review_offers, best_price=best_price, providers=providers, retailer_sources=retailer_breakdown(products), category=scope["category"] or "general", category_name=scope["category_name"] or "General", domain=scope["domain"], domain_name=DOMAIN_INDEX.get(scope["domain"], {"name": "General Shopping"})["name"], requested_domain=request.args.get("domain", "").strip(), intelligence=get_product_intelligence_status(application.config))

    @application.get('/api/suggestions')
    def api_suggestions():
        query = request.args.get('q', '').strip()[:100]
        if not query or len(query) < 2:
            return jsonify({'suggestions': []})
        # Lightweight local suggestions, isolated from live retailer requests.
        # Protect against aggressive clients and avoid leaking any user history.
        client_key = hmac.new(str(application.secret_key).encode(),
                              (request.remote_addr or 'unknown').encode(), hashlib.sha256).hexdigest()
        if not check_search_rate_limit('suggest:' + client_key, 150, 60):
            return jsonify({'error': 'Suggestion rate limit exceeded'}), 429
        return jsonify({'suggestions': autocomplete(query, limit=6), 'source': 'curated_search_ideas'})

    @application.get('/account')
    def account():
        user_id = current_user_id()
        if not user_id:
            return redirect(url_for('login', next=url_for('account')))
        user = get_user_by_id(user_id)
        history = get_user_searches(user_id) if user.get('history_enabled') else []
        ideas = personalized(history) if history else []
        return render_template('account.html', history=history, personal_suggestions=ideas)

    @application.post('/account/preferences')
    def account_preferences():
        if not current_user_id():
            abort(401)
        enabled = request.form.get('history_enabled') == 'yes'
        set_history_preference(current_user_id(), enabled)
        flash('Search history and recommendations enabled.' if enabled else 'Search history disabled and previously saved searches deleted.', 'success')
        return redirect(url_for('account'))

    @application.post('/account/history/clear')
    def account_clear_history():
        if not current_user_id():
            abort(401)
        clear_user_searches(current_user_id())
        flash('Your saved search history has been cleared.', 'success')
        return redirect(url_for('account'))

    @application.get("/history/<product_key>")
    def history(product_key):
        if len(product_key) != 24 or any(char not in "0123456789abcdef" for char in product_key):
            abort(404)
        return render_template("history.html", product_key=product_key, history=get_price_history(product_key))

    @application.post("/watchlist/add")
    def watch_add():
        product = {key: request.form.get(key, "").strip() for key in ("product_key", "name", "retailer", "url")}
        if not valid_watch_product(product):
            flash("The product could not be saved. Please try again from a comparison result.", "error")
            return redirect(request.referrer if request.referrer and urlsplit(request.referrer).netloc == request.host else url_for("index"))
        user_id = current_user_id()
        if not user_id:
            session["pending_watch"] = product
            flash("Log in or create an account to save this product.", "info")
            return redirect(url_for("login", next=url_for("watchlist")))
        add_watch(product, user_id)
        flash("Product added to your watchlist.", "success")
        referrer = request.referrer or ""
        parsed_referrer = urlsplit(referrer)
        destination = parsed_referrer.path + ("?" + parsed_referrer.query if parsed_referrer.query else "") if parsed_referrer.netloc == request.host else url_for("index")
        return redirect(destination if destination.startswith("/") and not destination.startswith("//") else url_for("index"))

    @application.get("/watchlist")
    def watchlist():
        if not current_user_id():
            flash("Log in to view your saved products.", "info")
            return redirect(url_for("login", next=url_for("watchlist")))
        return render_template("watchlist.html", items=get_watchlist(current_user_id()))

    @application.post("/watchlist/<int:item_id>/remove")
    def watch_remove(item_id):
        if not current_user_id():
            return redirect(url_for("login", next=url_for("watchlist")))
        remove_watch(item_id, current_user_id())
        flash("Product removed.", "success")
        return redirect(url_for("watchlist"))

    @application.get("/account/export")
    def account_export():
        if not current_user_id():
            abort(401)
        response = jsonify(export_user_data(current_user_id()))
        response.headers["Content-Disposition"] = 'attachment; filename="costquest-account.json"'
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.post("/account/delete")
    def account_delete():
        if not current_user_id():
            abort(401)
        if request.form.get("confirmation") != "DELETE":
            flash("Type DELETE to confirm account deletion.", "error")
            return redirect(url_for("watchlist"))
        delete_user_account(current_user_id())
        session.clear()
        flash("Your account and saved watchlist have been deleted.", "success")
        return redirect(url_for("index"))

    @application.get("/api/search")
    def api_search():
        query = request.args.get("q", "").strip()[:160]
        if not query:
            return jsonify({"error": "Query parameter q is required."}), 400
        if not search_allowed():
            return jsonify({"error": "Search rate limit exceeded. Please retry shortly."}), 429
        scope = parse_search(query, request.args.get("domain"), request.args.get("category"))
        products, providers = search_products(query, scope["category"], scope["domain"])
        save_price_snapshots(products)
        return jsonify({"application": "Cost Quest", "query": query, "domain": scope["domain"], "domain_name": DOMAIN_INDEX.get(scope["domain"], {"name": "General Shopping"})["name"], "category": scope["category"], "category_name": scope["category_name"], "currency": "INR", "products": products, "providers": providers, "retailer_sources": retailer_breakdown(products), "product_intelligence": get_product_intelligence_status(application.config)})

    @application.get("/health")
    def health():
        try:
            with closing(connect()) as db:
                db.execute("SELECT 1")
            return jsonify({"status": "ok", "database": "ok", "application": "Cost Quest"})
        except Exception:
            return jsonify({"status": "degraded", "database": "unavailable", "application": "Cost Quest"}), 503

    @application.errorhandler(400)
    def bad_request(_):
        return render_template("error.html", message="The request could not be completed. Refresh the page and try again."), 400

    @application.errorhandler(403)
    def access_denied(_):
        return render_template("error.html", message="You do not have access to this page."), 403

    @application.errorhandler(404)
    def not_found(_):
        return render_template("error.html", message="This page could not be found."), 404

    @application.errorhandler(429)
    def rate_limited(_):
        return render_template("error.html", message="Search or account limit reached. Please wait briefly before trying again."), 429

    @application.errorhandler(500)
    def server_error(_):
        return render_template("error.html", message="Something went wrong while processing your request."), 500

    return application


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
