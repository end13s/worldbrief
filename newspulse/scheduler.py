from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from newspulse.classifier import classify_pending
from newspulse.fetcher import run_all

FETCH_INTERVAL_MINUTES = 30


def refresh():
    """One cycle: pull new articles, then classify whatever is still unclassified."""
    run_all()
    classify_pending()


def start() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    # Run once right away instead of waiting a full interval after startup.
    scheduler.add_job(
        refresh, "interval", minutes=FETCH_INTERVAL_MINUTES,
        next_run_time=datetime.now(), max_instances=1, coalesce=True,
    )
    scheduler.start()
    return scheduler
