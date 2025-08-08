import os
from flask import Flask, jsonify, render_template, request
from recommend import suggest_for_item, recent_purchase_for_customer, list_customers
import pandas as pd
from pathlib import Path

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/customers")
def api_customers():
    ids, names = list_customers()
    return jsonify([{"id": i, "name": n} for i, n in zip(ids, names)])

@app.route("/api/recent_purchase")
def api_recent_purchase():
    customer_id = request.args.get("customer_id")
    item = recent_purchase_for_customer(customer_id)
    return jsonify({"customer_id": customer_id, "recent_item": item})

@app.route("/api/suggest")
def api_suggest():
    item = request.args.get("item")
    top_k = int(request.args.get("k", "5"))
    suggestions = suggest_for_item(item, top_k=top_k)
    return jsonify({"item": item, "suggestions": suggestions})

@app.route("/api/customer_history")
def api_customer_history():
    customer_id = request.args.get("customer_id")
    data_dir = Path(__file__).parent / "data"
    purchases = pd.read_csv(data_dir / "purchases.csv")
    df = purchases[purchases["customer_id"] == customer_id].sort_values("date")
    return jsonify(df.to_dict(orient="records"))

@app.route("/api/catalog_main")
def api_catalog_main():
    from pathlib import Path
    import json
    data_dir = Path(__file__).parent / "data"
    main_path = data_dir / "main_products.json"
    if main_path.exists():
        items = json.loads(main_path.read_text())
    else:
        # fallback: derive from products.csv if json doesn't exist
        import pandas as pd
        all_items = pd.read_csv(data_dir / "products.csv")["item"].tolist()
        items = [x for x in all_items if "Warranty" not in x and "Filter" not in x and "Kit" not in x and "Plan" not in x and "Cover" not in x and "Bag" not in x and "Blade" not in x and "Hose" not in x and "Nozzle" not in x]
    return jsonify(items)

@app.route("/api/customer_details")
def api_customer_details():
    cid = request.args.get("customer_id")
    from pathlib import Path
    import pandas as pd
    data_dir = Path(__file__).parent / "data"
    df = pd.read_csv(data_dir / "customers.csv")
    row = df[df["customer_id"] == cid]
    if row.empty:
        return jsonify({})
    r = row.iloc[0].to_dict()
    return jsonify({"customer_id": r["customer_id"], "name": r["name"], "address": r["address"], "phone": r["phone"], "email": r["email"]})

@app.route("/api/customer_invoices")
def api_customer_invoices():
    cid = request.args.get("customer_id")
    limit = int(request.args.get("limit", "2"))
    from pathlib import Path
    import pandas as pd
    data_dir = Path(__file__).parent / "data"
    inv = pd.read_csv(data_dir / "invoices.csv")
    items = pd.read_csv(data_dir / "invoice_items.csv")
    merged = inv[inv["customer_id"] == cid].sort_values("date", ascending=False).head(limit)
    out = []
    for _, r in merged.iterrows():
        its = items[items["invoice_id"] == r["invoice_id"]]["item"].tolist()
        out.append({"invoice_id": r["invoice_id"], "date": r["date"], "items": its, "total": r["total"]})
    return jsonify(out)

@app.route("/api/additional_recs")
def api_additional_recs():
    cid = request.args.get("customer_id")
    from recommend import additional_recommendations
    recs = additional_recommendations(cid, top_k=8)
    return jsonify({"customer_id": cid, "suggestions": recs})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)