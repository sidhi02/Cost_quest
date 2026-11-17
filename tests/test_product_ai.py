import unittest
from unittest.mock import patch

from services.product_ai.engine import ProductIntelligenceEngine
from services.product_ai.normalization import extract_entities, normalize_product_text
from services.product_ai.retrieval import BM25Retriever, char_tfidf_scores


class ProductAINormalizationTests(unittest.TestCase):
    def test_aliases_normalize_different_retailer_spellings(self):
        self.assertEqual(normalize_product_text("Sony WH-1000XM5 Bluetooth Headphones"), normalize_product_text("Sony WH 1000 XM5 Bluetooth Headphones"))
        self.assertEqual(normalize_product_text("TP Link Archer AX55"), normalize_product_text("TP-Link Archer AX55"))

    def test_product_ner_extracts_specifications(self):
        entities = extract_entities("Samsung Galaxy S26 256GB Storage 12GB RAM 45W 6.2 inch 5G")
        self.assertEqual(entities["storage"], "256gb")
        self.assertEqual(entities["ram"], "12gb ram")
        self.assertEqual(entities["wattage"], "45w")
        self.assertEqual(entities["screen_inches"], "6.2 inch")
        self.assertEqual(entities["connectivity"], "5g")

    def test_bm25_retrieval_ranks_relevant_title(self):
        scores = BM25Retriever(["Sony WH1000XM5 noise cancelling headphones", "Wooden dining table", "Sony headphone carry case"]).scores("Sony WH1000XM5 headphones")
        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[0], scores[2])

    def test_character_tfidf_is_available_when_optional_dependency_exists(self):
        scores = char_tfidf_scores("WH-1000XM5", ["WH1000XM5 headphones", "wooden chair"])
        self.assertEqual(len(scores), 2)
        self.assertGreaterEqual(scores[0], scores[1])

    def test_runtime_falls_back_without_transformer_packages(self):
        engine = ProductIntelligenceEngine({"AI_SEMANTIC_ENABLED": "0", "AI_CROSS_ENCODER_ENABLED": "0", "AI_SIAMESE_ENABLED": "0", "AI_CLIP_ENABLED": "0"})
        features = engine.score_candidates("Sony headphones", [{"name": "Sony wireless headphones"}, {"name": "Wooden chair"}], "electronics")
        self.assertEqual(len(features), 2)
        self.assertGreater(features[0]["rank_score"], features[1]["rank_score"])
        self.assertIsNone(features[0]["semantic"])


class FakeEngine:
    def __init__(self, features, pair_scores=None):
        self.features = features
        self.pair_scores = pair_scores or []

    def score_candidates(self, query, offers, domain):
        return self.features

    def compare_title_pairs(self, pairs):
        return self.pair_scores

    def siamese_threshold(self):
        return 0.99

    def status(self):
        return {"stage1": {"state": "test"}, "stage2": {"state": "test"}, "stage3": {"state": "test"}}


