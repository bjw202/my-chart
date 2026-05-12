import sqlite3

import pandas as pd

from backend.deps import DAILY_DB_PATH


def enrich_market_cap(stocks_df: pd.DataFrame, db_path: str = DAILY_DB_PATH) -> pd.DataFrame:
    # REQ-NT-007, REQ-NT-C-001: stock_meta.market_cap을 read-only URI로 JOIN
    # LEFT JOIN 의미 — DB에 없는 코드는 market_cap = NaN
    if stocks_df.empty:
        stocks_df = stocks_df.copy()
        stocks_df["market_cap"] = pd.Series(dtype="float64")
        return stocks_df

    codes = stocks_df["stock_code"].astype(str).unique().tolist()
    placeholders = ",".join("?" * len(codes))

    # mode=ro: INSERT/UPDATE/DELETE 시도 시 SQLite가 거부 (REQ-NT-C-001)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            f"SELECT code, market_cap FROM stock_meta WHERE code IN ({placeholders})",
            codes,
        ).fetchall()
    finally:
        conn.close()

    cap_map: dict[str, float] = {code: float(cap) for code, cap in rows}
    result = stocks_df.copy()
    result["market_cap"] = result["stock_code"].map(cap_map).astype("float64")
    return result
