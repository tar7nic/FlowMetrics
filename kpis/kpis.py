# kpis/phase5_kpis.py
# Phase 5 - KPI Computation using SQL on SQLite Warehouse

import pandas as pd
import numpy as np
import sqlite3
import os
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
DB_PATH     = "warehouse/supply_chain.db"
KPI_OUT_DIR = "kpis/results"
os.makedirs(KPI_OUT_DIR, exist_ok=True)


# ─────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────
def run_query(conn, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)

def save_kpi(df: pd.DataFrame, name: str):
    path = os.path.join(KPI_OUT_DIR, f"{name}.csv")
    df.to_csv(path, index=False)
    return path


# ─────────────────────────────────────────
# KPI 1 — ON-TIME DELIVERY RATE
# ─────────────────────────────────────────
def kpi_01_on_time_delivery(conn):
    print("\n" + "="*60)
    print("KPI 01: On-Time Delivery Rate")
    print("="*60)

    # Overall
    overall = run_query(conn, """
        SELECT
            COUNT(*)                                AS total_orders,
            SUM(on_time_flag)                       AS on_time_orders,
            ROUND(AVG(on_time_flag) * 100, 2)       AS on_time_rate_pct,
            ROUND((1 - AVG(on_time_flag)) * 100, 2) AS late_rate_pct
        FROM fact_orders
    """)
    print("\n   Overall:")
    print(overall.to_string(index=False))

    # By shipping mode
    by_mode = run_query(conn, """
        SELECT
            shipping_mode,
            COUNT(*)                                AS total_orders,
            ROUND(AVG(on_time_flag) * 100, 2)       AS on_time_rate_pct,
            ROUND(AVG(delivery_delay_days), 2)      AS avg_delay_days
        FROM fact_orders
        GROUP BY shipping_mode
        ORDER BY on_time_rate_pct DESC
    """)
    print("\n   By Shipping Mode:")
    print(by_mode.to_string(index=False))

    # By year
    by_year = run_query(conn, """
        SELECT
            d.year,
            COUNT(*)                                AS total_orders,
            ROUND(AVG(f.on_time_flag) * 100, 2)    AS on_time_rate_pct
        FROM fact_orders f
        JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY d.year
        ORDER BY d.year
    """)
    print("\n   By Year:")
    print(by_year.to_string(index=False))

    result = {"overall": overall, "by_mode": by_mode, "by_year": by_year}
    save_kpi(overall,  "kpi01_on_time_overall")
    save_kpi(by_mode,  "kpi01_on_time_by_mode")
    save_kpi(by_year,  "kpi01_on_time_by_year")
    return result


# ─────────────────────────────────────────
# KPI 2 — FULFILLMENT RATE
# ─────────────────────────────────────────
def kpi_02_fulfillment_rate(conn):
    print("\n" + "="*60)
    print("KPI 02: Fulfillment Rate")
    print("="*60)

    overall = run_query(conn, """
        SELECT
            COUNT(*)                                AS total_orders,
            SUM(is_fulfilled)                       AS fulfilled_orders,
            ROUND(AVG(is_fulfilled) * 100, 2)       AS fulfillment_rate_pct,
            SUM(is_cancelled)                       AS cancelled_orders,
            ROUND(AVG(is_cancelled) * 100, 2)       AS cancellation_rate_pct
        FROM fact_orders
    """)
    print("\n   Overall:")
    print(overall.to_string(index=False))

    by_region = run_query(conn, """
        SELECT
            g.market,
            g.order_region,
            COUNT(*)                                AS total_orders,
            ROUND(AVG(f.is_fulfilled) * 100, 2)    AS fulfillment_rate_pct,
            ROUND(AVG(f.is_cancelled) * 100, 2)    AS cancellation_rate_pct
        FROM fact_orders f
        JOIN dim_geography g ON f.geo_id = g.geo_id
        GROUP BY g.market, g.order_region
        ORDER BY fulfillment_rate_pct DESC
        LIMIT 10
    """)
    print("\n   By Region (Top 10):")
    print(by_region.to_string(index=False))

    save_kpi(overall,   "kpi02_fulfillment_overall")
    save_kpi(by_region, "kpi02_fulfillment_by_region")
    return {"overall": overall, "by_region": by_region}


