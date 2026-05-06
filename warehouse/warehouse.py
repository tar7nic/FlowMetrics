# Star Schema Data Warehouse Setup 

import pandas as pd
import numpy as np
import sqlite3
import os
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
PROCESSED_DIR = "data/processed"
DB_PATH       = "warehouse/supply_chain.db"
os.makedirs("warehouse", exist_ok=True)

# ─────────────────────────────────────────
# STEP 1: LOAD PROCESSED CSVs
# ─────────────────────────────────────────
def load_processed_data():
    print("\n" + "="*60)
    print("STEP 1: Loading Processed Data")
    print("="*60)

    files = {
        "orders"          : "orders.csv",
        "customers"       : "customers.csv",
        "products"        : "products.csv",
        "supplier_metrics": "supplier_metrics.csv",
        "kpi_monthly"     : "kpi_monthly.csv",
        "kpi_regional"    : "kpi_regional.csv",
        "kpi_shipping"    : "kpi_shipping.csv",
    }

    dfs = {}
    for name, fname in files.items():
        path = os.path.join(PROCESSED_DIR, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing: {path} — run Phase 3 first")
        dfs[name] = pd.read_csv(path)
        print(f"   ✅ {name:<22} {dfs[name].shape[0]:>8,} rows | {dfs[name].shape[1]} cols")

    return dfs


# ─────────────────────────────────────────
# STEP 2: BUILD DIMENSION TABLES
# ─────────────────────────────────────────
def build_dimensions(dfs: dict):
    print("\n" + "="*60)
    print("STEP 2: Building Dimension Tables")
    print("="*60)

    orders   = dfs["orders"]
    products = dfs["products"]

    # ── dim_customers
    dim_customers = dfs["customers"].copy()
    dim_customers.columns = [c.lower().strip() for c in dim_customers.columns]
    dim_customers = dim_customers.drop_duplicates(subset=["customer_id"])
    dim_customers["customer_id"] = dim_customers["customer_id"].astype(int)
    print(f"   ✅ dim_customers : {dim_customers.shape[0]:,} rows")

    # ── dim_products
    dim_products = products.copy()
    dim_products.columns = [c.lower().strip() for c in dim_products.columns]
    dim_products = dim_products.drop_duplicates(subset=["product_id"])
    dim_products["product_id"] = dim_products["product_id"].astype(int)
    print(f"   ✅ dim_products  : {dim_products.shape[0]:,} rows")

    # ── dim_suppliers (derived from department in orders)
    supplier_cols = [c for c in ["department_id", "department_name"] if c in orders.columns]
    dim_suppliers = (
        orders[supplier_cols]
        .drop_duplicates()
        .dropna()
        .reset_index(drop=True)
    )
    dim_suppliers.columns = [c.lower().strip() for c in dim_suppliers.columns]
    dim_suppliers["supplier_id"] = range(1, len(dim_suppliers) + 1)
    # Reorder columns
    dim_suppliers = dim_suppliers[["supplier_id", "department_id", "department_name"]]
    print(f"   ✅ dim_suppliers : {dim_suppliers.shape[0]:,} rows")

    # ── dim_date (derived from order dates)
    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    date_df = orders[["order_date"]].drop_duplicates().dropna().copy()
    date_df["date_id"]      = date_df["order_date"].dt.strftime("%Y%m%d").astype(int)
    date_df["date"]         = date_df["order_date"].dt.date
    date_df["year"]         = date_df["order_date"].dt.year
    date_df["month"]        = date_df["order_date"].dt.month
    date_df["month_name"]   = date_df["order_date"].dt.strftime("%B")
    date_df["quarter"]      = date_df["order_date"].dt.quarter
    date_df["week"]         = date_df["order_date"].dt.isocalendar().week.astype(int)
    date_df["day_of_week"]  = date_df["order_date"].dt.day_name()
    date_df["is_weekend"]   = date_df["order_date"].dt.dayofweek.isin([5, 6]).astype(int)
    dim_date = date_df.drop(columns=["order_date"]).drop_duplicates(subset=["date_id"])
    print(f"   ✅ dim_date      : {dim_date.shape[0]:,} rows")

    # ── dim_geography
    geo_cols = [c for c in
        ["market", "order_region", "order_country", "order_city", "order_state"]
        if c in orders.columns
    ]
    dim_geography = (
        orders[geo_cols]
        .drop_duplicates()
        .dropna()
        .reset_index(drop=True)
    )
    dim_geography["geo_id"] = range(1, len(dim_geography) + 1)
    cols = ["geo_id"] + geo_cols
    dim_geography = dim_geography[cols]
    print(f"   ✅ dim_geography : {dim_geography.shape[0]:,} rows")

    return dim_customers, dim_products, dim_suppliers, dim_date, dim_geography


# ─────────────────────────────────────────
# STEP 3: BUILD FACT TABLE
# ─────────────────────────────────────────
def build_fact_table(dfs: dict, dim_suppliers, dim_geography):
    print("\n" + "="*60)
    print("STEP 3: Building Fact Table")
    print("="*60)

    orders = dfs["orders"].copy()
    orders.columns = [c.lower().strip() for c in orders.columns]

    # Parse dates
    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    orders["ship_date"]  = pd.to_datetime(orders["ship_date"],  errors="coerce")

    # Add date_id for joining with dim_date
    orders["date_id"] = orders["order_date"].dt.strftime("%Y%m%d")
    orders["date_id"] = pd.to_numeric(orders["date_id"], errors="coerce")

    # Add supplier_id via merge on department_id
    if "department_id" in orders.columns and "department_id" in dim_suppliers.columns:
        orders = orders.merge(
            dim_suppliers[["supplier_id", "department_id"]],
            on="department_id",
            how="left"
        )
    else:
        orders["supplier_id"] = None

    # Add geo_id via merge
    geo_cols = [c for c in
        ["market", "order_region", "order_country", "order_city", "order_state"]
        if c in orders.columns and c in dim_geography.columns
    ]
    if geo_cols:
        orders = orders.merge(
            dim_geography[["geo_id"] + geo_cols],
            on=geo_cols,
            how="left"
        )
    else:
        orders["geo_id"] = None

    # ── Select final fact table columns
    fact_cols = [c for c in [
        # Keys
        "order_id", "order_item_id", "customer_id", "product_id",
        "supplier_id", "date_id", "geo_id",
        # Dates
        "order_date", "ship_date",
        # Order details
        "order_status", "shipping_mode", "delivery_status",
        "late_delivery_risk", "payment_type",
        # Time metrics
        "days_shipping_real", "days_shipping_scheduled",
        "delivery_delay_days", "processing_days",
        # KPI flags
        "on_time_flag", "is_cancelled", "is_fulfilled",
        "perfect_order_flag",
        # Financial metrics
        "sales", "quantity", "discount", "discount_rate",
        "unit_price", "profit_ratio", "profit",
        "item_total", "profit_margin_pct",
        "cost_per_order", "revenue_at_risk",
    ] if c in orders.columns]

    fact_orders = orders[fact_cols].copy()

    # Clean up types
    int_cols = ["on_time_flag", "is_cancelled", "is_fulfilled",
                "perfect_order_flag", "late_delivery_risk"]
    for c in int_cols:
        if c in fact_orders.columns:
            fact_orders[c] = pd.to_numeric(fact_orders[c], errors="coerce").fillna(0).astype(int)

    float_cols = ["sales", "profit", "discount", "profit_margin_pct",
                  "cost_per_order", "revenue_at_risk", "item_total"]
    for c in float_cols:
        if c in fact_orders.columns:
            fact_orders[c] = pd.to_numeric(fact_orders[c], errors="coerce").fillna(0.0)

    print(f"   ✅ fact_orders : {fact_orders.shape[0]:,} rows | {fact_orders.shape[1]} cols")
    print(f"\n   Fact table columns:")
    print(f"   {fact_orders.columns.tolist()}")

    return fact_orders


# ─────────────────────────────────────────
# STEP 4: CREATE SQLite DATABASE + LOAD
# ─────────────────────────────────────────
def load_to_sqlite(fact_orders, dim_customers, dim_products,
                   dim_suppliers, dim_date, dim_geography,
                   dfs, db_path):
    print("\n" + "="*60)
    print("STEP 4: Creating SQLite Database and Loading Tables")
    print("="*60)

    # Remove existing DB so we start fresh
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"   🗑️  Removed old database")

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # ── Create tables with proper SQL schema
    cur.executescript("""
        -- DIMENSION: Customers
        CREATE TABLE IF NOT EXISTS dim_customers (
            customer_id     INTEGER PRIMARY KEY,
            first_name      TEXT,
            last_name       TEXT,
            email           TEXT,
            segment         TEXT,
            customer_city   TEXT,
            customer_state  TEXT,
            customer_country TEXT,
            zipcode         TEXT
        );

        -- DIMENSION: Products
        CREATE TABLE IF NOT EXISTS dim_products (
            product_id      INTEGER PRIMARY KEY,
            product_name    TEXT,
            category        TEXT,
            category_id     INTEGER,
            product_price   REAL,
            product_status  TEXT,
            department_id   INTEGER,
            department_name TEXT
        );

        -- DIMENSION: Suppliers
        CREATE TABLE IF NOT EXISTS dim_suppliers (
            supplier_id     INTEGER PRIMARY KEY,
            department_id   INTEGER,
            department_name TEXT
        );

        -- DIMENSION: Date
        CREATE TABLE IF NOT EXISTS dim_date (
            date_id         INTEGER PRIMARY KEY,
            date            TEXT,
            year            INTEGER,
            month           INTEGER,
            month_name      TEXT,
            quarter         INTEGER,
            week            INTEGER,
            day_of_week     TEXT,
            is_weekend      INTEGER
        );

        -- DIMENSION: Geography
        CREATE TABLE IF NOT EXISTS dim_geography (
            geo_id          INTEGER PRIMARY KEY,
            market          TEXT,
            order_region    TEXT,
            order_country   TEXT,
            order_city      TEXT,
            order_state     TEXT
        );

        -- FACT: Orders
        CREATE TABLE IF NOT EXISTS fact_orders (
            order_id              INTEGER,
            order_item_id         INTEGER,
            customer_id           INTEGER,
            product_id            INTEGER,
            supplier_id           INTEGER,
            date_id               INTEGER,
            geo_id                INTEGER,
            order_date            TEXT,
            ship_date             TEXT,
            order_status          TEXT,
            shipping_mode         TEXT,
            delivery_status       TEXT,
            late_delivery_risk    INTEGER,
            payment_type          TEXT,
            days_shipping_real    REAL,
            days_shipping_scheduled REAL,
            delivery_delay_days   REAL,
            processing_days       INTEGER,
            on_time_flag          INTEGER,
            is_cancelled          INTEGER,
            is_fulfilled          INTEGER,
            perfect_order_flag    INTEGER,
            sales                 REAL,
            quantity              INTEGER,
            discount              REAL,
            discount_rate         REAL,
            unit_price            REAL,
            profit_ratio          REAL,
            profit                REAL,
            item_total            REAL,
            profit_margin_pct     REAL,
            cost_per_order        REAL,
            revenue_at_risk       REAL,
            FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
            FOREIGN KEY (product_id)  REFERENCES dim_products(product_id),
            FOREIGN KEY (supplier_id) REFERENCES dim_suppliers(supplier_id),
            FOREIGN KEY (date_id)     REFERENCES dim_date(date_id),
            FOREIGN KEY (geo_id)      REFERENCES dim_geography(geo_id)
        );

        -- KPI ROLLUP TABLES
        CREATE TABLE IF NOT EXISTS kpi_monthly (
            order_year              INTEGER,
            order_month             INTEGER,
            total_orders            INTEGER,
            total_revenue           REAL,
            total_profit            REAL,
            avg_delay_days          REAL,
            on_time_rate            REAL,
            avg_profit_margin       REAL,
            cancelled_orders        INTEGER,
            fulfilled_orders        INTEGER,
            perfect_orders          INTEGER,
            revenue_at_risk         REAL,
            avg_cost_per_order      REAL,
            cancellation_rate   REAL,
            fulfillment_rate    REAL,
            perfect_order_rate_pct  REAL,
            on_time_rate_pct        REAL
        );

        CREATE TABLE IF NOT EXISTS kpi_regional (
            market          TEXT,
            order_region    TEXT,
            total_orders    INTEGER,
            total_revenue   REAL,
            total_profit    REAL,
            on_time_rate    REAL,
            avg_delay_days  REAL,
            revenue_at_risk REAL,
            on_time_rate_pct REAL
        );

        CREATE TABLE IF NOT EXISTS kpi_shipping (
            shipping_mode       TEXT,
            total_orders        INTEGER,
            avg_actual_days     REAL,
            avg_delay_days      REAL,
            on_time_rate        REAL,
            total_revenue       REAL,
            on_time_rate_pct    REAL
        );

        CREATE TABLE IF NOT EXISTS supplier_metrics (
            department_id           INTEGER,
            department_name         TEXT,
            total_orders            INTEGER,
            total_revenue           REAL,
            total_profit            REAL,
            avg_delay_days          REAL,
            on_time_rate            REAL,
            avg_lead_time_days      REAL,
            avg_profit_margin       REAL,
            total_cancelled         INTEGER,
            total_fulfilled         INTEGER,
            total_revenue_at_risk   REAL,
            distinct_products       INTEGER,
            regions_served          INTEGER,
            cancellation_rate_pct   REAL,
            fulfillment_rate_pct    REAL,
            on_time_rate_pct        REAL
        );
    """)
    conn.commit()
    print("   ✅ All table schemas created")

    # ── Load data into tables
    load_map = {
        "dim_customers"  : dim_customers,
        "dim_products"   : dim_products,
        "dim_suppliers"  : dim_suppliers,
        "dim_date"       : dim_date,
        "dim_geography"  : dim_geography,
        "fact_orders"    : fact_orders,
        "kpi_monthly"    : dfs["kpi_monthly"],
        "kpi_regional"   : dfs["kpi_regional"],
        "kpi_shipping"   : dfs["kpi_shipping"],
        "supplier_metrics": dfs["supplier_metrics"],
    }

    for table_name, df in load_map.items():
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"   ✅ Loaded {table_name:<22} → {count:>8,} rows")

    conn.commit()
    conn.close()
    print(f"\n   ✅ Database saved → {db_path}")


