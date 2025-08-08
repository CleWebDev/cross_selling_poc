import json
import numpy as np
import pandas as pd
from pathlib import Path
import os
import threading

# ---- bootstrap guards to avoid multiple concurrent trainings ----
_bootstrap_lock = threading.Lock()
_bootstrap_running = False
_bootstrapped = False


def ensure_artifacts():
    """
    Generate synthetic data and train artifacts if missing.
    Guarded so concurrent requests don't trigger duplicate work.
    """
    global _bootstrap_running, _bootstrapped
    with _bootstrap_lock:
        if _bootstrapped or _bootstrap_running:
            return
        _bootstrap_running = True

    try:
        data_dir = Path(__file__).parent / "data"

        need_core = any(
            not (data_dir / f).exists()
            for f in [
                "customers.csv",
                "purchases.csv",
                "products.csv",
                "item_to_index.json",
                "index_to_item.json",
                "complements.json",
                "main_products.json",
                "invoices.csv",
                "invoice_items.csv",
                "prices.json",
                "rooms.json",
            ]
        )
        need_assoc = not (data_dir / "assoc_rules.json").exists()
        need_emb = not (data_dir / "embeddings.npy").exists()

        if need_core:
            import data_generation
            print("[bootstrap] Generating synthetic data…")
            data_generation.main()

        if need_assoc or need_emb:
            import model_train
            print("[bootstrap] Training model artifacts…")
            model_train.main()
    finally:
        with _bootstrap_lock:
            _bootstrapped = True
            _bootstrap_running = False


def load_artifacts():
    """
    Load all on-disk artifacts, ensuring they exist first.
    """
    ensure_artifacts()

    data_dir = Path(__file__).parent / "data"

    with open(data_dir / "item_to_index.json", "r") as f:
        item_to_index = json.load(f)
    with open(data_dir / "index_to_item.json", "r") as f:
        index_to_item = {int(k): v for k, v in json.load(f).items()}
    with open(data_dir / "assoc_rules.json", "r") as f:
        assoc_rules = json.load(f)

    embeddings = np.load(data_dir / "embeddings.npy")

    with open(data_dir / "complements.json", "r") as f:
        complements = json.load(f)

    import json as _json
    main_products = _json.loads((data_dir / "main_products.json").read_text())
    prices = _json.loads((data_dir / "prices.json").read_text())
    rooms = _json.loads((data_dir / "rooms.json").read_text())

    purchases = pd.read_csv(data_dir / "purchases.csv")
    invoices = pd.read_csv(data_dir / "invoices.csv")
    invoice_items = pd.read_csv(data_dir / "invoice_items.csv")

    return (
        item_to_index,
        index_to_item,
        assoc_rules,
        embeddings,
        complements,
        set(main_products),
        prices,
        rooms,
        purchases,
        invoices,
        invoice_items,
    )


