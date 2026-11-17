"""Search ideas, NLP normalization and catalog regression coverage for all domains.

These offline tests are independent of the retailer APIs and Flask deployment.
"""
import unittest
from collections import Counter
from core.domain_registry import CATEGORY_INDEX, DOMAIN_CATEGORIES, DOMAIN_INDEX
from services.recommendations import (catalogue, fitted_model, recommend, autocomplete,
                                      personalized, normalize_query, domain_samples)


class SixDomainDiscoveryTests(unittest.TestCase):
    def test_every_category_has_more_than_one_search_example(self):
        by_category = Counter(row['category'] for row in catalogue())
        self.assertEqual(len(by_category),61)
        self.assertTrue(all(count >= 2 for count in by_category.values()))
        for domain in DOMAIN_INDEX:
            with self.subTest(domain=domain):
                self.assertTrue(any(row['domain']==domain for row in catalogue()))

    def test_all_category_recommendations_are_in_domain_and_category(self):
        checks=0
        for domain,cats in DOMAIN_CATEGORIES.items():
            for category in cats:
                names=[r['title'] for r in catalogue() if r['category']==category['slug']]
                results=recommend(names[0],domain=domain,category=category['slug'],limit=4)
                with self.subTest(domain=domain,category=category['slug']):
                    self.assertTrue(results)
                    self.assertTrue(all(r['domain']==domain and r['category']==category['slug'] for r in results))
                    self.assertNotIn(names[0],[r['title'] for r in results])
                    checks+=1
        self.assertEqual(checks,61)

    def test_all_catalogue_product_prefixes_in_autocomplete(self):
        for row in catalogue():
            with self.subTest(row=row['title']):
                prefix=row['title'][:max(6,len(row['title'])//2)]
                self.assertIn(row['title'],[r['title'] for r in autocomplete(prefix,limit=6)])

    def test_six_domains_have_homepage_discovery(self):
        samples=domain_samples()
        self.assertEqual(set(samples),set(DOMAIN_INDEX))
        for rows in samples.values():
            self.assertTrue(rows)

    def test_similarity_avoids_accessory_cross_category(self):
        queries=[
            ('Samsung Galaxy S25 256GB','phones'),
            ('Sony WH1000XM5','audio'),
            ('Atomic Habits','books-fiction'),
            ('Nike Air Force 1 White UK 8','fashion-footwear'),
            ('LG 8kg washing machine','appliances-washing-machines'),
            ('Wakefit queen size mattress','home-mattresses'),
            ('Yonex Astrox 99 badminton racket','sports-badminton'),
        ]
        for q,expected_category in queries:
            with self.subTest(query=q):
                rows=recommend(q,limit=5)
                self.assertTrue(rows)
                self.assertTrue(all(r['category']==expected_category for r in rows),rows)

    def test_typo_and_alias_normalization(self):
        self.assertEqual(normalize_query('One Plus 13R 256 GB'),normalize_query('OnePlus 13R 256GB'))
        self.assertEqual(normalize_query('Sony WH 1000 XM5'),normalize_query('Sony WH1000XM5'))
        self.assertEqual(normalize_query('iPhone16 128 GB'),normalize_query('iPhone 16 128GB'))

    def test_recommendations_contain_no_fake_prices_or_retail_links(self):
        for row in recommend('Sony WH-1000XM5',limit=6):
            self.assertNotIn('price',row)
            self.assertNotIn('url',row)
            self.assertNotIn('retailer',row)

    def test_personalized_history_returns_relevant_and_unique_queries(self):
        results=personalized([{'query':'Atomic Habits paperback English'}, {'query':'Sony WH-1000XM5'}])
        self.assertGreaterEqual(len(results),2)
        self.assertEqual(len(set(x['title'] for x in results)),len(results))

    def test_blank_queries_safe(self):
        self.assertEqual(recommend(''),[])
        self.assertEqual(autocomplete('a'),[])
        self.assertEqual(personalized([]),[])

    def test_model_fitted_over_125_entries(self):
        self.assertEqual(len(fitted_model().vectors),len(catalogue()))
        self.assertEqual(len(catalogue()),125)

if __name__=='__main__':
    unittest.main()