# ─────────────────────────────────────────
# KPI 3 — AVERAGE DELIVERY DELAY
# ─────────────────────────────────────────
def kpi_03_delivery_delay(conn):
    print("\n" + "="*60)
    print("KPI 03: Average Delivery Delay")
    print("="*60)

    overall = run_query(conn, """
        SELECT
            ROUND(AVG(delivery_delay_days), 2)      AS avg_delay_days,
            ROUND(MIN(delivery_delay_days), 2)      AS min_delay_days,
            ROUND(MAX(delivery_delay_days), 2)      AS max_delay_days,
            SUM(CASE WHEN delivery_delay_days > 0
                THEN 1 ELSE 0 END)                  AS late_orders,
            SUM(CASE WHEN delivery_delay_days <= 0
                THEN 1 ELSE 0 END)                  AS on_time_or_early
        FROM fact_orders
    """)
    print("\n   Overall Delay Stats:")
    print(overall.to_string(index=False))

    by_category = run_query(conn, """
        SELECT
            p.category,
            ROUND(AVG(f.delivery_delay_days), 2)   AS avg_delay_days,
            COUNT(*)                                AS total_orders,
            ROUND(AVG(f.on_time_flag)*100, 2)      AS on_time_pct
        FROM fact_orders f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.category
        ORDER BY avg_delay_days DESC
        LIMIT 10
    """)
    print("\n   Delay by Product Category (Worst 10):")
    print(by_category.to_string(index=False))

    by_month = run_query(conn, """
        SELECT
            d.year,
            d.month,
            d.month_name,
            ROUND(AVG(f.delivery_delay_days), 2)   AS avg_delay_days,
            COUNT(*)                                AS total_orders
        FROM fact_orders f
        JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY d.year, d.month, d.month_name
        ORDER BY d.year, d.month
    """)
    print("\n   Monthly Delay Trend (sample 12):")
    print(by_month.head(12).to_string(index=False))

    save_kpi(overall,     "kpi03_delay_overall")
    save_kpi(by_category, "kpi03_delay_by_category")
    save_kpi(by_month,    "kpi03_delay_by_month")
    return {"overall": overall, "by_category": by_category, "by_month": by_month}


# ─────────────────────────────────────────
# KPI 4 — SUPPLIER LEAD TIME
# ─────────────────────────────────────────
def kpi_04_supplier_lead_time(conn):
    print("\n" + "="*60)
    print("KPI 04: Supplier Lead Time")
    print("="*60)

    by_supplier = run_query(conn, """
        SELECT
            s.department_name                       AS supplier,
            ROUND(AVG(f.days_shipping_real), 2)     AS avg_lead_time_days,
            ROUND(AVG(f.days_shipping_scheduled),2) AS avg_scheduled_days,
            ROUND(AVG(f.delivery_delay_days), 2)    AS avg_delay_days,
            ROUND(AVG(f.on_time_flag)*100, 2)       AS on_time_rate_pct,
            COUNT(DISTINCT f.order_id)              AS total_orders
        FROM fact_orders f
        JOIN dim_suppliers s ON f.supplier_id = s.supplier_id
        GROUP BY s.department_name
        ORDER BY avg_lead_time_days DESC
    """)
    print("\n   Lead Time by Supplier:")
    print(by_supplier.to_string(index=False))

    save_kpi(by_supplier, "kpi04_supplier_lead_time")
    return by_supplier


