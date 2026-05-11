# Export SQLite Warehouse Tables to Power BI-Ready CSVs

import sqlite3
import pandas as pd
import os

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
DB_PATH    = "warehouse/supply_chain.db"
EXPORT_DIR = "powerbi/data"
os.makedirs(EXPORT_DIR, exist_ok=True)

# ─────────────────────────────────────────
# TABLES TO EXPORT
# ─────────────────────────────────────────
TABLES = [
    # Star Schema Core
    "fact_orders",
    "dim_customers",
    "dim_products",
    "dim_suppliers",
    "dim_date",
    "dim_geography",
    # KPI Rollups
    "kpi_monthly",
    "kpi_regional",
    "kpi_shipping",
    "supplier_metrics",
]

# ─────────────────────────────────────────
# EXPORT FUNCTION
# ─────────────────────────────────────────
def export_tables(db_path: str, export_dir: str):
    print("\n" + "="*60)
    print("Exporting Tables for Power BI")
    print("="*60)

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}\nRun Phase 4 first.")

    conn = sqlite3.connect(db_path)

    for table in TABLES:
        try:
            df   = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            path = os.path.join(export_dir, f"{table}.csv")
            df.to_csv(path, index=False)
            print(f"   ✅ {table:<25} → {df.shape[0]:>8,} rows | {df.shape[1]:>3} cols  →  {path}")
        except Exception as e:
            print(f"   ❌ {table} failed: {e}")

    conn.close()

    print("\n" + "="*60)
    print("✅ EXPORT COMPLETE")
    print("="*60)
    print(f"\n   All CSVs saved to: {os.path.abspath(export_dir)}")
    print("""
   Files ready for Power BI:
     fact_orders.csv         ← Main fact table (180K rows)
     dim_customers.csv       ← Customer dimension
     dim_products.csv        ← Product dimension
     dim_suppliers.csv       ← Supplier dimension
     dim_date.csv            ← Date dimension
     dim_geography.csv       ← Geography dimension
     kpi_monthly.csv         ← Monthly KPI rollup
     kpi_regional.csv        ← Regional KPI rollup
     kpi_shipping.csv        ← Shipping mode rollup
     supplier_metrics.csv    ← Supplier performance rollup
""")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    export_tables(DB_PATH, EXPORT_DIR)