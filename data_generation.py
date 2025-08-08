import json
import random
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

random.seed(7)

def get_products():
    products = [
        "Refrigerator","Dishwasher","Washer","Dryer","Microwave","Range",
        "Coffee Maker","Vacuum","Air Purifier","Grill","Water Heater",
        "Blender","Stand Mixer","Toaster Oven","Slow Cooker","Food Processor",
        "Robot Vacuum","Portable Heater","Ceiling Fan","Dehumidifier","Lawn Mower",
        "Leaf Blower","Pressure Washer","Outdoor Fire Pit","Patio Furniture Set"
    ]
    complements = {
        "Refrigerator": ["Water Filter","Surge Protector","Extended Warranty"],
        "Dishwasher": ["Dishwasher Pods","Rinse Aid","Extended Warranty","Installation Kit"],
        "Washer": ["Dryer","Washer Hoses","Extended Warranty","Stacking Kit"],
        "Dryer": ["Dryer Vent Kit","Lint Trap","Extended Warranty","Stacking Kit"],
        "Microwave": ["Microwave Trim Kit","Surge Protector","Extended Warranty"],
        "Range": ["Oven Liners","Cast Iron Griddle","Extended Warranty","Installation Kit"],
        "Coffee Maker": ["Coffee Filters","Descaler","Extended Warranty"],
        "Vacuum": ["Vacuum Bags","HEPA Filter","Extended Warranty"],
        "Air Purifier": ["HEPA Filter","Carbon Filter","Extended Warranty"],
        "Grill": ["Grill Cover","Propane Tank","Grill Brush","Extended Warranty"],
        "Water Heater": ["Anode Rod","Expansion Tank","Extended Warranty","Installation Kit"],
        "Blender": ["Extra Pitcher","Blade Assembly","Recipe Book","Extended Warranty"],
        "Stand Mixer": ["Dough Hook","Pouring Shield","Recipe Book","Extended Warranty"],
        "Toaster Oven": ["Baking Tray","Pizza Stone","Surge Protector","Extended Warranty"],
        "Slow Cooker": ["Extra Crock Insert","Recipe Book","Extended Warranty"],
        "Food Processor": ["Slicing Blade Set","Dough Blade","Recipe Book","Extended Warranty"],
        "Robot Vacuum": ["Extra Brushes","Extra Filters","Extended Warranty","Mop Attachment"],
        "Portable Heater": ["Remote Control","Safety Guard","Extended Warranty"],
        "Ceiling Fan": ["Light Kit","Remote Control","Installation Kit","Extended Warranty"],
        "Dehumidifier": ["Drain Hose","HEPA Filter","Extended Warranty"],
        "Lawn Mower": ["Grass Catcher","Spare Blades","Fuel Stabilizer","Extended Warranty"],
        "Leaf Blower": ["Battery Pack","Shoulder Strap","Nozzle Attachment","Extended Warranty"],
        "Pressure Washer": ["Hose Extension","Foam Cannon","Nozzle Set","Extended Warranty"],
        "Outdoor Fire Pit": ["Firewood Rack","Weather Cover","Grill Grate","Extended Warranty"],
        "Patio Furniture Set": ["Cushion Covers","Furniture Covers","Patio Umbrella","Extended Warranty"]
    }
    all_items = sorted(set(products + [c for v in complements.values() for c in v]))
    return products, complements, all_items

def make_customers(n_customers=150):
    first_names = ["Olivia","Liam","Emma","Noah","Ava","Sophia","Elijah","Isabella","Lucas","Mia",
                   "Mason","Charlotte","Ethan","Amelia","James","Harper","Benjamin","Evelyn","Henry","Abigail"]
    last_names  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
                   "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin"]
    streets     = ["Oak","Maple","Pine","Cedar","Elm","Willow","Birch","Walnut","Chestnut","Spruce"]
    cities      = ["Cleveland","Akron","Parma","Mentor","Medina","Strongsville","Lakewood","Euclid","Lorain","Brunswick"]
    states      = ["OH"]
    zips        = ["44101","44102","44103","44104","44105","44106","44107","44108","44109","44110"]

    rows = []
    for i in range(1, n_customers+1):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        addr = f"{random.randint(100,9999)} {random.choice(streets)} St"
        city = random.choice(cities)
        state = random.choice(states)
        zipc = random.choice(zips)
        phone = f"({random.randint(216,440)}) {random.randint(200,999)}-{random.randint(1000,9999)}"
        email = f"{name.lower().replace(' ', '.')}@example.com"
        rows.append({
            "customer_id": f"C{i:04d}",
            "name": name,
            "address": f"{addr}, {city}, {state} {zipc}",
            "phone": phone,
            "email": email
        })
    return pd.DataFrame(rows)

