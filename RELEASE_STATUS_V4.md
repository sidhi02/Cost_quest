# Cost Quest V4 — honest release status

**Status: tested local portfolio prototype; NOT production-certified.**

### Implemented or strengthened in V4
- More precise model identifiers for JBL Tune, Logitech MX Master and Yonex Astrox.
- Gaming laptop/RTX category resolution, wearable case sizes, sports pack quantities and gram weights.
- Conservative best-price eligibility; invalid price, unavailable stock, and unknown confidence do not win.
- Guest-friendly shopping site, cross-domain TF-IDF suggestions, similar-product discovery, manual colour choice, lowest price first, retailer filter, always-visible clear action.
- Opt-in personal search-history and watchlist retained; added protected, read-only `/admin` dashboard requiring `ADMIN_EMAILS` with an authorized registered account.
- Error handlers for 400/403/404/429/500 and accessible focus outlines.
- All-domain unit tests and desktop/mobile offline Chromium QA screenshots.

### Validated
- 144 passing offline Python tests, 757 subtests; three Flask-dependent test modules skipped here.
- 61 legacy + 36 new synthetic positive/negative matching fixtures passed after fixes.
- 13 Jinja page states and mobile/desktop browser screening completed; generated browser report in `artifacts/browser_qa/report.json`.

### NOT validated / still missing
- Live retailer API availability and broad crawling permissions; no credentials are bundled.
- Actual end-to-end Flask routes, emails, PostgreSQL migration, production scheduler, price alerts and HTTPS deployment.
- Robust production neural product matching (experimental domain classifier only, with 57.6% grouped holdout accuracy).
- Full checkout price accuracy, security audit and production performance/load test.

See `docs/QA_REPORT_V4.md` for complete evidence and test commands. Do not describe this ZIP as deployed or production-certified on a resume.