# ─────────────────────────────────────────
# KPI 5 — INVENTORY TURNOVER (PROXY)
# ─────────────────────────────────────────
def kpi_05_inventory_turnover(conn):
    print("\n" + "="*60)
    print("KPI 05: Inventory Turnover (Proxy)")
    print("="*60)

    # Proxy: total quantity sold / avg quantity per product
    # Higher = faster moving inventory
    by_product = run_query(conn, """
        SELECT
            p.category,
            p.product_name,
            SUM(f.quantity)                         AS total_qty_sold,
            COUNT(DISTINCT f.order_id)              AS order_count,
            ROUND(SUM(f.sales), 2)                  AS total_revenue,
            ROUND(SUM(f.quantity) * 1.0 /
                COUNT(DISTINCT f.order_id), 2)      AS avg_qty_per_order,
            ROUND(SUM(f.sales) /
                NULLIF(SUM(f.cost_per_order),0),2)  AS turnover_proxy
        FROM fact_orders f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.category, p.product_name
        ORDER BY total_qty_sold DESC
        LIMIT 15
    """)
    print("\n   Top 15 Products by Quantity Sold:")
    print(by_product.to_string(index=False))

    by_category = run_query(conn, """
        SELECT
            p.category,
            SUM(f.quantity)                         AS total_qty_sold,
            ROUND(SUM(f.sales), 2)                  AS total_revenue,
            ROUND(SUM(f.sales) /
                NULLIF(SUM(f.cost_per_order),0),2)  AS turnover_proxy
        FROM fact_orders f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.category
        ORDER BY turnover_proxy DESC
    """)
    print("\n   Turnover Proxy by Category:")
    print(by_category.to_string(index=False))

    save_kpi(by_product,  "kpi05_inventory_by_product")
    save_kpi(by_category, "kpi05_inventory_by_category")
    return {"by_product": by_product, "by_category": by_category}


# ─────────────────────────────────────────
# KPI 6 — PROFIT MARGIN %
# ─────────────────────────────────────────
def kpi_06_profit_margin(conn):
    print("\n" + "="*60)
    print("KPI 06: Profit Margin %")
    print("="*60)

    overall = run_query(conn, """
        SELECT
            ROUND(SUM(sales), 2)                    AS total_revenue,
            ROUND(SUM(profit), 2)                   AS total_profit,
            ROUND(AVG(profit_margin_pct), 2)        AS avg_margin_pct,
            ROUND(MIN(profit_margin_pct), 2)        AS min_margin_pct,
            ROUND(MAX(profit_margin_pct), 2)        AS max_margin_pct
        FROM fact_orders
    """)
    print("\n   Overall:")
    print(overall.to_string(index=False))

    by_category = run_query(conn, """
        SELECT
            p.category,
            ROUND(SUM(f.sales), 2)                  AS total_revenue,
            ROUND(SUM(f.profit), 2)                 AS total_profit,
            ROUND(AVG(f.profit_margin_pct), 2)      AS avg_margin_pct
        FROM fact_orders f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.category
        ORDER BY avg_margin_pct DESC
    """)
    print("\n   By Product Category:")
    print(by_category.to_string(index=False))

    by_segment = run_query(conn, """
        SELECT
            c.segment,
            ROUND(SUM(f.sales), 2)                  AS total_revenue,
            ROUND(SUM(f.profit), 2)                 AS total_profit,
            ROUND(AVG(f.profit_margin_pct), 2)      AS avg_margin_pct
        FROM fact_orders f
        JOIN dim_customers c ON f.customer_id = c.customer_id
        GROUP BY c.segment
        ORDER BY avg_margin_pct DESC
    """)
    print("\n   By Customer Segment:")
    print(by_segment.to_string(index=False))

    save_kpi(overall,     "kpi06_margin_overall")
    save_kpi(by_category, "kpi06_margin_by_category")
    save_kpi(by_segment,  "kpi06_margin_by_segment")
    return {"overall": overall, "by_category": by_category, "by_segment": by_segment}


