"""Opt-in retailer smoke checks across all six domains.

Default: print the planned searches, no network.
Run: python -m scripts.qa_live_domains --live --per-domain 1
WARNING: Uses the providers YOU have configured. Respect provider terms/limits.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from core.domain_registry import DOMAIN_CATEGORIES
from services.recommendations import catalogue

BASE = Path(__file__).resolve().parent.parent


def main():
    parser=argparse.ArgumentParser(description='Cost Quest six-domain live retailer QA (opt-in)')
    parser.add_argument('--live',action='store_true',help='Perform actual configured provider searches')
    parser.add_argument('--per-domain',type=int,default=1,help='1-3 searches per domain (default 1)')
    parser.add_argument('--output',default='artifacts/search_models/live_qa_report.json')
    args=parser.parse_args()
    per_domain=max(1,min(3,args.per_domain))
    cases=[]
    for domain in DOMAIN_CATEGORIES:
        domain_rows=[item for item in catalogue() if item['domain']==domain]
        # Choose distinct categories when checking multiple examples.
        chosen=set()
        for row in domain_rows:
            if row['category'] in chosen:continue
            chosen.add(row['category'])
            cases.append(row)
            if len(chosen)==per_domain:break
    print('Planned six-domain searches:',json.dumps(cases,indent=2))
    if not args.live:
        print('Dry run only. Add --live to contact configured providers. No fabricated results.')
        return
    from app import app
    from services.comparison import configured_providers,search_products
    from services.presentation import prepare_comparison
    with app.app_context():
        statuses=[p.status() for p in configured_providers()]
        if not any(p.get('configured') for p in statuses):
            print('No configured providers. Cannot verify live retailer coverage.')
            return
        report=[]
        for case in cases:
            started=time.monotonic()
            try:
                offers,status=search_products(case['title'],case['category'],case['domain'])
                verified,uncertain,_=prepare_comparison(offers)
                report.append({'query':case['title'],'domain':case['domain'],'category':case['category'],
                               'total_offers':len(offers),'verified_offers':len(verified),
                               'unverified_offers':len(uncertain),'duration_seconds':round(time.monotonic()-started,2),
                               'sources':status})
            except Exception as exc:
                report.append({'query':case['title'],'domain':case['domain'],'error':type(exc).__name__,
                               'duration_seconds':round(time.monotonic()-started,2)})
            time.sleep(1)  # avoid aggressive back-to-back request bursts
    payload={'tested_at_utc':datetime.now(timezone.utc).isoformat(),'live':True,
             'source_notice':'Aggregator-listed storefronts do not prove direct API access.',
             'cases':report}
    output=BASE / args.output
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,indent=2,default=str),encoding='utf-8')
    print('Results written to',output)

if __name__=='__main__':
    main()
