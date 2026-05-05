# Phase 3 - PySpark Transformations for DataCo Supply Chain
import os
import warnings
warnings.filterwarnings("ignore")

os.environ["PYSPARK_PYTHON"]        = "python"
os.environ["PYSPARK_DRIVER_PYTHON"] = "python"

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DoubleType, TimestampType
)
from pyspark.sql.window import Window

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
CLEAN_DIR     = "data/raw/cleaned"
PROCESSED_DIR = "data/processed"
os.makedirs(PROCESSED_DIR, exist_ok=True)

ORDERS_CSV    = os.path.join(CLEAN_DIR, "orders_clean.csv")
CUSTOMERS_CSV = os.path.join(CLEAN_DIR, "customers_clean.csv")
PRODUCTS_CSV  = os.path.join(CLEAN_DIR, "products_clean.csv")


# ─────────────────────────────────────────
# STEP 1: START SPARK SESSION
# ─────────────────────────────────────────
def get_spark() -> SparkSession:
    print("\n" + "="*60)
    print("STEP 1: Starting Spark Session")
    print("="*60)

    spark = (
        SparkSession.builder
        .appName("SupplyChainKPI")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("ERROR")
    print(f"   ✅ Spark {spark.version} started")
    print(f"   ✅ Master : {spark.sparkContext.master}")
    print(f"   ✅ Cores  : {spark.sparkContext.defaultParallelism}")
    return spark


# ─────────────────────────────────────────
# STEP 2: LOAD CLEANED CSVs INTO SPARK
# ─────────────────────────────────────────
def load_csvs(spark: SparkSession):
    print("\n" + "="*60)
    print("STEP 2: Loading Cleaned CSVs into Spark")
    print("="*60)

    # ── Orders
    df_orders = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(ORDERS_CSV)
    )

    # Parse date strings explicitly
    df_orders = df_orders.withColumn(
        "order_date", F.to_timestamp("order_date", "yyyy-MM-dd HH:mm:ss")
    ).withColumn(
        "ship_date", F.to_timestamp("ship_date", "yyyy-MM-dd HH:mm:ss")
    )

    # ── Customers
    df_customers = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(CUSTOMERS_CSV)
    )

    # ── Products
    df_products = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(PRODUCTS_CSV)
    )

    print(f"   ✅ df_orders    : {df_orders.count():,} rows | {len(df_orders.columns)} cols")
    print(f"   ✅ df_customers : {df_customers.count():,} rows | {len(df_customers.columns)} cols")
    print(f"   ✅ df_products  : {df_products.count():,} rows | {len(df_products.columns)} cols")

    print("\n   Orders Schema:")
    df_orders.printSchema()

    return df_orders, df_customers, df_products


# ─────────────────────────────────────────
# STEP 3: ENRICH ORDERS WITH BUSINESS COLS
# ─────────────────────────────────────────
def enrich_orders(df_orders):
    print("\n" + "="*60)
    print("STEP 3: Enriching Orders with Business Columns")
    print("="*60)

    df = df_orders

    # ── Recompute delay cleanly in Spark
    df = df.withColumn(
        "delivery_delay_days",
        F.col("days_shipping_real") - F.col("days_shipping_scheduled")
    )

    # ── On-time flag: 1 if delivered on time or early
    df = df.withColumn(
        "on_time_flag",
        F.when(F.col("delivery_delay_days") <= 0, 1).otherwise(0)
    )

    # ── Profit margin %
    df = df.withColumn(
        "profit_margin_pct",
        F.when(
            F.col("sales") != 0,
            F.round((F.col("profit") / F.col("sales")) * 100, 2)
        ).otherwise(0.0)
    )

    # ── Is cancelled
    df = df.withColumn(
        "is_cancelled",
        F.when(F.lower(F.col("order_status")) == "canceled", 1).otherwise(0)
    )

    # ── Is fulfilled
    df = df.withColumn(
        "is_fulfilled",
        F.when(
            (F.col("is_cancelled") == 0) &
            (F.lower(F.col("delivery_status")) != "shipping canceled"),
            1
        ).otherwise(0)
    )

    # ── Revenue at risk
    df = df.withColumn(
        "revenue_at_risk",
        F.when(F.col("is_fulfilled") == 0, F.col("sales")).otherwise(0.0)
    )

    # ── Cost per order proxy
    df = df.withColumn(
        "cost_per_order",
        (F.col("unit_price") * F.col("quantity")) - F.col("profit")
    )

    # ── Fulfilment rate flag (perfect order = on time + fulfilled)
    df = df.withColumn(
        "perfect_order_flag",
        F.when(
            (F.col("on_time_flag") == 1) & (F.col("is_fulfilled") == 1),
            1
        ).otherwise(0)
    )

    # ── Order processing time (days from order to ship)
    df = df.withColumn(
        "processing_days",
        F.datediff(F.col("ship_date"), F.col("order_date"))
    )

    # ── Derived: week number
    df = df.withColumn("order_week", F.weekofyear(F.col("order_date")))

    # Print sample
    print("\n   Enriched columns added:")
    new_cols = [
        "delivery_delay_days", "on_time_flag", "profit_margin_pct",
        "is_cancelled", "is_fulfilled", "revenue_at_risk",
        "cost_per_order", "perfect_order_flag", "processing_days", "order_week"
    ]
    for c in new_cols:
        print(f"   ✅ {c}")

    print("\n   Sample (5 rows, key columns):")
    df.select(
        "order_id", "order_date", "delivery_delay_days",
        "on_time_flag", "profit_margin_pct", "is_fulfilled",
        "perfect_order_flag", "processing_days"
    ).show(5, truncate=False)

    return df