# ─────────────────────────────────────────
# KPI 7 — COST PER ORDER
# ─────────────────────────────────────────
def kpi_07_cost_per_order(conn):
    print("\n" + "="*60)
    print("KPI 07: Cost Per Order")
    print("="*60)

    overall = run_query(conn, """
        SELECT
            ROUND(AVG(cost_per_order), 2)           AS avg_cost_per_order,
            ROUND(MIN(cost_per_order), 2)           AS min_cost,
            ROUND(MAX(cost_per_order), 2)           AS max_cost,
            ROUND(SUM(cost_per_order), 2)           AS total_cost
        FROM fact_orders
    """)
    print("\n   Overall:")
    print(overall.to_string(index=False))

    by_shipping = run_query(conn, """
        SELECT
            shipping_mode,
            ROUND(AVG(cost_per_order), 2)           AS avg_cost_per_order,
            ROUND(AVG(sales), 2)                    AS avg_sales,
            ROUND(AVG(profit_margin_pct), 2)        AS avg_margin_pct,
            COUNT(*)                                AS total_orders
        FROM fact_orders
        GROUP BY shipping_mode
        ORDER BY avg_cost_per_order DESC
    """)
    print("\n   By Shipping Mode:")
    print(by_shipping.to_string(index=False))

    by_market = run_query(conn, """
        SELECT
            g.market,
            ROUND(AVG(f.cost_per_order), 2)         AS avg_cost_per_order,
            ROUND(SUM(f.cost_per_order), 2)         AS total_cost,
            COUNT(*)                                AS total_orders
        FROM fact_orders f
        JOIN dim_geography g ON f.geo_id = g.geo_id
        GROUP BY g.market
        ORDER BY avg_cost_per_order DESC
    """)
    print("\n   By Market:")
    print(by_market.to_string(index=False))

    save_kpi(overall,    "kpi07_cost_overall")
    save_kpi(by_shipping,"kpi07_cost_by_shipping")
    save_kpi(by_market,  "kpi07_cost_by_market")
    return {"overall": overall, "by_shipping": by_shipping, "by_market": by_market}


# ─────────────────────────────────────────
# KPI 8 — CANCELLED ORDER RATE
# ─────────────────────────────────────────
def kpi_08_cancelled_order_rate(conn):
    print("\n" + "="*60)
    print("KPI 08: Cancelled Order Rate")
    print("="*60)

    overall = run_query(conn, """
        SELECT
            COUNT(*)                                AS total_orders,
            SUM(is_cancelled)                       AS cancelled_orders,
            ROUND(AVG(is_cancelled) * 100, 2)       AS cancellation_rate_pct,
            ROUND(SUM(CASE WHEN is_cancelled=1
                THEN sales ELSE 0 END), 2)          AS revenue_lost
        FROM fact_orders
    """)
    print("\n   Overall:")
    print(overall.to_string(index=False))

    by_market = run_query(conn, """
        SELECT
            g.market,
            g.order_region,
            COUNT(*)                                AS total_orders,
            SUM(f.is_cancelled)                     AS cancelled,
            ROUND(AVG(f.is_cancelled)*100, 2)       AS cancellation_rate_pct,
            ROUND(SUM(CASE WHEN f.is_cancelled=1
                THEN f.sales ELSE 0 END), 2)        AS revenue_lost
        FROM fact_orders f
        JOIN dim_geography g ON f.geo_id = g.geo_id
        GROUP BY g.market, g.order_region
        ORDER BY cancellation_rate_pct DESC
        LIMIT 10
    """)
    print("\n   By Region (Top 10 highest cancellation):")
    print(by_market.to_string(index=False))

    by_month = run_query(conn, """
        SELECT
            d.year,
            d.month_name,
            COUNT(*)                                AS total_orders,
            ROUND(AVG(f.is_cancelled)*100, 2)       AS cancellation_rate_pct
        FROM fact_orders f
        JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY d.year, d.month_name, d.month
        ORDER BY d.year, d.month
    """)
    print("\n   Monthly Cancellation Trend (sample 12):")
    print(by_month.head(12).to_string(index=False))

    save_kpi(overall,   "kpi08_cancellation_overall")
    save_kpi(by_market, "kpi08_cancellation_by_region")
    save_kpi(by_month,  "kpi08_cancellation_by_month")
    return {"overall": overall, "by_market": by_market, "by_month": by_month}


