# Cost Quest V4 — Six-domain QA release

Read **[Release Status](RELEASE_STATUS_V4.md)** and **[QA Report](docs/QA_REPORT_V4.md)** before deployment. This is an improved local portfolio prototype, **not production-certified**.

Guest search and cross-domain product suggestions are supported. Account creation is optional. To allow a protected diagnostics view, register your admin account and set `ADMIN_EMAILS=your-admin-email@example.com` in `.env`, then visit `/admin` while logged in. Never grant admin access to the public by default.

# Cost Quest

**India-focused, multi-domain product discovery and price comparison.** Cost Quest searches connected product-data providers, validates the returned listings, separates materially different configurations, and records price observations for history and watchlists.

## Supported domains

The application currently contains six domain taxonomies and 61 category definitions. Each category has at least one representative positive/negative product fixture; the category-term suite covers 451 configured phrases:

| Domain | Categories | Important attributes handled |
|---|---:|---|
| Electronics | 20 | Model, storage, RAM, wattage, screen size, refresh rate, connectivity, console edition and product type |
| Fashion & Lifestyle | 7 | Clothing/shoe size and size scale, gender, material, colour, volume/quantity |
| Home Appliances | 10 | Capacity, AC tonnage, energy stars, wattage, load type, inverter type and dimensions |
| Books & Stationery | 8 | ISBN, edition, language, binding/format and pack quantity |
| Sports & Fitness | 8 | Weight, size and size scale, material, sport and pack quantity |
| Furniture & Home | 8 | Mattress/bed size, dimensions, material and seat count |

Category recognition is a convenience, not proof that a provider has live inventory. The shopper-facing search experience uses automatic domain detection and does not expose the internal domain taxonomy on the homepage. Product matching uses domain-specific attributes and conservative comparison groups; a similar title alone is not proof of equivalence. Ambiguous terms such as “running shoes” or “smartwatch” may require a more specific search phrase.

## Customer storefront and content-based discovery (v3)

- Responsive marketplace-style homepage with 6 domain tiles and search ideas.
- Guest search is **always available**; login/registration are optional.
- Both search bars have a visible **×** clear button, keyboard-friendly suggestions, and results sorting/filtering.
- `GET /api/suggestions?q=<text>` returns up to six local NLP suggestions without contacting retailers.
- Suggestions are drawn from 125 curated search ideas covering **all 61 categories**. These are *not* live store offers, price quotes, or guaranteed inventory.
- Content-based recommendations use a locally fitted sparse word/character TF-IDF model (`services/recommendations.py`).
- Product results display lowest verified listed price first, with colour variants grouped only within verified retailer/identity/price matches; other prices remain separate.
- Account search history is **off by default**. An opted-in user can enable or disable it, clear history, export data, or delete the account from `/account`. Turning it off deletes stored searches. Guest searches are not saved to an account.
- If no retailer offer is verified, the website can still suggest related searches, but it never pretends the search ideas have current prices.

**A separate experimental domain classifier was trained** on the 125 curated items with category-group holdout (33 evaluation titles): held-out accuracy **57.58%**. It is *not used* to accept retailer matches, because this is below a production reliability threshold. Retrain/evaluate it with a substantially larger, independent labelled dataset. Detailed results: `artifacts/search_models/evaluation.json`.

See `docs/STOREFRONT_AND_AI_QA.md` for the test matrix, live coverage limits, macOS commands and release blockers.

## Architecture