def biased_choice(base_items, anchor=None, complements=None):
    if anchor is None or complements is None:
        return random.choice(base_items)
    choices = base_items[:]
    weights = []
    for item in choices:
        w = 1.0
        if anchor in complements and item in complements[anchor]:
            w = 4.0
        if item == anchor:
            w = 0.2
        weights.append(w)
    total = sum(weights)
    pick = random.uniform(0, total)
    cum = 0
    for item, w in zip(choices, weights):
        cum += w
        if pick <= cum:
            return item
    return random.choice(base_items)

def make_purchases(customers_df, products, complements, all_items, days=120):
    rows = []
    start_date = datetime.today() - timedelta(days=days)
    for _, row in customers_df.iterrows():
        customer_id = row["customer_id"]
        num_orders = random.randint(2, 7)
        order_dates = sorted([start_date + timedelta(days=random.randint(0, days)) for _ in range(num_orders)])
        for dt in order_dates:
            # main item
            main_item = random.choice(products)
            rows.append({
                "customer_id": customer_id,
                "date": dt.strftime("%Y-%m-%d"),
                "item": main_item
            })
            # possible complements (1-3 items)
            k = random.randint(0, 3)
            for _ in range(k):
                comp = biased_choice(all_items, anchor=main_item, complements=complements)
                rows.append({
                    "customer_id": customer_id,
                    "date": dt.strftime("%Y-%m-%d"),
                    "item": comp
                })
            # occasional service contract
            if random.random() < 0.25:
                rows.append({
                    "customer_id": customer_id,
                    "date": dt.strftime("%Y-%m-%d"),
                    "item": "Maintenance Plan"
                })
    purchases = pd.DataFrame(rows).sort_values(["customer_id", "date"])
    return purchases

def make_invoices(customers_df, products, complements, prices, days_back=120):
    """Two prior invoices per customer; each invoice: 1-3 mains + their complements."""
    invoices = []
    inv_items = []
    start = datetime.today() - timedelta(days=days_back)
    for _, row in customers_df.iterrows():
        cid = row["customer_id"]
        for n in range(2):  # two invoices
            dt = start + timedelta(days=random.randint(0, days_back-7*(1-n)))
            # choose mains (bias to 1-2 mains)
            mains = random.sample(products, k=random.choice([1,1,2]))
            items = set(mains)
            # add complements
            for m in mains:
                for _ in range(random.choice([1,2,2,3])):
                    comp_choices = complements.get(m, [])
                    if comp_choices:
                        items.add(random.choice(comp_choices))
            # maybe add plan
            if random.random() < 0.35:
                items.add("Maintenance Plan")

            # total from prices
            total = sum(prices.get(i, 29) for i in items)
            inv_id = f"INV-{cid}-{n+1}"
            invoices.append({"invoice_id": inv_id, "customer_id": cid, "date": dt.strftime("%Y-%m-%d"), "total": round(total, 2)})
            for it in items:
                inv_items.append({"invoice_id": inv_id, "item": it})
    return pd.DataFrame(invoices), pd.DataFrame(inv_items)

def write_catalog(all_items, data_dir):
    pd.DataFrame({"item": all_items}).to_csv(data_dir / "products.csv", index=False)

def write_main_products(main_items, data_dir):
    # keep a clean list of "primary" products for UI selection (excludes add-ons)
    from json import dumps
    (data_dir / "main_products.json").write_text(dumps(main_items))

def write_complements(complements, data_dir):
    from json import dumps
    (data_dir / "complements.json").write_text(dumps(complements))

def save_mapping(items, data_dir):
    item_to_index = {item: i for i, item in enumerate(items)}
    index_to_item = {i: item for item, i in item_to_index.items()}
    (data_dir / "item_to_index.json").write_text(json.dumps(item_to_index))
    (data_dir / "index_to_item.json").write_text(json.dumps(index_to_item))

