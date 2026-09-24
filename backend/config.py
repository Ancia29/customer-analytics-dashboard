import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE, ".env"))
UPLOAD_DIR = os.path.join(BASE, "backend", "uploads")
MODEL_DIR = os.getenv("MODEL_DIR", os.path.join(BASE, "backend", "model"))
MAX_UPLOAD_MB = 10
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


def db_url():
    """DATABASE_URL override (used by tests), otherwise MySQL from .env."""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    g = os.getenv
    return "mysql+pymysql://{}:{}@{}:{}/{}".format(
        g("DB_USER", "root"), quote_plus(g("DB_PASSWORD", "")), g("DB_HOST", "localhost"),
        g("DB_PORT", "3306"), g("DB_NAME", "customer_analytics"))
