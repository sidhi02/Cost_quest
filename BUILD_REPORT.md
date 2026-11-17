# Cost Quest — Git-Ready Pre-Release Audit

**Audit date:** 2026-11-08  
**Baseline:** `Cost_Quest_Git_Ready_PreRelease_2026-11-08.zip`  
**Build purpose:** Integrate the three-stage NLP/deep-learning Product Intelligence Engine into the Flask search flow and deliver the complete source package.

## Release decision

| Intended use | Decision |
|---|---|
| Upload source to a private Git repository | **Ready**, after checking the local `.env` and database are not copied into the repository |
| Upload source to a public Git repository | **Ready as source code**, subject to the same secret scan and license/provider-terms review |
| Local acceptance testing on macOS | **Ready to test** after installing dependencies |
| Public production deployment | **NO-GO** until the remaining gates below pass |

This is not a production certification. Application integration tests and live retailer calls could not be executed in the build environment.

## AI Product Intelligence scope added

1. Stage 1: Unicode/title normalization, retailer alias normalization, product NER for identifiers/specifications, BM25, character 3–5 gram TF-IDF and optional MiniLM embeddings.
2. Stage 2: optional Cross-Encoder reranking after deterministic brand/model/category/variant checks.
3. Stage 3: Siamese pair-classifier architecture, training script, labelled-pair schema/template, validation metrics and learned threshold loading; optional CLIP text/image evidence for local cached images only.
4. Search integration: AI scores and extracted entities are attached to accepted listings; comparison HTML and `/api/search` expose engine readiness and per-offer evidence.
5. Conservative grouping: only compatible domain/brand/model/attribute pairs are considered; semantic pair merges require both semantic and Cross-Encoder agreement or a trained Siamese score. Cluster merging requires pairwise agreement to avoid transitive chain over-merging.
6. Safety: AI cannot override hard product variant mismatches. CLIP does not fetch arbitrary remote URLs. No trained Siamese model is fabricated or bundled.

## Seven-step corrective scope retained

1. Domain detection: six explicit domains plus General Shopping fallback; unknown products do not default to Electronics.
2. Search diagnostics: per-provider mapped, accepted, rejected and duplicate counts, rejection reasons and capped title samples.
3. Query expansion: bounded domain-aware alternatives; matching remains against the original user query.
4. Product matching: category, brand, model, size, capacity, edition and variant checks; accessory rejection; conservative deduplication; image fallback; single-offer state is not described as a comparison.
5. Regression: original ten electronics searches and 22 cross-domain screenshot searches, with positive and negative title fixtures.
6. Verification: offline tests, compilation, Jinja/JavaScript parsing and configuration security tests; app/live checks clearly separated.
7. Delivery: clean Git-ready source archive and this audit report.

## Authentication and session controls

- Routes: `/register` and `/login` support GET/POST; `/logout` is POST-only. There are no separate password-management JSON APIs in this release.
- Passwords must be 12–128 characters and are hashed with Werkzeug `scrypt:32768:8:1`; plaintext passwords are not stored.
- Unknown-account login attempts execute a dummy scrypt verification to reduce account-enumeration timing differences.
- Login failure text is generic.
- CSRF validation is applied to all POST requests.
- Login and registration attempts use HMAC-keyed IP and IP/email fixed-window rate-limit buckets.
- Login rotates the session, sets it permanent, and applies a 12-hour rolling lifetime.
- Authenticated and watchlist responses use `Cache-Control: no-store, private`; login and registration responses are also no-store.
- Production requires a 32-character-or-longer `SECRET_KEY`; production rejects disabled CSRF, disabled Secure cookies and debug mode.
- Production uses the `__Host-costquest-session` cookie name with Secure, HttpOnly, SameSite=Lax, Path=/ and no Domain attribute.
- Watchlist queries are scoped by authenticated user ID. Guest product search remains public by design; `/api/search` is a public, rate-limited search endpoint and does not expose account data.
- Security headers include CSP, X-Frame-Options, X-Content-Type-Options, no-referrer, Permissions-Policy and HSTS when Secure cookies are enabled.
- Google Fonts external requests have been removed; product images may still load from third-party HTTPS hosts with `referrerpolicy="no-referrer"`.

### Authentication features not included

Email verification, password reset/recovery, password change, MFA/passkeys, account deletion and self-service personal-data export are not included. There is no password reset API. Do not advertise account recovery or open public registration until these workflows and a privacy/data-retention policy are designed, implemented and tested.

## Git hygiene and CI