# ─────────────────────────────────────────
# STEP 4: DERIVE SUPPLIER TABLE
# ─────────────────────────────────────────
def derive_suppliers(df_orders, df_products):
    print("\n" + "="*60)
    print("STEP 4: Deriving Supplier-Level Metrics")
    print("="*60)

    # DataCo has no explicit supplier — we derive it from department + category
    # Logic: each department supplies a set of product categories
    # supplier_id = department_id, supplier_name = department_name

    df_suppliers = (
    df_orders.select("department_id", "department_name", "product_id",
            "order_region", "market").dropDuplicates(["department_id", "product_id"])
    )

    # ── Supplier performance metrics (aggregated from orders)
    df_supplier_metrics = (
        df_orders
        .groupBy("department_id", "department_name")
        .agg(
            F.count("order_id")                        .alias("total_orders"),
            F.sum("sales")                             .alias("total_revenue"),
            F.sum("profit")                            .alias("total_profit"),
            F.avg("delivery_delay_days")               .alias("avg_delay_days"),
            F.avg("on_time_flag")                      .alias("on_time_rate"),
            F.avg("days_shipping_real")                .alias("avg_lead_time_days"),
            F.avg("profit_margin_pct")                 .alias("avg_profit_margin"),
            F.sum("is_cancelled")                      .alias("total_cancelled"),
            F.sum("is_fulfilled")                      .alias("total_fulfilled"),
            F.sum("revenue_at_risk")                   .alias("total_revenue_at_risk"),
            F.countDistinct("product_id")              .alias("distinct_products"),
            F.countDistinct("order_region")            .alias("regions_served"),
        )
        .withColumn(
            "cancellation_rate",
            F.round(F.col("total_cancelled") / F.col("total_orders") * 100, 2)
        )
        .withColumn(
            "fulfillment_rate",
            F.round(F.col("total_fulfilled") / F.col("total_orders") * 100, 2)
        )
        .withColumn(
            "on_time_rate_pct",
            F.round(F.col("on_time_rate") * 100, 2)
        )
        .orderBy("department_id")
    )

    print(f"\n   ✅ Supplier metrics derived for {df_supplier_metrics.count()} suppliers")
    print("\n   Supplier Metrics Sample:")
    df_supplier_metrics.show(10, truncate=False)

    return df_supplier_metrics


