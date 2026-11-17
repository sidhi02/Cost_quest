# Cost Quest V4 — Independent QA within this environment

## Scope and what was actually tested

This report accompanies the source ZIP. Product data below is **synthetic, hand-labelled test input**, never live retailer pricing or availability. Do not interpret passing these cases as real-world 100% matching accuracy.

### Results

| Check | Result |
|---|---|
| Existing six-domain 61-category fixture evaluation | 61 positive / 61 negative cases passed |
| New unseen-from-legacy product examples | 36 positive / 36 negative variants passed after fixes |
| Python automated suite in this environment | 144 passed, 3 skipped (Flask-dependent), 757 subtests passed |
| Template rendering | 13 page states rendered using Jinja2 StrictUndefined |
| Chromium offline desktop/mobile screen checks | Passed, 18 screenshots saved in `artifacts/browser_qa/` |
| Clear button | Visible and functional on tested homepage and comparison states |
| Retailer filtering and price sorting | Passed in Chromium using synthetic sample offers |
| Same-retailer, same-price colour grouping | Passed offline; separate prices preserved |
| Unverified or unavailable offers | Excluded from lowest-price selection in unit tests |
| JavaScript/Python compilation | Checked during release |
| Flask routes, session integration and APIs | **NOT run** because Flask cannot be installed in this environment |
| Real-time retailer coverage | **NOT run** — no live authorized credentials / accessible providers |
| Production security, load testing, HTTPS | **NOT run** — deployment required |

## New products tested (different from the first five screenshot products)

Each case supplies a different retailer title as positive and an intentionally incorrect variant as negative.

### Electronics

| Search | Positive title accepted | Wrong variant rejected |
|---|:---:|:---:|
| Logitech MX Master 3S Wireless Mouse | ✓ | ✓ |
| Canon EOS R50 Camera | ✓ | ✓ |
| JBL Tune 770NC Headphones | ✓ | ✓ |
| Acer Nitro V 15 RTX 4050 | ✓ | ✓ |
| Samsung Galaxy Tab S9 FE 128GB | ✓ | ✓ |
| Apple Watch Series 9 45mm | ✓ | ✓ |

### Fashion & Lifestyle

| Search | Positive title accepted | Wrong variant rejected |
|---|:---:|:---:|
| Adidas Ultraboost 5 UK 9 | ✓ | ✓ |
| Puma Smash V2 Sneakers UK 8 | ✓ | ✓ |
| Levis 511 Slim Fit Jeans Size 32 | ✓ | ✓ |
| Fastrack Analog Wrist Watch | ✓ | ✓ |
| Ray Ban Polarized Sunglasses | ✓ | ✓ |
| Allen Solly Cotton Shirt Size L | ✓ | ✓ |

### Home Appliances

| Search | Positive title accepted | Wrong variant rejected |
|---|:---:|:---:|
| Voltas 1.5 Ton Inverter AC | ✓ | ✓ |
| Bosch 8kg Front Load Washing Machine | ✓ | ✓ |
| Whirlpool 265L Double Door Refrigerator | ✓ | ✓ |
| Philips 4L Air Fryer | ✓ | ✓ |
| IFB 30L Convection Microwave | ✓ | ✓ |
| LG 5 Star 1.5 Ton Inverter AC | ✓ | ✓ |

### Books & Stationery

| Search | Positive title accepted | Wrong variant rejected |
|---|:---:|:---:|
| Deep Work Paperback English | ✓ | ✓ |
| Ikigai Hindi Paperback | ✓ | ✓ |
| Classmate 200 Pages Notebook Pack of 6 | ✓ | ✓ |
| Oxford English Dictionary 3rd Edition | ✓ | ✓ |
| Cello Gel Pen Pack of 10 | ✓ | ✓ |
| Camlin Scientific Calculator | ✓ | ✓ |

### Sports & Fitness

