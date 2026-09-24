import io, os, sys, tempfile
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["MODEL_DIR"] = os.path.join(_tmp, "model")
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "backend"))
import pandas as pd, pytest
from app import app
from services import analytics, data_cleaning as cleaning

SAMPLE = os.path.join(HERE, "..", "data", "sample_transactions.csv")


@pytest.fixture(scope="module")
def client():
    return app.test_client()


def test_health(client):
    assert client.get("/api/health").get_json()["success"]


def test_missing_columns():
    with pytest.raises(cleaning.ValidationError):
        cleaning.clean(pd.DataFrame({"a": [1]}))


def test_cleaning_removes_bad_rows():
    df = pd.DataFrame({"CustomerID": ["1", "1", None, "2"], "InvoiceNo": ["A", "A", "B", "C"],
                       "InvoiceDate": ["2024-01-01"] * 3 + ["bad"], "Quantity": [2, 2, 1, 1], "UnitPrice": [5, 5, 5, 5]})
    clean, report = cleaning.clean(df)
    assert len(clean) == 1 and report["rows_removed"] == 3 and clean.revenue.iloc[0] == 10


def test_upload_and_endpoints(client):
    with open(SAMPLE, "rb") as f:
        r = client.post("/api/upload", data={"file": (f, "s.csv")}, content_type="multipart/form-data")
    body = r.get_json()
    assert r.status_code == 200 and body["data"]["clv_model_trained"]
    s = client.get("/api/dashboard-summary").get_json()["data"]
    assert s["total_revenue"] > 0 and 0 <= s["repeat_customer_rate"] <= 100
    assert len(client.get("/api/segments").get_json()["data"]) >= 3
    assert "r2" in client.get("/api/model-metrics").get_json()["data"]
    assert client.get("/api/customers?per_page=5").get_json()["data"]["customers"][0]["predicted_clv"] is not None


def test_invalid_customer_and_sort(client):
    assert client.get("/api/customers/nope").status_code == 404
    assert client.get("/api/customers?sort=bad").status_code == 400


def test_rejects_non_csv(client):
    r = client.post("/api/upload", data={"file": (io.BytesIO(b"x"), "a.txt")}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_rfm_scores_in_range():
    tx, _ = cleaning.clean(pd.read_csv(SAMPLE, dtype={"CustomerID": str}))
    c = analytics.add_rfm(analytics.build_customers(tx))
    assert c.r_score.between(1, 5).all() and c.segment.notna().all()