# ─────────────────────────────────────────
# STEP 5: COMPUTE ORDER-LEVEL KPI ROLLUPS
# ─────────────────────────────────────────
def compute_kpi_rollups(df_orders):
    print("\n" + "="*60)
    print("STEP 5: Computing KPI Rollups")
    print("="*60)

    # ── Monthly KPI rollup
    df_monthly = (
        df_orders
        .groupBy("order_year", "order_month")
        .agg(
            F.count("order_id")                   .alias("total_orders"),
            F.sum("sales")                        .alias("total_revenue"),
            F.sum("profit")                       .alias("total_profit"),
            F.avg("delivery_delay_days")          .alias("avg_delay_days"),
            F.avg("on_time_flag")                 .alias("on_time_rate"),
            F.avg("profit_margin_pct")            .alias("avg_profit_margin"),
            F.sum("is_cancelled")                 .alias("cancelled_orders"),
            F.sum("is_fulfilled")                 .alias("fulfilled_orders"),
            F.sum("perfect_order_flag")           .alias("perfect_orders"),
            F.sum("revenue_at_risk")              .alias("revenue_at_risk"),
            F.avg("cost_per_order")               .alias("avg_cost_per_order"),
        )
        .withColumn(
            "cancellation_rate_pct",
            F.round(F.col("cancelled_orders") / F.col("total_orders") * 100, 2)
        )
        .withColumn(
            "fulfillment_rate_pct",
            F.round(F.col("fulfilled_orders") / F.col("total_orders") * 100, 2)
        )
        .withColumn(
            "perfect_order_rate_pct",
            F.round(F.col("perfect_orders") / F.col("total_orders") * 100, 2)
        )
        .withColumn(
            "on_time_rate_pct",
            F.round(F.col("on_time_rate") * 100, 2)
        )
        .orderBy("order_year", "order_month")
    )

    # ── Regional KPI rollup
    df_regional = (
        df_orders
        .groupBy("market", "order_region")
        .agg(
            F.count("order_id")          .alias("total_orders"),
            F.sum("sales")               .alias("total_revenue"),
            F.sum("profit")              .alias("total_profit"),
            F.avg("on_time_flag")        .alias("on_time_rate"),
            F.avg("delivery_delay_days") .alias("avg_delay_days"),
            F.sum("revenue_at_risk")     .alias("revenue_at_risk"),
        )
        .withColumn(
            "on_time_rate_pct",
            F.round(F.col("on_time_rate") * 100, 2)
        )
        .orderBy(F.desc("total_revenue"))
    )

    # ── Shipping mode KPI rollup
    df_shipping = (
        df_orders
        .groupBy("shipping_mode")
        .agg(
            F.count("order_id")          .alias("total_orders"),
            F.avg("days_shipping_real")  .alias("avg_actual_days"),
            F.avg("delivery_delay_days") .alias("avg_delay_days"),
            F.avg("on_time_flag")        .alias("on_time_rate"),
            F.sum("sales")               .alias("total_revenue"),
        )
        .withColumn(
            "on_time_rate_pct",
            F.round(F.col("on_time_rate") * 100, 2)
        )
        .orderBy(F.desc("total_orders"))
    )

    print("\n   ── Monthly KPI Rollup (sample):")
    df_monthly.show(6, truncate=False)

    print("\n   ── Regional KPI Rollup (top 10):")
    df_regional.show(10, truncate=False)

    print("\n   ── Shipping Mode KPI Rollup:")
    df_shipping.show(10, truncate=False)

    return df_monthly, df_regional, df_shipping


# ─────────────────────────────────────────
# STEP 6: SAVE AS PARQUET
# ─────────────────────────────────────────
def save_parquet(
    df_orders, df_customers, df_products,
    df_supplier_metrics, df_monthly, df_regional, df_shipping,
    out_dir: str
):
    print("\n" + "="*60)
    print("STEP 6: Saving to Parquet")
    print("="*60)

    outputs = {
        "orders"           : df_orders,
        "customers"        : df_customers,
        "products"         : df_products,
        "supplier_metrics" : df_supplier_metrics,
        "kpi_monthly"      : df_monthly,
        "kpi_regional"     : df_regional,
        "kpi_shipping"     : df_shipping,
    }

    for name, df in outputs.items():
        path = os.path.join(out_dir, name)
        df.coalesce(1).write.mode("overwrite").parquet(path)
        print(f"   ✅ Saved → {path}/")

    print(f"\n   All parquet files saved to: {out_dir}/")


# ─────────────────────────────────────────
# STEP 7: QUICK VALIDATION
# ─────────────────────────────────────────
def validate_parquet(spark: SparkSession, out_dir: str):
    print("\n" + "="*60)
    print("STEP 7: Validating Parquet Files")
    print("="*60)

    tables = [
        "orders", "customers", "products",
        "supplier_metrics", "kpi_monthly", "kpi_regional", "kpi_shipping"
    ]

    for name in tables:
        path = os.path.join(out_dir, name)
        df   = spark.read.parquet(path)
        print(f"   ✅ {name:<20} {df.count():>8,} rows | {len(df.columns):>3} cols")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    spark = get_spark()

    df_orders, df_customers, df_products = load_csvs(spark)

    df_orders           = enrich_orders(df_orders)
    df_supplier_metrics = derive_suppliers(df_orders, df_products)

    df_monthly, df_regional, df_shipping = compute_kpi_rollups(df_orders)

    save_parquet(
        df_orders, df_customers, df_products,
        df_supplier_metrics, df_monthly, df_regional, df_shipping,
        PROCESSED_DIR
    )

    validate_parquet(spark, PROCESSED_DIR)

    spark.stop()

    print("\n" + "="*60)
    print("✅ PHASE 3 COMPLETE")
    print("="*60)
    print("""
Parquet files saved to data/processed/:
  orders/             ← enriched fact table (180K rows)
  customers/          ← customer dimension
  products/           ← product dimension
  supplier_metrics/   ← derived supplier KPIs
  kpi_monthly/        ← monthly rollups
  kpi_regional/       ← regional rollups
  kpi_shipping/       ← shipping mode rollups

New columns added in Spark:
  delivery_delay_days   on_time_flag      profit_margin_pct
  is_cancelled          is_fulfilled      revenue_at_risk
  cost_per_order        perfect_order_flag processing_days
  order_week
""")