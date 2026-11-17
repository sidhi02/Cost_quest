import importlib.util
import math
import os
import threading
from pathlib import Path

from services.product_ai.normalization import extract_entities, normalize_product_text
from services.product_ai.retrieval import BM25Retriever, char_tfidf_scores
from services.product_ai.siamese import SiamesePairScorer


class ProductIntelligenceEngine:
    def __init__(self, config=None):
        self.config = config or {}
        self._lock = threading.RLock()
        self._semantic_model = None
        self._cross_encoder = None
        self._semantic_error = None
        self._cross_error = None
        self._clip_matcher = None
        self._clip_error = None
        self._siamese = SiamesePairScorer(self._setting("AI_SIAMESE_CHECKPOINT", "artifacts/siamese/siamese_head.pt"))

    def _setting(self, name, default):
        return self.config.get(name, os.getenv(name, default))

    def _enabled(self, name, default="1"):
        return str(self._setting(name, default)).strip().lower() not in {"0", "false", "no", "off"}

    def _device(self):
        try:
            import torch
            return "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "auto"

    def _load_semantic(self):
        with self._lock:
            if self._semantic_model is not None:
                return self._semantic_model
            if self._semantic_error:
                return None
            try:
                from sentence_transformers import SentenceTransformer
                self._semantic_model = SentenceTransformer(self._setting("AI_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"), device=self._device())
            except Exception as exc:
                self._semantic_error = type(exc).__name__ + ": " + str(exc)[:180]
            return self._semantic_model

    def _load_cross_encoder(self):
        with self._lock:
            if self._cross_encoder is not None:
                return self._cross_encoder
            if self._cross_error:
                return None
            try:
                from sentence_transformers import CrossEncoder
                self._cross_encoder = CrossEncoder(self._setting("AI_CROSS_ENCODER_MODEL", "cross-encoder/stsb-distilroberta-base"), device=self._device())
            except Exception as exc:
                self._cross_error = type(exc).__name__ + ": " + str(exc)[:180]
            return self._cross_encoder

    def _load_clip(self):
        with self._lock:
            if self._clip_matcher is not None:
                return self._clip_matcher
            if self._clip_error:
                return None
            try:
                from services.product_ai.clip import LocalClipMatcher
                self._clip_matcher = LocalClipMatcher(self._setting("AI_CLIP_CACHE_DIR", "instance/product_images"), self._setting("AI_CLIP_MODEL", "openai/clip-vit-base-patch32"))
            except Exception as exc:
                self._clip_error = type(exc).__name__ + ": " + str(exc)[:180]
            return self._clip_matcher

    def score_candidates(self, query, offers, domain="general"):
        titles = [" ".join(str(offer.get(key) or "") for key in ("name", "brand", "model")) for offer in offers]
        bm25 = BM25Retriever(titles).scores(query) if titles else []
        tfidf = char_tfidf_scores(query, titles) if titles else []
        features = []
        for index, title in enumerate(titles):
            features.append({"bm25": round(bm25[index], 4), "char_tfidf": round(tfidf[index], 4), "semantic": None, "cross_encoder": None, "siamese": None, "clip": None, "entities": extract_entities(title)})
        semantic_model = self._load_semantic() if titles and self._enabled("AI_SEMANTIC_ENABLED") else None
        if semantic_model is not None:
            try:
                vectors = semantic_model.encode([query, *titles], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False, batch_size=32)
                scores = [float(vectors[0] @ vector) for vector in vectors[1:]]
                for feature, score in zip(features, scores):
                    feature["semantic"] = round(score, 4)
            except Exception as exc:
                self._semantic_error = type(exc).__name__ + ": " + str(exc)[:180]
        cross_encoder = self._load_cross_encoder() if titles and self._enabled("AI_CROSS_ENCODER_ENABLED") else None
        if cross_encoder is not None:
            try:
                values = cross_encoder.predict([(query, title) for title in titles], batch_size=16, show_progress_bar=False)
                for feature, value in zip(features, values):
                    score = float(value)
                    feature["cross_encoder"] = round(score / 5.0 if 0 <= score <= 5 else 1 / (1 + math.exp(-max(-30, min(30, score)))), 4)
            except Exception as exc:
                self._cross_error = type(exc).__name__ + ": " + str(exc)[:180]
        if titles and self._enabled("AI_SIAMESE_ENABLED") and self._siamese.checkpoint.is_file() and semantic_model is not None:
            try:
                scores = self._siamese.score([(query, title) for title in titles], self._setting("AI_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
                for feature, score in zip(features, scores):
                    feature["siamese"] = round(float(score), 4)
                    feature["siamese_threshold"] = self._siamese.metadata.get("threshold")
            except Exception as exc:
                self._siamese_error = type(exc).__name__ + ": " + str(exc)[:180]
        if titles and self._enabled("AI_CLIP_ENABLED", "0"):
            clip = self._load_clip()
            if clip:
                for feature, offer, title in zip(features, offers, titles):
                    image_path = offer.get("image_path") or offer.get("cached_image_path")
                    if image_path:
                        try:
                            value = clip.score(title, image_path)
                            feature["clip"] = round(value, 4) if value is not None else None
                        except Exception as exc:
                            self._clip_error = type(exc).__name__ + ": " + str(exc)[:180]
                            break
        for feature in features:
            components = [("bm25", 0.18), ("char_tfidf", 0.12), ("semantic", 0.28), ("cross_encoder", 0.18), ("siamese", 0.19), ("clip", 0.05)]
            available = [(feature[key], weight) for key, weight in components if feature.get(key) is not None]
            denominator = sum(weight for _, weight in available)
            feature["rank_score"] = round(sum(value * weight for value, weight in available) / denominator, 4) if denominator else 0.0
        return features

    def compare_title_pairs(self, pairs):
        results = [{"semantic": None, "cross_encoder": None, "siamese": None} for _ in pairs]
        if not pairs:
            return results
        model = self._load_semantic() if self._enabled("AI_SEMANTIC_ENABLED") else None
        if model is not None:
            try:
                texts = list(dict.fromkeys(text for pair in pairs for text in pair))
                vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False, batch_size=32)
                index = {text: position for position, text in enumerate(texts)}
                for result, (left, right) in zip(results, pairs):
                    result["semantic"] = float(vectors[index[left]] @ vectors[index[right]])
            except Exception as exc:
                self._semantic_error = type(exc).__name__ + ": " + str(exc)[:180]
        cross = self._load_cross_encoder() if self._enabled("AI_CROSS_ENCODER_ENABLED") else None
        if cross is not None:
            try:
                values = cross.predict(pairs, batch_size=32, show_progress_bar=False)
                for result, value in zip(results, values):
                    score = float(value)
                    result["cross_encoder"] = score / 5.0 if 0 <= score <= 5 else 1 / (1 + math.exp(-max(-30, min(30, score))))
            except Exception as exc:
                self._cross_error = type(exc).__name__ + ": " + str(exc)[:180]
        if self._siamese.checkpoint.is_file() and self._enabled("AI_SIAMESE_ENABLED") and model is not None:
            try:
                scores = self._siamese.score(pairs, self._setting("AI_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
                for result, score in zip(results, scores):
                    result["siamese"] = float(score)
            except Exception as exc:
                self._siamese_error = type(exc).__name__ + ": " + str(exc)[:180]
        return results

    def siamese_threshold(self):
        if self._siamese.metadata.get("threshold") is not None:
            return float(self._siamese.metadata["threshold"])
        try:
            import torch
            payload = torch.load(self._siamese.checkpoint, map_location="cpu", weights_only=True)
            return float(payload.get("threshold", 1.0))
        except Exception:
            return 1.0

    def status(self):
        sentence_package = importlib.util.find_spec("sentence_transformers") is not None
        transformer_package = importlib.util.find_spec("transformers") is not None
        checkpoint_exists = self._siamese.checkpoint.is_file()
        clip_enabled = self._enabled("AI_CLIP_ENABLED", "0")
        stage1_state = "ready" if self._semantic_model is not None and not self._semantic_error else "configured" if sentence_package and self._enabled("AI_SEMANTIC_ENABLED") and not self._semantic_error else "partial"
        stage2_state = "ready" if self._cross_encoder is not None and not self._cross_error else "configured" if sentence_package and self._enabled("AI_CROSS_ENCODER_ENABLED") and not self._cross_error else "partial"
        stage3_state = "ready" if self._siamese._head is not None or (self._clip_matcher is not None and self._clip_matcher._model is not None) else "configured" if (checkpoint_exists and sentence_package) or (clip_enabled and transformer_package) else "setup"
        stage1_details = "MiniLM embeddings are loaded. NLP normalization, product NER, BM25 and character TF-IDF are active." if stage1_state == "ready" else "MiniLM is configured and loads on the first search; the first use may download model weights." if stage1_state == "configured" else "Normalization, product NER and BM25 are active; install requirements-ai.txt or check model availability to enable MiniLM embeddings."
        stage2_details = "Cross-Encoder reranking is loaded after deterministic product checks." if stage2_state == "ready" else "Cross-Encoder is configured and loads lazily; model weights may download on first use." if stage2_state == "configured" else "Cross-Encoder code is integrated; install requirements-ai.txt or check model availability to enable inference."
        stage3_details = "Siamese checkpoint and/or CLIP model are loaded." if stage3_state == "ready" else "A trained Siamese checkpoint or enabled CLIP image cache is configured but will load lazily." if stage3_state == "configured" else "Siamese training workflow is included; train it with labelled product pairs. CLIP requires enabled, locally cached product images."
        return {
            "stage1": {"name": "NLP + semantic retrieval", "state": stage1_state, "details": stage1_details},
            "stage2": {"name": "Cross-Encoder reranking", "state": stage2_state, "details": stage2_details},
            "stage3": {"name": "Siamese + CLIP", "state": stage3_state, "details": stage3_details},
            "models": {"embedding": self._setting("AI_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"), "cross_encoder": self._setting("AI_CROSS_ENCODER_MODEL", "cross-encoder/stsb-distilroberta-base"), "siamese_trained": checkpoint_exists, "clip_enabled": clip_enabled, "device": self._device()},
            "errors": {"semantic": self._semantic_error, "cross_encoder": self._cross_error, "clip": self._clip_error, "siamese": getattr(self, "_siamese_error", None)},
        }



_ENGINE = None
_ENGINE_LOCK = threading.Lock()


def get_engine(config=None):
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = ProductIntelligenceEngine(config)
        elif config is not None:
            _ENGINE.config = config
            checkpoint = Path(_ENGINE._setting("AI_SIAMESE_CHECKPOINT", "artifacts/siamese/siamese_head.pt"))
            if checkpoint != _ENGINE._siamese.checkpoint:
                _ENGINE._siamese = SiamesePairScorer(checkpoint)
        return _ENGINE


def get_product_intelligence_status(config=None):
    return get_engine(config).status()
