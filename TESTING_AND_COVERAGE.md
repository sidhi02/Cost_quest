# Cost Quest testing and coverage

## Test suites

The project includes:

- Twenty electronics category and matching tests, including the ten supplied electronics regression searches.
- Cross-domain registry, brand, category, variant and comparison-group fixtures.
- Provider offer validation tests for malformed prices, non-INR offers and unsafe URLs.
- Flask route/database tests and mocked provider-adapter tests, to be run after installing project dependencies.

## Ten electronics regression searches retained

1. Samsung Galaxy S26 256GB — reject S26+, Ultra, FE and accessories.
2. Apple Watch — permit family discovery but preserve series/configuration groups.
3. Apple Watch strap — return strap/band products rather than watch devices.
4. Sony WH-1000XM5 — reject WH-1000XM4 and WF earbuds.
5. MacBook Air M4 16GB — preserve Air/Pro family and RAM configuration.
6. iPad Air M3 11 inch — preserve generation, screen size, storage and Wi-Fi/Cellular.
7. NVIDIA RTX 5070 — show compatible GPU family variants but keep board-partner SKUs separate.
8. PlayStation 5 Slim Disc Edition — reject Digital and non-Slim editions.
9. Samsung 45W USB-C charger — require Samsung and charger product type; reject cable and unrelated brands.
10. TP-Link Archer AX55 router — reject AX50 and unrelated models.

## Cross-domain product matrix

`tests/test_domain_product_matrix.py` contains:

- 20 realistic Electronics category scenarios with an intended product and a wrong product/variant for each family.
- 41 realistic scenarios across Fashion & Lifestyle, Home Appliances, Books & Stationery, Sports & Fitness, and Furniture & Home. These cover size, capacity, appliance type, ISBN/edition/format, exam/paper type, sport/equipment attributes and furniture configuration.
- All 451 configured category search phrases tested in an explicitly selected domain/category.
- Ten screenshot-driven search-routing regressions, including OnePlus 13R vs 13, Canon EOS R50 vs R10, Prestige PIC 20.0 identity and queen-mattress size requirements.
- Accessory rejection checks across all six domains.
- Auto-detection checks for appliance terms that previously fell into the overlapping electronics category.

The latest offline selected-suite result is **87 passed, 558 subtests passed**. This is local fixture validation, not live provider verification.

## Original electronics regression cases retained

1. Samsung Galaxy S26 256GB — reject S26+, Ultra, FE and accessories.
2. Apple Watch — permit family discovery but preserve series/configuration groups.
3. Apple Watch strap — return strap/band products rather than watch devices.
4. Sony WH-1000XM5 — reject WH-1000XM4 and WF-series earbuds.
5. MacBook Air M4 16GB — preserve Air/Pro family and RAM configuration.
6. iPad Air M3 11 inch — preserve generation, screen size, storage and Wi-Fi/Cellular.
7. NVIDIA RTX 5070 — show compatible GPU family variants but keep board-partner SKUs separate.
8. PlayStation 5 Slim Disc Edition — reject Digital and non-Slim editions.
9. Samsung 45W USB-C charger — require Samsung and charger product type; reject cable and unrelated brands.
10. TP-Link Archer AX55 router — reject AX50 and unrelated AX55 products.

## Category auto-detection boundary

A few category phrases intentionally overlap between domains. `running shoes` and `sports shoes` default to Sports & Fitness; `smartwatch` and `smart watch` default to Electronics. The shopper-facing forms use automatic domain detection and do not expose the internal domain selector; use a more specific query phrase for ambiguous products. Clear appliance terms such as vacuum cleaner, robot vacuum, air purifier and induction cooktop now default to Home Appliances.

## Recommended local commands (macOS)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m compileall -q app.py config.py database.py core domains integrations services tests scripts
python -m unittest discover -s tests -v
python -m pytest -q --cov=core --cov=domains --cov=services --cov=integrations --cov-report=term-missing
ruff check .
```

Run live read-only provider diagnostics separately:

```bash
python scripts/run_provider_smoke.py
```

## Verification boundary

See `BUILD_REPORT.md` for the exact offline checks executed while creating this archive. The build environment did not have Flask or MCP installed and could not reach the Python package index or external providers. Therefore the Flask route/API/database integration tests, mocked provider tests and live provider smoke checks are not represented as passed. Run the complete suite on the target Mac after installing dependencies and then capture authorized live-provider outcomes.

A successful provider query is evidence for that query only; it does not guarantee the entire domain or retailer catalogue is covered. Confirm product identity, variant, availability, product URL and checkout price manually before public release.

## Homepage/search UX checks

The homepage hides the internal domain count and taxonomy, shows configured shopping sources, and offers a generic product search. Both homepage and comparison-page search fields include a keyboard-accessible clear (×) button. The zero-offer state is highlighted in red and labelled `NO RESULTS`, while provider connection errors remain distinct.

## Seven-step corrective build regression update (2026-11-08)

The focused offline suite now includes all 22 user screenshot queries with expected domain/category routing and positive/negative offer fixtures, query expansion, search-rejection diagnostics, storefront normalization and provider query-variant deduplication. Latest result: **87 passed, 558 subtests passed**. All eight templates parse and Python compilation passes.

Account routes, CSRF, login/logout, guest watch handling and user-scoped watchlist tests have been added to `tests/test_app.py`. They were not executable in the build runtime because Flask/Werkzeug are not installed. SQLite user isolation and legacy watchlist migration were separately exercised with a lightweight `current_app` shim; this is not a substitute for Flask integration tests.

The provider cards distinguish aggregator integration results from merchant storefronts represented by aggregator offers. Unconfigured feeds show as skipped. Rejection diagnostics retain capped examples of filtered titles and explicit reasons. Do not infer live retailer availability from the offline fixtures.
