# Cost Quest — Agreed Development Order

Implementation order is fixed. Complete the acceptance criteria for a phase before progressing to the next phase.

## Phase 0 — Source audit and baseline consolidation

- Compare the Full Audit Release Candidate and Consolidated QA Release.
- Preserve the stronger offer validation, provider diagnostics and ten-product electronics regression tests from the QA release.
- Reuse the broader 20-category electronics catalog and specification extraction from the Full Audit candidate.
- Keep the original project and user `.env` outside the development copy; never overwrite a user's local secrets.
- Record existing limitations and maintain one canonical working copy.

**Current status:** archive comparison completed and the working tree consolidated; the two archives were not blindly overlaid.

## Phase 1 — Backend architecture and domain registry

- Introduce shared domain registry, query parser and offer schema.
- Keep one catalog and attribute extractor per domain.
- Keep the existing Flask application and SQLite persistence model.
- Add schema-version tracking and backward-compatible price-history columns.
- Avoid creating microservices or changing frameworks without evidence.

**Acceptance:** all six domains resolve, category slugs are unique, normalized offers follow one schema, and older SQLite history survives initialization.

## Phase 2 — Shared search, matching and comparison engine

- Normalize titles, brand aliases and provider attributes.
- Enforce explicit model and configuration constraints.
- Reject unrelated categories and accessory noise.
- Deduplicate repeated retailer URLs.
- Distinguish exact configurations from family-level/similar results.
- Rank in-stock offers first; do not call out-of-stock prices the lowest available price.
- Isolate provider failures and report mapped versus accepted counts honestly.

**Acceptance:** golden positive/negative fixtures pass across all domains; comparison keys do not collapse known variants.

## Phase 3 — Six product domains

1. Electronics — retain the ten user-supplied searches and twenty category families.
2. Fashion & Lifestyle — clothing, footwear, bags, watches, eyewear, jewellery, beauty/personal care.
3. Home Appliances — refrigerators/freezers, washers/dryers, ACs, ovens, dishwashers, vacuums, kitchen appliances, purifiers and water heaters.
4. Books & Stationery — textbooks, exam prep, fiction/non-fiction, reference books, notebooks, writing, art/craft and office/school supplies.
5. Sports & Fitness — gym equipment, footwear, cycling, yoga, cricket, badminton, football and protective gear.
6. Furniture & Home — sofas, beds, mattresses, dining, office/study furniture, storage, lighting and décor.

**Acceptance:** each domain has category taxonomy, attribute extraction, explicit negative matching cases and regression tests. Local implementation does not imply provider live coverage.

## Phase 4 — Retailer integrations and coverage intelligence

- Preserve PriceInIndia, Amazon Creators API, Flipkart Affiliate API and authorized JSON-feed adapters.
- Require current credentials/permission for direct retailer feeds.
- Distinguish adapter configured, adapter reachable, mapped offers and accepted offers.
- Keep per-domain coverage unverified until live search evidence exists.
- Check provider terms, attribution, caching and redistribution permissions.

**Acceptance:** mocked provider contract tests pass; live smoke tests are separately executed and documented when authorized access/network is available.

## Phase 5 — Database and application backend

- Versioned/backward-compatible SQLite schema.
- Price observations include domain/category.
- Watchlist remains persistent.
- Repository/service boundaries stay clear and avoid database writes in matching code.
- Health endpoint reports database health only, not assumed provider health.

**Acceptance:** persistence, migration, history and watchlist tests pass against an isolated temporary database.

## Phase 6 — Frontend and product experience

- Six-domain home navigation and category links.
- Domain selection plus auto-detection.
- Clear product specifications, stock, retailer and source status.
- Comparison group labels and honest empty-result state.
- History and watchlist remain available.

**Acceptance:** all six domain routes render; forms and links preserve the selected search scope; mobile layouts remain usable.

## Phase 7 — Security, reliability and performance

- Secret management and production secret enforcement.
- CSRF protection, HTTPS-only watchlist URLs and safe redirects.
- Configured feed URL validation and redirect rejection.
- Provider timeouts, failure isolation, sanitized errors and bounded concurrency.
- Search request throttling and safe request size limits.
- Security headers and production HTTPS/Wsgi deployment guidance.
- Load-test before increasing provider concurrency.

**Acceptance:** security regression tests pass; no secrets appear in artifacts/logs; one failed provider does not crash a search.

## Phase 8 — Comprehensive test and verification

- Unit tests for parsers, extractors, matching, grouping and validation.
- Domain-specific positive/negative regression tests.
- Provider contract tests with mocked responses.
- Flask route/API/database integration tests.
- CSRF, SSRF, invalid URL, rate-limit and unsafe redirect tests.
- Performance tests with bounded provider latency.
- Live provider smoke tests, clearly separated from offline test results.
- Manual acceptance workflow on macOS.

**Acceptance:** mandatory suites green; core matching coverage target >=90%; overall project coverage target >=80%; no unresolved critical security issue; provider coverage accurately reported.

## Phase 9 — Final release

- Complete source, runtime and development requirements.
- `.env.example`, macOS setup/run instructions, architecture and coverage documentation.
- Tests, fixtures, smoke-test script and verification report.
- Exclude `.env`, databases, caches, virtual environments and machine-specific artifacts.

**Acceptance:** ZIP integrity check passes and the exact release archive is tested from a clean extraction. Do not call the release production-certified unless the runtime, provider and deployment checks have actually passed.


## Corrective release order (locked)

1. Correct domain detection; unknown items must not default to Electronics.
2. Add search/provider diagnostics, including rejection counts and reasons.
3. Add bounded query expansion; preserve the original request and deduplicate results.
4. Improve matching, model/variant validation, duplicate control, broken-image fallbacks and honest single-offer presentation.
5. Run regression tests for all 22 agreed searches plus negative cases.
6. Run application, database, provider, security and performance tests; report blocked live checks separately.
7. Deliver a consolidated ZIP and evidence-based validation report.

Additional UX and account scope for this corrective build: provider cards distinguish aggregator/direct API connections from retailer storefronts represented in results; guest browsing remains enabled; registration/login unlocks account-scoped watchlists.
