# QA, Provider Coverage and Release Gates

## Current offline verification

The local build runtime has Python 3.13, requests, python-dotenv, pytest and pytest-cov. Flask, MCP and ruff are not installed, and the environment cannot reach the Python package index. Therefore:

- Electronics catalogue, matching and ten-search regression tests can run offline.
- New cross-domain matching fixtures can run offline.
- Python compilation can run offline.
- Jinja templates can be parsed offline using the installed Jinja2 package.
- Flask route/API tests, database-under-Flask tests and mocked provider tests cannot be executed in this build runtime because Flask is missing.
- Live PriceInIndia MCP searches cannot run because MCP and external network access are unavailable.
- Amazon, Flipkart, Croma and Reliance Digital live tests require valid credentials/authorized feeds not included in the source archives.

Do not treat a blocked test as a pass. Run the complete test commands on the user's Mac after installing `requirements.txt` and `requirements-dev.txt`.

## Electronics regression cases retained

1. Samsung Galaxy S26 256GB — exclude S26+, Ultra, FE and accessories.
2. Apple Watch — allow different generations in a family search but keep generation/configurations separate.
3. Apple Watch strap — return strap/band accessory products, not watches or unrelated watch accessories.
4. Sony WH-1000XM5 — exclude XM4 and WF-series earbuds.
5. MacBook Air M4 16GB — distinguish Air/Pro, chip and RAM.
6. iPad Air M3 11-inch — preserve generation, screen size, Wi-Fi/Cellular and storage.
7. NVIDIA RTX 5070 — allow board-partner products for family discovery but keep partner SKUs separate.
8. PlayStation 5 Slim Disc Edition — exclude Digital and non-Slim editions.
9. Samsung 45W USB-C charger — require Samsung and charger type; exclude cables and unrelated brands.
10. TP-Link Archer AX55 router — exclude AX50 and unrelated AX55 products.

## New domain regression coverage

- Fashion: brand, clothing/shoe size and scale, gender/fit, material, colour and quantity.
- Home appliances: capacity, AC tonnage, inverter/load type and energy rating.
- Books: ISBN identity, edition, language, binding and pack size.
- Sports: sport/product type, weight, size scale, material and pack count.
- Furniture: mattress/bed size, dimensions, material and seat count.

## Provider smoke test

`scripts/run_provider_smoke.py` sends read-only searches to PriceInIndia. It reports the raw rows returned by that provider for diagnostic purposes. These results are not automatically validated Cost Quest offers and do not establish coverage for every model, retailer or domain.

## Release evidence to capture on macOS

1. Python version and dependency installation success.
2. Complete `python -m unittest discover -s tests -v` output.
3. `python -m pytest -q --cov=core --cov=domains --cov=services --cov=integrations --cov-report=term-missing` report and coverage for core matching/domain logic.
4. `ruff check .` output.
5. Flask smoke checks for `/`, `/health`, `/api/search` validation, compare page, watchlist add/remove and CSRF rejection.
6. Live-provider search outcomes for each of the six domains, showing provider name, mapped count, relevant count, errors and sample product links.
7. Manual check that no incorrect variant or out-of-stock offer is presented as an available lowest price.
8. ZIP integrity and clean-extraction smoke test.

## Go/no-go policy

- **GO for local development:** offline matching, source compilation and template parse checks pass.
- **GO for user acceptance testing:** complete Flask-dependent suite passes on the target Mac; provider smoke test results are recorded; unsupported provider domains are clearly disclosed.
- **GO for public production:** current provider contracts/permissions verified, secrets and HTTPS configured, database backup/migration tested, security and performance gates passed, monitoring/logging in place, and live offers manually sampled for quality.


## Additional acceptance checks for the corrective build

- The 22 saved product queries resolve to the expected domain/category or to General Shopping when no domain is evidenced.
- Unknown products never fall back to Electronics by default.
- Provider cards distinguish completed searches, empty responses, unconfigured connections and errors.
- Aggregator-originated retailer listings appear in a separate storefront breakdown; they are not counted as direct retailer API offers.
- Diagnostics record mapped, accepted, rejected and duplicate counts plus rejection reasons for each provider source.
- A single offer is not described as a price comparison. Potential matches with unverified specifications are not ranked as lowest price.
- Registration/login uses scrypt password hashes, CSRF tokens, session rotation, a 12-hour permanent session lifetime and HMAC-keyed IP/IP-email rate limits. Watchlist rows are not visible to other accounts.
- Guests can search; saving a product prompts authentication and preserves the selected offer until login/registration completes.
- Email verification, password reset and MFA are not included in this release (account deletion is available) and must be added before a public multi-user production launch.