- `app.py` — Flask application factory, HTML routes, JSON search endpoint, CSRF validation and security headers.
- `core/` — domain registry, normalized offer contract, query parsing and shared matching/comparison logic.
- `domains/` — independent category catalogs and attribute extractors for each domain.
- `integrations/` — provider adapters and common offer validation.
- `services/` — provider orchestration plus a staged NLP/deep-learning Product Intelligence Engine (`services/product_ai/`).
- `database.py` — SQLite persistence, schema migration, price observations, watchlist and hashed-client search throttling.
- `templates/`, `static/` — responsive application interface.
- `tests/` — electronics regression tests and positive/negative domain-matching fixtures.
- `scripts/run_provider_smoke.py` — optional read-only live provider smoke test.
- `scripts/qa_live_domains.py` — read-only QA queries across every domain (`--live` explicitly required).
- `scripts/train_search_models.py` — experiment-only six-domain classifier training and held-out evaluation.
- `scripts/evaluate_all_domains.py` — offline positive/negative fixture evaluation across all six domains.
- `scripts/train_siamese_matcher.py` — trains Stage 3 from manually verified product-pair labels.
- `docs/` — architecture, AI matching pipeline, delivery order, QA gates and domain coverage boundaries.

The design is a modular Flask application, not a microservice system. SQLite is suitable for local/single-instance use; PostgreSQL should be evaluated before a multi-instance deployment.

