"""Privacy-conscious content-based search suggestions for *all six* shopping domains.

The model is a fitted sparse TF-IDF retriever over curated, labelled search
ideas. These suggestions are NOT retailer listings and have no live prices.
No external service, model download, user data or retail credentials are needed.
"""
import json
import math
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from core.domain_registry import CATEGORY_INDEX, DOMAIN_CATEGORIES, DOMAIN_INDEX, resolve_search_scope

IDEAS_PATH = Path(__file__).resolve().parent.parent / 'data' / 'search_ideas.json'
ALIASES = (
    (r'\bone\s+plus\b', 'oneplus'),
    (r'\biphone\s*(\d+)\b', r'iphone \1'),
    (r'\bwh[\s-]*1000[\s-]*xm[\s-]*(\d)\b', r'wh1000xm\1'),
    (r'\b(\d+)\s+(gb|tb|kg|inch|mm|l|w)\b', r'\1\2'),
    (r'\bmac\s*book\b', 'macbook'),
    (r'\bair\s+conditioner\b', 'ac'),
)


def normalize_query(text):
    """Canonicalize common human spellings without discarding SKU digits."""
    text = re.sub(r'[^\w\s]+', ' ', str(text or '').casefold())
    for pattern, repl in ALIASES:
        text = re.sub(pattern, repl, text)
    return ' '.join(text.split())


def features(text):
    """Word and char n-grams, robust to hyphens, spacing and minor typos."""
    clean = normalize_query(text)
    words = re.findall(r'[a-z0-9]+', clean)
    result = Counter('w:' + word for word in words if len(word) > 1)
    for word in words:
        if len(word) >= 4:
            for n in (3, 4):
                result.update('c:' + word[i:i+n] for i in range(len(word)-n+1))
    return result


class FittedTfidf:
    """Small, inspectable TF-IDF model (fit on product names; sparse vectors)."""

    def __init__(self, documents):
        rows = [features(d) for d in documents]
        n = len(rows)
        df = Counter()
        for row in rows:
            df.update(row.keys())
        self.idf = {term: math.log((n+1)/(freq+1))+1 for term, freq in df.items()}
        self.vectors = [self.transform(row) for row in rows]

    def transform(self, words):
        words = features(words) if isinstance(words, str) else words
        weights = {term: (1 + math.log(count)) * self.idf.get(term, 0)
                   for term, count in words.items() if count > 0 and term in self.idf}
        magnitude = math.sqrt(sum(v*v for v in weights.values())) or 1
        return {term: v/magnitude for term, v in weights.items()}

    def score(self, query):
        vector = self.transform(query)
        return [sum(weight * doc.get(term, 0) for term, weight in vector.items())
                for doc in self.vectors]


@lru_cache(maxsize=1)
def catalogue():
    items = json.loads(IDEAS_PATH.read_text(encoding='utf-8'))
    if not items or any(row['category'] not in CATEGORY_INDEX or
                        CATEGORY_INDEX[row['category']]['domain'] != row['domain'] for row in items):
        raise ValueError('Invalid multi-domain recommendation catalogue')
    return tuple(items)


@lru_cache(maxsize=1)
def fitted_model():
    return FittedTfidf([row['title'] + ' ' + CATEGORY_INDEX[row['category']]['name'] for row in catalogue()])


def _format(row):
    return {'title': row['title'], 'domain': row['domain'], 'domain_name': DOMAIN_INDEX[row['domain']]['name'],
            'category': row['category'], 'category_name': CATEGORY_INDEX[row['category']]['name']}


def recommend(query, *, limit=6, domain=None, category=None, exclude_exact=True):
    """Return relevant suggested SEARCHES, never pretend they're offers/prices.

    Same-category examples have priority so recommendations never become a
    cross-category jumble. Requests with unknown category use learned text
    similarity, and can recommend from all six domains.
    """
    query = str(query or '').strip()[:160]
    if not query:
        return []
    scores = fitted_model().score(query)
    rows = catalogue()
    if category in CATEGORY_INDEX:
        domain = CATEGORY_INDEX[category]['domain']
    else:
        inferred_domain, inferred_category = resolve_search_scope(query, domain)
        category = inferred_category['slug'] if inferred_category else None
        domain = inferred_domain if inferred_domain in DOMAIN_INDEX else None
        # Recognize named products even if the query omits a category word.
        # This is *discovery*, never evidence of an exact retailer match.
        if not category and scores:
            best_idx = max(range(len(scores)), key=lambda i: scores[i])
            if scores[best_idx] >= .30 and (not domain or rows[best_idx]['domain'] == domain):
                domain, category = rows[best_idx]['domain'], rows[best_idx]['category']
    options = []
    normalized = normalize_query(query)
    for i, row in enumerate(rows):
        title_norm = normalize_query(row['title'])
        if exclude_exact and (title_norm == normalized or
                              (len(normalized) >= 10 and len(normalized.split()) >= 2 and
                               title_norm.startswith(normalized + ' '))):
            continue
        # Product discovery across domains is possible for ambiguous queries;
        # a confidently detected domain must be respected.
        if domain and row['domain'] != domain:
            continue
        if category and row['category'] != category:
            continue
        match = scores[i]
        if match <= 0 and not category:
            continue
        options.append((match, row['title'].casefold(), i))
    options.sort(key=lambda v: (-v[0], v[1]))
    return [_format(rows[i]) for _, _, i in options[:max(0, min(int(limit), 12))]]


def autocomplete(query, *, limit=6):
    """NLP suggestions; no network lookup, used by the input drop-down."""
    query = str(query or '').strip()
    if len(query) < 2:
        return []
    normalized = normalize_query(query)
    rows = catalogue()
    scores = fitted_model().score(query)
    ranked = []
    for i, row in enumerate(rows):
        title = normalize_query(row['title'])
        tokens = set(normalized.split())
        # Prefix and phrase matches are particularly valuable for typing.
        prefix = 3 if title.startswith(normalized) else 2 if normalized in title else 0
        if scores[i] > .04 or prefix:
            ranked.append((prefix + scores[i], row['title'].casefold(), i))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    return [_format(rows[i]) for _, _, i in ranked[:max(0, min(int(limit), 10))]]


def personalized(history, *, limit=6):
    """Recommendations based only on *opted-in* account search history."""
    picks = []
    seen = set()
    for query in list(history)[:6]:
        text = query['query'] if isinstance(query, dict) else str(query)
        for item in recommend(text, limit=4):
            key = normalize_query(item['title'])
            if key not in seen and key != normalize_query(text):
                seen.add(key)
                picks.append(item)
                if len(picks) == limit:
                    return picks
    return picks


def domain_samples(limit=3):
    """Homepage cards for every domain (suggested searches, not stock)."""
    result = defaultdict(list)
    for item in catalogue():
        if len(result[item['domain']]) < limit:
            result[item['domain']].append(_format(item))
    return dict(result)
