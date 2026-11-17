from pathlib import Path


class SiamesePairScorer:
    """Shared sentence encoder plus a trained neural pair-classification head."""
    def __init__(self, checkpoint, device=None):
        self.checkpoint = Path(checkpoint)
        self.device = device
        self._head = None
        self._torch = None
        self.metadata = {}

    @staticmethod
    def available():
        try:
            import torch  # noqa: F401
            from sentence_transformers import SentenceTransformer  # noqa: F401
            return True
        except Exception:
            return False

    def _load(self, embedding_model):
        import torch
        from sentence_transformers import SentenceTransformer
        if not self.checkpoint.is_file():
            raise FileNotFoundError("Siamese checkpoint has not been trained")
        payload = torch.load(self.checkpoint, map_location="cpu", weights_only=True)
        if payload.get("embedding_model") != embedding_model:
            raise ValueError("Siamese checkpoint embedding model does not match runtime configuration")
        hidden_size = int(payload.get("embedding_dimension", 384))
        head = torch.nn.Sequential(torch.nn.Linear(hidden_size * 4, 256), torch.nn.ReLU(), torch.nn.Dropout(0.15), torch.nn.Linear(256, 64), torch.nn.ReLU(), torch.nn.Linear(64, 1))
        head.load_state_dict(payload["state_dict"])
        selected_device = self.device or ("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")
        head.to(selected_device).eval()
        self._encoder = SentenceTransformer(embedding_model, device=selected_device)
        self._head, self._torch, self.device = head, torch, selected_device
        self.metadata = {key: payload.get(key) for key in ("threshold", "validation_precision", "validation_recall", "validation_f1", "training_pairs")}

    def score(self, pairs, embedding_model):
        if not pairs:
            return []
        if self._head is None:
            self._load(embedding_model)
        torch = self._torch
        texts = list(dict.fromkeys(text for pair in pairs for text in pair))
        embeddings = self._encoder.encode(texts, convert_to_tensor=True, normalize_embeddings=True, show_progress_bar=False)
        index = {text: position for position, text in enumerate(texts)}
        left = torch.stack([embeddings[index[a]] for a, _ in pairs])
        right = torch.stack([embeddings[index[b]] for _, b in pairs])
        features = torch.cat((left, right, torch.abs(left - right), left * right), dim=1)
        with torch.inference_mode():
            return torch.sigmoid(self._head(features)).squeeze(1).detach().cpu().tolist()
