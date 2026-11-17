# Product-pair labels for the Siamese matcher

Copy `product_pairs_template.csv` to `product_pairs.csv`, then add verified pairs from real Cost Quest provider results. The checked-in file is only a small starter example and is intentionally too small to train a useful model.

- `text_a`, `text_b`: complete listing titles, including brand and variant details.
- `label`: `1` only when the listings are the same sellable product/configuration; `0` for a different model, variant, accessory or merely similar item.
- `split_group`: a stable product-family ID. Keep all pairs anchored to the same canonical family in one group to reduce train/validation leakage.

Include hard negatives for model generations, storage/RAM, size, capacity, edition, connectivity and accessories. Do not label compatible accessories as the same product. Have pairs reviewed by a person before training. A model trained on incorrect labels will learn incorrect matching decisions.
