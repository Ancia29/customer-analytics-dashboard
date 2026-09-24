import pandas as pd

REQUIRED = ["CustomerID", "InvoiceNo", "InvoiceDate", "Quantity", "UnitPrice"]
OPTIONAL = ["Country", "StockCode", "Description"]
RENAME = {"CustomerID": "customer_id", "InvoiceNo": "invoice_no", "InvoiceDate": "invoice_date",
          "StockCode": "stock_code", "Description": "description", "Quantity": "quantity",
          "UnitPrice": "unit_price", "Revenue": "revenue", "Country": "country"}


class ValidationError(ValueError):
    """Raised for problems the user can fix (bad CSV, missing columns...)."""


def clean(raw):
    """Validate + clean a raw transactions DataFrame. Returns (clean_df, report)."""
    if raw.empty:
        raise ValidationError("The CSV file is empty.")
    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        raise ValidationError("Missing required columns: " + ", ".join(missing))
    df = raw.copy()
    for c in OPTIONAL:
        if c not in df:
            df[c] = None
    df = df[REQUIRED + OPTIONAL]
    removed = {}

    def keep(frame, mask, reason):
        removed[reason] = int((~mask).sum())
        return frame[mask]

    n = len(df)
    df = df.drop_duplicates()
    removed["duplicate_rows"] = n - len(df)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    for c in ("Quantity", "UnitPrice"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = keep(df, df["CustomerID"].notna() & (df["CustomerID"].astype(str).str.strip() != ""), "missing_customer_id")
    df = keep(df, df["InvoiceDate"].notna(), "invalid_date")
    df = keep(df, df["Quantity"].notna() & df["UnitPrice"].notna(), "non_numeric_quantity_or_price")
    df = keep(df, df["Quantity"] > 0, "zero_or_negative_quantity")
    df = keep(df, df["UnitPrice"] > 0, "zero_or_negative_price")
    if df.empty:
        raise ValidationError("No valid transactions left after cleaning.")
    df = df.copy()
    df["CustomerID"] = df["CustomerID"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df["Revenue"] = (df["Quantity"] * df["UnitPrice"]).round(2)
    df = df.rename(columns=RENAME)
    report = {"rows_uploaded": len(raw), "rows_removed": len(raw) - len(df), "removed_breakdown": removed,
              "valid_rows": len(df), "customers": int(df.customer_id.nunique()),
              "total_revenue": round(float(df.revenue.sum()), 2)}
    return df, report
