# Cost Quest product coverage

Last updated: 2026-11-08

## Local catalogue coverage

The local catalogue includes six domains and 61 category definitions. This describes query classification and local matching rules, not guaranteed live inventory.

| Domain | Categories | Example coverage | Key matching safeguards |
|---|---:|---|---|
| Electronics | 20 | Phones, laptops, tablets, audio, components, TVs, cameras, networking, wearables, gaming, printers, accessories | Brand/model family, storage, RAM, wattage, dimensions, connectivity, edition and accessory exclusion |
| Fashion & Lifestyle | 7 | Clothing, footwear, bags, watches, eyewear, jewellery, beauty | Brand, apparel/shoe size and scale, gender, material, colour, quantity, bag dimensions/type, watch type, eyewear/lens type and ring size |
| Home Appliances | 10 | Refrigerators, washers/dryers, ACs, microwaves, dishwashers, vacuums, kitchen appliances, purifiers, heaters | Litre/kg capacity, tonnage, star rating, power, dishwasher place settings, load type, inverter state and appliance subtype |
| Books & Stationery | 8 | Textbooks, exam prep, fiction, reference, notebooks, writing, art/craft, office/school supplies | ISBN, edition, language, binding/format, pack quantity, exam type, writing-instrument type, calculator type and page count |
| Sports & Fitness | 8 | Gym equipment, footwear, cycling, yoga, cricket, badminton, football, protective gear | Product type, sport, weight, size/scale, material, pack quantity, gear count, yoga-mat thickness, glove weight and cycle type |
| Furniture & Home | 8 | Sofas, beds, mattresses, dining, office/study, storage, lighting, décor | Product type, size, dimensions, material, seat count, wardrobe door count and lighting power |

## Matching and data-integrity rules

- Explicit query constraints such as model, brand, size, capacity, edition, ISBN, weight, connectivity or material are treated as hard constraints when the extractor can identify them.
- A product title mapped to a different category is rejected for an explicitly selected category.
- Device searches exclude known accessories unless an accessory is explicitly requested.
- Chargers, cables and power banks are separate product types.
- Electronics model signatures and book ISBNs provide stronger identity signals. RTX GPU partner models remain separate comparison groups.
- For products without stable identifiers, comparison grouping uses a normalized title-token fingerprint plus extracted attributes. This is intentionally conservative and can miss some equivalent cross-retailer listings.
- Duplicate retailer listing URLs are removed.
- In-stock offers are preferred for lowest-price ranking. Out-of-stock-only groups do not receive an available-lowest badge.
- Invalid/non-positive/non-finite prices, non-INR offers, credentialed/invalid product URLs and invalid image URLs are rejected or sanitized.
- Provider mapped counts and locally accepted/filtered counts are reported separately. A mapped offer is not necessarily relevant.

## Offline product validation

The product matrix tests one representative positive offer and a materially different negative offer for each of the 61 category definitions. It additionally tests all 451 category search phrases with an explicit domain/category, 6 cross-domain accessory-rejection cases and the ten original electronics search regressions. The latest selected offline suite reports 87 test methods passed and 558 subtests passed. These are synthetic/local fixture tests, not actual retailer search results.

Automatic detection intentionally resolves a few ambiguous phrases to a default domain. Use a more specific phrase for `running shoes`, `sports shoes`, `smartwatch` or `smart watch` when the automatic choice does not match the intended product. `Atomic Habits`/`James Clear` titles and coffee-table searches are now included in automatic routing regression tests.

## Live coverage limitations

Actual listings depend on provider inventory, query interpretation, provider terms and any authorized retailer feeds configured by the operator. The app cannot guarantee a result for every product, category, retailer or variant. A zero-result search remains valid; do not substitute fabricated offers.

Amazon, Flipkart, Croma and Reliance Digital direct connections require current approved credentials or authorized feed URLs. PriceInIndia is a third-party aggregator, not an official API for every retailer represented in its results. Review current terms for attribution, caching, display and redistribution before public launch.

## Verification status

See `BUILD_REPORT.md` and `docs/QA_AND_RELEASE_GATES.md` for exact test outcomes and environment limitations. Local catalogue/matching tests do not prove live retailer coverage, current stock, product-page correctness or checkout price.

## Corrective build update (2026-11-08)

The comparison form now auto-detects each new query and does not carry stale domain/category values into the next search. Unknown products resolve to `General Shopping` rather than defaulting to Electronics. Books, appliances, sports, fashion and furniture routing include screenshot-driven title/author/model terms.

Provider diagnostics now include per-connection states, mapped/accepted/rejected/duplicate counts, rejection reason totals and a capped list of rejected title examples. PriceInIndia is clearly labelled as an aggregator; the actual retailer storefront breakdown is separate. Unconfigured direct feeds are skipped rather than presented as providers that returned zero offers.

Controlled query expansion generates up to three domain-aware queries, retains the original phrase first, and deduplicates query-variant results. Offer deduplication preserves distinct SKU variants on the same product URL. The new account flow includes email/password registration/login and account-scoped watchlists; it does not yet include verification, password recovery or MFA.

The latest focused offline suites report **87 passed, 558 subtests passed**. Eight Jinja templates compile. Full Flask tests and all live-provider checks remain unverified in the build environment; see `BUILD_REPORT.md`.


## Provider category-filter boundary

PriceInIndia's `search_products` category filter expects a PriceInIndia category group ID or category name, not Cost Quest's internal category slugs. The adapter therefore does not pass internal slugs as upstream categories. It searches using controlled natural-language query variants, then applies Cost Quest domain/category and variant validation locally. Provider schema reference: https://www.priceinindia.website/mcp (reviewed 2026-11-08).
