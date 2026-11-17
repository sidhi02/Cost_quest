# Cost Quest — Backend Architecture

## Design principles

1. Shared search and persistence infrastructure; independent domain-specific identity rules.
2. Fail closed for explicit configuration constraints: if the query requests a size, capacity, edition, storage amount or identifier and the offer does not prove it, reject the offer.
3. Keep exact products, equivalent configurations and merely similar products separate.
4. Never invent offers, prices, stock states or provider coverage.
5. Provider failures are isolated; one provider must not fail the complete search.
6. Keep provider data, normalized offers and canonical comparison groups conceptually distinct.

## Search flow

```text
HTTP request
  -> validate query/domain/category
  -> resolve domain and category
  -> fan out to configured provider adapters
  -> map responses to normalized INR offers
  -> validate URLs, price, retailer and currency
  -> normalize title and domain-specific attributes
  -> reject category / brand / model / attribute mismatches
  -> deduplicate retailer listing URLs
  -> group only conservative comparable configurations
  -> rank in-stock offers before unknown/out-of-stock offers
  -> persist price observation
  -> render HTML or JSON response
```

## Shared offer contract

Core required fields: `name`, `price`, `url`, `retailer`, `currency`, `availability`. Optional data includes `brand`, `sku`, `image`, source timestamps and provider-supplied attributes. Every adapter must return INR prices as numeric values and validated HTTP(S) product URLs. Offers with malformed or non-INR prices are rejected.

## Domain contracts

| Domain | Identity / configuration signals |
|---|---|
| Electronics | Model signature, generation, storage, RAM, screen size, connectivity, edition, wattage and board partner |
| Fashion & Lifestyle | Brand, category, clothing/shoe size, size scale, gender/fit, material, colour and product quantity |
| Home Appliances | Brand/model, capacity, tonnage, load type, inverter state, energy rating and dimensions |
| Books & Stationery | ISBN-10/13, title, edition, language, binding and pack count |
| Sports & Fitness | Product type, sport, weight, footwear size/scale, material and pack count |
| Furniture & Home | Product type, size, dimensions, material, finish and seat count |

Attribute extraction is intentionally deterministic in this release. It does not infer missing dimensions or manufacturer specifications from images. Domain rules can be extended with verified catalog/GTIN data later.

## Comparison identity

The comparison key includes domain, selected category, detected product identity and extracted variant attributes. Electronics model signatures and book ISBNs provide stronger identity signals. RTX GPU partner models remain separate groups. For other products without stable manufacturer IDs, normalized title and available attributes are used conservatively; this can miss a valid cross-retailer grouping, but avoids claiming equivalence without evidence.

## Provider orchestration

Provider adapters expose `status()` and `search(query)`. The comparison service runs adapters concurrently with bounded provider-level request timeouts, collects provider-specific errors, maps returned results, and applies a shared matching pipeline. `mapped_count` means offers mapped by an adapter into Cost Quest's offer schema; it is not necessarily the source's raw HTTP/MCP row count. `accepted_count` means locally relevant offers after matching.

`domain_coverage` stays `unverified` unless an explicit live search for that domain has established a result. A configured credential/feed is not proof of supported product coverage.

## Persistence

SQLite tables:

- `price_history`: append-only price observations, domain and category metadata.
- `watchlist`: saved retailer offers.
- `search_rate_limits`: hashed client key and fixed-window request count.
- `schema_migrations`: applied schema version records.

The database initializer adds domain/category columns to older price-history databases without deleting existing records. Before production deployment, back up the database and validate migrations on a copy.

## Security boundaries

- `.env` is external configuration and must never enter the ZIP/source control.
- POST forms are CSRF-protected.
- Watchlist product URLs must be HTTPS and credential-free.
- JSON feeds are administrator-configured HTTPS endpoints, reject local/private literal hosts and redirects, and are not accepted as user-entered URLs.
- Provider request errors are not exposed verbatim.
- Search traffic uses a fixed-window rate limit keyed by an HMAC of the remote address; reverse-proxy deployments must configure trusted network boundaries rather than blindly trust forwarded headers.
- Deploy behind HTTPS, set a cryptographically random `SECRET_KEY` (32+ characters), and use a production WSGI server. Production rejects disabled CSRF, debug mode, weak secrets and insecure session cookies.

## Scaling boundary

This is a modular monolith. The bounded thread pool and SQLite work for a modest single-instance deployment. For multi-instance or high-volume use, move persistence/rate limits to PostgreSQL, add distributed caching/queueing only where measured load requires it, add provider circuit breakers/observability and enforce provider-specific rate budgets.


## Search diagnostics and storefront attribution

Search integrations are distinct from retailer storefronts. PriceInIndia is an aggregator; its offers can originate from Croma, Reliance Digital, Amazon, Tata CLiQ and other marketplaces. Provider cards therefore report connection state, offers returned, offers accepted, rejected offers, duplicates and rejection reasons by integration. A separate storefront breakdown counts retailer names represented by accepted offers. Unconfigured direct APIs are skipped and shown as not connected; they are not reported as a successful zero-result search.

Product matching returns rejection diagnostics by reason. Requested attributes that conflict with a candidate are rejected. Some missing attributes are marked unverified and the offer is not eligible for lowest-price ranking. A requested size with no confirmation is rejected because size is a critical variant. Search expansion is bounded to three phrases per query and always keeps the original query; the matcher evaluates offers against the original request.

## Authentication boundary

Accounts are optional for search. Registration and login use Werkzeug scrypt password hashes, CSRF-protected forms, session rotation, fixed-lifetime sessions and HMAC-keyed IP/IP-email attempt rate limits. Watchlist rows are scoped by user ID. Price observations are product-wide snapshots rather than private user activity. The current version does not provide email verification, password recovery, MFA or social login.


## NLP and deep-learning product intelligence

The matching engine calls `services/product_ai/` before deterministic offer validation. The pipeline computes BM25 and character n-gram TF-IDF relevance, extracts product entities, and optionally adds MiniLM embeddings and Cross-Encoder query/listing reranking. AI evidence is carried on accepted offer rows and surfaced in the HTML comparison page and `/api/search` response. Semantic evidence may recover a low lexical-overlap title only after the normal brand/model/category/attribute checks; it cannot override a hard mismatch.

A second, conservative pairwise pass can group titles from the same brand when model identity and all shared extracted attributes are compatible. It requires either a high MiniLM + Cross-Encoder pair score or a trained Siamese score at its validation-selected threshold. Potential model scores are not calibrated identity probabilities. Pair grouping is limited to the top 30 validated candidates per search to bound inference cost.

Stage 3's Siamese head is trained by `scripts/train_siamese_matcher.py` from manually reviewed pairs (`text_a`, `text_b`, `label`, `split_group`). The codebase intentionally contains no fabricated checkpoint. CLIP supports local image paths only under the configured cache directory; the application does not fetch arbitrary provider image URLs on the server. See `docs/PRODUCT_INTELLIGENCE_AI.md` for setup and validation.

The large PyTorch / Transformers stack is an optional extra in `requirements-ai.txt`. Without it, normalization, lightweight NER, BM25, deterministic checks and (when scikit-learn is installed) character TF-IDF still run. Model loading is lazy, and missing weights/packages fall back to the non-neural pipeline.