class ProductAIMatchingIntegrationTests(unittest.TestCase):
    @staticmethod
    def offer(name, store):
        return {"name": name, "price": 10000, "retailer": store, "url": f"https://{store.lower()}.example/item", "availability": "In stock"}

    def test_semantic_retrieval_can_rescue_wording_difference_after_brand_checks(self):
        from core.matching_engine import process_offers_detailed
        rows = [self.offer("Sony WH1000XM5 wireless Bluetooth over-ear", "Amazon")]
        feature = {"bm25": 0.2, "char_tfidf": 0.3, "semantic": 0.93, "cross_encoder": 0.8, "siamese": None, "clip": None, "entities": {"model_tokens": ["wh1000xm5"]}, "rank_score": 0.7}
        fake = FakeEngine([feature])
        with patch("core.matching_engine.get_engine", return_value=fake):
            products, diagnostics = process_offers_detailed("Sony premium audio device with adaptive sound control", rows, domain="electronics")
        self.assertEqual(len(products), 1)
        self.assertTrue(products[0]["semantic_rescued"])
        self.assertIn("semantic", products[0]["ai_evidence"])
        self.assertIn("intelligence", diagnostics)

    def test_semantic_score_never_overrides_wrong_brand(self):
        from core.matching_engine import process_offers_detailed
        rows = [self.offer("JBL Wireless Noise Cancelling Headphones", "Amazon")]
        feature = {"bm25": 0.2, "char_tfidf": 0.3, "semantic": 0.99, "cross_encoder": 0.99, "siamese": 0.99, "clip": None, "entities": {}, "rank_score": 0.9}
        with patch("core.matching_engine.get_engine", return_value=FakeEngine([feature])):
            products, diagnostics = process_offers_detailed("Sony premium audio device with adaptive sound control", rows, domain="electronics")
        self.assertEqual(products, [])
        self.assertEqual(diagnostics["rejection_reasons"].get("wrong_brand"), 1)

    def test_semantic_score_never_overrides_requested_storage_mismatch(self):
        from core.matching_engine import process_offers_detailed
        rows = [self.offer("Samsung Galaxy S26 128GB 12GB RAM", "Amazon")]
        feature = {"bm25": 0.9, "char_tfidf": 0.9, "semantic": 0.99, "cross_encoder": 0.99, "siamese": 0.99, "clip": None, "entities": {}, "rank_score": 0.9}
        with patch("core.matching_engine.get_engine", return_value=FakeEngine([feature])):
            products, diagnostics = process_offers_detailed("Samsung Galaxy S26 256GB 12GB RAM", rows, domain="electronics")
        self.assertEqual(products, [])
        self.assertIn("attribute_mismatch:storage", diagnostics["rejection_reasons"])

    def test_semantic_grouping_rejects_transitive_match_chains(self):
        from core.matching_engine import _apply_semantic_grouping
        candidates = [
            {"name": "Sony over ear headphones alpha", "brand": "Sony", "domain": "electronics", "category": "headphones", "comparison_key": "a", "unverified_attributes": [], "attributes": {}, "relevance_score": 0.9},
            {"name": "Sony wireless headphones beta", "brand": "Sony", "domain": "electronics", "category": "headphones", "comparison_key": "b", "unverified_attributes": [], "attributes": {}, "relevance_score": 0.8},
            {"name": "Sony noise cancelling headset gamma", "brand": "Sony", "domain": "electronics", "category": "headphones", "comparison_key": "c", "unverified_attributes": [], "attributes": {}, "relevance_score": 0.7},
        ]
        scores = [
            {"semantic": 0.93, "cross_encoder": 0.94, "siamese": None},
            {"semantic": 0.60, "cross_encoder": 0.55, "siamese": None},
            {"semantic": 0.92, "cross_encoder": 0.93, "siamese": None},
        ]
        fake = FakeEngine([], scores)
        self.assertEqual(_apply_semantic_grouping(candidates, "electronics", fake), 1)
        self.assertEqual(candidates[0]["comparison_key"], candidates[1]["comparison_key"])
        self.assertNotEqual(candidates[1]["comparison_key"], candidates[2]["comparison_key"])

    def test_transformer_pair_evidence_can_group_equivalent_retailer_titles(self):
        from core.matching_engine import process_offers_detailed
        rows = [self.offer("Sony Wireless Noise Cancelling Headphones", "Amazon"), self.offer("Sony Bluetooth Over-Ear Noise Cancelling Headset", "Croma")]
        features = [{"bm25": 0.9, "char_tfidf": 0.8, "semantic": 0.9, "cross_encoder": 0.8, "siamese": None, "clip": None, "entities": {}, "rank_score": 0.85} for _ in rows]
        fake = FakeEngine(features, [{"semantic": 0.91, "cross_encoder": 0.92, "siamese": None}])
        with patch("core.matching_engine.get_engine", return_value=fake):
            products, diagnostics = process_offers_detailed("Sony noise cancelling headphones", rows, domain="electronics")
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]["comparison_key"], products[1]["comparison_key"])
        self.assertGreaterEqual(diagnostics["semantic_pair_merges"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
