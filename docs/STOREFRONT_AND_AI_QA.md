# Cost Quest v3 — Storefront, AI search and six-domain QA

## What changed

- Replaced the original homepage with a responsive, retail-style browsing experience and category discovery cards for all 6 domains / 61 categories.
- Visible **×** clear action on the homepage and search-results input, including when the input is empty; keyboard-friendly typeahead suggestions support ↑, ↓, Enter and Escape.
- Product recommendations: local TF-IDF search-idea model; no invented prices or retailer links.
- Search results: default best verified offer first, clearly highlighted; colour variants at the same retailer/identity/price can be collapsed, whereas different prices remain visible. Interactive sorting and retailer filters.
- No account required to browse or compare. Accounts optionally enable persistent watchlists, opt-in search history, account export, and account deletion. Turning off history clears prior saved searches.
- `/api/suggestions` is rate-limited, local, and independent of live retailer connectivity.

## What was really trained

1. `services/recommendations.py` constructs a *fitted* sparse TF-IDF model over 125 curated search ideas from 61 categories. It uses word tokens and character 3/4-grams to handle formatting variations. This is a content-based retriever, **not** an end-to-end neural product matcher.
2. `scripts/train_search_models.py` trained a separate experimental TF-IDF+logistic-regression domain classifier with category-group holdout; 92 training and 33 evaluation examples. Held-out accuracy **57.58%**. The model is saved to `artifacts/search_models/experimental_domain_classifier.joblib` for experimentation only. **It is intentionally not used in live matching** because its held-out accuracy is weak. Joblib models should only be loaded from trusted sources; retrain locally if your scikit-learn version differs.
3. The original Siamese training workflow exists, but **no dependable trained Siamese matching checkpoint** is shipped. This requires independent manually labelled retailer pairs.

## What was actually tested in the build environment

- 71 selected offline matching and recommendation tests passed with 757 subtests, covering electronics, fashion, appliances, books, sports, furniture.
- 61 synthetic positive/negative product-match fixtures (one per category) passed: 61 true positives, 61 true negatives, 0 false positives, 0 false negatives *on these fixtures*. **This is fixture regression, not an independent benchmark.** See `artifacts/search_models/offline_qa_report.json`.
- 125/125 in-catalogue prefix suggestions were found within the top six (in-catalogue smoke check, not unseen-query precision).
- New Flask integration tests were authored for guest browsing, suggestions, account personalization opt-in/opt-out, and history deletion, but could not run locally because Flask was unavailable and dependency installation was blocked by network access. Jinja2 template parsing/rendering and JavaScript syntax checks passed.
- Live provider connectivity, browser screenshots, deployed HTTPS, and a production security audit were **not** verified.

## Repeat testing on macOS

Inside the extracted `cost_quest` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
cp .env.example .env       # if no existing .env
python -m pytest -q
python -m scripts.evaluate_all_domains
python -m scripts.qa_live_domains             # dry run, NO NETWORK
python -m scripts.qa_live_domains --live --per-domain 1  # opt-in live test
python app.py
```

Optional classifier training:

```bash
python -m pip install scikit-learn joblib
python -m scripts.train_search_models
```

Validate: guest searches, comparison links, × clearing, suggestion selection, different-domain queries, colour-price grouping, retailer filter, watchlist login redirect, account history opt-in/opt-out, export and deletion. Test on desktop and mobile sizes.

## Six-domain examples and exceptions

| Domain | Positive examples | Critical exceptions |
|---|---|---|
| Electronics | Sony WH-1000XM5; iPhone 16 128GB; MacBook Air M4 | XM4 vs XM5, storage, RAM, model family, accessories |
| Fashion | Nike Air Force 1 UK 8; Levi's 511 jeans | shoe size, fit, colour, gender categories, variants |
| Home appliances | LG 8kg front-load washer; Daikin 1.5-ton AC | capacity, load type, energy stars, 1 vs 1.5 ton |
| Books & stationery | Atomic Habits paperback; Classmate notebook pack | ISBN/edition, binding, pack quantity |
| Sports & fitness | Yonex Astrox 99; Nivia football size 5 | model, weight, size, incompatible accessories |
| Furniture & home | Wakefit queen mattress; IKEA dining table | dimensions, bed size, materials, number of seats |

Run `python -m scripts.qa_live_domains --live` *only after* configuring permitted retailer data providers. The read-only test limits requests and reports accepted vs unverified offers. No website is guaranteed to be accessible.

## Known release blockers

1. External retailer API/feed credentials and usage permissions must be verified; aggregator storefront mentions are not direct API connectivity.
2. Collect large, diverse, manually labelled retailer product pairs and retrain neural product matcher; evaluate precision, recall, F1 and false-match rate on *retailer-separated* held-out data.
3. Resolve product feeds missing storage/variant specifications without silently marking them verified.
4. Implement and validate delivery charges, eligible coupons, PIN-code and final checkout pricing; don't claim exact final price without data.
5. Add password recovery and email verification before opening public accounts.
6. Move from SQLite and local rate-limit storage to production-grade database and centralized throttling for horizontal scaling.
7. Deploy with HTTPS, strong secrets, worker/scheduler setup, observability, dependency scanning, full browser/integration tests and backups.

**Current status:** improved portfolio prototype, **not yet an independently verified production launch**.