- `.gitignore` excludes `.env`, `.env.*` except `.env.example`, virtual environments, local databases, `instance/`, caches, build output, logs and common editor/OS files.
- `.github/workflows/ci.yml` installs application and dev dependencies on Python 3.13, compiles the project and runs the complete pytest suite on pushes and pull requests.
- The CI workflow has been added but has not yet run on GitHub; the current local full-suite run is blocked at test collection because Flask is missing from this execution environment.
- The delivered ZIP excludes `.env`, database files, virtual environments, `.git/` and caches. Check your own local working directory before `git add`; `.gitignore` cannot remove secrets already committed or tracked.

## Provider/data boundaries

- PriceInIndia is a marketplace aggregator; storefronts represented in its offers are not separate direct API calls.
- Amazon, Flipkart and authorized JSON feeds are separate integrations. Unconfigured feeds are skipped.
- PriceInIndia category filters are not sent using Cost Quest internal slugs. Its documented `category` parameter expects provider category group IDs/names; local matching performs Cost Quest domain filtering.
- Domain coverage remains `unverified` until actual live searches are performed.
- Do not use retailer storefront URLs as API endpoints; only connect authorized feeds and verify current provider terms for display, caching, attribution and redistribution.

## Test evidence executed for this archive

| Check | Result |
|---|---|
| Focused offline pytest suite including Product AI tests and config-security tests | **87 passed, 558 subtests passed** |
| Python compilation | Passed |
| Jinja template parsing | 8/8 passed |
| Jinja comparison-page render with AI-stage context | Passed |
| JavaScript syntax check (`node --check`) | Passed |
| ZIP extraction/integrity | Passed after archive creation; verified with `ZipFile.testzip()` and fresh extraction |
| Git ignore pattern review | Passed: `.env`, `instance/`, `.venv/` ignored and `.env.example` retained |
| Full `pytest -q` | **Blocked**: Flask is missing from this runtime, so `tests/test_app.py` and `tests/test_integrations.py` cannot be collected |
| Flask login/register/CSRF/session route tests | Defined in tests, not executed here |
| Live PriceInIndia requests | Not run: MCP package and outbound provider access unavailable |
| Live Amazon/Flipkart/Croma/Reliance Digital | Not run: credentials/authorized feeds and network required |
| Ruff / dependency vulnerability scan | Not run: Ruff and pip-audit unavailable |
| Load/concurrency and penetration testing | Not run |

The offline command used:

```bash
python -m pytest -q tests/test_product_ai.py tests/test_config_security.py tests/test_multidomain.py tests/test_domain_product_matrix.py tests/test_electronics_catalog.py tests/test_product_intelligence.py tests/test_regression_products.py tests/test_screenshot_search_regressions.py tests/test_search_diagnostics.py tests/test_provider_results.py
```

Result: `87 passed, 558 subtests passed`.

The AI test suite validates lexical retrieval and fallback behavior using the installed runtime. It does not execute MiniLM/Cross-Encoder inference, train a Siamese checkpoint or run CLIP: `sentence-transformers` and `transformers` are not installed and model downloads are not available in this environment. The checked-in product-pair file is a starter example, not training data; no trained model artifact is included.

## Required macOS acceptance checks

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -r requirements-ai.txt
python -m compileall -q app.py config.py database.py core domains integrations services tests scripts
python -m pytest -q
ruff check .
```

Then verify registration, login, logout, CSRF rejection, wrong-password handling, rate limits, per-user watchlist isolation, session cookie attributes, and all 32 known product searches. Search with AI packages installed and inspect the Stage 1/2 status after the first model downloads. Add a verified pair dataset, train the Siamese classifier, inspect the independent holdout metrics and re-run variant regression tests before enabling it for automatic grouping. CLIP requires approved local cached images. Run `python scripts/run_provider_smoke.py` only after outbound network and MCP are available; check authorized direct provider feeds separately.

## Production go/no-go gates

Public launch remains **NO-GO** until:

1. The complete Flask and provider mocked test suite passes on the target runtime/CI.
2. The current provider agreements/permissions and live listing samples are verified for each domain.
3. HTTPS is terminated by a trusted reverse proxy; production environment variables and cookie settings are verified.
4. A persistent database, automated backups, restore test and migration plan are in place. SQLite is single-instance oriented; use PostgreSQL for multiple app instances.
5. Password reset, email verification, account deletion, privacy notice and data-retention policy are completed or the product scope is explicitly changed with a documented user account lifecycle.
6. Dependency vulnerability scan, security review/penetration test, logging/monitoring and load test pass.

No live inventory, current pricing, all-product coverage or production security guarantee is inferred from the offline fixture tests.
