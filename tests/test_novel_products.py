"""Previously untested products across ALL six domains, no live retailer claims."""
import pytest
from scripts.qa_novel_products import CASES
from services.product_intelligence import process_offers


@pytest.mark.parametrize('domain,query,matching,wrong_variant',CASES)
def test_relevant_and_wrong_variants(domain,query,matching,wrong_variant):
    listings=[{'name':name,'price':1000+i,'availability':'Available','retailer':f'Demo Store {i}',
               'url':f'https://example.com/novel/{i}'}
              for i,name in enumerate((matching,wrong_variant))]
    result=process_offers(query,listings,domain=domain)
    titles={r['name'] for r in result}
    assert matching in titles, f'Rejected genuine title: {query!r}'
    assert wrong_variant not in titles, f'Accepted incompatible variant: {query!r}'
