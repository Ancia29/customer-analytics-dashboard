import json
import logging
import os
import numpy as np
import pandas as pd
from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
import config
import database as db
from services import analytics, data_cleaning as cleaning

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
app = Flask(__name__, static_folder=os.path.join(config.BASE, "frontend"), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024
CORS(app)


def ok(data, code=200):
    return jsonify(success=True, data=data), code


def fail(msg, code=400):
    return jsonify(success=False, error=msg), code


def rows(df):
    return json.loads(df.to_json(orient="records", date_format="iso"))


@app.errorhandler(HTTPException)
def http_error(e):
    return fail(f"File too large (max {config.MAX_UPLOAD_MB} MB)" if e.code == 413 else e.description, e.code)


@app.errorhandler(ValueError)
def value_error(e):
    return fail(str(e) if isinstance(e, cleaning.ValidationError) else "Invalid request parameters", 400)


@app.errorhandler(SQLAlchemyError)
def db_error(e):
    log.exception("Database error")  # technical details stay in the log
    return fail("Database unavailable. Check your MySQL connection settings.", 503)


@app.errorhandler(Exception)
def unexpected(e):
    log.exception("Unhandled error")
    return fail("Internal server error", 500)


def load(table, dates):
    if not db.table_exists(table):
        abort(404, "No data uploaded yet. Upload a CSV first.")
    return db.read(f"SELECT * FROM {table}", dates)


def load_tx():
    return load("transactions", ["invoice_date"])


def load_customers():
    return load("customers", ["first_purchase_date", "last_purchase_date"])


def refresh(strict=False):
    """Recompute customers, RFM segments and CLV from stored transactions."""
    tx = db.read("SELECT * FROM transactions", ["invoice_date"])
    cust = analytics.add_rfm(analytics.build_customers(tx))
    try:
        metrics = analytics.train_clv(tx)
        cust["predicted_clv"] = analytics.predict_clv(cust)
    except Exception:
        if strict:
            raise
        log.exception("CLV training failed")
        metrics, cust["predicted_clv"] = None, None
    db.replace_table(cust, "customers")
    return metrics


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return ok({"status": "running"})


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return fail("No file selected.")
    name = secure_filename(f.filename)
    if not name.lower().endswith(".csv"):
        return fail("Only .csv files are allowed.")
    path = os.path.join(config.UPLOAD_DIR, name)
    f.save(path)
    try:
        raw = pd.read_csv(path, dtype={"CustomerID": str})
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        return fail("Could not read the file as a valid CSV.")
    clean, report = cleaning.clean(raw)
    db.replace_table(clean, "transactions")
    report["clv_model_trained"] = refresh() is not None
    return ok(report)


@app.post("/api/train-model")
def train_model():
    load_tx()
    return ok(refresh(strict=True))


@app.get("/api/model-metrics")
def model_metrics():
    if not os.path.exists(analytics.METRICS_PATH):
        abort(404, "Model has not been trained yet.")
    with open(analytics.METRICS_PATH) as f:
        return ok(json.load(f))


@app.get("/api/dashboard-summary")
def summary():
    return ok(analytics.kpis(load_tx(), load_customers()))


@app.get("/api/customers")
def list_customers():
    c, q = load_customers(), request.args
    if q.get("segment"):
        c = c[c.segment == q["segment"]]
    if q.get("search"):
        c = c[c.customer_id.str.contains(q["search"], case=False, regex=False)]
    sort = q.get("sort", "total_revenue")
    if sort not in c.columns:
        return fail("Invalid sort column.")
    c = c.sort_values(sort, ascending=q.get("order") == "asc")
    page, size = max(int(q.get("page", 1)), 1), min(max(int(q.get("per_page", 10)), 1), 100)
    return ok({"total": len(c), "page": page, "per_page": size,
               "customers": rows(c.iloc[(page - 1) * size: page * size])})


@app.get("/api/customers/<customer_id>")
def customer_detail(customer_id):
    row = load_customers().query("customer_id == @customer_id")
    if row.empty:
        return fail("Customer not found.", 404)
    history = db.read("SELECT invoice_no, invoice_date, description, quantity, unit_price, revenue "
                      "FROM transactions WHERE customer_id = :id ORDER BY invoice_date DESC",
                      ["invoice_date"], {"id": customer_id})
    return ok({"customer": rows(row)[0], "history": rows(history.head(50))})


@app.get("/api/segments")
def segments():
    g = load_customers().groupby("segment").agg(customers=("customer_id", "count"),
                                                revenue=("total_revenue", "sum")).reset_index()
    g["revenue"] = g.revenue.round(2)
    return ok(rows(g))


@app.get("/api/revenue-trend")
def revenue_trend():
    tx = load_tx()
    m = tx.groupby(tx.invoice_date.dt.strftime("%Y-%m")).revenue.sum().round(2)
    return ok([{"month": k, "revenue": float(v)} for k, v in m.items()])


@app.get("/api/top-customers")
def top_customers():
    return ok(rows(load_customers().nlargest(10, "total_revenue")[["customer_id", "total_revenue"]]))


@app.get("/api/products")
def products():
    p = load_tx().groupby("stock_code").agg(description=("description", "first"), revenue=("revenue", "sum"),
                                            quantity=("quantity", "sum")).nlargest(10, "revenue").reset_index()
    return ok(rows(p))


@app.get("/api/clv")
def clv_distribution():
    v = pd.to_numeric(load_customers().predicted_clv, errors="coerce").dropna()
    if v.empty:
        return ok([])
    counts, edges = np.histogram(v, bins=10)
    return ok([{"range": f"{edges[i]:.0f}-{edges[i + 1]:.0f}", "customers": int(counts[i])} for i in range(10)])


if __name__ == "__main__":
    app.run(port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
