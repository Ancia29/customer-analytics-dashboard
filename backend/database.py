import pandas as pd
from sqlalchemy import create_engine, inspect, text
import config

engine = create_engine(config.db_url(), pool_pre_ping=True)


def read(sql, dates=None, params=None):
    return pd.read_sql(text(sql), engine, params=params, parse_dates=dates)


def table_exists(name):
    return inspect(engine).has_table(name)


def replace_table(df, name):
    """Empty the table (keeps schema/indexes) and insert the new rows."""
    with engine.begin() as conn:
        if inspect(conn).has_table(name):
            conn.execute(text(f"DELETE FROM {name}"))
        df.to_sql(name, conn, if_exists="append", index=False, chunksize=1000)
