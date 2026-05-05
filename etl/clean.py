# Phase 2 - Data Cleaning for DataCo Supply Chain Dataset

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
RAW_DATA_PATH   = "data/raw/DataCoSupplyChainDataset.csv"
CLEAN_OUT_DIR   = "data/raw/cleaned"
os.makedirs(CLEAN_OUT_DIR, exist_ok=True)


# ─────────────────────────────────────────
# STEP 1: RELOAD RAW DATA
# ─────────────────────────────────────────
def load_raw(path: str) -> pd.DataFrame:
    print("\n" + "="*60)
    print("STEP 1: Loading Raw Dataset")
    print("="*60)
    df = pd.read_csv(path, encoding="latin-1")
    print(f"✅ Loaded {df.shape[0]:,} rows × {df.shape[1]} columns")
    return df


# ─────────────────────────────────────────
# STEP 2: NULL ANALYSIS + FIX
# ─────────────────────────────────────────
def fix_nulls(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "="*60)
    print("STEP 2: Null Analysis and Fixing")
    print("="*60)

    # Show columns with nulls before fixing
    null_counts = df.isnull().sum()
    null_cols   = null_counts[null_counts > 0]
    print("\nColumns with nulls (before fix):")
    for col, cnt in null_cols.items():
        pct = cnt / len(df) * 100
        print(f"   {col:<45} {cnt:>6} nulls  ({pct:.2f}%)")

    # ── Numeric columns → fill with median
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for col in num_cols:
        if df[col].isnull().sum() > 0:
            median_val = df[col].median()
            df[col].fillna(median_val, inplace=True)
            print(f"   ✅ Filled numeric null [{col}] with median={median_val:.2f}")

    # ── Categorical/text columns → fill with 'Unknown'
    cat_cols = df.select_dtypes(include=["object"]).columns.tolist()
    for col in cat_cols:
        if df[col].isnull().sum() > 0:
            df[col].fillna("Unknown", inplace=True)
            print(f"   ✅ Filled text null    [{col}] with 'Unknown'")

    # Confirm no nulls remain
    remaining = df.isnull().sum().sum()
    print(f"\n✅ Nulls remaining after fix: {remaining}")
    return df


# ─────────────────────────────────────────
# STEP 3: FIX DATE COLUMNS
# ─────────────────────────────────────────
def fix_dates(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "="*60)
    print("STEP 3: Fixing Date Columns")
    print("="*60)

    date_cols = {
        "order date (DateOrders)"    : "order_date",
        "shipping date (DateOrders)" : "ship_date"
    }

    for raw_col, clean_col in date_cols.items():
        if raw_col in df.columns:
            df[clean_col] = pd.to_datetime(df[raw_col], infer_datetime_format=True, errors="coerce")
            bad_dates     = df[clean_col].isnull().sum()
            print(f"   ✅ Converted [{raw_col}] → [{clean_col}]")
            print(f"      Range : {df[clean_col].min().date()} → {df[clean_col].max().date()}")
            print(f"      Bad/unparsed dates: {bad_dates}")
            df.drop(columns=[raw_col], inplace=True)

    # Extract useful date parts from order_date
    df["order_year"]    = df["order_date"].dt.year
    df["order_month"]   = df["order_date"].dt.month
    df["order_quarter"] = df["order_date"].dt.quarter
    df["order_dow"]     = df["order_date"].dt.day_name()   # Mon, Tue...

    print(f"\n   ✅ Added: order_year, order_month, order_quarter, order_dow")
    print(f"      Years in data : {sorted(df['order_year'].unique().tolist())}")
    return df


