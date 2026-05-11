# pipelines/daily_pipeline.py
# Phase 8 - Daily Pipeline Simulation

import sqlite3
import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime, timedelta
import random

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
WAREHOUSE_DB  = "warehouse/supply_chain.db"
LOG_DB        = "pipelines/pipeline_logs/pipeline_log.db"
LOG_DIR       = "pipelines/pipeline_logs"
EXPORT_DIR    = "powerbi/data"

os.makedirs(LOG_DIR,    exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# ─────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────
log = logging.getLogger(__name__)
logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s | %(levelname)s | %(message)s",
    handlers = [
        logging.FileHandler(
            os.path.join(LOG_DIR, "pipeline.log"),
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)


# ─────────────────────────────────────────
# STEP 1 — SETUP LOG DATABASE
# ─────────────────────────────────────────
def setup_log_db():
    conn = sqlite3.connect(LOG_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_timestamp   TEXT,
            status          TEXT,
            rows_processed  INTEGER,
            rows_inserted   INTEGER,
            source_table    TEXT,
            duration_secs   REAL,
            error_message   TEXT
        )
    """)
    conn.commit()
    conn.close()
    log.info("Log database ready")


# ─────────────────────────────────────────
# STEP 2 — LOG A PIPELINE RUN
# ─────────────────────────────────────────
def log_run(status, rows_processed, rows_inserted,
            source_table, duration_secs, error_message=None):
    conn = sqlite3.connect(LOG_DB)
    conn.execute("""
        INSERT INTO pipeline_runs
            (run_timestamp, status, rows_processed, rows_inserted,
             source_table, duration_secs, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status,
        rows_processed,
        rows_inserted,
        source_table,
        round(duration_secs, 2),
        error_message
    ))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────
# STEP 3 — SIMULATE NEW DAILY DATA
# ─────────────────────────────────────────
def simulate_new_data(conn, batch_size=500):
    log.info(f"Simulating {batch_size} new order records...")

    # Sample existing records as base
    df = pd.read_sql_query("SELECT * FROM fact_orders", conn)

    # Sample a batch
    new_batch = df.sample(n=batch_size, replace=True).copy()

    # Modify to make it look like new data
    max_item_id = df["order_item_id"].max()
    new_batch["order_item_id"] = range(
        int(max_item_id) + 1,
        int(max_item_id) + batch_size + 1
    )

    # Shift dates forward by 1 day
    new_batch["order_date"] = pd.to_datetime(
        new_batch["order_date"]
    ) + timedelta(days=1)

    new_batch["ship_date"] = pd.to_datetime(
        new_batch["ship_date"]
    ) + timedelta(days=1)

    # Add small random noise to financial metrics
    new_batch["sales"]   = new_batch["sales"]   * np.random.uniform(0.95, 1.05, batch_size)
    new_batch["profit"]  = new_batch["profit"]  * np.random.uniform(0.90, 1.10, batch_size)

    log.info(f"New batch created: {len(new_batch)} rows")
    return new_batch


# ─────────────────────────────────────────
# STEP 4 — INSERT NEW DATA INTO WAREHOUSE
# ─────────────────────────────────────────
def insert_new_data(conn, new_batch: pd.DataFrame):
    log.info("Inserting new batch into fact_orders...")
    new_batch.to_sql("fact_orders", conn, if_exists="append", index=False)
    log.info(f"Inserted {len(new_batch)} rows into fact_orders")
    return len(new_batch)


# ─────────────────────────────────────────
# STEP 5 — RECOMPUTE KPI ROLLUPS
# ─────────────────────────────────────────
def recompute_kpis(conn):
    log.info("Recomputing KPI rollups...")

    # Monthly KPI
    monthly = pd.read_sql_query("""
        SELECT
            d.year                              AS order_year,
            d.month                             AS order_month,
            COUNT(f.order_id)                   AS total_orders,
            ROUND(SUM(f.sales), 2)              AS total_revenue,
            ROUND(SUM(f.profit), 2)             AS total_profit,
            ROUND(AVG(f.delivery_delay_days),2) AS avg_delay_days,
            ROUND(AVG(f.on_time_flag)*100, 2)   AS on_time_rate_pct,
            ROUND(AVG(f.profit_margin_pct), 2)  AS avg_profit_margin,
            SUM(f.is_cancelled)                 AS cancelled_orders,
            SUM(f.is_fulfilled)                 AS fulfilled_orders,
            SUM(f.perfect_order_flag)           AS perfect_orders,
            ROUND(SUM(f.revenue_at_risk), 2)    AS revenue_at_risk,
            ROUND(AVG(f.cost_per_order), 2)     AS avg_cost_per_order
        FROM fact_orders f
        JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY d.year, d.month
        ORDER BY d.year, d.month
    """, conn)

    monthly.to_sql("kpi_monthly", conn, if_exists="replace", index=False)
    log.info(f"kpi_monthly recomputed: {len(monthly)} rows")

    # Regional KPI
    regional = pd.read_sql_query("""
        SELECT
            g.market,
            g.order_region,
            COUNT(f.order_id)                   AS total_orders,
            ROUND(SUM(f.sales), 2)              AS total_revenue,
            ROUND(SUM(f.profit), 2)             AS total_profit,
            ROUND(AVG(f.on_time_flag)*100, 2)   AS on_time_rate_pct,
            ROUND(AVG(f.delivery_delay_days),2) AS avg_delay_days,
            ROUND(SUM(f.revenue_at_risk), 2)    AS revenue_at_risk
        FROM fact_orders f
        JOIN dim_geography g ON f.geo_id = g.geo_id
        GROUP BY g.market, g.order_region
        ORDER BY total_revenue DESC
    """, conn)

    regional.to_sql("kpi_regional", conn, if_exists="replace", index=False)
    log.info(f"kpi_regional recomputed: {len(regional)} rows")


# ─────────────────────────────────────────
# STEP 6 — RE-EXPORT TO POWERBI CSVs
# ─────────────────────────────────────────
def re_export_powerbi(conn):
    log.info("Re-exporting updated tables to Power BI CSVs...")

    tables = ["fact_orders", "kpi_monthly", "kpi_regional"]
    for table in tables:
        df   = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        path = os.path.join(EXPORT_DIR, f"{table}.csv")
        df.to_csv(path, index=False)
        log.info(f"Exported {table} → {path} ({len(df):,} rows)")


# ─────────────────────────────────────────
# MAIN PIPELINE RUN
# ─────────────────────────────────────────
def run_pipeline():
    log.info("="*50)
    log.info("PIPELINE RUN STARTED")
    log.info("="*50)

    start_time = datetime.now()
    setup_log_db()

    try:
        conn = sqlite3.connect(WAREHOUSE_DB)

        # Simulate + insert new data
        new_batch     = simulate_new_data(conn, batch_size=500)
        rows_inserted = insert_new_data(conn, new_batch)

        # Recompute KPIs
        recompute_kpis(conn)

        # Re-export for Power BI
        re_export_powerbi(conn)

        conn.close()

        duration = (datetime.now() - start_time).total_seconds()

        log_run(
            status         = "SUCCESS",
            rows_processed = len(new_batch),
            rows_inserted  = rows_inserted,
            source_table   = "fact_orders",
            duration_secs  = duration
        )

        log.info(f"PIPELINE COMPLETED in {duration:.2f}s")

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        log_run(
            status         = "FAILED",
            rows_processed = 0,
            rows_inserted  = 0,
            source_table   = "fact_orders",
            duration_secs  = duration,
            error_message  = str(e)
        )
        log.error(f"PIPELINE FAILED: {e}")
        raise


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    run_pipeline()