# ─────────────────────────────────────────
# STEP 5: VERIFY WITH SQL QUERIES
# ─────────────────────────────────────────
def verify_with_sql(db_path):
    print("\n" + "="*60)
    print("STEP 5: Verifying Star Schema with SQL Queries")
    print("="*60)

    conn = sqlite3.connect(db_path)

    queries = {

        "── Total Revenue & Profit": """
            SELECT
                ROUND(SUM(sales), 2)            AS total_revenue,
                ROUND(SUM(profit), 2)           AS total_profit,
                ROUND(AVG(profit_margin_pct),2) AS avg_margin_pct,
                COUNT(DISTINCT order_id)        AS total_orders,
                COUNT(DISTINCT customer_id)     AS total_customers
            FROM fact_orders
        """,

        "── On-Time vs Late Delivery": """
            SELECT
                delivery_status,
                COUNT(*)                        AS order_count,
                ROUND(COUNT(*) * 100.0 /
                    SUM(COUNT(*)) OVER(), 2)    AS pct
            FROM fact_orders
            GROUP BY delivery_status
            ORDER BY order_count DESC
        """,

        "── Revenue by Market (join geo dim)": """
            SELECT
                g.market,
                ROUND(SUM(f.sales), 2)          AS total_revenue,
                ROUND(AVG(f.profit_margin_pct),2) AS avg_margin,
                COUNT(DISTINCT f.order_id)      AS total_orders
            FROM fact_orders f
            JOIN dim_geography g ON f.geo_id = g.geo_id
            GROUP BY g.market
            ORDER BY total_revenue DESC
        """,

        "── Top 5 Product Categories by Revenue": """
            SELECT
                p.category,
                ROUND(SUM(f.sales), 2)          AS total_revenue,
                ROUND(SUM(f.profit), 2)         AS total_profit,
                COUNT(*)                        AS order_lines
            FROM fact_orders f
            JOIN dim_products p ON f.product_id = p.product_id
            GROUP BY p.category
            ORDER BY total_revenue DESC
            LIMIT 5
        """,

        "── Customer Segment Performance": """
            SELECT
                c.segment,
                COUNT(DISTINCT f.order_id)      AS total_orders,
                ROUND(SUM(f.sales), 2)          AS total_revenue,
                ROUND(AVG(f.profit_margin_pct),2) AS avg_margin_pct
            FROM fact_orders f
            JOIN dim_customers c ON f.customer_id = c.customer_id
            GROUP BY c.segment
            ORDER BY total_revenue DESC
        """,

        "── Yearly KPI Summary": """
            SELECT
                d.year,
                COUNT(DISTINCT f.order_id)          AS total_orders,
                ROUND(SUM(f.sales), 2)              AS total_revenue,
                ROUND(AVG(f.on_time_flag)*100, 2)   AS on_time_rate_pct,
                ROUND(AVG(f.profit_margin_pct), 2)  AS avg_margin_pct,
                ROUND(SUM(f.revenue_at_risk), 2)    AS revenue_at_risk
            FROM fact_orders f
            JOIN dim_date d ON f.date_id = d.date_id
            GROUP BY d.year
            ORDER BY d.year
        """,

       "── Supplier Performance Summary": """
            SELECT
                department_name,
                total_orders,
                ROUND(total_revenue, 2)         AS total_revenue,
                ROUND(on_time_rate_pct, 2)      AS on_time_rate_pct,
                ROUND(fulfillment_rate, 2)       AS fulfillment_rate_pct,
                ROUND(cancellation_rate, 2)      AS cancellation_rate_pct,
                ROUND(avg_lead_time_days, 2)     AS avg_lead_time_days
            FROM supplier_metrics
            ORDER BY total_revenue DESC
            LIMIT 8
        """,
    }

    for title, sql in queries.items():
        print(f"\n   {title}")
        result = pd.read_sql_query(sql, conn)
        print(result.to_string(index=False))

    conn.close()


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":

    dfs = load_processed_data()

    dim_customers, dim_products, dim_suppliers, dim_date, dim_geography = build_dimensions(dfs)

    fact_orders = build_fact_table(dfs, dim_suppliers, dim_geography)

    load_to_sqlite(
        fact_orders,
        dim_customers, dim_products, dim_suppliers,
        dim_date, dim_geography,
        dfs, DB_PATH
    )

    verify_with_sql(DB_PATH)

    print("\n" + "="*60)
    print("✅ PHASE 4 COMPLETE")
    print("="*60)
    print(f"""
Database created → {DB_PATH}

Star Schema Tables:
  FACT    : fact_orders       (180K rows)
  DIM     : dim_customers     (20K rows)
  DIM     : dim_products      (118 rows)
  DIM     : dim_suppliers     (22 rows)
  DIM     : dim_date          (unique dates)
  DIM     : dim_geography     (unique regions)
  ROLLUPS : kpi_monthly, kpi_regional, kpi_shipping, supplier_metrics
""")