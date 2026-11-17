# Cost Quest incremental upgrade (November 2026)

## Implemented in this package
- One-shot watchlist-based scheduled price refresh CLI: `python -m scripts.track_prices --dry-run` then run without `--dry-run` under a scheduler. Configure **one** scheduled worker and respect each provider's access rules and rate limits.
- Account JSON export at `GET /account/export` (authenticated), account deletion at `POST /account/delete` (CSRF-protected, `confirmation=DELETE`).
- `services/pricing.py` conservative payable-price estimator. Shipping must be known for a complete estimate; unverified discounts are ignored. This is a reusable service, **not yet wired into the retailer results UI**.
- Tracking-run audit table and tests for pricing.

## Not implemented / not verified
- Live access to Amazon, Flipkart, Croma, Reliance Digital; approved credentials and feeds must be supplied, and endpoint support verified.
- Generic retailer HTML scrapers: a crawler cannot lawfully or reliably guarantee access to every retailer. Use provider-specific permitted sources.
- PostgreSQL migration: current application remains SQLite. Migration needs an adapter/ORM, data migration and concurrency testing.
- Email verification, password reset, mail notifications, trained AI model checkpoint, real price forecasting and recommendation evaluation.
- Payment/shipping/coupon data ingestion and UI integration.
- Full production security/load testing, monitoring, deployment verification, and real-world data quality measurements.

## Before claiming production readiness
1. Configure approved retailer integrations and test real data.
2. Run full tests, integration tests, security review and load tests.
3. Replace SQLite with PostgreSQL for multi-instance deployment and migrate existing records.
4. Configure secure email and complete recovery/verification workflows.
5. Collect consented, labelled training data and evaluate AI against baselines.
6. Configure an HTTPS reverse proxy, managed secrets, backups, alerts and monitoring.

## Scheduler example (Linux cron, every six hours)
`0 */6 * * * cd /path/to/cost_quest && /path/to/venv/bin/python -m scripts.track_prices --limit 50`

Run with a single worker, lock against overlapping executions, and monitor provider rate limits. Avoid polling large catalogues without provider permission.
