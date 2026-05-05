# Phase 1 - Load and Understand the DataCo Supply Chain Dataset

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
RAW_DATA_PATH = "data/raw/DataCoSupplyChainDataset.csv"

# ─────────────────────────────────────────
# STEP 1: LOAD DATASET
# ─────────────────────────────────────────
def load_dataset(path: str) -> pd.DataFrame:
    print("\n" + "="*60)
    print("STEP 1: Loading Dataset")
    print("="*60)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found at: {path}\nPlease download it from Kaggle and place it in data/raw/")

    # DataCo CSV has encoding issues — latin-1 fixes it
    df = pd.read_csv(path, encoding="latin-1")
    print(f"✅ Loaded successfully!")
    print(f"   Rows    : {df.shape[0]:,}")
    print(f"   Columns : {df.shape[1]}")
    return df


# ─────────────────────────────────────────
# STEP 2: COLUMN OVERVIEW
# ─────────────────────────────────────────
def explore_columns(df: pd.DataFrame):
    print("\n" + "="*60)
    print("STEP 2: Column Overview")
    print("="*60)

    col_info = pd.DataFrame({
        "Column": df.columns,
        "DType": df.dtypes.values,
        "Nulls": df.isnull().sum().values,
        "Null%": (df.isnull().sum().values / len(df) * 100).round(2),
        "Unique": df.nunique().values,
        "Sample": [df[c].dropna().iloc[0] if df[c].dropna().shape[0] > 0 else "N/A" for c in df.columns]
    })

    print(col_info.to_string(index=False))
    return col_info


# ─────────────────────────────────────────
# STEP 3: GROUP COLUMNS BY DOMAIN
# ─────────────────────────────────────────
def identify_domain_columns(df: pd.DataFrame):
    print("\n" + "="*60)
    print("STEP 3: Grouping Columns by Domain")
    print("="*60)

    # These are the key groups we'll use for our star schema later
    order_cols = [
        "Order Id", "order date (DateOrders)", "Order Status",
        "shipping date (DateOrders)", "Shipping Mode", "Days for shipping (real)",
        "Days for shipment (scheduled)", "Delivery Status",
        "Late_delivery_risk", "Sales", "Order Item Quantity",
        "Order Item Discount", "Order Item Discount Rate",
        "Order Item Product Price", "Order Item Profit Ratio",
        "Order Profit Per Order", "Order Item Total"
    ]

    customer_cols = [
        "Customer Id", "Customer Fname", "Customer Lname",
        "Customer Email", "Customer Segment", "Customer City",
        "Customer State", "Customer Country", "Customer Zipcode"
    ]

    product_cols = [
        "Product Card Id", "Product Name", "Product Category Id",
        "Category Name", "Product Price", "Product Status"
    ]

    geo_cols = [
        "Market", "Order Region", "Order Country", "Order City",
        "Order State", "Latitude", "Longitude"
    ]

    # Print each group
    domains = {
        "ORDER / TRANSACTION": order_cols,
        "CUSTOMER":            customer_cols,
        "PRODUCT":             product_cols,
        "GEOGRAPHY":           geo_cols,
    }

    for domain, cols in domains.items():
        existing = [c for c in cols if c in df.columns]
        missing  = [c for c in cols if c not in df.columns]
        print(f"\n📦 {domain} ({len(existing)} columns found)")
        for c in existing:
            print(f"   ✅  {c}")
        if missing:
            for c in missing:
                print(f"   ❌  {c}  ← not in dataset")

    return domains


# ─────────────────────────────────────────
# STEP 4: KEY STATISTICS
# ─────────────────────────────────────────
def key_statistics(df: pd.DataFrame):
    print("\n" + "="*60)
    print("STEP 4: Key Business Statistics")
    print("="*60)

    stats = {
        "Total Orders"           : df["Order Id"].nunique() if "Order Id" in df.columns else "N/A",
        "Total Customers"        : df["Customer Id"].nunique() if "Customer Id" in df.columns else "N/A",
        "Total Products"         : df["Product Card Id"].nunique() if "Product Card Id" in df.columns else "N/A",
        "Total Categories"       : df["Category Name"].nunique() if "Category Name" in df.columns else "N/A",
        "Markets"                : df["Market"].nunique() if "Market" in df.columns else "N/A",
        "Order Regions"          : df["Order Region"].nunique() if "Order Region" in df.columns else "N/A",
        "Delivery Statuses"      : df["Delivery Status"].unique().tolist() if "Delivery Status" in df.columns else "N/A",
        "Order Statuses"         : df["Order Status"].unique().tolist() if "Order Status" in df.columns else "N/A",
        "Shipping Modes"         : df["Shipping Mode"].unique().tolist() if "Shipping Mode" in df.columns else "N/A",
        "Date Range (Order)"     : f"{df['order date (DateOrders)'].min()} → {df['order date (DateOrders)'].max()}" if "order date (DateOrders)" in df.columns else "N/A",
        "Total Revenue ($)"      : f"${df['Sales'].sum():,.2f}" if "Sales" in df.columns else "N/A",
        "Total Profit ($)"       : f"${df['Order Profit Per Order'].sum():,.2f}" if "Order Profit Per Order" in df.columns else "N/A",
        "Avg Profit Per Order"   : f"${df['Order Profit Per Order'].mean():,.2f}" if "Order Profit Per Order" in df.columns else "N/A",
        "Late Delivery Risk %"   : f"{df['Late_delivery_risk'].mean()*100:.1f}%" if "Late_delivery_risk" in df.columns else "N/A",
    }

    for k, v in stats.items():
        print(f"   {k:<30}: {v}")

    return stats


