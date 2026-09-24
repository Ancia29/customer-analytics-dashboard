# Customer Analytics Dashboard

[![CI](https://github.com/Ancia29/customer-analytics-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/Ancia29/customer-analytics-dashboard/actions/workflows/ci.yml)

Upload transaction data (CSV) and get KPIs, RFM customer segments and an estimated 90-day customer value, shown in an interactive dashboard.

**Problem:** businesses have transaction data but struggle to see customer behaviour, revenue patterns and customer value.
**Solution:** a Flask + MySQL app that validates and cleans a CSV, analyses it with Pandas/NumPy, segments customers, estimates CLV with scikit-learn, and serves everything to a Chart.js dashboard through REST APIs.

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, vanilla JavaScript, Chart.js |
| Backend | Flask, Flask-CORS, SQLAlchemy |
| Database | MySQL |
| Analysis / ML | Pandas, NumPy, scikit-learn |
| CI / CD | GitHub Actions |
| Version control | Git / GitHub |

## How it works
CSV upload → Flask → Pandas validation and cleaning → clean rows stored in MySQL → KPIs → RFM segmentation → Random Forest CLV estimate → JSON REST API → JavaScript `fetch` → Chart.js charts and customer table.

## Structure
```
backend/  app.py (routes), config.py, database.py, services/{data_cleaning,analytics}.py
frontend/ index.html, css/style.css, js/app.js
data/     sample_transactions.csv, generate_sample_data.py
database/ schema.sql        tests/ test_core.py
```

## Setup
```
git clone https://github.com/Ancia29/customer-analytics-dashboard.git
cd customer-analytics-dashboard
python -m venv venv
venv\Scripts\activate          # PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt
mysql -u root -p < database/schema.sql
copy .env.example .env         # then edit .env with your MySQL credentials
python backend/app.py          # open http://localhost:5000
```
Then upload `data/sample_transactions.csv`.

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/health | Health check |
| POST | /api/upload | Upload + clean + analyse CSV |
| GET | /api/dashboard-summary | KPIs |
| GET | /api/customers?search&segment&sort&order&page | Customer table |
| GET | /api/customers/<id> | Profile + purchase history |
| GET | /api/segments, /api/revenue-trend, /api/top-customers, /api/products, /api/clv | Chart data |
| POST | /api/train-model, GET /api/model-metrics | Model training / metrics |

Responses: `{"success": true, "data": ...}` or `{"success": false, "error": "..."}`.

## RFM segmentation
Recency, frequency and monetary value each get a 1-5 quintile score (recent = high R). Rules, in order: R≥4 & F≥4 Champions; R≥3 & F≥3 Loyal Customers; R≥4 & F≤2 New Customers; R≥3 Potential Loyalists; R=2 At Risk; else Lost Customers. Ties in frequency are split by rank order.

## CLV model (estimation, not true lifetime value)
- **Features:** recency, frequency, monetary value, average order value, lifetime days, computed only from purchases before a cutoff date (last date minus 90 days).
- **Target:** each customer's actual revenue in the 90 days after the cutoff (0 if none).
- **Model:** RandomForestRegressor, 80/20 train/test split, metrics MAE, RMSE, R² (`/api/model-metrics`).
- **Prediction:** the saved model applied to features from full history gives estimated spend over the next 90 days. The dataset has no observed long-term future, so this is a 90-day CLV estimate.

## Tests
`python -m pytest -q` (uses a temporary SQLite database, no MySQL needed).

## Git workflow
```
git init
git add .
git commit -m "Initial commit - Customer Analytics Dashboard"
git remote add origin https://github.com/Ancia29/customer-analytics-dashboard.git
git branch -M main
git push -u origin main
```
Small, meaningful commits (e.g. "Add RFM segmentation") show your progress and make the project easier to review.

## Screenshots
`screenshots/dashboard.png`, `screenshots/upload.png`, `screenshots/customer-details.png` (add after running).

## Future improvements
Power BI integration, advanced CLV models, authentication, cloud deployment, automated and email reports, more ML models.

## Author
Ancia Preethi C · B.Tech Artificial Intelligence and Data Science
GitHub: https://github.com/Ancia29 · LinkedIn: https://www.linkedin.com/in/ancia29/
