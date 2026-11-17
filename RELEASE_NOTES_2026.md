# Cost Quest — Customer comparison refresh

## Implemented in this revision
- Customer search results no longer expose AI model setup, provider errors, or rejection logs.
- Verified offers are sorted by ascending listed price; tied lowest offers receive a best-price label.
- A customer-controlled sort allows highest price or retailer ordering.
- Unverified matches are separated from price-ranked offers.
- Same-price colour variants are grouped **only** when retailer, verified comparison identity and price agree. Original variant links remain accessible.
- Responsive result cards, summary pricing, empty state and transparent price disclaimers.
- Unit tests for the presentation grouping and ranking.

## Existing features retained from the uploaded source
- Flask search, provider adapters, NLP candidate processing, user accounts, watchlists, historical snapshots and associated tests.

## Not completed or externally verifiable
- Direct retailer API connectivity requires retailer authorization and valid credentials. An aggregator listing a retailer is not a direct connection.
- Optional neural model training, checkpoint evaluation, production PostgreSQL migration, Redis worker deployment, live checkout-price verification and real hosted monitoring are not supplied by this revision.
- Production launch requires a security review, secrets, HTTPS deployment, performance tests, legal review of data sources, and end-to-end retailer tests.

## Run on macOS
```bash
cd cost_quest
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python app.py
```
Open http://127.0.0.1:5000. Set safe environment secrets before any public deployment.

## Tests
```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```
