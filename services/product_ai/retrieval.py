import math
import re
from collections import Counter

from services.product_ai.normalization import normalize_product_text


def _tokens(text):
    return re.findall(r"[a-z0-9]+", normalize_product_text(text))


class BM25Retriever:
    """Small in-memory BM25 implementation; no external search service is required."""
    def __init__(self, documents, k1=1.5, b=0.75):
        self.documents = [_tokens(doc) for doc in documents]
        self.k1, self.b = k1, b
        self.lengths = [len(doc) for doc in self.documents]
        self.avg_length = sum(self.lengths) / max(1, len(self.lengths))
        self.frequencies = [Counter(doc) for doc in self.documents]
        self.df = Counter(token for document in self.documents for token in set(document))

    def scores(self, query):
        terms = _tokens(query)
        count = len(self.documents)
        scores = []
        for frequencies, length in zip(self.frequencies, self.lengths):
            score = 0.0
            for term in terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                inverse = math.log(1 + (count - self.df[term] + 0.5) / (self.df[term] + 0.5))
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / max(self.avg_length, 1))
                score += inverse * frequency * (self.k1 + 1) / denominator
            scores.append(score)
        maximum = max(scores, default=0.0)
        return [score / maximum if maximum else 0.0 for score in scores]


def char_tfidf_scores(query, documents):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True)
        matrix = vectorizer.fit_transform([normalize_product_text(query), *[normalize_product_text(value) for value in documents]])
        return cosine_similarity(matrix[0:1], matrix[1:]).ravel().tolist()
    except Exception:
        return [0.0] * len(documents)
