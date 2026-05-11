import sqlite3
import pandas as pd

LOG_DB = "pipelines/pipeline_logs/pipeline_log.db"

conn = sqlite3.connect(LOG_DB)
df   = pd.read_sql_query("""
    SELECT * FROM pipeline_runs
    ORDER BY run_id DESC
""", conn)
conn.close()

print("\n" + "="*60)
print("PIPELINE RUN HISTORY")
print("="*60)
print(df.to_string(index=False))