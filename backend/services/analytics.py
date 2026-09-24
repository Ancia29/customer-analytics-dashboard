import json
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import config
from services.data_cleaning import ValidationError

FEATURES = ["recency", "frequency", "monetary_value", "avg_order_value", "lifetime_days"]
HORIZON_DAYS = 90
MODEL_PATH = os.path.join(config.MODEL_DIR, "clv_model.joblib")
METRICS_PATH = os.path.join(config.MODEL_DIR, "metrics.json")


def kpis(tx, c):
    rev, orders, n = float(tx.revenue.sum()), int(tx.invoice_no.nunique()), len(c)
    repeat = int((c.total_orders > 1).sum())
    clv = pd.to_numeric(c["predicted_clv"], errors="coerce").mean() if "predicted_clv" in c else np.nan
    return {"total_revenue": round(rev, 2), "total_customers": n, "total_orders": orders,
            "avg_order_value": round(rev / orders, 2), "avg_customer_revenue": round(rev / n, 2),
            "total_products": int(tx.stock_code.nunique()), "repeat_customers": repeat,
            "repeat_customer_rate": round(100 * repeat / n, 1),
            "avg_clv": None if pd.isna(clv) else round(float(clv), 2)}


def build_customers(tx, as_of=None):
    """One row per customer. Frequency = orders, Monetary = total revenue."""
    as_of = as_of if as_of is not None else tx.invoice_date.max() + pd.Timedelta(days=1)
    c = tx.groupby("customer_id").agg(
        first_purchase_date=("invoice_date", "min"), last_purchase_date=("invoice_date", "max"),
        total_orders=("invoice_no", "nunique"), total_revenue=("revenue", "sum")).reset_index()
    c["total_revenue"] = c.total_revenue.round(2)
    c["recency"] = (as_of - c.last_purchase_date).dt.days
    c["frequency"] = c.total_orders
    c["monetary_value"] = c.total_revenue
    c["avg_order_value"] = (c.total_revenue / c.total_orders).round(2)
    c["lifetime_days"] = (c.last_purchase_date - c.first_purchase_date).dt.days
    return c


def _score(s, reverse=False):
    """Quintile score 1-5 (rank-based so ties don't break qcut). Recency: lower = better."""
    if len(s) < 5:
        return pd.Series(3, index=s.index)
    labels = [5, 4, 3, 2, 1] if reverse else [1, 2, 3, 4, 5]
    return pd.qcut(s.rank(method="first"), 5, labels=labels).astype(int)


def _segment(r, f):
    if r >= 4 and f >= 4: return "Champions"
    if r >= 3 and f >= 3: return "Loyal Customers"
    if r >= 4 and f <= 2: return "New Customers"
    if r >= 3: return "Potential Loyalists"
    if r == 2: return "At Risk"
    return "Lost Customers"


def add_rfm(c):
    c = c.copy()
    c["r_score"] = _score(c.recency, reverse=True)
    c["f_score"] = _score(c.frequency)
    c["m_score"] = _score(c.monetary_value)
    c["segment"] = [_segment(r, f) for r, f in zip(c.r_score, c.f_score)]
    return c


def train_clv(tx):
    """Features from history BEFORE a cutoff; target = revenue in the 90 days AFTER it."""
    cutoff = tx.invoice_date.max() - pd.Timedelta(days=HORIZON_DAYS)
    X = build_customers(tx[tx.invoice_date < cutoff], cutoff)
    if len(X) < 20:
        raise ValidationError("Need at least 20 customers with purchases before the last 90 days to train the model.")
    future = tx[tx.invoice_date >= cutoff].groupby("customer_id").revenue.sum()
    y = X.customer_id.map(future).fillna(0)
    Xtr, Xte, ytr, yte = train_test_split(X[FEATURES], y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=100, random_state=42).fit(Xtr, ytr)
    pred = model.predict(Xte)
    metrics = {"mae": round(float(mean_absolute_error(yte, pred)), 2),
               "rmse": round(float(np.sqrt(mean_squared_error(yte, pred))), 2),
               "r2": round(float(r2_score(yte, pred)), 3), "train_rows": len(Xtr), "test_rows": len(Xte),
               "target": f"customer revenue in the {HORIZON_DAYS} days after the cutoff date"}
    joblib.dump(model, MODEL_PATH)
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f)
    return metrics


def predict_clv(c):
    """Estimated spend over the next 90 days, using the saved model."""
    return joblib.load(MODEL_PATH).predict(c[FEATURES]).round(2)