## Setup (macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-ai.txt  # optional NLP / deep-learning models
if [ ! -f .env ]; then cp .env.example .env; fi  # keep your backed-up .env if you already have one
```

Edit `.env` locally. Do not share or commit it. Start the application:

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

## Testing

Install development dependencies and run:

```bash
python -m pip install -r requirements-dev.txt
python -m compileall -q app.py config.py database.py core domains integrations services tests scripts
python -m unittest tests.test_electronics_catalog tests.test_product_intelligence tests.test_regression_products tests.test_multidomain -v
python -m unittest discover -s tests -v
python -m pytest -q tests/test_search_recommendations.py tests/test_domain_product_matrix.py tests/test_presentation.py
python -m scripts.evaluate_all_domains
python -m scripts.train_search_models  # optional scikit-learn dependency
python -m pytest -q --cov=core --cov=domains --cov=services --cov=integrations --cov-report=term-missing
ruff check .
```

Run the live read-only smoke test only after network access is available:

```bash
python scripts/run_provider_smoke.py
```

The offline matching suite does not establish retailer coverage. On the packaged build, 71 selected offline tests and 757 subtests passed; the complete Flask integration suite was not runnable in the build environment (Flask unavailable). Run the complete suite on your Mac after installing requirements. Provider credentials, terms, network access, and current retailer listings determine live offer availability. See `docs/QA_AND_RELEASE_GATES.md`.

## NLP and deep-learning product matching

Technical AI stage status remains an internal development concern, not part of the customer comparison page. The matching pipeline still uses three stages. Stage 1 adds product-title normalization, product NER, BM25, character n-gram TF-IDF and optional MiniLM semantic embeddings. Stage 2 adds Cross-Encoder reranking. Stage 3 adds a trainable Siamese pair classifier and optional CLIP text/image evidence for locally cached product images. The deterministic identity and variant checks remain hard gates; neural scores cannot override a specification mismatch.

The base app works without the large model dependencies. Install `requirements-ai.txt` to enable MiniLM and Cross-Encoder inference; model weights download lazily on first search. Stage 3's training script, labelled-pair schema and example file are included, but no fake trained checkpoint is bundled. See `docs/PRODUCT_INTELLIGENCE_AI.md` for Mac setup, data labelling, training, model thresholds, CLIP cache safety and evaluation requirements.

## Accounts and watchlists

- Browsing and product searches remain available without an account.
- Users can register and log in with an email address and password; passwords are stored using Werkzeug's salted password-hashing implementation.
- Watchlists are account-scoped. A guest who presses **Watch** is sent to log in or register, and the selected offer is saved after successful authentication.
- POST forms, including login, registration, logout and watchlist actions, require CSRF tokens. Login/registration attempts are rate-limited by HMAC-keyed IP and IP/email buckets.
- Account deletion and data export are available. Public deployment still needs email verification, password reset, and potentially MFA/social login. See `SECURITY.md` for release limitations. Do not reuse a sensitive password; add email verification and recovery before public production launch.

## Provider integrations

- **PriceInIndia MCP:** configured as the default read-only marketplace aggregator. It is a third-party aggregator, not an official API for every retailer represented in its results. The provider card reports the aggregator connection; a separate retailer breakdown identifies storefronts found in its returned offers.
- **Amazon Creators API:** optional; requires eligible Associates account/API access and credentials.
- **Flipkart Affiliate API:** optional; requires active affiliate API credentials and current provider access.
- **Croma / Reliance Digital:** optional authorized JSON feeds. A storefront URL is not a product-search API or an authorized feed.
- **Extra feeds:** configured as `Name|HTTPS_URL|BearerToken;...` through `EXTRA_JSON_FEEDS`.

Feed endpoints must use HTTPS, cannot redirect, and local/private literal hosts are rejected. Only connect feeds for which you have authorization. Confirm every provider's latest terms for display, caching, attribution and redistribution before public launch.

## API

`GET /api/suggestions?q=Sony` — local, rate-limited autocomplete using curated search ideas; no retailer API request.

`GET /account` — optional account preferences, data export and saved history, available only after login.


`GET /api/search?q=Samsung%20Galaxy%20S26%20256GB&domain=electronics`

Optional parameters: `domain` and `category`. If omitted, the domain/category is inferred where possible. Use an explicit domain for ambiguous or title-only searches, such as book names.

`GET /health` verifies application database connectivity only. It does not test external providers. `/api/search` also returns a `product_intelligence` section describing configured AI stages.

## Security and deployment

See [SECURITY.md](SECURITY.md) for the implemented controls, deployment requirements and known authentication limitations.
 notes

- Keep `.env`, credentials and the SQLite database out of version control.
- Production startup requires a cryptographically random `SECRET_KEY` of at least 32 characters (`ENVIRONMENT=production`).
- CSRF checks protect POST forms; search and account endpoints have configurable hashed-client rate limits. Login and registration use password hashing and session rotation.
- Session cookies are HttpOnly and SameSite=Lax. Production forces Secure cookies and a `__Host-` cookie name; the application must be deployed behind HTTPS.
- Provider and feed requests use bounded timeouts; provider errors are sanitized before display.
- The application is intended to run behind a production WSGI server such as Gunicorn with HTTPS termination and suitable logging/monitoring.
- In-memory caches are not relied upon for product correctness. SQLite is single-instance oriented; move to PostgreSQL and review rate-limiter deployment before horizontally scaling.

## Known limitations

1. All six domain matching layers are implemented locally, but live provider coverage for each domain has **not** been established by this build environment.
2. Amazon, Flipkart, Croma and Reliance Digital direct integrations cannot be live-verified without valid user credentials/authorized feeds.
3. Some provider titles omit relevant attributes. When a requested attribute is missing, the matcher may reject the offer; this is deliberate to avoid unsafe comparisons.
4. Product model/ISBN/GTIN identifiers and verified retailer specifications are preferred. Similar title strings are not enough to prove identical SKUs. When a requested non-size attribute is absent, a candidate may be shown as a potential match and is excluded from lowest-price ranking until verified; a requested size without confirmation is rejected.
5. Price history starts when Cost Quest records an observation. A watchlist tracking command is included (`scripts/track_prices.py`), but you must configure a recurring scheduler and valid sources; past prices cannot be reconstructed.
6. Shipping, coupons, card discounts, delivery pin code and checkout price may differ from the displayed provider price.
7. Fashion and furniture taxonomies require ongoing refinement for brand-specific sizing, materials, dimensions and region-specific variants.
8. Transformer models must be benchmarked on labelled, retailer-separated product pairs. The bundled Siamese example CSV is not enough to train a dependable production model; Stage 3 remains in setup state until a real checkpoint is trained.
9. CLIP reads only local images inside `AI_CLIP_CACHE_DIR`. The current retailer adapters do not automatically download images into that cache.

## Project development plan

Follow the same implementation order and acceptance criteria in `docs/DEVELOPMENT_ROADMAP.md`. Do not skip regression testing or mark provider coverage verified based only on local fixtures.