# ─────────────────────────────────────────
# KPI 9 — PERFECT ORDER RATE
# ─────────────────────────────────────────
def kpi_09_perfect_order_rate(conn):
    print("\n" + "="*60)
    print("KPI 09: Perfect Order Rate")
    print("="*60)

    # Perfect order = on time + fulfilled + not cancelled
    overall = run_query(conn, """
        SELECT
            COUNT(*)                                    AS total_orders,
            SUM(perfect_order_flag)                     AS perfect_orders,
            ROUND(AVG(perfect_order_flag)*100, 2)       AS perfect_order_rate_pct,
            SUM(CASE WHEN on_time_flag=1
                AND is_fulfilled=1
                AND is_cancelled=0
                THEN 1 ELSE 0 END)                      AS verified_perfect_orders
        FROM fact_orders
    """)
    print("\n   Overall:")
    print(overall.to_string(index=False))

    by_supplier = run_query(conn, """
        SELECT
            s.department_name                           AS supplier,
            COUNT(*)                                    AS total_orders,
            ROUND(AVG(f.perfect_order_flag)*100, 2)     AS perfect_order_rate_pct,
            ROUND(AVG(f.on_time_flag)*100, 2)           AS on_time_rate_pct,
            ROUND(AVG(f.is_fulfilled)*100, 2)           AS fulfillment_rate_pct
        FROM fact_orders f
        JOIN dim_suppliers s ON f.supplier_id = s.supplier_id
        GROUP BY s.department_name
        ORDER BY perfect_order_rate_pct DESC
    """)
    print("\n   By Supplier:")
    print(by_supplier.to_string(index=False))

    by_category = run_query(conn, """
        SELECT
            p.category,
            COUNT(*)                                    AS total_orders,
            ROUND(AVG(f.perfect_order_flag)*100, 2)     AS perfect_order_rate_pct
        FROM fact_orders f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.category
        ORDER BY perfect_order_rate_pct DESC
    """)
    print("\n   By Product Category:")
    print(by_category.to_string(index=False))

    save_kpi(overall,     "kpi09_perfect_order_overall")
    save_kpi(by_supplier, "kpi09_perfect_order_by_supplier")
    save_kpi(by_category, "kpi09_perfect_order_by_category")
    return {"overall": overall, "by_supplier": by_supplier, "by_category": by_category}


# ─────────────────────────────────────────
# KPI 10 — REVENUE AT RISK
# ─────────────────────────────────────────
def kpi_10_revenue_at_risk(conn):
    print("\n" + "="*60)
    print("KPI 10: Revenue At Risk")
    print("="*60)

    overall = run_query(conn, """
        SELECT
            ROUND(SUM(sales), 2)                    AS total_revenue,
            ROUND(SUM(revenue_at_risk), 2)          AS total_revenue_at_risk,
            ROUND(SUM(revenue_at_risk) /
                NULLIF(SUM(sales),0) * 100, 2)      AS risk_pct_of_revenue,
            COUNT(CASE WHEN revenue_at_risk > 0
                THEN 1 END)                         AS at_risk_orders
        FROM fact_orders
    """)
    print("\n   Overall:")
    print(overall.to_string(index=False))

    by_region = run_query(conn, """
        SELECT
            g.market,
            g.order_region,
            ROUND(SUM(f.revenue_at_risk), 2)        AS revenue_at_risk,
            ROUND(SUM(f.sales), 2)                  AS total_revenue,
            ROUND(SUM(f.revenue_at_risk) /
                NULLIF(SUM(f.sales),0)*100, 2)      AS risk_pct
        FROM fact_orders f
        JOIN dim_geography g ON f.geo_id = g.geo_id
        GROUP BY g.market, g.order_region
        ORDER BY revenue_at_risk DESC
        LIMIT 10
    """)
    print("\n   By Region (Top 10):")
    print(by_region.to_string(index=False))

    by_category = run_query(conn, """
        SELECT
            p.category,
            ROUND(SUM(f.revenue_at_risk), 2)        AS revenue_at_risk,
            ROUND(SUM(f.sales), 2)                  AS total_revenue,
            ROUND(SUM(f.revenue_at_risk) /
                NULLIF(SUM(f.sales),0)*100, 2)      AS risk_pct
        FROM fact_orders f
        JOIN dim_products p ON f.product_id = p.product_id
        GROUP BY p.category
        ORDER BY revenue_at_risk DESC
    """)
    print("\n   By Category:")
    print(by_category.to_string(index=False))

    save_kpi(overall,     "kpi10_revenue_at_risk_overall")
    save_kpi(by_region,   "kpi10_revenue_at_risk_by_region")
    save_kpi(by_category, "kpi10_revenue_at_risk_by_category")
    return {"overall": overall, "by_region": by_region, "by_category": by_category}


