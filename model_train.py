import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
import tensorflow as tf

def ensure_data_exists():
    base = Path(__file__).parent
    data_dir = base / "data"
    needed = ["customers.csv", "purchases.csv", "products.csv", "item_to_index.json", "index_to_item.json"]
    missing = [f for f in needed if not (data_dir / f).exists()]
    if missing:
        print("Data files missing:", missing, "→ generating synthetic data...")
        # import locally to avoid circulars at module import time
        import data_generation
        data_generation.main()
    return data_dir

# goal: build (1) simple association rules, (2) tiny TF embeddings
def load_data():
    data_dir = Path(__file__).parent / "data"
    purchases = pd.read_csv(data_dir / "purchases.csv")
    invoices = pd.read_csv(data_dir / "invoices.csv")
    invoice_items = pd.read_csv(data_dir / "invoice_items.csv")
    with open(data_dir / "item_to_index.json", "r") as f:
        item_to_index = json.load(f)
    with open(data_dir / "index_to_item.json", "r") as f:
        index_to_item = {int(k): v for k, v in json.load(f).items()}
    with open(data_dir / "complements.json", "r") as f:
        complements = json.load(f)
    return purchases, invoices, invoice_items, complements, item_to_index, index_to_item, data_dir

def baskets_by_order(purchases, invoices, invoice_items):
    baskets = []
    # purchases grouped by (customer_id, date)
    for (cid, dt), grp in purchases.groupby(["customer_id", "date"]):
        baskets.append(sorted(list(set(grp["item"].tolist()))))
    # invoices grouped by invoice_id
    for inv_id, grp in invoice_items.groupby("invoice_id"):
        baskets.append(sorted(list(set(grp["item"].tolist()))))
    return baskets

def build_association_rules(baskets, min_support=0.015, min_conf=0.08):
    item_counts = defaultdict(int)
    pair_counts = defaultdict(int)
    total_baskets = len(baskets)

    for basket in baskets:
        for i, a in enumerate(basket):
            item_counts[a] += 1
            for b in basket[i+1:]:
                key = tuple(sorted([a, b]))
                pair_counts[key] += 1

    rules = defaultdict(dict)
    for (a, b), cnt in pair_counts.items():
        support = cnt / total_baskets
        if support < min_support:
            continue
        conf_ab = cnt / item_counts[a]
        conf_ba = cnt / item_counts[b]
        if conf_ab >= min_conf:
            rules[a][b] = {"support": support, "confidence": conf_ab}
        if conf_ba >= min_conf:
            rules[b][a] = {"support": support, "confidence": conf_ba}
    return rules
def apply_defaults_for_complements(rules, complements, min_conf_default=0.25, min_sup_default=0.05):
    for a, comp_list in complements.items():
        rules.setdefault(a, {})
        for b in comp_list:
            if b not in rules[a]:
                rules[a][b] = {"support": min_sup_default, "confidence": min_conf_default}
            else:
                # bump to at least defaults (avoid 0s)
                rules[a][b]["support"] = max(rules[a][b].get("support", 0.0), min_sup_default)
                rules[a][b]["confidence"] = max(rules[a][b].get("confidence", 0.0), min_conf_default)
    return rules

def make_training_pairs(baskets, item_to_index, max_pairs_per_basket=20):
    pairs = []
    for basket in baskets:
        idxs = [item_to_index[i] for i in basket if i in item_to_index]
        if len(idxs) < 2:
            continue
        # positive pairs (undirected)
        added = 0
        for i in range(len(idxs)):
            for j in range(i+1, len(idxs)):
                pairs.append((idxs[i], idxs[j], 1.0))
                pairs.append((idxs[j], idxs[i], 1.0))
                added += 2
                if added >= max_pairs_per_basket:
                    break
            if added >= max_pairs_per_basket:
                break
        # a few random negatives
        all_ids = list(item_to_index.values())
        for pos in idxs[: min(2, len(idxs))]:
            neg = np.random.choice(all_ids)
            if neg not in idxs:
                pairs.append((pos, neg, 0.0))
    np.random.shuffle(pairs)
    return np.array(pairs, dtype=np.int32), np.array([p[2] for p in pairs], dtype=np.float32)

def train_embeddings(num_items, pairs, labels, embedding_dim=16, epochs=5, batch_size=256):
    import tensorflow as tf

    # Inputs are scalar indices, shape: (batch,)
    left_input = tf.keras.layers.Input(shape=(), dtype=tf.int32, name="left_id")
    right_input = tf.keras.layers.Input(shape=(), dtype=tf.int32, name="right_id")

    # One shared embedding layer for both sides
    shared_emb = tf.keras.layers.Embedding(num_items, embedding_dim, name="item_emb")

    # With Input(shape=()), Embedding outputs shape (batch, embedding_dim) already.
    left_vec = shared_emb(left_input)    # (None, D)
    right_vec = shared_emb(right_input)  # (None, D)

    # Cosine similarity -> [0,1] with sigmoid
    dot = tf.keras.layers.Dot(axes=-1, normalize=True)([left_vec, right_vec])
    output = tf.keras.layers.Activation("sigmoid")(dot)

    model = tf.keras.Model([left_input, right_input], output)
    model.compile(optimizer="adam", loss="binary_crossentropy")
    model.fit([pairs[:, 0], pairs[:, 1]], labels, epochs=epochs, batch_size=batch_size, verbose=0)

    # Pull trained embeddings
    embeddings = model.get_layer("item_emb").get_weights()[0]
    return embeddings


def save_artifacts(assoc_rules, embeddings, data_dir):
    (data_dir / "assoc_rules.json").write_text(json.dumps(assoc_rules))
    np.save(data_dir / "embeddings.npy", embeddings)
    print("Saved assoc_rules.json and embeddings.npy")

def main():
    purchases, invoices, invoice_items, complements, item_to_index, index_to_item, data_dir = load_data()
    baskets = baskets_by_order(purchases, invoices, invoice_items)

    assoc_rules = build_association_rules(baskets, min_support=0.015, min_conf=0.08)
    assoc_rules = {a: {b: v for b, v in d.items()} for a, d in assoc_rules.items()}
    assoc_rules = apply_defaults_for_complements(assoc_rules, complements, 0.25, 0.05)

    pairs, labels = make_training_pairs(baskets, item_to_index, max_pairs_per_basket=24)
    num_items = len(item_to_index)
    embeddings = train_embeddings(num_items, pairs, labels, embedding_dim=16, epochs=6, batch_size=256)

    save_artifacts(assoc_rules, embeddings, data_dir)
