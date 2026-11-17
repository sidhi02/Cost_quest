"""Run once per schedule from cron, a managed scheduler, or a single worker.
Example: python -m scripts.track_prices --limit 50
Do not run concurrently with itself. Only configured authorized providers are used.
"""
import argparse
import json
from app import create_app
from database import list_tracking_queries, record_tracking_run, save_price_snapshots
from services.comparison import search_products


def run(limit=50, dry_run=False):
    app = create_app()
    with app.app_context():
        queries = list_tracking_queries(limit)
        result = {"queries": len(queries), "offers": 0, "errors": 0}
        if dry_run:
            return {**result, "dry_run": True, "product_names": queries}
        for query in queries:
            try:
                products, statuses = search_products(query)
                save_price_snapshots(products)
                result["offers"] += len(products)
                result["errors"] += sum(1 for status in statuses if status.get("state") == "error")
            except Exception:
                result["errors"] += 1
        record_tracking_run(result["queries"], result["offers"], result["errors"])
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(max(1, min(args.limit, 500)), args.dry_run), indent=2))