# ─────────────────────────────────────────
# STEP 4: STANDARDIZE CATEGORICAL COLUMNS
# ─────────────────────────────────────────
def standardize_categories(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "="*60)
    print("STEP 4: Standardizing Categorical Columns")
    print("="*60)

    # ── Rename messy column names to snake_case
    rename_map = {
        "Order Id"                       : "order_id",
        "Customer Id"                    : "customer_id",
        "Product Card Id"                : "product_id",
        "Order Status"                   : "order_status",
        "Shipping Mode"                  : "shipping_mode",
        "Delivery Status"                : "delivery_status",
        "Late_delivery_risk"             : "late_delivery_risk",
        "Days for shipping (real)"       : "days_shipping_real",
        "Days for shipment (scheduled)"  : "days_shipping_scheduled",
        "Sales"                          : "sales",
        "Order Item Quantity"            : "quantity",
        "Order Item Discount"            : "discount",
        "Order Item Discount Rate"       : "discount_rate",
        "Order Item Product Price"       : "unit_price",
        "Order Item Profit Ratio"        : "profit_ratio",
        "Order Profit Per Order"         : "profit",
        "Order Item Total"               : "item_total",
        "Market"                         : "market",
        "Order Region"                   : "order_region",
        "Order Country"                  : "order_country",
        "Order City"                     : "order_city",
        "Order State"                    : "order_state",
        "Customer Fname"                 : "first_name",
        "Customer Lname"                 : "last_name",
        "Customer Email"                 : "email",
        "Customer Segment"               : "segment",
        "Customer City"                  : "customer_city",
        "Customer State"                 : "customer_state",
        "Customer Country"               : "customer_country",
        "Customer Zipcode"               : "zipcode",
        "Product Name"                   : "product_name",
        "Category Name"                  : "category",
        "Product Price"                  : "product_price",
        "Product Status"                 : "product_status",
        "Product Category Id"            : "category_id",
        "Latitude"                       : "latitude",
        "Longitude"                      : "longitude",
        "Type"                           : "payment_type",
        "Department Id"                  : "department_id",
        "Department Name"                : "department_name",
        "Order Item Cardprod Id"         : "cardprod_id",
        "Order Item Id"                  : "order_item_id",
        "Order Customer Id"              : "order_customer_id",
    }

    # Only rename columns that exist
    existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
    df.rename(columns=existing_renames, inplace=True)
    print(f"   ✅ Renamed {len(existing_renames)} columns to snake_case")

    # ── Standardize text values: strip whitespace, title case
    text_cols = ["order_status", "shipping_mode", "delivery_status",
                 "market", "order_region", "segment", "category",
                 "payment_type", "department_name"]

    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    print(f"   ✅ Stripped and title-cased text columns")

    # ── Show unique values for key categoricals
    for col in ["order_status", "delivery_status", "shipping_mode", "market", "segment"]:
        if col in df.columns:
            vals = df[col].unique().tolist()
            print(f"\n   [{col}] → {vals}")

    return df


# ─────────────────────────────────────────
# STEP 5: ADD DERIVED COLUMNS
# ─────────────────────────────────────────
def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "="*60)
    print("STEP 5: Adding Derived Columns")
    print("="*60)

    # ── Delivery delay (actual - scheduled)
    if "days_shipping_real" in df.columns and "days_shipping_scheduled" in df.columns:
        df["delivery_delay_days"] = df["days_shipping_real"] - df["days_shipping_scheduled"]
        print(f"   ✅ delivery_delay_days  (mean={df['delivery_delay_days'].mean():.2f} days)")

    # ── On-time delivery flag (1 = on time or early, 0 = late)
    if "delivery_delay_days" in df.columns:
        df["on_time_flag"] = (df["delivery_delay_days"] <= 0).astype(int)
        on_time_pct = df["on_time_flag"].mean() * 100
        print(f"   ✅ on_time_flag         (on-time rate = {on_time_pct:.1f}%)")

    # ── Profit margin % per order item
    if "profit" in df.columns and "sales" in df.columns:
        df["profit_margin_pct"] = np.where(
            df["sales"] != 0,
            (df["profit"] / df["sales"] * 100).round(2),
            0.0
        )
        print(f"   ✅ profit_margin_pct    (mean={df['profit_margin_pct'].mean():.2f}%)")

    # ── Cancelled order flag
    if "order_status" in df.columns:
        df["is_cancelled"] = (df["order_status"].str.lower() == "canceled").astype(int)
        cancelled_pct = df["is_cancelled"].mean() * 100
        print(f"   ✅ is_cancelled         (cancelled rate = {cancelled_pct:.1f}%)")

    # ── Fulfillment flag: order shipped and not cancelled
    if "delivery_status" in df.columns and "is_cancelled" in df.columns:
        df["is_fulfilled"] = (
            (df["is_cancelled"] == 0) &
            (df["delivery_status"].str.lower() != "shipping canceled")
        ).astype(int)
        fulfilled_pct = df["is_fulfilled"].mean() * 100
        print(f"   ✅ is_fulfilled         (fulfillment rate = {fulfilled_pct:.1f}%)")

    # ── Revenue at risk: unfulfilled orders with sales value
    if "is_fulfilled" in df.columns and "sales" in df.columns:
        df["revenue_at_risk"] = np.where(df["is_fulfilled"] == 0, df["sales"], 0.0)
        total_risk = df["revenue_at_risk"].sum()
        print(f"   ✅ revenue_at_risk      (total = ${total_risk:,.2f})")

    # ── Cost per order proxy = unit_price * quantity - profit
    if all(c in df.columns for c in ["unit_price", "quantity", "profit"]):
        df["cost_per_order"] = (df["unit_price"] * df["quantity"]) - df["profit"]
        print(f"   ✅ cost_per_order       (mean = ${df['cost_per_order'].mean():,.2f})")

    return df


