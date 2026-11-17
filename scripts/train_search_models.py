"""Train / evaluate an experimental cross-domain NLP classifier.

This trains only a domain classifier on 125 curated *search ideas*. It is NOT a
Siamese product identity model, does not learn live prices, and must not override
verified retailer specification checks. The category-group holdout reduces
memorization of exact product families in the evaluation.

Run: python -m scripts.train_search_models
Optional dependency: scikit-learn, joblib (requirements-ai.txt)
"""
import json
from collections import Counter
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline

from services.recommendations import catalogue, normalize_query

BASE = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = BASE / 'artifacts' / 'search_models'


def train():
    import joblib
    records = catalogue()
    names = [normalize_query(row['title']) for row in records]
    labels = [row['domain'] for row in records]
    groups = [row['category'] for row in records]
    split = GroupShuffleSplit(n_splits=1, test_size=.25, random_state=24)
    train_idx, test_idx = next(split.split(names, labels, groups))

    def build():
        return Pipeline([
            ('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5), lowercase=True,
                                      sublinear_tf=True, min_df=1)),
            ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=24))
        ])

    pipeline = build()
    pipeline.fit([names[i] for i in train_idx], [labels[i] for i in train_idx])
    expected = [labels[i] for i in test_idx]
    predicted = pipeline.predict([names[i] for i in test_idx]).tolist()
    classes = sorted(set(labels))
    report = {
        'model': 'TF-IDF character ngrams + logistic regression',
        'evaluation': 'Held-out category groups from curated search ideas (offline only)',
        'examples': len(records),
        'training_examples': len(train_idx),
        'evaluation_examples': len(test_idx),
        'training_categories': len({groups[i] for i in train_idx}),
        'evaluation_categories': len({groups[i] for i in test_idx}),
        'domains': classes,
        'evaluation_domain_counts': dict(Counter(expected)),
        'accuracy': round(float(accuracy_score(expected, predicted)), 4),
        'classification_report': classification_report(expected, predicted, labels=classes, zero_division=0, output_dict=True),
        'confusion_matrix': confusion_matrix(expected, predicted, labels=classes).tolist(),
        'scope_warning': 'Small curated search-idea set. Not representative of live retailer products, end-to-end matching, or production accuracy.'
    }
    # Fit a separate copy on all curated examples only AFTER holdout evaluation.
    final = build()
    final.fit(names, labels)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final, ARTIFACT_DIR / 'experimental_domain_classifier.joblib')
    (ARTIFACT_DIR / 'evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('examples','training_examples','evaluation_examples','training_categories','evaluation_categories','accuracy','evaluation_domain_counts')}, indent=2))
    return report


if __name__ == '__main__':
    train()
