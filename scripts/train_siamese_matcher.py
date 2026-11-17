import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

np = torch = SentenceTransformer = None
accuracy_score = f1_score = precision_score = recall_score = None
GroupShuffleSplit = train_test_split = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def read_pairs(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    pairs = []
    for row in rows:
        left, right = str(row.get("text_a") or "").strip(), str(row.get("text_b") or "").strip()
        label = str(row.get("label") or "").strip().lower()
        if not left or not right or label not in {"0", "1", "same", "different", "match", "no_match"}:
            continue
        pairs.append({"text_a": left, "text_b": right, "label": 1 if label in {"1", "same", "match"} else 0, "split_group": str(row.get("split_group") or "").strip()})
    counts = Counter(row["label"] for row in pairs)
    if len(pairs) < 30 or min(counts.get(0, 0), counts.get(1, 0)) < 10:
        raise ValueError("Provide at least 30 valid pairs, including at least 10 positive and 10 negative pairs.")
    return pairs


def build_head(dimension):
    return torch.nn.Sequential(torch.nn.Linear(dimension * 4, 256), torch.nn.ReLU(), torch.nn.Dropout(0.15), torch.nn.Linear(256, 64), torch.nn.ReLU(), torch.nn.Linear(64, 1))


def features_for(pairs, encoded, index):
    left = torch.tensor(np.stack([encoded[index[row["text_a"]]] for row in pairs]), dtype=torch.float32)
    right = torch.tensor(np.stack([encoded[index[row["text_b"]]] for row in pairs]), dtype=torch.float32)
    return torch.cat((left, right, torch.abs(left - right), left * right), dim=1)


def select_threshold(labels, probabilities):
    best = None
    for threshold in [value / 100 for value in range(50, 100)]:
        predictions = (probabilities >= threshold).astype(int)
        precision = precision_score(labels, predictions, zero_division=0)
        recall = recall_score(labels, predictions, zero_division=0)
        if precision >= 0.98 and (best is None or recall > best["recall"]):
            best = {"threshold": threshold, "precision": precision, "recall": recall, "f1": f1_score(labels, predictions, zero_division=0)}
    return best or {"threshold": 0.99, "precision": precision_score(labels, probabilities >= 0.99, zero_division=0), "recall": recall_score(labels, probabilities >= 0.99, zero_division=0), "f1": f1_score(labels, probabilities >= 0.99, zero_division=0)}


def main():
    parser = argparse.ArgumentParser(description="Train the Cost Quest Siamese product-pair classifier.")
    parser.add_argument("--data", default="data/product_matching/product_pairs.csv")
    parser.add_argument("--output", default="artifacts/siamese/siamese_head.pt")
    parser.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    global np, torch, SentenceTransformer, accuracy_score, f1_score, precision_score, recall_score, GroupShuffleSplit, train_test_split
    try:
        import numpy as np
        import torch
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
        from sklearn.model_selection import GroupShuffleSplit, train_test_split
    except ImportError as exc:
        raise SystemExit("Install the optional AI dependencies first: python -m pip install -r requirements-ai.txt") from exc
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    pairs = read_pairs(ROOT / args.data)
    groups = [row["split_group"] for row in pairs]
    if all(groups):
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=args.seed)
        train_indices, validation_indices = next(splitter.split(pairs, groups=groups))
    else:
        print("WARNING: split_group is missing; using a stratified random split. Group-aware evaluation is recommended.")
        train_indices, validation_indices = train_test_split(np.arange(len(pairs)), test_size=0.2, random_state=args.seed, stratify=[row["label"] for row in pairs])
    train_rows = [pairs[int(index)] for index in train_indices]
    validation_rows = [pairs[int(index)] for index in validation_indices]
    if len({row["label"] for row in train_rows}) < 2 or len({row["label"] for row in validation_rows}) < 2:
        raise ValueError("Train and validation splits must each contain positive and negative pairs; add more split_group families.")

    texts = list(dict.fromkeys(row[key] for row in pairs for key in ("text_a", "text_b")))
    device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
    encoder = SentenceTransformer(args.embedding_model, device=device)
    vectors = encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True, batch_size=64)
    index = {text: position for position, text in enumerate(texts)}
    train_x = features_for(train_rows, vectors, index).to(device)
    train_y = torch.tensor([row["label"] for row in train_rows], dtype=torch.float32, device=device).unsqueeze(1)
    validation_x = features_for(validation_rows, vectors, index).to(device)
    validation_y = np.array([row["label"] for row in validation_rows], dtype=int)

    head = build_head(vectors.shape[1]).to(device)
    optimizer = torch.optim.AdamW(head.parameters(), lr=2e-4, weight_decay=1e-4)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    best_state, best_loss = None, float("inf")
    batch_size = max(4, args.batch_size)
    for epoch in range(max(1, args.epochs)):
        head.train()
        order = torch.randperm(len(train_x), device=device)
        for start in range(0, len(order), batch_size):
            indices = order[start:start + batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(head(train_x[indices]), train_y[indices])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(head.parameters(), 1.0)
            optimizer.step()
        head.eval()
        with torch.inference_mode():
            target = torch.tensor(validation_y, dtype=torch.float32, device=device).unsqueeze(1)
            validation_loss = float(loss_fn(head(validation_x), target).item())
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_state = {key: value.detach().cpu().clone() for key, value in head.state_dict().items()}
        print(f"epoch {epoch + 1:02d}/{args.epochs} · validation_loss={validation_loss:.4f}")
    head.load_state_dict(best_state)
    head.eval()
    with torch.inference_mode():
        probabilities = torch.sigmoid(head(validation_x)).squeeze(1).cpu().numpy()
    threshold = select_threshold(validation_y, probabilities)
    predictions = (probabilities >= threshold["threshold"]).astype(int)
    metrics = {"validation_accuracy": accuracy_score(validation_y, predictions), "validation_precision": threshold["precision"], "validation_recall": threshold["recall"], "validation_f1": threshold["f1"], "threshold": threshold["threshold"], "validation_pairs": len(validation_rows), "training_pairs": len(train_rows), "validation_loss": best_loss, "warning": "Threshold is selected on a small validation set; collect more independently grouped pairs and recalibrate before production."}
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": best_state, "embedding_model": args.embedding_model, "embedding_dimension": int(vectors.shape[1]), **metrics}, output)
    output.with_suffix(".metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"checkpoint": str(output), **metrics}, indent=2))


if __name__ == "__main__":
    main()