# ─────────────────────────────────────────
# STEP 6: SPLIT INTO DOMAIN DATAFRAMES
# ─────────────────────────────────────────
def split_domains(df: pd.DataFrame):
    print("\n" + "="*60)
    print("STEP 6: Splitting into Domain DataFrames")
    print("="*60)

    # ── ORDERS (fact table base)
    order_cols = [c for c in [
        "order_id", "order_item_id", "customer_id", "product_id",
        "order_date", "ship_date", "order_year", "order_month",
        "order_quarter", "order_dow", "order_status", "shipping_mode",
        "delivery_status", "late_delivery_risk", "days_shipping_real",
        "days_shipping_scheduled", "delivery_delay_days", "on_time_flag",
        "sales", "quantity", "discount", "discount_rate", "unit_price",
        "profit_ratio", "profit", "item_total", "profit_margin_pct",
        "is_cancelled", "is_fulfilled", "revenue_at_risk", "cost_per_order",
        "market", "order_region", "order_country", "order_city", "order_state",
        "payment_type", "department_id", "department_name"
    ] if c in df.columns]
    df_orders = df[order_cols].copy()

    # ── CUSTOMERS (dimension)
    cust_cols = [c for c in [
        "customer_id", "first_name", "last_name", "email",
        "segment", "customer_city", "customer_state",
        "customer_country", "zipcode"
    ] if c in df.columns]
    df_customers = df[cust_cols].drop_duplicates(subset=["customer_id"]).copy()

    # ── PRODUCTS (dimension)
    prod_cols = [c for c in [
        "product_id", "product_name", "category", "category_id",
        "product_price", "product_status", "department_id", "department_name"
    ] if c in df.columns]
    df_products = df[prod_cols].drop_duplicates(subset=["product_id"]).copy()

    # Print summaries
    print(f"\n   📋 df_orders    : {df_orders.shape[0]:,} rows × {df_orders.shape[1]} cols")
    print(f"   👤 df_customers : {df_customers.shape[0]:,} rows × {df_customers.shape[1]} cols")
    print(f"   📦 df_products  : {df_products.shape[0]:,} rows × {df_products.shape[1]} cols")

    return df_orders, df_customers, df_products


# ─────────────────────────────────────────
# STEP 7: SAVE CLEANED FILES
# ─────────────────────────────────────────
def save_cleaned(df_orders, df_customers, df_products, out_dir: str):
    print("\n" + "="*60)
    print("STEP 7: Saving Cleaned Files")
    print("="*60)

    paths = {
        "orders"    : os.path.join(out_dir, "orders_clean.csv"),
        "customers" : os.path.join(out_dir, "customers_clean.csv"),
        "products"  : os.path.join(out_dir, "products_clean.csv"),
    }

    df_orders.to_csv(paths["orders"],    index=False)
    df_customers.to_csv(paths["customers"], index=False)
    df_products.to_csv(paths["products"],  index=False)

    print(f"   ✅ orders_clean.csv    → {paths['orders']}")
    print(f"   ✅ customers_clean.csv → {paths['customers']}")
    print(f"   ✅ products_clean.csv  → {paths['products']}")

    # Quick validation
    print("\n   Validation (reload and check):")
    for name, path in paths.items():
        check = pd.read_csv(path)
        nulls = check.isnull().sum().sum()
        print(f"   [{name}] {check.shape[0]:,} rows | {check.shape[1]} cols | {nulls} nulls")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    df = load_raw(RAW_DATA_PATH)
    df = fix_nulls(df)
    df = fix_dates(df)
    df = standardize_categories(df)
    df = add_derived_columns(df)
    df_orders, df_customers, df_products = split_domains(df)
    save_cleaned(df_orders, df_customers, df_products, CLEAN_OUT_DIR)

    print("\n" + "="*60)
    print("✅ PHASE 2 COMPLETE")
    print("="*60)
    print("""
Output files saved to:
  data/raw/cleaned/orders_clean.csv
  data/raw/cleaned/customers_clean.csv
  data/raw/cleaned/products_clean.csv

New columns added:
  delivery_delay_days  → actual minus scheduled shipping days
  on_time_flag         → 1 if on time, 0 if late
  profit_margin_pct    → profit / sales * 100
  is_cancelled         → 1 if order was canceled
  is_fulfilled         → 1 if order completed successfully
  revenue_at_risk      → sales value of unfulfilled orders
  cost_per_order       → proxy cost calculation

""")