| Search | Positive title accepted | Wrong variant rejected |
|---|:---:|:---:|
| Yonex Astrox 77 Pro Badminton Racket | ✓ | ✓ |
| Nivia Storm Football Size 5 | ✓ | ✓ |
| Domyos 5kg Dumbbell | ✓ | ✓ |
| Cosco Tennis Balls Pack of 3 | ✓ | ✓ |
| Adidas Football Shoes UK 9 | ✓ | ✓ |
| Wilson Pro Staff 97 315g Racket | ✓ | ✓ |

### Furniture & Home

| Search | Positive title accepted | Wrong variant rejected |
|---|:---:|:---:|
| Wakefit Queen Memory Foam Mattress 78x60 inches | ✓ | ✓ |
| Nilkamal 4 Seater Dining Table | ✓ | ✓ |
| Godrej 3 Door Wardrobe | ✓ | ✓ |
| IKEA LACK Side Table | ✓ | ✓ |
| Durian Leather Sofa 3 Seater | ✓ | ✓ |
| Philips 9W LED Ceiling Light | ✓ | ✓ |

## Seven issues discovered and repaired

1. Logitech MX Master 3S was confused with MX Master 2S; added specific model identifiers.
2. JBL Tune 770NC could match Tune 760NC; added safer model identification.
3. Acer Nitro V laptops with RTX GPUs were misclassified as graphics cards; added laptop-family category detection.
4. Apple Watch 45 mm and 41 mm cases were incorrectly treated as interchangeable; now validate wearable case size.
5. Yonex Astrox 77 Pro and Astrox 99 Pro were matched as the same family; added sports model identity checks.
6. Tennis ball "pack of" quantity was not captured by sports attributes; added pack quantity extraction.
7. Tennis-racket weights stated in grams (315g vs 300g) were not differentiated; added gram-weight extraction.

## ML training and evaluated limitations

- The existing sparse TF-IDF search recommendation model is fitted on 125 curated ideas spanning 61 categories. It suggests searches, not live product offers.
- The *experimental* trained TF-IDF + logistic-regression six-domain classifier was retrained. It scored **57.58%** on category-group-held-out examples (33 test queries), and **91.67%** on 36 new manually written examples. The higher figure does not supersede the more rigorous category-group holdout; the classifier remains **not enabled for production matching**.
- The optional Siamese model has a training script but no independently trained, validated checkpoint. This V4 ZIP does **not** claim a trained production Siamese neural matcher.
- Model/variant safety rules remain the final arbiter for exact matches.

## Browser screening approach

The system Chromium browser rendered the Jinja HTML and exact local CSS/JavaScript (via injected offline assets) at **1440 × 900** and **390 × 844**. The 13 states were homepage, populated comparison, empty comparison, unverified-only comparison, login, registration, account, populated watchlist, empty watchlist, price history, empty history, error, and protected admin.

Browser assertions included no horizontal overflow at either viewport, one H1, always-visible clear button, clearing the query, lowest first, high-to-low price sort, retailer filter, and unverified separate state. Screenshots are evidence of **static rendered templates**, not proof that a live Flask server was running or connected to a retailer.

## Production and release blockers

1. Install Flask and Python dependencies on the target Mac; run the full Flask integration suite.
2. Acquire authorized retailer feeds/API contracts and verify live product prices, dates and URLs across all six domains.
3. Obtain a substantial independent product-pair dataset; train and benchmark neural matching without leakage across retailer/product families.
4. Implement and validate PostgreSQL migrations, centralized rate limiting, scheduled jobs, alerts and backups under deployed conditions.
5. Implement account email verification, secure password reset, and consider MFA before public account launch.
6. Verify actual shipping, location-dependent availability, coupon eligibility and final payable prices; do not label unverified estimates as checkout totals.
7. Run deployed HTTPS, browser end-to-end, security, dependency-audit, load and observability acceptance tests.

## Reproduce on macOS

```bash
cd cost_quest
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m pytest -q
python -m scripts.evaluate_all_domains
python -m scripts.qa_novel_products
python -m scripts.qa_live_domains         # DRY RUN, no network
python app.py
```

To run live provider QA **only after authorized connections are configured**: `python -m scripts.qa_live_domains --live --per-domain 1`.

The optional browser test uses `playwright` and installed Chromium; it is not required for the Flask app to run.
