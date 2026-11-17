# Cost Quest — NLP and Deep-Learning Product Intelligence

Cost Quest uses a staged matching pipeline. The existing domain-specific rules remain authoritative: AI scores assist retrieval and ranking but cannot override an explicit brand, model, category, size, capacity, storage, edition, connectivity or other extracted-attribute mismatch.

## Runtime flow

```text
Provider listings
  -> title normalization and product NER
  -> BM25 + character TF-IDF retrieval
  -> MiniLM sentence embeddings
  -> deterministic identity / variant / category / accessory gates
  -> Cross-Encoder candidate reranking
  -> optional trained Siamese pair classifier
  -> optional CLIP text/image evidence for locally cached images
  -> conservative semantic product grouping
  -> availability and price ranking
```

### Stage 1 — NLP and semantic retrieval

- Unicode/case/punctuation normalization and known product alias normalization.
- Product entity extraction for ISBN, model tokens, storage, RAM, wattage, screen size, capacity, shoe size, edition, quantity and connectivity.
- Domain-specific attribute extractors remain the source of hard variant checks.
- BM25 and character 3–5 gram TF-IDF support candidate retrieval.
- `sentence-transformers/all-MiniLM-L6-v2` provides dense semantic embeddings when the optional AI dependencies and model weights are available.

### Stage 2 — Deep-learning reranking

- `cross-encoder/stsb-distilroberta-base` scores the original query/listing title pair and reranks candidates.
- It is a general sentence-similarity model, not a product-identity classifier. Its output is ranking evidence only; it is not presented as a calibrated probability.
- Semantic rescue is only allowed after brand/model/category/attribute checks and uses a conservative configurable threshold. Thresholds must be evaluated on Cost Quest's labelled product pairs before a launch.

### Stage 3 — learned pair matching and multimodal evidence

- `scripts/train_siamese_matcher.py` trains a shared Sentence Transformer encoder representation with a trainable pair-classification head from labelled pairs.
- The training script uses a group-aware validation split when `split_group` is populated, reports precision/recall/F1, and selects a conservative threshold targeting at least 98% validation precision when possible.
- The checkpoint is written to `artifacts/siamese/siamese_head.pt` with validation metrics. This repository does **not** include a fabricated trained model. Stage 3 becomes active after you collect and review enough real labelled pairs and run training.
- CLIP (`openai/clip-vit-base-patch32`) can compare a listing title with a locally cached product image. It only reads paths inside `AI_CLIP_CACHE_DIR`; it never downloads arbitrary provider URLs, avoiding server-side request forgery risks. Provider adapters can populate `image_path` after applying an approved image-cache policy.
- CLIP contributes a small weight to the relevance-ranking composite but never approves a product identity. It is supporting evidence only and cannot establish storage, size, capacity, edition or any other attribute not visible in an image.

## Installation on macOS / Apple Silicon

Create and activate the project's virtual environment, then install the normal application requirements and optional AI dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-ai.txt
```

PyTorch selects Apple MPS when available; CPU is used as fallback. The first search may download MiniLM and Cross-Encoder model weights from Hugging Face. The initial download requires internet access. For a no-download run, set `AI_SEMANTIC_ENABLED=0` and `AI_CROSS_ENCODER_ENABLED=0`; BM25, TF-IDF (when scikit-learn is installed), normalization and product NER still work.

## Train Stage 3

1. Copy `data/product_matching/product_pairs_template.csv` to `data/product_matching/product_pairs.csv`.
2. Add at least 30 manually verified pairs, including at least 10 positive and 10 negative examples. This is only a technical minimum; a meaningful production evaluation needs a much larger, diverse dataset.
3. Set `split_group` consistently by product family. Include hard negatives for closely related variants and accessories.
4. Run:

```bash
python scripts/train_siamese_matcher.py --data data/product_matching/product_pairs.csv
```

5. Review `artifacts/siamese/siamese_head.metrics.json`. Do not enable automatic semantic grouping from the learned model until the independent validation set has an acceptable false-match rate.
6. Restart the Flask app. The runtime loads the checkpoint lazily and checks that its embedding model matches `AI_EMBEDDING_MODEL`.

The current checkpoint threshold is selected on a validation split; it is not a universal guarantee. Keep an untouched, retailer-separated holdout set for the final evaluation and recalibrate after each model/data change.

## Configuration

See `.env.example` for `AI_SEMANTIC_ENABLED`, `AI_CROSS_ENCODER_ENABLED`, `AI_SIAMESE_ENABLED`, `AI_CLIP_ENABLED`, model identifiers, checkpoint/cache paths and rescue thresholds. CLIP is disabled by default because it is heavier and needs pre-cached local images. All AI model loading is lazy. If an optional package or model is unavailable, the search falls back to the lexical/deterministic matching path and exposes the stage state on the comparison page and `/api/search` response.

## What the scores mean

- BM25 and TF-IDF: lexical candidate relevance.
- Semantic score: cosine similarity between embeddings.
- Cross-Encoder score: model-specific reranking value (the configured STS model output is scaled from its 0–5 range); it is not a calibrated identity probability.
- Siamese score: sigmoid output from the trained pair head; not calibrated unless a separate calibration process is run.
- CLIP score: cosine similarity between text and image embeddings.

None of these values is an identity probability. A false match is costlier than a missed comparison, so the rules are intentionally conservative.

## Validation checklist

- Positive and hard-negative pairs across all six domains.
- Exact model/variant/size/capacity/edition/accessory rejection tests.
- Precision, recall, F1, false-match rate and recall@10 for retrieval.
- Results split by domain and retailer; do not randomly split near-duplicate listings from one product family across train/test.
- Compare lexical-only baseline, Stage 1, Stage 1+2, and Stage 1+2+3 on the same fixed holdout set.
- Measure search latency and model memory on the actual Mac M4 deployment environment.
