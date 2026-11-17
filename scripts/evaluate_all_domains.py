"""Run repeatable, offline six-domain QA with labelled product-pair fixtures.

The fixtures are synthetic and are also used by the existing regression tests.
This script measures regression consistency, not real-world retail coverage or
independent ML generalization. Execute in the project folder with Python 3.
"""
import json
from collections import Counter
from pathlib import Path
from core.domain_registry import DOMAIN_CATEGORIES
from services.product_intelligence import process_offers
from services.recommendations import catalogue, autocomplete, recommend

BASE = Path(__file__).resolve().parent.parent


def offer(name, retailer, ident):
    return {'name': name, 'price': 1000, 'retailer': retailer,
            'url': 'https://example.com/qa/' + str(ident),
            'availability': 'Available'}


def evaluate():
    samples = json.loads((BASE / 'data/evaluation/retailer_title_fixtures.json').read_text())
    totals = Counter()
    domain_stats = {name:Counter() for name in DOMAIN_CATEGORIES}
    failures = []
    for i, case in enumerate(samples):
        rows = process_offers(case['query'], [offer(case['positive'], 'Test A',f'{i}/positive'),
                                                 offer(case['negative'], 'Test B',f'{i}/negative')],
                              domain=case['domain'], category=case['category'])
        names = {row['name'] for row in rows}
        tp = int(case['positive'] in names)
        fn = int(case['positive'] not in names)
        fp = int(case['negative'] in names)
        tn = int(case['negative'] not in names)
        domain_stats[case['domain']].update(tp=tp,fn=fn,fp=fp,tn=tn)
        totals.update(tp=tp,fn=fn,fp=fp,tn=tn)
        if fn or fp:
            failures.append({'domain':case['domain'],'category':case['category'],'query':case['query'],
                             'false_negative':bool(fn),'false_positive':bool(fp)})
    p = totals['tp'] / max(1,totals['tp']+totals['fp'])
    r = totals['tp'] / max(1,totals['tp']+totals['fn'])
    f1 = 2*p*r / (p+r) if p+r else 0
    cat_coverage = {d:len(cats) for d,cats in DOMAIN_CATEGORIES.items()}
    idea_coverage = Counter(row['domain'] for row in catalogue())
    smoke = {'total':0,'top_6_prefix_hits':0}
    for row in catalogue():
        query = row['title'][:max(6,len(row['title'])//2)]
        results = autocomplete(query,limit=6)
        smoke['total'] += 1
        smoke['top_6_prefix_hits'] += int(any(x['title']==row['title'] for x in results))
    output = {'type':'Offline synthetic fixture and in-catalogue smoke evaluation',
              'fixtures':len(samples), 'across_domains':list(DOMAIN_CATEGORIES),
              'category_coverage':cat_coverage, 'suggestion_corpus_by_domain':dict(idea_coverage),
              'classification':{'tp':totals['tp'],'fp':totals['fp'],'fn':totals['fn'],'tn':totals['tn'],
                                 'precision':round(p,4),'recall':round(r,4),'f1':round(f1,4)},
              'by_domain':{d:dict(stats) for d,stats in domain_stats.items()},
              'autocomplete_prefix_smoke':smoke,'failures':failures,
              'limitations':'These 61 labelled fixtures are regression examples, NOT retailer-independent benchmark data. Prefix smoke uses catalogue items that are in the TF-IDF corpus. No live API or price correctness was tested.'}
    path=BASE/'artifacts/search_models/offline_qa_report.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps({k:output[k] for k in ('fixtures','category_coverage','suggestion_corpus_by_domain','classification','autocomplete_prefix_smoke')},indent=2))
    return output


if __name__=='__main__':
    evaluate()
