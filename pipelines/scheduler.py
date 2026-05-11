# pipelines/scheduler.py
# Runs daily_pipeline.py every 24 hours

import schedule
import time
import subprocess
import logging
from datetime import datetime

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s | %(message)s"
)
log = logging.getLogger(__name__)

def job():
    log.info("Triggering daily pipeline run...")
    subprocess.run(["python", "pipelines/daily_pipeline.py"], check=True)
    log.info("Pipeline run complete.")

# Schedule to run every day at 6:00 AM
schedule.every().day.at("06:00").do(job)

# Also run immediately on start
job()

log.info("Scheduler running... Press Ctrl+C to stop.")
while True:
    schedule.run_pending()
    time.sleep(60)