"""Generates synthetic transactions (no personal data), incl. a few bad rows to show cleaning."""
import numpy as np, pandas as pd
rng = np.random.default_rng(42)
products = [(f"P{i:03d}", f"Product {i}", round(float(rng.uniform(3, 60)), 2)) for i in range(1, 31)]
countries = ["United Kingdom", "Germany", "France"]
rows, inv = [], 10000
for cid in range(1001, 1301):
    start = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 540)))
    for _ in range(int(rng.choice([1, 2, 3, 5, 8, 12], p=[.3, .25, .2, .12, .08, .05]))):
        d = start + pd.Timedelta(days=int(rng.integers(0, 180)))
        if d > pd.Timestamp("2025-12-31"):
            continue
        inv += 1
        for i in rng.choice(30, size=int(rng.integers(1, 5)), replace=False):
            code, desc, price = products[i]
            rows.append([cid, inv, d.strftime("%Y-%m-%d"), int(rng.integers(1, 10)), price, str(rng.choice(countries)), code, desc])
df = pd.DataFrame(rows, columns=["CustomerID", "InvoiceNo", "InvoiceDate", "Quantity", "UnitPrice", "Country", "StockCode", "Description"])
bad = df.sample(6, random_state=1).copy()
bad.iloc[0, 3] = -2; bad.iloc[1, 0] = None; bad.iloc[2, 2] = "not-a-date"; bad.iloc[3, 4] = 0
df = pd.concat([df, bad, df.head(3)], ignore_index=True)  # bad rows + 3 exact duplicates
df.to_csv("data/sample_transactions.csv", index=False)
print(len(df), "rows")