# ─────────────────────────────────────────
# FINAL SUMMARY DASHBOARD (All KPIs)
# ─────────────────────────────────────────
def print_executive_summary(conn):
    print("\n" + "="*60)
    print("EXECUTIVE SUMMARY — ALL 10 KPIs")
    print("="*60)

    summary = run_query(conn, """
        SELECT
            COUNT(DISTINCT order_id)                    AS total_orders,
            ROUND(SUM(sales), 2)                        AS total_revenue,
            ROUND(SUM(profit), 2)                       AS total_profit,
            ROUND(AVG(profit_margin_pct), 2)            AS avg_profit_margin_pct,
            ROUND(AVG(on_time_flag) * 100, 2)           AS on_time_delivery_rate,
            ROUND(AVG(is_fulfilled) * 100, 2)           AS fulfillment_rate,
            ROUND(AVG(is_cancelled) * 100, 2)           AS cancellation_rate,
            ROUND(AVG(perfect_order_flag) * 100, 2)     AS perfect_order_rate,
            ROUND(AVG(delivery_delay_days), 2)          AS avg_delivery_delay_days,
            ROUND(AVG(cost_per_order), 2)               AS avg_cost_per_order,
            ROUND(SUM(revenue_at_risk), 2)              AS total_revenue_at_risk,
            ROUND(SUM(revenue_at_risk) /
                NULLIF(SUM(sales),0)*100, 2)            AS revenue_at_risk_pct
        FROM fact_orders
    """)

    # Print as vertical table for readability
    kpi_labels = {
        "total_orders"           : "Total Orders",
        "total_revenue"          : "Total Revenue ($)",
        "total_profit"           : "Total Profit ($)",
        "avg_profit_margin_pct"  : "Avg Profit Margin (%)",
        "on_time_delivery_rate"  : "On-Time Delivery Rate (%)",
        "fulfillment_rate"       : "Fulfillment Rate (%)",
        "cancellation_rate"      : "Cancellation Rate (%)",
        "perfect_order_rate"     : "Perfect Order Rate (%)",
        "avg_delivery_delay_days": "Avg Delivery Delay (days)",
        "avg_cost_per_order"     : "Avg Cost Per Order ($)",
        "total_revenue_at_risk"  : "Total Revenue At Risk ($)",
        "revenue_at_risk_pct"    : "Revenue At Risk (%)",
    }

    print(f"\n   {'KPI':<35} {'VALUE':>15}")
    print(f"   {'-'*50}")
    for col, label in kpi_labels.items():
        val = summary[col].iloc[0]
        print(f"   {label:<35} {str(val):>15}")

    save_kpi(summary, "kpi_executive_summary")
    return summary


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found: {DB_PATH}\nRun Phase 4 first.")

    conn = sqlite3.connect(DB_PATH)

    kpi_01_on_time_delivery(conn)
    kpi_02_fulfillment_rate(conn)
    kpi_03_delivery_delay(conn)
    kpi_04_supplier_lead_time(conn)
    kpi_05_inventory_turnover(conn)
    kpi_06_profit_margin(conn)
    kpi_07_cost_per_order(conn)
    kpi_08_cancelled_order_rate(conn)
    kpi_09_perfect_order_rate(conn)
    kpi_10_revenue_at_risk(conn)

    print_executive_summary(conn)

    conn.close()

    print("\n" + "="*60)
    print("✅ PHASE 5 COMPLETE")
    print("="*60)
    print(f"""
KPI result CSVs saved to: kpis/results/
  kpi01_on_time_overall.csv
  kpi02_fulfillment_overall.csv
  kpi03_delay_overall.csv
  kpi04_supplier_lead_time.csv
  kpi05_inventory_by_category.csv
  kpi06_margin_overall.csv
  kpi07_cost_overall.csv
  kpi08_cancellation_overall.csv
  kpi09_perfect_order_overall.csv
  kpi10_revenue_at_risk_overall.csv
  kpi_executive_summary.csv


""")