def suggest_for_item(target_item, top_k=5):
    """
    Locked-down per-item suggestions:
      - Allow explicit complements for the item.
      - Allow strong co-purchase candidates (min support/confidence).
      - Disallow other main products unless explicitly whitelisted.
      - Use embedding similarity only for RANKING within the allowed set.
      - Fill in sane floors so UI never shows 0s.
    """
    (
        item_to_index,
        index_to_item,
        assoc_rules,
        embeddings,
        complements,
        main_products,
        prices,
        rooms,
        purchases,
        invoices,
        invoice_items,
    ) = load_artifacts()

    if target_item not in item_to_index:
        return []

    # Candidate set
    strong_conf_min = 0.12
    strong_sup_min = 0.02

    whitelist = set(complements.get(target_item, []))

    assoc_candidates = set()
    if target_item in assoc_rules:
        for other, stats in assoc_rules[target_item].items():
            conf = float(stats.get("confidence", 0.0))
            sup = float(stats.get("support", 0.0))
            if conf >= strong_conf_min and sup >= strong_sup_min:
                assoc_candidates.add(other)

    candidates = set()
    for c in whitelist.union(assoc_candidates):
        if c in whitelist:
            candidates.add(c)
            continue
        if c not in main_products:
            candidates.add(c)

    candidates.discard(target_item)
    if not candidates:
        return []

    # Ranking
    src_idx = item_to_index[target_item]
    src_vec = embeddings[src_idx]

    confs = [
        float(assoc_rules.get(target_item, {}).get(c, {}).get("confidence", 0.0))
        for c in candidates
    ]
    max_conf = max(confs) if confs else 1.0

    results = []
    for c in candidates:
        stats = assoc_rules.get(target_item, {}).get(c, {})
        conf = float(stats.get("confidence", 0.0))
        sup = float(stats.get("support", 0.0))

        # Similarity only used for ranking—never to admit
        c_idx = item_to_index.get(c)
        sim = 0.0
        if c_idx is not None:
            c_vec = embeddings[c_idx]
            denom = (np.linalg.norm(src_vec) * np.linalg.norm(c_vec)) + 1e-8
            sim = float(np.dot(src_vec, c_vec) / denom)

        # Normalize and score
        conf_norm = conf / max_conf if max_conf > 0 else 0.0
        sim_norm = (sim + 1.0) / 2.0
        score = 0.7 * conf_norm + 0.3 * sim_norm

        # Floors so the UI never shows 0/0 for whitelisted-but-rare pairs
        if conf == 0.0 and sup == 0.0:
            conf = 0.22
            sup = 0.04

        results.append(
            {
                "item": c,
                "probability": round(conf, 3),
                "similarity": round(sim, 3),
                "score": round(float(score), 3),
                "support": round(sup, 3),
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def recent_purchase_for_customer(customer_id):
    data_dir = Path(__file__).parent / "data"
    purchases = pd.read_csv(data_dir / "purchases.csv")
    df = purchases[purchases["customer_id"] == customer_id].sort_values("date")
    if df.empty:
        return None
    return df.iloc[-1]["item"]


def list_customers():
    data_dir = Path(__file__).parent / "data"
    customers = pd.read_csv(data_dir / "customers.csv")
    return customers["customer_id"].tolist(), customers["name"].tolist()


def additional_recommendations(customer_id, top_k=8):
    """
    Recommend additional MAIN products for rooms already represented
    in the customer's last two invoices. Uses:
      - room overlap
      - max confidence against any bought item (with floors)
      - embedding similarity as a tie-breaker
    """
    (
        item_to_index,
        index_to_item,
        assoc_rules,
        embeddings,
        complements,
        main_products,
        prices,
        rooms,
        purchases,
        invoices,
        invoice_items,
    ) = load_artifacts()

    # last two invoices
    invs = (
        invoices[invoices["customer_id"] == customer_id]
        .sort_values("date", ascending=False)
        .head(2)
    )
    inv_ids = invs["invoice_id"].tolist()
    bought = set(
        invoice_items[invoice_items["invoice_id"].isin(inv_ids)]["item"].tolist()
    )

    # rooms represented in bought items
    used_rooms = set(rooms.get(i, None) for i in bought if rooms.get(i))

    # candidate mains in those rooms that customer hasn't bought yet
    candidate_mains = [
        m for m in main_products if m not in bought and rooms.get(m) in used_rooms
    ]

    results = []
    for c in candidate_mains:
        confs = []
        sims = []
        sups = []
        for b in bought:
            # confidence/support for (b -> c)
            stats = assoc_rules.get(b, {}).get(c, {})
            confs.append(float(stats.get("confidence", 0.0)))
            sups.append(float(stats.get("support", 0.0)))

            # similarity(b, c)
            if b in item_to_index and c in item_to_index:
                b_vec = embeddings[item_to_index[b]]
                c_vec = embeddings[item_to_index[c]]
                denom = (np.linalg.norm(b_vec) * np.linalg.norm(c_vec)) + 1e-8
                sims.append(float(np.dot(b_vec, c_vec) / denom))

        max_conf = max(confs) if confs else 0.0
        max_sup = max(sups) if sups else 0.0
        avg_sim = (sum(sims) / len(sims)) if sims else 0.0

        # floors so UI never shows zeros
        if max_conf == 0.0:
            max_conf = 0.2
        if max_sup == 0.0:
            max_sup = 0.05

        score = 0.7 * max_conf + 0.3 * ((avg_sim + 1.0) / 2.0)

        results.append(
            {
                "item": c,
                "probability": round(max_conf, 3),
                "similarity": round(avg_sim, 3),
                "score": round(float(score), 3),
                "support": round(max_sup, 3),
                "room": rooms.get(c, "General"),
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
