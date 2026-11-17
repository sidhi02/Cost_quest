from pathlib import Path


class LocalClipMatcher:
    """Optional CLIP text/image similarity. Only reads image paths inside the configured cache."""
    def __init__(self, cache_dir, model_name="openai/clip-vit-base-patch32"):
        self.cache_dir = Path(cache_dir).resolve()
        self.model_name = model_name
        self._model = None
        self._processor = None
        self._torch = None
        self._device = None

    def _safe_image(self, image_path):
        path = Path(str(image_path or "")).resolve()
        if not path.is_relative_to(self.cache_dir) or not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
            return None
        try:
            from PIL import Image
            with Image.open(path) as image:
                image.verify()
            return path
        except Exception:
            return None

    def _load(self):
        import torch
        from transformers import CLIPModel, CLIPProcessor
        self._device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
        self._model = CLIPModel.from_pretrained(self.model_name).to(self._device).eval()
        self._processor = CLIPProcessor.from_pretrained(self.model_name)
        self._torch = torch

    def score(self, text, image_path):
        path = self._safe_image(image_path)
        if path is None:
            return None
        if self._model is None:
            self._load()
        from PIL import Image
        with Image.open(path) as image:
            inputs = self._processor(text=[text], images=[image.convert("RGB")], return_tensors="pt", padding=True)
        inputs = {key: value.to(self._device) for key, value in inputs.items()}
        with self._torch.inference_mode():
            text_vector = self._model.get_text_features(input_ids=inputs["input_ids"], attention_mask=inputs.get("attention_mask"))
            image_vector = self._model.get_image_features(pixel_values=inputs["pixel_values"])
            text_vector = self._torch.nn.functional.normalize(text_vector, dim=-1)
            image_vector = self._torch.nn.functional.normalize(image_vector, dim=-1)
            return float((text_vector * image_vector).sum(dim=-1).item())