# ─────────────────────────────────────────
# STEP 5: CREATE DOMAIN DATAFRAMES
# ─────────────────────────────────────────
def create_domain_dataframes(df: pd.DataFrame):
    print("\n" + "="*60)
    print("STEP 5: Creating Domain DataFrames")
    print("="*60)

    # --- Orders ---
    order_cols = [c for c in [
        "Order Id", "order date (DateOrders)", "shipping date (DateOrders)",
        "Order Status", "Shipping Mode", "Delivery Status", "Late_delivery_risk",
        "Days for shipping (real)", "Days for shipment (scheduled)",
        "Sales", "Order Item Quantity", "Order Item Discount",
        "Order Item Discount Rate", "Order Item Product Price",
        "Order Item Profit Ratio", "Order Profit Per Order", "Order Item Total",
        "Customer Id", "Product Card Id", "Market", "Order Region",
        "Order Country", "Order City", "Order State"
    ] if c in df.columns]

    df_orders = df[order_cols].copy()
    df_orders.rename(columns={
        "order date (DateOrders)"    : "order_date",
        "shipping date (DateOrders)" : "ship_date",
        "Order Id"                   : "order_id",
        "Customer Id"                : "customer_id",
        "Product Card Id"            : "product_id",
        "Order Status"               : "order_status",
        "Shipping Mode"              : "shipping_mode",
        "Delivery Status"            : "delivery_status",
        "Late_delivery_risk"         : "late_delivery_risk",
        "Days for shipping (real)"   : "days_shipping_real",
        "Days for shipment (scheduled)": "days_shipping_scheduled",
        "Sales"                      : "sales",
        "Order Item Quantity"        : "quantity",
        "Order Item Discount"        : "discount",
        "Order Item Discount Rate"   : "discount_rate",
        "Order Item Product Price"   : "unit_price",
        "Order Item Profit Ratio"    : "profit_ratio",
        "Order Profit Per Order"     : "profit",
        "Order Item Total"           : "item_total",
        "Market"                     : "market",
        "Order Region"               : "order_region",
        "Order Country"              : "order_country",
        "Order City"                 : "order_city",
        "Order State"                : "order_state"
    }, inplace=True)

    # --- Customers ---
    cust_cols = [c for c in [
        "Customer Id", "Customer Fname", "Customer Lname",
        "Customer Email", "Customer Segment", "Customer City",
        "Customer State", "Customer Country", "Customer Zipcode"
    ] if c in df.columns]

    df_customers = df[cust_cols].drop_duplicates(subset=["Customer Id"]).copy()
    df_customers.rename(columns={
        "Customer Id"       : "customer_id",
        "Customer Fname"    : "first_name",
        "Customer Lname"    : "last_name",
        "Customer Email"    : "email",
        "Customer Segment"  : "segment",
        "Customer City"     : "city",
        "Customer State"    : "state",
        "Customer Country"  : "country",
        "Customer Zipcode"  : "zipcode"
    }, inplace=True)

    # --- Products ---
    prod_cols = [c for c in [
        "Product Card Id", "Product Name", "Category Name",
        "Product Price", "Product Status", "Product Category Id"
    ] if c in df.columns]

    df_products = df[prod_cols].drop_duplicates(subset=["Product Card Id"]).copy()
    df_products.rename(columns={
        "Product Card Id"    : "product_id",
        "Product Name"       : "product_name",
        "Category Name"      : "category",
        "Product Price"      : "price",
        "Product Status"     : "status",
        "Product Category Id": "category_id"
    }, inplace=True)

    # Print summaries
    print(f"\n📋 df_orders    : {df_orders.shape[0]:,} rows × {df_orders.shape[1]} cols")
    print(df_orders.head(3).to_string())

    print(f"\n👤 df_customers : {df_customers.shape[0]:,} rows × {df_customers.shape[1]} cols")
    print(df_customers.head(3).to_string())

    print(f"\n📦 df_products  : {df_products.shape[0]:,} rows × {df_products.shape[1]} cols")
    print(df_products.head(3).to_string())

    return df_orders, df_customers, df_products


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
if __name__ == "__main__":
    df             = load_dataset(RAW_DATA_PATH)
    col_info       = explore_columns(df)
    domains        = identify_domain_columns(df)
    stats          = key_statistics(df)
    df_orders, df_customers, df_products = create_domain_dataframes(df)

    print("\n" + "="*60)
    print("✅ PHASE 1 COMPLETE")
    print("="*60)
    print("""
Next Steps (Phase 2):
  - Clean nulls and fix data types
  - Convert date columns
  - Standardize category names
  - Save cleaned data to data/raw/cleaned/
""")