def get_price_map():
    return {
        # mains
        "Refrigerator": 1499, "Dishwasher": 699, "Washer": 899, "Dryer": 899, "Microwave": 199, "Range": 1099,
        "Coffee Maker": 129, "Vacuum": 249, "Air Purifier": 199, "Grill": 399, "Water Heater": 899,
        "Blender": 99, "Stand Mixer": 299, "Toaster Oven": 179, "Slow Cooker": 89, "Food Processor": 159,
        "Robot Vacuum": 399, "Portable Heater": 89, "Ceiling Fan": 179, "Dehumidifier": 229, "Lawn Mower": 449,
        "Leaf Blower": 139, "Pressure Washer": 249, "Outdoor Fire Pit": 229, "Patio Furniture Set": 799,
        # add-ons
        "Water Filter": 49, "Surge Protector": 29, "Extended Warranty": 129, "Installation Kit": 59,
        "Dishwasher Pods": 18, "Rinse Aid": 11, "Washer Hoses": 29, "Stacking Kit": 79, "Dryer Vent Kit": 39,
        "Lint Trap": 19, "Microwave Trim Kit": 89, "Oven Liners": 16, "Cast Iron Griddle": 39,
        "Coffee Filters": 9, "Descaler": 14, "Vacuum Bags": 19, "HEPA Filter": 24, "Carbon Filter": 22,
        "Grill Cover": 35, "Propane Tank": 59, "Grill Brush": 14, "Anode Rod": 35, "Expansion Tank": 89,
        "Extra Pitcher": 24, "Blade Assembly": 19, "Recipe Book": 15, "Baking Tray": 12, "Pizza Stone": 34,
        "Extra Crock Insert": 29, "Slicing Blade Set": 29, "Dough Blade": 19, "Extra Brushes": 17,
        "Extra Filters": 19, "Mop Attachment": 29, "Remote Control": 19, "Safety Guard": 15,
        "Light Kit": 39, "Drain Hose": 12, "Grass Catcher": 59, "Spare Blades": 29, "Fuel Stabilizer": 9,
        "Battery Pack": 59, "Shoulder Strap": 19, "Nozzle Attachment": 15, "Hose Extension": 29,
        "Foam Cannon": 24, "Nozzle Set": 19, "Firewood Rack": 69, "Weather Cover": 39, "Grill Grate": 24,
        "Cushion Covers": 49, "Furniture Covers": 69, "Patio Umbrella": 129, "Maintenance Plan": 149
    }

def get_room_map():
    return {
        "Refrigerator": "Kitchen", "Dishwasher": "Kitchen", "Microwave": "Kitchen", "Range": "Kitchen",
        "Coffee Maker": "Kitchen", "Blender": "Kitchen", "Stand Mixer": "Kitchen", "Toaster Oven": "Kitchen",
        "Slow Cooker": "Kitchen", "Food Processor": "Kitchen",
        "Washer": "Laundry", "Dryer": "Laundry", "Stacking Kit": "Laundry", "Washer Hoses": "Laundry",
        "Dryer Vent Kit": "Laundry",
        "Vacuum": "General", "Robot Vacuum": "General", "Air Purifier": "General", "Portable Heater": "General",
        "Ceiling Fan": "General", "Dehumidifier": "General",
        "Water Heater": "Utility",
        "Grill": "Outdoor", "Outdoor Fire Pit": "Outdoor", "Pressure Washer": "Outdoor",
        "Lawn Mower": "Outdoor", "Leaf Blower": "Outdoor", "Patio Furniture Set": "Outdoor",
        # add-ons fallback
    }

def write_prices_rooms(prices, rooms, data_dir):
    import json
    (data_dir / "prices.json").write_text(json.dumps(prices))
    (data_dir / "rooms.json").write_text(json.dumps(rooms))

def main():
    base = Path(__file__).parent
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    products, complements, all_items = get_products()
    prices = get_price_map()
    rooms  = get_room_map()

    customers_df = make_customers(150)
    # Purchases (session baskets)
    purchases_df = make_purchases(customers_df, products, complements, all_items, days=120)
    # Invoices (historical, 2 per customer)
    invoices_df, invoice_items_df = make_invoices(customers_df, products, complements, prices)

    customers_df.to_csv(data_dir / "customers.csv", index=False)
    purchases_df.to_csv(data_dir / "purchases.csv", index=False)
    invoices_df.to_csv(data_dir / "invoices.csv", index=False)
    invoice_items_df.to_csv(data_dir / "invoice_items.csv", index=False)

    write_catalog(sorted(set(all_items + ["Maintenance Plan"])), data_dir)
    write_main_products(products, data_dir)        # from earlier step
    write_complements(complements, data_dir)       # from earlier step
    write_prices_rooms(prices, rooms, data_dir)

    all_map_items = sorted(set(all_items + ["Maintenance Plan"]))
    save_mapping(all_map_items, data_dir)

    print("Synthetic data created under ./data (customers, purchases, invoices, prices, rooms)")

if __name__ == "__main__":
    main()